---
name: foreman-cost-agent
description: "foreman-cost STUB agent — static replace verdict, no DF/LLM/external; built & run-verified"
metadata: 
  node_type: memory
  type: project
  originSessionId: 82243a89-64c5-43e0-bb1b-128ed36d7dab
---

FOREMAN `foreman-cost` is a STUB (not invoked in MC4 demo), built like [[foreman-vendor-agent]] and [[foreman-entitlement-agent]]: static contract-valid response, no Data Fabric / LLM / external calls, async, never throws.

INPUT `{ asset_id, fix }` (tolerant, extra=ignore, ignored). OUTPUT (strict, extra=forbid): `decision="replace"`, `whole_life_cost=0.0`, `capex_flag=false`, `rationale="a charred connector is always cut out and replaced - no repair-vs-replace trade-off"`, `error=""`. Single node `cost_stub`, `StateGraph(State, input=Input, output=Output)` START→cost_stub→END, exposes `graph`.

BUILT & RUN-VERIFIED MC4. `uipath init` writes schema to entry-points.json (uipath.json is schema-less in this SDK version). Run with `uv run uipath run agent '{...}'`.
