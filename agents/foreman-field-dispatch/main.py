"""FOREMAN Field-Dispatch agent (the crew-routing check).

Given a site, a required certification, and the kind of fix needed, choose the
best field crew to send: one that is available, ideally holds the required
certification, whose skills cover the fix, and is closest by drive time. The
Supervisor calls this once a fix has been diagnosed and cleared by parts/safety,
to turn "this needs doing at SITE X" into "send CREW Y, ~N minutes out".

CONTRACT
  input : { site_id: str, required_cert: str, fix_kind: str }
  output: one flat object (see GraphOutput) — strict, pydantic-validated, no prose.

READS (real, verified live in DefaultTenant):
  * Data Fabric ``Crew`` — flattened fields: crewid, name, region, skills
    (";"-list), certifications (";"-list), homesite (a site_id), available
    ("true"/"false" STRING).
  * Data Fabric ``Site`` — flattened fields: siteid, lat (float), lon (float).
  Read via ``sdk.entities.retrieve_records(entity_id)``; name->id via
  ``list_entities()``. All id matching is case-insensitive.

DESIGN
  * The match and the ETA are DETERMINISTIC, computed in code:
      - certification_ok = required_cert is a token in the crew's certifications
      - skill_match      = a crew skill token overlaps the fix_kind tokens
      - eta_min / route  = maps.eta_route(home_coords -> target_coords)
  * The LLM (``UiPathChat(model="gpt-4.1-mini-2025-04-14")``) is OPTIONAL: it is
    used ONLY to infer the required certification from ``fix_kind`` when
    ``required_cert`` is empty. It never influences the match or the routing.
  * Selection: among available crews, prefer the certified ones and pick the
    lowest ETA; if none is certified, pick the lowest-ETA crew anyway but report
    certification_ok=false (so the Supervisor sees "a crew exists but isn't
    certified"). If no crew at all -> empty contract.

The LLM + SDK clients are built INSIDE the node so the module imports without
credentials and ``uipath init`` can introspect the graph. The node NEVER throws —
on any failed read it returns the contract shape with a non-empty ``error`` and
neutral values.
"""

import re
from typing import List, Optional, Tuple

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath
from uipath_langchain.chat import UiPathChat

import maps

# --- Configuration ----------------------------------------------------------

CREW_ENTITY = "Crew"
SITE_ENTITY = "Site"
LLM_MODEL = "gpt-4.1-mini-2025-04-14"  # confirmed in this tenant's LLM Gateway
FETCH_LIMIT = 1000                     # bounded fetch; scope/match in Python

# Tokens too generic to count as a skill/cert overlap on their own.
_STOPWORDS = {"the", "a", "an", "of", "to", "and", "or", "for", "on", "at", "in", "re"}


# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Thin input from the Supervisor."""

    site_id: str = Field(default="", description="Target site where the work is")
    required_cert: str = Field(
        default="",
        description="Required certification token; if empty, inferred from fix_kind",
    )
    fix_kind: str = Field(default="", description="The kind of fix needed (free text)")


class GraphOutput(BaseModel):
    """Output contract — ONE flat object (field names/types match the spec)."""

    crew_id: str = ""            # chosen crew, or "" if none qualifies
    skill_match: bool = False    # chosen crew's skills cover the fix_kind
    certification_ok: bool = False  # chosen crew holds the required_cert
    eta_min: int = 0             # minutes from the crew's home_site to site_id (0 if no crew)
    route: str = ""              # human-readable route summary ("" if no crew)
    error: str = ""              # "" if ok


class _CertInfer(BaseModel):
    """The LLM's only job: name the certification a fix_kind implies."""

    required_cert: str = Field(
        default="",
        description="A single certification token implied by the fix (e.g. 'pv_certified'), or ''",
    )


# --- Data Fabric helpers ----------------------------------------------------


def _entity_ids(sdk: UiPath) -> dict:
    """Map entity name -> id (the read endpoint needs the id, not the name)."""
    return {e.name: e.id for e in sdk.entities.list_entities()}


def _rows(sdk: UiPath, entity_id: str) -> List[dict]:
    """All rows of an entity as plain dicts with lowercased keys."""
    resp = sdk.entities.retrieve_records(entity_id, limit=FETCH_LIMIT)
    out: List[dict] = []
    for rec in getattr(resp, "items", None) or []:
        if hasattr(rec, "model_dump"):
            try:
                data = rec.model_dump()
            except Exception:
                data = {}
        elif isinstance(rec, dict):
            data = dict(rec)
        else:
            data = {}
        out.append({str(k).lower(): v for k, v in data.items()})
    return out


