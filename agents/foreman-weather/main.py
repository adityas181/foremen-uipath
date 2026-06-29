"""FOREMAN Weather agent (the go/no-go weather window planner).

Given a SITE and the kind of fix to perform, this agent returns the earliest
safe outdoor work window: a slot that is simultaneously DRY, within DAYLIGHT and
LIGHTNING-FREE (and not blown out by high wind). It reads the site's coordinates
+ environment from Data Fabric and the live forecast / lightning from the
UiPath-HOSTED Weather MCP (streamable HTTP, PAT-authenticated). All numbers fall
out of the real forecast — nothing about the window is hard-coded.

CONTRACT
  input : { site_id: str, fix_kind: str }
  output: { safe_window, weather_blockers[], access_constraints[],
            earliest_safe_time, error }   (strict, pydantic-validated, 5 keys)

READS (real)
  * Data Fabric ``Site``  (siteid, lat, lon, environment, humidity, status) via
    the UiPath SDK — ``retrieve_records`` + name->id, flattened field names.
  * Hosted Weather MCP (AgentHub, folder "Shared/foremen v1") over streamable
    HTTP with a Bearer token: ``get_forecast`` (hourly), ``get_lightning_activity``
    and ``search_location`` (only when the Site has no coordinates).

DESIGN NOTES (verified live against this tenant + the @dangahagan/weather-mcp
server — these differ from the spec's idealized shapes):
  * The MCP tools return human-readable MARKDOWN, not JSON, so the forecast /
    lightning text is PARSED (precip %, wind mph, conditions; safety status).
  * The hourly forecast carries a reliable IANA ``Timezone`` header but the
    daily forecast renders sunrise/sunset with a timezone shift, so DAYLIGHT is
    computed analytically from lat/lon + the slot's UTC instant (NOAA solar
    elevation) rather than parsed — fully deterministic.
  * The MCP bearer is the live SDK session token (``UIPATH_PAT`` overrides);
    ``WEATHER_MCP_URL`` overrides the SDK-resolved server URL.
  * If the hosted MCP can't be reached, an Open-Meteo fallback (no key) supplies
    the same dry+daylight window from structured JSON (lightning omitted) and
    notes itself in ``error`` so the demo still proceeds.
  * The LLM (UiPathChat gpt-4.1-mini) is created INSIDE the node and only PHRASES
    the computed window; every contract field is computed deterministically with
    a code fallback, so the result holds even if the model drifts or errors.

The node NEVER throws — on any failure it returns the contract shape with a
non-empty ``error``.
"""

from __future__ import annotations

import math
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from uipath.platform import UiPath
from uipath.platform.entities.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    QueryFilterOperator,
)
from uipath_langchain.chat import UiPathChat

# --- Configuration ----------------------------------------------------------

FOLDER = "Shared/foremen v1"            # folder the Data Fabric + MCP live in
MCP_SLUG = "weather"                    # hosted Weather MCP server slug
LLM_MODEL = "gpt-4.1-mini-2025-04-14"   # confirmed in this tenant's LLM Gateway

PRECIP_DRY_MAX = 20      # precip probability (%) strictly below this == "dry"
WIND_HIGH_MPH = 25       # sustained wind at/above this == high-wind blocker
GUST_HIGH_MPH = 35       # gusts at/above this == high-wind blocker
DAYLIGHT_ELEV_MIN = -0.833   # solar elevation (deg) above which it is "daylight"
HORIZON_HOURS = 48       # how far ahead we will look for a window
LIGHTNING_HOLD_MIN = 60  # if lightning is active now, hold the next this-many min

# site_id prefix -> city, used only when a Site has no stored coordinates.
CITY_BY_PREFIX = {
    "DEL": "Delhi", "MUM": "Mumbai", "BLR": "Bengaluru", "HYD": "Hyderabad",
    "CHN": "Chennai", "CHE": "Chennai", "KOL": "Kolkata", "PUN": "Pune",
    "AHM": "Ahmedabad", "JAI": "Jaipur", "NG": "Nagpur", "GOA": "Goa",
}

# --- Schemas ----------------------------------------------------------------


