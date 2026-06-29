"""FOREMAN Diagnosis-Recommendation agent (the always-on brain).

Turns *symptoms (perception) + facts (Data Fabric) + the learned skill cards +
retrieved reference knowledge* into ONE defensible diagnosis: a hard-gated skill
match, a single root cause with confidence + ruled-out alternatives, a concrete
cited recommendation, a stable fingerprint, a safety flag and a history-derived
systemic hint. The Supervisor invokes this agent by process name in folder
"Shared/foremen v1", so the output is a single FLAT JSON object.

CONTRACT
  input : { perception: dict, history_match: dict, asset_id: str, site_id: str,
            worker_text: str }
  output: one flat object (see GraphOutput) — strict, pydantic-validated, no prose.

READS (exact names, verified live in Orchestrator folder "Shared/foremen v1"):
  * Context Grounding index ``skill``   -> learned SK-* cards (the hard gate).
  * Context Grounding index ``context`` -> reference PDFs (the citations).
  * Data Fabric ``Asset``               -> assetid/type/vendor/batch/spec/siteid.
  * Data Fabric ``AssetIssueHistory``   -> prior issues (only if history_match is
    empty); camelCase fields assetId/faultType/component/severity/batchId/...
  * Agent Memory                        -> prior corrections (no-op if unset).
  NO graph / neo4j read here — the causal / blast-radius read is the fleet agent.

DESIGN NOTES (verified against the installed uipath 2.10.x SDK + uipath-langchain
and the live DefaultTenant — these differ from the spec's sample code):
  * Data Fabric reads use ``sdk.entities.retrieve_records(entity_id,
    filter_group=...)`` (the spec's ``sdk.entities.list(...)`` does not exist and
    ``list_records``'s OData ``$filter`` is silently ignored). ``retrieve_records``
    needs the entity's GUID id, resolved name->id via ``list_entities()``.
  * Retrieval: ``ContextGroundingRetriever(index_name=..., folder_path=
    "Shared/foremen v1")`` from ``uipath_langchain.retrievers``. Each returned doc
    carries ``metadata['source']`` = the EXACT file name (e.g.
    "mc4-connector-install-spec.pdf") — ``citations`` is built ONLY from those, so
    a citation is never invented.
  * LLM: ``UiPathChat(model="gpt-4.1-mini-2025-04-14")`` from
    ``uipath_langchain.chat`` with ``.with_structured_output`` for fixed-shape JSON.
  * The HARD GATE, the safety floor and ``systemic_hint`` are enforced in CODE
    after the LLM call so the contract holds even if the model drifts: a skill id
    is only accepted if it actually appears among the returned ``skill`` cards;
    ``systemic_hint`` is HISTORY-derived only; ``safety`` is floored to "critical"
    for arc/fire/exposed-conductor/HV hazards.

All UiPath clients are created INSIDE the node so the module imports without
credentials and ``uipath init`` can introspect the graph. The node NEVER throws —
on any error it returns the contract shape with a non-empty ``error``.
"""

import re
from typing import List, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath
from uipath.platform.entities.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    QueryFilterOperator,
)
from uipath_langchain.chat import UiPathChat
from uipath_langchain.retrievers import ContextGroundingRetriever

# --- Configuration ----------------------------------------------------------

FOLDER = "Shared/foremen v1"          # folder the indexes + Data Fabric live in
SKILL_INDEX = "skill"                  # learned SK-* cards (the hard gate)
CONTEXT_INDEX = "context"              # reference PDFs (the citations)
LLM_MODEL = "gpt-4.1-mini-2025-04-14"  # confirmed in this tenant's LLM Gateway
SKILL_RESULTS = 6
CONTEXT_RESULTS = 6
HISTORY_FETCH_LIMIT = 1000             # bounded fetch; filter in Python

