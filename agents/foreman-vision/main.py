"""UiPath LangGraph coded agent — generic field-fault Vision agent.

Pipeline (single graph node):
  1. Read this asset's history from the Data Fabric entity `AssetIssueHistory`
     FIRST — it both feeds the match step and supplies the canonical
     fault/component vocabulary used to constrain the vision prompt (so the
     model's wording aligns with history and matching actually hits). Never
     crashes — on any error history is empty and `history_ok` is False.
  2. Download `mediaPath` from the UiPath Storage Bucket `foremenbucket`
     (folder `Shared/foremen v1`) into bytes, then send to Google Gemini
     (gemini-2.5-flash) via google-genai (image -> inline `Part.from_bytes`;
     video -> inline `Blob` < ~20 MB else Files API). Prompt for STRICT JSON,
     strip ```json fences, `json.loads` into `perception`.
  3. Match every detected fault against THIS asset's history (already asset-
     scoped) -> `history_match`; the fault most tied to this asset's history
     becomes the primary.
  4. Auto-log a genuinely-new primary fault back into `AssetIssueHistory` (guarded).

Output: { perception, history_match, history_logged, history_logged_error }.

All clients (UiPath SDK + google-genai) are created INSIDE the node, so the
module imports without credentials and `uipath init` can introspect the graph.

Note: the import is `from uipath.platform import UiPath` — `from uipath import
UiPath` does not exist in the installed SDK and raises ImportError.
"""

import io
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath

from foreman_emit import Emitter, configure as fm_configure  # FOREMAN UI live feed

# --- Configuration ----------------------------------------------------------

BUCKET_NAME = "foremenbucket"
BUCKET_FOLDER = "Shared/foremen v1"
GEMINI_MODEL = "gemini-3.1-pro-preview"
INLINE_MAX_BYTES = 20 * 1024 * 1024  # ~20 MB: inline below this, Files API above.
GEMINI_MAX_ATTEMPTS = 4              # retry transient 429/5xx (e.g. 503 "high demand")

# Data Fabric history entity + auto-log policy.
HISTORY_ENTITY = "AssetIssueHistory"
HISTORY_FETCH_LIMIT = 1000           # bounded fetch; we filter by assetId in Python.
HISTORY_DESCRIPTION_MAXLEN = 200     # AssetIssueHistory.description Text field cap
AUTO_LOG_MIN_CONFIDENCE = 0.7
AUTO_LOG_TECHNICIAN = "auto-logged by foreman-vision"
SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
# Relationship strength — the primary fault prefers the strongest tie to THIS
# asset's history (recurrence > related > new), then severity, then confidence.
MATCH_STRENGTH = {"new": 0, "related": 1, "recurrence": 2}

# The prompt is split so the canonical vocabulary can be injected between the
# rules and the (always-last) strict-JSON instruction. See `_build_prompt`.
PROMPT_HEAD = """You are a field-equipment inspection vision system. Analyze the \
attached media (an image or a video) and report any infrastructure or equipment \
fault you can see or hear.

Detect ANY kind of fault — not just one type. Examples include, but are not \
limited to: corrosion/rust, overheating or thermal discoloration, smoke, fire, \
sparks, loose/exposed/damaged wiring, structural damage or cracks, deformation, \
leaks (oil/water/gas/coolant), missing or broken components, and abnormal \
sounds. If the media is a VIDEO WITH AUDIO, use the audio as evidence (e.g. \
grinding, buzzing, hissing, knocking, alarms) and say so in the evidence field.

Rules:
- Set "relevant" to false if the media is NOT a field-equipment / infrastructure \
scene (e.g. a plain road, an ordinary building, a person, or a random/unrelated \
clip). When false, leave "faults" as an empty array and explain why in \
"relevance_reason".
- NEVER invent a fault. Only report a fault that has clear VISIBLE or AUDIBLE \
evidence in this specific media. If there is no evidence of any fault, return an \
empty "faults" array.
- "confidence" is a number between 0 and 1.
- "severity" is one of: none, low, medium, high, critical.
- "recommended_urgency" is one of: routine, priority, emergency."""

