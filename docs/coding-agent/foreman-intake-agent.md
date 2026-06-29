---
name: foreman-intake-agent
description: "FOREMAN Intake gatekeeper agent — contract, design, and verified build status"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fdd8a18-4c1d-4e3d-8042-d24dce0f1f4c
---

`foreman-intake` (d:\UIpath\foreman-intake) is the FOREMAN front-door gatekeeper: runs once per WhatsApp message and decides if a fault report is COMPLETE before the rest of the pipeline. Built by converting the copied `foreman-entitlement` project. **Built & verified live** (2026-06-22) against staging `hackathon26_457/DefaultTenant`.

**Contract.** Input: `latest_message:str`, `has_media:bool`, `current_issue_text:str=""`, `current_asset_id:str=""`. Output: `complete:bool`, `issue_text:str`, `asset_id:str` (validated or ""), `site_id:str`, `asset_verified:bool`, `missing:list[str]` (subset of "media","issue","asset"), `reply_message:str` ("" if complete). Complete = media (the bool, NEVER inferred from text) AND a real issue AND an asset that EXISTS in Data Fabric.

**Design (matches the spec division of labour):** LLM does EXTRACTION (refine issue, pull asset candidate) + PHRASES the reply; asset VALIDATION is in CODE. Asset lookup reuses the verified [[foreman-datafabric-read-pattern]] `df_one` (retrieve_records + name→id, field `assetid`→`siteid`); explicit id accepted only if the record exists, NL (type+site) accepted only on a single confident match, never invents an asset. LLM = `UiPathChat(model="gpt-4.1-mini-2025-04-14")` from `uipath_langchain.chat` with `.with_structured_output(Extraction)` — same as [[foreman-root-cause]] (NOT the boilerplate's `UiPathChatAnthropicBedrock`; chosen for proven structured-output support). `UiPath()`/LLM built inside the node so `uipath init` can import. Decision logic factored into `evaluate_intake(state, *, extract, validate, compose_reply)` with injected deps → offline deterministic tests.

**Tests:** `test_intake.py` — the 5 required scenarios, fully offline (fakes injected), runnable `./.venv/Scripts/python.exe test_intake.py` (5/5 pass) or pytest. Live smoke verified: `AST-PDU-DEL-0512`→complete, site_id `DEL-0512`; unknown id→not complete, LLM reply asks to re-check.

**Commands.** Test: `uv run python test_intake.py`. Run live: `uv run uipath run agent '{"latest_message":"...","has_media":true}'` (auto-loads `.env`; harmless `Resource overwrites config file not found: __uipath\uipath.json` warning). Schema regen after I/O changes: `uv run uipath init`. Publish to the FOREMAN folder: `uv run uipath deploy --folder "Shared/foremen v1"` (= `uipath pack` + `uipath publish -f "Shared/foremen v1"`).
