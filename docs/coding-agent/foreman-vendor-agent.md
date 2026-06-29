---
name: foreman-vendor-agent
description: "FOREMAN Vendor agent — STUB (not in MC4); static no-defect/no-recall vendor verdict, no DF/LLM/external; BUILT & RUN-VERIFIED"
metadata: 
  node_type: memory
  type: project
  originSessionId: a79d452a-ea16-464d-a9a5-9512bd100219
---

foreman-vendor is a STUB agent (uipath-langchain), present for completeness, NOT invoked in the MC4 demo. Built on the same template as [[foreman-entitlement-agent]].

INPUT: { vendor, batch_id, root_cause } (Input extra="ignore", all tolerant — input ignored).
OUTPUT (extra="forbid"): { known_defect_or_recall: bool, rma_path: str|null, approved_replacement_source: str|null, supplier_escalation: str|null, error: str }.
STATIC RETURN regardless of input: known_defect_or_recall=false, three string fields null, error="" — "no confirmed supplier defect/recall; field workmanship is the lead cause." Async, no Data Fabric/LLM/external, never throws.

Single-node StateGraph (START→vendor_stub→END), `graph` exposed. BUILT & RUN-VERIFIED in d:\UIpath\foreman-vendor.

Gotchas: `uipath init` takes NO positional entrypoint (just `uipath init`); runnable entrypoint is named `agent` not `main.py` (`uipath run agent`). IDE input=/output= warnings on StateGraph(...) are type-stub false positives. I/O schema lives in entry-points.json (uipath.json is pack/bindings config only).
