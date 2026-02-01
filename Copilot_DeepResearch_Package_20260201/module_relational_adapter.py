import json
from typing import Any, Dict, List, Optional, TypedDict

from module_ai_brain_bridge import measure_ai_brain_for_record
from module_storage import _atomic_write_json


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

    # Normalize list fields if corrupted.
    if not isinstance(rs.get("entities"), list):
        rs["entities"] = []
    if not isinstance(rs.get("relations"), list):
        rs["relations"] = []
    if not isinstance(rs.get("constraints"), list):
        rs["constraints"] = []
    if not isinstance(rs.get("objective_links"), list):
        rs["objective_links"] = []

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
            and (r.get("subj") == entity_id or (isinstance((r.get("args") or {}), dict) and (r.get("args") or {}).get("entity_id") == entity_id))
        )
    ]


def attach_spatial_relational_state(record_path: str) -> Dict[str, Any]:
    """Attach AI_Brain 3D measurement mapped into a RelationalState.

    - If the record has no spatial asset path, returns status=skipped.
    - If measurement fails, returns status=error.
    - If measurement completes but ok=false, stores the measurement block and returns status=skipped.

    The updated relational_state is written back atomically.
    """
    # 1) Measure (bridge handles reading record + extracting spatial path)
    out = measure_ai_brain_for_record(record_path)
    status = out.get("status")
    if status != "completed":
        # Preserve the bridge contract.
        return {
            "record_path": record_path,
            "status": status or "error",
            "reason": out.get("reason") or out.get("error") or "measurement_not_completed",
        }

    measurement = out.get("measurement")
    if not isinstance(measurement, dict):
        return {"record_path": record_path, "status": "error", "reason": "missing measurement block"}

    # 2) Load record
    try:
        with open(record_path, "r", encoding="utf-8") as f:
            rec = json.load(f)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "failed to load record"}

    record_id = rec.get("id") if isinstance(rec, dict) else None
    if not isinstance(record_id, str) or not record_id:
        record_id = "unknown"

    # 3) Ensure relational_state container
    rs = _ensure_relational_state(rec)

    # Always store the raw measurement (even if ok=false) as evidence.
    rs["spatial_measurement"] = measurement

    # If measurement signals failure, do not attach derived entities/relations/constraints.
    if measurement.get("ok") is False:
        try:
            _atomic_write_json(record_path, rec)
            return {"record_path": record_path, "status": "skipped", "reason": "measurement_ok_false"}
        except Exception:
            return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    # 4) Build + merge entity/relations/constraints (idempotent for 3d source)
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

    # 5) Atomic persist
    try:
        _atomic_write_json(record_path, rec)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    return {"record_path": record_path, "status": "completed"}


def objects_to_entities(
    objects: list[Raw3DObject],
    context_id: str,
) -> dict[str, RelationalEntity]:
    """Map Raw3DObject items into RelationalEntity objects."""
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
    """Map Raw3DRelation items into RelationalLink objects."""
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
    """Construct a full RelationalState from 3D inputs."""
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
    """Update an existing RelationalState with new 3D inputs."""
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
