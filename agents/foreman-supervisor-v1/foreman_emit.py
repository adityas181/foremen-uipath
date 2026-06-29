"""
foreman_emit — the one bridge every UiPath coded agent imports to make the
FOREMAN UI animate in real time.

Drop this file beside your agents (or pip-install it as a tiny internal package)
and call the helpers at each meaningful step. Each call POSTs one `CaseEvent`
(shape = src/types.ts) to the view-backend, which fans it out to the browser
over WebSocket in ~tens of ms.

    from foreman_emit import Emitter

    fm = Emitter(case_id=instance_id)          # routing key = Maestro instance id
    fm.case_opened(case_id="CASE-DEL-0788",    # external key shown in the UI
                   site_id="DEL-0788", title="MC4 connector · DEL-0788")
    fm.stage("perceive"); fm.agent_running("vision")
    fm.perception_ready(perception, asset_note="DEL-0788 · OpenAI vision")
    fm.agent_completed("vision", headline="Exposed wiring (high)", confidence=0.95)

Design rules:
  * NEVER raises. Telemetry must not break the automation. Failures are printed.
  * Routing key (`case_id`) is whatever the store buckets by — use the Maestro
    INSTANCE ID (ambient, unique, present in webhooks). Show the friendly
    external key by passing it inside case_opened(...). See LIVE_SETUP.md.
  * Risk is normalised to 0..1 for the UI's RiskMeter (it draws v*100 and marks
    the 0.70 "call" threshold). Pass 84 or 0.84 — both land as 0.84.
"""
from __future__ import annotations

import json as _json
import os
import time
import urllib.request
from typing import Any


BACKEND = os.environ.get("FOREMAN_BACKEND_URL", "http://localhost:8000").rstrip("/")
SECRET = os.environ.get("FOREMAN_INGEST_SECRET", "dev-secret")


def configure(backend: str | None = None, secret: str | None = None) -> None:
    """Override backend/secret at runtime (call once at agent startup). Useful in
    UiPath cloud where you read these from Orchestrator Assets rather than env."""
    global BACKEND, SECRET
    if backend:
        BACKEND = backend.rstrip("/")
    if secret:
        SECRET = secret


def configure_from_assets(url_asset: str = "FOREMAN_BACKEND_URL",
                          secret_asset: str = "FOREMAN_INGEST_SECRET",
                          folder_path: str | None = None) -> None:
    """Production path: pull the backend URL (text asset) and ingest secret
    (credential asset) from Orchestrator. Import is lazy so this module stays
    dependency-light (only `requests`) when the SDK isn't present."""
    try:
        from uipath.platform import UiPath  # type: ignore
        sdk = UiPath()
        url = sdk.assets.retrieve(name=url_asset, folder_path=folder_path)
        cred = sdk.assets.retrieve_credential(name=secret_asset, folder_path=folder_path)
        configure(backend=getattr(url, "value", str(url)), secret=str(cred))
    except Exception as e:  # pragma: no cover
        print("foreman_emit: configure_from_assets failed (using env defaults):", e)


def _norm_risk(x: float) -> float:
    """UI RiskMeter is 0..1. Accept 0..1 or 0..100 and clamp."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v > 1.0:
        v = v / 100.0
    return max(0.0, min(1.0, v))


def post_event(case_id: str, event: dict, *, backend: str | None = None, secret: str | None = None) -> None:
    """Low-level: POST one CaseEvent. Swallows all errors by design — telemetry
    must never break the agent. Uses stdlib urllib (no extra dependency), with a
    short timeout so a wrong/unreachable backend can't stall the run."""
    url = f"{(backend or BACKEND).rstrip('/')}/ingest/{case_id}"
    body = _json.dumps(event).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "x-foreman-secret": secret or SECRET},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:  # nosec - internal telemetry
            resp.read()
    except Exception as e:  # pragma: no cover
        print("foreman_emit: emit failed:", e)


