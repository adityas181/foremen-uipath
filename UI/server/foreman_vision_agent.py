"""
FOREMAN coded agent — OpenAI + LangChain + LangGraph.

A vision + root-cause agent that reads the mp4 (already in the UiPath storage
bucket) and the worker text, and EMITS CaseEvents to the view-backend at each
step — so the UI animates in real time, exactly like the demo replay.

The key idea: you control this code, so you just call emit(...) at every
meaningful moment. No webhooks needed for fine-grained agent progress.

Deploy as a UiPath coded agent:
    pip install uipath-langchain
    uipath new foreman-vision
    # drop this graph in main.py ; langgraph.json -> :graph
    uipath auth && uipath init && uipath pack && uipath publish
The Maestro Case then "Starts and waits for" this agent, passing the case input
(case_id, site_id, media_path, text). media_path is the bucket file the RPA step
already downloaded (or download it here via the UiPath SDK).
"""
import os
import json
import time
import base64
import requests
from typing import TypedDict

import cv2  # opencv-python — pull frames from the mp4 (OpenAI vision takes images)
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

BACKEND = os.environ.get("FOREMAN_BACKEND_URL", "http://localhost:8000")
SECRET = os.environ.get("FOREMAN_INGEST_SECRET", "dev-secret")


# ── the emit() bridge — one CaseEvent → the view-backend → the UI ────────────
def emit(case_id: str, event: dict) -> None:
    try:
        requests.post(
            f"{BACKEND}/ingest/{case_id}",
            json=event,
            headers={"x-foreman-secret": SECRET},
            timeout=5,
        )
    except Exception as e:
        print("emit failed:", e)  # never let telemetry break the agent


def log(case_id: str, stage: str, source: str, text: str, tone: str = "agent") -> None:
    emit(case_id, {"kind": "log", "entry": {
        "ts": time.strftime("%H:%M:%S"), "stage": stage,
        "source": source, "text": text, "tone": tone}})


# ── structured outputs (shapes match the UI's CaseEvent payloads) ────────────
class Perception(BaseModel):
    corrosion_present: bool
    corrosion_severity: str = Field(description="none | low | medium | high")
    generator_anomaly: str = "none"
    generator_confidence: float = 0.0
    issues: list[str]


class RootCause(BaseModel):
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    alternatives_ruled_out: list[str]
    recommendation: str
    risk_score: float = Field(ge=0, le=1)


def sample_frames(path: str, n: int = 6) -> list[str]:
    """N evenly-spaced frames from the mp4 as base64 image data-URLs."""
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    urls = []
    for i in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * i / n))
        ok, frame = cap.read()
        if not ok:
            continue
        _, buf = cv2.imencode(".jpg", frame)
        urls.append("data:image/jpeg;base64," + base64.b64encode(buf).decode())
    cap.release()
    return urls


# ── LangGraph state ──────────────────────────────────────────────────────────
class S(TypedDict):
    case_id: str
    site_id: str
    media_path: str  # local path to the bucket-downloaded mp4
    text: str        # the worker's message text
    perception: dict
    investigation: dict


def perceive(state: S) -> dict:
    cid = state["case_id"]
    emit(cid, {"kind": "stage.entered", "stage": "perceive"})
    emit(cid, {"kind": "agent.running", "agent": "vision"})
    log(cid, "perceive", "Vision · OpenAI", "Sampling frames + reading worker text")

    frames = sample_frames(state["media_path"])
    content = [{"type": "text", "text":
                "You are an RF/telecom field inspector. From these tower-site video "
                "frames and the worker's note, report corrosion and any generator "
                "audio cues you can infer. Worker note: " + state["text"]}]
    content += [{"type": "image_url", "image_url": {"url": u}} for u in frames]

    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Perception)
    p: Perception = llm.invoke([HumanMessage(content=content)])

    perception = {
        "corrosion": {"present": p.corrosion_present, "severity": p.corrosion_severity},
        "generator_audio": {"anomaly": p.generator_anomaly, "confidence": p.generator_confidence},
        "issues": p.issues,
    }
    emit(cid, {"kind": "perception.ready", "perception": perception,
               "asset_note": f"{state['site_id']} · analysed by OpenAI vision"})
    emit(cid, {"kind": "agent.completed", "agent": "vision", "run": {
        "headline": f"Corrosion {p.corrosion_severity}",
        "detail": ", ".join(p.issues), "confidence": 0.85}})
    return {"perception": perception}


def root_cause(state: S) -> dict:
    cid = state["case_id"]
    emit(cid, {"kind": "stage.entered", "stage": "investigate"})
    emit(cid, {"kind": "agent.running", "agent": "rootcause"})
    log(cid, "investigate", "Root-cause · OpenAI", "Weighing evidence to a cause")

    llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(RootCause)
    rc: RootCause = llm.invoke(
        f"Perception: {json.dumps(state['perception'])}\nWorker note: {state['text']}\n"
        "Decide the single most likely root cause, list the alternatives you ruled "
        "out, recommend one action, and score operational risk 0..1.")

    inv = {
        "root_cause": rc.root_cause, "confidence": rc.confidence,
        "alternatives_ruled_out": rc.alternatives_ruled_out,
        "systemic": False, "fleet_affected": 0,
        "risk_score": rc.risk_score, "recommendation": rc.recommendation,
    }
    emit(cid, {"kind": "agent.completed", "agent": "rootcause", "run": {
        "headline": rc.root_cause, "detail": rc.recommendation, "confidence": rc.confidence}})
    emit(cid, {"kind": "risk.scored", "risk": rc.risk_score})
    emit(cid, {"kind": "investigation.ready", "investigation": inv})
    log(cid, "investigate", "Supervisor", f"Recommendation ready · risk {rc.risk_score:.2f}", "agent")
    return {"investigation": inv}


_g = StateGraph(S)
_g.add_node("perceive", perceive)
_g.add_node("root_cause", root_cause)
_g.add_edge(START, "perceive")
_g.add_edge("perceive", "root_cause")
_g.add_edge("root_cause", END)
graph = _g.compile()  # <- uipath init exposes this as the deployable agent


# Local smoke test (outside UiPath):
if __name__ == "__main__":
    graph.invoke({
        "case_id": "CASE-0916", "site_id": "DEL-0473",
        "media_path": "clip.mp4",
        "text": "RF cable looks corroded again and the generator is knocking.",
        "perception": {}, "investigation": {},
    })
