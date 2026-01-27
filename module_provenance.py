"""module_provenance.py

Deterministic event log and provenance utilities.

Public API:
- create_event
- append_event
- compute_hash
- get_version
- trace_provenance
"""

from __future__ import annotations

import datetime
import hashlib
import json
import time
from typing import Any, Dict, List, Optional


def _fixed_timestamp_seconds() -> float:
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode") and det.get("fixed_timestamp"):
            ts = str(det.get("fixed_timestamp"))
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return float(dt.timestamp())
    except Exception:
        pass
    return 0.0


def now_ts() -> float:
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode"):
            return _fixed_timestamp_seconds()
    except Exception:
        pass
    return float(time.time())


def compute_hash(event: Dict[str, Any]) -> str:
    """Deterministic hash of an event dict."""
    s = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def create_event(event_type: str, payload: Dict[str, Any], prev_hash: Optional[str] = None, timestamp: Optional[float] = None) -> Dict[str, Any]:
    """Create an event with deterministic id.

    The event_id is a hash of {event_type, payload, timestamp, prev_hash}.
    """
    ts = float(now_ts() if timestamp is None else timestamp)
    event: Dict[str, Any] = {
        "event_type": str(event_type),
        "payload": dict(payload) if isinstance(payload, dict) else {},
        "timestamp": ts,
        "prev_hash": prev_hash,
    }
    event_id = compute_hash(event)
    event["event_id"] = event_id
    return event


def append_event(log: List[Dict[str, Any]], event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Immutable append."""
    return list(log or []) + [event]


def get_version(record_id: str, log: List[Dict[str, Any]]) -> int:
    rid = str(record_id)
    n = 0
    for e in log or []:
        if not isinstance(e, dict):
            continue
        payload = e.get("payload")
        if not isinstance(payload, dict):
            continue
        targets = payload.get("target_ids")
        if isinstance(targets, list) and rid in targets:
            n += 1
    return int(n)


def trace_provenance(record_id: str, log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return events affecting record_id, in log order."""
    rid = str(record_id)
    out: List[Dict[str, Any]] = []
    for e in log or []:
        if not isinstance(e, dict):
            continue
        payload = e.get("payload")
        if not isinstance(payload, dict):
            continue
        targets = payload.get("target_ids")
        if isinstance(targets, list) and rid in targets:
            out.append(e)
    return out
