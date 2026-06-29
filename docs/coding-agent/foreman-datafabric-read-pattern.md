---
name: foreman-datafabric-read-pattern
description: Verified UiPath SDK call for FOREMAN agents to read a Data Fabric record by a field value
metadata: 
  node_type: memory
  type: project
  originSessionId: a3459b4a-f4c2-4659-816b-dd5559edc5cd
---

For FOREMAN coded agents (Option A: thin keys in, agent reads its own Data Fabric records), the **verified** read-one-by-field call against the staging `hackathon26_457/DefaultTenant` (uipath SDK 2.10.x) is:

```python
from uipath.platform import UiPath
from uipath.platform.entities.entities import (
    EntityQueryFilter, EntityQueryFilterGroup, QueryFilterOperator,
)

sdk = UiPath()
ids = {e.name: e.id for e in sdk.entities.list_entities()}  # name -> GUID id

def df_one(entity_id, field, value):
    fg = EntityQueryFilterGroup(query_filters=[
        EntityQueryFilter(field_name=field, operator=QueryFilterOperator.Equals, value=value)
    ])
    resp = sdk.entities.retrieve_records(entity_id, filter_group=fg, limit=1)
    return resp.items[0] if resp.items else None
```

**Why:** the spec's sample `sdk.entities.list(entity, filter="f eq 'v'")` does NOT exist. Two real gotchas: (1) `entities.list_records(..., filter="...")` exists but its OData `$filter` is **silently ignored** by this tenant's `/read` endpoint — it returns the whole table, so `limit=1` just yields the first row (wrong record). Use `retrieve_records` (structured POST query) instead. (2) `retrieve_records`/`list_records` need the entity's **GUID id**, not its name — the name returns `400 'Asset' is not valid`. Resolve name→id via `list_entities()`.

**Data Fabric field names are flattened, not the spec's snake_case.** Real entities + fields: Asset(`assetid`, `vendor`, `batch`, `installed` [tz-aware ISO], `siteid`, `type`, `spec`); Warranty(`assetid`, `warrantyid`, `windowdays` [float], `status`, `liable`); **ServiceContract(`siteid`, `tenant`, `contract`, `penaltyperhr` [float], `responseslamin` [float])** — verified live, multiple rows per `siteid`; **Site(`siteid`, `environment` [note: trailing space e.g. `"indoor "` — always `.strip()`], `humidity` [float], `status`)**; **Batch(`batchid`, `spec`, `health` e.g. `"suspect"`)** — verified live for AST-PDU-DEL-0512→batch VE-BATCH-07→health `suspect`. Full entity list (12): Asset, Batch, Conversation, ConversationLog, InboundMessage, Perception, ServiceContract, Site, Skill, SystemUser, Vendor, Warranty. `sdk.entities.*` produces **no bindings** (bindings.json stays `resources: []`).

**EntityRecord access:** records returned by `retrieve_records().items` are `EntityRecord` objects — use `getattr(rec, key)` (or `rec.model_dump()`), NOT `rec.get(key)` (raises AttributeError). The `_g(rec, key, default)` helper handles both attr and dict. For multi-row reads (e.g. all contracts for a site) use a `df_many` variant: same `retrieve_records` + filter_group but return `resp.items or []` with a higher `limit`.

**Standalone scripts need `from dotenv import load_dotenv; load_dotenv()`** before `UiPath()` — only `uipath run` auto-loads `.env`; a bare `python x.py` raises `BaseUrlMissingError`.

Apply this in the other readers: [[foreman-entitlement-agent]] is the proven Agent 01; **Agent 02 SLA-Risk is built & verified** (reads ServiceContract by `siteid`, aggregates `penaltyperhr`/`responseslamin`; DEL-0512→18000/1 tenant/high, DEL-0473→48000/3 tenants/high, missing site→0/empty/no-crash). **Agent 03 Root-cause is built & verified** (reads Asset→Site+Batch via this `df_one`+name→id; LLM=`UiPathChat(model="gpt-4.1-mini-2025-04-14")` from `uipath_langchain.chat` with `.with_structured_output(GraphOutput)` — both confirmed; knowledge via `ContextGroundingRetriever(index_name="foreman-knowledge", folder_path="Shared/foremen v1")` from `uipath_langchain.retrievers`. **Index name is `foreman-knowledge` (HYPHEN, not underscore), in folder `Shared/foremen v1`, ingestion Successful — `retrieve_across_folders(name="foreman_knowledge")` with an underscore returns nothing, which is misleading.** DEL-0512 emergency→`safety:critical`, casing-seam defect tied to VE-BATCH-07, `systemic_hint:true`, exposed wiring ruled-out-as-cosmetic not labelled cosmetic, and `citations:["pdu-spec-VE-BATCH-07","pdu-fault-troubleshooting","anti-patterns"]` once the name was fixed). **Agent 04 Fleet is built & verified** (reads Asset by `assetid`→`batch` via this `df_one`+name→id, then queries Neo4j). Neo4j creds live in Orchestrator **Assets** in folder `Shared/foremen v1` (Text type, read `.value`/`.string_value`) — `sdk.assets.retrieve(name=..., folder_path="Shared/foremen v1")` REQUIRES a folder_path or it 400s `1101 'A folder is required'`. **`neo4j_user` asset value is the Aura instance id `e1dfbbbd`, NOT `neo4j`** — read it from the asset, don't hard-code `neo4j`. `neo4j_uri=neo4j+s://e1dfbbbd.databases.neo4j.io`. neo4j driver is 6.x (`pip install neo4j`, dep `neo4j>=5.0.0`). Blast-radius Cypher `MATCH (s:Site)-[:USES]->(b:Batch {id:$batch_id}) RETURN s.id,s.environment,s.status,b.spec,b.health` verified: VE-BATCH-07→3 sites (BLR-0331/DEL-0512/HYD-0140) suspect→systemic, NG-BATCH-22→4 failing→systemic, NG-BATCH-30→1 (CHN-0455) healthy→not, XX-BATCH-99→0 no-crash. `systemic = health in (failing,suspect) AND sites>1`. Other folders (`Shared/Solution 1..4`) are empty; `Shared` has differently-named `Neo4j-Uri/-User/-Pass/-Database`. Agent 05 Supervisor should reuse this `df_one`/`df_many` + name→id + flattened field names. LLM models live in the gateway: gpt-4.1[-mini/-nano], gpt-4o*, gpt-5*/5.1/5.2/5.4, gemini-2.5-flash/pro, anthropic.claude-opus-4-7/4-8 & sonnet-4*/haiku-4-5 (via AwsBedrock).
