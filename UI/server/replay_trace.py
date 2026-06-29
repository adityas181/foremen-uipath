"""
replay_trace — drive the FOREMAN UI end-to-end from a REAL Maestro trace export.

It reads a Maestro instance trace (the JSON you exported), pulls each coded
agent node's actual output, maps it to the UI's CaseEvent contract, and POSTs
the events to the running view-backend with lifelike pacing. The browser (in
live mode) animates exactly as it will when the real agents emit.

Use it to (a) see the whole pipeline working in ~40s without touching UiPath,
and (b) read it as the precise spec for which node emits which CaseEvent — then
mirror these same `fm.*` calls inside your live agents via foreman_emit.

    # 1) backend up:   FOREMAN_INGEST_SECRET=dev-secret uvicorn view_backend:app --port 8000
    # 2) UI in live mode (.env: VITE_FEED_MODE=live) :  npm run dev
    # 3) replay:
    python replay_trace.py "C:/Users/Dell/Downloads/trace-1782457166681.json"

Env: FOREMAN_BACKEND_URL (default http://localhost:8000), FOREMAN_INGEST_SECRET.
"""
from __future__ import annotations

import json
import sys
import time

from foreman_emit import Emitter, _norm_risk


# ── trace helpers ─────────────────────────────────────────────────────────────
def load_trace(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def attrs(span: dict) -> dict:
    try:
        return json.loads(span.get("Attributes") or "{}")
    except Exception:
        return {}


def node_output(spans: list[dict], name: str):
    """Final output.value of the named coded-agent node (the richest = last run)."""
    hits = [s for s in spans if s.get("Name") == name and attrs(s).get("output.value") is not None]
    if not hits:
        return None
    return attrs(hits[-1]).get("output.value")


def instance_id(spans: list[dict]) -> str:
    for s in spans:
        a = attrs(s)
        if a.get("instanceId"):
            return a["instanceId"]
    return spans[0].get("TraceId", "unknown") if spans else "unknown"


def g(d, *keys, default=None):
    """Safe nested get: g(out, 'perception', 'faults', default=[])."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# ── the replay ─────────────────────────────────────────────────────────────────
def replay(path: str) -> None:
    spans = load_trace(path)
    out = {n: node_output(spans, n) for n in (
        "intake", "perceive", "supervise", "diagnose", "assess",
        "check_parts", "plan_weather", "blast", "make_brief", "place_call", "dispatch")}

    inst = instance_id(spans)                       # routing key (what the UI buckets by)
    case = out.get("supervise", {}).get("case", {}) if out.get("supervise") else {}
    site_id = case.get("site_id") or g(out.get("perceive") or {}, "history_match", "matched_record", "siteid") or "DEL-0788"
    asset_id = case.get("asset_id") or "AST-SCB-DEL-0788"
    display_id = f"CASE-{site_id}"                  # friendly external key shown in UI

    fm = Emitter(case_id=inst)
    print(f"replaying trace {path}\n  routing key (instance) = {inst}\n  display case_id        = {display_id}\n")

    def step(fn, *a, pause=0.6, **k):
        fn(*a, **k)
        time.sleep(pause)

    # ── INTAKE ────────────────────────────────────────────────────────────────
    step(fm.case_opened, case_id=display_id, site_id=site_id,
         title=f"MC4 connector · {site_id}", worker_name="Field engineer",
         worker_phone="+91 •••• ••5778", scenario="C", opened_at=time.strftime("%H:%M"))
    step(fm.stage, "intake")
    worker_text = (g(out.get("perceive") or {}, "issue_text_received")
                   or "MC4 connector is faulty again, copper wire is coming out, contact is very loose.")
    step(fm.message, "worker", worker_text)
    if g(out.get("intake") or {}, "reply_message"):
        step(fm.message, "foreman", out["intake"]["reply_message"])
    step(fm.media_received, [{"kind": "video", "label": f"{asset_id}.mp4",
                              "meta": "MP4 · field clip", "note": "Close-up MC4 connector inspection"}])
    step(fm.log, "intake", "Intake agent", f"Asset {asset_id} verified · routing to Perceive", "ok")

    # ── PERCEIVE ────────────────────────────────────────────────────────────────
    p = out.get("perceive") or {}
    perception = p.get("perception") or {}
    faults = perception.get("faults") or []
    findings = [{"modality": "image", "label": f.get("type", "fault"),
                 "detail": f.get("evidence"), "severity": f.get("severity"),
                 "confidence": f.get("confidence")} for f in faults]
    step(fm.stage, "perceive")
    step(fm.agent_running, "vision")
    step(fm.perception_ready,
         {"findings": findings, "issues": [f.get("type", "") for f in faults],
          "corrosion": {"present": True, "severity": (faults[0].get("severity") if faults else "high")}},
         asset_note=f"{site_id} · {perception.get('scene', 'field media')} — analysed by vision")
    top = faults[0] if faults else {}
    step(fm.agent_completed, "vision",
         headline=f"{top.get('type', 'fault')} ({top.get('severity', 'high')})",
         detail=perception.get("summary"), confidence=top.get("confidence", 0.95))
    hm = p.get("history_match") or {}
    if hm:
        step(fm.log, "perceive", "History match",
             f"{hm.get('match_type', 'related')} prior record · {hm.get('recommendation', '')[:90]}", "info")

    # ── INVESTIGATE (supervisor assembles a dynamic crew) ────────────────────────
    sup = out.get("supervise") or {}
    diag = out.get("diagnose") or {}
    step(fm.stage, "investigate")
    step(fm.agent_running, "supervisor")
    # assemble the crew the supervisor actually invoked (mapped to UI agent cards)
    step(fm.agent_assembled, "rootcause")
    step(fm.agent_assembled, "fleet")

    # root cause (diagnose)
    step(fm.agent_running, "rootcause")
    step(fm.skill_matched, {"id": diag.get("skill_hit", "SK-pv-mc4-connector-burn"),
                            "status": diag.get("skill_status", "candidate"), "source": "skill library"})
    step(fm.agent_completed, "rootcause",
         headline=diag.get("root_cause", "Loose MC4 crimp → DC-arc risk"),
         detail=(diag.get("recommendation", "").split("\n")[0] if diag.get("recommendation") else None),
         confidence=diag.get("confidence", 0.95), citations=diag.get("citations"))

    # fleet blast radius (blast) — output already matches FleetView
    blast = (out.get("blast") or {}).get("fleet")
    if blast:
        step(fm.agent_running, "fleet")
        step(fm.fleet_ready, blast)
        step(fm.agent_completed, "fleet",
             headline=f"{len(blast.get('affected', []))} strings at risk via shared crew + lot",
             detail=g(blast, "sqlVsGraph", "graphNote"))

    # the rest of the crew (no dedicated UI card) → activity log
    if out.get("assess"):
        step(fm.log, "investigate", "Safety", "Safety-critical: LOTO + de-energise gate required", "danger")
    if out.get("check_parts"):
        cp = out["check_parts"]
        step(fm.log, "investigate", "Parts", f"In stock at {cp.get('location', 'warehouse')} · lead {cp.get('lead_time_days', 0)}d", "ok")
    if out.get("plan_weather"):
        step(fm.log, "investigate", "Weather", out["plan_weather"].get("safe_window", "safe window confirmed"), "info")

    risk = g(sup, "risk", "score", default=84)
    step(fm.risk_scored, risk)
    step(fm.investigation_ready, {
        "root_cause": diag.get("root_cause", ""),
        "confidence": diag.get("confidence", 0.95),
        "alternatives_ruled_out": diag.get("alternatives_ruled_out", []),
        "systemic": bool(blast and blast.get("systemic")),
        "fleet_affected": len(blast.get("affected", [])) if blast else 0,
        "risk_score": _norm_risk(risk),
        "recommendation": diag.get("recommendation", g(sup, "summary", default="")),
        "eta_min": (out.get("dispatch") or {}).get("eta_min", 27)})
    step(fm.agent_completed, "supervisor",
         headline=f"Plan ready · risk {_norm_risk(risk):.2f} · auto-resolve blocked (human gate)",
         detail=g(sup, "worker_message", default="")[:140])

    # ── ESCALATE (Human Safety Review + voice) ───────────────────────────────────
    brief = out.get("make_brief") or {}
    call = out.get("place_call") or {}
    step(fm.stage, "escalate")
    step(fm.task_raised, {"id": "TASK-100136072", "kind": "approve_call",
                          "prompt": brief.get("spoken_recommendation",
                                              "Authorize isolation + MC4 replacement and fleet audit?"),
                          "options": ["Approve", "Reject"], "status": "pending"})
    step(fm.call_started, call.get("to", "+91 •••• ••5778"), "Site Manager")
    step(fm.call_connected)
    if brief.get("spoken_opener"):
        step(fm.call_line, "foreman", brief["spoken_opener"])
    if brief.get("spoken_recommendation"):
        step(fm.call_line, "foreman", brief["spoken_recommendation"])
    for line in call.get("transcript", []):
        if str(line).startswith("manager:"):
            step(fm.call_line, "manager", str(line).split(":", 1)[1].strip(), pause=0.4)
    approved = (call.get("decision", "approved") == "approved")
    step(fm.call_decision, authorized=approved,
         actions=["Isolate string (LOTO)", "Replace MC4 pair", "Thermal scan", "Fleet audit (3 siblings)"],
         by="Site Manager")
    step(fm.task_answered, "TASK-100136072", "Approve" if approved else "Reject", by="Site Manager")

    # ── RESOLVE (guarded downstream writes) ──────────────────────────────────────
    disp = out.get("dispatch") or {}
    step(fm.stage, "resolve")
    step(fm.action_produced, {"type": "work_order", "id": f"WO-{site_id}",
         "title": f"Replace MC4 pair · {asset_id}", "guard": "human-approved",
         "fields": {"crew": disp.get("crew_id", "CREW-PV-W"), "eta_min": disp.get("eta_min", 27),
                    "route": disp.get("route", "—"), "parts": "MC4 pair + dielectric grease"}})
    if blast:
        step(fm.action_produced, {"type": "fleet_case", "id": f"FLEET-{blast.get('batch_id', 'HV-BATCH-19')}",
             "title": f"Fleet audit · {len(blast.get('affected', []))} sibling strings",
             "fields": {"affected": ", ".join(blast.get("affected", [])),
                        "shared": "crew CREW-PV-W + lot MC4-LOT-X"}})
        step(fm.graph_updated, f"Blast radius: {len(blast.get('affected', []))} strings linked via crew + part-lot")

    # ── CLOSE (audit + learn) ────────────────────────────────────────────────────
    step(fm.stage, "close")
    report = g(sup, "report_url", default="")
    attachments = (diag.get("citations") or []) + ([report.split("/")[-1].split("?")[0]] if report else [])
    step(fm.audit_ready, to="ops@foreman.example",
         subject=f"[FOREMAN] {asset_id} · MC4 connector · CRITICAL · resolved (human-approved)",
         body=g(sup, "summary", default="Case resolved. SOP applied; fleet audit raised."),
         attachments=attachments)
    fp = diag.get("fingerprint") or {}
    step(fm.skill_written, {
        "id": diag.get("skill_hit", "SK-pv-mc4-connector-burn"),
        "match_key": {"equipment_class": fp.get("equipment_class", "pv_array"),
                      "component": fp.get("component", "MC4 connector"),
                      "environment": fp.get("environment", "outdoor"),
                      "spec": fp.get("capacity_band", "outdoor_rated"),
                      "failure_mode": fp.get("failure_mode", "exposed_wiring")},
        "diagnosis": diag.get("root_cause", ""),
        "recipe": [s for s in (diag.get("recommendation", "").split("\n")) if s.strip()],
        "status": diag.get("skill_status", "candidate"), "approve_count": 1,
        "source_cases": [display_id], "citations": diag.get("citations", [])})
    step(fm.feedback, "up")
    step(fm.closed, pause=0)
    print("\n[done] replay complete - the case should be fully populated in the UI.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python replay_trace.py "<path-to-trace.json>"')
        sys.exit(1)
    replay(sys.argv[1])
