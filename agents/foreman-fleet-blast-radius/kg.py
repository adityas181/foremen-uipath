"""FOREMAN Knowledge Graph (Neo4j) - generic, domain-agnostic.

The graph models the *shape* of field operations, not any one equipment family:
    (Asset)-[:FROM_BATCH]->(Batch)-[:SUPPLIED_BY]->(Vendor)
    (Asset)-[:LOCATED_AT]->(Site {environment, cluster, status})
    (Asset)-[:OF_CLASS]->(EquipmentClass)
    (Asset)-[:HAS_COMPONENT]->(Component)
    (Asset)-[:EXHIBITS {confidence, case_id, ts}]->(FailureMode)   - grown per case

Two operations:
  - blast_radius(asset_id)  - READ at the Investigate stage (parameterized; no literals)
  - grow_graph(...)         - WRITE at the Close stage (MERGE the learned facts)

Credentials resolve env-first (local .env) then UiPath Assets (cloud):
    NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD   or   Assets  Neo4j-Uri / Neo4j-User / Neo4j-Pass
"""
import math
import os
from typing import Any

# Use the OS trust store (Windows) so TLS-inspecting corporate proxies that re-sign
# certs with an internal root CA are trusted - fixes AuraDB CERTIFICATE_VERIFY_FAILED.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001 - harmless if unavailable (e.g. cloud Linux)
    pass

from neo4j import GraphDatabase

# The asset-level edges along which a fault can PROPAGATE between siblings. Two
# assets are "blast-radius related" if they share *any* of these - same build
# batch, same connector/part lot, OR the same install crew. This is the heart of
# why it's a graph: real co-failure is multi-relationship, not one shared column.
FACTOR_RELS = ["FROM_BATCH", "USES_PART_LOT", "INSTALLED_BY"]
# coalesce the id property across the heterogeneous factor node labels
_FACTOR_KEY = "coalesce(f.crew_id, f.lot_id, f.batch_id, f.name)"


def _creds() -> tuple[str, str, str]:
    uri = os.environ.get("NEO4J_URI")
    # Aura writes NEO4J_USERNAME; older guides use NEO4J_USER. AuraDB user is always 'neo4j'.
    user = os.environ.get("NEO4J_USERNAME") or os.environ.get("NEO4J_USER") or "neo4j"
    pwd = os.environ.get("NEO4J_PASSWORD")
    if not uri:
        from uipath.platform import UiPath  # imported lazily so local runs need no UiPath

        sdk = UiPath()

        def _asset(name: str) -> str:
            a = sdk.assets.retrieve(name, folder_path="Shared")
            return (
                getattr(a, "string_value", None)
                or getattr(a, "value", None)
                or getattr(a, "credential_password", None)
            )

        uri, user, pwd = _asset("Neo4j-Uri"), _asset("Neo4j-User"), _asset("Neo4j-Pass")
    return uri, user, pwd


def driver():
    uri, user, pwd = _creds()
    return GraphDatabase.driver(uri, auth=(user, pwd))


def database() -> str:
    # 2026 Aura instances name the default DB after the instance id; older ones use 'neo4j'.
    db = os.environ.get("NEO4J_DATABASE")
    if db:
        return db
    try:  # cloud: optional Asset, else fall back to the conventional default
        from uipath.platform import UiPath

        a = UiPath().assets.retrieve("Neo4j-Database", folder_path="Shared")
        return getattr(a, "string_value", None) or getattr(a, "value", None) or "neo4j"
    except Exception:  # noqa: BLE001
        return "neo4j"


