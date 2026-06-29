"""FOREMAN Email agent (the stakeholder incident-summary mailer).

This coded agent is the LAST step of the FOREMAN fleet. It takes the FULL
supervisor response object plus the foreman-voice result, uses a FAST LLM
(UiPathChat gpt-4.1-mini) to COMPOSE a concise internal incident-summary email
(subject + body), and sends it via Gmail SMTP with up to three attachments:

  (a) the SOP / report PDF  — fetched from a URL,
  (b) a generated call-transcript.txt — built in-memory from the voice result,
  (c) the worker's video    — fetched from a UiPath Storage Bucket.

CONTRACT
  input : the foreman-supervisor outputs FLATTENED 1:1 (case, diagnosis, risk,
          safety_gate, auto_resolve_blocked, invoked, not_invoked, action_plan,
          summary, worker_message, report_url, errors) + the foreman-voice
          outputs FLATTENED 1:1 (spoken_opener, spoken_recommendation, transcript,
          decision, call_sid, call_to, call_from) + the email config
          (decision_context, recipients, cc, media_blob_path, media_bucket,
          media_folder, max_attachment_mb, dry_run).
  output: { subject, body, attached, sent, error }

NOTE: the supervisor and voice agents expose each output as a SEPARATE field (not
one bundled object), so this agent's Input mirrors those fields one-for-one — every
field can be dragged straight from the upstream node in a Maestro flow.

TWO NODES
  1. ``compose`` — defensively extract the case/diagnosis/risk/fleet/plan/warranty
     fields from the supervisor JSON, then ask the fast LLM for STRICT JSON
     {subject, body}. On any LLM/parse failure it falls back to a plain subject
     + the supervisor ``summary``. Never throws.
  2. ``send`` — build a multipart message, assemble the three attachments (each
     guarded by ``max_attachment_mb`` and individually fault-tolerant), and send
     via smtp.gmail.com:587 + STARTTLS. ``dry_run`` composes + builds attachments
     but does NOT send.

CREDENTIALS are read env-first, then lazily from UiPath Assets in folder
"Shared" — so a local ``.env`` run needs no UiPath connection for SMTP:
  GMAIL_USER         | Gmail-User
  GMAIL_APP_PASSWORD | Gmail-App-Password   (a Google App Password, NOT the login)

Like the rest of the FOREMAN fleet, ``send`` NEVER throws — on any failure it
returns the output contract with a non-empty ``error``; a single bad attachment
is skipped (noted in ``error``) and never blocks the rest of the send.
"""

from __future__ import annotations

import html as _html
import json
import os
import smtplib
import tempfile
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse

import truststore  # corporate TLS proxies — inject the OS trust store into SSL
truststore.inject_into_ssl()

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath_langchain.chat import UiPathChat

# --- Configuration ----------------------------------------------------------

FOLDER = "Shared"                       # folder the Gmail Assets live in
LLM_MODEL = "gpt-4.1-mini-2025-04-14"   # fast model used to compose the email
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# env var  ->  UiPath Asset name (folder "Shared")
ASSET_MAP = {
    "GMAIL_USER": "Gmail-User",
    "GMAIL_APP_PASSWORD": "Gmail-App-Password",
}

