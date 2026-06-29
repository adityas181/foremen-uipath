---
name: foreman-entitlement-agent
description: "FOREMAN entitlement STUB agent — static contract-valid vendor/warranty verdict, no DF/LLM/external calls, not invoked in MC4"
metadata: 
  node_type: memory
  type: project
  originSessionId: 995ef164-892e-4405-87d6-16fcbe5e2824
---

`foreman-entitlement` (d:\UIpath\foreman-entitlement) is a STUB agent present for completeness — NOT invoked in the MC4 demo. No Data Fabric, no LLM, no external calls; returns a STATIC contract-valid response regardless of input.

INPUT (all optional/tolerant): `asset_id`, `site_id`, `root_cause` (str).
OUTPUT (strict, extra="forbid"): `vendor=""`, `warranty_active=false`, `vendor_liable=false`, `claim_basis="field workmanship - not a claimable vendor/spec defect"`, `recovery_inr=0.0`, `error=""`.

Single-node `StateGraph` (`entitlement_stub`), exposed as `graph`. Scaffolded by copying [[foreman-vendor]]'s LangGraph project files (pyproject/langgraph.json/uv.lock/.agent) — only langgraph + pydantic imported. BUILT & RUN-VERIFIED (`uv run uipath run agent --file input.json` returns exact static JSON; empty `{}` also succeeds). `input.json` holds a sample DG-set payload for testing.

**Why:** demo solution needs the full agent roster to exist even though the entitlement path isn't exercised.
**How to apply:** if other STUB agents are needed, reuse this same copy-vendor-scaffold → rewrite main.py → `uipath init` recipe.
