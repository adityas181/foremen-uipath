---
name: foreman-diagnosis-recommendation-agent
description: "FOREMAN Agent 06 diagnosis-recommendation (the brain) — built & run-verified; skill/context CG indexes, hard gate + safety floor + systemic_hint enforced in code"
metadata: 
  node_type: memory
  type: project
  originSessionId: ba4ce3ac-b079-49ff-b61b-4f126bf65110
---

`foreman-diagnosis-recommendation/main.py` (the always-on brain) is **BUILT & RUN-VERIFIED**. Single `diagnose` node, never throws (returns contract shape with non-empty `error` on failure), strict flat pydantic `GraphOutput`. Reuses the proven [[foreman-datafabric-read-pattern]] (`df_one` via `retrieve_records`+filter_group, name→id, lowercased keys) and [[foreman-root-cause-agent]]-style `UiPathChat(model="gpt-4.1-mini-2025-04-14").with_structured_output(...)` + `ContextGroundingRetriever(index_name=..., folder_path="Shared/foremen v1")`.

**Contract:** input `{perception: dict, history_match: dict, asset_id, site_id, worker_text}` → output flat `{skill_hit, skill_status, match_type(exact|related|new), root_cause, confidence, alternatives_ruled_out[], recommendation, citations[], what_differs, fingerprint{equipment_class,component,failure_mode,capacity_band,environment}, safety(normal|critical), systemic_hint, error}`.

**Verified live (DefaultTenant, folder `Shared/foremen v1`):**
- Two Context Grounding indexes: **`skill`** (bucket foreman-skill) and **`context`** (bucket foreman-context). **As of 2026-06-24 the user ingested the SK-* cards into `skill`** → full hard-gate match now VERIFIED end-to-end (was empty earlier → degraded to null/new, which also proved graceful degradation). The `context` retriever returns `doc.metadata['source']` = **exact filename** (e.g. `mc4-connector-install-spec.pdf`, `pv-dc-arc-safety-bulletin.pdf`, `connector-cross-mating-warning.pdf`) — `citations` is built ONLY from those (never invented).

**Real input shape (what the agent actually receives from vision — NOT the clean spec shape):** top-level `issue_text_received` (worker text), `perception`, `history_match`, `history_logged*`. **`asset_id`/`site_id` are NOT top-level — they live in `history_match.matched_record.assetid/siteid` (lowercase).** The node now resolves asset_id/site_id from matched_record and uses `issue_text_received` as the worker_text fallback (GraphInput has both `worker_text` and `issue_text_received` fields; pydantic ignores the other extra vision keys). Do NOT rewrite input.json to add top-level keys — handle it in code.

**VERIFIED full MC4 run (real input, no top-level asset_id):** skill_hit `SK-pv-mc4-connector-burn`, skill_status `candidate`, match_type `related`, confidence 0.85, alternatives_ruled_out `[cross-mating, water ingress, module hot-spot]` (the matched card's Differential entries — prompt steers away from unrelated-equipment-class rule-outs), citations all three expected files, fingerprint `pv_array/MC4 connector/exposed_wiring/outdoor_rated/outdoor` (capacity_band+environment resolve because asset_id is derived → Asset read), safety critical, systemic_hint true, error "".
- `Asset` fields flattened lowercase: `assetid,type,vendor,batch,spec,siteid,installed`. `AssetIssueHistory` mixed camelCase: `assetId,siteId,issueDate,faultType,component,severity,description,resolution,status,batchId,technician,recurrenceCount,mediaPath` (+ optional `resolvedDate`) — normalize to lowercase keys.
- MC4 fixture asset **`AST-SCB-DEL-0788`** = solar_connector / HelioVolt / batch **HV-BATCH-19** / outdoor_rated; has prior `melted_connector` history + sibling assets (0791,0802) same batch → `systemic_hint=true`.

**Enforced in CODE after the LLM call (so the contract holds even if the model drifts):**
1. **Hard gate** — accept `skill_hit` only if it's an `SK-*` id that literally appears in the returned skill cards (regex `\bSK-[A-Za-z0-9-]+`); else null + `match_type="new"`.
2. **Citations** — intersect the LLM's cited names with the EXACT `context` source filenames actually returned; fallback to top-3 returned sources if the model named none.
3. **systemic_hint** — HISTORY-derived only (prior fault same asset OR same-batch siblings); NO graph read here (that's the fleet agent).
4. **Safety floor** — `critical` for arc/fire/exposed-conductor/HV terms, but **negation-aware** (`_hazard_present` skips terms inside a ~22-char window containing `no `/`not `/`without`/`n't`/`free of`/`absence of`/`no sign`). Bug caught in test: "casing intact, **no exposed conductors**" was falsely flooring cosmetic faults to critical — the negation guard fixed it (benign→normal, MC4→critical).

**Verified runs:** MC4 (loose_connection+exposed_wiring high) → safety critical, systemic true, fingerprint `pv_array/MC4 connector/loose_connection/outdoor_rated/outdoor`, citations `[mc4-connector-install-spec.pdf, pv-dc-arc-safety-bulletin.pdf]`, conf 0.95, error "". Benign (cosmetic yellowing, unknown asset `AST-DOES-NOT-EXIST-9999`) → safety normal, systemic false, match new, fingerprint degrades to `unknown`, error "" (no crash). `pyproject` deps already had `uipath-langchain[bedrock,vertex]` + `uipath-langchain-client[bedrock]`; `uipath init` introspects the graph fine.

Note: `.env` `UIPATH_ACCESS_TOKEN` was the SAME token as `.uipath/.auth.json` and still valid this session — CLI needs the env token set (commenting it out broke `uipath` CLI auth), so this run did NOT need the [[foreman-auth-token-gotcha]] workaround.