class Emitter:
    """Bound to one case (one routing key). One instance per agent invocation."""

    def __init__(self, case_id: str, *, backend: str | None = None, secret: str | None = None):
        # case_id here is the ROUTING KEY the UI buckets by. For the LIVE path,
        # pass your external case_id (the value the Maestro case computes for its
        # Case ID and maps into every agent's input) so all events for one case
        # share one key. backend/secret default to module config (env/configure).
        self.case_id = str(case_id)
        self.backend = (backend or BACKEND).rstrip("/")
        self.secret = secret or SECRET

    # ── core ────────────────────────────────────────────────────────────────
    def emit(self, event: dict) -> None:
        post_event(self.case_id, event, backend=self.backend, secret=self.secret)

    def log(self, stage: str, source: str, text: str, tone: str = "agent") -> None:
        self.emit({"kind": "log", "entry": {
            "ts": time.strftime("%H:%M:%S"), "stage": stage,
            "source": source, "text": text, "tone": tone}})

    # ── case / stage ──────────────────────────────────────────────────────────
    def case_opened(self, **case_fields: Any) -> None:
        """First event. Put the friendly external key + display fields here:
        case_id, site_id, title, worker_phone, worker_name, scenario, opened_at."""
        self.emit({"kind": "case.opened", "case": case_fields})

    def stage(self, stage_id: str, note: str | None = None) -> None:
        ev: dict = {"kind": "stage.entered", "stage": stage_id}
        if note:
            ev["note"] = note
        self.emit(ev)

    def closed(self) -> None:
        self.emit({"kind": "case.closed"})

    # ── chat / media ──────────────────────────────────────────────────────────
    def message(self, frm: str, text: str, *, ts: str | None = None,
                media: list[dict] | None = None, options: list[str] | None = None,
                mid: str | None = None) -> None:
        msg: dict = {"id": mid or f"m{int(time.time()*1000)}", "from": frm,
                     "text": text, "ts": ts or time.strftime("%H:%M")}
        if media:
            msg["media"] = media
        if options:
            msg["options"] = options
        self.emit({"kind": "message", "message": msg})

    def media_received(self, media: list[dict]) -> None:
        self.emit({"kind": "media.received", "media": media})

    # ── agents (crew cards) ─────────────────────────────────────────────────
    # agent ∈ supervisor | vision | entitlement | sla | rootcause | fleet
    def agent_assembled(self, agent: str) -> None:
        self.emit({"kind": "agent.assembled", "agent": agent})

    def agent_running(self, agent: str) -> None:
        self.emit({"kind": "agent.running", "agent": agent})

    def agent_completed(self, agent: str, *, headline: str | None = None,
                        detail: str | None = None, confidence: float | None = None,
                        citations: list[str] | None = None) -> None:
        run: dict = {}
        if headline is not None:
            run["headline"] = headline
        if detail is not None:
            run["detail"] = detail
        if confidence is not None:
            run["confidence"] = confidence
        if citations is not None:
            run["citations"] = citations
        self.emit({"kind": "agent.completed", "agent": agent, "run": run})

    # ── perception / skills / investigation / fleet ──────────────────────────
    def perception_ready(self, perception: dict, asset_note: str = "") -> None:
        self.emit({"kind": "perception.ready", "perception": perception,
                   "asset_note": asset_note})

    def skill_matched(self, hit: dict | None) -> None:
        # hit = {"id": "SK-...", "status": "candidate"|"trusted"|..., "source": "..."}
        self.emit({"kind": "skill.matched", "hit": hit})

    def risk_scored(self, risk: float) -> None:
        self.emit({"kind": "risk.scored", "risk": _norm_risk(risk)})

    def investigation_ready(self, investigation: dict) -> None:
        inv = dict(investigation)
        if "risk_score" in inv:
            inv["risk_score"] = _norm_risk(inv["risk_score"])
        self.emit({"kind": "investigation.ready", "investigation": inv})

    def fleet_ready(self, fleet: dict) -> None:
        # `fleet` already matches the UI FleetView (systemic/affected/nodes/edges/...)
        self.emit({"kind": "fleet.ready", "fleet": fleet})

    def graph_updated(self, note: str) -> None:
        self.emit({"kind": "graph.updated", "note": note})

    # ── human-in-the-loop (Action Center) ────────────────────────────────────
    def task_raised(self, task: dict) -> None:
        # task = {"id","kind":"confirm"|"approve_call","prompt","options?","status":"pending"}
        self.emit({"kind": "task.raised", "task": task})

    def task_answered(self, task_id: str, answer: str, by: str | None = None) -> None:
        ev: dict = {"kind": "task.answered", "taskId": task_id, "answer": answer}
        if by:
            ev["by"] = by
        self.emit(ev)

    # ── voice call ────────────────────────────────────────────────────────────
    def call_started(self, to: str, to_role: str) -> None:
        self.emit({"kind": "call.started", "to": to, "toRole": to_role})

    def call_connected(self) -> None:
        self.emit({"kind": "call.connected"})

    def call_line(self, speaker: str, text: str) -> None:
        # speaker ∈ foreman | manager
        self.emit({"kind": "call.line", "line": {"speaker": speaker, "text": text}})

    def call_decision(self, *, authorized: bool, actions: list[str], by: str,
                      at: str | None = None) -> None:
        self.emit({"kind": "call.decision", "decision": {
            "authorized": authorized, "actions": actions, "by": by,
            "at": at or time.strftime("%H:%M")}})

    # ── outputs / audit / learning ────────────────────────────────────────────
    def action_produced(self, artifact: dict) -> None:
        # artifact = {"type","id","title","guard?","fields":{...},"external?":bool}
        self.emit({"kind": "action.produced", "artifact": artifact})

    def audit_ready(self, to: str, subject: str, body: str, attachments: list[str]) -> None:
        self.emit({"kind": "audit.ready", "audit": {
            "email": {"to": to, "subject": subject, "body": body},
            "attachments": attachments}})

    def skill_written(self, skill: dict) -> None:
        self.emit({"kind": "skill.written", "skill": skill})

    def skill_promoted(self, skill_id: str, approve_count: int, status: str) -> None:
        self.emit({"kind": "skill.promoted", "skillId": skill_id,
                   "approve_count": approve_count, "status": status})

    def feedback(self, verdict: str) -> None:  # 'up' | 'down'
        self.emit({"kind": "feedback", "verdict": verdict})


# ── module-level convenience (when you don't want to hold an Emitter) ─────────
def emit(case_id: str, event: dict) -> None:
    post_event(case_id, event)


def log(case_id: str, stage: str, source: str, text: str, tone: str = "agent") -> None:
    Emitter(case_id).log(stage, source, text, tone)


def routing_key(instance_id: str, external_key: str | None = None) -> str:
    """We route by the Maestro instance id (ambient + in webhooks). The friendly
    external_key is shown via case_opened(case_id=external_key, ...), not used as
    the bucket key. Kept as a function so the intent is explicit at call sites."""
    return str(instance_id)
