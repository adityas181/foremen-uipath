"""FOREMAN Voice agent (the spoken-approval caller).

This coded agent places a TWO-WAY outbound Twilio VOICE call to a site manager,
reads them a short spoken opener about a maintenance case, asks for a verbal
approval of a recommended action, and returns the manager's decision. A FAST LLM
(UiPathChat gpt-4.1-mini) both (a) compresses the case ``summary`` into the spoken
opener and (b) DERIVES the recommendation to authorise from that same summary — the
recommendation is no longer an input.

CONTRACT
  input : { to_number, summary, to_role, site_id, title, message_override,
            voice, wait_for_decision, timeout_sec, from_number,
            language, case_id, dry_run }
  output: { placed, two_way, call_sid, status, spoken_opener,
            spoken_recommendation, decision, to, from_, transcript, error }

TWO NODES
  1. ``make_brief`` — two fast-LLM calls over ``summary``:
       * ``spoken_opener``         — ONE/TWO short sentences (or ``message_override``
         verbatim if set). Falls back to the first ~300 chars of the summary.
       * ``spoken_recommendation`` — ONE short imperative sentence stating the action
         to authorise. Falls back to a generic "proceed with the recommended fix".
     Never throws.
  2. ``place_call`` — place the call and return the decision:
       * TWO-WAY (a webhook is configured): POST the opener + derived recommendation
         to ``{webhook}/prepare``, ring the manager with TwiML served by
         ``{webhook}/voice``, then (if ``wait_for_decision``) poll
         ``{webhook}/decision`` until approved / hold (or times out -> no_answer).
       * ONE-WAY fallback (no webhook): <Say> the opener + recommendation, hang up.
       * ``dry_run``: place NO call, return the opener + recommendation only.

``voice`` selects the Twilio voice used by the ``<Say>`` verb (e.g. "alice",
"man", "woman", or a Polly voice like "Polly.Aditi").

CREDENTIALS are read env-first, then lazily from UiPath Assets in folder
"Shared" — so a local ``.env`` run needs no UiPath connection at all:
  TWILIO_ACCOUNT_SID | Twilio-Account-Sid
  TWILIO_AUTH_TOKEN  | Twilio-Auth-Token
  TWILIO_FROM_NUMBER | Twilio-From-Number   (the VOICE number)
  VOICE_WEBHOOK_URL  | Voice-Webhook-Url    (the public voice_server URL)

Like the rest of the FOREMAN fleet, ``place_call`` NEVER throws — on any failure
it returns the output contract with a non-empty ``error``.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape, quoteattr

import truststore  # corporate TLS proxies — inject the OS trust store into SSL
truststore.inject_into_ssl()

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath_langchain.chat import UiPathChat

# --- Configuration ----------------------------------------------------------

FOLDER = "Shared"                       # folder the Twilio Assets live in
LLM_MODEL = "gpt-4.1-mini-2025-04-14"   # fast model used to compress + derive
BRIEF_FALLBACK_CHARS = 300              # chars of summary used if the LLM is unavailable
POLL_INTERVAL_SEC = 2                   # how often we poll the webhook for a decision
SPEECH_RATE = "90%"                     # speak a little slower (SSML; Polly voices only)

# env var  ->  UiPath Asset name (folder "Shared")
ASSET_MAP = {
    "TWILIO_ACCOUNT_SID": "Twilio-Account-Sid",
    "TWILIO_AUTH_TOKEN": "Twilio-Auth-Token",
    "TWILIO_FROM_NUMBER": "Twilio-From-Number",
    "VOICE_WEBHOOK_URL": "Voice-Webhook-Url",
}

OPENER_SYSTEM = (
    "You are FOREMAN. Compress the maintenance case summary into ONE or TWO short spoken "
    "sentences to OPEN a phone call to a site manager. ALWAYS begin with "
    "'This is FOREMAN about <id>'. Use the provided Asset id as <id>; if no Asset id is "
    "provided, use the asset id found in the summary, else the provided Site id. NEVER "
    "invent or guess an id. Then state the core hazard with its key number, and if the "
    "summary mentions sibling assets or a shared crew/lot, add the fleet exposure. Plain "
    "spoken English, no markdown, no lists, under 45 words. The following shows STYLE ONLY "
    "(do not reuse its ids or numbers): 'This is FOREMAN about <id> — a melted MC4 "
    "connector with an 82-degree hot-spot, a DC-arc risk; the same install crew and "
    "connector lot put three sibling strings at risk.'"
)

REC_SYSTEM = (
    "From this maintenance case summary, state the action to AUTHORISE in ONE short "
    "spoken sentence for a phone call. Imperative, plain spoken English, no markdown, "
    "no lists, under 35 words. Example: 'I recommend isolating the affected string "
    "under lockout, replacing both connector halves with genuine parts, and a fleet "
    "audit of the three sibling assets.'"
)

REC_FALLBACK = "I recommend we proceed with the recommended fix now and log the action."

# --- Schemas ----------------------------------------------------------------


class Input(BaseModel):
    """Call request from the supervisor / dispatcher."""

    to_number: str = Field(default="", description="Callee E.164, verified on Twilio trial")
    summary: str = Field(default="", description="Full case summary (long) -> LLM compresses + derives")
    to_role: str = Field(default="the manager", description="Who is being called, for context")
    asset_id: str = Field(default="", description="Asset id to lead the opener with, e.g. AST-SCB-DEL-0788")
    site_id: str = Field(default="", description="Site id (fallback id for the opener), for context")
    title: str = Field(default="Voice escalation", description="Subject of the call, for context")
    message_override: str = Field(default="", description="If set, speak this opener verbatim and SKIP the opener LLM")
    voice: str = Field(default="alice", description="Twilio <Say> voice (alice/man/woman or Polly.*)")
    wait_for_decision: bool = True
    timeout_sec: int = 75
    from_number: str = Field(default="", description="Twilio VOICE number (NOT the WhatsApp sandbox)")
    language: str = "en-IN"
    case_id: str = ""
    dry_run: bool = False


class State(BaseModel):
    """Internal state flowing make_brief -> place_call (inputs + produced fields)."""

    # carried inputs
    to_number: str = ""
    summary: str = ""
    to_role: str = "the manager"
    asset_id: str = ""
    site_id: str = ""
    title: str = "Voice escalation"
    message_override: str = ""
    voice: str = "alice"
    wait_for_decision: bool = True
    timeout_sec: int = 75
    from_number: str = ""
    language: str = "en-IN"
    case_id: str = ""
    dry_run: bool = False
    # produced
    spoken_opener: str = ""
    spoken_recommendation: str = ""


class Output(BaseModel):
    """Output contract — strict JSON."""

    placed: bool = False
    two_way: bool = False
    call_sid: str = ""
    status: str = ""
    spoken_opener: str = ""           # the LLM-compressed opener actually used
    spoken_recommendation: str = ""   # the recommendation DERIVED from the summary
    decision: str = "pending"         # approved / hold / no_answer / pending
    to: str = ""
    from_: str = ""
    transcript: list[str] = Field(default_factory=list)  # what each side said (two-way)
    recording_url: str = ""  # URL of the call recording (mp3) — for the email agent to attach
    webhook_url: str = ""    # the voice_server URL actually used (env VOICE_WEBHOOK_URL or Voice-Webhook-Url asset)
    error: str = ""


# --- Credential helpers (env-first, then lazy UiPath Assets) ----------------


class _LazySDK:
    """Create the UiPath SDK only on first Asset read, so local .env runs need none."""

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


def _clean_url(raw: str) -> str:
    """Sanitise a URL read from an asset/env so a stray char can't break DNS.

    str.strip() does NOT remove zero-width / BOM characters (\u200b, \ufeff ...)
    that copy-paste injects into an Orchestrator asset value; they stay invisible in
    the UI but make the hostname unresolvable ([Errno -2] Name or service not known).
    A URL has no internal whitespace, so drop ALL whitespace, zero-width, control
    chars and wrapping quotes.
    """
    s = str(raw or "").strip().strip('"').strip("'")
    s = re.sub(r"[\s\u200b\u200c\u200d\u2060\ufeff\x00-\x1f\x7f]+", "", s)
    return s


def _log(msg: str) -> None:
    """Emit a line visible in the UiPath job logs / traces (stdout, flushed)."""
    print(f"[foreman-voice] {msg}", flush=True)


# --- Node 1: make_brief -----------------------------------------------------


async def _llm_one_line(system_prompt: str, user_content: str) -> str:
    """Single fast-LLM call returning one cleaned line (raises on failure)."""
    llm = UiPathChat(model=LLM_MODEL, temperature=0)
    out = await llm.ainvoke([SystemMessage(system_prompt), HumanMessage(user_content)])
    return (getattr(out, "content", "") or "").strip().strip('"')


def _fallback_opener(summary: str, asset_id: str, site_id: str) -> str:
    """A clean opener used only when the LLM is unavailable.

    Keeps ONLY the hazard/diagnosis part of the summary (everything before the
    recommendation/plan) so the recommendation never leaks into the opener, and
    leads with the asset id (else site id) so it still sounds like a FOREMAN call.
    """
    head = summary
    for marker in ("Recommended fix", "Recommended Fix", "Recommendation", "Plan:", "Plan :"):
        idx = head.find(marker)
        if idx > 0:
            head = head[:idx]
            break
    head = head.strip().strip(".").strip()[:BRIEF_FALLBACK_CHARS].strip()
    lead_id = asset_id or site_id
    prefix = f"This is FOREMAN about {lead_id}. " if lead_id else "This is FOREMAN. "
    return (prefix + head).strip()


async def _safe_opener(summary: str, asset_id: str, site_id: str) -> str:
    """LLM-compress the summary into the opener; fall back to a clean hazard-only line."""
    ctx = []
    if asset_id:
        ctx.append(f"Asset id (use this as the id): {asset_id}")
    if site_id:
        ctx.append(f"Site id (fallback if no asset id): {site_id}")
    user = (("\n".join(ctx) + "\n\nCase summary:\n") if ctx else "") + summary
    try:
        return await _llm_one_line(OPENER_SYSTEM, user) or _fallback_opener(summary, asset_id, site_id)
    except Exception:
        return _fallback_opener(summary, asset_id, site_id)


async def _safe_rec(summary: str) -> str:
    """Derive the recommendation from the summary; fall back to a generic line."""
    try:
        return await _llm_one_line(REC_SYSTEM, summary) or REC_FALLBACK
    except Exception:
        return REC_FALLBACK


async def make_brief(state: State) -> dict:
    """Produce the spoken opener AND derive the recommendation from the summary.

    The opener and recommendation LLM calls run CONCURRENTLY (asyncio.gather) so they
    are produced together rather than one-after-the-other (~half the latency).
    """
    summary = (state.summary or "").strip()
    override = (state.message_override or "").strip()
    asset_id = (state.asset_id or "").strip()
    site_id = (state.site_id or "").strip()

    if override and summary:
        # opener is verbatim; only the recommendation needs the LLM.
        spoken_opener = override
        spoken_recommendation = await _safe_rec(summary)
    elif override:
        spoken_opener = override
        spoken_recommendation = REC_FALLBACK
    elif summary:
        spoken_opener, spoken_recommendation = await asyncio.gather(
            _safe_opener(summary, asset_id, site_id), _safe_rec(summary)
        )
    else:
        spoken_opener, spoken_recommendation = "", REC_FALLBACK

    return {
        "spoken_opener": spoken_opener,
        "spoken_recommendation": spoken_recommendation,
    }


# --- Node 2: place_call -----------------------------------------------------


def _say(text: str, voice: str, language: str) -> str:
    """One <Say> verb with the chosen Twilio voice + language (attrs/text escaped)."""
    inner = xml_escape(text or "")
    if SPEECH_RATE and SPEECH_RATE != "100%":
        inner = f"<prosody rate={quoteattr(SPEECH_RATE)}>{inner}</prosody>"
    return (
        f"<Say voice={quoteattr(voice or 'alice')} "
        f"language={quoteattr(language or 'en-IN')}>{inner}</Say>"
    )


def _twiml_one_way(opener: str, recommendation: str, voice: str, language: str) -> str:
    """One-shot TwiML: speak the opener, then the recommendation, then hang up."""
    body = _say(opener, voice, language)
    if recommendation:
        body += "<Pause length=\"1\"/>" + _say(recommendation, voice, language)
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}<Hangup/></Response>'


async def _prepare_webhook(base: str, payload: dict) -> None:
    """POST the opener + derived recommendation to {webhook}/prepare (stored by token)."""
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{base}/prepare", json=payload)
        resp.raise_for_status()


async def _poll_decision(base: str, token: str, timeout_sec: int):
    """Poll {webhook}/decision until 'decided' or timeout.

    Returns (decision, transcript). On timeout -> ("no_answer", last transcript seen).
    """
    import httpx

    deadline_iters = max(1, int(timeout_sec / POLL_INTERVAL_SEC))
    transcript: list[str] = []
    async with httpx.AsyncClient(timeout=15) as client:
        for _ in range(deadline_iters):
            await asyncio.sleep(POLL_INTERVAL_SEC)
            try:
                resp = await client.get(f"{base}/decision", params={"token": token})
                data = resp.json()
            except Exception:
                continue  # transient — keep polling until the deadline
            transcript = data.get("transcript") or transcript
            if data.get("status") == "decided":
                return data.get("decision") or "hold", transcript
    return "no_answer", transcript


# --- FOREMAN UI live feed (additive; never raises into the call) -------------
def _emit_call_start(state) -> None:
    """Show the call going live + FOREMAN's spoken brief on the UI Calls tab."""
    try:
        from foreman_events import emit
        cid = (getattr(state, "case_id", "") or "").strip()
        if not cid:
            return
        emit(cid, {"kind": "stage.entered", "stage": "escalate"})
        emit(cid, {"kind": "call.started", "to": state.to_number or "",
                   "toRole": state.to_role or "Site Manager"})
        emit(cid, {"kind": "call.connected"})
        for line in (state.spoken_opener, state.spoken_recommendation):
            if (line or "").strip():
                emit(cid, {"kind": "call.line", "line": {"speaker": "foreman", "text": line.strip()}})
    except Exception as e:  # noqa: BLE001 - telemetry must never break the call
        print(f"[foreman-voice] ui emit (start) skipped: {e}")


