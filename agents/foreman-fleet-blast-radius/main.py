"""FOREMAN - Knowledge-Graph coded agent (read at Investigate, learn at Close).

Two modes, one published agent - selected by the `mode` input:

  - mode="investigate" (default) - blast-radius traversal of the Neo4j graph: given the
    failing asset, find everything that shares the failure-driving factors (same batch, same
    environment) - is this a systemic fleet pattern or an isolated fault? Drives the case branch.

  - mode="close" - grow_graph: write the confirmed finding back so the graph LEARNS - the asset
    now EXHIBITS the failure mode, and once enough siblings on a batch fail the batch is flagged
    'failure_pattern'. That makes the next case smarter.

Generic: the traversal is parameterized by the asset only (batch + environment are derived in
Cypher), so it serves any equipment family without code changes. Emits CaseEvents at each step
so the UI's Fleet tab lights up live.
"""
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

import kg
from foreman_events import configure, emit, log


# -- Agent I/O contract (the Maestro Case passes Input, consumes Output) ------
class Input(BaseModel):
    case_id: str = Field(description="Maestro case id, e.g. CASE-PV-0758")
    asset_id: str = Field(description="The failing asset, e.g. AST-PV-RJ-S12")
    site_id: str = Field(default="", description="Site id, e.g. RJ-SOLAR-1")
    mode: str = Field(default="investigate", description="'investigate' (read) or 'close' (learn)")
    failure_mode: str = Field(default="mc4_connector_burn", description="Confirmed failure, e.g. mc4_connector_burn (drives common-cause + close)")
    confidence: float = Field(default=0.9, description="Confidence of the confirmed failure (close mode)")
    backend_url: str = Field(default="", description="Public URL of the view-backend (cloud); empty = localhost")


class State(BaseModel):
    case_id: str = ""
    asset_id: str = ""
    site_id: str = ""
    mode: str = "investigate"
    failure_mode: str = "mc4_connector_burn"
    confidence: float = 0.9
    backend_url: str = ""
    fleet: dict[str, Any] = {}
    grew: dict[str, Any] = {}


class Output(BaseModel):
    systemic: bool = False
    affected_count: int = 0
    affected_sites: list[str] = []
    batch_id: str = ""
    batch_status: str = ""
    known_pattern: bool = False           # has the graph learned this batch is a failure pattern?
    prior_failures: int = 0               # confirmed failures already recorded on this batch
    affected_assets: list[str] = []       # asset_ids in the blast radius (v2.1 JSON contract)
    criticality_rank: list[dict] = []     # [{factor, factorType, count}] biggest SPOFs first
    recommendation: str = ""


# -- Router: pick the mode at the entry --------------------------------------
def route(state: State) -> str:
    return "close" if state.mode == "close" else "blast"


# -- Investigate (read) ------------------------------------------------------
async def blast(state: State) -> dict[str, Any]:
    cid = state.case_id
    configure(state.backend_url)  # point emits at the public backend (cloud) when provided
    emit(cid, {"kind": "stage.entered", "stage": "investigate"})
    emit(cid, {"kind": "agent.running", "agent": "fleet"})
    log(cid, "investigate", "Fleet - Neo4j", "Blast-radius traversal on the knowledge graph")

    try:
        rows = kg.blast_radius(state.asset_id)
    except Exception as e:  # noqa: BLE001
        log(cid, "investigate", "Fleet - Neo4j", f"Knowledge graph unavailable: {e}", "warn")
        return {}

    payload = kg.to_fleet_payload(rows, state.asset_id)

    # Prefer the enriched multi-factor payload (crew/lot nodes, common-cause,
    # criticality, SQL-vs-graph) when the graph supports it; else keep v1.
    try:
        rich = kg.fleet_payload_v2(state.asset_id, state.failure_mode)
    except Exception as e:  # noqa: BLE001
        rich = {}
        log(cid, "investigate", "Fleet - Neo4j", f"Enriched payload skipped: {e}", "warn")
    if rich:
        payload = rich

    # What has the graph already LEARNED about this batch? (the "next case is
    # smarter" signal - confirmed prior failures + whether it's a known pattern)
    try:
        intel = kg.batch_intel(state.asset_id)
    except Exception:  # noqa: BLE001
        intel = {"confirmed_failures": 0, "known_pattern": False, "failure_modes": []}
    payload["prior_failures"] = intel["confirmed_failures"]
    payload["known_pattern"] = intel["known_pattern"]
    batch = rows[0]["batch_id"] if rows else ""
    payload["batch_id"] = batch

    # "Affected" means AT-RISK (structurally exposed), not only confirmed-failed:
    # pull every sibling that shares a failure-propagating factor (batch / crew /
    # part-lot) via the structural multi-factor traversal. This makes a clean graph
    # (no EXHIBITS edges yet) still flag the fleet. Additive - the confirmed-failure
    # path above (rich nodes/edges, batch_intel, prior_failures) is untouched.
    try:
        siblings = kg.multi_factor_blast_radius(state.asset_id)
    except Exception as e:  # noqa: BLE001 - degrade gracefully to not-systemic
        siblings = []
        log(cid, "investigate", "Fleet - Neo4j", f"Multi-factor blast-radius skipped: {e}", "warn")
    affected = list(dict.fromkeys([state.asset_id] + [s["asset_id"] for s in siblings]))
    payload["affected"] = affected
    payload["systemic"] = len(affected) >= 2

    # affected_assets carries the asset_ids; affected_sites must carry the SITE ids
    # of those assets - resolve them, de-duplicated and order-preserving (assets
    # with no site are skipped).
    try:
        site_map = kg.sites_for_assets(affected)
    except Exception as e:  # noqa: BLE001 - degrade gracefully to no site ids
        site_map = {}
        log(cid, "investigate", "Fleet - Neo4j", f"Site lookup skipped: {e}", "warn")
    affected_sites: list[str] = []
    for aid in affected:
        sid = site_map.get(aid)
        if sid and sid not in affected_sites:
            affected_sites.append(sid)
    payload["affected_sites"] = affected_sites

    emit(cid, {"kind": "fleet.ready", "fleet": payload})

    if intel["confirmed_failures"] > 0:
        modes = ", ".join(intel["failure_modes"]) or "failures"
        log(cid, "investigate", "Fleet - Neo4j",
            f"Graph memory: this batch already has {intel['confirmed_failures']} confirmed "
            f"{modes}" + (" - recognised failure pattern." if intel["known_pattern"] else "."),
            "warn" if intel["known_pattern"] else "agent")

    unit = payload.get("unitNoun", "site")
    n_aff = len(payload.get("affected", []))
    if payload.get("rootCause"):
        root = payload["rootCause"][0]
        headline = (f"Systemic - {n_aff} {unit}s via {root['factor']}"
                    if payload.get("systemic") else "Isolated - no shared factor")
        detail = (f"Common cause: {root['factorType']} {root['factor']} - a same-batch query misses it"
                  if payload.get("systemic") else "No shared failing factor")
        cites = ["neo4j:multi-factor", "neo4j:common-cause"]
    else:
        pat = " (known failure pattern)" if intel["known_pattern"] else ""
        headline = (f"Systemic - {n_aff} sites on {batch}{pat}"
                    if payload.get("systemic") else "Isolated - no fleet pattern")
        detail = ("Shares the failing batch in the same environment"
                  if payload.get("systemic") else "No shared failing batch")
        cites = ["neo4j:blast-radius", "neo4j:batch-intel"]
    emit(cid, {"kind": "agent.completed", "agent": "fleet", "run": {
        "headline": headline, "detail": detail, "confidence": 0.92, "citations": cites}})

    return {"fleet": payload}


