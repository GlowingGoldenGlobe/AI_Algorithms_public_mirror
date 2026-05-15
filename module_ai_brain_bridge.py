# module_ai_brain_bridge.py
import hashlib
import json
import os
import sys
import time
import logging
from datetime import datetime, timezone
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from module_composition_contracts import (
    build_composition_fixture_bundle,
    validate_recipe_sidecar,
    validate_scene_manifest,
    validate_validation_summary,
)
from module_tools import canonical_json_bytes

logger = logging.getLogger(__name__)

DETERMINISTIC_TS_ENV = "DETERMINISTIC_TIMESTAMP"

# Thread-safe metrics tracking for 3D operations
_3d_metrics = {
    "3d_calls_total": 0,
    "3d_failures_total": 0,
    "3d_latency_ms_total": 0.0,
    "3d_cache_hits_total": 0,
    "3d_cache_misses_total": 0,
}

CacheKey = Tuple[str, str, Tuple[Tuple[str, Any], ...]]

DEFAULT_MAX_CACHE_ENTRIES = 64
_3d_cache: "OrderedDict[CacheKey, Dict[str, Any]]" = OrderedDict()


def _load_config_from_disk() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    return loaded
    except Exception as exc:
        logger.warning(f"Failed to load config.json: {exc}")
    return {}


def _resolve_3d_timestamp(determinism_config: Optional[Dict[str, Any]]) -> str:
    env_ts = os.environ.get(DETERMINISTIC_TS_ENV)
    if env_ts:
        return env_ts
    try:
        cfg = _load_config_from_disk()
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode") and det.get("fixed_timestamp"):
            return str(det.get("fixed_timestamp"))
    except Exception:
        pass
    if isinstance(determinism_config, dict) and determinism_config.get("3d_fixed_timestamps"):
        return "1970-01-01T00:00:00Z"
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _derive_space_id(spatial_path: str) -> str:
    try:
        base = os.path.basename(spatial_path)
        stem = os.path.splitext(base)[0]
        if stem:
            return stem
    except Exception:
        pass
    return "space_unknown"