# Hazard signs that floor safety to "critical" regardless of the model's call.
HAZARD_TERMS = (
    "arc", "fire", "burn", "burnt", "smoke", "spark", "exposed", "conductor",
    "melt", "molten", "char", "shock", "electrocut", "flame", "ignit",
    "high voltage", "high-voltage", " hv ", "live wire", "energiz",
)
# Negation cues — a hazard term inside one of these windows ("no exposed
# conductors", "without charring") is NOT a hazard and must not floor safety.
NEG_CUES = ("no ", "not ", "without", "n't", "free of", "absence of", "no sign")
# A skill id always looks like SK-... — used to read a card's own id from text.
SK_ID_RE = re.compile(r"\bSK-[A-Za-z0-9][A-Za-z0-9\-]*", re.IGNORECASE)


# --- Schemas ----------------------------------------------------------------


class Fingerprint(BaseModel):
    equipment_class: str = ""
    component: str = ""
    failure_mode: str = ""
    capacity_band: str = ""
    environment: str = ""


class GraphInput(BaseModel):
    """Thin input from the vision agent / supervisor.

    ``asset_id`` / ``site_id`` may arrive at the top level (supervisor) OR be
    carried inside ``history_match.matched_record`` (raw vision output); the node
    resolves both. The worker text may arrive as ``worker_text`` or as the vision
    agent's ``issue_text_received`` echo.
    """

    perception: dict = Field(default_factory=dict, description="vision_output.perception")
    history_match: dict = Field(
        default_factory=dict, description="vision_output.history_match (may be {})"
    )
    asset_id: str = Field(default="", description="Asset id, e.g. 'AST-SCB-DEL-0788'")
    site_id: str = Field(default="", description="Site id, e.g. 'DEL-0788'")
    worker_text: str = Field(default="", description="Worker-reported issue text")
    issue_text_received: str = Field(
        default="", description="Worker text echoed by the vision agent (fallback for worker_text)"
    )


class GraphOutput(BaseModel):
    """Output contract — ONE flat object (field names/types match the spec)."""

    skill_hit: Optional[str] = None
    skill_status: Optional[str] = None
    match_type: str = "new"  # exact | related | new
    root_cause: str = ""
    confidence: float = 0.0
    alternatives_ruled_out: List[str] = Field(default_factory=list)
    recommendation: str = ""
    citations: List[str] = Field(default_factory=list)
    what_differs: str = ""
    fingerprint: Fingerprint = Field(default_factory=Fingerprint)
    safety: str = "normal"  # normal | critical
    systemic_hint: bool = False
    error: str = ""


class _LLMDiagnosis(BaseModel):
    """The subset the LLM produces; the rest is enforced in code."""

    skill_hit: Optional[str] = None
    skill_status: Optional[str] = None
    match_type: str = "new"
    root_cause: str = ""
    confidence: float = 0.0
    alternatives_ruled_out: List[str] = Field(default_factory=list)
    recommendation: str = ""
    what_differs: str = ""
    citations: List[str] = Field(default_factory=list)
    safety: str = "normal"


# --- Data Fabric helpers ----------------------------------------------------


def _entity_ids(sdk: UiPath) -> dict:
    """Map entity name -> GUID id (the read endpoint needs the id, not the name)."""
    return {e.name: e.id for e in sdk.entities.list_entities()}


def _df_one(sdk: UiPath, entity_id: str, field: str, value: str):
    """First record where ``entity.field == value`` (structured query), else None."""
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


def _g(rec, key: str, default=None):
    """Read ``key`` from an EntityRecord (attr) or a dict, else ``default``."""
    if rec is None:
        return default
    if isinstance(rec, dict):
        return rec.get(key, default)
    return getattr(rec, key, default)


def _clean(value, default="") -> str:
    """Trim a Data Fabric string field (some carry trailing spaces, e.g. 'indoor ')."""
    if value is None:
        return default
    return str(value).strip()


