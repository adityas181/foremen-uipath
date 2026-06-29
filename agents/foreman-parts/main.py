"""FOREMAN Parts agent (the spares / logistics check).

Given the engine's recommended FIX, decide whether the parts that fix needs are
actually on the shelf — and, if a part is short, whether a GENUINE equivalent can
substitute or the fix is blocked. The Supervisor calls this after the
diagnosis-recommendation agent so it can route a job (do-it-now vs order-parts vs
escalate) before a crew is dispatched.

CONTRACT
  input : { fix: str, required_parts: [str], equipment_class: str }
  output: one flat object (see GraphOutput) — strict, pydantic-validated, no prose.

READS (real, verified live in DefaultTenant):
  * Data Fabric ``Inventory`` — flattened fields: partid, name, equipmentclass,
    kind, genuine ("true"/"false" STRING), stockqty (float), location,
    leadtimedays (float). Read via ``sdk.entities.retrieve_records(entity_id)``
    (the spec's ``sdk.entities.list(...)`` does not exist); name->id via
    ``list_entities()``. Matching is case-insensitive.

DESIGN
  * The LLM (``UiPathChat(model="gpt-4.1-mini-2025-04-14")``) does only the
    SEMANTIC part: (a) read ``fix`` and extract the concrete parts/consumables it
    needs when ``required_parts`` is empty, and (b) match each needed part to the
    best Inventory row by name/kind, proposing a genuine substitute when the
    primary match is short.
  * Every contract value (in_stock / location / lead_time_days / substitute /
    blocks_fix) is then computed in CODE from the resolved Inventory rows, so the
    model can never relax the safety rule. THE SUBSTITUTE RULE is enforced here:
    a substitute is accepted ONLY if it is a different in-stock row with
    ``genuine=true`` — a ``genuine=false`` / mixed-brand part (e.g. MC4-COMPAT-MIX)
    is NEVER offered, because cross-mating mixed connectors is the failure mode.

The LLM + SDK clients are built INSIDE the node so the module imports without
credentials and ``uipath init`` can introspect the graph. The node NEVER throws —
on any failed read it returns the contract shape with a non-empty ``error``.
"""

from typing import List, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath
from uipath_langchain.chat import UiPathChat

# --- Configuration ----------------------------------------------------------

INVENTORY_ENTITY = "Inventory"
LLM_MODEL = "gpt-4.1-mini-2025-04-14"  # confirmed in this tenant's LLM Gateway
INVENTORY_FETCH_LIMIT = 1000           # bounded fetch; scope/match in Python


# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Thin input from the diagnosis engine / supervisor."""

    fix: str = Field(default="", description="The recommended fix text (free text)")
    required_parts: List[str] = Field(
        default_factory=list,
        description="Concrete parts the fix needs; if empty, inferred from `fix`",
    )
    equipment_class: str = Field(
        default="", description="e.g. 'pv_string'; scopes the Inventory lookup"
    )


class GraphOutput(BaseModel):
    """Output contract — ONE flat object (field names/types match the spec)."""

    in_stock: bool = False        # true only if EVERY required part has stock_qty > 0
    location: str = ""            # where the required parts are; "" if none
    lead_time_days: int = 0       # max lead time across required parts (0 if all in stock)
    substitute: Optional[str] = None  # a GENUINE equivalent part_id if a part is short; else null
    blocks_fix: bool = False      # required part unavailable AND no valid substitute
    error: str = ""              # "" if ok


class _Req(BaseModel):
    """One required part, as resolved by the LLM against the catalog."""

    need: str = Field(default="", description="The concrete part/consumable needed")
    matched_part_id: Optional[str] = Field(
        default=None, description="part_id of the best Inventory match, or null if none"
    )
    substitute_part_id: Optional[str] = Field(
        default=None,
        description="part_id of a GENUINE equivalent to use if `need` is short, or null",
    )


class _LLMMatch(BaseModel):
    """The LLM's semantic result; the contract is computed from it in code."""

    requirements: List[_Req] = Field(default_factory=list)


# --- Data Fabric helpers ----------------------------------------------------


