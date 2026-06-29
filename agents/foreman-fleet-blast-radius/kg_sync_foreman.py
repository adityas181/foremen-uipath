"""Sync FOREMAN's REAL Data Fabric entities -> Neo4j (solar / MC4 build).

Drop-in replacement for the template kg_sync.py. Reads the REAL entities
(Asset, Site, Vendor, Batch, Crew, PartLot) - NOT the *Test ones - and MERGEs them into Neo4j,
including the crew + part-lot factor layer so the multi-factor blast-radius works.

    uipath auth
    uv run python kg_sync_foreman.py

Idempotent (MERGE). Run BEFORE the demo; in production attach to an Orchestrator nightly trigger.
Writes ONLY the structural backbone (no failures). The learned layer (EXHIBITS / failure_pattern) is
written live by the agent's close mode and is NEVER touched here.

CONNECTIVITY (so the graph renders as ONE fleet, not separate blobs):
  * every Asset links DIRECTLY to its Vendor      (Asset)-[:SUPPLIED_BY]->(Vendor)
  * every Site joins a Region from its id prefix  (Site)-[:IN_REGION]->(Region)   e.g. DEL-0788 -> DEL
These are STRUCTURAL connectors only - they are NOT in kg.py's FACTOR_RELS, so the blast-radius stays
precise (vendor/region do not make assets count as "affected").
Batch/Site are MERGEd (not MATCHed) so an asset is never dropped when its batch/site row is missing.
"""
import os

# load .env (Neo4j creds) before importing kg
for _l in open(".env", encoding="utf-8"):
    _l = _l.strip()
    if _l and not _l.startswith("#") and "=" in _l:
        _k, _, _v = _l.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip())

import kg  # the agent's kg.py, UNCHANGED (FACTOR_RELS = FROM_BATCH/USES_PART_LOT/INSTALLED_BY)
from uipath.platform import UiPath

# ── REAL entity Names in your DefaultTenant (no _Test suffix) ─────────────────
E_ASSET, E_SITE, E_VENDOR, E_BATCH, E_CREW, E_PARTLOT = (
    "Asset", "Site", "Vendor", "Batch", "Crew", "PartLot")

CONSTRAINTS = [
    "CREATE CONSTRAINT asset_id  IF NOT EXISTS FOR (a:Asset)          REQUIRE a.asset_id IS UNIQUE",
    "CREATE CONSTRAINT site_id   IF NOT EXISTS FOR (s:Site)           REQUIRE s.site_id  IS UNIQUE",
    "CREATE CONSTRAINT batch_id  IF NOT EXISTS FOR (b:Batch)          REQUIRE b.batch_id IS UNIQUE",
    "CREATE CONSTRAINT vendor_nm IF NOT EXISTS FOR (v:Vendor)         REQUIRE v.name     IS UNIQUE",
    "CREATE CONSTRAINT class_nm  IF NOT EXISTS FOR (e:EquipmentClass) REQUIRE e.name     IS UNIQUE",
    "CREATE CONSTRAINT crew_id   IF NOT EXISTS FOR (w:Crew)           REQUIRE w.crew_id  IS UNIQUE",
    "CREATE CONSTRAINT lot_id    IF NOT EXISTS FOR (p:PartLot)        REQUIRE p.lot_id   IS UNIQUE",
    "CREATE CONSTRAINT region_nm IF NOT EXISTS FOR (r:Region)         REQUIRE r.name     IS UNIQUE",
]

VENDOR = "MERGE (v:Vendor {name:$name})"
BATCH = "MERGE (b:Batch {batch_id:$batch_id}) SET b.spec=$spec, b.status=$status"
SITE = "MERGE (s:Site {site_id:$site_id}) SET s.environment=$environment, s.status=$status"
CREW = "MERGE (w:Crew {crew_id:$crew_id}) SET w.name=$name, w.region=$region"
PARTLOT = "MERGE (p:PartLot {lot_id:$lot_id}) SET p.kind=$kind, p.status=$status"