class GraphInput(BaseModel):
    """Thin input from the supervisor / dispatcher."""

    site_id: str = Field(default="", description="Site id, e.g. 'DEL-0788'")
    fix_kind: str = Field(
        default="", description="Fix descriptor, e.g. 'outdoor live-electrical DC'"
    )


class GraphOutput(BaseModel):
    """Output contract — EXACTLY these five keys, strict JSON."""

    safe_window: str = ""
    weather_blockers: List[str] = Field(default_factory=list)
    access_constraints: List[str] = Field(default_factory=list)
    earliest_safe_time: str = ""
    error: str = ""


# --- Data Fabric helpers ----------------------------------------------------


def _entity_ids(sdk: UiPath) -> dict:
    """Map entity name -> GUID id (the read endpoint needs the id, not the name)."""
    return {e.name: e.id for e in sdk.entities.list_entities()}


def _df_one(sdk: UiPath, entity_id: str, field: str, value: str):
    """First record where ``entity.field == value`` (case-insensitive), else None."""
    if not value:
        return None
    fg = EntityQueryFilterGroup(
        query_filters=[
            EntityQueryFilter(
                field_name=field, operator=QueryFilterOperator.Equals, value=value
            )
        ]
    )
    resp = sdk.entities.retrieve_records(entity_id, filter_group=fg, limit=1)
    items = getattr(resp, "items", None) or []
    if items:
        return items[0]
    # Case-insensitive fallback: ids may differ only by case from the stored value.
    resp = sdk.entities.retrieve_records(entity_id, limit=1000)
    target = value.strip().lower()
    for rec in (getattr(resp, "items", None) or []):
        if str(_g(rec, field, "")).strip().lower() == target:
            return rec
    return None


def _g(rec, key: str, default=None):
    """Read ``key`` from an EntityRecord (attr) or a dict, else ``default``."""
    if rec is None:
        return default
    if isinstance(rec, dict):
        return rec.get(key, default)
    return getattr(rec, key, default)


def _clean(value, default="") -> str:
    """Trim a Data Fabric string field (some carry trailing spaces)."""
    if value is None:
        return default
    return str(value).strip()


