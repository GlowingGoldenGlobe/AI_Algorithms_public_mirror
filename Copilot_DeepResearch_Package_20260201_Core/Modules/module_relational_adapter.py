import json
import re
import time
import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, TypedDict

from module_ai_brain_bridge import (
    measure_ai_brain_for_record,
    get_3d_limits,
    peek_cached_measurement,
    get_3d_determinism_config,
)
from module_storage import _atomic_write_json


logger = logging.getLogger(__name__)


class Raw3DObject(TypedDict):
    object_id: str
    position: list[float]
    rotation: list[float]
    scale: list[float]
    properties: dict[str, Any]


class Raw3DRelation(TypedDict):
    relation_id: str
    type: str
    source_object_id: str
    target_object_id: str
    strength: float


class RelationalEntity(TypedDict):
    entity_id: str
    attributes: dict[str, Any]


class RelationalLink(TypedDict):
    link_id: str
    type: str
    source_id: str
    target_id: str
    weight: float


class RelationalState(TypedDict):
    entities: dict[str, RelationalEntity]
    links: dict[str, RelationalLink]
    contexts: dict[str, Any]


_CYCLE_STALE_SECONDS = 15 * 60
_DEFAULT_CYCLE_ID = "__default__"
_CYCLE_ID_REGEX = re.compile(r"(cycle_[A-Za-z0-9_-]+)", re.IGNORECASE)

_3d_cycle_counters: Dict[str, Dict[str, Any]] = {}


def _extract_spatial_path_from_record(rec: Dict[str, Any]) -> Optional[str]:
    for key in ("spatial_asset_path", "point_cloud_path", "mesh_path"):
        val = rec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    meta = rec.get("metadata") if isinstance(rec, dict) else None
    if isinstance(meta, dict):
        for key in ("spatial_asset_path", "point_cloud_path", "mesh_path"):
            val = meta.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def _extract_units_from_record(rec: Dict[str, Any]) -> str:
    units = "meters"
    try:
        candidate = rec.get("units")
        if not (isinstance(candidate, str) and candidate.strip()):
            meta = rec.get("metadata") if isinstance(rec, dict) else None
            if isinstance(meta, dict):
                candidate = meta.get("units")
        if isinstance(candidate, str) and candidate.strip():
            units = candidate.strip()
    except Exception:
        pass
    return units


