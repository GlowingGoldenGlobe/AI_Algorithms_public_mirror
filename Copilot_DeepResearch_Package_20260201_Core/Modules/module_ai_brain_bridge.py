# module_ai_brain_bridge.py
import json
import os
import sys
import time
import logging
from collections import OrderedDict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Thread-safe metrics tracking for 3D operations
_3d_metrics = {
    "3d_calls_total": 0,
    "3d_failures_total": 0,
    "3d_latency_ms_total": 0.0,
    "3d_cache_hits_total": 0,
    "3d_cache_misses_total": 0,
}

CacheKey = Tuple[str, str, Tuple[Tuple[str, Any], ...]]

_MAX_CACHE_ENTRIES = 64
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


def _store_cache_entry(key: CacheKey, result: Dict[str, Any], timestamp: float) -> None:
    _3d_cache[key] = {"timestamp": timestamp, "result": deepcopy(result)}
    _3d_cache.move_to_end(key)
    while len(_3d_cache) > _MAX_CACHE_ENTRIES:
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
    return {"size": len(_3d_cache), "entries": entries}


def get_3d_limits(config: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    cfg = config if isinstance(config, dict) else _load_config_from_disk()
    limits = cfg.get("3d_limits", {}) if isinstance(cfg, dict) else {}
    max_calls = limits.get("3d_max_calls_per_cycle", 0)
    ttl_seconds = limits.get("3d_cache_ttl_seconds", 0)
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
        max_latency = int(max_latency)
    except Exception:
        max_latency = 0
    return {
        "3d_max_calls_per_cycle": max(0, max_calls),
        "3d_cache_ttl_seconds": max(0, ttl_seconds),
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
    """Import AI_Brain's measurement_engine as a normal Python module."""

    ai_dir = _ai_brain_dir()
    if ai_dir not in sys.path:
        sys.path.insert(0, ai_dir)
    import measurement_engine  # type: ignore

    return measurement_engine


def _extract_spatial_path(rec: Dict[str, Any]) -> Optional[str]:
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


def get_3d_determinism_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config if isinstance(config, dict) else _load_config_from_disk()
    det_block = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
    return {
        "3d_seed": det_block.get("3d_seed", 42),
        "3d_fixed_timestamps": det_block.get("3d_fixed_timestamps", True),
        "3d_noise_mode": det_block.get("3d_noise_mode", "none"),
    }


def measure_ai_brain(
    spatial_path: str,
    *,
    units: str = "meters",
    determinism_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if determinism_config is None:
        determinism_config = get_3d_determinism_config()

    if not isinstance(spatial_path, str) or not spatial_path.strip():
        return {"status": "skipped", "reason": "empty spatial_path", "cache_hit": False}

    spatial_path = spatial_path.strip()
    if not os.path.exists(spatial_path):
        return {
            "status": "skipped",
            "reason": "spatial asset not found",
            "path": spatial_path,
            "cache_hit": False,
        }

    normalized_units = units.strip() if isinstance(units, str) else "meters"
    limits = get_3d_limits()
    ttl_seconds = limits.get("3d_cache_ttl_seconds", 0)

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
            _store_cache_entry(key, result, now)

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
    if not isinstance(obj, dict):
        raise TypeError(f"Expected dict, got {type(obj).__name__}")

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

    if obj["source"] not in ("3d",):
        raise SchemaError(f"Field 'source' must be '3d', got {obj['source']!r}")

    version_parts = obj["version"].split(".")
    if not (len(version_parts) >= 2 and all(p.isdigit() for p in version_parts[:2])):
        raise SchemaError(
            f"Field 'version' must match format '1.0' or similar, got {obj['version']!r}"
        )

    try:
        ts = obj["timestamp"]
        if not (isinstance(ts, str) and "T" in ts and "Z" in ts):
            raise ValueError("Timestamp must be ISO 8601 UTC format")
    except Exception as exc:
        raise SchemaError(f"Field 'timestamp': {exc}")

    if obj["entities"]:
        for i, entity in enumerate(obj["entities"]):
            if not isinstance(entity, dict):
                raise SchemaError(f"entities[{i}]: expected dict, got {type(entity).__name__}")
            if "id" not in entity:
                raise SchemaError(f"entities[{i}]: missing required field 'id'")
            if "type" not in entity:
                raise SchemaError(f"entities[{i}]: missing required field 'type'")

    if obj["constraints"]:
        for i, constraint in enumerate(obj["constraints"]):
            if not isinstance(constraint, dict):
                raise SchemaError(f"constraints[{i}]: expected dict, got {type(constraint).__name__}")
            if "type" not in constraint:
                raise SchemaError(f"constraints[{i}]: missing required field 'type'")

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

    logger.debug(
        "3D measurement schema validation passed for space_id=%s",
        obj.get("space_id"),
    )
    return obj


DETERMINISTIC_TS_ENV = "DETERMINISTIC_TIMESTAMP"


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
        raise

    if not isinstance(raw_out, dict):
        raise TypeError("ai_brain_client returned non-dict result")

    normalized = {
        "entities": _normalize_entities(raw_out.get("entities")),
        "relations": _normalize_relations(raw_out.get("relations")),
        "timestamp": raw_out.get("timestamp") or timestamp,
        "source": raw_out.get("source", "3d"),
    }

    if "api_version" in raw_out:
        normalized["api_version"] = raw_out["api_version"]
    if "extras" in raw_out:
        normalized["extras"] = raw_out["extras"]

    if isinstance(measurement.get("meta"), dict):
        measurement["meta"]["timestamp"] = normalized["timestamp"]

    return normalized