def _num(value):
    """Coerce a Data Fabric numeric-ish field to float, else None."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


# --- MCP plumbing -----------------------------------------------------------


def _resolve_mcp_url(sdk: UiPath) -> str:
    """The hosted Weather MCP URL: env override, else SDK lookup in the folder."""
    url = os.environ.get("WEATHER_MCP_URL")
    if url:
        return url
    server = sdk.mcp.retrieve(slug=MCP_SLUG, folder_path=FOLDER)
    return getattr(server, "mcp_url", None) or getattr(server, "url", "")


def _bearer(sdk: UiPath) -> str:
    """Bearer for the MCP: explicit PAT, else the live (auto-refreshed) SDK token."""
    return os.environ.get("UIPATH_PAT") or getattr(sdk._config, "secret", "") or ""


def _parse_jsonrpc(resp) -> Optional[dict]:
    """Parse a streamable-HTTP POST response (JSON or SSE) to its JSON-RPC message."""
    import json as _json

    ctype = resp.headers.get("content-type", "")
    text = resp.text
    if "text/event-stream" in ctype:
        last = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    last = _json.loads(line[5:].strip())
                except Exception:
                    pass
        return last
    try:
        return _json.loads(text)
    except Exception:
        return None


class _PostOnlyMCP:
    """A minimal POST-only streamable-HTTP MCP session.

    The UiPath AgentHub MCP endpoint is POST-only — it 405s the optional
    server->client GET notification stream that ``MultiServerMCPClient`` always
    opens. This client speaks the same JSON-RPC protocol over POST/DELETE only,
    so there is NO GET stream and therefore NO 405s, while still using a single
    session for every tool call.
    """

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.client = None
        self.headers = {}
        self._rid = 0

    def _next_id(self) -> int:
        self._rid += 1
        return self._rid

    async def __aenter__(self):
        import httpx

        self.client = httpx.AsyncClient(timeout=60)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        init = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "foreman-weather", "version": "1.0.0"},
            },
        }
        resp = await self.client.post(self.url, headers=self.headers, json=init)
        resp.raise_for_status()
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self.headers["Mcp-Session-Id"] = sid
        msg = _parse_jsonrpc(resp) or {}
        version = (msg.get("result") or {}).get("protocolVersion")
        if version:  # required on follow-up requests by recent MCP revisions
            self.headers["MCP-Protocol-Version"] = version
        await self.client.post(
            self.url,
            headers=self.headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        return self

    async def call(self, name: str, arguments: dict) -> str:
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = await self.client.post(self.url, headers=self.headers, json=req)
        resp.raise_for_status()
        msg = _parse_jsonrpc(resp) or {}
        if msg.get("error"):
            raise RuntimeError(f"MCP tool {name} error: {msg['error']}")
        content = (msg.get("result") or {}).get("content") or []
        return _tool_text(content)

    async def __aexit__(self, *exc):
        try:
            await self.client.delete(self.url, headers=self.headers)
        except Exception:
            pass
        await self.client.aclose()


async def _gather_with_session(session, site_id: str, lat, lon) -> dict:
    """Run search_location (if needed) + forecast + lightning over one session."""
    if lat is None or lon is None:
        prefix = site_id.split("-")[0].upper()
        city = CITY_BY_PREFIX.get(prefix, prefix)
        loc_text = await session.call("search_location", {"query": city, "limit": 1})
        m = re.search(r"Latitude:\s*([\-\d.]+),\s*Longitude:\s*([\-\d.]+)", loc_text)
        if m:
            lat, lon = float(m.group(1)), float(m.group(2))
    if lat is None or lon is None:
        return {"lat": None, "lon": None, "forecast": None, "lightning": None}

    forecast = await session.call(
        "get_forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "days": 2,
            "granularity": "hourly",
            "include_precipitation_probability": True,
        },
    )
    lightning = None
    try:
        lightning = await session.call(
            "get_lightning_activity",
            {"latitude": lat, "longitude": lon, "radius": 50, "timeWindow": 60},
        )
    except Exception:
        lightning = None  # lightning is best-effort; window still computes
    return {"lat": lat, "lon": lon, "forecast": forecast, "lightning": lightning}


async def _gather_via_adapter(url: str, token: str, site_id: str, lat, lon) -> dict:
    """Fallback path using the official MultiServerMCPClient (incurs the GET 405)."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    last_err: Optional[Exception] = None
    for transport in ("streamable_http", "sse"):
        try:
            client = MultiServerMCPClient(
                {
                    "weather": {
                        "url": url,
                        "transport": transport,
                        "headers": {"Authorization": f"Bearer {token}"},
                    }
                }
            )
            async with client.session("weather") as raw:
                tools = {t.name: t for t in await load_mcp_tools(raw)}

                class _Shim:
                    async def call(self, name, arguments):
                        if name not in tools:
                            raise RuntimeError(f"tool {name} unavailable")
                        return _tool_text(await tools[name].ainvoke(arguments))

                return await _gather_with_session(_Shim(), site_id, lat, lon)
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"hosted MCP unreachable: {last_err}")


async def _mcp_gather(url: str, token: str, site_id: str, lat, lon) -> dict:
    """All hosted-MCP work in ONE session: POST-only first (no 405s), else adapter."""
    try:
        async with _PostOnlyMCP(url, token) as session:
            return await _gather_with_session(session, site_id, lat, lon)
    except Exception as exc:
        # Any protocol hiccup in the lean client -> fall back to the official one.
        import sys

        print(f"[post-only MCP fell back] {type(exc).__name__}: {exc}", file=sys.stderr)
        return await _gather_via_adapter(url, token, site_id, lat, lon)


def _tool_text(result) -> str:
    """Flatten an MCP tool result (list of text parts / str / obj) to one string."""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts = []
        for p in result:
            if isinstance(p, dict):
                parts.append(str(p.get("text", "")))
            else:
                parts.append(str(getattr(p, "text", p)))
        return "\n".join(parts)
    return str(result)