COMPOSE_SYSTEM = (
    "You write a concise internal incident-summary email for a field-operations team, "
    "sent AFTER a case was triaged and a human approved the action (often via a voice "
    "call). Output STRICT JSON with exactly two keys: subject and body.\n"
    "SUBJECT (incident-ticket style): 'Incident <case_id>: <fault> - <status>', e.g. "
    "'Incident AST-SCB-DEL-0788: MC4 connector failure - action approved'. Use the "
    "decision to set <status> (approved/on hold/etc.); keep it under ~90 chars.\n"
    "BODY starts with 'Summary of the episode for everyone involved.' then a blank line, "
    "then these labeled lines, each on its own line, only if info is available:\n"
    "   Report: <what happened, who/how flagged>\n"
    "   Root cause: <root cause + confidence + core hazard; use ' -> ' to show the "
    "causal chain, e.g. 'cross-mated connector -> contact heating -> DC-arc risk'>\n"
    "   Systemic: <fleet spread: how many strings/assets, shared batch/crew/lot>\n"
    "   Decision: <who authorised what, via voice call if applicable>\n"
    "   Actions: <the remediation steps only, condensed and comma-separated on ONE "
    "line: isolate/LOTO, matched-brand connector swap + re-crimp, IR thermal scan, "
    "array/fleet crew audit. Do NOT mention crew dispatch, ETA, travel time, or any "
    "scheduling window/time.>\n"
    "   Warranty: <warranty/workmanship stance if present>\n"
    "Do NOT include any report or SOP URL in the body — the SOP PDF is attached "
    "separately. Plain professional English, no markdown, no bullet characters, one "
    "sentence per line, concise. Derive only from provided data; do NOT invent specifics."
)

# --- Schemas ----------------------------------------------------------------


class Input(BaseModel):
    """Compose+send request — the supervisor + voice outputs flattened 1:1."""

    case_id: str = Field(default="", description="FOREMAN case id (external key) — routing key for the live UI feed; map to the Maestro Case ID expression")

    # --- foreman-supervisor outputs (only the fields the email actually uses) ---
    case: dict = Field(default_factory=dict, description="supervisor.case {asset_id, site_id, worker_text, ...}")
    diagnosis: dict = Field(default_factory=dict, description="supervisor.diagnosis {root_cause, confidence, ...}")
    risk: dict = Field(default_factory=dict, description="supervisor.risk {band, score, ...}")
    invoked: list = Field(default_factory=list, description="supervisor.invoked[] (holds fleet_blast_radius result)")
    not_invoked: list = Field(default_factory=list, description="supervisor.not_invoked[] (holds warranty why)")
    action_plan: list = Field(default_factory=list, description="supervisor.action_plan[] {order, category, action}")
    summary: str = Field(default="", description="supervisor.summary (fallback email body)")
    report_url: str = Field(default="", description="supervisor.report_url — the SOP PDF to attach")

    # --- foreman-voice outputs (drag each from the voice node) ---
    spoken_opener: str = Field(default="", description="voice.spoken_opener")
    spoken_recommendation: str = Field(default="", description="voice.spoken_recommendation")
    transcript: list = Field(default_factory=list, description="voice.transcript[] (call turns)")
    decision: str = Field(default="", description="voice.decision (approved/hold/...)")
    call_sid: str = Field(default="", description="voice.call_sid")
    call_to: str = Field(default="", description="voice.to — the number called")
    call_from: str = Field(default="", description="voice.from_ — the calling number")
    recording_url: str = Field(default="", description="voice.recording_url — URL of the call recording (mp3) to download + attach")

    # --- email configuration ---
    decision_context: str = Field(default="", description="Override describing the human/voice decision")
    recipients: str = Field(default="", description="Comma-separated To addresses")
    cc: str = Field(default="", description="Optional comma-separated Cc addresses")
    media_blob_path: str = Field(default="", description="Video blob path in the bucket, e.g. MM....mp4")
    media_bucket: str = Field(default="foremenbucket", description="Storage Bucket name holding the video")
    media_folder: str = Field(default="Shared/foremen v1", description="Folder the bucket lives in")
    max_attachment_mb: int = Field(default=24, description="Skip any attachment larger than this (Gmail ~25MB)")
    dry_run: bool = Field(default=False, description="Compose + build attachments but DO NOT send")


class State(BaseModel):
    """Internal state flowing compose -> send (carried inputs + produced fields)."""

    case_id: str = ""
    # carried supervisor inputs
    case: dict = Field(default_factory=dict)
    diagnosis: dict = Field(default_factory=dict)
    risk: dict = Field(default_factory=dict)
    invoked: list = Field(default_factory=list)
    not_invoked: list = Field(default_factory=list)
    action_plan: list = Field(default_factory=list)
    summary: str = ""
    report_url: str = ""
    # carried voice inputs
    spoken_opener: str = ""
    spoken_recommendation: str = ""
    transcript: list = Field(default_factory=list)
    decision: str = ""
    call_sid: str = ""
    call_to: str = ""
    call_from: str = ""
    recording_url: str = ""
    # carried email config
    decision_context: str = ""
    recipients: str = ""
    cc: str = ""
    media_blob_path: str = ""
    media_bucket: str = "foremenbucket"
    media_folder: str = "Shared/foremen v1"
    max_attachment_mb: int = 24
    dry_run: bool = False
    # produced by compose
    subject: str = ""
    body: str = ""