def _entity_ids(sdk: UiPath) -> dict:
    """Map entity name -> GUID id (the read endpoint needs the id, not the name)."""
    return {e.name: e.id for e in sdk.entities.list_entities()}


def _norm_row(rec) -> dict:
    """An EntityRecord/dict -> a clean dict with lowercased keys and typed fields."""
    if hasattr(rec, "model_dump"):
        try:
            data = rec.model_dump()
        except Exception:
            data = {}
    elif isinstance(rec, dict):
        data = dict(rec)
    else:
        data = {}
    low = {str(k).lower(): v for k, v in data.items()}
    return {
        "part_id": str(low.get("partid", "") or "").strip(),
        "name": str(low.get("name", "") or "").strip(),
        "equipment_class": str(low.get("equipmentclass", "") or "").strip(),
        "kind": str(low.get("kind", "") or "").strip(),
        "genuine": _as_bool(low.get("genuine")),
        "stock_qty": _as_int(low.get("stockqty")),
        "location": str(low.get("location", "") or "").strip(),
        "lead_time_days": _as_int(low.get("leadtimedays")),
    }


def _as_bool(value) -> bool:
    """`genuine` arrives as the STRING 'true'/'false' (not a real bool)."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _as_int(value) -> int:
    """`stockqty`/`leadtimedays` arrive as floats; coerce safely to int."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _load_inventory(sdk: UiPath, entity_id: str) -> List[dict]:
    """All Inventory rows as clean dicts."""
    resp = sdk.entities.retrieve_records(entity_id, limit=INVENTORY_FETCH_LIMIT)
    return [_norm_row(r) for r in (getattr(resp, "items", None) or [])]


def _scope(rows: List[dict], equipment_class: str) -> List[dict]:
    """Scope the catalog to `equipment_class` (case-insensitive) — but only if that
    yields rows, so a slightly-off class never starves the lookup."""
    ec = (equipment_class or "").strip().lower()
    if not ec:
        return rows
    scoped = [r for r in rows if r["equipment_class"].lower() == ec]
    return scoped or rows


def _by_id(rows: List[dict], part_id) -> Optional[dict]:
    """Find an Inventory row by part_id, case-insensitively."""
    if not part_id:
        return None
    key = str(part_id).strip().lower()
    return next((r for r in rows if r["part_id"].lower() == key), None)


# --- Prompt -----------------------------------------------------------------

SYSTEM = (
    "You are FOREMAN's spare-parts logistics checker. You receive the engine's "
    "recommended FIX, an optional explicit list of REQUIRED PARTS, an optional "
    "EQUIPMENT CLASS, and the live INVENTORY CATALOG. Do TWO things:\n\n"
    "1) DETERMINE THE REQUIRED PARTS. If REQUIRED PARTS is non-empty, use exactly "
    "those as the needs. Otherwise read the FIX and extract the concrete parts and "
    "consumables it actually requires — including the tools a correct fix implies "
    "(e.g. a fix that says 'replace both mating MC4 connectors with a matched "
    "genuine pair and re-crimp' needs a genuine MC4 connector pair AND the MC4 "
    "crimp die). Do not invent parts the fix does not call for.\n\n"
    "2) MATCH each needed part to the single best row in the INVENTORY CATALOG by "
    "name/kind (and equipment_class when given); set matched_part_id to that row's "
    "part_id, or null if nothing in the catalog plausibly is that part. When a "
    "needed part calls for a GENUINE component (connectors especially), a "
    "genuine=false / mixed-brand row is NOT an acceptable match for it.\n\n"
    "SUBSTITUTE: only when the matched part is out of stock, propose "
    "substitute_part_id = a DIFFERENT catalog row that is a genuine, equivalent "
    "replacement (genuine=true and in stock). NEVER propose a genuine=false / "
    "mixed-brand part as a substitute for a connector — cross-mating mismatched "
    "connectors is the failure mode. If the matched part is in stock, leave "
    "substitute_part_id null.\n\n"
    "Use ONLY part_ids that literally appear in the INVENTORY CATALOG. Return ONLY "
    "the structured requirements."
)


