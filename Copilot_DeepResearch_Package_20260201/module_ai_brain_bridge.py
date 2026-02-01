# module_ai_brain_bridge.py
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple


def _ai_brain_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_Brain")


def _import_measurement_engine():
    """Import AI_Brain's measurement_engine as a normal Python module.

    AI_Brain is not a Python package at repo root, so we temporarily add the
    AI_Brain directory to sys.path.
    """
    ai_dir = _ai_brain_dir()
    if ai_dir not in sys.path:
        sys.path.insert(0, ai_dir)
    import measurement_engine  # type: ignore
    return measurement_engine


def _extract_spatial_path(rec: Dict[str, Any]) -> Optional[str]:
    # Common field names we might store later.
    for key in ("spatial_asset_path", "point_cloud_path", "mesh_path"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    meta = rec.get("metadata")
    if isinstance(meta, dict):
        for key in ("spatial_asset_path", "point_cloud_path", "mesh_path"):
            val = meta.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def measure_ai_brain(spatial_path: str, *, units: str = "meters") -> Dict[str, Any]:
    """Run AI_Brain 3D measurement engine on a spatial asset path.

    Returns a dict suitable for collector output details.
    """
    if not isinstance(spatial_path, str) or not spatial_path.strip():
        return {"status": "skipped", "reason": "empty spatial_path"}

    spatial_path = spatial_path.strip()
    if not os.path.exists(spatial_path):
        return {"status": "skipped", "reason": "spatial asset not found", "path": spatial_path}

    try:
        engine = _import_measurement_engine()
        points, fmt = engine.load_point_cloud(spatial_path)
        if not points:
            return {"status": "skipped", "reason": "no points loaded", "path": spatial_path, "format": fmt}
        measurement = engine.measure_point_cloud(points, units=units)
        return {
            "status": "completed",
            "path": spatial_path,
            "format": fmt,
            "points": len(points),
            "measurement": measurement,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "path": spatial_path}


def measure_ai_brain_for_record(record_path: str) -> Dict[str, Any]:
    """Load a semantic record and run AI_Brain measurement if it has a spatial path."""
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            rec = json.load(f)
    except Exception as e:
        return {"status": "error", "error": f"failed to load record: {e}", "record_path": record_path}

    spatial_path = _extract_spatial_path(rec)
    if not spatial_path:
        return {"status": "skipped", "reason": "no spatial asset path in record", "record_path": record_path}

    # Allow a record to specify units; default to meters.
    units = "meters"
    try:
        u = rec.get("units") or (rec.get("metadata") or {}).get("units")
        if isinstance(u, str) and u.strip():
            units = u.strip()
    except Exception:
        pass

    out = measure_ai_brain(spatial_path, units=units)
    out["record_path"] = record_path
    return out