class Output(BaseModel):
    """Output contract — strict JSON."""

    subject: str = ""
    body: str = ""
    attached: list[str] = Field(default_factory=list)  # filenames successfully attached
    sent: bool = False
    error: str = ""


# --- Credential helpers (env-first, then lazy UiPath Assets) ----------------


class _LazySDK:
    """Create the UiPath SDK only on first need (Asset read / bucket fetch)."""

    def __init__(self):
        self._sdk = None

    def get(self):
        if self._sdk is None:
            from uipath.platform import UiPath

            self._sdk = UiPath()
        return self._sdk


def _asset_value(sdk, asset_name: str) -> str:
    """Read an Asset's value, tolerating Text vs Credential asset shapes."""
    try:
        cred = sdk.assets.retrieve_credential(asset_name, folder_path=FOLDER)
        if cred:
            return str(cred).strip()
    except Exception:
        pass  # not a credential asset (or no access) — fall through to plain value
    asset = sdk.assets.retrieve(asset_name, folder_path=FOLDER)
    for attr in ("value", "string_value", "credential_password"):
        val = getattr(asset, attr, None)
        if val:
            return str(val).strip()
    return ""


def _secret(sdk_holder: _LazySDK, env_key: str) -> str:
    """env-first, then the matching UiPath Asset in folder "Shared"."""
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val.strip()
    try:
        return _asset_value(sdk_holder.get(), ASSET_MAP[env_key])
    except Exception:
        return ""


# --- Node 1: compose --------------------------------------------------------


def _supervisor_dict(s) -> dict:
    """Re-bundle the flattened supervisor fields into the nested shape the
    extractor expects (so the extraction logic stays shape-driven)."""
    return {
        "case": s.case,
        "diagnosis": s.diagnosis,
        "risk": s.risk,
        "invoked": s.invoked,
        "not_invoked": s.not_invoked,
        "action_plan": s.action_plan,
        "summary": s.summary,
        "report_url": s.report_url,
    }


def _voice_dict(s) -> dict:
    """Re-bundle the flattened voice fields into the shape the transcript builder
    and decision-resolver expect (``to``/``from_`` match the voice outputs)."""
    return {
        "spoken_opener": s.spoken_opener,
        "spoken_recommendation": s.spoken_recommendation,
        "transcript": s.transcript,
        "decision": s.decision,
        "call_sid": s.call_sid,
        "to": s.call_to,
        "from_": s.call_from,
    }


def _has_voice(s) -> bool:
    """True if any voice field is populated (so we should attach a transcript)."""
    return bool(
        s.transcript or s.spoken_opener or s.spoken_recommendation or s.call_sid or s.decision
    )


def _find_by_id(items, target_id):
    """Return the first list item whose ``id`` == target_id (or {} if none)."""
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict) and it.get("id") == target_id:
                return it
    return {}


