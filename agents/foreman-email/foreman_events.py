"""Bridge from the coded agent to the FOREMAN view-backend (which fans events
out to the live UI over WebSocket). Each call is one normalized CaseEvent - the
exact shape src/types.ts consumes, so the dashboard renders it identically.

Backend URL + secret resolve in priority order (asset-only in cloud):
  1. configure(backend_url, secret)                              (optional override)
  2. env  FOREMAN_BACKEND_URL / FOREMAN_INGEST_SECRET            (local .env)
  3. UiPath Assets  FOREMAN_BACKEND_URL (Text) / FOREMAN_INGEST_SECRET (Credential)
     - tried in the agent's execution folder, then the `Shared` folder
  4. http://localhost:8000 / dev-secret                          (local default)

Never raises - telemetry must never break the call.
"""
import os
import time

import httpx  # bundled with the uipath SDK (also used by this agent's poller)

_explicit_backend: str | None = None
_explicit_secret: str | None = None
_resolved: tuple[str, str] | None = None

# Try the agent's default execution-folder context first, then the Shared folder.
_ASSET_FOLDERS = (None, "Shared")


def configure(backend_url: str | None = None, secret: str | None = None) -> None:
    global _explicit_backend, _explicit_secret, _resolved
    if backend_url:
        _explicit_backend = backend_url.rstrip("/")
    if secret:
        _explicit_secret = secret
    _resolved = None  # force re-resolve on next emit


def _asset_text(name: str) -> str | None:
    """Read a Text asset's value (FOREMAN_BACKEND_URL), trying both folders."""
    try:
        from uipath.platform import UiPath  # lazy: local runs need no UiPath
        sdk = UiPath()
    except Exception:  # noqa: BLE001 - no UiPath context locally
        return None
    for fp in _ASSET_FOLDERS:
        try:
            a = sdk.assets.retrieve(name) if fp is None else sdk.assets.retrieve(name, folder_path=fp)
            v = getattr(a, "value", None) or getattr(a, "string_value", None)
            if v:
                return v
        except Exception:  # noqa: BLE001 - try the next folder
            continue
    return None


def _asset_credential(name: str) -> str | None:
    """Read a Credential asset's password (FOREMAN_INGEST_SECRET), trying both folders."""
    try:
        from uipath.platform import UiPath  # lazy
        sdk = UiPath()
    except Exception:  # noqa: BLE001
        return None
    for fp in _ASSET_FOLDERS:
        try:
            v = (sdk.assets.retrieve_credential(name) if fp is None
                 else sdk.assets.retrieve_credential(name, folder_path=fp))
            if v:
                return v
        except Exception:  # noqa: BLE001
            continue
    return None


def _resolve() -> tuple[str, str]:
    global _resolved
    if _resolved is not None:
        return _resolved
    backend = (_explicit_backend or os.environ.get("FOREMAN_BACKEND_URL")
               or _asset_text("FOREMAN_BACKEND_URL"))
    secret = (_explicit_secret or os.environ.get("FOREMAN_INGEST_SECRET")
              or _asset_credential("FOREMAN_INGEST_SECRET"))
    _resolved = ((backend or "http://localhost:8000").rstrip("/"), secret or "dev-secret")
    return _resolved


def emit(case_id: str, event: dict) -> None:
    backend, secret = _resolve()
    try:
        httpx.post(
            f"{backend}/ingest/{case_id}",
            json=event,
            headers={"x-foreman-secret": secret},
            timeout=5.0,
        )
    except Exception as e:  # noqa: BLE001 - never let telemetry break the call
        print(f"[foreman_events] emit failed: {e}")


def log(case_id: str, stage: str, source: str, text: str, tone: str = "agent") -> None:
    emit(case_id, {
        "kind": "log",
        "entry": {
            "ts": time.strftime("%H:%M:%S"),
            "stage": stage,
            "source": source,
            "text": text,
            "tone": tone,
        },
    })
