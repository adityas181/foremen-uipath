"""FOREMAN supervisor (foreman-supervisor-v1) — coded orchestrator (uipath-langchain).

A single LangGraph node that:
  0) normalizes the real vision payload,
  1) runs the always-on diagnosis ENGINE (unconditional),
  2) routes the 10 specialists with a frontier ROUTER LLM (gpt-5) + a deterministic
     safety floor enforced in code,
  3) builds each invoked specialist's input from the engine/normalized case,
  4) invokes the chosen specialists CONCURRENTLY (Pattern A),
  5) computes risk + the auto-resolve gate,
  6) merges everything into an ordered action_plan + a human-readable summary,
  7) returns the section-3 object — never throwing; every failure lands in errors[].

Only the router (step 2) uses the frontier model; the specialists are separate
agents on gpt-4.1-mini. The four core helpers below (registry+g, invoke,
normalize, risk_score) are the build-doc blocks, used verbatim.
"""

# ===========================================================================
# BUILD-DOC BLOCK 1 — registry + g()  (VERBATIM)
# ===========================================================================
FOLDER = "Shared/foremen v1"
ENGINE = "foreman-diagnosis-recommendation"

PROC = {
    "safety_compliance":    "foreman-safety",
    "fleet_blast_radius":   "foreman-fleet-blast-radius",
    "parts_logistics":      "foreman-parts",
    "field_dispatch":       "foreman-field-dispatch",
    "site_access_weather":  "foreman-weather",
    "warranty_entitlement": "foreman-entitlement",
    "sla_commercial_impact":"foreman-sla-risk",
    "vendor_supply_chain":  "foreman-vendor",
    "telemetry_predictive": "foreman-telemetry",
    "cost_optimization":    "foreman-cost",
}

INVOKE_WHEN = {
    "safety_compliance":    "the matched skill has safety_protocol=true, OR the equipment/failure is hazardous (arc/fire, fall, derailment, pressure, HV)",
    "fleet_blast_radius":   "the asset shares a failure-propagating link with others - same batch, vendor, firmware, power feeder, cooling loop, or install crew",
    "parts_logistics":      "the recommended fix needs a replacement part or consumable",
    "field_dispatch":       "a physical repair, swap or inspection visit is required",
    "site_access_weather":  "the fix is outdoor / at height / in a live environment / weather-sensitive, or site access is constrained",
    "warranty_entitlement": "the asset is in a warranty window AND the root cause is a vendor / batch / spec / manufacturing defect - NOT field-workmanship faults",
    "sla_commercial_impact":"the asset/site serves multiple tenants/customers/an SLA AND the commercial exposure could CHANGE the priority or action",
    "vendor_supply_chain":  "the root cause implicates a SUPPLIER - a batch/lot defect, a recall, counterfeit/substituted parts - NOT a one-off field workmanship fault",
    "telemetry_predictive": "the fault is INCIPIENT / degrading and a sensor trend would decide fix-now-vs-schedule - NOT when the part has already hard-failed",
    "cost_optimization":    "there is a GENUINE repair-vs-replace-vs-upgrade trade-off - NOT when the fix is forced/trivial",
}

def g(d, *keys, default=""):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


# ===========================================================================
# BUILD-DOC BLOCK 2 — invoke()  (Pattern A, VERBATIM)
# ===========================================================================
import asyncio, json
from uipath.platform import UiPath  # SDK path in this env (build-doc block wrote `from uipath import UiPath`)

async def invoke(sdk, process_name: str, payload: dict) -> dict:
    try:
        job = await sdk.processes.invoke_async(
            name=process_name, input_arguments=payload, folder_path=FOLDER
        )
        while True:
            j = await sdk.jobs.retrieve_async(job.key, folder_path=FOLDER)
            state = (j.state or "").lower()
            if state in {"successful", "faulted", "stopped"}:
                break
            await asyncio.sleep(2)
        if state != "successful":
            return {}
        out = await sdk.jobs.extract_output_async(j)  # SDK takes job only (block wrote folder_path=FOLDER)
        if isinstance(out, str):
            return json.loads(out) if out.strip() else {}
        return out or {}
    except Exception:
        return {}


# ===========================================================================
# BUILD-DOC BLOCK 3 — normalize()  (VERBATIM)
# ===========================================================================
def normalize(vin: dict) -> dict:
    pe  = vin.get("perception", {}) or {}
    hm  = vin.get("history_match", {}) or {}
    rec = hm.get("matched_record", {}) or {}
    faults = pe.get("faults") or []
    rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    ordered = sorted(
        faults,
        key=lambda f: (rank.get(str(f.get("severity", "")).lower(), 0), float(f.get("confidence", 0) or 0)),
        reverse=True,
    )
    primary = ordered[0] if ordered else {}
    return {
        "asset_id":    vin.get("asset_id") or rec.get("assetid", ""),
        "site_id":     vin.get("site_id")  or rec.get("siteid", ""),
        "worker_text": vin.get("issue_text_received", ""),
        "perception":  pe,
        "primary_fault": primary,
        "batch_id":    rec.get("batchid", ""),
        "history": {
            "is_recurrence":   bool(hm.get("is_recurrence", False)),
            "match_type":      hm.get("match_type", ""),
            "severity_trend":  hm.get("severity_trend", ""),
            "recurrence_count": int(rec.get("recurrencecount", 0) or 0),
            "past_resolution": hm.get("past_resolution", ""),
            "prior_fault_type": rec.get("faulttype", ""),
        },
    }


