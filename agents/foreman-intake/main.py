"""FOREMAN Intake agent (Phase 4 - front-door gatekeeper).

A field worker reports a fault over WhatsApp, often across several messages. This
agent runs ONCE PER MESSAGE and decides whether the report is COMPLETE before the
rest of the FOREMAN pipeline runs. A complete report needs three things:

  1. MEDIA  - a photo/video. Provided as the boolean input ``has_media``. This is
              NEVER inferred from text.
  2. ISSUE  - a fault description in the worker's own words.
  3. ASSET  - an asset id that EXISTS in the Data Fabric ``Asset`` entity.

Division of labour (per the FOREMAN spec):
  * the LLM does EXTRACTION (refine the issue text, pull an asset candidate) and
    PHRASES the reply;
  * the asset VALIDATION is done in CODE against Data Fabric - the LLM never
    decides whether an asset exists, and we never invent one.

SDK / repo notes (verified against the installed ``uipath`` 2.10.x SDK + the live
DefaultTenant Data Fabric - identical to ``foreman-entitlement`` / ``foreman-root-cause``):
  * Data Fabric reads use ``sdk.entities.retrieve_records(entity_id, filter_group=...)``
    (the spec's ``sdk.entities.list(...)`` does not exist and ``list_records``'s OData
    ``$filter`` is silently ignored by this tenant). ``retrieve_records`` needs the
    entity's **GUID id**, resolved name -> id via ``list_entities()``.
  * Asset field names are flattened, verified live: ``assetid``, ``siteid``, ``type``,
    ``vendor``, ``batch``, ``spec``. So ``site_id`` comes from ``siteid``.
  * LLM: ``UiPathChat`` from ``uipath_langchain.chat`` (the repo/AGENTS.md convention),
    ``gpt-4.1-mini-2025-04-14`` (confirmed in this tenant's LLM Gateway), used with
    ``.with_structured_output`` for the fixed-shape extraction.

All UiPath clients are created INSIDE the node so the module imports without
credentials and ``uipath init`` can introspect the graph. The decision logic is
factored into :func:`evaluate_intake`, whose LLM/Data-Fabric dependencies are
injected - that keeps the gatekeeper logic deterministically unit-testable
offline (see ``test_intake.py``).
"""

from typing import List, Tuple

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath
from uipath.platform.entities.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    QueryFilterOperator,
)
from uipath_langchain.chat import UiPathChat

from foreman_emit import Emitter, configure as fm_configure  # FOREMAN UI live feed

LLM_MODEL = "gpt-4.1-mini-2025-04-14"  # confirmed in this tenant's LLM Gateway
_NL_SCAN_LIMIT = 50  # max Asset rows scanned for a natural-language match


# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Per-message intake state carried forward across the worker's messages."""

    latest_message: str = Field(
        default="", description="Newest worker message (may be empty if media-only)"
    )
    has_media: bool = Field(
        default=False, description="True if a photo/video has arrived so far"
    )
    current_issue_text: str = Field(
        default="", description="Issue gathered so far (carried forward)"
    )
    current_asset_id: str = Field(
        default="", description="Validated asset gathered so far (carried forward)"
    )
    caseId: str = Field(
        default="",
        description="FOREMAN case id (the case's external key). Routing key for the "
        "live UI feed; map this to the Maestro Case ID expression. Optional.",
    )


class GraphOutput(BaseModel):
    """Output contract - field names/types must match the FOREMAN spec exactly."""

    complete: bool = False
    issue_text: str = ""
    asset_id: str = ""  # validated id, or "" if not valid yet
    site_id: str = ""  # the matched asset's site, or ""
    asset_verified: bool = False
    missing: List[str] = []  # any of "media", "issue", "asset"
    reply_message: str = ""  # WhatsApp text to send; "" if complete


class Extraction(BaseModel):
    """What the LLM pulls out of the latest message (extraction only)."""

    issue_text: str = Field(
        default="",
        description=(
            "The fault description in the worker's own words, merged with what is "
            "already known and lightly cleaned up. Empty if the message is only a "
            "greeting/small-talk with no fault described."
        ),
    )
    asset_id: str = Field(
        default="",
        description=(
            "An EXPLICIT asset identifier exactly as written, e.g. 'AST-PDU-DEL-0512'. "
            "Empty if the worker did not give an explicit id. Never guess one."
        ),
    )
    asset_type: str = Field(
        default="",
        description=(
            "If the worker described the asset in words (no explicit id), the "
            "normalized equipment type, e.g. 'power_distribution_unit' for 'PDU'. "
            "Empty otherwise."
        ),
    )
    site_hint: str = Field(
        default="",
        description=(
            "If the worker named a location (no explicit id), a short site token, "
            "e.g. 'DEL' for 'Delhi'. Empty otherwise."
        ),
    )