def _fetch_history_for_asset(sdk: UiPath, entity_id: str, asset_id: str) -> list:
    """All AssetIssueHistory rows for THIS asset, newest first (lowercased keys)."""
    target = asset_id.strip().lower()
    if not target:
        return []
    resp = sdk.entities.retrieve_records(entity_id, limit=HISTORY_FETCH_LIMIT)
    rows = [_norm_record(r) for r in (getattr(resp, "items", None) or [])]
    rows = [r for r in rows if str(r.get("assetid", "")).strip().lower() == target]
    rows.sort(key=lambda r: str(r.get("issuedate") or ""), reverse=True)
    return rows


def _batch_siblings(sdk: UiPath, entity_id: str, batch_id: str, asset_id: str) -> int:
    """Count prior history rows on the SAME batch but a DIFFERENT asset."""
    batch = batch_id.strip().lower()
    if not batch:
        return 0
    me = asset_id.strip().lower()
    resp = sdk.entities.retrieve_records(entity_id, limit=HISTORY_FETCH_LIMIT)
    n = 0
    for r in (getattr(resp, "items", None) or []):
        d = _norm_record(r)
        if str(d.get("batchid", "")).strip().lower() == batch and \
                str(d.get("assetid", "")).strip().lower() != me:
            n += 1
    return n


# --- Domain helpers ---------------------------------------------------------