# ===========================================================================
# BUILD-DOC BLOCK 4 — risk_score()  (VERBATIM)
# ===========================================================================
def risk_score(engine, safety, fleet, parts, weather, dispatch, history=None):
    history = history or {}
    c = []
    s = 0
    if safety.get("safety_critical"):
        s += 50; c.append(("safety_critical", 50, "DC arc + fire hazard; human gate mandatory"))
    if fleet.get("systemic"):
        n = int(fleet.get("affected_count", 0) or 0)
        pts = min(30, 8 * n)
        s += pts; c.append(("blast_radius", pts, f"{n} assets share crew/lot/batch and are at risk"))
    if history.get("is_recurrence") or int(history.get("recurrence_count", 0) or 0) > 0:
        s += 10; c.append(("recurrence", 10,
                           f"fault recurred (count={history.get('recurrence_count', 0)}, "
                           f"prior={history.get('prior_fault_type','')}); prior fix did not hold"))
    if parts.get("blocks_fix"):
        s += 10; c.append(("parts_blocked", 10, "a required genuine part is unavailable; fix is blocked"))
    real_wb = [b for b in (weather.get("weather_blockers") or []) if b != "after-dark"]
    if real_wb:
        s += 5; c.append(("weather", 5, f"weather blockers: {real_wb}"))
    if dispatch and dispatch.get("crew_id") and not dispatch.get("certification_ok", True):
        s += 8; c.append(("no_certified_crew", 8, "available crew is not certified for this work"))
    conf = float(engine.get("confidence", 1.0) or 1.0)
    if conf < 0.8:
        pts = round((0.8 - conf) * 25); s += pts; c.append(("low_confidence", pts, f"diagnosis confidence {conf}"))
    s = min(100, s)
    band = "CRITICAL" if s >= 70 else "HIGH" if s >= 45 else "MEDIUM" if s >= 20 else "LOW"
    if safety.get("safety_critical"):
        if fleet.get("systemic"):
            band = "CRITICAL"
        elif band in ("LOW", "MEDIUM"):
            band = "HIGH"
    return s, band, [{"factor": f, "points": p, "reason": r} for (f, p, r) in c]


# ===========================================================================
# ORCHESTRATOR
# ===========================================================================
import re
from typing import Any, List, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph, END
from uipath_langchain.chat import UiPathChat
from pydantic import BaseModel, Field

ROUTER_MODEL = "gpt-5-2025-08-07"  # frontier router (build-doc said "gpt-5"; this is the real Gateway id);
                                   # specialists are separate agents on gpt-4.1-mini
RATIONALE_MODEL = "gpt-4.1-2025-04-14"   # OPTIONAL risk rationale (read-only prose)
WORKER_MSG_MODEL = "gpt-4.1-2025-04-14"  # worker reply is ENGLISH-ONLY (user pref) — no language mirroring
REPORT_BUCKET = "foreman-context"            # Storage Bucket holding the reference PDFs (folder = FOLDER)
REPORT_DEFAULT_BLOB = "mc4-connector-install-spec.pdf"  # fallback reference doc
REPORT_EXPIRY_MIN = 20                        # pre-signed read URL validity (minutes)

# hazard terms for the deterministic safety floor (step 2)
_HAZARD_TERMS = [
    "arc", "fire", "burn", "burnt", "melt", "melted", "exposed", "shock",
    "short", "spark", "smoke", "high voltage", "high-voltage", "explos", "flame",
]
_HAZARD_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _HAZARD_TERMS) + r")", re.I)
_HV_RE = re.compile(r"\bhv\b", re.I)


def _hazard_present(*chunks) -> bool:
    """A hazard term appears anywhere in the supplied blobs (primary_fault / perception / fingerprint)."""
    blob = " ".join(json.dumps(c, default=str) if not isinstance(c, str) else c for c in chunks)
    return bool(_HAZARD_RE.search(blob) or _HV_RE.search(blob))


# ---- LangGraph I/O ---------------------------------------------------------
class GraphInput(BaseModel):
    """The REAL vision payload (build-doc section 2). Extra vision keys are tolerated."""
    model_config = {"extra": "allow"}

    issue_text_received: str = ""
    perception: Dict[str, Any] = Field(default_factory=dict)
    history_match: Dict[str, Any] = Field(default_factory=dict)
    asset_id: str = ""
    site_id: str = ""
    caseId: str = ""  # FOREMAN case id (external key) — routing key for the live UI feed


class GraphOutput(BaseModel):
    """Build-doc section 3 — the detailed reasoned object."""
    case: Dict[str, Any] = Field(default_factory=dict)
    diagnosis: Dict[str, Any] = Field(default_factory=dict)
    risk: Dict[str, Any] = Field(default_factory=dict)
    safety_gate: Dict[str, Any] = Field(default_factory=dict)
    auto_resolve_blocked: bool = False
    invoked: List[Dict[str, Any]] = Field(default_factory=list)
    not_invoked: List[Dict[str, Any]] = Field(default_factory=list)
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    worker_message: str = ""   # short English reply to send back to the worker (the recommended actions)
    report_url: str = ""       # pre-signed (read) URL to the relevant reference PDF; "" if minting failed
    errors: List[str] = Field(default_factory=list)


# ---- Router structured-output schema --------------------------------------
class _Decision(BaseModel):
    id: str
    invoke: bool
    why: str = ""