# --- Node -------------------------------------------------------------------


async def check_parts(state: GraphInput) -> GraphOutput:
    fix = (state.fix or "").strip()
    required_parts = [str(p).strip() for p in (state.required_parts or []) if str(p).strip()]
    equipment_class = (state.equipment_class or "").strip()

    try:
        sdk = UiPath()
        ids = _entity_ids(sdk)
        if INVENTORY_ENTITY not in ids:
            return GraphOutput(blocks_fix=True, error=f"Inventory entity not found")

        catalog = _scope(_load_inventory(sdk, ids[INVENTORY_ENTITY]), equipment_class)

        # Render the catalog for the LLM (part_id is the only key it may emit).
        catalog_text = "\n".join(
            f"- part_id={r['part_id']} | name={r['name']} | kind={r['kind']} | "
            f"equipment_class={r['equipment_class']} | genuine={str(r['genuine']).lower()} | "
            f"stock_qty={r['stock_qty']} | location={r['location']} | "
            f"lead_time_days={r['lead_time_days']}"
            for r in catalog
        ) or "(catalog empty)"

        llm = UiPathChat(model=LLM_MODEL, temperature=0).with_structured_output(_LLMMatch)
        user = (
            f"FIX: {fix or '(none)'}\n\n"
            f"REQUIRED PARTS (explicit; empty means infer from FIX): "
            f"{required_parts or '(none — extract from FIX)'}\n\n"
            f"EQUIPMENT CLASS: {equipment_class or '(none)'}\n\n"
            f"INVENTORY CATALOG:\n{catalog_text}\n\n"
            "Produce the structured requirements (need + matched_part_id + "
            "substitute_part_id)."
        )
        llm_out: _LLMMatch = await llm.ainvoke(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        )

        reqs = llm_out.requirements or []
        if not reqs:
            # Nothing to source — cannot positively confirm stock, but it isn't a
            # parts shortage either: report empty, non-blocking.
            return GraphOutput(in_stock=False, error="")

        # --- Enforce the contract in code from the resolved Inventory rows. -----
        in_stock_all = True
        locations: List[str] = []
        max_lead = 0
        chosen_substitute: Optional[str] = None
        blocks = False

        for req in reqs:
            row = _by_id(catalog, req.matched_part_id)
            own_in_stock = bool(row) and row["stock_qty"] > 0

            if own_in_stock:
                locations.append(row["location"])
                max_lead = max(max_lead, row["lead_time_days"])
                continue

            # This required part is short (missing row or stock_qty == 0).
            in_stock_all = False

            # Validate the proposed substitute: a DIFFERENT, in-stock, GENUINE row.
            sub = _by_id(catalog, req.substitute_part_id)
            valid_sub = (
                sub is not None
                and sub["genuine"]
                and sub["stock_qty"] > 0
                and (row is None or sub["part_id"].lower() != row["part_id"].lower())
            )
            if valid_sub:
                if chosen_substitute is None:
                    chosen_substitute = sub["part_id"]
                locations.append(sub["location"])
                max_lead = max(max_lead, sub["lead_time_days"])
            else:
                # Short part with no genuine substitute -> the fix is blocked.
                blocks = True
                if row is not None:
                    max_lead = max(max_lead, row["lead_time_days"])

        # location: the shared location of the sourced parts ("" if none / mixed -> joined).
        distinct_locs = list(dict.fromkeys(loc for loc in locations if loc))
        location = (
            distinct_locs[0] if len(distinct_locs) == 1
            else ", ".join(distinct_locs) if distinct_locs else ""
        )
        lead_time_days = 0 if in_stock_all else max_lead

        return GraphOutput(
            in_stock=in_stock_all,
            location=location,
            lead_time_days=lead_time_days,
            substitute=chosen_substitute,
            blocks_fix=blocks,
            error="",
        )
    except Exception as exc:  # never throw out of the node — return the contract shape
        return GraphOutput(blocks_fix=True, error=f"{type(exc).__name__}: {exc}")


# --- Graph ------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("check_parts", check_parts)
builder.add_edge(START, "check_parts")
builder.add_edge("check_parts", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
