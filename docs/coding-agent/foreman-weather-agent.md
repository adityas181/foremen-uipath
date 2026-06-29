---
name: foreman-weather-agent
description: FOREMAN Weather agent — hosted Weather MCP (markdown!) + analytic daylight + Open-Meteo fallback; BUILT & RUN-VERIFIED
metadata: 
  node_type: memory
  type: project
  originSessionId: 1afa6316-2426-4912-adfb-cace26407f41
---

`foreman-weather` (uipath-langchain coded agent, node `plan_weather`) — go/no-go outdoor work-window planner. Input `{site_id, fix_kind}` → strict 5-key output `{safe_window, weather_blockers[], access_constraints[], earliest_safe_time, error}`. BUILT & RUN-VERIFIED for MC4 (DEL-0788, "outdoor live-electrical DC"): earliest_safe_time `2026-06-25 05:30 IST`, full daylight dry+lightning-free window, current blocker `after-dark`, access_constraints include `outdoor ground mount environment`. All values fall out of live forecast, nothing hard-coded.

**Site Data Fabric fields (verified):** `Site` has `siteid, lat, lon, environment, humidity, status` — DEL-0788 → lat 28.6139, lon 77.209, environment `outdoor_ground_mount`, humidity 38. (Spec was right that Site has lat/lon, unlike the older [[foreman-datafabric-read-pattern]] note that listed only siteid/environment/humidity/status.) Reuse `_df_one` = retrieve_records + name→id from that pattern.

**Hosted Weather MCP gotchas (the big ones):**
- Server lives in folder `Shared/foremen v1`, slug `weather` (@dangahagan/weather-mcp@1.6.1). `sdk.mcp.list()` 400s "Folder key is required" — MUST pass `folder_path`. `mcp_url` field on the server = the streamable-HTTP endpoint (`.../agenthub_/mcp/<folderkey>/weather`).
- Connect with `MultiServerMCPClient({"weather":{"url",transport:"streamable_http",headers:{Authorization:Bearer <tok>}}})`; `streamable_http` works, retry `sse` on failure. `langchain_mcp_adapters` is the dep.
- **The endpoint is POST-only**, so the streamable-HTTP transport's server→client GET stream always `405`s + "reconnecting in 1000ms". Do NOT open a session per tool call — that pays the handshake/405/DELETE churn 3×. Open ONE session: `async with client.session("weather") as s: tools={t.name:t for t in await load_mcp_tools(s)}` (`from langchain_mcp_adapters.tools import load_mcp_tools`) and run search_location+get_forecast+get_lightning_activity inside it. Dropped 405s 6→2 (2 is the irreducible minimum). Same pattern applies to any UiPath AgentHub MCP.
- **MCP tools return human-readable MARKDOWN, not JSON.** Result is `[{"type":"text","text":"...md..."}]` — flatten then REGEX-parse. 12 tools; we use `get_forecast`(hourly), `get_lightning_activity`, `search_location`. get_current_conditions THROWS for non-US (NOAA-only).
- Hourly forecast: blocks `## M/D/YYYY, H:MM AM/PM` with `**Precipitation Chance:** N%`, `**Wind:** N mph`, `**Wind Gusts:** N mph`, `**Conditions:**`. Units °F / mph. Header has reliable `**Timezone:** Asia/Kolkata`.
- **Daily forecast DOES print Sunrise/Sunset but timezone-SHIFTED (~+offset twice, e.g. Delhi sunrise shown 10:55AM vs real 05:25) — UNUSABLE.** So daylight is computed ANALYTICALLY: parse IANA tz from header → tz-aware UTC instant per slot → NOAA solar-elevation > -0.833°. (Added `tzdata` dep so `zoneinfo` works on Windows; longitude/15 offset fallback.)
- Lightning markdown: `Safety Status: SAFE|CAUTION|...`, `Total Strikes: N`. Lightning-free == SAFE.
- "now" matters: forecast includes PAST hours of today, so filter slots to `>= now_utc` (datetime.now is fine in the agent node — it's normal Python, not a Workflow script).

**Auth (CRITICAL, bit us live):** the [[foreman-auth-token-gotcha]] is worse than "just comment it out". In THIS SDK version the in-process `UiPath()` does NOT auto-read/refresh `.uipath/.auth.json` — commenting out the env token gives `SecretMissingError`, leaving it gives 401 expired once it ages out (1h). A run needs a CURRENTLY-VALID `UIPATH_ACCESS_TOKEN` in `.env`. To mint one without interactive `uipath auth`: POST `https://staging.uipath.com/identity_/connect/token` with `grant_type=refresh_token`, `refresh_token` (from .auth.json), `client_id=36dea5b8-e8bb-423d-8e7b-c808df8f1c00` → fresh access_token (valid 1h); write it to `.env` + `.auth.json`. The MCP bearer is separate: code uses `UIPATH_PAT` (user set an `rt_…` PAT) or falls back to `sdk._config.secret`.

LLM = `UiPathChat(model="gpt-4.1-mini-2025-04-14")` created INSIDE node, used ONLY to phrase `safe_window`; every contract field computed deterministically with code fallback. Node never throws. Open-Meteo fallback (`/v1/forecast?...&daily=sunrise,sunset&timezone=auto&wind_speed_unit=mph`) gives structured JSON window (lightning omitted) when MCP unreachable. Test input `input.json`; run `uv run uipath run agent --file input.json --output-file out.json`.