def _extract(so: dict, voice: dict, decision_context: str, report_url: str) -> dict:
    """Pull every field the email needs out of the supervisor object, defensively."""
    case = so.get("case", {}) if isinstance(so, dict) else {}
    case = case if isinstance(case, dict) else {}
    diagnosis = so.get("diagnosis", {}) if isinstance(so, dict) else {}
    diagnosis = diagnosis if isinstance(diagnosis, dict) else {}
    risk = so.get("risk", {}) if isinstance(so, dict) else {}
    risk = risk if isinstance(risk, dict) else {}

    asset_id = case.get("asset_id", "") or ""
    fleet_item = _find_by_id(so.get("invoked", []), "fleet_blast_radius")
    fleet_result = fleet_item.get("result", {}) if isinstance(fleet_item, dict) else {}
    fleet = fleet_result if isinstance(fleet_result, dict) else {}
    warranty_item = _find_by_id(so.get("not_invoked", []), "warranty_entitlement")
    warranty_why = warranty_item.get("why", "") if isinstance(warranty_item, dict) else ""

    return {
        "case_id": asset_id,
        "asset_id": asset_id,
        "site_id": case.get("site_id", "") or "",
        "worker_text": case.get("worker_text", "") or "",
        "root_cause": diagnosis.get("root_cause", "") or "",
        "confidence": diagnosis.get("confidence", "") if diagnosis.get("confidence") is not None else "",
        "risk_band": risk.get("band", "") or "",
        "risk_score": risk.get("score", "") if risk.get("score") is not None else "",
        "fleet": fleet,
        "action_plan": so.get("action_plan", []) if isinstance(so.get("action_plan"), list) else [],
        "summary": so.get("summary", "") or "",
        "warranty": warranty_why or "",
        "rep_url": (report_url or so.get("report_url", "") or "").strip(),
        "decision": (decision_context or (voice.get("decision", "") if isinstance(voice, dict) else "") or "").strip(),
    }


def _user_block(f: dict) -> str:
    """A compact text block of the extracted fields for the LLM to compose from."""
    fleet = f.get("fleet") or {}
    affected_count = fleet.get("affected_count", "")
    affected_assets = fleet.get("affected_assets", "")
    crit = fleet.get("criticality_rank", "")
    # drop logistics steps the email must NOT mention (crew dispatch/ETA, scheduling)
    _skip_categories = {"CREW", "WINDOW", "DISPATCH", "SCHEDULE"}
    plan_lines = []
    for step in f.get("action_plan") or []:
        if isinstance(step, dict):
            if str(step.get("category", "")).upper() in _skip_categories:
                continue
            plan_lines.append(f"  {step.get('order', '')}) {step.get('category', '')}: {step.get('action', '')}")
    plan = "\n".join(plan_lines)
    return (
        f"case_id: {f['case_id']}\n"
        f"asset_id: {f['asset_id']}\n"
        f"site_id: {f['site_id']}\n"
        f"worker_text: {f['worker_text']}\n"
        f"root_cause: {f['root_cause']}\n"
        f"confidence: {f['confidence']}\n"
        f"risk_band: {f['risk_band']}\n"
        f"risk_score: {f['risk_score']}\n"
        f"fleet_affected_count: {affected_count}\n"
        f"fleet_affected_assets: {affected_assets}\n"
        f"fleet_criticality_rank: {crit}\n"
        f"warranty: {f['warranty']}\n"
        f"decision: {f['decision']}\n"
        f"action_plan:\n{plan}\n\n"
        f"summary: {f['summary']}"
    )


def _parse_compose(raw: str) -> tuple[str, str]:
    """Parse the LLM reply into (subject, body). Tolerates ```json fences."""
    text = (raw or "").strip()
    if text.startswith("```"):
        # strip a leading ``` / ```json fence and a trailing ```
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    data = json.loads(text)
    subject = str(data.get("subject", "")).strip()
    body = str(data.get("body", "")).strip()
    return subject, body


async def _compose_impl(state: State) -> dict:
    """Extract fields, ask the fast LLM for {subject, body}, fall back on failure."""
    f = _extract(_supervisor_dict(state), _voice_dict(state), state.decision_context, state.report_url)
    summary = f["summary"]
    case_id = f["case_id"]

    # default fallback (used if the LLM call or JSON parse fails)
    subject = f"Incident {case_id}: case summary"
    body = summary

    try:
        llm = UiPathChat(model=LLM_MODEL, temperature=0)
        out = await llm.ainvoke([SystemMessage(COMPOSE_SYSTEM), HumanMessage(_user_block(f))])
        parsed_subject, parsed_body = _parse_compose(getattr(out, "content", "") or "")
        if parsed_subject:
            subject = parsed_subject
        if parsed_body:
            body = parsed_body
    except Exception:
        pass  # keep the deterministic fallback — never throw

    return {"subject": subject, "body": body}