# -- READ: generic blast-radius (only needs the asset id; batch + environment are
#         derived inside the traversal, so it works for any equipment family) ----
BLAST_RADIUS = """
MATCH (a:Asset {asset_id:$asset_id})-[:FROM_BATCH]->(b:Batch)
OPTIONAL MATCH (b)-[:SUPPLIED_BY]->(v:Vendor)
MATCH (a)-[:LOCATED_AT]->(asite:Site)
MATCH (b)<-[:FROM_BATCH]-(other:Asset)-[:LOCATED_AT]->(s:Site)
WHERE s.environment = asite.environment
RETURN DISTINCT other.asset_id AS asset_id, s.site_id AS site_id,
       s.environment AS environment, coalesce(s.status,'') AS status,
       b.batch_id AS batch_id, coalesce(b.status,'') AS batch_status,
       coalesce(v.name,'') AS vendor
ORDER BY site_id
"""


def blast_radius(asset_id: str) -> list[dict[str, Any]]:
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(BLAST_RADIUS, asset_id=asset_id).data()


# -- READ: what has the graph already LEARNED about this asset's batch? ----------
# This is what makes the *next* case smarter - it surfaces confirmed prior failures
# and whether the batch has crossed into a recognised failure pattern.
BATCH_INTEL = """
MATCH (a:Asset {asset_id:$asset_id})-[:FROM_BATCH]->(b:Batch)
OPTIONAL MATCH (b)<-[:FROM_BATCH]-(x:Asset)-[r:EXHIBITS]->(f:FailureMode)
RETURN b.batch_id AS batch_id, coalesce(b.status,'') AS batch_status,
       count(DISTINCT x) AS confirmed_failures,
       collect(DISTINCT f.name) AS failure_modes
"""


def batch_intel(asset_id: str) -> dict[str, Any]:
    with driver() as d, d.session(database=database()) as ses:
        rows = ses.run(BATCH_INTEL, asset_id=asset_id).data()
    r = rows[0] if rows else {}
    modes = [m for m in r.get("failure_modes", []) if m]
    return {
        "batch_id": r.get("batch_id", ""),
        "batch_status": r.get("batch_status", ""),
        "confirmed_failures": r.get("confirmed_failures", 0),
        "known_pattern": r.get("batch_status") == "failure_pattern",
        "failure_modes": modes,
    }


# ----------------------------------------------------------------------------
#  Graph-native intelligence - the four queries a SQL JOIN cannot express.
#  These are what turn "isn't this just a Data Fabric query?" into the strongest
#  moment of the demo. None of them break the v1 single-hop blast_radius above.
# ----------------------------------------------------------------------------

# -- (a) MULTI-FACTOR blast-radius: who else is at risk, and through WHICH link? --
# A batch JOIN only ever sees one shared column. This finds every sibling that
# shares ANY propagating factor (batch / connector lot / install crew) and reports
# the factor(s) - so the MC4 cluster that spans *different module batches* but the
# *same crew + lot* shows up, which a batch query misses entirely.
MULTI_FACTOR = f"""
MATCH (a:Asset {{asset_id:$asset_id}})-[r]->(f)<-[r2]-(other:Asset)
WHERE type(r) IN $rels AND type(r) = type(r2) AND other <> a
WITH other,
     collect(DISTINCT {{factor_type: head(labels(f)), via: type(r),
                        node: {_FACTOR_KEY}}}) AS shared
RETURN other.asset_id AS asset_id, shared, size(shared) AS shared_factors
ORDER BY shared_factors DESC, asset_id
"""


def multi_factor_blast_radius(asset_id: str) -> list[dict[str, Any]]:
    """Siblings reachable through ANY failure-propagating factor, with the why."""
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(MULTI_FACTOR, asset_id=asset_id, rels=FACTOR_RELS).data()


# -- (c) COMMON-CAUSE: across everything that exhibited this failure, what is the
#        single shared upstream node that explains the most of them? (the root,
#        not the symptom). For MC4 this returns the CREW and the LOT - never the
#        module batch - because the failures span batches but share the crew/lot.
COMMON_CAUSE = f"""
MATCH (a:Asset)-[:EXHIBITS]->(:FailureMode {{name:$failure_mode}})
MATCH (a)-[r]->(f) WHERE type(r) IN $rels
WITH head(labels(f)) AS factor_type, type(r) AS via, {_FACTOR_KEY} AS factor,
     count(DISTINCT a) AS explains, collect(DISTINCT a.asset_id) AS assets
WHERE explains >= $min_explains
RETURN factor_type, via, factor, explains, assets
ORDER BY explains DESC, factor_type
"""