def _derive_cycle_identifier(rec: Dict[str, Any], record_path: str) -> str:
    candidates = [
        rec.get("cycle_id") if isinstance(rec, dict) else None,
        (rec.get("cycle_artifact") or {}).get("cycle_id") if isinstance(rec, dict) else None,
        (rec.get("metadata") or {}).get("cycle_id") if isinstance(rec, dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    record_id = rec.get("id") if isinstance(rec, dict) else None
    if isinstance(record_id, str) and record_id.strip():
        return record_id.strip()

    match = _CYCLE_ID_REGEX.search(record_path or "")
    if match:
        return match.group(1)

    return _DEFAULT_CYCLE_ID


def _prune_stale_cycle_counters(now: float) -> None:
    stale = [
        key
        for key, entry in _3d_cycle_counters.items()
        if now - entry.get("last_seen", now) > _CYCLE_STALE_SECONDS
    ]
    for key in stale:
        _3d_cycle_counters.pop(key, None)


def _get_cycle_tracker(cycle_id: str, now: float) -> Dict[str, Any]:
    tracker = _3d_cycle_counters.get(cycle_id)
    if not tracker:
        tracker = {"count": 0, "last_seen": now}
        _3d_cycle_counters[cycle_id] = tracker
    else:
        tracker["last_seen"] = now
    return tracker


def reset_3d_cycle_counters() -> None:
    _3d_cycle_counters.clear()


def get_3d_cycle_counters_snapshot() -> Dict[str, Any]:
    return {
        cycle_id: {"count": entry.get("count", 0), "last_seen": entry.get("last_seen")}
        for cycle_id, entry in _3d_cycle_counters.items()
    }


def _ensure_relational_state(rec: Dict[str, Any]) -> Dict[str, Any]:
    rs = rec.get("relational_state")
    if not isinstance(rs, dict):
        rs = {}
        rec["relational_state"] = rs

    rs.setdefault("entities", [])
    rs.setdefault("relations", [])
    rs.setdefault("constraints", [])
    rs.setdefault("objective_links", [])
    rs.setdefault("spatial_measurement", None)
    rs.setdefault("decision_trace", {})
    rs.setdefault("bridge_outputs", [])

    if not isinstance(rs.get("entities"), list):
        rs["entities"] = []
    if not isinstance(rs.get("relations"), list):
        rs["relations"] = []
    if not isinstance(rs.get("constraints"), list):
        rs["constraints"] = []
    if not isinstance(rs.get("objective_links"), list):
        rs["objective_links"] = []
    if not isinstance(rs.get("bridge_outputs"), list):
        rs["bridge_outputs"] = []

    return rs


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_spatial_entity(record_id: str, measurement: Dict[str, Any]) -> Dict[str, Any]:
    entity_id = f"{record_id}::spatial_object"
    return {
        "id": entity_id,
        "type": "spatial_object",
        "attributes": {
            "units": measurement.get("units"),
            "count": measurement.get("count"),
            "centroid": measurement.get("centroid"),
            "bounds": measurement.get("bounds"),
            "volume": measurement.get("volume"),
            "shape": measurement.get("shape"),
            "aabb_dimensions": measurement.get("aabb_dimensions"),
            "aabb_surface_area": measurement.get("aabb_surface_area"),
        },
        "source": "3d",
    }


def _build_spatial_relations(entity_id: str, measurement: Dict[str, Any]) -> List[Dict[str, Any]]:
    shape = measurement.get("shape") or "unknown"
    volume = measurement.get("volume", 0.0)
    extent = measurement.get("aabb_dimensions", {})

    return [
        {
            "subj": entity_id,
            "pred": "has_shape",
            "obj": str(shape),
            "confidence": 0.9,
            "evidence": ["3d_measurement_core"],
            "source": "3d",
        },
        {
            "subj": entity_id,
            "pred": "has_volume",
            "obj": str(volume),
            "confidence": 0.9,
            "evidence": ["3d_measurement_core"],
            "source": "3d",
        },
        {
            "subj": entity_id,
            "pred": "has_extent",
            "obj": _stable_json(extent if isinstance(extent, dict) else {}),
            "confidence": 0.9,
            "evidence": ["3d_measurement_core"],
            "source": "3d",
        },
    ]


def _build_spatial_constraints(entity_id: str, measurement: Dict[str, Any]) -> List[Dict[str, Any]]:
    units = measurement.get("units")
    bounds = measurement.get("bounds")
    volume = measurement.get("volume")

    return [
        {
            "type": "spatial",
            "args": {"entity_id": entity_id, "bounds": bounds, "units": units},
            "severity": "hard",
            "source": "3d",
        },
        {
            "type": "spatial",
            "args": {"entity_id": entity_id, "volume": volume, "units": units},
            "severity": "soft",
            "source": "3d",
        },
    ]


def _dedupe_replace_by_entity_id(entities: List[Dict[str, Any]], new_entity: Dict[str, Any]) -> None:
    new_id = new_entity.get("id")
    if not isinstance(new_id, str) or not new_id:
        entities.append(new_entity)
        return
    entities[:] = [e for e in entities if not (isinstance(e, dict) and e.get("id") == new_id)]
    entities.append(new_entity)


def _remove_prior_3d_subject(rows: List[Dict[str, Any]], entity_id: str) -> None:
    rows[:] = [
        r
        for r in rows
        if not (
            isinstance(r, dict)
            and r.get("source") == "3d"
            and (
                r.get("subj") == entity_id
                or (
                    isinstance((r.get("args") or {}), dict)
                    and (r.get("args") or {}).get("entity_id") == entity_id
                )
            )
        )
    ]


def _persist_bridge_outputs(
    rs: Dict[str, Any],
    normalized: Dict[str, Any],
    *,
    record_id: str,
    record_path: str,
) -> None:
    outputs = rs.setdefault("bridge_outputs", [])
    if not isinstance(outputs, list):
        outputs = []
        rs["bridge_outputs"] = outputs

    entry = deepcopy(normalized)
    entry.setdefault("record_id", record_id)
    entry.setdefault("record_path", record_path)
    timestamp = entry.get("timestamp")

    outputs[:] = [
        existing
        for existing in outputs
        if not (
            isinstance(existing, dict)
            and existing.get("record_id") == record_id
            and existing.get("timestamp") == timestamp
        )
    ]
    outputs.append(entry)


def attach_spatial_relational_state(record_path: str) -> Dict[str, Any]:
    now = time.time()
    _prune_stale_cycle_counters(now)

    try:
        with open(record_path, "r", encoding="utf-8") as handle:
            rec = json.load(handle)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "failed to load record"}

    if not isinstance(rec, dict):
        return {"record_path": record_path, "status": "error", "reason": "record_not_object"}

    spatial_path = _extract_spatial_path_from_record(rec)
    if not spatial_path:
        return {"record_path": record_path, "status": "skipped", "reason": "no spatial asset path in record"}

    units = _extract_units_from_record(rec)
    determinism_config = get_3d_determinism_config()
    limits = get_3d_limits()
    max_calls = limits.get("3d_max_calls_per_cycle", 0)

    measurement_out = peek_cached_measurement(
        spatial_path,
        units=units,
        determinism_config=determinism_config,
        limits=limits,
    )

    cycle_tracker: Optional[Dict[str, Any]] = None
    cycle_id = _derive_cycle_identifier(rec, record_path)

    if measurement_out is not None:
        measurement_out["record_path"] = record_path
    else:
        if max_calls and max_calls > 0:
            cycle_tracker = _get_cycle_tracker(cycle_id, now)
            if cycle_tracker.get("count", 0) >= max_calls:
                logger.debug(
                    "3D measurement call limit reached for cycle %s (limit=%s)",
                    cycle_id,
                    max_calls,
                )
                return {
                    "record_path": record_path,
                    "status": "skipped",
                    "reason": "3d_call_limit_reached",
                    "cycle_id": cycle_id,
                    "limit": max_calls,
                }
            cycle_tracker["count"] = cycle_tracker.get("count", 0) + 1

        measurement_out = measure_ai_brain_for_record(
            record_path,
            record=rec,
            determinism_config=determinism_config,
            units=units,
        )

        if cycle_tracker is not None:
            cycle_tracker["last_seen"] = time.time()
            if measurement_out.get("cache_hit"):
                cycle_tracker["count"] = max(0, cycle_tracker.get("count", 0) - 1)

    status = measurement_out.get("status")
    if status != "completed":
        return {
            "record_path": record_path,
            "status": status or "error",
            "reason": measurement_out.get("reason")
            or measurement_out.get("error")
            or "measurement_not_completed",
        }

    measurement = measurement_out.get("measurement")
    if not isinstance(measurement, dict):
        return {"record_path": record_path, "status": "error", "reason": "missing measurement block"}

    record_id = rec.get("id") if isinstance(rec, dict) else None
    if not isinstance(record_id, str) or not record_id:
        record_id = "unknown"

    rs = _ensure_relational_state(rec)

    normalized_payloads = measurement_out.get("bridge_normalized")
    if isinstance(normalized_payloads, dict):
        normalized_payloads_iter = [normalized_payloads]
    elif isinstance(normalized_payloads, list):
        normalized_payloads_iter = [payload for payload in normalized_payloads if isinstance(payload, dict)]
    else:
        normalized_payloads_iter = []

    for payload in normalized_payloads_iter:
        _persist_bridge_outputs(rs, payload, record_id=record_id, record_path=record_path)

    rs["spatial_measurement"] = measurement

    if measurement.get("ok") is False:
        try:
            _atomic_write_json(record_path, rec)
            return {"record_path": record_path, "status": "skipped", "reason": "measurement_ok_false"}
        except Exception:
            return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    entity = _build_spatial_entity(record_id, measurement)
    entity_id = entity["id"]

    entities = rs.get("entities")
    relations = rs.get("relations")
    constraints = rs.get("constraints")

    if not isinstance(entities, list) or not isinstance(relations, list) or not isinstance(constraints, list):
        return {"record_path": record_path, "status": "error", "reason": "relational_state lists invalid"}

    _dedupe_replace_by_entity_id(entities, entity)

    _remove_prior_3d_subject(relations, entity_id)
    relations.extend(_build_spatial_relations(entity_id, measurement))

    _remove_prior_3d_subject(constraints, entity_id)
    constraints.extend(_build_spatial_constraints(entity_id, measurement))

    try:
        _atomic_write_json(record_path, rec)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    return {"record_path": record_path, "status": "completed"}


def objects_to_entities(
    objects: list[Raw3DObject],
    context_id: str,
) -> dict[str, RelationalEntity]:
    entities: dict[str, RelationalEntity] = {}
    for obj in objects:
        oid = obj.get("object_id")
        if not isinstance(oid, str) or not oid:
            continue
        entities[oid] = {
            "entity_id": oid,
            "attributes": {
                "position": obj.get("position"),
                "rotation": obj.get("rotation"),
                "scale": obj.get("scale"),
                "properties": obj.get("properties"),
                "context_id": context_id,
            },
        }
    return entities


def relations_to_links(
    relations: list[Raw3DRelation],
    context_id: str,
) -> dict[str, RelationalLink]:
    _ = context_id
    links: dict[str, RelationalLink] = {}
    for rel in relations:
        rid = rel.get("relation_id")
        if not isinstance(rid, str) or not rid:
            continue
        links[rid] = {
            "link_id": rid,
            "type": rel.get("type") if isinstance(rel.get("type"), str) else "",
            "source_id": rel.get("source_object_id") if isinstance(rel.get("source_object_id"), str) else "",
            "target_id": rel.get("target_object_id") if isinstance(rel.get("target_object_id"), str) else "",
            "weight": float(rel.get("strength") or 0.0),
        }
    return links


def build_relational_state(
    objects: list[Raw3DObject],
    relations: list[Raw3DRelation],
    context_id: str,
    context_metadata: dict[str, Any],
) -> RelationalState:
    entities = objects_to_entities(objects, context_id)
    links = relations_to_links(relations, context_id)
    return {
        "entities": entities,
        "links": links,
        "contexts": {
            context_id: dict(context_metadata) if isinstance(context_metadata, dict) else {},
        },
    }


def update_relational_state(
    state: RelationalState,
    objects: list[Raw3DObject],
    relations: list[Raw3DRelation],
    context_id: str,
    context_metadata: dict[str, Any],
) -> RelationalState:
    prev_entities = state.get("entities") if isinstance(state, dict) else None
    prev_links = state.get("links") if isinstance(state, dict) else None
    prev_contexts = state.get("contexts") if isinstance(state, dict) else None
    new_state: RelationalState = {
        "entities": dict(prev_entities) if isinstance(prev_entities, dict) else {},
        "links": dict(prev_links) if isinstance(prev_links, dict) else {},
        "contexts": dict(prev_contexts) if isinstance(prev_contexts, dict) else {},
    }

    new_entities = objects_to_entities(objects, context_id)
    new_links = relations_to_links(relations, context_id)

    new_state["entities"].update(new_entities)
    new_state["links"].update(new_links)
    new_state["contexts"][context_id] = dict(context_metadata) if isinstance(context_metadata, dict) else {}
    return new_state
