---
name: foreman-safety-agent
description: "FOREMAN Safety agent — the hard safety gate; built & run-verified; floors safety_critical + can_block_auto_resolve in code, citations only from `context` retrieval"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbe5b2ed-995f-452b-bf10-c5f25ea95c66
---

FOREMAN `foreman-safety` coded agent (uipath-langchain), folder "Shared/foremen v1". The hard SAFETY GATE. BUILT & RUN-VERIFIED.

**Contract** — input `{fault_type, component, severity, equipment_class, skill_hit|null, engine_safety}` → flat output `{safety_critical, protocol, standard_clause[], blockers[], citations[], can_block_auto_resolve, error}`.

**Reads:** Context Grounding `context` (PRIMARY → clauses + EXACT citation filenames) and `skill` (OPTIONAL, only if skill_hit set, to confirm safety_protocol). NO Data Fabric, NO Neo4j. Mirrors [[foreman-diagnosis-recommendation-agent]] structure (ContextGroundingRetriever, UiPathChat gpt-4.1-mini, clients inside node, never-throw).

**Code-enforced (not LLM-trusted):** `safety_critical` floored true when engine_safety=="critical" OR negation-aware hazard scan hits arc/fire/exposed-energised-conductor/HV/fall/derailment/pressure (same `_hazard_present` window+NEG_CUES trick as the diagnosis agent, so "no exposed conductor" does NOT floor). `can_block_auto_resolve = safety_critical`. `citations` filtered to exact `metadata['source']` names the `context` retrieval returned (audit fallback = top 3 if LLM cites none).

**MC4 acceptance PASSED** ({exposed_wiring, MC4 connector, high, pv_array, SK-pv-mc4-connector-burn, critical} → safety_critical=true, no-load isolation+LOTO protocol, NEC 690.11 in clauses, both required blockers, pv-dc-arc-safety-bulletin.pdf cited, can_block_auto_resolve=true). Non-hazard + negation controls correctly return safety_critical=false.

**Why:** completes the 5th of the FOREMAN foremen; Supervisor force-invokes it whenever engine.safety=="critical" (safety floor).
**How to apply:** auth uses live .env UIPATH_ACCESS_TOKEN — uipath-langchain's PlatformSettings REQUIRES the token in env (unlike platform UiPath() which falls back to .auth.json per [[foreman-auth-token-gotcha]]); only comment it out if actually expired, else restore from .uipath/.auth.json.