PROMPT_JSON = """Respond with STRICT, RAW JSON ONLY — no markdown, no code fences, \
no commentary — in EXACTLY this shape:
{"media_kind":"image|video","relevant":bool,"relevance_reason":string,\
"scene":string,"faults":[{"type":string,"component":string,\
"severity":"none|low|medium|high|critical","evidence":string,\
"confidence":number}],"summary":string,\
"recommended_urgency":"routine|priority|emergency"}"""


# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Agent input."""

    mediaPath: str = Field(description="Path/key of the media file inside the bucket")
    mediaType: str = Field(description="MIME type, e.g. 'image/jpeg' or 'video/mp4'")
    assetId: str = Field(description="Asset identifier, e.g. 'AST-SCB-DEL-0788'")
    issueText: str = Field(
        default="",
        description="Worker-reported issue text from intake (optional; grounds the vision)",
    )
    caseId: str = Field(
        default="",
        description="FOREMAN case id (the case's external key). Routing key for the "
        "live UI feed; map this to the Maestro Case ID expression. Optional.",
    )


class GraphOutput(BaseModel):
    """Agent output."""

    issue_text_received: str = Field(
        default="",
        description="The worker-reported issue text the agent received (echoed for visibility)",
    )
    perception: dict = Field(
        default_factory=dict,
        description="Structured fault perception parsed from the vision model",
    )
    history_match: dict = Field(
        default_factory=dict,
        description="How the top fault relates to this asset's prior issue history",
    )
    history_logged: bool = Field(
        default=False,
        description="True if a new AssetIssueHistory record was written this run",
    )
    history_logged_error: str = Field(
        default="",
        description="Error detail if the auto-log write failed (empty when fine)",
    )


class GraphState(TypedDict, total=False):
    """Internal graph state."""

    mediaPath: str
    mediaType: str
    assetId: str
    issueText: str
    caseId: str
    perception: dict
    history_match: dict
    history_logged: bool
    history_logged_error: str
    issue_text_received: str


# --- Helpers ----------------------------------------------------------------


def _log(msg: str) -> None:
    """Emit a visible progress line to stderr (shows in `uip codedagent run`)."""
    print(f"[foreman-vision] {msg}", file=sys.stderr, flush=True)


def _norm_text(value) -> str:
    """Lowercase, trim, and collapse internal whitespace for robust comparison."""
    return " ".join(str(value or "").lower().split())


