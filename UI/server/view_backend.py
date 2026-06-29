"""
FOREMAN view-backend — the bridge between your UiPath case and the UI.

Endpoints
  POST /ingest/{case_id}        ← coded agents push CaseEvents here (foreman_emit)
  WS   /ws                      → the React UI subscribes; events fan out live
  POST /register                ← map a Maestro instanceId → friendly case_id
  POST /webhook/orchestrator    ← Orchestrator/Maestro job.* webhooks → CaseEvent
  POST /webhook/actioncenter    ← Action Center task.* webhooks → CaseEvent
  GET  /healthz

Routing key = the Maestro INSTANCE ID (ambient everywhere, and the only id
webhooks carry). The friendly external key is shown via the case.opened payload,
or registered with POST /register so webhook-translated events show a nice title.

Run:
    pip install -r requirements.txt
    FOREMAN_INGEST_SECRET=dev-secret uvicorn view_backend:app --port 8000
Public endpoint (so UiPath cloud can reach it):
    cloudflared tunnel --url http://localhost:8000     (or ngrok http 8000)
"""
import os
import time
import json
import asyncio
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware


def _load_env_file(path: str) -> None:
    """Tiny dependency-free .env loader (python-dotenv isn't installed here). Reads
    KEY=VALUE lines from server/.env so you don't have to export env vars on every
    launch. Inline/real env vars win (setdefault never overrides them)."""
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass
    except Exception as e:  # never let config loading crash startup
        print("view_backend: .env load skipped:", e)


_load_env_file(os.path.join(os.path.dirname(__file__), ".env"))

SECRET = os.environ.get("FOREMAN_INGEST_SECRET", "dev-secret")
# Phase 2 voice audio: the Twilio auth token lets THIS backend fetch a call
# recording on the browser's behalf (account sid arrives in the proxy URL), so the
# mp3 URL the UI plays never carries credentials.
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")

app = FastAPI(title="FOREMAN view-backend")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# In-memory truth: per-case ordered event log (the "snapshot" for late clients).
# Swap for Redis if you run multiple backend instances.
CASES: dict[str, list[dict]] = {}
CLIENTS: set[WebSocket] = set()
# instanceId (routing key) -> friendly external case_id, set via /register.
CASE_NAMES: dict[str, str] = {}


async def broadcast(msg: dict) -> None:
    dead = []
    for ws in CLIENTS:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)


def _stamp_local_time(event: dict) -> dict:
    """Re-stamp an event's wall-clock fields with THIS backend's local time.

    Coded agents run in UiPath cloud (UTC), so the HH:MM strings they emit are in
    UTC and don't match the operator's clock (e.g. 19:15 UTC shows while the wall
    clock reads 00:45 IST — and it even crosses midnight, so a client can't safely
    convert a bare HH:MM string). The backend runs in the viewer's timezone, so we
    stamp on ingest. Because the stamp is stored in the per-case snapshot, a
    reconnecting browser replays the correct local times instead of collapsing the
    whole history to 'now'.
    """
    kind = event.get("kind")
    if kind == "log":
        entry = event.get("entry")
        if isinstance(entry, dict):
            entry["ts"] = time.strftime("%H:%M:%S")
    elif kind == "message":
        msg = event.get("message")
        if isinstance(msg, dict):
            msg["ts"] = time.strftime("%H:%M")
    elif kind == "call.decision":
        dec = event.get("decision")
        if isinstance(dec, dict):
            dec["at"] = time.strftime("%H:%M")
    elif kind == "case.opened":
        case = event.get("case")
        if isinstance(case, dict) and case.get("opened_at"):
            case["opened_at"] = time.strftime("%H:%M")
    return event


async def record_and_broadcast(case_id: str, event: dict) -> int:
    """Append one CaseEvent to the case log and push it to every browser."""
    _stamp_local_time(event)
    CASES.setdefault(case_id, []).append(event)
    await broadcast({"case_id": case_id, "event": event})
    return len(CASES[case_id])


@app.post("/ingest/{case_id}")
async def ingest(case_id: str, event: dict, x_foreman_secret: str = Header(default="")):
    """Coded agents call this for every CaseEvent. `event` must match the UI's
    CaseEvent union (kind + payload) — see src/types.ts."""
    if x_foreman_secret != SECRET:
        raise HTTPException(status_code=401, detail="bad secret")
    count = await record_and_broadcast(case_id, event)
    return {"ok": True, "count": count}