# --- Forecast parsing -------------------------------------------------------


class Slot(BaseModel):
    when_local: datetime          # naive local civil time (site timezone)
    when_utc: datetime            # tz-aware UTC instant
    precip_pct: int = 0
    wind_mph: int = 0
    gust_mph: int = 0
    conditions: str = ""
    daylight: bool = True


_TZ_RE = re.compile(r"\*\*Timezone:\*\*\s*([A-Za-z]+/[A-Za-z_]+)")
_PRECIP_RE = re.compile(r"Precipitation Chance:\*\*\s*(\d+)\s*%", re.IGNORECASE)
_WIND_RE = re.compile(r"\*\*Wind:\*\*\s*(\d+)\s*mph", re.IGNORECASE)
_GUST_RE = re.compile(r"Wind Gusts:\*\*\s*(\d+)\s*mph", re.IGNORECASE)
_COND_RE = re.compile(r"\*\*Conditions:\*\*\s*(.+)")
_LIGHT_RE = re.compile(r"Safety Status:\s*([A-Za-z]+)", re.IGNORECASE)
_STRIKES_RE = re.compile(r"Total Strikes:\*\*\s*(\d+)", re.IGNORECASE)
_NEAREST_RE = re.compile(r"[Nn]earest[^0-9]*([\d.]+)\s*km")


def _site_tz(tz_name: str):
    """Return a tzinfo for the site (zoneinfo if available), else None."""
    if not tz_name:
        return None
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(tz_name)
    except Exception:
        return None


def _to_utc(naive_local: datetime, tz, lon: float) -> datetime:
    """Convert a naive local civil time to a tz-aware UTC instant."""
    if tz is not None:
        return naive_local.replace(tzinfo=tz).astimezone(timezone.utc)
    # No tz database: approximate the offset from longitude (15 deg per hour).
    return (naive_local - timedelta(hours=lon / 15.0)).replace(tzinfo=timezone.utc)


def _solar_elevation_deg(lat: float, lon: float, when_utc: datetime) -> float:
    """NOAA solar elevation (degrees) for (lat, lon) at a UTC instant."""
    doy = when_utc.timetuple().tm_yday
    hour = when_utc.hour + when_utc.minute / 60.0 + when_utc.second / 3600.0
    g = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)
    decl = (
        0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
        - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
        - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g)
    )
    eqtime = 229.18 * (
        0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
        - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g)
    )
    time_offset = eqtime + 4.0 * lon            # minutes
    tst = hour * 60.0 + time_offset             # true solar time, minutes
    ha = math.radians(tst / 4.0 - 180.0)        # hour angle
    lat_r = math.radians(lat)
    cos_zen = (
        math.sin(lat_r) * math.sin(decl)
        + math.cos(lat_r) * math.cos(decl) * math.cos(ha)
    )
    cos_zen = max(-1.0, min(1.0, cos_zen))
    return 90.0 - math.degrees(math.acos(cos_zen))


def _parse_hourly(text: str, lat: float, lon: float) -> Tuple[List[Slot], str]:
    """Parse the hourly forecast markdown into Slots (with daylight computed)."""
    tz_match = _TZ_RE.search(text)
    tz_name = tz_match.group(1) if tz_match else ""
    tz = _site_tz(tz_name)
    slots: List[Slot] = []
    for block in text.split("\n## ")[1:]:
        header = block.splitlines()[0].strip()
        when_local = _parse_local_dt(header)
        if when_local is None:
            continue
        when_utc = _to_utc(when_local, tz, lon)
        precip = _PRECIP_RE.search(block)
        wind = _WIND_RE.search(block)
        gust = _GUST_RE.search(block)
        cond = _COND_RE.search(block)
        elev = _solar_elevation_deg(lat, lon, when_utc)
        slots.append(
            Slot(
                when_local=when_local,
                when_utc=when_utc,
                precip_pct=int(precip.group(1)) if precip else 0,
                wind_mph=int(wind.group(1)) if wind else 0,
                gust_mph=int(gust.group(1)) if gust else 0,
                conditions=cond.group(1).strip() if cond else "",
                daylight=elev > DAYLIGHT_ELEV_MIN,
            )
        )
    return slots, tz_name


