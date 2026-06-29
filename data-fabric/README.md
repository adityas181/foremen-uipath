# Data Fabric — schema + seed data

Data Fabric exports the **schema** (entities, fields, relationships) as a JSON file, but it does **not** export the record data. To reproduce the demo data, import the schema first, then load the records per entity from the CSVs in this folder.

These CSVs were rebuilt to match the live Data Fabric entities exactly (column names and values verified against the running tenant).

## Import order

1. **Schema** — Data Fabric → Entities → **Import/Export → Import schema** → select `../schema/entities-schema.json`. This recreates every entity and field.
2. **Records** — for each entity, open it → **Data** tab → **Import data** → upload the matching CSV.

Recommended load order (so any text foreign keys line up with the rows that reference them):

| # | Entity | File | Records |
|---|---|---|---|
| 1 | Site | `Site.csv` | 10 |
| 2 | Vendor | `Vendor.csv` | 2 |
| 3 | PartLot | `PartLot.csv` | 2 |
| 4 | Inventory | `Inventory.csv` | 3 |
| 5 | Crew | `Crew.csv` | 2 |
| 6 | Asset | `Asset.csv` | 10 |
| 7 | Warranty | `Warranty.csv` | 2 |
| 8 | ServiceContract | `ServiceContract.csv` | 4 |
| 9 | AssetIssueHistory | `AssetIssueHistory.csv` | 11 |

> **Not included here:** `Batch`, `Conversation`, and `ConversationLog` were not captured in the source screenshots, so no CSV was generated for them. Export those separately (or send the screenshots) if you want them in the repo. `Conversation`/`ConversationLog` are populated at runtime, so they don't strictly need seeding.

## Two data caveats (read before importing)

1. **`AssetIssueHistory` — three columns are truncated.** The `description`, `resolution`, and `mediaPath` values were cut off in the source screenshots; each truncated value ends with `…`. The structured fields (`faultType`, `component`, `status`, `batchId`, `severity`, `technician`, `recurrenceCount`) are complete and are what the matching/reasoning logic keys on. Before a final import, replace the `…` values with the full text from the live entity (widen the columns and re-copy, or pull them via Data Fabric **API Access**).
2. **`Site` — `MUM-0210` environment reads `costal`.** This is a typo in the live data (every other coastal site reads `coastal`). It's reproduced as-is so a re-import matches your tenant exactly. If you want, correct it to `coastal` in both Data Fabric and this CSV — but if FOREMAN's matching logic currently filters on `coastal`, fixing the typo also changes behaviour, so change both together.

## Import gotchas (from UiPath docs)

- CSV import is **not supported in Firefox** — use Chrome or Edge.
- CSV import does **not** support **relationship fields, choice sets, or auto-number fields**. If any of these entities use relationship-type fields, design them as **non-required** and link records after import — or keep the foreign key as a plain text column (these CSVs use text keys like `site_id`, `asset_id`, `batch`, `crew`, `part_lot` for exactly this reason).
- Columns for any field marked **required** must contain values; **unique** fields must not contain duplicates.
- Empty cells fall back to the field's default value.

## Note on the data model

The demo centres on the DEL-0473 case (coastal RF-cable corrosion + DG knock). `NG-BATCH-22` is the failing non-marine batch the Neo4j blast-radius query keys on, and DEL-0473's SLA exposure is ~₹48,000/hour while breached (Airtel ₹22k + Jio ₹16k + Vodafone Idea ₹10k, from `ServiceContract.csv`).