@app.post("/register")
async def register(body: dict, x_foreman_secret: str = Header(default="")):
    """Tell the backend the friendly id for an instance. Optional, but lets
    webhook-translated events carry a readable title.
        { "instance_id": "a0a5b80b-...", "case_id": "CASE-DEL-0788",
          "site_id": "DEL-0788", "title": "MC4 connector · DEL-0788" }"""
    if x_foreman_secret != SECRET:
        raise HTTPException(status_code=401, detail="bad secret")
    inst = str(body.get("instance_id") or body.get("instanceId") or "")
    if not inst:
        raise HTTPException(status_code=400, detail="instance_id required")
    CASE_NAMES[inst] = str(body.get("case_id") or inst)
    # Seed a case.opened so the card shows the friendly fields immediately.
    case_fields = {k: v for k, v in body.items() if k not in ("instance_id", "instanceId")}
    await record_and_broadcast(inst, {"kind": "case.opened", "case": case_fields})
    return {"ok": True}


# ── webhook translators ───────────────────────────────────────────────────────
# UiPath webhook payload field names vary by product/version. These readers are
# deliberately tolerant — adjust the field paths to match YOUR tenant's payloads
# (inspect a real delivery first with `print(await request.json())`).

def _dig(d: dict, *paths: str, default=None):
    """First present value among dotted paths, e.g. _dig(p, 'Job.Key', 'job.id')."""
    for path in paths:
        cur = d
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def _resolve_case(payload: dict, query_case: str | None) -> str:
    """Routing key for a webhook = the Maestro instance id it references.
    Falls back to ?case= override, then any job/task key so events still group."""
    return str(
        query_case
        or _dig(payload, "InstanceId", "instanceId", "Reference",
                "SpecificContent.case_id", "Job.Reference")
        or _dig(payload, "Job.Key", "Job.Id", "Task.Id", "Id")
        or "unknown"
    )


@app.post("/webhook/orchestrator")
async def webhook_orchestrator(request: Request, case: str | None = None):
    """Orchestrator/Maestro job webhooks (job.started/job.completed/job.faulted)
    for the RPA jobs + API workflows you don't emit from directly."""
    payload = await request.json()
    case_id = _resolve_case(payload, case)
    typ = str(_dig(payload, "Type", "type", "EventType", default="")).lower()
    name = _dig(payload, "Job.ReleaseName", "Job.Name", "ProcessName", "Name", default="job")

    if "fault" in typ or "error" in typ:
        await record_and_broadcast(case_id, {"kind": "log", "entry": {
            "ts": "", "stage": "resolve", "source": str(name),
            "text": f"RPA job faulted: {name}", "tone": "danger"}})
    elif "complet" in typ or "success" in typ or "finish" in typ:
        # A finished downstream write → a produced artifact on the Audit tab.
        await record_and_broadcast(case_id, {"kind": "action.produced", "artifact": {
            "type": "work_order", "id": str(_dig(payload, "Job.Key", "Job.Id", default=name)),
            "title": f"{name} completed",
            "fields": {"job": str(name), "status": "completed"}, "external": True}})
    else:  # started / running
        await record_and_broadcast(case_id, {"kind": "log", "entry": {
            "ts": "", "stage": "resolve", "source": str(name),
            "text": f"RPA job started: {name}", "tone": "info"}})
    return {"ok": True, "case_id": case_id, "type": typ}