def _parse_local_dt(header: str) -> Optional[datetime]:
    """Parse a forecast hour header like '6/24/2026, 5:30 AM' (a few variants)."""
    header = header.strip().rstrip("#").strip()
    for fmt in ("%m/%d/%Y, %I:%M %p", "%m/%d/%Y, %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(header, fmt)
        except ValueError:
            continue
    return None


def _parse_lightning(text: str) -> Tuple[bool, str]:
    """Return (active, note). active == lightning present (not 'SAFE')."""
    status = _LIGHT_RE.search(text)
    level = status.group(1).upper() if status else "UNKNOWN"
    strikes = _STRIKES_RE.search(text)
    nearest = _NEAREST_RE.search(text)
    active = level not in ("SAFE", "UNKNOWN")
    note = f"lightning status {level}"
    if strikes:
        note += f", {strikes.group(1)} strikes/60min"
    if nearest:
        note += f", nearest ~{nearest.group(1)}km"
    return active, note


# --- Window computation -----------------------------------------------------


def _slot_label(slot_local: datetime, ref_date) -> str:
    """'Today' / 'Tomorrow' / weekday relative to the reference (now) date."""
    delta = (slot_local.date() - ref_date).days
    if delta <= 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return slot_local.strftime("%a %b %d")


def _tz_abbr(slots: List[Slot], tz_name: str) -> str:
    """A short tz label (e.g. 'IST') for the window string, else the IANA name."""
    tz = _site_tz(tz_name)
    if tz is not None and slots:
        try:
            return slots[0].when_local.replace(tzinfo=tz).tzname() or tz_name
        except Exception:
            pass
    return tz_name or "local"


def _is_safe(slot: Slot, lightning_active: bool, now_utc: datetime) -> bool:
    """A slot is workable: dry, in daylight, not high-wind, and lightning-clear."""
    if slot.precip_pct >= PRECIP_DRY_MAX:
        return False
    if not slot.daylight:
        return False
    if slot.wind_mph >= WIND_HIGH_MPH or slot.gust_mph >= GUST_HIGH_MPH:
        return False
    if lightning_active and slot.when_utc <= now_utc + timedelta(minutes=LIGHTNING_HOLD_MIN):
        return False
    return True


def _compute_window(
    slots: List[Slot], lightning_active: bool, tz_name: str, now_utc: datetime
) -> Tuple[str, str, List[Slot]]:
    """Return (safe_window text, earliest_safe_time text, the safe run of slots)."""
    horizon_end = now_utc + timedelta(hours=HORIZON_HOURS)
    future = [s for s in slots if s.when_utc >= now_utc - timedelta(minutes=30)
              and s.when_utc <= horizon_end]
    if not future:
        return ("No forecast hours available in the next 48h.", "", [])

    ref_date = future[0].when_local.date()
    abbr = _tz_abbr(slots, tz_name)

    first_idx = next(
        (i for i, s in enumerate(future) if _is_safe(s, lightning_active, now_utc)),
        None,
    )
    if first_idx is None:
        return (
            f"No fully safe (dry, daylit, lightning-free) window in the next "
            f"{HORIZON_HOURS}h.",
            "",
            [],
        )

    run = [future[first_idx]]
    for s in future[first_idx + 1:]:
        if _is_safe(s, lightning_active, now_utc):
            run.append(s)
        else:
            break

    start = run[0].when_local
    end = run[-1].when_local + timedelta(hours=1)   # slot covers its hour
    label = _slot_label(start, ref_date)
    earliest = f"{start:%Y-%m-%d %H:%M} {abbr}"
    window = (
        f"{label} {start:%H:%M}-{end:%H:%M} {abbr}, dry & lightning-free "
        f"({len(run)}h clear)"
    )
    return window, earliest, run


def _access_constraints(environment: str, humidity, fix_kind: str) -> List[str]:
    """Readable access constraints from Site.environment (+ humidity / fix notes)."""
    out: List[str] = []
    env = _clean(environment)
    if env:
        phrase = env.replace("_", " ").replace("-", " ").strip()
        readable = phrase + (" environment" if "environment" not in phrase else "")
        out.append(readable)
        low = phrase.lower()
        if "outdoor" in low or "ground" in low:
            out.append("exposed outdoor / ground-mount site — weather-gated access")
    hum = _num(humidity)
    if hum is not None and hum >= 70:
        out.append(f"high humidity ({hum:.0f}%) — condensation / insulation risk")
    fk = (fix_kind or "").lower()
    if "live" in fk or "electric" in fk:
        out.append("live-electrical work — requires dry conditions and LOTO before start")
    return out or ["no special access constraints on record"]


# --- Open-Meteo fallback ----------------------------------------------------


async def _fallback_open_meteo(
    lat: float, lon: float, now_utc: datetime
) -> Tuple[str, List[str], str]:
    """Structured-JSON fallback (no key): dry+daylight window, lightning omitted."""
    import httpx

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation_probability,wind_speed_10m,wind_gusts_10m"
        "&daily=sunrise,sunset&forecast_days=2&timezone=auto&wind_speed_unit=mph"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        data = (await client.get(url)).json()

    tz_abbr = data.get("timezone_abbreviation") or "local"
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    precip = hourly.get("precipitation_probability") or []
    winds = hourly.get("wind_speed_10m") or []
    gusts = hourly.get("wind_gusts_10m") or []
    daily = data.get("daily") or {}
    sunrises = [datetime.fromisoformat(s) for s in (daily.get("sunrise") or [])]
    sunsets = [datetime.fromisoformat(s) for s in (daily.get("sunset") or [])]
    off = timedelta(seconds=data.get("utc_offset_seconds") or 0)

    def is_day(local_dt: datetime) -> bool:
        for sr, ss in zip(sunrises, sunsets):
            if sr.date() == local_dt.date():
                return sr <= local_dt <= ss
        return True

    slots: List[Slot] = []
    for i, t in enumerate(times):
        local = datetime.fromisoformat(t)
        slots.append(
            Slot(
                when_local=local,
                when_utc=(local - off).replace(tzinfo=timezone.utc),
                precip_pct=int(precip[i]) if i < len(precip) and precip[i] is not None else 0,
                wind_mph=int(winds[i]) if i < len(winds) and winds[i] is not None else 0,
                gust_mph=int(gusts[i]) if i < len(gusts) and gusts[i] is not None else 0,
                daylight=is_day(local),
            )
        )
    window, earliest, _ = _compute_window(slots, False, tz_abbr, now_utc)
    blockers = _current_blockers(slots, False, now_utc)
    return window, earliest, blockers


def _current_blockers(
    slots: List[Slot], lightning_active: bool, now_utc: datetime
) -> List[str]:
    """Blockers active right now (current hour) + global lightning."""
    blockers: List[str] = []
    if lightning_active:
        blockers.append("lightning")
    current = next(
        (s for s in slots if s.when_utc >= now_utc - timedelta(minutes=30)), None
    )
    if current is not None:
        if current.precip_pct >= PRECIP_DRY_MAX:
            blockers.append("rain")
        if not current.daylight:
            blockers.append("after-dark")
        if current.wind_mph >= WIND_HIGH_MPH or current.gust_mph >= GUST_HIGH_MPH:
            blockers.append("high-wind")
    # de-dupe, preserve order
    seen = set()
    return [b for b in blockers if not (b in seen or seen.add(b))]


# --- Window phrasing (LLM, with deterministic fallback) ---------------------

_PHRASE_SYSTEM = (
    "You are FOREMAN's weather window planner. Rewrite the COMPUTED safe-work "
    "window as ONE short, calm sentence a field crew can act on. Keep the day, the "
    "exact start-end times, the timezone, and that it is dry & lightning-free. Do "
    "NOT invent times, do not add caveats, return only the sentence."
)


async def _phrase_window(deterministic: str, fix_kind: str, blockers: List[str]) -> str:
    """Use the LLM to polish the window sentence; fall back to the computed text."""
    try:
        llm = UiPathChat(model=LLM_MODEL, temperature=0)
        out = await llm.ainvoke(
            [
                {"role": "system", "content": _PHRASE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Fix kind: {fix_kind or 'general outdoor work'}\n"
                        f"Active blockers right now: {blockers or 'none'}\n"
                        f"Computed window: {deterministic}\n"
                        "Rewrite as one sentence."
                    ),
                },
            ]
        )
        text = (getattr(out, "content", "") or "").strip().strip('"')
        return text or deterministic
    except Exception:
        return deterministic


