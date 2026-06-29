# Going live — wiring the real Maestro case into the FOREMAN UI

This is the end-to-end recipe. The UI renders entirely off the `CaseEvent`
contract ([`src/types.ts`](../src/types.ts)); "live" just means feeding it real
events instead of the scripted demo. Nothing in the tabs changes.

## Files in this folder

| File | Role |
|---|---|
| [`foreman_emit.py`](foreman_emit.py) | **The SDK every coded agent imports.** `Emitter(...)` + one typed method per `CaseEvent`. Never raises; normalises risk to 0..1. |
| [`view_backend.py`](view_backend.py) | The bridge. `POST /ingest/{case_id}` → fan out over `/ws`. Now also has `/register`, `/webhook/orchestrator`, `/webhook/actioncenter`. |
| [`replay_trace.py`](replay_trace.py) | Drives the **whole UI from a real Maestro trace export** — no UiPath needed. Doubles as the exact node→event spec. |
| `foreman_vision_agent.py` | The original inline-emit example (vision + root-cause only). |

## The one decision you already made

- **Routing key** (what the UI buckets a case by) = the **Maestro instance id**.
  It is ambient in every agent / RPA job / API workflow, and it is the *only* id
  webhooks carry — so all event sources agree without a server-side lookup.
- **Displayed id** (what humans see) = your **external key** from the payload —
  sent inside the first `case.opened` event, e.g. `case_id="CASE-DEL-0788"`.

Verified: replaying your trace posts 45 events under instance
`a0a5b80b-…` while the card displays `CASE-DEL-0788`.

---

## Step 0 — See it work right now (2 minutes, no UiPath)

```bash
# backend
cd server
pip install -r requirements.txt
FOREMAN_INGEST_SECRET=dev-secret uvicorn view_backend:app --port 8000

# UI in live mode (repo root, new terminal)
cp .env.example .env        # set VITE_FEED_MODE=live  (VITE_FEED_WS_URL=ws://localhost:8000/ws)
npm run dev

# replay your real trace into it (new terminal)
cd server
FOREMAN_BACKEND_URL=http://localhost:8000 FOREMAN_INGEST_SECRET=dev-secret \
  python replay_trace.py "C:/Users/Dell/Downloads/trace-1782457166681.json"
```

The dashboard fills in across all six stages: Intake → Perceive → Investigate
(dynamic crew + fleet blast radius) → Human Safety Review → Voice Escalation →
Close (audit + learned skill). That proves the entire UI path.

---

## Step 1 — Instrument the real coded agents

In each LangGraph node, import the SDK and emit at entry/exit. `replay_trace.py`
is the line-by-line spec — these are the same calls, just with live data instead
of trace data.

```python
from foreman_emit import Emitter

def perceive(state):
    fm = Emitter(case_id=state["instance_id"])     # instance id passed in by Maestro
    fm.stage("perceive"); fm.agent_running("vision")
    perception = run_vision(state)                  # your real work
    fm.perception_ready({"findings": [...], "issues": [...]},
                        asset_note=f'{state["site_id"]} · vision')
    fm.agent_completed("vision", headline="exposed_wiring (high)", confidence=0.95)
    return {...}
```

Node → event map (mirrors your trace):

| Your node | Emit |
|---|---|
| `intake` | `case_opened(case_id=external_key, …)`, `message`, `media_received`, `stage("intake")` |
| `perceive` | `stage("perceive")`, `agent_running/completed("vision")`, `perception_ready`, `skill_matched` |
| `supervise` | `stage("investigate")`, `agent_running("supervisor")`, `agent_assembled(...)` per crew member |
| `diagnose` | `agent_running/completed("rootcause")`, `risk_scored`, `investigation_ready` |
| `blast` | `agent_running/completed("fleet")`, `fleet_ready(output["fleet"])` *(already FleetView-shaped)* |
| `assess` / `check_parts` / `plan_weather` | `log(...)` (no dedicated UI card) |
| `make_brief` + `place_call` | `task_raised`, `call_started/connected/line/decision`, `task_answered` |
| `dispatch` | `action_produced({type:"work_order", …})` |
| close / email | `audit_ready`, `skill_written`, `skill_promoted`, `feedback`, `closed()` |

**Pass the instance id into every agent.** In the Maestro case, set a variable to
the instance id and map it onto each agent's `instance_id` input (alongside your
external `case_id`). Every `Emitter` for one case must use the same routing key,
or the UI splits it into two cards.

> Risk: the UI RiskMeter is 0..1 (0.70 = "call" threshold). The SDK normalises —
> pass `84` or `0.84`, both render as 0.84.

## Step 2 — Cover the parts you don't emit from (RPA / API workflow / Action Center)

Two options, mix freely:

- **A — emit from the orchestrating agent** (simplest): bracket the invoke with
  `fm.log(...)` / `fm.media_received(...)` / `fm.action_produced(...)`. For the
  `foreman-downloadandsave` API workflow you can also add an HTTP step that POSTs
  `media.received` straight to `/ingest/{instance_id}`.
- **B — webhooks → translator**: point Orchestrator `job.*` at
  `POST /webhook/orchestrator` and Action Center `task.*` at
  `POST /webhook/actioncenter`. They convert to `CaseEvent`s and broadcast under
  the instance-id key. **Inspect a real webhook delivery first** and adjust the
  field paths in `_dig(...)` — UiPath payload field names vary by tenant/version.

Optionally call `POST /register {instance_id, case_id, site_id, title}` at intake
so webhook-only events show a friendly title.

## Step 3 — Make the backend reachable from UiPath cloud

The cloud agents/webhooks need HTTPS to your backend:

- durable: deploy via [`../render.yaml`](../render.yaml) (Render/Fly/VM), or
- demo: `cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`).

Set a **real** `FOREMAN_INGEST_SECRET` (not `dev-secret`) and use it in every
agent's env. Point the UI's `VITE_FEED_WS_URL` at `wss://<your-host>/ws`.

## Step 4 — Production notes

- **Multi-instance backend** → move the in-memory `CASES` dict to Redis
  ([`view_backend.py`](view_backend.py) `CASES`).
- **Late/refreshed clients** → already handled: the backend replays a per-case
  snapshot on WS connect.
- **Idempotency** → emits can retry; give events stable ids if you ever see dupes.
- **LLM governance** → your agents already call through `UiPathChat` (LLM Gateway
  / AI Trust Layer). Keep it.