async def finalize(state: State) -> Output:
    f = state.fleet or {}
    affected = f.get("affected", [])
    affected_sites = f.get("affected_sites", [])
    prior = f.get("prior_failures", 0)
    known = f.get("known_pattern", False)
    if f.get("systemic"):
        rec = (f"Systemic - {len(affected)} assets share the same crew/lot/batch and are at risk; "
               f"escalate a fleet review and pre-empt them.")
        if known:
            rec = (f"KNOWN failure pattern on batch {f.get('batch_id', '')} "
                   f"({prior} confirmed prior failures) - pre-empt all {len(affected)} assets now.")
    else:
        rec = "Isolated fault - handle as a one-off repair."
    return Output(systemic=f.get("systemic", False), affected_count=len(affected),
                  affected_sites=affected_sites, affected_assets=affected,
                  criticality_rank=f.get("criticality", []),
                  batch_id=f.get("batch_id", ""),
                  known_pattern=known, prior_failures=prior, recommendation=rec)


# -- Close (learn) -----------------------------------------------------------
async def close(state: State) -> Output:
    cid = state.case_id
    configure(state.backend_url)
    emit(cid, {"kind": "stage.entered", "stage": "close"})
    log(cid, "close", "Fleet - Neo4j", f"Learning: {state.asset_id} exhibits {state.failure_mode}")

    ts = datetime.now(timezone.utc).isoformat()
    try:
        rows = kg.grow_graph(state.asset_id, state.failure_mode, state.confidence,
                             cid, ts, threshold=2)
    except Exception as e:  # noqa: BLE001
        log(cid, "close", "Fleet - Neo4j", f"Knowledge graph unavailable: {e}", "warn")
        return Output(recommendation=f"Close failed to write graph: {e}")

    r = rows[0] if rows else {}
    batch, status, hits = r.get("batch_id", ""), r.get("status", ""), r.get("hits", 0)
    learned = (f"Batch {batch} is now a recognised failure pattern ({hits} siblings)."
               if status == "failure_pattern"
               else f"Recorded on batch {batch}; {hits} sibling(s) so far - not yet a pattern.")
    emit(cid, {"kind": "agent.completed", "agent": "fleet", "run": {
        "headline": "Graph updated", "detail": learned,
        "confidence": state.confidence, "citations": ["neo4j:grow"]}})
    emit(cid, {"kind": "case.closed", "case_id": cid})
    return Output(batch_id=batch, batch_status=status, recommendation=learned)


# -- Graph -------------------------------------------------------------------
builder = StateGraph(State, input=Input, output=Output)
builder.add_node("blast", blast)
builder.add_node("finalize", finalize)
builder.add_node("close", close)
builder.add_conditional_edges(START, route, {"blast": "blast", "close": "close"})
builder.add_edge("blast", "finalize")
builder.add_edge("finalize", END)
builder.add_edge("close", END)

graph = builder.compile()