def common_cause(failure_mode: str, min_explains: int = 2) -> list[dict[str, Any]]:
    """The shared upstream factor(s) that explain >= min_explains failures."""
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(COMMON_CAUSE, failure_mode=failure_mode,
                       rels=FACTOR_RELS, min_explains=min_explains).data()


# -- (d) CRITICALITY ranking: which factor, if it goes bad, exposes the MOST
#        assets? Degree centrality over the dependency graph - pure Cypher, no GDS
#        plugin needed (AuraDB-Free safe). This is the PROACTIVE flip: rank the
#        single-points-of-failure to harden first, before anything fails.
CRITICALITY = f"""
MATCH (f)<-[r]-(a:Asset) WHERE type(r) IN $rels
WITH head(labels(f)) AS factor_type, type(r) AS via, {_FACTOR_KEY} AS factor,
     count(DISTINCT a) AS dependents,
     coalesce(f.status,'') AS status
RETURN factor_type, via, factor, dependents, status
ORDER BY dependents DESC, factor_type
LIMIT $top
"""


def criticality_ranking(top: int = 10) -> list[dict[str, Any]]:
    """Factors ranked by how many assets depend on them (biggest SPOFs first)."""
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(CRITICALITY, rels=FACTOR_RELS, top=top).data()


# -- (f) EXPLAINABLE PATH: the traversal IS the audit evidence. Returns the
#        (asset)-[via]-(factor)-(sibling) triples, ready to drop into the pack.
BLAST_PATHS = f"""
MATCH (a:Asset {{asset_id:$asset_id}})-[r]->(f)<-[r2]-(other:Asset)
WHERE type(r) IN $rels AND type(r) = type(r2) AND other <> a
RETURN type(r) AS via, head(labels(f)) AS factor_type, {_FACTOR_KEY} AS through,
       other.asset_id AS sibling
ORDER BY via, sibling
"""


def blast_radius_paths(asset_id: str) -> list[dict[str, Any]]:
    """The explicit propagation paths, as cited reasoning for the audit pack."""
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(BLAST_PATHS, asset_id=asset_id, rels=FACTOR_RELS).data()


# -- READ: resolve asset_ids -> their site_ids (for the affected_sites output) ----
SITES_FOR_ASSETS = """
MATCH (a:Asset)-[:LOCATED_AT]->(s:Site)
WHERE a.asset_id IN $ids
RETURN a.asset_id AS asset_id, s.site_id AS site_id
"""


def sites_for_assets(asset_ids: list[str]) -> dict[str, str]:
    """Map each asset_id -> its site_id. Assets with no site are simply absent."""
    if not asset_ids:
        return {}
    with driver() as d, d.session(database=database()) as ses:
        rows = ses.run(SITES_FOR_ASSETS, ids=asset_ids).data()
    return {r["asset_id"]: r["site_id"] for r in rows if r.get("site_id")}


# ----------------------------------------------------------------------------
#  FULL enriched blast-radius payload for the UI Fleet tab - the same rich shape
#  the scripted MC4 scenario ships (asset + crew/lot/batch nodes, hot edges,
#  common-cause, criticality, SQL-vs-graph), but built LIVE from Neo4j. main.py
#  prefers this; it falls back to to_fleet_payload() if it returns nothing.
# ----------------------------------------------------------------------------
_SUBGRAPH = f"""
MATCH (origin:Asset {{asset_id:$asset_id}})
OPTIONAL MATCH (origin)-[r1]->(sf)<-[r2]-(sib:Asset)
WHERE type(r1) IN $rels AND type(r1) = type(r2) AND sib <> origin
WITH origin, collect(DISTINCT sib) AS sibs
WITH [origin] + sibs AS assets
UNWIND assets AS a
OPTIONAL MATCH (a)-[:EXHIBITS]->(fm:FailureMode {{name:$failure_mode}})
WITH a, count(fm) AS ex
MATCH (a)-[r]->(f)
WHERE type(r) IN $rels
RETURN a.asset_id AS asset_id, (a.asset_id = $asset_id) AS is_origin, (ex > 0) AS failed,
       type(r) AS rel, head(labels(f)) AS factor_type,
       {_FACTOR_KEY} AS factor, coalesce(f.status,'') AS factor_status
"""

