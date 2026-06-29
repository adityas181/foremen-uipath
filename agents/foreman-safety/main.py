"""FOREMAN Safety agent (the hard safety gate).

Given a fault classification (fault_type + component + severity + equipment_class
+ the optional matched skill id + the engine's own safety call), this agent
returns the MANDATORY safety protocol: whether the case is safety-critical, the
ordered action sequence (isolate first, LOTO, confirm de-energised, ...), the
specific standard clauses, the blockers that must clear before any work, the
EXACT source files it grounded on, and whether it can block auto-resolution. The
Supervisor invokes this agent by process name in folder "Shared/foremen v1", so
the output is a single FLAT JSON object.

CONTRACT
  input : { fault_type: str, component: str, severity: str,
            equipment_class: str, skill_hit: str|null, engine_safety: str }
  output: one flat object (see GraphOutput) — strict, pydantic-validated, no prose.

READS (exact names, folder "Shared/foremen v1"):
  * Context Grounding index ``context`` (PRIMARY) -> codes & standards / safety
    bulletins -> the standard clauses + the EXACT citation file names.
  * Context Grounding index ``skill`` (OPTIONAL)  -> if ``skill_hit`` is set, read
    that card to confirm its ``safety_protocol`` flag and reuse its safety
    citation(s).
  NO Data Fabric, NO Neo4j.

DESIGN NOTES (verified against the installed uipath-langchain SDK + the sibling
FOREMAN agents in this solution):
  * Retrieval: ``ContextGroundingRetriever(index_name=..., folder_path=
    "Shared/foremen v1")`` from ``uipath_langchain.retrievers``. Each returned doc
    carries ``metadata['source']`` = the EXACT file name (e.g.
    "pv-dc-arc-safety-bulletin.pdf"); ``citations`` is built ONLY from those, so a
    citation is never invented.
  * LLM: ``UiPathChat(model="gpt-4.1-mini-2025-04-14")`` from
    ``uipath_langchain.chat`` with ``.with_structured_output`` for fixed-shape JSON.
  * The SAFETY FLOOR is enforced in CODE after the LLM call so the contract holds
    even if the model drifts: ``safety_critical`` is forced true for any
    arc/fire/exposed-energised-conductor/HV/fall/derailment/pressure hazard or when
    ``engine_safety=="critical"``; ``can_block_auto_resolve`` is forced true for any
    safety-critical (life-safety) case; ``citations`` are filtered to the exact file
    names the retrieval actually returned.

All UiPath clients are created INSIDE the node so the module imports without
credentials and ``uipath init`` can introspect the graph. The node NEVER throws —
on any error it returns the contract shape with a non-empty ``error``.
"""

from typing import List, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath_langchain.chat import UiPathChat
from uipath_langchain.retrievers import ContextGroundingRetriever

# --- Configuration ----------------------------------------------------------

FOLDER = "Shared/foremen v1"           # folder the indexes live in
CONTEXT_INDEX = "context"              # codes & standards / safety bulletins (PRIMARY)
SKILL_INDEX = "skill"                  # learned SK-* cards (OPTIONAL confirm/reuse)
LLM_MODEL = "gpt-4.1-mini-2025-04-14"  # confirmed in this tenant's LLM Gateway
CONTEXT_RESULTS = 6
SKILL_RESULTS = 4

# Hazard signs that FLOOR safety_critical to true regardless of the model's call.
# Each entry is a life-safety hazard class: arc/fire, exposed energised conductor,
# high voltage, fall, derailment, pressure.
HAZARD_TERMS = (
    # arc / fire / thermal-electrical
    "arc", "arcing", "fire", "burn", "burnt", "smoke", "spark", "melt", "molten",
    "char", "scorch", "flame", "ignit", "thermal runaway",
    # exposed / energised conductor + shock
    "exposed", "exposed_wiring", "exposed wiring", "bare conductor", "bare copper",
    "exposed copper", "live wire", "live conductor", "energiz", "energis",
    "conductor", "shock", "electrocut", "short circuit", "short-circuit",
    # high voltage
    "high voltage", "high-voltage", " hv ", "kv", "dc bus", "dc string",
    # fall
    "fall", "height", "rooftop", "roof edge", "scaffold", "ladder",
    # derailment (rail)
    "derail", "derailment",
    # pressure
    "pressure", "pressurized", "pressurised", "overpressure", "burst", "rupture",
    "explos", "gas leak", "hydraulic",
)
# Negation cues — a hazard term inside one of these windows ("no exposed
# conductors", "without charring") is NOT a hazard and must not floor safety.
NEG_CUES = ("no ", "not ", "without", "n't", "free of", "absence of", "no sign")


# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Input from the Supervisor / diagnosis agent (all fields tolerant)."""

    fault_type: str = Field(default="", description="e.g. 'exposed_wiring'")
    component: str = Field(default="", description="e.g. 'MC4 connector'")
    severity: str = Field(default="", description="low | medium | high | critical")
    equipment_class: str = Field(default="", description="e.g. 'pv_array'")
    skill_hit: Optional[str] = Field(default=None, description="matched SK-id or null")
    engine_safety: str = Field(default="", description="upstream safety call: 'critical' | 'normal'")


class GraphOutput(BaseModel):
    """Output contract — ONE flat object (field names/types match the spec)."""

    safety_critical: bool = False
    protocol: str = ""                                       # mandatory action sequence
    standard_clause: List[str] = Field(default_factory=list)  # e.g. "NEC 690.11 (DC AFCI)"
    blockers: List[str] = Field(default_factory=list)         # must clear before work
    citations: List[str] = Field(default_factory=list)        # EXACT source file names
    can_block_auto_resolve: bool = False
    error: str = ""


class _LLMSafety(BaseModel):
    """The subset the LLM produces; the booleans/citations are enforced in code."""

    safety_critical: bool = False
    protocol: str = ""
    standard_clause: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


# --- Helpers ----------------------------------------------------------------


def _clean(value, default="") -> str:
    if value is None:
        return default
    return str(value).strip()


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


def _is_hazard(fault_type: str, component: str, equipment_class: str, severity: str) -> bool:
    """True if any classified field points to a life-safety hazard class."""
    # Check each fragment independently so a negation in one can't span into another.
    return any(
        _hazard_present(p)
        for p in (fault_type, component, equipment_class, severity)
        if p
    )