async def compose(state: State) -> dict:
    """Safety net around ``_compose_impl`` — this node can NEVER throw, so a
    compose failure never fails the flow (falls back to a plain subject + summary)."""
    try:
        return await _compose_impl(state)
    except Exception:
        case = state.case if isinstance(state.case, dict) else {}
        case_id = case.get("asset_id", "") or ""
        return {"subject": f"Incident {case_id}: case summary", "body": state.summary or ""}


# --- Node 2: send -----------------------------------------------------------


# Labeled sections the LLM emits, each with an accent colour for the HTML render.
_SECTIONS = [
    ("Report", "#5a6b7b"),       # slate  — what happened / who flagged
    ("Root cause", "#c0392b"),   # red    — the hazard
    ("Systemic", "#b9770e"),     # amber  — fleet spread
    ("Decision", "#1e8449"),     # green  — who authorised
    ("Actions", "#0b5394"),      # blue   — the plan
    ("Warranty", "#6c5ce7"),     # purple — workmanship stance
]


def _render_html(body: str) -> str:
    """Render the labeled plain-text body as a clean, inline-styled HTML email.

    Parses 'Label: value' lines into accented section cards; the Actions value is
    split on ';' into a bulleted list. Never throws — on any parse trouble it falls
    back to the body wrapped in a <pre> block.
    """
    try:
        labels = {lbl.lower(): (lbl, color) for lbl, color in _SECTIONS}
        intro = ""
        sections: list[tuple[str, str, str]] = []  # (label, color, value)
        for raw in (body or "").split("\n"):
            s = raw.strip()
            if not s or s.lower().startswith("full sop"):
                continue
            hit = None
            for low, (lbl, color) in labels.items():
                if s.lower().startswith(low + ":"):
                    hit = (lbl, color, s[len(lbl) + 1:].strip())
                    break
            if hit:
                sections.append(hit)
            elif not intro:
                intro = s
            elif sections:  # stray continuation -> fold into the last section
                lbl, color, val = sections[-1]
                sections[-1] = (lbl, color, (val + " " + s).strip())

        parts = [
            '<div style="font-family:Arial,Helvetica,sans-serif;color:#1a1a1a;'
            'max-width:660px;line-height:1.5;">'
        ]
        if intro:
            parts.append(
                f'<p style="font-size:15px;margin:0 0 18px;color:#333;">{_html.escape(intro)}</p>'
            )
        for lbl, color, val in sections:
            label_html = (
                f'<div style="font-weight:700;color:{color};font-size:11px;'
                'text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px;">'
                f'{_html.escape(lbl)}</div>'
            )
            value_html = f'<div style="font-size:14px;">{_html.escape(val)}</div>'
            parts.append(
                f'<div style="border-left:3px solid {color};background:#f6f8fa;'
                f'padding:8px 14px;margin:0 0 10px;border-radius:3px;">{label_html}{value_html}</div>'
            )
        parts.append(
            '<hr style="border:none;border-top:1px solid #e3e8ee;margin:18px 0 10px;">'
            '<p style="font-size:12px;color:#8a94a0;margin:0;">Generated by FOREMAN. '
            'The SOP, call transcript, and on-site video are attached.</p>'
            "</div>"
        )
        return "".join(parts)
    except Exception:
        return f"<pre style='font-family:Arial,sans-serif;font-size:14px;'>{_html.escape(body or '')}</pre>"


def _basename_from_url(url: str, default: str) -> str:
    """Basename of a URL path with the query string stripped (or ``default``)."""
    try:
        path = urlparse(url).path
        name = os.path.basename(path)
        return name or default
    except Exception:
        return default