def _as_bool(value) -> bool:
    """``available`` arrives as the STRING 'true'/'false' (not a real bool)."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _as_coords(row: dict) -> Optional[Tuple[float, float]]:
    """Pull (lat, lon) from a Site row, or None if not numeric."""
    try:
        return float(row["lat"]), float(row["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def _site_coords(sites: List[dict], site_id) -> Optional[Tuple[float, float]]:
    """Resolve a site_id (case-insensitive) to (lat, lon), or None."""
    if not site_id:
        return None
    key = str(site_id).strip().lower()
    row = next((s for s in sites if str(s.get("siteid", "")).strip().lower() == key), None)
    return _as_coords(row) if row else None


# --- Match helpers (deterministic) ------------------------------------------


def _tokens(text: str) -> set:
    """Lowercased alphanumeric tokens, dropping stopwords/empties."""
    raw = re.split(r"[^a-z0-9]+", (text or "").lower())
    return {t for t in raw if t and t not in _STOPWORDS}


def _cert_ok(certifications: str, required_cert: str) -> bool:
    """True if required_cert is one of the crew's ';'-separated certifications."""
    need = (required_cert or "").strip().lower()
    if not need:
        return False
    held = {c.strip().lower() for c in str(certifications or "").split(";") if c.strip()}
    return need in held


def _skill_match(skills: str, fix_kind: str) -> bool:
    """True if any skill token relates to a fix_kind token (equality or
    substring of length >= 4, so 'termination' covers 're-termination')."""
    fix_toks = _tokens(fix_kind)
    if not fix_toks:
        return False
    skill_toks = _tokens(skills)
    for s in skill_toks:
        for f in fix_toks:
            if s == f:
                return True
            if len(s) >= 4 and len(f) >= 4 and (s in f or f in s):
                return True
    return False


# --- Required-cert inference (the only LLM use) -----------------------------

_SYSTEM = (
    "You are FOREMAN's dispatch assistant. Given the KIND OF FIX a field job "
    "needs, name the single certification a crew must hold to perform it safely, "
    "as one lowercase token (e.g. 'pv_certified', 'dc_arc', 'rf_certified', "
    "'hv_certified'). If no specific certification is implied, return an empty "
    "string. Return ONLY the structured field."
)


async def _infer_cert(fix_kind: str) -> str:
    """Ask the LLM to infer the required cert from fix_kind. Best-effort: any
    failure yields '' (no certification requirement)."""
    try:
        llm = UiPathChat(model=LLM_MODEL, temperature=0).with_structured_output(_CertInfer)
        out: _CertInfer = await llm.ainvoke(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"KIND OF FIX: {fix_kind or '(none)'}"},
            ]
        )
        return (out.required_cert or "").strip()
    except Exception:
        return ""


# --- Node -------------------------------------------------------------------


async def dispatch(state: GraphInput) -> GraphOutput:
    site_id = (state.site_id or "").strip()
    required_cert = (state.required_cert or "").strip()
    fix_kind = (state.fix_kind or "").strip()

    try:
        sdk = UiPath()
        ids = _entity_ids(sdk)
        for ent in (CREW_ENTITY, SITE_ENTITY):
            if ent not in ids:
                return GraphOutput(error=f"{ent} entity not found")

        sites = _rows(sdk, ids[SITE_ENTITY])

        # 1. Target coords. Missing -> can't route, return neutral with error.
        target = _site_coords(sites, site_id)
        if target is None:
            return GraphOutput(error=f"site '{site_id}' not found or has no coordinates")

        # 2. Required cert: use the input; infer from fix_kind only if empty.
        if not required_cert:
            required_cert = await _infer_cert(fix_kind)

        # 3. Available crews.
        crews = _rows(sdk, ids[CREW_ENTITY])
        candidates = [c for c in crews if _as_bool(c.get("available"))]
        if not candidates:
            return GraphOutput(error="")  # no crew available; empty, non-blocking

        # 4. Score each candidate (cert / skill / ETA), deterministically.
        scored = []
        for c in candidates:
            home = _site_coords(sites, c.get("homesite"))
            if home is not None:
                routing = await maps.eta_route(home, target)
                eta_min, route, routable = int(routing["eta_min"]), routing["route"], True
            else:
                eta_min, route, routable = 0, "", False  # unroutable: no home coords
            scored.append(
                {
                    "crew_id": str(c.get("crewid", "") or "").strip(),
                    "certification_ok": _cert_ok(c.get("certifications"), required_cert),
                    "skill_match": _skill_match(c.get("skills"), fix_kind),
                    "eta_min": eta_min,
                    "route": route,
                    # routable crews sort ahead of unroutable ones, then by ETA.
                    "_sort": (0 if routable else 1, eta_min),
                }
            )

        # 5. Prefer certified crews; pick the lowest ETA. Fall back to any crew.
        certified = [s for s in scored if s["certification_ok"]]
        pool = certified or scored
        chosen = min(pool, key=lambda s: s["_sort"])

        return GraphOutput(
            crew_id=chosen["crew_id"],
            skill_match=chosen["skill_match"],
            certification_ok=chosen["certification_ok"],
            eta_min=chosen["eta_min"],
            route=chosen["route"],
            error="",
        )
    except Exception as exc:  # never throw out of the node — return the contract shape
        return GraphOutput(error=f"{type(exc).__name__}: {exc}")


# --- Graph ------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("dispatch", dispatch)
builder.add_edge(START, "dispatch")
builder.add_edge("dispatch", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