class _RouterOut(BaseModel):
    decisions: List[_Decision] = Field(default_factory=list)


_ROUTER_SYS = (
    "You are FOREMAN's routing brain. You decide which downstream specialist agents to invoke "
    "for a single field-maintenance case. You are given: the diagnosis ENGINE findings, the "
    "PRIMARY FAULT, the HISTORY block, and an INVOKE_WHEN manifest describing the trigger "
    "condition for each of the 10 specialist ids.\n"
    "For EACH of the 10 ids return {id, invoke, why}. Set invoke=true ONLY when that id's "
    "invoke_when condition is genuinely satisfied by this case; the `why` must cite the concrete "
    "evidence (or, when false, why the trigger is not met).\n"
    "History matters: a RELATED recurrence after a prior re-crimp/repair strengthens "
    "fleet_blast_radius (a systemic install/crew issue) and keeps warranty_entitlement / "
    "vendor_supply_chain OFF unless a fleet audit proves a procurement substitution. An "
    "already-hard-failed part keeps telemetry_predictive OFF (no trend left to decide). "
    "Do not invent triggers; ground every decision in the manifest."
)


async def _route(engine: dict, primary_fault: dict, history: dict, errors: list) -> Dict[str, _Decision]:
    """Hybrid router (step 2): ask the frontier LLM for a per-id decision. Degrades to all-false."""
    payload = {
        "engine_findings": {
            "root_cause":    g(engine, "root_cause"),
            "recommendation": g(engine, "recommendation"),
            "confidence":    engine.get("confidence"),
            "skill_hit":     g(engine, "skill_hit", default=None),
            "fingerprint":   g(engine, "fingerprint", default={}),
            "safety":        g(engine, "safety", "engine_safety"),
            "systemic_hint": engine.get("systemic_hint"),
        },
        "primary_fault": primary_fault,
        "history":       history,
        "invoke_when":   INVOKE_WHEN,
    }
    try:
        llm = UiPathChat(model=ROUTER_MODEL)
        router = llm.with_structured_output(_RouterOut)
        res = await router.ainvoke([
            SystemMessage(_ROUTER_SYS),
            HumanMessage(json.dumps(payload, default=str)),
        ])
        return {d.id: d for d in res.decisions if d.id in PROC}
    except Exception as e:  # never throw out of the node
        errors.append(f"router:{type(e).__name__}:{e}")
        return {}


# ---- Specialist input builders (step 3 — copies, never invents) ------------
def _build_inputs(invoked_ids, n, engine, primary_fault, fp) -> Dict[str, dict]:
    failure_mode    = g(fp, "failure_mode") or g(primary_fault, "type")
    component       = g(fp, "component") or g(primary_fault, "component")
    equipment_class = g(fp, "equipment_class")
    severity        = g(primary_fault, "severity")
    recommendation  = g(engine, "recommendation")
    root_cause      = g(engine, "root_cause")
    engine_safety   = g(engine, "safety", "engine_safety")

    builders = {
        "safety_compliance": lambda: {
            "fault_type": failure_mode or g(primary_fault, "type"),
            "component": component or g(primary_fault, "component"),
            "severity": severity,
            "equipment_class": equipment_class,
            "skill_hit": g(engine, "skill_hit", default=None),
            "engine_safety": engine_safety,
        },
        "fleet_blast_radius": lambda: {
            "asset_id": n["asset_id"],
            "batch_id": n["batch_id"],
            "failure_mode": failure_mode or g(primary_fault, "type"),
            "mode": "investigate",
        },
        "parts_logistics": lambda: {
            "fix": recommendation,
            "required_parts": [],
            "equipment_class": equipment_class,
        },
        "field_dispatch": lambda: {
            "site_id": n["site_id"],
            "required_cert": "pv_certified" if str(equipment_class).startswith("pv") else "",
            "fix_kind": recommendation,
        },
        "site_access_weather": lambda: {
            "site_id": n["site_id"],
            "fix_kind": recommendation,
        },
        "warranty_entitlement": lambda: {
            "asset_id": n["asset_id"],
            "site_id": n["site_id"],
            "root_cause": root_cause,
        },
        "sla_commercial_impact": lambda: {
            "site_id": n["site_id"],
            "severity": severity,
        },
        "vendor_supply_chain": lambda: {
            "vendor": g(engine, "vendor"),
            "batch_id": n["batch_id"],
            "root_cause": root_cause,
        },
        "telemetry_predictive": lambda: {
            "asset_id": n["asset_id"],
            "fault": failure_mode or g(primary_fault, "type"),
        },
        "cost_optimization": lambda: {
            "asset_id": n["asset_id"],
            "fix": recommendation,
        },
    }
    return {i: builders[i]() for i in invoked_ids if i in builders}