_SQL_BATCH = """
MATCH (a:Asset {asset_id:$asset_id})-[:FROM_BATCH]->(b:Batch)<-[:FROM_BATCH]-(o:Asset)
WHERE o <> a
OPTIONAL MATCH (o)-[ex:EXHIBITS]->(:FailureMode {name:$failure_mode})
RETURN count(DISTINCT o) AS peers,
       count(DISTINCT CASE WHEN ex IS NOT NULL THEN o END) AS real
"""

_ORIGIN_CLASS = """
MATCH (a:Asset {asset_id:$asset_id})-[:OF_CLASS]->(e:EquipmentClass)
RETURN e.name AS cls
"""

_FACTOR_NODE_TYPE = {"Crew": "crew", "PartLot": "part_lot", "Batch": "batch",
                     "Vendor": "vendor", "Site": "site"}
_HOT_RELS = {"INSTALLED_BY", "USES_PART_LOT"}


def _unit_noun(cls: str) -> str:
    c = (cls or "").lower()
    if "pv" in c or "string" in c or "panel" in c or "solar" in c:
        return "string"
    if "rf" in c or "jumper" in c or "tower" in c or "antenna" in c:
        return "site"
    return "unit"


def _clamp(v: float) -> float:
    return max(6.0, min(94.0, round(v, 1)))


def _place_band(nodes: list[dict], y: float, span: float = 16.0) -> None:
    n = len(nodes)
    for i, nd in enumerate(nodes):
        nd["x"] = _clamp(50 + (i - (n - 1) / 2) * span)
        nd["y"] = y


def _place_rim(nodes: list[dict], y: float = 14.0) -> None:
    n = len(nodes)
    for i, nd in enumerate(nodes):
        nd["x"] = _clamp(50 if n <= 1 else 15 + 70 * (i / (n - 1)))
        nd["y"] = y


def _place_ring(nodes: list[dict], cx: float = 50, cy: float = 66, r: float = 32) -> None:
    n = max(len(nodes), 1)
    for i, nd in enumerate(nodes):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        nd["x"] = _clamp(cx + r * math.cos(ang))
        nd["y"] = _clamp(cy + (r * 0.78) * math.sin(ang))


