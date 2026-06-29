# Binding real UiPath agents to the FOREMAN UI (real-time)

The UI renders **entirely off one normalized event contract** — `CaseEvent` in
[`src/types.ts`](src/types.ts). The demo replays scripted `CaseEvent`s; "going
live" just means feeding it **real** `CaseEvent`s instead. Nothing in the tabs
changes.

```
 UiPath Automation Cloud                          your infra                 browser
┌───────────────────────────────┐        ┌───────────────────────┐     ┌──────────────┐
│  Maestro Case (conductor)      │        │   view-backend        │     │  React UI    │
│   └ stage: Perceive            │        │   (FastAPI/Node)      │     │              │
│      └ Coded Vision Agent  ────┼──emit──▶  POST /ingest/{case}  │     │  Zustand     │
│         (OpenAI + LangGraph)   │  HTTPS │   holds case state    │     │  store       │
│      └ stage: Investigate ─────┼──emit──▶  broadcast ───────────┼─WS─▶│  ingestEvent │
│   (RPA already dropped the     │        │                       │     │  → tabs      │
│    mp4 + text into the bucket) │        └───────────────────────┘     └──────────────┘
└───────────────────────────────┘
```

Three layers, one shared shape (`CaseEvent`):

| Layer | File | Job |
|---|---|---|
| **Agent** (in UiPath) | [`server/foreman_vision_agent.py`](server/foreman_vision_agent.py) | runs the logic; calls `emit(case_id, event)` at each step |
| **View-backend** (your infra) | [`server/view_backend.py`](server/view_backend.py) | receives events, fans them out over WebSocket, keeps a snapshot for late clients |
| **UI** (this repo) | [`src/store/liveFeed.ts`](src/store/liveFeed.ts) + `ingestEvent` | subscribes to the socket, applies each event into the store — same reducer the demo uses |

## Why this is *real-time* (and simple)

For a **coded** agent you own the code, so you don't need webhooks for
fine-grained progress — you just `emit()` a `CaseEvent` the instant each thing
happens (vision done, root cause done, risk scored). The view-backend pushes it
to the browser over an open WebSocket. Latency = one HTTP POST + one socket
frame ≈ tens of milliseconds.

(Orchestrator webhooks — `job.*`, `task.*` — are still useful for things you
*don't* control, like "an RPA job finished" or "an Action Center task was
raised". Point those at the same `/ingest` endpoint and translate them to
`CaseEvent`s. But the agent's own emits are what make the crew/console feel live.)

## Your exact scenario, step by step

You said: mp4 + text are already in the bucket (the WhatsApp/RPA intake is built).
So the flow is:

1. The **Maestro Case** enters the *Perceive* stage and **starts & waits for** your
   coded Vision agent, passing `{ case_id, site_id, media_path, text }`
   (`media_path` = the bucket file your RPA step downloaded).
2. The agent ([`foreman_vision_agent.py`](server/foreman_vision_agent.py)):
   - emits `agent.running {agent:"vision"}` → the Crew/Console show Vision "thinking".
   - samples frames from the mp4 (OpenAI vision takes **images**, so extract
     frames with OpenCV) and sends them + the worker text to `gpt-4o` with
     `with_structured_output(Perception)`.
   - emits `perception.ready {...}` and `agent.completed {agent:"vision", run:{...}}`
     → the Perception card + Vision finding render.
3. The agent then does root cause (`with_structured_output(RootCause)`) and emits
   `agent.completed {agent:"rootcause"}`, `risk.scored {risk}`, `investigation.ready {...}`
   → the merged recommendation + risk meter animate in.
4. The browser, connected to `/ws`, applies each event through `ingestEvent` — the
   **same** reducer the demo replay uses — so the Console, Crew, and Live-activity
   tabs update live, identically to the scripted run.

Add more agents (entitlement, SLA, fleet) the same way: each is a node that
`emit()`s its `agent.running` / `agent.completed` events. Action Center gates →
emit `task.raised` / `task.answered`. BPMN writes → emit `action.produced`.

## Run it locally (end to end)

```bash
# 1) view-backend
cd server
pip install -r requirements.txt
FOREMAN_INGEST_SECRET=dev-secret uvicorn view_backend:app --port 8000

# 2) point the UI at it  (in the repo root)
cp .env.example .env
#   set:  VITE_FEED_MODE=live
npm run dev          # the header now shows ● LIVE instead of replay controls

# 3) run the agent (locally, or deployed in UiPath)
cd server
export FOREMAN_BACKEND_URL=http://localhost:8000 FOREMAN_INGEST_SECRET=dev-secret OPENAI_API_KEY=sk-...
python foreman_vision_agent.py     # watch the UI fill in live
```

Switch back to the scripted demo any time with `VITE_FEED_MODE=demo`.

## The CaseEvent payloads you'll emit (match `src/types.ts`)

```jsonc
{ "kind": "case.opened",   "case": { "case_id":"CASE-0916", "site_id":"DEL-0473", "title":"...", "stage":"intake" } }
{ "kind": "stage.entered", "stage": "perceive" }
{ "kind": "agent.running", "agent": "vision" }
{ "kind": "perception.ready", "perception": { "corrosion": {"present":true,"severity":"high"},
                                              "generator_audio": {"anomaly":"knock","confidence":0.86},
                                              "issues": ["rf_cable_corrosion"] }, "asset_note": "..." }
{ "kind": "agent.completed", "agent": "rootcause", "run": { "headline":"spec defect", "confidence":0.9, "citations":["..."] } }
{ "kind": "risk.scored", "risk": 0.82 }
{ "kind": "investigation.ready", "investigation": { "root_cause":"...", "confidence":0.9, "risk_score":0.82, "recommendation":"...", "systemic":false, "fleet_affected":0, "alternatives_ruled_out":["..."] } }
{ "kind": "log", "entry": { "ts":"14:31:02", "stage":"investigate", "source":"Root-cause", "text":"...", "tone":"agent" } }
```
`agent` ∈ `supervisor|vision|entitlement|sla|rootcause|fleet` · `stage` ∈ `intake|perceive|confirm|investigate|escalate|resolve|close`.

## Production notes

- **Public endpoint**: the agent (running in UiPath cloud) needs to reach your
  view-backend over HTTPS — deploy it (Render/Fly/a VM) or tunnel
  (`cloudflared tunnel --url http://localhost:8000`).
- **Auth**: `/ingest` checks the `x-foreman-secret` header. Use a real secret.
- **OpenAI in UiPath**: either call OpenAI directly (as shown) or route through
  UiPath's **LLM Gateway / AI Trust Layer** for governance.
- **Reconnect/replay**: the backend keeps a per-case event log and replays it as
  a `snapshot` when a browser connects, so a late/refreshed client catches up.
  For multi-instance backends, move that log to Redis.
```
