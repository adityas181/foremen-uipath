"""Routing helper for FOREMAN field-dispatch.

One function, ``eta_route``, turns a pair of (lat, lon) points into a drive-time
estimate. It tries real road routing first (OSRM public demo server, no API key)
and falls back to a haversine great-circle approximation on ANY failure, so it
ALWAYS returns a number and NEVER raises.
"""

from math import asin, cos, radians, sin, sqrt
from typing import Tuple

import httpx

# OSRM public demo routing server. NOTE: it expects coordinates as lon,lat.
_OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
_OSRM_TIMEOUT_S = 4.0

# Haversine fallback assumptions.
_DETOUR_FACTOR = 1.3   # road distance vs. straight-line great-circle distance
_AVG_KMH = 35.0        # assumed average road speed
_EARTH_KM = 6371.0


def _haversine_km(origin: Tuple[float, float], dest: Tuple[float, float]) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    lat1, lon1 = radians(origin[0]), radians(origin[1])
    lat2, lon2 = radians(dest[0]), radians(dest[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_KM * asin(sqrt(a))


def _haversine_route(origin: Tuple[float, float], dest: Tuple[float, float]) -> dict:
    """Deterministic offline fallback — always succeeds."""
    road_km = _haversine_km(origin, dest) * _DETOUR_FACTOR
    eta_min = round(road_km / _AVG_KMH * 60)
    return {
        "eta_min": int(eta_min),
        "route": f"~{round(road_km, 1)} km approx (haversine fallback)",
        "source": "haversine",
    }


async def eta_route(origin: Tuple[float, float], dest: Tuple[float, float]) -> dict:
    """Estimate drive time + a human route summary between two (lat, lon) points.

    Returns ``{"eta_min": int, "route": str, "source": "osrm"|"haversine"}``.
    Tries OSRM road routing once (4s timeout); on ANY error/timeout/non-Ok
    response it falls back to a haversine approximation. Never raises.
    """
    o_lat, o_lon = origin
    d_lat, d_lon = dest
    # OSRM coordinate order is lon,lat (longitude first).
    url = f"{_OSRM_URL}/{o_lon},{o_lat};{d_lon},{d_lat}"
    try:
        async with httpx.AsyncClient(timeout=_OSRM_TIMEOUT_S) as client:
            resp = await client.get(url, params={"overview": "false"})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route0 = data["routes"][0]
                distance_m = float(route0["distance"])  # metres
                duration_s = float(route0["duration"])  # seconds
                return {
                    "eta_min": int(round(duration_s / 60)),
                    "route": f"{round(distance_m / 1000, 1)} km by road",
                    "source": "osrm",
                }
    except Exception:
        pass  # any failure -> haversine fallback below
    return _haversine_route(origin, dest)