def fleet_payload_v2(asset_id: str, failure_mode: str) -> dict[str, Any]:
    with driver() as d, d.session(database=database()) as ses:
        rows = ses.run(_SUBGRAPH, asset_id=asset_id, rels=FACTOR_RELS,
                       failure_mode=failure_mode).data()
        if not rows:
            return {}
        sqlrow = ses.run(_SQL_BATCH, asset_id=asset_id, failure_mode=failure_mode).data()
        clsrow = ses.run(_ORIGIN_CLASS, asset_id=asset_id).data()
    root = common_cause(failure_mode, min_explains=2)
    crit = criticality_ranking(top=8)
    root_ids = {r["factor"] for r in root}

    # First pass: collect assets and, per factor, its type/rel and the set of
    # assets that connect to it (so we can detect STRUCTURAL propagation hubs -
    # crew/part-lot nodes the origin shares with >=1 sibling - even before any
    # EXHIBITS failure exists yet).
    assets: dict[str, dict] = {}
    factor_meta: dict[str, dict] = {}
    raw_edges: list[dict] = []
    origin_batch = ""
    for r in rows:
        aid = r["asset_id"]
        if aid not in assets:
            parts = aid.split("-")
            label = "-".join(parts[-2:]) if len(parts) >= 2 else aid
            assets[aid] = {"id": aid, "label": label, "type": "asset",
                           "_failed": bool(r["failed"] or r["is_origin"])}
        fkey = r["factor"]
        if not fkey:
            continue
        meta = factor_meta.setdefault(
            fkey, {"type": _FACTOR_NODE_TYPE.get(r["factor_type"], "batch"),
                   "rel": r["rel"], "assets": set(), "origin": False})
        meta["assets"].add(aid)
        if r["is_origin"]:
            meta["origin"] = True
            if r["rel"] == "FROM_BATCH":
                origin_batch = fkey
        raw_edges.append({"from": aid, "to": fkey, "rel": r["rel"]})

    # A factor is a propagation hub if it is a CONFIRMED common-cause root (EXHIBITS
    # based) OR a STRUCTURAL crew/part-lot shared by the origin and >=1 sibling.
    # Batch is never a hot hub - FROM_BATCH is the weaker, coincidental factor.
    def _is_struct_hub(meta: dict) -> bool:
        return (meta["rel"] in _HOT_RELS and meta["origin"]
                and any(a != asset_id for a in meta["assets"]))

    factors: dict[str, dict] = {}
    for fkey, meta in factor_meta.items():
        ftype = meta["type"]
        confirmed = fkey in root_ids
        struct = _is_struct_hub(meta)
        is_hub = confirmed or struct
        if confirmed:
            status = "failing"          # a proven common-cause root
        elif struct:
            status = "at_risk"          # structural propagation hub (no failure yet)
        elif ftype == "batch":
            status = "healthy"          # batch-only overlap is the weak/false signal
        else:
            status = "at_risk"
        factors[fkey] = {"id": fkey, "label": fkey, "type": ftype,
                         "hub": is_hub, "status": status}

    # An edge is "hot" only along a propagating rel (crew / part-lot) to a hub;
    # FROM_BATCH edges always stay cool, even if the batch is a common-cause root.
    edges: list[dict] = []
    for e in raw_edges:
        hot = e["rel"] in _HOT_RELS and bool(factors[e["to"]].get("hub"))
        edges.append({**e, "hot": hot})

    # status: failing if it exhibited a real failure (or is the origin); at_risk if
    # it shares a hot crew/part-lot hub; healthy if it only shares a batch - that
    # last group is exactly the false positive a "same batch" query wrongly flags.
    hot_assets = {e["from"] for e in edges if e["hot"]}
    for aid, nd in assets.items():
        if nd.pop("_failed"):
            nd["status"] = "failing"
        elif aid in hot_assets:
            nd["status"] = "at_risk"
        else:
            nd["status"] = "healthy"

    # layout: hubs (and non-batch factors) in a centre band, batches on the top
    # rim (the scattered "false signal"), assets in a ring around the hubs
    hubs = [n for n in factors.values() if n.get("hub")]
    non_batch = [n for n in factors.values() if not n.get("hub") and n["type"] != "batch"]
    batches = [n for n in factors.values() if not n.get("hub") and n["type"] == "batch"]
    asset_nodes = list(assets.values())
    _place_band(hubs + non_batch, y=46)
    _place_rim(batches)
    _place_ring(asset_nodes)

    affected = [aid for aid, nd in assets.items() if nd["status"] != "healthy"]
    peers = sqlrow[0]["peers"] if sqlrow else 0
    real = sqlrow[0]["real"] if sqlrow else 0
    unit = _unit_noun(clsrow[0]["cls"] if clsrow else "")

    return {
        "systemic": len(affected) >= 2,
        "affected": affected,
        "nodes": asset_nodes + list(factors.values()),
        "edges": edges,
        "unitNoun": unit,
        "rootCause": [{"factor": r["factor"], "factorType": r["factor_type"],
                       "via": r["via"], "count": r["explains"]} for r in root],
        "criticality": [{"factor": r["factor"], "factorType": r["factor_type"],
                         "count": r["dependents"]} for r in crit
                        if r["factor"] in factors][:5],
        "sqlVsGraph": {
            "sqlFound": real,
            "sqlNote": f"WHERE batch = {origin_batch or 'X'} -> {peers} same-batch {unit}s",
            "graphFound": len(affected),
            "graphNote": f"traverse crew + part lot -> {len(affected)} {unit}s at risk across the fleet",
        },
        "queryTitle": "Multi-factor blast-radius - Cypher",
        "query": (f"MATCH (a:Asset {{asset_id:'{asset_id}'}})-[r]->(f)<-[r2]-(o:Asset)\n"
                  f"WHERE type(r) IN ['INSTALLED_BY','USES_PART_LOT'] AND type(r)=type(r2)\n"
                  f"RETURN o.asset_id, type(r) AS via, f"),
    }