# ---- OPTIONAL risk rationale (LLM EXPLAINS the score; never produces it) ---
async def _risk_rationale(score, band, contributors, history, errors) -> str:
    """One plain-English sentence explaining the DETERMINISTIC score. The model is told the
    number/band are fixed and must not recompute or change them — pure phrasing of risk_score()'s
    output. Always falls back to a code-built string; never throws, never affects the gate."""
    code_fallback = (f"Risk {band} (score {score})"
                     + (" driven by: " + ", ".join(c["factor"] for c in contributors) if contributors
                        else " — no aggravating factors detected."))
    if not contributors:
        return code_fallback
    try:
        llm = UiPathChat(model=RATIONALE_MODEL)
        facts = {
            "score": score, "band": band, "contributors": contributors,
            "recurrence": {"is_recurrence": history.get("is_recurrence"),
                           "recurrence_count": history.get("recurrence_count")},
        }
        sys = SystemMessage(
            "You write ONE plain-English sentence explaining a field-maintenance risk score to a human. "
            "The score and band are FIXED and were computed by a deterministic policy elsewhere — do NOT "
            "recompute, change, second-guess, or invent them. Explain WHY the band holds using ONLY the "
            "supplied contributor factors, leading with the biggest drivers. No new facts, no numbers other "
            "than those given, max ~40 words."
        )
        res = await llm.ainvoke([sys, HumanMessage(json.dumps(facts, default=str))])
        txt = (res.content or "").strip()
        return txt or code_fallback
    except Exception as e:  # never throw out of the node
        errors.append(f"risk_rationale:{type(e).__name__}:{e}")
        return code_fallback


# ---- action_plan + summary (step 6) ---------------------------------------
def _build_action_plan(safety, parts, dispatch, weather, fleet, parts_on, dispatch_on,
                       weather_on, fleet_on) -> List[Dict[str, Any]]:
    """Order: SAFETY -> PARTS -> CREW -> WINDOW -> FLEET AUDIT. Isolation FIRST."""
    plan: List[Dict[str, Any]] = []

    def step(category, action, source):
        plan.append({"order": len(plan) + 1, "category": category, "action": action, "source": source})

    # 1) SAFETY — isolation first, then clear blockers
    if safety.get("safety_critical"):
        protocol = g(safety, "protocol")
        step("SAFETY", f"ISOLATE & MAKE SAFE FIRST — {protocol}" if protocol
             else "ISOLATE & MAKE SAFE FIRST — follow site lockout/tagout before any work",
             "foreman-safety")
        for b in (safety.get("blockers") or []):
            step("SAFETY", f"Clear safety blocker before work: {b}", "foreman-safety")

    # 2) PARTS — stock / lead / substitute
    if parts_on:
        if parts.get("blocks_fix"):
            sub = g(parts, "substitute", default=None)
            step("PARTS", f"Required part unavailable — fix BLOCKED"
                 + (f"; evaluate substitute {sub}" if sub else "; no valid substitute on hand"),
                 "foreman-parts")
        elif parts.get("in_stock"):
            step("PARTS", f"Parts in stock at {g(parts, 'location') or 'depot'} — pull for the job",
                 "foreman-parts")
        elif int(parts.get("lead_time_days", 0) or 0) > 0:
            step("PARTS", f"Order parts — lead time {parts.get('lead_time_days')} day(s)", "foreman-parts")

    # 3) CREW — certified crew + ETA/route
    if dispatch_on:
        if dispatch.get("crew_id"):
            cert = "certified" if dispatch.get("certification_ok") else "NOT certified — escalate"
            step("CREW", f"Dispatch crew {dispatch.get('crew_id')} ({cert}); ETA "
                 f"{dispatch.get('eta_min', 0)} min via {g(dispatch, 'route') or 'planned route'}",
                 "foreman-field-dispatch")
        else:
            step("CREW", "No qualified crew available — escalate for scheduling", "foreman-field-dispatch")

    # 4) WINDOW — earliest safe weather window
    if weather_on:
        earliest = g(weather, "earliest_safe_time", "safe_window")
        wb = weather.get("weather_blockers") or []
        ac = weather.get("access_constraints") or []
        detail = f"earliest safe window {earliest}" if earliest else "no clear window — monitor forecast"
        if wb:
            detail += f"; weather blockers {wb}"
        if ac:
            detail += f"; access constraints {ac}"
        step("WINDOW", f"Schedule into {detail}", "foreman-weather")

    # 5) FLEET AUDIT — at-risk siblings
    if fleet_on and fleet.get("systemic"):
        cnt = fleet.get("affected_count", 0)
        assets = fleet.get("affected_assets") or fleet.get("affected_sites") or []
        step("FLEET AUDIT", f"Audit {cnt} at-risk sibling asset(s) sharing batch/crew/lot"
             + (f": {assets}" if assets else "")
             + (f" — {g(fleet, 'recommendation')}" if g(fleet, 'recommendation') else ""),
             "foreman-fleet-blast-radius")

    return plan


def _build_summary(n, engine, score, band, auto_resolve_blocked, safety, fleet, plan) -> str:
    h = n["history"]
    root_cause = g(engine, "root_cause") or "undetermined root cause"
    rec = g(engine, "recommendation") or "no recommendation produced"
    parts_summary = []

    diag = f"Diagnosis: {root_cause}. Recommended fix: {rec}."
    risk_txt = f"Risk is {band} (score {score})."
    gate_txt = ("Auto-resolve is BLOCKED — a human safety gate is required."
                if auto_resolve_blocked else "Auto-resolve is permitted.")
    recur_txt = ""
    if h.get("is_recurrence") or int(h.get("recurrence_count", 0) or 0) > 0:
        recur_txt = (f" NOTE: this RECURRED after a prior repair"
                     + (f" ({h.get('past_resolution')})" if h.get("past_resolution") else "")
                     + f" — a fleet audit and a crew/process review matter, not just a re-fix.")
    if fleet.get("systemic"):
        recur_txt += (f" Fleet exposure: {fleet.get('affected_count', 0)} sibling asset(s) at risk.")
    plan_txt = " Plan: " + " | ".join(
        f"{i+1}) {s['category']}: {s['action']}" for i, s in enumerate(plan)
    ) if plan else " No action steps were generated."

    return f"{diag} {risk_txt} {gate_txt}{recur_txt}{plan_txt}"