EXTRACT_SYSTEM = (
    "You are the intake extractor for FOREMAN, a field-ops fault-reporting assistant used "
    "over WhatsApp by telecom field workers. From the worker's latest message (plus any "
    "issue text already gathered) extract exactly two things and nothing else:\n"
    "1) issue_text: the fault description in the worker's own words, merged with what is "
    "already known and lightly cleaned up. If the latest message is only a greeting or "
    "small talk (e.g. 'hi', 'hello', 'you there?') that adds no fault information, return "
    "the issue already known unchanged (empty if nothing is known). Never invent a fault.\n"
    "2) An asset reference, ONLY if the worker actually gave one:\n"
    "   - asset_id: an EXPLICIT identifier exactly as written, e.g. 'AST-PDU-DEL-0512'. "
    "Set this only if such an id literally appears. Never guess or fabricate an id.\n"
    "   - Otherwise, if the worker described the asset in words, set asset_type to the "
    "normalized equipment type (e.g. 'power_distribution_unit' for 'PDU') and site_hint to "
    "a short location token (e.g. 'DEL' for 'Delhi'). Leave both empty if no asset was given.\n"
    "Do NOT decide completeness and do NOT write any reply - only extract."
)

REPLY_SYSTEM = (
    "You are FOREMAN's intake assistant replying to a field worker on WhatsApp. Their fault "
    "report is incomplete. Write ONE short, friendly message (1-2 sentences, no greeting "
    "needed) asking ONLY for the items still missing. The missing-item codes mean: "
    "'media' = a photo or short video of the problem; 'issue' = a short description of what is "
    "wrong; 'asset' = the asset ID from the equipment label. If an asset was provided but could "
    "NOT be found in our records, say you couldn't find that asset and ask them to double-check "
    "and re-send the asset ID. Never ask for anything already provided. No explanations, no lists."
)


# --- Data Fabric helpers (identical pattern to the other FOREMAN readers) ----


def _entity_ids(sdk: UiPath) -> dict:
    """Map entity name -> GUID id (the read endpoint needs the id, not the name)."""
    return {e.name: e.id for e in sdk.entities.list_entities()}


def _df_one(sdk: UiPath, entity_id: str, field: str, value: str):
    """First record where ``entity.field == value``, else None."""
    if not value:
        return None
    fg = EntityQueryFilterGroup(
        query_filters=[
            EntityQueryFilter(
                field_name=field, operator=QueryFilterOperator.Equals, value=value
            )
        ]
    )
    resp = sdk.entities.retrieve_records(entity_id, filter_group=fg, limit=1)
    return resp.items[0] if resp.items else None


def _df_by_type(sdk: UiPath, entity_id: str, asset_type: str, limit: int = _NL_SCAN_LIMIT):
    """Assets whose ``type == asset_type`` (or a capped page if no type given)."""
    if asset_type:
        fg = EntityQueryFilterGroup(
            query_filters=[
                EntityQueryFilter(
                    field_name="type",
                    operator=QueryFilterOperator.Equals,
                    value=asset_type,
                )
            ]
        )
        resp = sdk.entities.retrieve_records(entity_id, filter_group=fg, limit=limit)
    else:
        resp = sdk.entities.retrieve_records(entity_id, limit=limit)
    return resp.items or []


def _g(rec, key: str, default=None):
    """Read ``key`` from an EntityRecord (attr) or a dict, else ``default``."""
    if rec is None:
        return default
    if isinstance(rec, dict):
        return rec.get(key, default)
    return getattr(rec, key, default)


def _clean(value, default: str = "") -> str:
    """Trim a Data Fabric string field (some carry trailing spaces)."""
    if value is None:
        return default
    return str(value).strip()