# -- WRITE: grow the graph from a closed case (MERGE = idempotent upsert) --------
GROW = """
MATCH (a:Asset {asset_id:$asset_id})
MERGE (f:FailureMode {name:$failure_mode})
MERGE (a)-[r:EXHIBITS]->(f)
  SET r.confidence=$confidence, r.case_id=$case_id, r.ts=$ts
WITH a, f
MATCH (a)-[:LOCATED_AT]->(s:Site)  SET s.status='corroded'
WITH a, f
MATCH (a)-[:FROM_BATCH]->(b:Batch)
OPTIONAL MATCH (b)<-[:FROM_BATCH]-(sib:Asset)-[:EXHIBITS]->(f)
WITH b, count(DISTINCT sib) AS hits
SET b.status = CASE WHEN hits >= $threshold THEN 'failure_pattern'
                    ELSE coalesce(b.status,'healthy') END
RETURN b.batch_id AS batch_id, b.status AS status, hits
"""


def grow_graph(asset_id: str, failure_mode: str, confidence: float,
               case_id: str, ts: str, threshold: int = 2) -> list[dict[str, Any]]:
    with driver() as d, d.session(database=database()) as ses:
        return ses.run(GROW, asset_id=asset_id, failure_mode=failure_mode,
                       confidence=confidence, case_id=case_id, ts=ts,
                       threshold=threshold).data()


# -- Turn a blast-radius result into the UI's FleetGraph nodes/edges (radial) ----
def to_fleet_payload(rows: list[dict[str, Any]], origin_asset_id: str) -> dict[str, Any]:
    if not rows:
        return {"systemic": False, "affected": [], "nodes": [], "edges": []}

    batch_id = rows[0]["batch_id"]
    batch_status = rows[0]["batch_status"] or "failing"
    vendor = rows[0].get("vendor") or ""

    nodes: list[dict[str, Any]] = [{
        "id": batch_id, "label": batch_id, "type": "batch",
        "status": "failing" if batch_status in ("failing", "failure_pattern") else "healthy",
        "x": 50, "y": 50,
    }]
    edges: list[dict[str, Any]] = []
    if vendor:
        nodes.append({"id": vendor, "label": vendor, "type": "vendor", "x": 50, "y": 12})
        edges.append({"from": vendor, "to": batch_id, "rel": "SUPPLIED"})

    seen, sites = set(), []
    for r in rows:
        if r["site_id"] not in seen:
            seen.add(r["site_id"])
            sites.append(r)

    n = max(len(sites), 1)
    for i, r in enumerate(sites):
        theta = (2 * math.pi * i / n) - math.pi / 2
        x = round(50 + 34 * math.cos(theta), 1)
        y = round(58 + 30 * math.sin(theta), 1)
        origin = r["asset_id"] == origin_asset_id
        status = "corroded" if (origin or r["status"] in ("corroded", "affected")) else "at_risk"
        nodes.append({"id": r["site_id"], "label": r["site_id"], "type": "site",
                      "status": status, "x": x, "y": y})
        edges.append({"from": r["site_id"], "to": batch_id, "rel": "USES"})

    affected = [r["site_id"] for r in sites]
    return {"systemic": len(affected) >= 2, "affected": affected, "nodes": nodes, "edges": edges}