async def _retrieve(index: str, query: str, n: int):
    """Run a Context Grounding retrieval; return [] on any error (degrade gracefully)."""
    try:
        retriever = ContextGroundingRetriever(
            index_name=index, folder_path=FOLDER, number_of_results=n
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


# --- Prompt -----------------------------------------------------------------

SYSTEM = (
    "You are FOREMAN's field-equipment SAFETY gate. You receive a fault classification (fault_type, "
    "component, severity, equipment_class), the upstream engine's own safety call, the optional matched "
    "SKILL CARD, and retrieved STANDARDS & SAFETY BULLETINS. Produce the MANDATORY safety protocol.\n\n"
    "SAFETY-CRITICAL: true for ANY life-safety hazard — arc/fire, exposed or energised conductor, high "
    "voltage, fall from height, derailment, or pressure/explosion — OR when the engine's safety call is "
    "'critical'. (A PV DC connector with exposed copper carries live DC at system voltage -> critical.)\n\n"
    "PROTOCOL: the ordered, mandatory action SEQUENCE that must precede any contact. For live "
    "electrical / PV faults this is: isolate the affected string/circuit under NO LOAD by opening the DC "
    "isolator (disconnecting MC4s under load draws a sustained DC arc), then apply lockout/tagout (LOTO), "
    "then confirm de-energised at the meter, BEFORE any contact or repair. Isolation always comes first.\n\n"
    "STANDARD_CLAUSE: the SPECIFIC clauses the retrieved STANDARDS actually cite, e.g. 'NEC 690.11 (DC "
    "AFCI)' and the no-load isolation rule. Only clauses supported by the retrieved docs.\n\n"
    "BLOCKERS: the conditions that MUST clear before any work proceeds, e.g. 'confirm de-energised at "
    "system DC voltage', 'no work in wet conditions'. Concrete and checkable.\n\n"
    "CITATIONS: cite ONLY by the EXACT file names listed in AVAILABLE STANDARD SOURCES, and only those "
    "that actually grounded your protocol. Never cite a file not in that list.\n\n"
    "If a SKILL CARD is provided and it declares safety_protocol=true, treat the hazard as confirmed and "
    "reuse the card's safety citations.\n\n"
    "Return ONLY the structured fields. Be concise, ordered, and defensible."
)


# --- Node -------------------------------------------------------------------


async def assess(state: GraphInput) -> GraphOutput:
    fault_type = _clean(state.fault_type)
    component = _clean(state.component)
    severity = _clean(state.severity)
    equipment_class = _clean(state.equipment_class)
    skill_hit = _clean(state.skill_hit) or None
    engine_safety = _clean(state.engine_safety).lower()

    # Safety floor is computed up-front so even the error path is useful and safe.
    hazard = _is_hazard(fault_type, component, equipment_class, severity)
    safety_floor = bool(hazard or engine_safety == "critical")

    try:
        # 1) Retrieve the governing standards (PRIMARY) + the matched card (OPTIONAL).
        query = (
            f"Safety protocol, isolation procedure and governing standards for a "
            f"{fault_type} fault on a {component} in {equipment_class} "
            f"(severity {severity}). Hazard isolation, lockout/tagout, de-energise, "
            f"arc-flash, no-load disconnect, applicable code clauses."
        ).strip()

        context_docs = await _retrieve(CONTEXT_INDEX, query, CONTEXT_RESULTS)
        context_sources = _sources_of(context_docs)

        skill_docs = []
        if skill_hit:
            skill_docs = await _retrieve(
                SKILL_INDEX, f"{skill_hit} {fault_type} {component} safety_protocol", SKILL_RESULTS
            )

        context_text = "\n\n".join(
            f"[{(d.metadata or {}).get('source','?')}] {d.page_content}" for d in context_docs
        ) or "(no standards returned)"
        skill_text = "\n\n".join(
            f"[{(d.metadata or {}).get('source','?')}] {d.page_content}" for d in skill_docs
        ) or "(no skill card provided / returned)"

        # 2) Reason with the LLM Gateway (structured output).
        llm = UiPathChat(model=LLM_MODEL, temperature=0).with_structured_output(_LLMSafety)
        user = (
            f"FAULT CLASSIFICATION:\n"
            f"  fault_type      = {fault_type or '(none)'}\n"
            f"  component       = {component or '(none)'}\n"
            f"  severity        = {severity or '(none)'}\n"
            f"  equipment_class = {equipment_class or '(none)'}\n"
            f"  engine_safety   = {engine_safety or '(none)'}\n"
            f"  skill_hit       = {skill_hit or '(none)'}\n\n"
            f"MATCHED SKILL CARD (confirm its safety_protocol flag + reuse its safety citations):\n"
            f"{skill_text}\n\n"
            f"AVAILABLE STANDARD SOURCES (cite ONLY these exact names): {context_sources}\n\n"
            f"RETRIEVED STANDARDS & SAFETY BULLETINS:\n{context_text}\n\n"
            "Produce the structured safety protocol."
        )
        llm_out: _LLMSafety = await llm.ainvoke(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        )

        # 3) Enforce the contract in code (safety floor, citations, auto-resolve gate).
        safety_critical = bool(safety_floor or llm_out.safety_critical)

        # Citations: keep ONLY exact file names the standards retrieval really returned.
        src_lower = {s.lower(): s for s in context_sources}
        cited = []
        for c in (llm_out.citations or []):
            key = str(c).strip().lower()
            if key in src_lower and src_lower[key] not in cited:
                cited.append(src_lower[key])
        if not cited and context_sources:
            cited = context_sources[:3]  # audit fallback so the supervisor has a trail

        # Any life-safety hazard must gate auto-resolution (human gate required).
        can_block_auto_resolve = bool(safety_critical)

        return GraphOutput(
            safety_critical=safety_critical,
            protocol=_clean(llm_out.protocol),
            standard_clause=[_clean(s) for s in (llm_out.standard_clause or []) if _clean(s)],
            blockers=[_clean(b) for b in (llm_out.blockers or []) if _clean(b)],
            citations=cited,
            can_block_auto_resolve=can_block_auto_resolve,
            error="",
        )
    except Exception as exc:  # never throw out of the node — return the contract shape
        return GraphOutput(
            safety_critical=safety_floor,
            can_block_auto_resolve=safety_floor,
            error=f"{type(exc).__name__}: {exc}",
        )


# --- Graph ------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("assess", assess)
builder.add_edge(START, "assess")
builder.add_edge("assess", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
