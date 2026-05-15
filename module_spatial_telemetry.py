"""Deterministic telemetry logging for spatial measurements."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from collections import Counter
from typing import Any, Dict, Optional

from module_tools import safe_join, sanitize_id
from module_storage import ROOT as STORAGE_ROOT, _now_ts
from telemetry.collector import append_event as append_telemetry_event

_TELEMETRY_SUBDIR = os.path.join("LongTermStore", "Telemetry", "SpatialMeasurements")
_LOG_FILENAME = "events.jsonl"
_SEQ_FILENAME = "sequence.idx"
_LOCK_FILENAME = ".writer.lock"
_LATENCY_BUCKETS = [0, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000]

__all__ = ["record_spatial_event", "get_log_path", "summarize_spatial_telemetry_events"]


def summarize_spatial_telemetry_events(events: Any) -> Dict[str, Any]:
    """Summarize deterministic telemetry evidence for adequacy review."""

    if not isinstance(events, list):
        return {
            "total_events": 0,
            "status_counts": {},
            "completed_event_count": 0,
            "skipped_event_count": 0,
            "failed_event_count": 0,
            "telemetry_completed_present": False,
        }

    status_counts: Counter[str] = Counter()
    total_events = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        total_events += 1
        status = event.get("status") if isinstance(event.get("status"), str) else None
        if status:
            status_counts[status] += 1

    completed_count = int(status_counts.get("completed") or 0)
    skipped_count = int(status_counts.get("skipped") or 0)
    failed_count = int(status_counts.get("failed") or 0)
    return {
        "total_events": total_events,
        "status_counts": dict(status_counts),
        "completed_event_count": completed_count,
        "skipped_event_count": skipped_count,
        "failed_event_count": failed_count,
        "telemetry_completed_present": bool(completed_count),
    }


def _ensure_directory() -> str:
    """Return the absolute path to the telemetry directory, creating it if needed."""

    directory = safe_join(STORAGE_ROOT, _TELEMETRY_SUBDIR)
    os.makedirs(directory, exist_ok=True)
    return directory


def _resolve_paths() -> tuple[Path, Path, Path]:
    directory_str = _ensure_directory()
    directory = Path(directory_str)
    log_path = directory / _LOG_FILENAME
    sequence_path = directory / _SEQ_FILENAME
    lock_path = directory / _LOCK_FILENAME
    return log_path, sequence_path, lock_path


def get_log_path() -> str:
    """Return the absolute path to the spatial telemetry JSONL log file."""

    log_path, _, _ = _resolve_paths()
    return str(log_path)


def _coerce_float(value: Optional[Any]) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _coerce_bool(value: Optional[Any]) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _latency_band(latency_ms: Optional[float]) -> Optional[str]:
    if latency_ms is None or latency_ms < 0:
        return None
    for lower, upper in zip(_LATENCY_BUCKETS, _LATENCY_BUCKETS[1:]):
        if latency_ms < upper:
            return f"{lower}-{upper}"
    return f">={_LATENCY_BUCKETS[-1]}"


def _normalize_reason(reason: Optional[str]) -> Dict[str, Optional[str]]:
    if not isinstance(reason, str) or not reason.strip():
        return {"reason": None, "reason_detail": None}
    trimmed = reason.strip()
    code: Optional[str]
    if trimmed:
        try:
            code = sanitize_id(trimmed)
        except Exception:
            code = hashlib.sha256(trimmed.encode("utf-8")).hexdigest()[:24]
    else:
        code = None
    return {"reason": code or None, "reason_detail": trimmed}


def _clean_dict(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None
    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[str(key)] = value
        else:
            try:
                cleaned[str(key)] = value
            except Exception:
                continue
    return cleaned or None


def record_spatial_event(
    *,
    record_id: Optional[str],
    cycle_id: Optional[str],
    record_path: Optional[str],
    event_type: str,
    status: str,
    reason: Optional[str] = None,
    latency_ms: Optional[Any] = None,
    cache_hit: Optional[Any] = None,
    measurement_hash: Optional[str] = None,
    snapshot_hash: Optional[str] = None,
    snapshot_relative_path: Optional[str] = None,
    determinism: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append a deterministic event describing a spatial measurement outcome."""

    log_path, sequence_path, lock_path = _resolve_paths()
    timestamp_fixed = _now_ts()
    latency_value = _coerce_float(latency_ms)
    cache_value = _coerce_bool(cache_hit)
    latency_bucket = _latency_band(latency_value)
    reason_payload = _normalize_reason(reason)
    determinism_payload = _clean_dict(determinism)
    extra_payload = _clean_dict(extra)

    event: Dict[str, Any] = {
        "schema_version": "1.0",
        "timestamp_fixed": timestamp_fixed,
        "event_type": str(event_type),
        "status": str(status),
        "record_id": str(record_id) if isinstance(record_id, str) and record_id else None,
        "cycle_id": str(cycle_id) if isinstance(cycle_id, str) and cycle_id else None,
        "record_path": str(record_path) if isinstance(record_path, str) and record_path else None,
        "latency_ms": latency_value,
        "latency_band": latency_bucket,
        "cache_hit": cache_value,
        "measurement_hash": str(measurement_hash) if measurement_hash else None,
        "snapshot_hash": str(snapshot_hash) if snapshot_hash else None,
        "snapshot_relative_path": str(snapshot_relative_path) if snapshot_relative_path else None,
    }

    if reason_payload["reason"]:
        event["reason"] = reason_payload["reason"]
    if reason_payload["reason_detail"]:
        event["reason_detail"] = reason_payload["reason_detail"]
    if determinism_payload:
        event["determinism"] = determinism_payload
    if extra_payload:
        event["extra"] = extra_payload

    persisted = append_telemetry_event(
        event,
        ensure_dir=True,
        timestamp_fallback=timestamp_fixed,
        store_path=log_path,
        sequence_path=sequence_path,
        lock_path=lock_path,
    )

    return {
        "status": "ok",
        "path": str(log_path),
        "sequence_index": persisted.get("sequence_index"),
        "event_id": persisted.get("event_id"),
    }