# ---- worker reply (LLM; ENGLISH-ONLY; "screenshot" WhatsApp layout) --------
async def _worker_message(asset_id, site_id, diagnosis, fleet, safety, sop_attached, errors) -> str:
    """Short WhatsApp update to the worker, ALWAYS in plain English, in the FOREMAN screenshot
    layout: 'Analysis complete for <asset>' / Root cause / ⚠️ Action / Fleet / SOP attached.
    Pulls whatever fields it needs (asset, root cause, recommended action, fleet, crew/ETA) — not
    just a summary. The SOP PDF is sent as the WhatsApp attachment (which shows its own filename),
    so the text only says it's attached — no filename line. LLM phrasing; safety warning enforced
    in the code fallback too. Never throws."""
    safety_critical = bool(safety.get("safety_critical"))
    recommendation = g(diagnosis, "recommendation")   # the ACTUAL action steps
    root_cause = g(diagnosis, "root_cause")
    fleet_systemic = bool(fleet.get("systemic"))
    fleet_count = int(fleet.get("affected_count", 0) or 0)
    facts = {
        "asset_id": asset_id,
        "site_id": site_id,
        "root_cause": root_cause,
        "what_to_do": recommendation,
        "safety_critical": safety_critical,
        "fleet_systemic": fleet_systemic,
        "fleet_count": fleet_count,
        "sop_attached": bool(sop_attached),
    }
    try:
        llm = UiPathChat(model=WORKER_MSG_MODEL, temperature=0)
        sys = SystemMessage(
            "You are FOREMAN, posting a short WhatsApp update to the field worker who reported a fault. "
            "Write in plain ENGLISH only (never Hindi/Hinglish). Be concise and action-first. Follow THIS "
            "EXACT structure and order (blank line between blocks):\n\n"
            "Analysis complete for <asset_id>.\n\n"
            "Root cause: <one line, phrased as cause → effect → risk, from root_cause>.\n\n"
            "⚠️ Action: <the key steps from what_to_do condensed to 1-2 sentences, ISOLATION / DC-safe FIRST>."
            " If safety_critical, add 'Do NOT touch the live connector.' Do NOT mention any crew, ETA, or "
            "dispatch.\n\n"
            "<Include this Fleet line ONLY if fleet_systemic is true, else omit the whole line:> "
            "Fleet: <fleet_count> sibling strings share the same install crew / batch / lot — a crew audit "
            "is being raised.\n\n"
            "<Include this final line ONLY if sop_attached is true, else omit it:> "
            "Step-by-step SOP attached.\n\n"
            "RULES: use ONLY the facts provided — never invent parts, counts, names, or times. Do NOT write "
            "any filename (the attached PDF shows its own name). Use exactly ONE emoji: ⚠️ on the Action line. "
            "Keep it tight, like a real WhatsApp message."
        )
        res = await llm.ainvoke([sys, HumanMessage(json.dumps(facts, default=str, ensure_ascii=False))])
        txt = (res.content or "").strip()
        if txt:
            return txt
    except Exception as e:  # never throw out of the node
        errors.append(f"worker_message:{type(e).__name__}:{e}")
    # deterministic English fallback (always safe) — same screenshot layout
    blocks = [f"Analysis complete for {asset_id}." if asset_id else "Analysis complete."]
    if root_cause:
        blocks.append(f"Root cause: {root_cause}")
    action = "⚠️ Action: " + (recommendation or "follow the recommended repair steps.")
    if safety_critical:
        action += " Do NOT touch the live connector."
    blocks.append(action)
    if fleet_systemic:
        blocks.append(f"Fleet: {fleet_count} sibling strings share the same install crew / batch / lot "
                      "— a crew audit is being raised.")
    if sop_attached:
        blocks.append("Step-by-step SOP attached.")
    return "\n\n".join(blocks)


# ---- reference PDF pre-signed URL -----------------------------------------
def _pick_report_blob(diagnosis) -> str:
    """Choose the reference-doc filename: the FIRST citation from the diagnosis (engine
    citations are exact source filenames); falls back to the mc4 spec. Used for BOTH the
    SOP line in the worker message and the pre-signed report_url."""
    citations = g(diagnosis, "citations", default=[]) or []
    if isinstance(citations, list) and citations and isinstance(citations[0], str) and citations[0].strip():
        return citations[0].strip()
    return REPORT_DEFAULT_BLOB


async def _report_url(sdk, blob, errors) -> str:
    """Mint a temporary (read) pre-signed URL for `blob` in the `foreman-context` bucket.

    Minted THROUGH the authenticated SDK client (`request_async`) exactly like the SDK's
    own `buckets.download_async` does — so the call originates inside Orchestrator and does
    NOT hit the Cloudflare 1010 block a raw HTTP call would. Never throws."""
    blob = blob or REPORT_DEFAULT_BLOB
    try:
        bucket = await sdk.buckets.retrieve_async(name=REPORT_BUCKET, folder_path=FOLDER)
        spec = sdk.buckets._retrieve_readUri_spec(bucket.id, blob, folder_path=FOLDER)
        params = dict(spec.params or {})
        params["expiryInMinutes"] = REPORT_EXPIRY_MIN
        resp = await sdk.buckets.request_async(
            spec.method, url=spec.endpoint, params=params, headers=spec.headers
        )
        data = resp.json()
        uri = data.get("Uri") or data.get("uri") or ""
        if not uri:
            errors.append(f"report_url:GetReadUri returned no Uri for '{blob}'")
        return uri
    except Exception as e:  # never throw out of the node
        errors.append(f"report_url:{type(e).__name__}:{e}")
        return ""