def _augment_measurement_with_schema(
    measurement: Dict[str, Any],
    *,
    spatial_path: str,
    units: str,
    points: Optional[int],
    fmt: Optional[str],
    latency_ms: Optional[float],
    determinism_config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not isinstance(measurement, dict):
        return measurement

    measurement.setdefault("version", "1.0")
    measurement.setdefault("space_id", _derive_space_id(spatial_path))
    measurement.setdefault("timestamp", _resolve_3d_timestamp(determinism_config))
    if not isinstance(measurement.get("entities"), list):
        measurement["entities"] = []
    if not isinstance(measurement.get("constraints"), list):
        measurement["constraints"] = []
    measurement.setdefault("source", "3d")

    metrics = measurement.get("metrics") if isinstance(measurement.get("metrics"), dict) else {}
    if not isinstance(metrics, dict):
        metrics = {}
    if "latency_ms" not in metrics:
        metrics["latency_ms"] = int(round(float(latency_ms))) if isinstance(latency_ms, (int, float)) else 0
    if "success" not in metrics:
        metrics["success"] = bool(measurement.get("ok")) if "ok" in measurement else True
    if "seed" not in metrics and isinstance(determinism_config, dict):
        metrics["seed"] = determinism_config.get("3d_seed")
    if "point_count" not in metrics and isinstance(points, (int, float)):
        metrics["point_count"] = int(points)
    if "format" not in metrics and isinstance(fmt, str):
        metrics["format"] = fmt
    measurement["metrics"] = metrics

    metadata = measurement.get("metadata") if isinstance(measurement.get("metadata"), dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.setdefault("spatial_path", spatial_path)
    metadata.setdefault("units", units)
    measurement["metadata"] = metadata

    normalized_bounds = _normalize_bounds(measurement.get("bounds"))
    if normalized_bounds is None:
        normalized_bounds = _derive_bounds_from_measurement(measurement)
    if normalized_bounds is not None:
        measurement["bounds"] = normalized_bounds

    return measurement


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _normalize_bounds(bounds: Any) -> Optional[Dict[str, List[float]]]:
    if not isinstance(bounds, dict):
        return None
    mn = bounds.get("min")
    mx = bounds.get("max")
    if not (
        isinstance(mn, (list, tuple))
        and isinstance(mx, (list, tuple))
        and len(mn) == 3
        and len(mx) == 3
    ):
        return None
    normalized_min: list[float] = []
    normalized_max: list[float] = []
    for idx in range(3):
        min_val = _coerce_float(mn[idx])
        max_val = _coerce_float(mx[idx])
        if min_val is None or max_val is None:
            return None
        lo = min(min_val, max_val)
        hi = max(min_val, max_val)
        normalized_min.append(round(lo, 6))
        normalized_max.append(round(hi, 6))
    return {"min": normalized_min, "max": normalized_max}


def _derive_bounds_from_measurement(measurement: Dict[str, Any]) -> Optional[Dict[str, List[float]]]:
    centroid = measurement.get("centroid")
    dims = measurement.get("aabb_dimensions")
    if not (
        isinstance(centroid, (list, tuple))
        and len(centroid) == 3
        and isinstance(dims, dict)
    ):
        return None
    dim_x = _coerce_float(dims.get("x"))
    dim_y = _coerce_float(dims.get("y"))
    dim_z = _coerce_float(dims.get("z"))
    if dim_x is None or dim_y is None or dim_z is None:
        return None
    c0 = _coerce_float(centroid[0])
    c1 = _coerce_float(centroid[1])
    c2 = _coerce_float(centroid[2])
    if c0 is None or c1 is None or c2 is None:
        return None
    half_x = dim_x / 2.0
    half_y = dim_y / 2.0
    half_z = dim_z / 2.0
    return {
        "min": [round(c0 - half_x, 6), round(c1 - half_y, 6), round(c2 - half_z, 6)],
        "max": [round(c0 + half_x, 6), round(c1 + half_y, 6), round(c2 + half_z, 6)],
    }


def _normalize_determinism_config(determinism_config: Optional[Dict[str, Any]]) -> Tuple[Tuple[str, Any], ...]:
    if not isinstance(determinism_config, dict):
        return tuple()
    normalized: list[Tuple[str, Any]] = []
    for key in sorted(determinism_config.keys()):
        value = determinism_config[key]
        if isinstance(value, (dict, list)):
            try:
                normalized.append((key, json.dumps(value, sort_keys=True)))
            except Exception:
                normalized.append((key, str(value)))
        else:
            normalized.append((key, value))
    return tuple(normalized)


def _make_cache_key(spatial_path: str, units: str, determinism_config: Optional[Dict[str, Any]]) -> CacheKey:
    canonical_path = os.path.abspath(spatial_path)
    norm_units = units.strip().lower() if isinstance(units, str) else "meters"
    return (canonical_path, norm_units, _normalize_determinism_config(determinism_config))


def _evict_expired_entries(ttl_seconds: int, now: float) -> None:
    if ttl_seconds <= 0:
        return
    expired: list[CacheKey] = []
    for key, entry in _3d_cache.items():
        if now - entry.get("timestamp", 0.0) > ttl_seconds:
            expired.append(key)
    for key in expired:
        _3d_cache.pop(key, None)


def _store_cache_entry(key: CacheKey, result: Dict[str, Any], timestamp: float, *, max_entries: int) -> None:
    if max_entries <= 0:
        return
    _3d_cache[key] = {"timestamp": timestamp, "result": deepcopy(result)}
    _3d_cache.move_to_end(key)
    while len(_3d_cache) > max_entries:
        _3d_cache.popitem(last=False)


def get_3d_cache() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}
    now = time.time()
    for key, entry in _3d_cache.items():
        path, units, determinism = key
        snapshot[str(key)] = {
            "path": path,
            "units": units,
            "determinism": dict(determinism),
            "age_seconds": max(0.0, now - entry.get("timestamp", now)),
        }
    return snapshot


def clear_3d_cache() -> None:
    _3d_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    limits_snapshot = get_3d_limits()
    now = time.time()
    entries = []
    for key, entry in _3d_cache.items():
        path, units, determinism = key
        entries.append(
            {
                "path": path,
                "units": units,
                "determinism": dict(determinism),
                "age_seconds": max(0.0, now - entry.get("timestamp", now)),
            }
        )
    return {
        "size": len(_3d_cache),
        "entries": entries,
        "max_entries": limits_snapshot.get("3d_cache_max_entries", DEFAULT_MAX_CACHE_ENTRIES),
    }


def get_3d_limits(config: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    cfg = config if isinstance(config, dict) else _load_config_from_disk()
    limits = cfg.get("3d_limits", {}) if isinstance(cfg, dict) else {}
    max_calls = limits.get("3d_max_calls_per_cycle", 0)
    ttl_seconds = limits.get("3d_cache_ttl_seconds", 0)
    max_entries = limits.get("3d_cache_max_entries", DEFAULT_MAX_CACHE_ENTRIES)
    max_latency = limits.get("3d_max_latency_ms", 0)
    try:
        max_calls = int(max_calls)
    except Exception:
        max_calls = 0
    try:
        ttl_seconds = int(ttl_seconds)
    except Exception:
        ttl_seconds = 0
    try:
        max_entries = int(max_entries)
    except Exception:
        max_entries = DEFAULT_MAX_CACHE_ENTRIES
    try:
        max_latency = int(max_latency)
    except Exception:
        max_latency = 0
    return {
        "3d_max_calls_per_cycle": max(0, max_calls),
        "3d_cache_ttl_seconds": max(0, ttl_seconds),
        "3d_cache_max_entries": max(0, max_entries),
        "3d_max_latency_ms": max(0, max_latency),
    }


def peek_cached_measurement(
    spatial_path: str,
    *,
    units: str = "meters",
    determinism_config: Optional[Dict[str, Any]] = None,
    limits: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    cache_limits = limits if isinstance(limits, dict) else get_3d_limits()
    ttl_seconds = max(0, cache_limits.get("3d_cache_ttl_seconds", 0))
    if ttl_seconds <= 0:
        if _3d_cache:
            clear_3d_cache()
        return None
    now = time.time()
    _evict_expired_entries(ttl_seconds, now)
    key = _make_cache_key(spatial_path, units, determinism_config)
    entry = _3d_cache.get(key)
    if not entry:
        return None
    if now - entry.get("timestamp", 0.0) > ttl_seconds:
        _3d_cache.pop(key, None)
        return None
    _3d_cache.move_to_end(key)
    cached = deepcopy(entry.get("result", {}))
    cached["cache_hit"] = True
    cached["latency_ms"] = 0.0
    return cached

def get_3d_metrics() -> Dict[str, Any]:
    """Retrieve current 3D metrics snapshot."""
    return _3d_metrics.copy()

def increment_3d_metric(name: str, delta: float = 1.0) -> None:
    """Safely increment a 3D metric counter."""
    if name in _3d_metrics:
        _3d_metrics[name] += delta
    else:
        logger.warning(f"Unknown 3D metric: {name}")


class SchemaError(Exception):
    """Raised when a 3D measurement does not conform to the canonical schema."""
    pass


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


def _extract_units(rec: Dict[str, Any]) -> str:
    units = "meters"
    try:
        candidate = rec.get("units") if isinstance(rec, dict) else None
        if not (isinstance(candidate, str) and candidate.strip()):
            metadata = rec.get("metadata") if isinstance(rec, dict) else None
            if isinstance(metadata, dict):
                candidate = metadata.get("units")
        if isinstance(candidate, str) and candidate.strip():
            units = candidate.strip()
    except Exception:
        pass
    return units


def resolve_composition_export_measurement_candidate(
    response: Dict[str, Any],
    scene_manifest: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Resolve one deterministic export artifact path for later geometry measurement handoff.

    The candidate must be supported by both persisted composition response evidence
    and persisted scene-manifest export evidence. Resolution is intentionally narrow:
    choose the first response `export_asset` whose path matches a scene-manifest
    export entry.
    """

    if not isinstance(response, dict):
        raise TypeError(f"response must be a dict, got {type(response).__name__}")
    if not isinstance(scene_manifest, dict):
        raise TypeError(f"scene_manifest must be a dict, got {type(scene_manifest).__name__}")

    manifest_exports = scene_manifest.get("exports") if isinstance(scene_manifest.get("exports"), list) else []
    exports_by_path: Dict[str, Dict[str, Any]] = {}
    for idx, export in enumerate(manifest_exports):
        if not isinstance(export, dict):
            continue
        export_path = export.get("path")
        export_format = export.get("format")
        if not isinstance(export_path, str) or not export_path.strip():
            continue
        if not isinstance(export_format, str) or not export_format.strip():
            continue
        normalized_path = export_path.strip()
        if normalized_path not in exports_by_path:
            exports_by_path[normalized_path] = {
                "path": normalized_path,
                "format": export_format.strip(),
                "scene_manifest_export_index": idx,
            }

    raw_artifacts = response.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raw_artifacts = response.get("emitted_artifacts") if isinstance(response.get("emitted_artifacts"), list) else []

    for idx, artifact in enumerate(raw_artifacts):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("kind") or "").strip() != "export_asset":
            continue
        artifact_path = artifact.get("path")
        if not isinstance(artifact_path, str) or not artifact_path.strip():
            continue
        normalized_path = artifact_path.strip()
        manifest_match = exports_by_path.get(normalized_path)
        if manifest_match is None:
            continue
        candidate = {
            "path": normalized_path,
            "format": manifest_match["format"],
            "artifact_kind": "export_asset",
            "source": "composition_export_artifact",
            "response_artifact_index": idx,
            "scene_manifest_export_index": manifest_match["scene_manifest_export_index"],
        }
        sha_value = artifact.get("sha256")
        if isinstance(sha_value, str) and sha_value.strip():
            candidate["response_artifact_sha256"] = sha_value.strip()
        return candidate

    return None


def get_3d_determinism_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extract 3D-specific determinism settings from config.

    Args:
        config: Configuration dict (if None, loads from config.json).

    Returns:
        Dict with keys: 3d_seed, 3d_fixed_timestamps, 3d_noise_mode.
    """
    cfg = config if isinstance(config, dict) else _load_config_from_disk()
    det_block = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}

    return {
        "3d_seed": det_block.get("3d_seed", 42),
        "3d_fixed_timestamps": det_block.get("3d_fixed_timestamps", True),
        "3d_noise_mode": det_block.get("3d_noise_mode", "none"),
    }


def measure_ai_brain(spatial_path: str, *, units: str = "meters", determinism_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run AI_Brain 3D measurement engine on a spatial asset path.

    Args:
        spatial_path: Path to 3D spatial asset (.ply, .obj, etc.).
        units: Distance units for measurement (default: "meters").
        determinism_config: Optional determinism settings (seed, fixed_timestamps, noise_mode).
                           If not provided, loads from config.json.

    Returns:
        A dict with status, measurement, and determinism audit trail.
    """
    if determinism_config is None:
        determinism_config = get_3d_determinism_config()

    if not isinstance(spatial_path, str) or not spatial_path.strip():
        return {"status": "skipped", "reason": "empty spatial_path", "cache_hit": False}

    spatial_path = spatial_path.strip()
    if not os.path.exists(spatial_path):
        return {"status": "skipped", "reason": "spatial asset not found", "path": spatial_path, "cache_hit": False}

    normalized_units = units.strip() if isinstance(units, str) else "meters"
    limits = get_3d_limits()
    ttl_seconds = limits.get("3d_cache_ttl_seconds", 0)
    max_entries = limits.get("3d_cache_max_entries", DEFAULT_MAX_CACHE_ENTRIES)
    if not isinstance(max_entries, int):
        try:
            max_entries = int(max_entries)
        except Exception:
            max_entries = DEFAULT_MAX_CACHE_ENTRIES
    max_entries = max(0, max_entries)

    cached = peek_cached_measurement(
        spatial_path,
        units=normalized_units,
        determinism_config=determinism_config,
        limits=limits,
    )
    if cached is not None:
        increment_3d_metric("3d_cache_hits_total")
        cached.setdefault("status", "completed")
        cached.setdefault("path", spatial_path)
        cached.setdefault("determinism", determinism_config)
        return cached

    if ttl_seconds > 0:
        increment_3d_metric("3d_cache_misses_total")

    start_time = time.time()
    try:
        engine = _import_measurement_engine()
        increment_3d_metric("3d_calls_total")
        points, fmt = engine.load_point_cloud(spatial_path)

        if not points:
            elapsed_ms = (time.time() - start_time) * 1000.0
            increment_3d_metric("3d_latency_ms_total", elapsed_ms)
            return {
                "status": "skipped",
                "reason": "no points loaded",
                "path": spatial_path,
                "format": fmt,
                "latency_ms": elapsed_ms,
                "cache_hit": False,
            }

        measurement = engine.measure_point_cloud(points, units=normalized_units)
        elapsed_ms = (time.time() - start_time) * 1000.0
        increment_3d_metric("3d_latency_ms_total", elapsed_ms)

        measurement = _augment_measurement_with_schema(
            measurement,
            spatial_path=spatial_path,
            units=normalized_units,
            points=len(points),
            fmt=fmt,
            latency_ms=elapsed_ms,
            determinism_config=determinism_config,
        )

        logger.debug(f"3D measurement with determinism config: {determinism_config}")

        result = {
            "status": "completed",
            "path": spatial_path,
            "format": fmt,
            "points": len(points),
            "measurement": measurement,
            "determinism": determinism_config,
            "latency_ms": elapsed_ms,
            "cache_hit": False,
        }

        max_latency_ms = limits.get("3d_max_latency_ms", 0)
        if max_latency_ms and elapsed_ms > max_latency_ms:
            result["latency_limit_exceeded"] = True
            logger.warning(
                "3D measurement latency %.2fms exceeded limit %sms for %s",
                elapsed_ms,
                max_latency_ms,
                spatial_path,
            )

        if ttl_seconds > 0 and result.get("status") == "completed":
            now = time.time()
            _evict_expired_entries(ttl_seconds, now)
            key = _make_cache_key(spatial_path, normalized_units, determinism_config)
            _store_cache_entry(key, result, now, max_entries=max_entries)

        return result
    except Exception as exc:
        elapsed_ms = (time.time() - start_time) * 1000.0
        increment_3d_metric("3d_failures_total")
        increment_3d_metric("3d_latency_ms_total", elapsed_ms)
        logger.exception(f"3D measurement failed for {spatial_path}")
        return {
            "status": "error",
            "error": str(exc),
            "path": spatial_path,
            "latency_ms": elapsed_ms,
            "cache_hit": False,
        }


def measure_ai_brain_for_record(
    record_path: str,
    *,
    record: Optional[Dict[str, Any]] = None,
    determinism_config: Optional[Dict[str, Any]] = None,
    units: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a semantic record and run AI_Brain measurement if it has a spatial path.

    Args:
        record_path: Path to the semantic record JSON.
        record: Optional pre-loaded record dict to avoid re-reading from disk.
        determinism_config: Optional determinism overrides; defaults to config values.
        units: Optional units override; defaults to the record/"meters".

    Returns:
        Measurement output dict augmented with record_path.
    """

    rec: Optional[Dict[str, Any]]
    if record is not None:
        if not isinstance(record, dict):
            return {
                "status": "error",
                "error": "record parameter must be dict",
                "record_path": record_path,
            }
        rec = record
    else:
        try:
            with open(record_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except Exception as exc:
            return {
                "status": "error",
                "error": f"failed to load record: {exc}",
                "record_path": record_path,
            }
        if not isinstance(loaded, dict):
            return {
                "status": "error",
                "error": "record data is not an object",
                "record_path": record_path,
            }
        rec = loaded

    spatial_path = _extract_spatial_path(rec)
    if not spatial_path:
        return {
            "status": "skipped",
            "reason": "no spatial asset path in record",
            "record_path": record_path,
        }

    resolved_units = units if isinstance(units, str) and units.strip() else _extract_units(rec)
    det_config = determinism_config if isinstance(determinism_config, dict) else get_3d_determinism_config()

    result = measure_ai_brain(spatial_path, units=resolved_units, determinism_config=det_config)
    result["record_path"] = record_path
    return result

def validate_3d_measurement_schema(obj: Any) -> Dict[str, Any]:
    """Validate that a 3D measurement output conforms to the canonical schema v1.0.

    Args:
        obj: The measurement output dict to validate.

    Returns:
        The validated dict (same object, for chaining).

    Raises:
        SchemaError: If required fields are missing or types are incorrect.
        TypeError: If obj is not a dict.
    """
    if not isinstance(obj, dict):
        raise TypeError(f"Expected dict, got {type(obj).__name__}")

    # Required fields with type checks
    required_fields = {
        "version": str,
        "space_id": str,
        "timestamp": str,
        "entities": list,
        "constraints": list,
        "metrics": dict,
        "source": str,
    }

    for field, expected_type in required_fields.items():
        if field not in obj:
            raise SchemaError(f"Missing required field: {field}")
        val = obj[field]
        if not isinstance(val, expected_type):
            raise SchemaError(
                f"Field {field!r}: expected {expected_type.__name__}, got {type(val).__name__}"
            )

    # Validate source enum
    if obj["source"] not in ("3d",):
        raise SchemaError(f"Field 'source' must be '3d', got {obj['source']!r}")

    # Validate version format (e.g., "1.0")
    version_parts = obj["version"].split(".")
    if not (len(version_parts) >= 2 and all(p.isdigit() for p in version_parts[:2])):
        raise SchemaError(f"Field 'version' must match format '1.0' or similar, got {obj['version']!r}")

    # Validate timestamp is ISO 8601-like
    try:
        # Basic check: contains 'T' and 'Z' for UTC
        ts = obj["timestamp"]
        if not (isinstance(ts, str) and "T" in ts and "Z" in ts):
            raise ValueError("Timestamp must be ISO 8601 UTC format")
    except Exception as e:
        raise SchemaError(f"Field 'timestamp': {e}")

    # Validate entities list (if non-empty, check structure)
    if obj["entities"]:
        for i, entity in enumerate(obj["entities"]):
            if not isinstance(entity, dict):
                raise SchemaError(f"entities[{i}]: expected dict, got {type(entity).__name__}")
            if "id" not in entity:
                raise SchemaError(f"entities[{i}]: missing required field 'id'")
            if "type" not in entity:
                raise SchemaError(f"entities[{i}]: missing required field 'type'")

    # Validate constraints list (if non-empty, check structure)
    if obj["constraints"]:
        for i, constraint in enumerate(obj["constraints"]):
            if not isinstance(constraint, dict):
                raise SchemaError(f"constraints[{i}]: expected dict, got {type(constraint).__name__}")
            if "type" not in constraint:
                raise SchemaError(f"constraints[{i}]: missing required field 'type'")

    # Validate metrics dict
    metrics = obj["metrics"]
    if "latency_ms" not in metrics:
        raise SchemaError("metrics: missing required field 'latency_ms'")
    if "success" not in metrics:
        raise SchemaError("metrics: missing required field 'success'")
    if not isinstance(metrics["latency_ms"], int):
        raise SchemaError(
            f"metrics.latency_ms: expected int, got {type(metrics['latency_ms']).__name__}"
        )
    if not isinstance(metrics["success"], bool):
        raise SchemaError(
            f"metrics.success: expected bool, got {type(metrics['success']).__name__}"
        )

    logger.debug(f"3D measurement schema validation passed for space_id={obj.get('space_id')}")
    return obj


def _normalize_entities(raw_entities: Any) -> List[Dict[str, Any]]:
    if raw_entities is None:
        return []
    if isinstance(raw_entities, list):
        normalized: List[Dict[str, Any]] = []
        for item in raw_entities:
            if isinstance(item, dict):
                normalized.append(dict(item))
            else:
                normalized.append({"value": item})
        return normalized
    if isinstance(raw_entities, dict):
        return [
            {"id": key, **value} if isinstance(value, dict) else {"id": key, "value": value}
            for key, value in raw_entities.items()
        ]
    return [{"value": raw_entities}]


def _normalize_relations(raw_relations: Any) -> List[Dict[str, Any]]:
    if raw_relations is None:
        return []
    if isinstance(raw_relations, list):
        normalized: List[Dict[str, Any]] = []
        for item in raw_relations:
            if isinstance(item, dict):
                normalized.append(dict(item))
            else:
                normalized.append({"value": item})
        return normalized
    if isinstance(raw_relations, dict):
        return [dict(raw_relations)]
    return [{"value": raw_relations}]


def _normalize_constraints(raw_constraints: Any) -> List[Dict[str, Any]]:
    if raw_constraints is None:
        return []
    if isinstance(raw_constraints, list):
        normalized: List[Dict[str, Any]] = []
        for item in raw_constraints:
            if isinstance(item, dict):
                normalized.append(dict(item))
            else:
                normalized.append({"value": item})
        return normalized
    if isinstance(raw_constraints, dict):
        return [dict(raw_constraints)]
    return [{"value": raw_constraints}]


def _deterministic_timestamp(measurement: Dict[str, Any]) -> str:
    meta = measurement.get("meta") or {}
    ts = meta.get("timestamp") if isinstance(meta, dict) else None
    if isinstance(ts, str) and ts:
        return ts
    env_ts = os.environ.get(DETERMINISTIC_TS_ENV)
    if env_ts:
        return env_ts
    return "1970-01-01T00:00:00Z"


def process_measurement(measurement: Dict[str, Any], ai_brain_client: Any) -> Dict[str, Any]:
    """Run ai_brain_client over measurement and normalize output for downstream adapters.

    The normalized payload is intended for attachment under `relational_state`
    (entities/relations/constraints) while the raw measurement remains stored
    in `relational_state.spatial_measurement` by the relational adapter.
    """

    if measurement is None:
        raise ValueError("measurement must be provided")

    timestamp = _deterministic_timestamp(measurement)
    if not isinstance(measurement.get("meta"), dict):
        measurement["meta"] = {}
    measurement["meta"]["timestamp"] = timestamp

    try:
        if hasattr(ai_brain_client, "process"):
            raw_out = ai_brain_client.process(measurement)
        elif callable(ai_brain_client):
            raw_out = ai_brain_client(measurement)
        else:
            raise TypeError("ai_brain_client must provide a process(measurement) method")
    except Exception:
        # Re-raise so tests can assert on the original exception type.
        raise

    if not isinstance(raw_out, dict):
        raise TypeError("ai_brain_client returned non-dict result")

    normalized = {
        "entities": _normalize_entities(raw_out.get("entities")),
        "relations": _normalize_relations(raw_out.get("relations")),
        "constraints": _normalize_constraints(raw_out.get("constraints")),
        "timestamp": raw_out.get("timestamp") or timestamp,
        "source": raw_out.get("source", "3d"),
    }

    if "api_version" in raw_out:
        normalized["api_version"] = raw_out["api_version"]
    if "extras" in raw_out:
        normalized["extras"] = raw_out["extras"]

    # Ensure upstream measurement metadata reflects the normalized timestamp.
    if isinstance(measurement.get("meta"), dict):
        measurement["meta"]["timestamp"] = normalized["timestamp"]

    return normalized


def normalize_composition_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a validated composition fixture bundle into bridge-normalized rows.

    This is additive to the existing spatial measurement path and does not
    alter `source="3d"` measurement behavior.
    """

    if not isinstance(bundle, dict):
        raise TypeError(f"Expected dict, got {type(bundle).__name__}")

    request = bundle.get("request")
    response = bundle.get("response")
    recipe = bundle.get("recipe_sidecar")
    scene_manifest = bundle.get("scene_manifest")
    validation_summary = bundle.get("validation_summary")
    bridge_ready = bundle.get("bridge_ready")

    for label, value in (
        ("request", request),
        ("response", response),
        ("recipe_sidecar", recipe),
        ("scene_manifest", scene_manifest),
        ("validation_summary", validation_summary),
        ("bridge_ready", bridge_ready),
    ):
        if not isinstance(value, dict):
            raise TypeError(f"{label} must be a dict")

    determinism = request.get("determinism") if isinstance(request.get("determinism"), dict) else {}
    timestamp = determinism.get("fixed_timestamp") if isinstance(determinism.get("fixed_timestamp"), str) else None
    if not timestamp:
        timestamp = _resolve_3d_timestamp(get_3d_determinism_config())

    scene_id = str(scene_manifest.get("scene_id") or request.get("scene_id") or "scene_unknown")
    scene_entity_id = f"{scene_id}::scene"
    inventory = scene_manifest.get("object_inventory") if isinstance(scene_manifest.get("object_inventory"), list) else []

    def _scene_object_entity_id(object_id: Any) -> Optional[str]:
        if isinstance(object_id, str) and object_id:
            return f"{scene_id}::object::{object_id}"
        return None

    entities: List[Dict[str, Any]] = [
        {
            "id": scene_entity_id,
            "type": "scene",
            "attributes": {
                "scene_name": scene_manifest.get("scene_name"),
                "recipe_id": scene_manifest.get("recipe_id"),
                "recipe_version": scene_manifest.get("recipe_version"),
            },
            "source": "3d_scene_summary",
        }
    ]

    for item in inventory:
        if not isinstance(item, dict):
            continue
        item_id = _scene_object_entity_id(item.get("id"))
        item_type = item.get("type") if isinstance(item.get("type"), str) else "object"
        if not item_id:
            continue
        attributes = {k: deepcopy(v) for k, v in item.items() if k not in {"id", "type"}}
        entities.append(
            {
                "id": item_id,
                "type": item_type,
                "attributes": attributes,
                "source": "3d_scene_summary",
            }
        )

    relations: List[Dict[str, Any]] = []
    active_camera = scene_manifest.get("active_camera")
    active_lights = scene_manifest.get("active_lights") if isinstance(scene_manifest.get("active_lights"), list) else []
    active_camera_entity = _scene_object_entity_id(active_camera)
    if active_camera_entity:
        relations.append(
            {
                "subj": active_camera_entity,
                "pred": "observes_scene",
                "obj": scene_entity_id,
                "confidence": 1.0,
                "evidence": ["composition_scene_manifest"],
                "source": "3d_scene_summary",
            }
        )
    for light_id in active_lights:
        light_entity = _scene_object_entity_id(light_id)
        if light_entity:
            relations.append(
                {
                    "subj": light_entity,
                    "pred": "illuminates_scene",
                    "obj": scene_entity_id,
                    "confidence": 1.0,
                    "evidence": ["composition_scene_manifest"],
                    "source": "3d_scene_summary",
                }
            )
    relations.append(
        {
            "subj": scene_entity_id,
            "pred": "derived_from_recipe",
            "obj": f"{recipe.get('recipe_id')}@{recipe.get('recipe_version')}",
            "confidence": 1.0,
            "evidence": ["composition_recipe_sidecar"],
            "source": "3d_scene_summary",
        }
    )

    checks = validation_summary.get("checks") if isinstance(validation_summary.get("checks"), list) else []
    constraints: List[Dict[str, Any]] = []
    for check in sorted(
        [item for item in checks if isinstance(item, dict)],
        key=lambda item: str(item.get("name") or ""),
    ):
        name = str(check.get("name") or "")
        severity = "hard" if name in {"object_count", "active_camera", "export_target"} else "soft"
        args: Dict[str, Any] = {
            "scene_id": scene_id,
            "check_name": name,
            "expected": deepcopy(check.get("expected")),
            "actual": deepcopy(check.get("actual")),
        }
        if name == "active_camera" and active_camera_entity:
            args["entity_id"] = active_camera_entity
        constraints.append(
            {
                "type": "scene_validation",
                "args": args,
                "severity": severity,
                "status": check.get("status"),
                "source": "3d_scene_summary",
            }
        )

    inventory_hash = hashlib.sha256(canonical_json_bytes(inventory)).hexdigest()
    emitted_artifacts = response.get("emitted_artifacts") if isinstance(response.get("emitted_artifacts"), list) else []
    evidence_refs = [
        artifact.get("path")
        for artifact in emitted_artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("path"), str)
    ]
    measurement_candidate = resolve_composition_export_measurement_candidate(response, scene_manifest)

    normalized = {
        "timestamp": timestamp,
        "source": "3d_scene_summary",
        "api_version": "scene_summary_bridge.v1",
        "entities": entities,
        "relations": relations,
        "constraints": constraints,
        "extras": {
            "scene_id": scene_id,
            "scene_schema_version": scene_manifest.get("recipe_version"),
            "recipe": {
                "recipe_id": recipe.get("recipe_id"),
                "recipe_version": recipe.get("recipe_version"),
                "recipe_hash": recipe.get("recipe_hash"),
            },
            "validation": deepcopy(validation_summary),
            "inventory_hash": inventory_hash,
            "scene_hash": scene_manifest.get("scene_hash"),
            "summary_hash": validation_summary.get("summary_hash"),
            "bundle_hash": bundle.get("bundle_hash"),
            "bridge_ready_hash": hashlib.sha256(canonical_json_bytes(bridge_ready)).hexdigest(),
            "evidence_refs": evidence_refs,
            "measurement_candidate": deepcopy(measurement_candidate),
        },
    }
    return normalized


def normalize_composition_record_for_bridge(
    record: Dict[str, Any],
    *,
    determinism_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Normalize composition sidecars on a semantic record into bridge outputs."""

    if not isinstance(record, dict):
        return []

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict):
        return []

    scene_manifest_raw = artifacts.get("composition_scene_summary")
    if not isinstance(scene_manifest_raw, dict):
        scene_manifest_raw = artifacts.get("scene_manifest") if isinstance(artifacts.get("scene_manifest"), dict) else None

    recipe_sidecar_raw = artifacts.get("composition_recipe")
    if not isinstance(recipe_sidecar_raw, dict):
        recipe_sidecar_raw = artifacts.get("recipe_sidecar") if isinstance(artifacts.get("recipe_sidecar"), dict) else None

    validation_summary_raw = artifacts.get("composition_validation_summary")
    if not isinstance(validation_summary_raw, dict):
        validation_summary_raw = artifacts.get("validation_summary") if isinstance(artifacts.get("validation_summary"), dict) else None

    if not (
        isinstance(scene_manifest_raw, dict)
        and isinstance(recipe_sidecar_raw, dict)
        and isinstance(validation_summary_raw, dict)
    ):
        return []

    scene_manifest = deepcopy(validate_scene_manifest(scene_manifest_raw))
    recipe_sidecar = deepcopy(validate_recipe_sidecar(recipe_sidecar_raw))
    validation_summary = deepcopy(validate_validation_summary(validation_summary_raw))

    request = artifacts.get("composition_request") if isinstance(artifacts.get("composition_request"), dict) else None
    response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else None

    if isinstance(request, dict) and isinstance(response, dict):
        bundle = build_composition_fixture_bundle(
            request,
            response,
            recipe_sidecar,
            scene_manifest,
            validation_summary,
        )
        return [normalize_composition_bundle(bundle)]

    normalized_determinism = determinism_config if isinstance(determinism_config, dict) else get_3d_determinism_config()
    timestamp = _resolve_3d_timestamp(normalized_determinism)
    emitted_artifacts = [
        {
            "kind": export.get("format"),
            "path": export.get("path"),
        }
        for export in scene_manifest.get("exports", [])
        if isinstance(export, dict)
        and isinstance(export.get("format"), str)
        and export.get("format")
        and isinstance(export.get("path"), str)
        and export.get("path")
    ]
    bridge_ready = {
        "request_id": validation_summary.get("request_id"),
        "scene_id": scene_manifest.get("scene_id"),
        "recipe_hash": recipe_sidecar.get("recipe_hash"),
        "entities": [
            {"id": item.get("id"), "type": item.get("type")}
            for item in scene_manifest.get("object_inventory", [])
            if isinstance(item, dict)
        ],
        "constraints": [
            {
                "type": "scene_validation",
                "name": check.get("name"),
                "status": check.get("status"),
                "expected": deepcopy(check.get("expected")),
                "actual": deepcopy(check.get("actual")),
            }
            for check in validation_summary.get("checks", [])
            if isinstance(check, dict)
        ],
        "artifacts": {
            "scene_hash": scene_manifest.get("scene_hash"),
            "summary_hash": validation_summary.get("summary_hash"),
            "emitted": emitted_artifacts,
        },
        "validation_status": validation_summary.get("status"),
    }
    bundle = {
        "request": {
            "request_id": validation_summary.get("request_id") or record.get("id") or "composition_request_unknown",
            "scene_id": scene_manifest.get("scene_id"),
            "determinism": {"fixed_timestamp": timestamp},
        },
        "response": {"emitted_artifacts": emitted_artifacts},
        "recipe_sidecar": recipe_sidecar,
        "scene_manifest": scene_manifest,
        "validation_summary": validation_summary,
        "bridge_ready": bridge_ready,
        "bundle_hash": hashlib.sha256(
            canonical_json_bytes(
                {
                    "scene_id": scene_manifest.get("scene_id"),
                    "recipe_hash": recipe_sidecar.get("recipe_hash"),
                    "bridge_ready": bridge_ready,
                }
            )
        ).hexdigest(),
    }
    return [normalize_composition_bundle(bundle)]