# --- Node -------------------------------------------------------------------


async def plan_weather(state: GraphInput) -> GraphOutput:
    site_id = (state.site_id or "").strip()
    fix_kind = (state.fix_kind or "").strip()
    now_utc = datetime.now(timezone.utc)

    if not site_id:
        return GraphOutput(error="site_id is required")

    environment = ""
    humidity = None
    try:
        sdk = UiPath()
        ids = _entity_ids(sdk)

        # 1) Resolve the site: coords + environment from Data Fabric.
        site = _df_one(sdk, ids["Site"], "siteid", site_id) if "Site" in ids else None
        if site is None:
            return GraphOutput(error=f"Site '{site_id}' not found in Data Fabric")
        lat = _num(_g(site, "lat"))
        lon = _num(_g(site, "lon"))
        environment = _clean(_g(site, "environment"))
        humidity = _g(site, "humidity")
        access = _access_constraints(environment, humidity, fix_kind)

        # 2) One MCP session: forecast + lightning (+ coords if Site had none).
        #    On connection failure, run the Open-Meteo fallback.
        try:
            url = _resolve_mcp_url(sdk)
            data = await _mcp_gather(url, _bearer(sdk), site_id, lat, lon)
        except Exception as exc:
            if lat is None or lon is None:
                return GraphOutput(
                    access_constraints=access,
                    error=f"hosted MCP unreachable and no coordinates to fall back on: {exc}",
                )
            window, earliest, blockers = await _fallback_open_meteo(lat, lon, now_utc)
            safe_window = await _phrase_window(window, fix_kind, blockers)
            return GraphOutput(
                safe_window=safe_window,
                weather_blockers=blockers,
                access_constraints=access,
                earliest_safe_time=earliest,
                error=f"fallback: hosted MCP unreachable, used Open-Meteo (lightning omitted): {exc}",
            )

        # 3) Coordinates must be resolved by now (Site value or search_location).
        lat, lon = data["lat"], data["lon"]
        if lat is None or lon is None or not data.get("forecast"):
            return GraphOutput(
                access_constraints=access,
                error=f"could not resolve coordinates for site '{site_id}'",
            )

        # 4) Parse the forecast + lightning markdown returned by the session.
        slots, tz_name = _parse_hourly(data["forecast"], lat, lon)
        lightning_active = False
        if data.get("lightning"):
            lightning_active, _ = _parse_lightning(data["lightning"])

        if not slots:
            return GraphOutput(
                access_constraints=access,
                error="hosted MCP returned a forecast that could not be parsed",
            )

        # 5) Compute the earliest dry + daylit + lightning-free window.
        window, earliest, _run = _compute_window(slots, lightning_active, tz_name, now_utc)
        blockers = _current_blockers(slots, lightning_active, now_utc)
        safe_window = await _phrase_window(window, fix_kind, blockers)

        return GraphOutput(
            safe_window=safe_window,
            weather_blockers=blockers,
            access_constraints=access,
            earliest_safe_time=earliest,
            error="",
        )
    except Exception as exc:  # never throw out of the node
        return GraphOutput(
            access_constraints=_access_constraints(environment, humidity, fix_kind),
            error=f"{type(exc).__name__}: {exc}",
        )


# --- Graph ------------------------------------------------------------------

builder = StateGraph(GraphInput, output=GraphOutput)
builder.add_node("plan_weather", plan_weather)
builder.add_edge(START, "plan_weather")
builder.add_edge("plan_weather", END)

# The runtime factory looks for a compiled graph named exactly ``graph``.
graph = builder.compile()