# ===========================================================================
# FOREMAN UI live feed (additive telemetry — never alters orchestration)
# ===========================================================================
from foreman_emit import Emitter, configure as fm_configure

# supervisor specialist id -> UI crew-card AgentId. The rest render as log lines.
_UI_AGENT = {
    "fleet_blast_radius":   "fleet",
    "warranty_entitlement": "entitlement",
    "sla_commercial_impact": "sla",
}
_UI_SOURCE = {
    "safety_compliance": "Safety", "parts_logistics": "Parts",
    "field_dispatch": "Dispatch", "site_access_weather": "Weather",
    "vendor_supply_chain": "Vendor", "telemetry_predictive": "Telemetry",
    "cost_optimization": "Cost",
}


def _configure_emit_from_assets(sdk: UiPath) -> None:
    """Pull FOREMAN_BACKEND_URL (Text asset) + FOREMAN_INGEST_SECRET (Credential
    asset -> password) from Orchestrator; fall back to env. Never raises."""
    backend = secret = None
    try:
        a = sdk.assets.retrieve(name="FOREMAN_BACKEND_URL")
        backend = getattr(a, "value", None) or getattr(a, "string_value", None)
    except Exception as exc:
        print(f"[foreman-supervisor] FOREMAN_BACKEND_URL not read ({exc}); env default")
    try:
        secret = sdk.assets.retrieve_credential(name="FOREMAN_INGEST_SECRET")
    except Exception as exc:
        print(f"[foreman-supervisor] FOREMAN_INGEST_SECRET not read ({exc}); env default")
    fm_configure(backend=backend, secret=str(secret) if secret else None)


def _ui_specialist_log(i: str, r: dict) -> str:
    if not r:
        return f"{_UI_SOURCE.get(i, i)}: no output"
    if i == "safety_compliance":
        return ("Safety-critical — LOTO / de-energise gate required"
                if r.get("safety_critical") else "Safety check cleared")
    if i == "parts_logistics":
        return (f"Parts in stock at {g(r, 'location') or 'depot'}" if r.get("in_stock")
                else "Required part unavailable — fix blocked" if r.get("blocks_fix")
                else "Parts assessed")
    if i == "field_dispatch":
        return f"Crew {g(r, 'crew_id') or '?'} · ETA {r.get('eta_min', '?')} min · {g(r, 'route') or 'route planned'}"
    if i == "site_access_weather":
        return g(r, "earliest_safe_time", "safe_window") or "weather window assessed"
    return f"{_UI_SOURCE.get(i, i)} assessed"


def _ui_card_headline(i: str, r: dict) -> str:
    if i == "warranty_entitlement":
        return ("Covered under warranty" if (r.get("in_warranty") or r.get("covered"))
                else "Field workmanship — not warranty")
    if i == "sla_commercial_impact":
        return g(r, "band", "level", default="") or "SLA exposure assessed"
    return i


def _ui_fleet_view(r: dict) -> dict:
    """Build the UI FleetView (nodes/edges) from the fleet-blast specialist result.
    Internally guarded — never raises into the node."""
    try:
        assets = list(r.get("affected_assets") or r.get("affected_sites") or [])
        crit = list(r.get("criticality_rank") or [])
        nodes, edges = [], []
        na = max(1, len(assets))
        for idx, a in enumerate(assets):
            nodes.append({
                "id": a, "label": a, "type": "asset",
                "status": "failing" if idx == 0 else "at_risk",
                "x": round(15 + 70 * idx / (na - 1), 1) if na > 1 else 50, "y": 72,
            })
        tmap = {"Batch": "batch", "Crew": "crew", "PartLot": "part_lot", "Vendor": "vendor"}
        rmap = {"Batch": "FROM_BATCH", "Crew": "INSTALLED_BY", "PartLot": "USES_PART_LOT", "Vendor": "FROM_VENDOR"}
        nc = max(1, len(crit))
        for j, f in enumerate(crit):
            fid = f.get("factor")
            ft = f.get("factorType", "")
            if not fid:
                continue
            hub = ft in ("Crew", "PartLot")
            nodes.append({
                "id": fid, "label": fid, "type": tmap.get(ft, "batch"),
                "hub": hub, "status": "at_risk" if hub else "healthy",
                "x": round(20 + 60 * j / (nc - 1), 1) if nc > 1 else 50, "y": 26,
            })
            for a in assets:
                edges.append({"from": a, "to": fid, "rel": rmap.get(ft, "SHARES"), "hot": hub})
        return {
            "systemic": bool(r.get("systemic")), "affected": assets,
            "nodes": nodes, "edges": edges, "unitNoun": "string",
            "criticality": [{"factor": f.get("factor"), "factorType": f.get("factorType"),
                             "count": f.get("count", 0)} for f in crit],
            "batch_id": r.get("batch_id", ""), "affected_sites": r.get("affected_sites", []),
        }
    except Exception:
        return {"systemic": bool(r.get("systemic")),
                "affected": list(r.get("affected_assets") or []), "nodes": [], "edges": []}


