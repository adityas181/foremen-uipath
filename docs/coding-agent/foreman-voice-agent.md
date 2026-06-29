---
name: foreman-voice-agent
description: Two-way Twilio voice-approval agent (make_brief→place_call) + FastAPI webhook; BUILT & verified (dry_run + full webhook conversation)
metadata: 
  node_type: memory
  type: project
  originSessionId: 84a42de8-78cd-4dbc-91ed-90e7ed90c590
---

FOREMAN Voice agent in `foreman-voice/` — places a TWO-WAY outbound Twilio VOICE call to a site manager for a spoken approval and returns decision (approved/hold/no_answer/pending).

Two files: `main.py` (entry `agent`, compiled `graph`; nodes `make_brief`→`place_call`) and `voice_server.py` (FastAPI webhook, port 8090, in-memory dict keyed by token, 3-turn convo /prepare→/voice→/respond→/decide + /decision poll). Creds env-first then UiPath Assets in "Shared": Twilio-Account-Sid/Auth-Token/From-Number, Voice-Webhook-Url. `truststore.inject_into_ssl()` at top. Lazy SDK so local .env runs need no UiPath. Never throws — Output(error=...) on failure. Safety: HOLD words checked FIRST, ambiguous/silent→hold, never auto-authorise (`actionOnEmptyResult="true"` so silence still hits /decide).

LIVE-VERIFIED end-to-end: real two-way Twilio call placed from +13203078290 to +917225865778 over a cloudflared tunnel → manager answered, heard live-LLM brief + recommendation, said "yes" → decision="approved", call_sid returned, errors empty. Also verified: dry_run (no call), all webhook turns, approve/hold/ambiguous/silent/mixed classification, missing-creds clean-error path.

Twilio acct (hackathon): account is FULL (not trial) so it can call any number; the ONLY voice-capable owned number is +13203078290 (the WhatsApp sandbox +14155238886 CANNOT place voice). cloudflared was NOT installed — grab the binary from github cloudflare/cloudflared releases (windows-amd64.exe) and run `cloudflared tunnel --url http://localhost:8090`.

**Non-obvious gotcha (differs from [[foreman-auth-token-gotcha]]):** `UiPathChat` (uipath-langchain LLM client) REQUIRES `UIPATH_ACCESS_TOKEN` in env via PlatformSettings — it does NOT read the auto-refreshing `.uipath/.auth.json` like the `UiPath()` SDK does. So make_brief's LLM needs a fresh token (`uipath auth`); the SDK Assets read tolerates .auth.json. They pull auth from different places. make_brief degrades to first ~300 chars of summary if the token is missing/expired, so the agent still runs.

DEPLOY gotchas (hit while shipping foreman-voice-v3 to Orchestrator Tenant Processes Feed via `echo 0 | uv run uipath publish`):
- **case_id with `+`/`:` breaks the webhook token.** Supervisor sends `case_id="whatsapp:+91..."` → used as the token in `/voice?token=...`. A `+` in a query string decodes to a SPACE → SESSIONS miss → "Sorry, this call is not configured." FIX: `quote(token, safe='')` everywhere the token enters a URL — in main.py's voice_url AND in voice_server's `/respond` & `/decide` action URLs. (`voice_server.py` is a long-running process — edits need a RESTART to take effect; main.py reloads each `uipath run`.)
- **Asset folder mismatch.** main.py reads `Voice-Webhook-Url` from `folder_path="Shared"` (root). Editing the asset in `Shared/foremen v1` (subfolder) does nothing — keep the asset the agent reads in ROOT Shared.
- **Invalid voice/language → Twilio "an application error has occurred."** Supervisor sends `voice="Polly.aditi"` (wrong case; valid is `Polly.Aditi`) and `language="en-EN"` (not a real code). Either breaks the `<Say>` TwiML → call dies before /respond → decision=no_answer. Robust fix (NOT yet applied — user paused it): normalize Polly casing + DROP the `language` attr for Polly voices in both `_say` fns. With valid `Polly.Aditi`+`en-IN` it works.
- **Speech got cut off** → `<Gather speechTimeout="auto">` ends on first pause; set a fixed `speechTimeout` (used "4"s) + `timeout="6"`.
- **Greeting name suppressed** when `to_role` is generic ("the manager"); pass an actual name to hear "Hello Ritesh".
- Ephemeral `trycloudflare` URL changes every restart → update the ROOT-Shared asset each time. Cloud Serverless CAN reach trycloudflare (dashboard ingest got 200 from cloud IP), so past "Name or service not known" failures were always STALE/dead tunnel URLs, not egress. `.env` is NOT bundled into the package (verified by unzipping the .nupkg) — don't blame bundled .env for stale values.
- Turn 2 is now a FIXED demo script (`TURN2_LINE` constant), not the LLM opener/recommendation. Bump `pyproject` version (0.0.1→0.0.2) before re-publish or you get `409 Package already exists`.

**Why:** reuse the make_brief fallback + safety-floor pattern across any voice/HITL agent; remember UiPathChat≠SDK for auth, and the webhook token / asset-folder / Polly-voice / gather-timeout traps before the next deployed two-way call.