def _emit_call_result(state, decision: str, transcript) -> None:
    """Show the manager's replies + the final decision on the UI Calls tab."""
    try:
        import time
        from foreman_events import emit
        cid = (getattr(state, "case_id", "") or "").strip()
        if not cid:
            return
        for raw in (transcript or []):
            txt = str(raw)
            if ":" in txt:                      # strip "manager:" / "decision-answer:" prefixes
                txt = txt.split(":", 1)[1]
            txt = txt.strip()
            if txt:
                emit(cid, {"kind": "call.line", "line": {"speaker": "manager", "text": txt}})
        approved = (decision == "approved")
        emit(cid, {"kind": "call.decision", "decision": {
            "authorized": approved,
            "actions": [state.spoken_recommendation] if (approved and (state.spoken_recommendation or "").strip()) else [],
            "by": state.to_role or "Site Manager",
            "at": time.strftime("%H:%M"),
        }})
    except Exception as e:  # noqa: BLE001
        print(f"[foreman-voice] ui emit (result) skipped: {e}")


async def place_call(state: State) -> Output:
    """Place the two-way call (or one-way fallback / dry_run) and return the decision."""
    spoken_opener = (state.spoken_opener or "").strip()
    spoken_recommendation = (state.spoken_recommendation or "").strip()
    to_number = (state.to_number or "").strip()
    language = (state.language or "en-IN").strip() or "en-IN"
    voice = (state.voice or "alice").strip() or "alice"
    base_out = Output(
        spoken_opener=spoken_opener,
        spoken_recommendation=spoken_recommendation,
        to=to_number,
    )

    sdk_holder = _LazySDK()
    from_number = (state.from_number or "").strip() or _secret(sdk_holder, "TWILIO_FROM_NUMBER")
    # voice_server URL resolves from env VOICE_WEBHOOK_URL or the Voice-Webhook-Url
    # asset (no longer an agent input — update the asset, never redeploy).
    webhook = _clean_url(_secret(sdk_holder, "VOICE_WEBHOOK_URL")).rstrip("/")
    base_out.from_ = from_number
    base_out.webhook_url = webhook   # surface the resolved URL as output
    two_way = bool(webhook)
    base_out.two_way = two_way
    _log(f"resolved webhook={webhook!r} (two_way={two_way}) from={from_number!r} to={to_number!r}")

    # dry_run: no call placed, just hand back the opener + derived recommendation.
    if state.dry_run:
        base_out.status = "dry_run"
        _log("dry_run=true -> no call placed")
        return base_out

    if not to_number:
        base_out.error = "to_number is required"
        return base_out

    try:
        account_sid = _secret(sdk_holder, "TWILIO_ACCOUNT_SID")
        auth_token = _secret(sdk_holder, "TWILIO_AUTH_TOKEN")
        if not (account_sid and auth_token and from_number):
            base_out.error = "missing Twilio credentials (account sid / auth token / from number)"
            return base_out

        from twilio.rest import Client

        client = Client(account_sid, auth_token)

        # Resolve the public view-backend URL once (from the same asset foreman_events
        # uses) — drives BOTH the recording callback (live UI) and the recording_url
        # output the email agent attaches.
        try:
            from foreman_events import _resolve
            _backend = (_resolve()[0] or "").rstrip("/")
        except Exception:  # noqa: BLE001
            _backend = ""

        # Phase 2 (option b): ask Twilio to POST our view-backend the moment the
        # recording is ready (reliable timing, no agent wait); the backend proxies
        # the audio + broadcasts call.recording.
        rec_cb_kwargs: dict = {}
        if _backend and (state.case_id or "").strip():
            from urllib.parse import quote
            rec_cb_kwargs = {
                "recording_status_callback": f"{_backend}/twilio/recording?case_id={quote(state.case_id, safe='')}",
                "recording_status_callback_event": ["completed"],
                "recording_status_callback_method": "POST",
            }

        if two_way:
            # --- TWO-WAY: webhook drives the live conversation ---------------
            token = (state.case_id or "").strip() or uuid.uuid4().hex
            _log(f"two-way: POST {webhook}/prepare token={token!r}")
            await _prepare_webhook(
                webhook,
                {
                    "token": token,
                    "message": spoken_opener,
                    "recommendation": spoken_recommendation,   # DERIVED, not input
                    "case_id": state.case_id or "",
                    "title": state.title or "",
                    "to_role": state.to_role or "",
                    "site_id": state.site_id or "",
                    "voice": voice,
                    "language": language,
                },
            )
            # URL-encode the token: a case_id like "whatsapp:+91..." contains '+'/':'
            # which a query string would otherwise mangle ('+' -> space) and break the
            # voice_server SESSIONS lookup ("this call is not configured").
            voice_url = f"{webhook}/voice?token={quote(token, safe='')}"
            _log(f"two-way: calls.create to={to_number!r} url={voice_url!r}")
            call = await asyncio.to_thread(
                client.calls.create, to=to_number, from_=from_number, url=voice_url,
                record=True, **rec_cb_kwargs,
            )
            base_out.placed = True
            base_out.call_sid = getattr(call, "sid", "") or ""
            base_out.status = getattr(call, "status", "") or "initiated"
            _log(f"two-way: placed sid={base_out.call_sid!r} status={base_out.status!r}")
            _emit_call_start(state)  # FOREMAN UI: call live + FOREMAN's spoken brief

            if state.wait_for_decision:
                base_out.decision, base_out.transcript = await _poll_decision(
                    webhook, token, state.timeout_sec
                )
            else:
                base_out.decision = "pending"
            _log(f"two-way: decision={base_out.decision!r} transcript_lines={len(base_out.transcript)}")
            _emit_call_result(state, base_out.decision, base_out.transcript)  # FOREMAN UI: replies + decision
            # Recording → backend via Twilio recordingStatusCallback (no agent wait).
            # A stable, lazy URL the email agent can download (backend resolves the
            # recording by call sid on fetch — ready by the time the email stage runs).
            if _backend and base_out.call_sid:
                base_out.recording_url = f"{_backend}/recording/call/{account_sid}/{base_out.call_sid}"
            return base_out

        # --- ONE-WAY fallback: speak the opener + recommendation, hang up ---
        if not spoken_opener and not spoken_recommendation:
            base_out.error = "nothing to deliver and no webhook configured"
            _log("one-way: nothing to deliver -> aborting")
            return base_out
        _log(f"one-way: calls.create to={to_number!r} (no webhook configured)")
        call = await asyncio.to_thread(
            client.calls.create,
            to=to_number,
            from_=from_number,
            twiml=_twiml_one_way(spoken_opener, spoken_recommendation, voice, language),
            record=True, **rec_cb_kwargs,
        )
        base_out.placed = True
        base_out.call_sid = getattr(call, "sid", "") or ""
        base_out.status = getattr(call, "status", "") or "initiated"
        base_out.decision = "pending"   # one-way call collects no decision
        _log(f"one-way: placed sid={base_out.call_sid!r} status={base_out.status!r}")
        _emit_call_start(state)  # FOREMAN UI: one-way call + FOREMAN's spoken brief
        # Recording → backend via Twilio recordingStatusCallback (no agent wait).
        if _backend and base_out.call_sid:
            base_out.recording_url = f"{_backend}/recording/call/{account_sid}/{base_out.call_sid}"
        return base_out

    except Exception as exc:  # never throw out of the node
        # Include the resolved webhook (repr shows any hidden/stray char) so a DNS
        # failure points straight at the URL it actually dialed.
        detail = f" | webhook={webhook!r}" if webhook else ""
        base_out.error = f"{type(exc).__name__}: {exc}{detail}"
        _log(f"ERROR: {base_out.error}")
        return base_out


# --- Graph ------------------------------------------------------------------

builder = StateGraph(State, input=Input, output=Output)
builder.add_node("make_brief", make_brief)
builder.add_node("place_call", place_call)
builder.add_edge(START, "make_brief")
builder.add_edge("make_brief", "place_call")
builder.add_edge("place_call", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