def _top_fault(perception: dict) -> dict:
    """Pick the headline fault: highest severity, then confidence."""
    order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    faults = [f for f in (perception.get("faults") or []) if isinstance(f, dict)]
    if not faults:
        return {}

    def rank(f):
        try:
            conf = float(f.get("confidence") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        return (order.get(str(f.get("severity", "")).strip().lower(), -1), conf)

    return max(faults, key=rank)


def _equipment_class(asset_type: str, component: str) -> str:
    """Coarse equipment class from the asset type + component (best-effort)."""
    blob = f"{asset_type} {component}".lower()
    if "solar" in blob or "mc4" in blob or "pv" in blob or "module" in blob or \
            "string" in blob or "inverter" in blob:
        return "pv_array"
    if "pdu" in blob or "distribution" in blob:
        return "power_distribution_unit"
    if "battery" in blob or "ups" in blob:
        return "energy_storage"
    return _clean(asset_type) or "unknown"


def _build_fingerprint(top: dict, asset: dict) -> Fingerprint:
    """Stable fingerprint from the top fault + the Asset record."""
    component = _clean(top.get("component"))
    failure_mode = _clean(top.get("type"))
    asset_type = _clean(_g(asset, "type", ""))
    spec = _clean(_g(asset, "spec", ""))
    environment = ""
    spec_l = spec.lower()
    if "outdoor" in spec_l or "marine" in spec_l or "coastal" in spec_l:
        environment = "outdoor"
    elif "indoor" in spec_l:
        environment = "indoor"
    return Fingerprint(
        equipment_class=_equipment_class(asset_type, component),
        component=component,
        failure_mode=failure_mode,
        capacity_band=spec or "unknown",
        environment=environment or "unknown",
    )


def _hazard_present(text: str) -> bool:
    """True if a hazard term appears in ``text`` in a NON-negated context.

    Skips occurrences whose immediately-preceding window carries a negation cue,
    so "no exposed conductors" / "without charring" do not floor safety.
    """
    t = " " + text.lower() + " "
    for term in HAZARD_TERMS:
        start = 0
        while True:
            i = t.find(term, start)
            if i == -1:
                break
            window = t[max(0, i - 22):i]
            if not any(cue in window for cue in NEG_CUES):
                return True
            start = i + len(term)
    return False


def _is_hazard(perception: dict, top: dict) -> bool:
    """True if any sign points to an arc/fire/exposed-conductor/HV hazard."""
    parts = [
        str(perception.get("summary", "")),
        str(perception.get("recommended_urgency", "")),
    ]
    for f in (perception.get("faults") or []):
        if isinstance(f, dict):
            parts += [str(f.get("type", "")), str(f.get("component", "")),
                      str(f.get("evidence", "")), str(f.get("severity", ""))]
    parts.append(str(top.get("type", "")) + " " + str(top.get("evidence", "")))
    # Check each fragment independently so a negation in one can't span into another.
    return any(_hazard_present(p) for p in parts if p)


async def _retrieve(index: str, query: str):
    """Run a Context Grounding retrieval; return [] on any error (degrade gracefully)."""
    try:
        retriever = ContextGroundingRetriever(
            index_name=index, folder_path=FOLDER,
            number_of_results=SKILL_RESULTS if index == SKILL_INDEX else CONTEXT_RESULTS,
        )
        return await retriever.ainvoke(query)
    except Exception:
        return []


def _sources_of(docs) -> list:
    """Ordered-unique EXACT source file names returned by a retrieval."""
    out = []
    for d in docs:
        src = (d.metadata or {}).get("source")
        if src and src not in out:
            out.append(src)
    return out


def _skill_card_ids(docs) -> set:
    """All SK-* ids that actually appear in the returned skill cards (the gate set)."""
    ids = set()
    for d in docs:
        src = (d.metadata or {}).get("source") or ""
        for m in SK_ID_RE.findall(src):
            ids.add(m)
        for m in SK_ID_RE.findall(d.page_content or ""):
            ids.add(m)
    return ids


# --- Prompt -----------------------------------------------------------------

SYSTEM = (
    "You are FOREMAN's field-equipment diagnosis-and-recommendation brain. You receive a machine "
    "PERCEPTION of an asset, the asset FACTS, this asset's prior HISTORY, the learned SKILL CARDS "
    "(SK-*), and retrieved reference CONTEXT. Produce ONE defensible diagnosis.\n\n"
    "SKILL MATCH (hard gate — obey exactly):\n"
    "- A skill card has hard_keys (equipment_class, component, failure_mode), a skill_status "
    "(candidate|trusted), canonical signs, a Differential / Rule-out section and a fix recipe.\n"
    "- match_type='exact' ONLY when a card's hard_keys match the live fingerprint (same "
    "equipment_class AND component AND failure_mode). Set skill_hit to that card's own SK-id and "
    "read skill_status from the card.\n"
    "- SMART-MATCH -> match_type='related' when NO exact failure_mode match exists but a card shares "
    "equipment_class + component AND the live perception signs appear among that card's canonical "
    "signs (e.g. 'frayed/splayed exposed copper at the crimp' is a bad-termination sign on the MC4 "
    "burn card — the live fault is an earlier stage of the same failure chain). Lower the confidence "
    "and fill what_differs with how the live fault differs from the card.\n"
    "- NEVER match across differing hard keys. If no card shares equipment_class + component, set "
    "match_type='new', skill_hit=null, skill_status=null.\n"
    "- NEVER invent a skill id: skill_hit must be an SK-id that literally appears in the SKILL CARDS "
    "provided. If the SKILL CARDS section is empty, you MUST return match_type='new', skill_hit=null.\n\n"
    "ROOT CAUSE: reason to a SINGLE root_cause with a 0-1 confidence. alternatives_ruled_out must "
    "list COMPETING DIAGNOSES FOR THE SAME FAULT PRESENTATION on THIS component — the rejected "
    "entries from the matched card's Differential / Rule-out section plus the reference CONTEXT "
    "(e.g. for an MC4 termination: water/moisture ingress, module hot-spot, busbar/contact "
    "corrosion). Do NOT fill it with unrelated equipment classes or with the other skill cards you "
    "already excluded by the hard gate. Confirm a fault only from its defining evidence; never call "
    "exposed conductors / arcing / charring cosmetic.\n\n"
    "RECOMMENDATION: concrete and actionable — if a card matched, follow its recipe. For an "
    "electrical hazard, isolate under no-load + LOTO first.\n\n"
    "CITATIONS: cite ONLY by the EXACT file names listed in AVAILABLE CONTEXT SOURCES, and only those "
    "that actually grounded your recommendation. Never cite a file not in that list.\n\n"
    "SAFETY: 'critical' for any arc/fire/exposed-conductor/high-voltage hazard, else 'normal'.\n\n"
    "Return ONLY the structured fields. Be concise and defensible."
)


# --- Node -------------------------------------------------------------------


async def diagnose(state: GraphInput) -> GraphOutput:
    perception = state.perception or {}
    history_match = state.history_match or {}
    asset_id = (state.asset_id or "").strip()
    site_id = (state.site_id or "").strip()
    worker_text = (state.worker_text or state.issue_text_received or "").strip()

    # asset_id / site_id may be carried inside history_match.matched_record (the
    # raw vision output) rather than at the top level — resolve from there.
    matched = history_match.get("matched_record") or {}
    if isinstance(matched, dict):
        if not asset_id:
            asset_id = str(matched.get("assetid") or matched.get("assetId") or "").strip()
        if not site_id:
            site_id = str(matched.get("siteid") or matched.get("siteId") or "").strip()

    top = _top_fault(perception)
    # Fingerprint + safety floor are computed up-front so even the error path is useful.
    fingerprint = Fingerprint(
        component=_clean(top.get("component")),
        failure_mode=_clean(top.get("type")),
    )
    safety_floor = "critical" if _is_hazard(perception, top) else "normal"

    try:
        sdk = UiPath()
        ids = _entity_ids(sdk)

        # 1) Facts: read the Asset record (drives fingerprint + the retrieval query).
        asset = _df_one(sdk, ids["Asset"], "assetid", asset_id) if "Asset" in ids else None
        asset_n = _norm_record(asset) if asset is not None else {}
        batch_id = _clean(asset_n.get("batch"))
        fingerprint = _build_fingerprint(top, asset_n)

        # 2) History: fold in the passed history_match; only read AssetIssueHistory
        #    ourselves when history_match is empty. systemic_hint is HISTORY-derived.
        history_rows: list = []
        if not history_match and "AssetIssueHistory" in ids:
            history_rows = _fetch_history_for_asset(
                sdk, ids["AssetIssueHistory"], asset_id
            )
        prior_same_asset = bool(history_rows) or bool(
            history_match.get("matched_record")
            or history_match.get("is_recurrence")
            or history_match.get("times_seen_before")
            or (history_match.get("match_type") in ("recurrence", "related"))
        )
        sibling_count = (
            _batch_siblings(sdk, ids["AssetIssueHistory"], batch_id, asset_id)
            if ("AssetIssueHistory" in ids and batch_id) else 0
        )
        systemic_hint = bool(prior_same_asset or sibling_count > 0)

        # 3) Agent Memory — best-effort prior corrections; no-op if unconfigured.
        memory_note = ""
        try:
            spaces = sdk.memory.list(folder_path=FOLDER).memory_spaces or []
            if spaces and top:
                from uipath.platform.memory.memory import MemorySearchRequest

                q = f"{top.get('type','')} {top.get('component','')} {asset_id}".strip()
                res = sdk.memory.search(
                    spaces[0].id, MemorySearchRequest(query=q, number_of_results=3),
                    folder_path=FOLDER,
                )
                hits = getattr(res, "results", None) or getattr(res, "memories", None) or []
                memory_note = " | ".join(str(getattr(h, "content", h))[:200] for h in hits)
        except Exception:
            memory_note = ""

        # 4) Retrieval: skill cards (hard gate) + context PDFs (citations).
        fault_terms = ", ".join(
            f"{_clean(f.get('type'))} on {_clean(f.get('component'))} "
            f"(severity {_clean(f.get('severity'))})"
            for f in (perception.get("faults") or []) if isinstance(f, dict)
        ) or _clean(perception.get("summary"))
        query = (
            f"{fault_terms}. Asset: {fingerprint.equipment_class}, "
            f"type {_clean(asset_n.get('type'))}, vendor {_clean(asset_n.get('vendor'))}, "
            f"batch {batch_id}, spec {_clean(asset_n.get('spec'))}. "
            f"Worker report: {worker_text}".strip()
        )

        skill_docs = await _retrieve(SKILL_INDEX, query)
        context_docs = await _retrieve(CONTEXT_INDEX, query)
        context_sources = _sources_of(context_docs)
        allowed_skill_ids = _skill_card_ids(skill_docs)

        skill_text = "\n\n".join(
            f"[{(d.metadata or {}).get('source','?')}] {d.page_content}" for d in skill_docs
        ) or "(no skill cards returned — you MUST set match_type='new', skill_hit=null)"
        context_text = "\n\n".join(
            f"[{(d.metadata or {}).get('source','?')}] {d.page_content}"
            for d in context_docs
        ) or "(no reference context returned)"

        # 5) Reason with the LLM Gateway (structured output).
        llm = UiPathChat(model=LLM_MODEL, temperature=0).with_structured_output(_LLMDiagnosis)
        user = (
            f"PERCEPTION:\n{perception}\n\n"
            f"FINGERPRINT (built from the top fault + asset): {fingerprint.model_dump()}\n\n"
            f"ASSET FACTS: type={_clean(asset_n.get('type'))}, "
            f"vendor={_clean(asset_n.get('vendor'))}, batch={batch_id}, "
            f"spec={_clean(asset_n.get('spec'))}, site={site_id}\n\n"
            f"WORKER REPORT: {worker_text or '(none)'}\n\n"
            f"PRIOR HISTORY (this asset): {history_match or history_rows or '(none)'}\n"
            f"BATCH SIBLINGS WITH PRIOR ISSUES (same batch, other assets): {sibling_count}\n\n"
            f"AGENT MEMORY: {memory_note or '(none)'}\n\n"
            f"SKILL CARDS (the ONLY ids you may use for skill_hit):\n{skill_text}\n\n"
            f"AVAILABLE CONTEXT SOURCES (cite ONLY these exact names): {context_sources}\n\n"
            f"REFERENCE CONTEXT:\n{context_text}\n\n"
            "Produce the structured diagnosis."
        )
        llm_out: _LLMDiagnosis = await llm.ainvoke(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        )

        # 6) Enforce the contract in code (hard gate, citations, safety, systemic).
        skill_hit = llm_out.skill_hit
        skill_status = llm_out.skill_status
        match_type = llm_out.match_type if llm_out.match_type in ("exact", "related", "new") else "new"
        if not skill_hit or skill_hit not in allowed_skill_ids:
            # Never accept an id that did not literally come back from the skill index.
            skill_hit, skill_status, match_type = None, None, "new"
        if match_type == "new":
            skill_hit, skill_status = None, None

        # Citations: keep ONLY exact file names the context retrieval really returned.
        src_lower = {s.lower(): s for s in context_sources}
        cited = []
        for c in (llm_out.citations or []):
            key = str(c).strip().lower()
            if key in src_lower and src_lower[key] not in cited:
                cited.append(src_lower[key])
        if not cited and context_sources:
            cited = context_sources[:3]  # audit fallback so the supervisor has a trail

        safety = "critical" if (safety_floor == "critical" or llm_out.safety == "critical") else "normal"

        try:
            confidence = max(0.0, min(1.0, float(llm_out.confidence)))
        except (TypeError, ValueError):
            confidence = 0.0

        return GraphOutput(
            skill_hit=skill_hit,
            skill_status=skill_status,
            match_type=match_type,
            root_cause=llm_out.root_cause,
            confidence=confidence,
            alternatives_ruled_out=llm_out.alternatives_ruled_out,
            recommendation=llm_out.recommendation,
            citations=cited,
            what_differs=llm_out.what_differs,
            fingerprint=fingerprint,
            safety=safety,
            systemic_hint=systemic_hint,
            error="",
        )
    except Exception as exc:  # never throw out of the node — return the contract shape
        return GraphOutput(
            match_type="new",
            fingerprint=fingerprint,
            safety=safety_floor,
            error=f"{type(exc).__name__}: {exc}",
        )


# --- Graph ------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("diagnose", diagnose)
builder.add_edge(START, "diagnose")
builder.add_edge("diagnose", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