def _build_transcript(voice: dict) -> str:
    """Build the plain-text call transcript from the voice result (never throws)."""
    v = voice if isinstance(voice, dict) else {}
    lines = [
        "FOREMAN call transcript",
        "=======================",
        f"call_sid : {v.get('call_sid', '')}",
        f"from     : {v.get('from_', '')}",
        f"to       : {v.get('to', '')}",
        f"decision : {v.get('decision', '')}",
        "",
    ]
    opener = (v.get("spoken_opener", "") or "").strip()
    rec = (v.get("spoken_recommendation", "") or "").strip()
    if opener:
        lines += ["FOREMAN (opener): " + opener, ""]
    if rec:
        lines += ["FOREMAN (recommendation): " + rec, ""]
    convo = v.get("transcript", [])
    if isinstance(convo, list) and convo:
        lines.append("Conversation:")
        for turn in convo:
            lines.append("  " + str(turn))
    return "\n".join(lines) + "\n"


def _attach_bytes(msg: MIMEMultipart, data: bytes, maintype: str, subtype: str, filename: str) -> None:
    """Attach raw bytes as a base64-encoded MIME part with a download filename."""
    part = MIMEBase(maintype, subtype)
    part.set_payload(data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)


async def _send_impl(state: State) -> Output:
    """Assemble the attachments and send the email (or compose-only for dry_run)."""
    out = Output(subject=state.subject, body=state.body)
    notes: list[str] = []
    limit = max(1, int(state.max_attachment_mb)) * 1024 * 1024
    rep_url = (state.report_url or "").strip()

    # base message — the body part first, attachments appended below.
    # UTF-8 everywhere so em-dashes / non-ASCII in the subject or body don't
    # break msg.as_string() at send time.
    msg = MIMEMultipart()
    msg["Subject"] = Header(state.subject or "", "utf-8")
    # multipart/alternative: plain-text fallback + styled HTML (clients show HTML)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(state.body or "", "plain", "utf-8"))
    alt.attach(MIMEText(_render_html(state.body or ""), "html", "utf-8"))
    msg.attach(alt)

    sdk_holder = _LazySDK()

    # (a) SOP PDF — fetched from rep_url ------------------------------------
    if rep_url:
        try:
            import httpx

            resp = httpx.get(rep_url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            data = resp.content
            fname = _basename_from_url(rep_url, "report.pdf")
            if len(data) > limit:
                notes.append(f"PDF {len(data) // (1024 * 1024)}MB exceeds {state.max_attachment_mb}MB limit, skipped")
            else:
                _attach_bytes(msg, data, "application", "pdf", fname)
                out.attached.append(fname)
        except Exception as exc:
            notes.append(f"PDF fetch failed ({type(exc).__name__}), skipped")

    # (b) CALL TRANSCRIPT — built in-memory, written to a temp file --------
    if _has_voice(state):
        try:
            text = _build_transcript(_voice_dict(state))
            tmp_dir = tempfile.mkdtemp(prefix="foreman-email-")
            tpath = os.path.join(tmp_dir, "call-transcript.txt")
            with open(tpath, "w", encoding="utf-8") as fh:
                fh.write(text)
            data = text.encode("utf-8")
            if len(data) > limit:
                notes.append(f"transcript exceeds {state.max_attachment_mb}MB limit, skipped")
            else:
                _attach_bytes(msg, data, "text", "plain", "call-transcript.txt")
                out.attached.append("call-transcript.txt")
        except Exception as exc:
            notes.append(f"transcript build failed ({type(exc).__name__}), skipped")

    # (c) VIDEO — fetched from the Storage Bucket --------------------------
    if state.media_blob_path and state.media_bucket:
        vpath = None
        try:
            sdk = sdk_holder.get()
            vname = os.path.basename(state.media_blob_path) or "video.mp4"
            tmp_dir = tempfile.mkdtemp(prefix="foreman-email-vid-")
            vpath = os.path.join(tmp_dir, vname)
            await sdk.buckets.download_async(
                name=state.media_bucket,
                blob_file_path=state.media_blob_path,
                destination_path=vpath,
                folder_path=state.media_folder or None,
            )
            size = os.path.getsize(vpath)
            if size > limit:
                notes.append(f"video {size // (1024 * 1024)}MB exceeds {state.max_attachment_mb}MB limit, skipped")
            else:
                with open(vpath, "rb") as fh:
                    _attach_bytes(msg, fh.read(), "video", "mp4", vname)
                out.attached.append(vname)
        except Exception as exc:
            notes.append(f"video fetch failed ({type(exc).__name__}), skipped")

    # (d) CALL RECORDING — fetched from the voice agent's recording_url ------
    rec_url = (state.recording_url or "").strip()
    if rec_url:
        try:
            import httpx

            resp = httpx.get(rec_url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            data = resp.content
            if not data:
                notes.append("recording empty, skipped")
            elif len(data) > limit:
                notes.append(f"recording {len(data) // (1024 * 1024)}MB exceeds {state.max_attachment_mb}MB limit, skipped")
            else:
                _attach_bytes(msg, data, "audio", "mpeg", "call-recording.mp3")
                out.attached.append("call-recording.mp3")
        except Exception as exc:
            notes.append(f"recording fetch failed ({type(exc).__name__}), skipped")

    # dry_run: everything composed + assembled, but nothing is sent ---------
    if state.dry_run:
        out.sent = False
        out.error = "; ".join(notes)
        return out

    # --- SEND via Gmail SMTP ----------------------------------------------
    try:
        gmail_user = _secret(sdk_holder, "GMAIL_USER")
        gmail_pass = _secret(sdk_holder, "GMAIL_APP_PASSWORD")
        to_list = [a.strip() for a in (state.recipients or "").split(",") if a.strip()]
        cc_list = [a.strip() for a in (state.cc or "").split(",") if a.strip()]

        if not (gmail_user and gmail_pass):
            notes.append("missing Gmail credentials (Gmail-User / Gmail-App-Password)")
            out.error = "; ".join(notes)
            return out
        if not to_list:
            notes.append("no recipients")
            out.error = "; ".join(notes)
            return out

        msg["From"] = gmail_user
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
            smtp.starttls()
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, to_list + cc_list, msg.as_string())

        out.sent = True
        out.error = "; ".join(notes)
        return out
    except Exception as exc:  # never throw out of the node
        notes.append(f"send failed: {type(exc).__name__}: {exc}")
        out.sent = False
        out.error = "; ".join(notes)
        return out


# --- FOREMAN UI live feed (additive; never raises into the send) -------------
def _emit_audit(state, out) -> None:
    """Close stage on the UI: the audit email (subject/body/attachments) + case closed."""
    try:
        from foreman_events import emit
        cid = (getattr(state, "case_id", "") or "").strip()
        if not cid:
            return
        emit(cid, {"kind": "stage.entered", "stage": "close"})
        emit(cid, {"kind": "audit.ready", "audit": {
            "email": {
                "to": (state.recipients or "").strip(),
                "subject": out.subject or "",
                "body": out.body or "",
            },
            "attachments": list(out.attached or []),
        }})
        emit(cid, {"kind": "case.closed"})
    except Exception as e:  # noqa: BLE001 - telemetry must never break the send
        print(f"[foreman-email] ui emit skipped: {e}")


async def send(state: State) -> Output:
    """Safety net around ``_send_impl`` — this node can NEVER throw. A bad PDF /
    video / transcript is already skipped inside; this outer guard also catches any
    unexpected failure (SDK init, temp files, message assembly, SMTP) so the flow
    still completes with ``sent=False`` and the reason in ``error`` instead of
    crashing the run."""
    try:
        out = await _send_impl(state)
    except Exception as exc:
        out = Output(
            subject=state.subject,
            body=state.body,
            attached=[],
            sent=False,
            error=f"send aborted: {type(exc).__name__}: {exc}",
        )
    _emit_audit(state, out)  # FOREMAN UI: close stage — audit email + case closed
    return out


# --- Graph ------------------------------------------------------------------

builder = StateGraph(State, input=Input, output=Output)
builder.add_node("compose", compose)
builder.add_node("send", send)
builder.add_edge(START, "compose")
builder.add_edge("compose", "send")
builder.add_edge("send", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