# ---- THE NODE -------------------------------------------------------------
async def supervise(state: GraphInput) -> GraphOutput:
    errors: List[str] = []

    # 0) NORMALIZE
    vision_input = state.model_dump()
    n = normalize(vision_input)
    primary_fault = n["primary_fault"]

    # 1) ALWAYS-ON ENGINE (unconditional, first)
    sdk = UiPath()

    # --- FOREMAN UI live feed: open the Investigate stage + supervisor card ---
    _case_id = (getattr(state, "caseId", "") or "").strip() or f"CASE-{n['site_id'] or n['asset_id'] or 'SUP'}"
    try:
        _configure_emit_from_assets(sdk)
    except Exception as e:
        errors.append(f"ui_cfg:{e}")
    fm = Emitter(_case_id)
    try:
        fm.stage("investigate")
        fm.agent_running("supervisor")
        fm.log("investigate", "Supervisor", "Running diagnosis + assembling dynamic crew", "agent")
    except Exception as e:
        errors.append(f"ui_emit_start:{e}")

    engine = await invoke(sdk, ENGINE, {
        "perception": n["perception"],
        "site_id": n["site_id"],
        "asset_id": n["asset_id"],
        "worker_text": n["worker_text"],
    })
    if not engine:
        errors.append(f"{ENGINE}:engine failed — degrading to primary_fault + history")
        engine = {}

    fp = g(engine, "fingerprint", default={}) or {}
    engine_safety = g(engine, "safety", "engine_safety")
    failure_mode = g(fp, "failure_mode") or g(primary_fault, "type")
    component = g(fp, "component") or g(primary_fault, "component")
    equipment_class = g(fp, "equipment_class")

    diagnosis = {
        "root_cause": g(engine, "root_cause"),
        "recommendation": g(engine, "recommendation"),
        "confidence": engine.get("confidence"),
        "skill_hit": g(engine, "skill_hit", default=None),
        "skill_status": g(engine, "skill_status", default=None),
        "match_type": g(engine, "match_type", default=None),
        "citations": g(engine, "citations", default=[]),
        "fingerprint": {
            "equipment_class": equipment_class,
            "component": component,
            "failure_mode": failure_mode,
        },
        "engine_safety": engine_safety,
        "systemic_hint": engine.get("systemic_hint"),
    }

    # --- FOREMAN UI: root-cause (diagnosis engine) finding ---
    try:
        fm.agent_assembled("rootcause")
        fm.agent_running("rootcause")
        if diagnosis.get("skill_hit"):
            fm.skill_matched({"id": diagnosis["skill_hit"],
                              "status": diagnosis.get("skill_status") or "candidate",
                              "source": "skill library"})
        _rec = diagnosis.get("recommendation") or ""
        fm.agent_completed("rootcause",
                           headline=diagnosis.get("root_cause") or "Diagnosis ready",
                           detail=(_rec.split("\n")[0][:160] if _rec else None),
                           confidence=diagnosis.get("confidence"),
                           citations=diagnosis.get("citations") or None)
    except Exception as e:
        errors.append(f"ui_emit_rootcause:{e}")

    # 2) ROUTE (hybrid) — LLM proposes, code enforces the safety floor
    decisions = await _route(engine, primary_fault, n["history"], errors)

    invoke_map: Dict[str, Dict[str, Any]] = {}
    for i in PROC:
        d = decisions.get(i)
        invoke_map[i] = {"invoke": bool(d.invoke) if d else False,
                         "why": (d.why if d else "router did not return a decision; defaulted OFF")}

    # SAFETY FLOOR (deterministic, overrides the LLM)
    floor_hit = (str(engine_safety).lower() == "critical"
                 or _hazard_present(primary_fault, n["perception"], fp))
    if floor_hit:
        invoke_map["safety_compliance"] = {
            "invoke": True,
            "why": "SAFETY FLOOR (code-forced): engine_safety==critical or a hazard term "
                   "(arc/fire/burn/melt/exposed/shock/HV/short/...) present in fault/perception/fingerprint",
        }

    invoked_ids = [i for i in PROC if invoke_map[i]["invoke"]]
    not_invoked = [{"id": i, "why": invoke_map[i]["why"]} for i in PROC if not invoke_map[i]["invoke"]]

    # --- FOREMAN UI: announce the dynamic crew the router chose ---
    try:
        fm.log("investigate", "Supervisor", "Crew dispatched: " + (", ".join(invoked_ids) or "none"), "agent")
        for _i in invoked_ids:
            if _i == "fleet_blast_radius":
                continue  # the fleet agent emits its own card + real Neo4j graph
            _ui = _UI_AGENT.get(_i)
            if _ui:
                fm.agent_assembled(_ui)
                fm.agent_running(_ui)
    except Exception as e:
        errors.append(f"ui_emit_crew:{e}")

    # 3) BUILD INPUTS
    inputs = _build_inputs(invoked_ids, n, engine, primary_fault, fp)

    # Option 2: let the fleet agent emit its OWN real Neo4j graph. It reads the
    # backend URL + secret from the Orchestrator assets itself; we only hand it
    # the case id (per-case routing key) so its fleet.ready lands on the right card.
    if "fleet_blast_radius" in inputs:
        inputs["fleet_blast_radius"]["case_id"] = _case_id

    # 4) INVOKE CONCURRENTLY (Pattern A)
    results_list = await asyncio.gather(
        *[invoke(sdk, PROC[i], inputs[i]) for i in invoked_ids]
    )
    results: Dict[str, dict] = dict(zip(invoked_ids, results_list))
    invoked: List[Dict[str, Any]] = []
    for i in invoked_ids:
        r = results.get(i) or {}
        if not r:
            errors.append(f"{PROC[i]}:no output")
        invoked.append({
            "id": i, "process": PROC[i], "ok": bool(r),
            "why": invoke_map[i]["why"], "result": r,
        })

    # --- FOREMAN UI: crew results (cards for fleet/entitlement/sla; logs for the rest) ---
    try:
        for _i in invoked_ids:
            if _i == "fleet_blast_radius":
                continue  # the fleet agent self-emits its real Neo4j fleet.ready + card
            _r = results.get(_i) or {}
            _ui = _UI_AGENT.get(_i)
            if _ui == "fleet":
                if _r.get("systemic"):
                    fm.fleet_ready(_ui_fleet_view(_r))
                fm.agent_completed("fleet",
                                   headline=(f"{_r.get('affected_count', 0)} assets at risk via shared crew/lot"
                                             if _r.get("systemic") else "No fleet exposure"),
                                   detail=g(_r, "recommendation") or None)
            elif _ui:
                fm.agent_completed(_ui, headline=_ui_card_headline(_i, _r))
            else:
                fm.log("investigate", _UI_SOURCE.get(_i, _i), _ui_specialist_log(_i, _r), "info")
    except Exception as e:
        errors.append(f"ui_emit_results:{e}")

    # 5) RISK + GATE
    safety   = results.get("safety_compliance", {}) or {}
    fleet    = results.get("fleet_blast_radius", {}) or {}
    parts    = results.get("parts_logistics", {}) or {}
    weather  = results.get("site_access_weather", {}) or {}
    dispatch = results.get("field_dispatch", {}) or {}

    score, band, contributors = risk_score(engine, safety, fleet, parts, weather, dispatch, n["history"])
    auto_resolve_blocked = bool(safety.get("can_block_auto_resolve") or safety.get("safety_critical"))
    # OPTIONAL: LLM phrasing of the score — score/band/gate above stay authoritative
    risk_rationale = await _risk_rationale(score, band, contributors, n["history"], errors)

    # --- FOREMAN UI: risk meter + merged investigation card ---
    try:
        fm.risk_scored(score)  # 0..100 -> normalized to 0..1 by foreman_emit
        fm.investigation_ready({
            "root_cause": diagnosis.get("root_cause", ""),
            "confidence": diagnosis.get("confidence") or 0,
            "alternatives_ruled_out": g(engine, "alternatives_ruled_out", default=[]) or [],
            "systemic": bool(fleet.get("systemic")),
            "fleet_affected": int(fleet.get("affected_count", 0) or 0),
            "risk_score": score,
            "recommendation": diagnosis.get("recommendation", ""),
            "eta_min": int(dispatch.get("eta_min", 0) or 0) or None,
        })
    except Exception as e:
        errors.append(f"ui_emit_risk:{e}")

    # 6) MERGE -> action_plan + summary
    plan = _build_action_plan(
        safety, parts, dispatch, weather, fleet,
        parts_on=("parts_logistics" in results),
        dispatch_on=("field_dispatch" in results),
        weather_on=("site_access_weather" in results),
        fleet_on=("fleet_blast_radius" in results),
    )
    summary = _build_summary(n, engine, score, band, auto_resolve_blocked, safety, fleet, plan)
    sop_blob = _pick_report_blob(diagnosis)            # reference doc minted as the SOP attachment
    report_url = await _report_url(sdk, sop_blob, errors)
    worker_message = await _worker_message(            # "SOP attached" only if the URL actually minted
        n["asset_id"], n["site_id"], diagnosis, fleet, safety, bool(report_url), errors
    )

    # --- FOREMAN UI: supervisor done + worker reply bubble ---
    try:
        fm.agent_completed("supervisor",
                           headline=(f"Plan ready · risk {band} ({score}) · "
                                     + ("auto-resolve blocked" if auto_resolve_blocked else "auto-resolve ok")),
                           detail=(summary or "")[:150])
        if worker_message:
            fm.message("foreman", worker_message)
    except Exception as e:
        errors.append(f"ui_emit_done:{e}")

    # 7) RETURN section-3 object
    return GraphOutput(
        case={
            "asset_id": n["asset_id"],
            "site_id": n["site_id"],
            "batch_id": n["batch_id"],
            "worker_text": n["worker_text"],
            "primary_fault": primary_fault,
            "history": n["history"],
        },
        diagnosis=diagnosis,
        risk={"score": score, "band": band, "contributors": contributors, "rationale": risk_rationale},
        safety_gate={
            "safety_critical": bool(safety.get("safety_critical")),
            "can_block_auto_resolve": bool(safety.get("can_block_auto_resolve")),
            "protocol": g(safety, "protocol"),
            "standard_clause": safety.get("standard_clause") or [],
            "blockers": safety.get("blockers") or [],
            "floor_forced": bool(floor_hit),
        },
        auto_resolve_blocked=auto_resolve_blocked,
        invoked=invoked,
        not_invoked=not_invoked,
        action_plan=plan,
        summary=summary,
        worker_message=worker_message,
        report_url=report_url,
        errors=errors,
    )


# ---- GRAPH ----------------------------------------------------------------
builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("supervise", supervise)
builder.add_edge(START, "supervise")
builder.add_edge("supervise", END)
graph = builder.compile()