# Asset: structural backbone + the two propagating factors (crew + part-lot) + the two structural
# connectors (vendor, region). Batch/Site use MERGE so no asset is dropped if its row is missing.
ASSET = """
MERGE (a:Asset {asset_id:$asset_id})
MERGE (e:EquipmentClass {name:$equipment_class})
MERGE (a)-[:OF_CLASS]->(e)
MERGE (b:Batch {batch_id:$batch_id})
MERGE (a)-[:FROM_BATCH]->(b)
MERGE (s:Site {site_id:$site_id})
MERGE (a)-[:LOCATED_AT]->(s)
FOREACH (_ IN CASE WHEN $vendor <> '' THEN [1] ELSE [] END |
  MERGE (v:Vendor {name:$vendor})
  MERGE (a)-[:SUPPLIED_BY]->(v)
  MERGE (b)-[:SUPPLIED_BY]->(v))
FOREACH (_ IN CASE WHEN $region <> '' THEN [1] ELSE [] END |
  MERGE (rg:Region {name:$region})
  MERGE (s)-[:IN_REGION]->(rg))
FOREACH (_ IN CASE WHEN $crew <> '' THEN [1] ELSE [] END |
  MERGE (w:Crew {crew_id:$crew}) MERGE (a)-[:INSTALLED_BY]->(w))
FOREACH (_ IN CASE WHEN $part_lot <> '' THEN [1] ELSE [] END |
  MERGE (p:PartLot {lot_id:$part_lot}) MERGE (a)-[:USES_PART_LOT]->(p))
"""


def g(row: dict, key: str, default: str = "") -> str:
    """Field getter tolerant of Data Fabric's column-name transforms (case/underscore)."""
    def norm(s: str) -> str:
        return "".join(ch for ch in str(s).lower() if ch.isalnum())
    target = norm(key)
    for k, v in row.items():
        if norm(k) == target:
            return "" if v is None else str(v)
    return default


def _as_dict(rec) -> dict:
    if isinstance(rec, dict):
        return rec
    if hasattr(rec, "model_dump"):
        return rec.model_dump()
    return dict(getattr(rec, "__dict__", {}))


def fetch(sdk: UiPath, entity: str) -> list[dict]:
    ent = sdk.entities.retrieve_by_name(entity)
    key = getattr(ent, "key", None) or getattr(ent, "id", None)
    return [_as_dict(r) for r in sdk.entities.list_records(key)]


def region_of(site_id: str) -> str:
    """DEL-0788 -> DEL, MUM-0345 -> MUM. Empty if no recognisable prefix."""
    return site_id.split("-")[0].strip() if site_id and "-" in site_id else ""


if __name__ == "__main__":
    sdk = UiPath()
    with kg.driver() as d, d.session(database=kg.database()) as ses:
        for c in CONSTRAINTS:
            ses.run(c)

        for r in fetch(sdk, E_VENDOR):
            name = g(r, "vendor_name") or g(r, "name")
            if name:
                ses.run(VENDOR, name=name)

        for r in fetch(sdk, E_BATCH):
            ses.run(BATCH, batch_id=g(r, "batch_id"), spec=g(r, "spec"),
                    status=g(r, "health") or g(r, "status") or "healthy")

        for r in fetch(sdk, E_SITE):
            ses.run(SITE, site_id=g(r, "site_id"), environment=g(r, "environment"),
                    status=g(r, "status") or "open")

        for r in fetch(sdk, E_CREW):
            ses.run(CREW, crew_id=g(r, "crew_id"), name=g(r, "name"), region=g(r, "region"))

        for r in fetch(sdk, E_PARTLOT):
            ses.run(PARTLOT, lot_id=g(r, "lot_id"), kind=g(r, "kind"), status=g(r, "status"))

        for r in fetch(sdk, E_ASSET):
            site_id = g(r, "site_id")
            ses.run(ASSET,
                    asset_id=g(r, "asset_id"),
                    equipment_class=g(r, "type"),       # Asset.type  -> EquipmentClass
                    batch_id=g(r, "batch"),             # Asset.batch -> Batch.batch_id
                    site_id=site_id,
                    vendor=g(r, "vendor"),
                    region=region_of(site_id),          # site-id prefix -> Region
                    crew=g(r, "crew"),                  # new column on Asset
                    part_lot=g(r, "part_lot"))          # new column on Asset

    print("Synced REAL entities (Asset/Site/Vendor/Batch/Crew/PartLot) -> Neo4j.")
    print("Connectors added: Asset-[:SUPPLIED_BY]->Vendor and Site-[:IN_REGION]->Region (one fleet).\n")
    print("== same-batch + environment blast-radius from AST-SCB-DEL-0788 ==")
    for x in kg.blast_radius("AST-SCB-DEL-0788"):
        print(f"  {x['site_id']:10} env={x['environment']:20} batch={x['batch_id']} ({x['batch_status']})")
    print("\n== MULTI-FACTOR (crew + lot) blast-radius from AST-SCB-DEL-0788 ==")
    for x in kg.multi_factor_blast_radius("AST-SCB-DEL-0788"):
        vias = ", ".join(f"{s['via']}={s['node']}" for s in x["shared"])
        print(f"  {x['asset_id']:18} via [{vias}]")
    print("\n(Vendor + Region only connect the picture; they are NOT blast-radius factors, so the")
    print(" affected set is unchanged: DEL-0791 + DEL-0802 via batch+crew+lot; MUM-0345 excluded.)")