def _strip_json_fences(text: str) -> str:
    """Remove a leading ```json / ``` fence and trailing ``` if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _build_prompt(taxonomy: dict, issue_text: str = "") -> str:
    """Base prompt + optional worker-reported issue (grounding) + the canonical
    fault/component vocabulary. The strict-JSON instruction is always last."""
    sections = [PROMPT_HEAD]

    issue_text = (issue_text or "").strip()
    if issue_text:
        sections.append(
            "WORKER-REPORTED ISSUE (context only) — a field worker reported: "
            f'"{issue_text}".\n'
            "Use this to FOCUS your inspection and to choose consistent "
            "component/fault wording. BUT report only faults with clear visible or "
            "audible evidence in the media — you may CONFIRM or CONTRADICT this "
            "report. If the media does not actually show the reported problem, say "
            "so in relevance_reason/summary and do NOT fabricate it."
        )

    fault_types = taxonomy.get("faultTypes") or []
    components = taxonomy.get("components") or []
    vocab = []
    if fault_types:
        vocab.append(
            '- For each fault\'s "type": if it matches one of these known fault '
            "types, output that EXACT token — " + ", ".join(fault_types)
            + ". Only invent a short term of your own if none genuinely applies."
        )
    if components:
        vocab.append(
            '- For each fault\'s "component": if it matches one of these known '
            "components, output that EXACT string — " + ", ".join(components)
            + ". Only invent a short term of your own if none genuinely applies."
        )
    if vocab:
        sections.append(
            "KNOWN VOCABULARY (used so findings can be cross-referenced with this "
            "asset's maintenance history — prefer these exact values):\n"
            + "\n".join(vocab)
        )

    sections.append(PROMPT_JSON)
    return "\n\n".join(sections)


def _download_media(sdk: UiPath, media_path: str) -> bytes:
    """Download a file from the configured bucket into bytes (UiPath SDK)."""
    suffix = Path(media_path).suffix
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        sdk.buckets.download(
            name=BUCKET_NAME,
            blob_file_path=media_path,
            destination_path=tmp_path,
            folder_path=BUCKET_FOLDER,
        )
        return Path(tmp_path).read_bytes()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _build_media_part(client: genai.Client, data: bytes, media_type: str):
    """Build the Gemini content part for the media, per type and size."""
    if media_type.startswith("image/"):
        return types.Part.from_bytes(data=data, mime_type=media_type)

    if media_type.startswith("video/"):
        if len(data) < INLINE_MAX_BYTES:
            return types.Part(inline_data=types.Blob(data=data, mime_type=media_type))
        # Large video: upload via the Files API and wait for processing.
        uploaded = client.files.upload(
            file=io.BytesIO(data),
            config=types.UploadFileConfig(mime_type=media_type),
        )
        while uploaded.state and uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
        if uploaded.state and uploaded.state.name == "FAILED":
            raise RuntimeError(f"Gemini Files API failed to process media: {uploaded.name}")
        return uploaded

    raise ValueError(f"Unsupported mediaType {media_type!r}: expected image/* or video/*")


def _generate_with_retry(client: genai.Client, contents, config):
    """Call Gemini, retrying transient 429/5xx (e.g. 503 'high demand') with backoff."""
    delay = 4.0
    for attempt in range(1, GEMINI_MAX_ATTEMPTS + 1):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=config
            )
        except genai_errors.APIError as exc:
            transient = getattr(exc, "code", None) in (429, 500, 502, 503, 504)
            if not transient or attempt == GEMINI_MAX_ATTEMPTS:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable: retry loop always returns or raises")


# --- Data Fabric helpers ----------------------------------------------------
# AssetIssueHistory stores camelCase field names (assetId, siteId, ...). To stay
# robust to casing regardless, reads normalize every record to lowercase keys,
# and writes use the camelCase schema names (and additionally remap to a sample
# row's real casing if the live entity ever differs).


def _norm_record(rec) -> dict:
    """Return an EntityRecord (or dict) as a plain dict with lowercased keys."""
    if hasattr(rec, "model_dump"):
        try:
            data = rec.model_dump()
        except Exception:
            data = {}
    elif isinstance(rec, dict):
        data = dict(rec)
    else:
        data = {}
    return {str(k).lower(): v for k, v in data.items()}


def _real_key_casing(rec) -> dict:
    """Map lowercased field name -> real field name as stored on the entity."""
    if rec is None:
        return {}
    try:
        keys = rec.model_dump().keys() if hasattr(rec, "model_dump") else dict(rec).keys()
    except Exception:
        return {}
    return {str(k).lower(): k for k in keys}


def _sev_rank(severity) -> int:
    """Rank a severity label; unknown/empty sorts below 'none'."""
    return SEVERITY_ORDER.get(str(severity or "").strip().lower(), -1)


def _derive_site_id(asset_id: str) -> str:
    """AST-SCB-DEL-0788 -> 'DEL-0788'; '' when no site-like suffix is present."""
    match = re.search(r"([A-Za-z]+-\d+)$", asset_id.strip())
    return match.group(1) if match else ""


def _fetch_asset_history(sdk: UiPath, asset_id: str):
    """Read AssetIssueHistory and the fleet's fault/component vocabulary.

    Returns (rows, taxonomy, entity_id, raw_sample, ok):
      rows       - lowercase-key dicts for THIS asset, sorted issueDate desc
      taxonomy   - {"faultTypes": [...], "components": [...]} distinct across all
                   fetched rows (the controlled vocabulary)
      entity_id  - the entity GUID (needed for the auto-log write), or None
      raw_sample - one raw EntityRecord (for write-key casing), or None
      ok         - True only if the read completed without error
    Never raises.
    """
    empty_tax = {"faultTypes": [], "components": []}
    try:
        entity_id = next(
            (e.id for e in sdk.entities.list_entities()
             if str(e.name).lower() == HISTORY_ENTITY.lower()),
            None,
        )
        if entity_id is None:
            return [], empty_tax, None, None, False

        # retrieve_records is the structured endpoint that actually works on this
        # tenant (list_records' OData $filter is silently ignored). We fetch then
        # filter in Python for reliable case-insensitive matching.
        resp = sdk.entities.retrieve_records(entity_id, limit=HISTORY_FETCH_LIMIT)
        raw_items = getattr(resp, "items", None) or []
        raw_sample = raw_items[0] if raw_items else None
        all_norm = [_norm_record(r) for r in raw_items]

        taxonomy = {
            "faultTypes": sorted({
                str(d.get("faulttype", "")).strip()
                for d in all_norm if str(d.get("faulttype", "")).strip()
            }),
            "components": sorted({
                str(d.get("component", "")).strip()
                for d in all_norm if str(d.get("component", "")).strip()
            }),
        }

        target = asset_id.strip().lower()
        rows = [d for d in all_norm
                if str(d.get("assetid", "")).strip().lower() == target]
        rows.sort(key=lambda d: str(d.get("issuedate") or ""), reverse=True)
        return rows, taxonomy, entity_id, raw_sample, True
    except Exception:
        return [], empty_tax, None, None, False


def _fault_confidence(fault) -> float:
    """Parse a fault's confidence as float (0.0 on missing/invalid)."""
    try:
        return float((fault or {}).get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _classify_fault(fault: dict, history: list):
    """Classify ONE fault against THIS asset's history.

    Returns (match_type, matched_record, times_seen):
      recurrence - same component AND same faultType seen before on this asset
      related    - same component, different faultType
      new        - neither
    """
    f_type = _norm_text(fault.get("type"))
    f_component = _norm_text(fault.get("component"))
    recurrences, related = [], []
    if f_component:
        for rec in history:  # already newest-first, already this asset only
            if _norm_text(rec.get("component")) == f_component:
                if _norm_text(rec.get("faulttype")) == f_type:
                    recurrences.append(rec)
                else:
                    related.append(rec)
    if recurrences:
        return "recurrence", recurrences[0], len(recurrences)
    if related:
        return "related", related[0], 0
    return "new", None, 0


def _match_all_faults(faults: list, history: list):
    """Match every detected fault against THIS asset's history and pick the primary.

    `history` is already asset-scoped, so this only ever asks "has this issue
    happened on THIS asset before?". The primary fault ranks by relationship
    strength (recurrence > related > new), then severity, then confidence — so a
    known/recurring issue for this asset headlines over an unrelated higher-
    confidence detection. Returns (primary, all_matches); primary is None when
    there are no faults.
    """
    all_matches = []
    for fault in faults:
        match_type, matched, times_seen = _classify_fault(fault, history)
        all_matches.append({
            "fault": fault,
            "match_type": match_type,
            "matched": matched,
            "times_seen": times_seen,
            "rank": (MATCH_STRENGTH[match_type],
                     _sev_rank(fault.get("severity")),
                     _fault_confidence(fault)),
        })
    primary = max(all_matches, key=lambda m: m["rank"]) if all_matches else None
    return primary, all_matches


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', else 'Nth'."""
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _build_recommendation(match_type, top, matched, times_seen_before,
                          severity_trend, past_resolution, urgency, will_log) -> str:
    """Actionable, grounded recommendation — leads with the proven prior fix."""
    if top is None:
        return "No fault detected in the media; nothing to match against asset history."

    fault_type = top.get("type", "")
    component = top.get("component", "")
    severity = str(top.get("severity", "") or "")
    urgency_note = f" Recommended urgency: {urgency}." if urgency else ""

    if match_type == "recurrence":
        occ = _ordinal(times_seen_before + 1)
        msg = f"Recurring {fault_type} on {component} for this asset ({occ} occurrence)."
        if past_resolution:
            msg += f" Proven fix last time: '{past_resolution}' — apply the same remedy."
        else:
            msg += " No prior resolution was recorded; escalate for repair."
        if severity_trend == "escalation":
            msg += " Severity has escalated since last time — prioritize."
        return msg + urgency_note

    if match_type == "related":
        other = str(matched.get("faulttype", "")) if matched else ""
        if past_resolution:
            msg = (f"{component} was previously repaired on this asset for a '{other}' "
                   f"issue: '{past_resolution}'. Current fault is '{fault_type}' "
                   f"({severity}) — apply that proven remedy and check for a shared "
                   "root cause.")
        else:
            msg = (f"{component} has a prior '{other}' issue on this asset (no "
                   f"resolution recorded). Current fault is '{fault_type}' ({severity}) "
                   "— repair and check for a shared root cause.")
        return msg + urgency_note

    # new
    return (
        f"First recorded '{fault_type}' on '{component}' for this asset ({severity}). "
        "No prior fix on record — inspect and remediate per standard procedure."
        + urgency_note
        + (" Logged for future reference." if will_log else
           " (Not auto-logged: low confidence, not relevant, or history unavailable.)")
    )


# --- FOREMAN UI live feed ---------------------------------------------------


def _configure_emit_from_assets(sdk: UiPath) -> None:
    """Best-effort: pull the FOREMAN view-backend URL (text asset
    `FOREMAN_BACKEND_URL`) and ingest secret (credential asset
    `FOREMAN_INGEST_SECRET`) from Orchestrator, so the agent can reach the UI
    bridge. Falls back to env vars of the same names on any failure (passing
    None to configure() leaves the env-loaded defaults untouched). Never raises."""
    backend = None
    secret = None
    try:
        url_asset = sdk.assets.retrieve(name="FOREMAN_BACKEND_URL")
        backend = getattr(url_asset, "value", None) or str(url_asset)
    except Exception as exc:
        _log(f"FOREMAN_BACKEND_URL asset not read ({exc}); using env default")
    try:
        secret = str(sdk.assets.retrieve_credential(name="FOREMAN_INGEST_SECRET"))
    except Exception as exc:
        _log(f"FOREMAN_INGEST_SECRET asset not read ({exc}); using env default")
    fm_configure(backend=backend, secret=secret)


# --- Graph node -------------------------------------------------------------


async def perceive(state: GraphState) -> GraphState:
    """Perceive faults, reconcile against asset history, and auto-log new faults."""
    media_path = state["mediaPath"]
    media_type = state["mediaType"].strip()
    asset_id = state["assetId"]
    issue_text = (state.get("issueText") or "").strip()

    # All UiPath/Gemini clients are created here, inside the node.
    sdk = UiPath()

    # --- FOREMAN UI live feed: open the Perceive stage --------------------------
    site_id = _derive_site_id(asset_id)
    case_id = (state.get("caseId") or "").strip() or f"CASE-{site_id or asset_id}"
    _configure_emit_from_assets(sdk)
    fm = Emitter(case_id)
    # NOTE: the `intake` agent owns case.opened (the front door), so vision only
    # ADVANCES the stage — re-emitting case.opened here would reset the rail.
    # To run vision standalone, temporarily add:
    #   fm.case_opened(case_id=case_id, site_id=site_id, title=f"{asset_id} · field fault")
    fm.stage("perceive")
    fm.agent_running("vision")
    fm.log("perceive", "Vision · Gemini", "Reading asset history + analysing media")

    # --- Step 1: read history first (drives matching AND the prompt vocabulary) ---
    history, taxonomy, entity_id, raw_sample, history_ok = _fetch_asset_history(sdk, asset_id)
    _log(f"AssetIssueHistory read ok={history_ok} entity={entity_id} "
         f"rows_for_asset={len(history)}")
    for i, rec in enumerate(history):
        _log(
            f"  history#{i}: {rec.get('issuedate')} | type={rec.get('faulttype')} | "
            f"component={rec.get('component')} | sev={rec.get('severity')} | "
            f"status={rec.get('status')} | resolution={str(rec.get('resolution') or '')[:60]}"
        )
    _log(f"taxonomy.faultTypes={taxonomy['faultTypes']}")
    _log(f"taxonomy.components={taxonomy['components']}")

    # --- Step 2: media -> bytes -> Gemini perception (prompt aligned to taxonomy) ---
    data = _download_media(sdk, media_path)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Gemini credentials: set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env"
        )
    client = genai.Client(api_key=api_key)
    media_part = _build_media_part(client, data, media_type)

    _log(f"issue_text={issue_text!r}")
    response = _generate_with_retry(
        client,
        contents=[_build_prompt(taxonomy, issue_text), media_part],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    raw = _strip_json_fences(response.text or "")
    if not raw:
        raise RuntimeError("Gemini returned no text (possibly blocked or empty response)")
    perception = json.loads(raw)
    _log("perception relevant={} faults={}".format(
        perception.get("relevant"),
        [(f.get("type"), f.get("component"), f.get("severity"), f.get("confidence"))
         for f in (perception.get("faults") or [])],
    ))

    # --- FOREMAN UI live feed: media + perception cards ------------------------
    _ui_faults = perception.get("faults") or []
    fm.media_received([{
        "kind": "video" if media_type.startswith("video/") else "image",
        "label": Path(media_path).name, "meta": media_type,
        "note": perception.get("scene", ""),
    }])
    fm.perception_ready(
        {"findings": [{"modality": "image", "label": f.get("type", ""),
                       "detail": f.get("evidence"), "severity": f.get("severity"),
                       "confidence": f.get("confidence")} for f in _ui_faults],
         "issues": [f.get("type", "") for f in _ui_faults]},
        asset_note=f"{site_id or asset_id} · {perception.get('scene', '')} — Gemini vision",
    )

    # --- Step 3: match every detected fault against THIS asset's history -----
    # (history is already asset-scoped). The primary fault is the one most tied
    # to this asset's history: relationship (recurrence>related>new), then
    # severity, then confidence — so a known/recurring issue for THIS asset
    # headlines over an unrelated higher-confidence detection.
    faults = perception.get("faults") or []
    primary, all_matches = _match_all_faults(faults, history)
    for m in all_matches:
        _log(f"  fault-match: {m['match_type']} <- type={m['fault'].get('type')} "
             f"component={m['fault'].get('component')} sev={m['fault'].get('severity')} "
             f"conf={m['fault'].get('confidence')}")

    if primary is None:
        top, match_type, matched, times_seen_before = None, "new", None, 0
    else:
        top = primary["fault"]
        match_type = primary["match_type"]
        matched = primary["matched"]
        times_seen_before = primary["times_seen"]

    is_recurrence = match_type == "recurrence"
    is_new_fault_type = match_type == "new"
    past_resolution = str(matched.get("resolution", "")) if matched else ""

    # Severity trend vs. most recent matching record.
    if matched is not None and top is not None:
        cur_rank, past_rank = _sev_rank(top.get("severity")), _sev_rank(matched.get("severity"))
        if cur_rank > past_rank:
            severity_trend = "escalation"
        elif cur_rank < past_rank:
            severity_trend = "de-escalation"
        else:
            severity_trend = "same"
    else:
        severity_trend = "na"

    # Will we auto-log this fault? (decided before writing the recommendation)
    top_conf = _fault_confidence(top) if top else 0.0
    will_log = (
        bool(perception.get("relevant"))
        and top is not None
        and top_conf >= AUTO_LOG_MIN_CONFIDENCE
        and is_new_fault_type
        and history_ok
    )
    _log(f"primary match_type={match_type} times_seen_before={times_seen_before} "
         f"severity_trend={severity_trend} will_log={will_log}")

    # Actionable recommendation — leads with the proven prior fix for this asset.
    urgency = str(perception.get("recommended_urgency", "") or "")
    recommendation = _build_recommendation(
        match_type, top, matched, times_seen_before, severity_trend,
        past_resolution, urgency, will_log,
    )

    history_match = {
        "is_recurrence": is_recurrence,
        "match_type": match_type,
        "matched_record": matched,
        "times_seen_before": times_seen_before,
        "past_resolution": past_resolution,
        "severity_trend": severity_trend,
        "is_new_fault_type": is_new_fault_type,
        "recommendation": recommendation,
    }

    # --- Step 4: auto-log genuinely new faults ------------------------------
    history_logged = False
    history_logged_error = ""
    if will_log and top is not None and entity_id is not None:
        try:
            new_record = {
                "assetId": asset_id,
                "siteId": _derive_site_id(asset_id),
                # issueDate is a DateTime field (stored ISO); send full ISO UTC.
                "issueDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z"),
                "faultType": top.get("type", ""),
                "component": top.get("component", ""),
                "severity": top.get("severity", ""),
                "description": (
                    f"{top.get('evidence', '')} | {perception.get('summary', '')}"
                )[:HISTORY_DESCRIPTION_MAXLEN],
                "resolution": "",
                "status": "open",
                # resolvedDate (DateTime) is intentionally omitted while unresolved —
                # an empty string is rejected by the DateTime field.
                "batchId": "",
                "technician": AUTO_LOG_TECHNICIAN,
                "recurrenceCount": 0,
                "mediaPath": media_path,
            }
            # Keys match the AssetIssueHistory schema (camelCase). If the live
            # entity ever differs, remap to its real casing from a sample row.
            casing = _real_key_casing(raw_sample)
            if casing:
                new_record = {casing.get(k.lower(), k): v for k, v in new_record.items()}
            sdk.entities.insert_record(entity_id, new_record)
            history_logged = True
        except Exception as exc:  # never let a failed write crash the node
            history_logged = False
            history_logged_error = f"{type(exc).__name__}: {exc}"
    _log(f"auto-log logged={history_logged} error={history_logged_error[:150]}")

    # --- FOREMAN UI live feed: vision finding + history note -------------------
    ui_top = top or (faults[0] if faults else None)
    fm.agent_completed(
        "vision",
        headline=(f"{ui_top.get('type')} ({ui_top.get('severity')})"
                  if ui_top else "No fault detected"),
        detail=perception.get("summary"),
        confidence=(_fault_confidence(ui_top) if ui_top else None),
    )
    if history_match.get("recommendation"):
        fm.log("perceive", "History match", history_match["recommendation"][:140], "info")

    return {
        "issue_text_received": issue_text,
        "perception": perception,
        "history_match": history_match,
        "history_logged": history_logged,
        "history_logged_error": history_logged_error,
    }


builder = StateGraph(GraphState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("perceive", perceive)
builder.add_edge(START, "perceive")
builder.add_edge("perceive", END)

# The runtime factory looks for a compiled graph named exactly `graph`.
graph = builder.compile()
