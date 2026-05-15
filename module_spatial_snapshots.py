"""Deterministic persistence helpers for spatial measurement snapshots."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, Optional

from module_tools import canonical_json_bytes, safe_join, sanitize_id
from module_storage import ROOT as STORAGE_ROOT

_SPATIAL_SUBDIR = os.path.join("LongTermStore", "SpatialSnapshots")


def summarize_spatial_snapshot_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return the bounded snapshot evidence needed for measurement adequacy review."""

    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    spatial_measurement = (
        relational_state.get("spatial_measurement")
        if isinstance(relational_state.get("spatial_measurement"), dict)
        else {}
    )
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    bridge_outputs = relational_state.get("bridge_outputs") if isinstance(relational_state.get("bridge_outputs"), list) else []

    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    spatial_artifacts = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
    latest_snapshot = spatial_artifacts.get("latest") if isinstance(spatial_artifacts.get("latest"), dict) else {}

    measurement_hash = spatial_artifacts.get("measurement_hash") if isinstance(spatial_artifacts.get("measurement_hash"), str) else None
    if not measurement_hash and spatial_measurement:
        try:
            measurement_hash = hashlib.sha256(canonical_json_bytes(spatial_measurement)).hexdigest()
        except Exception:
            measurement_hash = None

    graph_metrics = derived.get("graph_metrics_composed") if isinstance(derived.get("graph_metrics_composed"), dict) else None
    snapshot_relative_path = latest_snapshot.get("relative_path") if isinstance(latest_snapshot.get("relative_path"), str) else None
    snapshot_hash = latest_snapshot.get("hash") if isinstance(latest_snapshot.get("hash"), str) else None

    return {
        "record_id": record.get("id") if isinstance(record.get("id"), str) else None,
        "cycle_id": record.get("cycle_id") if isinstance(record.get("cycle_id"), str) else None,
        "measurement_recorded": bool(spatial_measurement),
        "snapshot_present": bool(snapshot_relative_path or snapshot_hash),
        "snapshot_relative_path": snapshot_relative_path,
        "snapshot_hash": snapshot_hash,
        "measurement_hash_present": bool(measurement_hash),
        "measurement_hash": measurement_hash,
        "graph_metrics_present": bool(isinstance(graph_metrics, dict) and graph_metrics.get("available") is True),
        "bridge_present": any(isinstance(item, dict) for item in bridge_outputs),
    }


def _ensure_root() -> str:
    """Resolve and create the spatial snapshot root directory."""
    root = safe_join(STORAGE_ROOT, _SPATIAL_SUBDIR)
    os.makedirs(root, exist_ok=True)
    return root


def _sanitize_component(component: Optional[str], *, fallback: str) -> str:
    candidate = component.strip() if isinstance(component, str) else ""
    if not candidate:
        candidate = fallback
    try:
        return sanitize_id(candidate)
    except Exception:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:24]
        return sanitize_id(digest)


def persist_spatial_snapshot(
    payload: Dict[str, Any],
    *,
    record_id: Optional[str],
    cycle_id: Optional[str],
    snapshot_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a spatial snapshot payload to disk using deterministic serialization."""

    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    root = _ensure_root()
    safe_record = _sanitize_component(record_id, fallback="record")
    record_dir = safe_join(root, safe_record)
    os.makedirs(record_dir, exist_ok=True)

    safe_cycle = _sanitize_component(cycle_id, fallback="cycle")
    cycle_dir = safe_join(record_dir, safe_cycle)
    os.makedirs(cycle_dir, exist_ok=True)

    serialized = canonical_json_bytes(payload)
    snapshot_hash = hashlib.sha256(serialized).hexdigest()
    safe_label = _sanitize_component(snapshot_label, fallback="snapshot")
    label_segment = safe_label[:16] if safe_label else "snap"
    hash_segment = snapshot_hash[:32]
    filename = f"{label_segment}_{hash_segment}.json"
    file_path = safe_join(cycle_dir, filename)

    try:
        with open(file_path, "rb") as existing:
            if existing.read() == serialized:
                rel_path = os.path.relpath(file_path, STORAGE_ROOT).replace("\\", "/")
                return {
                    "status": "ok",
                    "path": file_path,
                    "relative_path": rel_path,
                    "hash": snapshot_hash,
                    "written": False,
                }
    except FileNotFoundError:
        pass

    tmp_path = f"{file_path}.tmp"
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(serialized)
        os.replace(tmp_path, file_path)
    except Exception as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return {
            "status": "error",
            "path": None,
            "relative_path": None,
            "hash": snapshot_hash,
            "written": False,
            "error": str(exc),
        }

    rel_path = os.path.relpath(file_path, STORAGE_ROOT).replace("\\", "/")
    return {
        "status": "ok",
        "path": file_path,
        "relative_path": rel_path,
        "hash": snapshot_hash,
        "written": True,
    }