def _validate_asset(
    sdk: UiPath, ids: dict, *, explicit_id: str = "", asset_type: str = "", site_hint: str = ""
) -> Tuple[str, str]:
    """Validate an asset candidate against the Data Fabric ``Asset`` entity.

    Returns ``(asset_id, site_id)`` of a real, matched record, or ``("", "")``.
    Never invents an asset:
      * an EXPLICIT id is accepted only if a record with that ``assetid`` exists;
      * a natural-language description (type + site) is accepted only if it
        resolves to a SINGLE confident match.
    """
    asset_entity = ids.get("Asset")
    if not asset_entity:
        return "", ""

    # 1) Exact id - authoritative when the worker gave one.
    if explicit_id:
        rec = _df_one(sdk, asset_entity, "assetid", explicit_id)
        if rec is not None:
            return _clean(_g(rec, "assetid")), _clean(_g(rec, "siteid"))
        return "", ""  # an explicit id that isn't in the entity is NOT valid

    # 2) Natural language - require exactly one type+site match to be confident.
    if asset_type or site_hint:
        matches = []
        for rec in _df_by_type(sdk, asset_entity, asset_type):
            siteid = _clean(_g(rec, "siteid"))
            if site_hint and site_hint.lower() not in siteid.lower():
                continue
            matches.append(rec)
        if len(matches) == 1:
            rec = matches[0]
            return _clean(_g(rec, "assetid")), _clean(_g(rec, "siteid"))

    return "", ""


# --- Reply phrasing ----------------------------------------------------------


def _fallback_reply(missing: List[str], bad_asset: str = "") -> str:
    """Deterministic WhatsApp line - the LLM phrases the reply, this is the safety net."""
    parts: List[str] = []
    if "media" in missing:
        parts.append("a photo or short video of the problem")
    if "issue" in missing:
        parts.append("a quick description of what's wrong")
    if "asset" in missing:
        if bad_asset:
            parts.append(
                f'the correct asset ID - I couldn\'t find "{bad_asset}" in our records, '
                "please double-check it"
            )
        else:
            parts.append("the asset ID from the equipment label")
    if not parts:
        return ""
    body = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Thanks for the report! To get this logged, could you also send {body}?"