@app.post("/webhook/actioncenter")
async def webhook_actioncenter(request: Request, case: str | None = None):
    """Action Center task webhooks (task.created / task.completed) — your Human
    Safety Review (SimpleApprovalApp) gate."""
    payload = await request.json()
    case_id = _resolve_case(payload, case)
    typ = str(_dig(payload, "Type", "type", "EventType", default="")).lower()
    task_id = str(_dig(payload, "Task.Id", "TaskId", "Id", default="task"))

    if "complet" in typ or "answer" in typ or "finish" in typ:
        answer = str(_dig(payload, "Task.Data.action", "Action", "Outcome", "Data.action",
                          default="approved"))
        by = _dig(payload, "Task.LastModifierName", "AssignedToUser.Name", "ModifiedBy")
        ev = {"kind": "task.answered", "taskId": task_id, "answer": answer}
        if by:
            ev["by"] = str(by)
        await record_and_broadcast(case_id, ev)
    else:  # created / assigned
        prompt = str(_dig(payload, "Task.Title", "Title", "Task.Data.prompt",
                          default="Human Safety Review — authorize escalation?"))
        await record_and_broadcast(case_id, {"kind": "task.raised", "task": {
            "id": task_id, "kind": "approve_call", "prompt": prompt,
            "options": ["Approve", "Reject"], "status": "pending"}})
    return {"ok": True, "case_id": case_id, "type": typ}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    CLIENTS.add(websocket)
    # Replay current truth so a freshly-connected browser catches up instantly.
    for case_id, events in CASES.items():
        await websocket.send_text(
            json.dumps({"type": "snapshot", "case_id": case_id, "events": events})
        )
    try:
        while True:
            await websocket.receive_text()  # keepalive pings; nothing to read
    except WebSocketDisconnect:
        CLIENTS.discard(websocket)


# ── Phase 2: voice call recording (Twilio recordingStatusCallback + audio proxy) ──
@app.post("/twilio/recording")
async def twilio_recording(request: Request, case_id: str = "", case: str = ""):
    """Twilio POSTs here the moment a call recording is ready (the voice agent sets
    this as recording_status_callback). We broadcast call.recording with a proxy URL
    the browser can play — the audio is fetched (with the Twilio token) by the
    /recording proxy below, so credentials never reach the client."""
    try:
        form = await request.form()
    except Exception:
        form = {}
    cid = (case_id or case or form.get("case_id") or "").strip()
    acct = (form.get("AccountSid") or "").strip()
    rec_sid = (form.get("RecordingSid") or "").strip()
    status = (form.get("RecordingStatus") or "completed").strip()
    duration = form.get("RecordingDuration")
    if cid and acct and rec_sid and status == "completed":
        try:
            dur = int(duration) if duration else None
        except (TypeError, ValueError):
            dur = None
        await record_and_broadcast(cid, {
            "kind": "call.recording",
            "url": f"/recording/{acct}/{rec_sid}",  # relative; UI prefixes the backend origin
            "duration": dur,
        })
    return {"ok": True, "case_id": cid, "recording": rec_sid}


@app.get("/recording/{account_sid}/{recording_sid}")
async def recording_proxy(account_sid: str, recording_sid: str):
    """Stream a Twilio call recording to the browser, authenticating with the Twilio
    token server-side (so the URL the UI plays carries no credentials)."""
    rid = recording_sid[:-4] if recording_sid.endswith(".mp3") else recording_sid
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Recordings/{rid}.mp3"
    try:
        r = await asyncio.to_thread(
            requests.get, url, auth=(account_sid, TWILIO_AUTH_TOKEN), timeout=30
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"recording fetch failed: {e}")
    return Response(content=r.content, media_type="audio/mpeg", status_code=r.status_code)


@app.get("/recording/call/{account_sid}/{call_sid}")
async def recording_by_call(account_sid: str, call_sid: str):
    """Resolve a recording by CALL sid (what an agent has synchronously) and stream
    the mp3, with a brief retry if Twilio hasn't finalized it yet. Backs the voice
    agent's `recording_url` output so the email agent can attach the audio."""
    import time as _t

    def _fetch():
        base = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"
        for _ in range(3):  # recording may lag the call end by a couple seconds
            lr = requests.get(f"{base}/Recordings.json", params={"CallSid": call_sid},
                              auth=(account_sid, TWILIO_AUTH_TOKEN), timeout=20)
            recs = (lr.json().get("recordings") if lr.status_code == 200 else None) or []
            if recs:
                sid = recs[0].get("sid")
                mr = requests.get(f"{base}/Recordings/{sid}.mp3",
                                  auth=(account_sid, TWILIO_AUTH_TOKEN), timeout=30)
                return mr.status_code, mr.content
            _t.sleep(2)
        return 404, b""

    code, content = await asyncio.to_thread(_fetch)
    if code != 200 or not content:
        raise HTTPException(status_code=404, detail="recording not available yet")
    return Response(content=content, media_type="audio/mpeg")


@app.get("/healthz")
def health():
    return {"ok": True, "cases": list(CASES.keys()), "clients": len(CLIENTS),
            "names": CASE_NAMES}