async def _compose_reply(llm, missing: List[str], issue_text: str, bad_asset: str) -> str:
    """Ask the LLM to phrase the 'what's still missing' reply; fall back to code."""
    user = (
        f"Missing items: {missing}.\n"
        + (
            f"The worker mentioned asset '{bad_asset}' but it was NOT found in our records.\n"
            if bad_asset
            else ""
        )
        + f"Issue understood so far: {issue_text or '(none yet)'}.\n"
        "Write the WhatsApp reply now."
    )
    try:
        out = await llm.ainvoke(
            [
                {"role": "system", "content": REPLY_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
        text = (out.content or "").strip()
        return text or _fallback_reply(missing, bad_asset)
    except Exception:  # LLM/network hiccup - degrade gracefully
        return _fallback_reply(missing, bad_asset)


# --- Core decision logic (dependencies injected for testability) -------------


async def evaluate_intake(state: GraphInput, *, extract, validate, compose_reply) -> GraphOutput:
    """Decide completeness for one message.

    ``extract(latest_message, current_issue_text) -> Extraction`` (async) and
    ``compose_reply(missing, issue_text, bad_asset) -> str`` (async) are the LLM
    jobs; ``validate(explicit_id, asset_type, site_hint) -> (asset_id, site_id)``
    (sync) is the Data Fabric job. The node wires the real implementations; tests
    inject deterministic fakes.
    """
    # 1) LLM extraction - refine the issue, pull an asset candidate.
    extraction: Extraction = await extract(state.latest_message, state.current_issue_text)

    # Idempotent: never drop known info. Prefer freshly refined text, else carry forward.
    issue_text = (extraction.issue_text or "").strip() or (state.current_issue_text or "").strip()

    # 2) Validate the asset candidate IN CODE. A new explicit id overrides; otherwise
    #    carry forward the asset already validated in a previous run.
    effective_explicit = (extraction.asset_id or "").strip() or (state.current_asset_id or "").strip()
    asset_id, site_id = validate(
        effective_explicit, (extraction.asset_type or "").strip(), (extraction.site_hint or "").strip()
    )
    asset_verified = bool(asset_id)
    bad_asset = effective_explicit if (effective_explicit and not asset_verified) else ""

    # 3) Presence. media is the boolean ONLY - never inferred from text.
    media_present = bool(state.has_media)
    issue_present = bool(issue_text)
    asset_present = asset_verified

    # 4) Completeness + the fixed-order missing list.
    missing: List[str] = []
    if not media_present:
        missing.append("media")
    if not issue_present:
        missing.append("issue")
    if not asset_present:
        missing.append("asset")
    complete = not missing

    reply_message = "" if complete else await compose_reply(missing, issue_text, bad_asset)

    return GraphOutput(
        complete=complete,
        issue_text=issue_text,
        asset_id=asset_id,
        site_id=site_id,
        asset_verified=asset_verified,
        missing=missing,
        reply_message=reply_message,
    )


# --- FOREMAN UI live feed ----------------------------------------------------


def _configure_emit_from_assets(sdk: UiPath) -> None:
    """Best-effort: pull the FOREMAN view-backend URL (text asset
    ``FOREMAN_BACKEND_URL``) and ingest secret (credential asset
    ``FOREMAN_INGEST_SECRET``) from Orchestrator so the agent can reach the UI
    bridge. Falls back to env vars of the same names on any failure (passing None
    to configure() leaves the env-loaded defaults untouched). Never raises."""
    backend = secret = None
    try:
        url_asset = sdk.assets.retrieve(name="FOREMAN_BACKEND_URL")
        backend = getattr(url_asset, "value", None) or str(url_asset)
    except Exception as exc:
        print(f"[foreman-intake] FOREMAN_BACKEND_URL asset not read ({exc}); using env default")
    try:
        secret = str(sdk.assets.retrieve_credential(name="FOREMAN_INGEST_SECRET"))
    except Exception as exc:
        print(f"[foreman-intake] FOREMAN_INGEST_SECRET asset not read ({exc}); using env default")
    fm_configure(backend=backend, secret=secret)


# --- Node --------------------------------------------------------------------


async def intake_node(state: GraphInput) -> GraphOutput:
    sdk = UiPath()

    # --- FOREMAN UI live feed: open the case + the Intake stage ----------------
    case_id = (getattr(state, "caseId", "") or "").strip() or "CASE-INTAKE"
    _configure_emit_from_assets(sdk)
    fm = Emitter(case_id)
    fm.case_opened(case_id=case_id, title="Field report", scenario="C")
    fm.stage("intake")
    _inbound = (state.latest_message or "").strip()
    if _inbound:
        fm.message("worker", _inbound)
    elif state.has_media:
        fm.message("worker", "(sent a photo / video)")

    ids = _entity_ids(sdk)
    llm_extract = UiPathChat(model=LLM_MODEL, temperature=0).with_structured_output(Extraction)
    llm_reply = UiPathChat(model=LLM_MODEL, temperature=0.3)

    async def extract(latest_message: str, current_issue_text: str) -> Extraction:
        msg = (latest_message or "").strip()
        if not msg:  # media-only message - nothing to extract, keep known issue
            return Extraction(issue_text=(current_issue_text or "").strip())
        user = (
            f"ISSUE ALREADY KNOWN: {current_issue_text or '(none)'}\n"
            f"LATEST MESSAGE: {latest_message}\n\n"
            "Extract now."
        )
        try:
            return await llm_extract.ainvoke(
                [
                    {"role": "system", "content": EXTRACT_SYSTEM},
                    {"role": "user", "content": user},
                ]
            )
        except Exception:  # degrade: keep known issue, no asset candidate
            return Extraction(issue_text=(current_issue_text or "").strip())

    def validate(explicit_id: str, asset_type: str, site_hint: str) -> Tuple[str, str]:
        return _validate_asset(
            sdk, ids, explicit_id=explicit_id, asset_type=asset_type, site_hint=site_hint
        )

    async def compose_reply(missing: List[str], issue_text: str, bad_asset: str) -> str:
        return await _compose_reply(llm_reply, missing, issue_text, bad_asset)

    result = await evaluate_intake(
        state, extract=extract, validate=validate, compose_reply=compose_reply
    )

    # --- FOREMAN UI live feed: reply / completion + stage progression ----------
    if result.complete:
        # enrich the card with the verified asset, then advance to Confirm
        fm.case_opened(case_id=case_id, site_id=result.site_id,
                       title=f"{result.asset_id} · field fault")
        fm.stage("confirm")
        fm.log("intake", "Intake", f"Report complete · asset {result.asset_id} verified", "ok")
        fm.message("foreman", "Got everything I need - analysing now.")
    else:
        if result.reply_message:
            fm.message("foreman", result.reply_message)
        fm.log("intake", "Intake", "Incomplete · still need: " + ", ".join(result.missing), "warn")

    return result


# --- Graph -------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("intake", intake_node)
builder.add_edge(START, "intake")
builder.add_edge("intake", END)
graph = builder.compile()
