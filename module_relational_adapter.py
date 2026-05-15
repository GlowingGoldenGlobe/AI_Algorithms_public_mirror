import json
import re
import time
import logging
import hashlib
from copy import deepcopy
from typing import Any, Dict, List, Optional, TypedDict

from module_ai_brain_bridge import (
    measure_ai_brain_for_record,
    get_3d_limits,
    peek_cached_measurement,
    get_3d_determinism_config,
    normalize_composition_record_for_bridge,
    resolve_composition_export_measurement_candidate,
)
from module_composition_contracts import materialize_runtime_lineage_for_semantic_record
from module_storage import _atomic_write_json
from module_tools import canonical_json_bytes, _load_config
from module_spatial_snapshots import persist_spatial_snapshot
from module_spatial_telemetry import record_spatial_event


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


def _get_bridge_output_cap() -> int:
    cfg = _load_config() or {}
    block = cfg.get("retention_limits", {}) if isinstance(cfg, dict) else {}
    if not isinstance(block, dict):
        block = {}
    cap = block.get("max_bridge_outputs_per_record", 64)
    try:
        cap = int(cap)
    except Exception:
        cap = 64
    return max(0, cap)


def composition_bridge_payload_to_relational_rows(
    record_id: str,
    normalized_payload: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Extract adapter-ready entities, relations, and constraints from a bridge payload."""

    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(normalized_payload, dict):
        raise TypeError(f"Expected dict, got {type(normalized_payload).__name__}")

    if normalized_payload.get("source") != "3d_scene_summary":
        raise ValueError("normalized_payload source must be '3d_scene_summary'")

    def _normalized_rows(key: str) -> List[Dict[str, Any]]:
        rows = normalized_payload.get(key)
        if not isinstance(rows, list):
            return []
        normalized_rows: List[Dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                entry = deepcopy(row)
                entry.setdefault("record_id", record_id)
                entry.setdefault("source", "3d_scene_summary")
                normalized_rows.append(entry)
        return normalized_rows

    return {
        "entities": _normalized_rows("entities"),
        "relations": _normalized_rows("relations"),
        "constraints": _normalized_rows("constraints"),
    }


def _extract_explicit_spatial_path_from_record(rec: Dict[str, Any]) -> Optional[str]:
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


def _looks_like_geometry_export_path(path_value: Any) -> bool:
    if not isinstance(path_value, str) or not path_value.strip():
        return False
    return not path_value.strip().lower().endswith(".json")


def _extract_promoted_composition_export_path(rec: Dict[str, Any], rs: Dict[str, Any]) -> Optional[str]:
    artifacts = rec.get("artifacts") if isinstance(rec.get("artifacts"), dict) else {}

    composition_response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else None
    composition_scene_summary = artifacts.get("composition_scene_summary") if isinstance(artifacts.get("composition_scene_summary"), dict) else None
    if isinstance(composition_response, dict) and isinstance(composition_scene_summary, dict):
        try:
            candidate = resolve_composition_export_measurement_candidate(
                composition_response,
                composition_scene_summary,
            )
        except Exception:
            candidate = None
        if isinstance(candidate, dict):
            candidate_path = candidate.get("path")
            if isinstance(candidate_path, str) and candidate_path.strip():
                return candidate_path.strip()

    for key in ("composition_response", "response"):
        response = artifacts.get(key) if isinstance(artifacts.get(key), dict) else None
        if not isinstance(response, dict):
            continue
        response_artifacts = response.get("artifacts") if isinstance(response.get("artifacts"), list) else []
        for artifact in response_artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("kind") != "export_asset":
                continue
            path_value = artifact.get("path")
            if isinstance(path_value, str) and path_value.strip():
                return path_value.strip()

    for key in ("composition_scene_summary", "scene_manifest"):
        manifest = artifacts.get(key) if isinstance(artifacts.get(key), dict) else None
        if not isinstance(manifest, dict):
            continue
        exports = manifest.get("exports") if isinstance(manifest.get("exports"), list) else []
        for export in exports:
            if not isinstance(export, dict):
                continue
            path_value = export.get("path")
            if _looks_like_geometry_export_path(path_value):
                return str(path_value).strip()

    bridge_outputs = rs.get("bridge_outputs") if isinstance(rs.get("bridge_outputs"), list) else []
    for payload in bridge_outputs:
        if not isinstance(payload, dict) or payload.get("source") != "3d_scene_summary":
            continue
        extras = payload.get("extras") if isinstance(payload.get("extras"), dict) else {}
        evidence_refs = extras.get("evidence_refs") if isinstance(extras.get("evidence_refs"), list) else []
        for ref in evidence_refs:
            if _looks_like_geometry_export_path(ref):
                return str(ref).strip()

    return None


def _extract_spatial_path_from_record(rec: Dict[str, Any], rs: Optional[Dict[str, Any]] = None) -> Optional[str]:
    explicit_path = _extract_explicit_spatial_path_from_record(rec)
    if explicit_path:
        return explicit_path
    if isinstance(rs, dict):
        return _extract_promoted_composition_export_path(rec, rs)
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


def _log_spatial_event(
    *,
    record_id: Optional[str],
    cycle_id: str,
    record_path: str,
    status: str,
    reason: Optional[str] = None,
    measurement_out: Optional[Dict[str, Any]] = None,
    measurement_hash: Optional[str] = None,
    snapshot_result: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort logging of spatial measurement telemetry."""

    latency_ms = None
    cache_hit = None
    determinism = None
    if isinstance(measurement_out, dict):
        latency_val = measurement_out.get("latency_ms")
        if isinstance(latency_val, (int, float)):
            latency_ms = float(latency_val)
        if isinstance(measurement_out.get("cache_hit"), bool):
            cache_hit = bool(measurement_out.get("cache_hit"))
        det_block = measurement_out.get("determinism")
        if isinstance(det_block, dict):
            determinism = det_block

    snapshot_hash = None
    snapshot_path = None
    snapshot_written = None
    if isinstance(snapshot_result, dict):
        if isinstance(snapshot_result.get("hash"), str):
            snapshot_hash = snapshot_result.get("hash")
        if isinstance(snapshot_result.get("relative_path"), str):
            snapshot_path = snapshot_result.get("relative_path")
        if isinstance(snapshot_result.get("written"), bool):
            snapshot_written = snapshot_result.get("written")

    telemetry_extra: Dict[str, Any] = {}
    if isinstance(extra, dict):
        telemetry_extra.update(extra)
    if snapshot_written is not None:
        telemetry_extra.setdefault("snapshot_written", snapshot_written)
    if isinstance(snapshot_result, dict) and isinstance(snapshot_result.get("status"), str):
        telemetry_extra.setdefault("snapshot_status", snapshot_result.get("status"))
    if isinstance(measurement_out, dict) and isinstance(measurement_out.get("status"), str):
        telemetry_extra.setdefault("measurement_status", measurement_out.get("status"))

    try:
        record_spatial_event(
            record_id=record_id,
            cycle_id=cycle_id,
            record_path=record_path,
            event_type="spatial_measurement",
            status=status,
            reason=reason,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            measurement_hash=measurement_hash,
            snapshot_hash=snapshot_hash,
            snapshot_relative_path=snapshot_path,
            determinism=determinism,
            extra=telemetry_extra,
        )
    except Exception:
        logger.exception("Failed to record spatial telemetry for record %s", record_id)


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

    # Normalize list fields if corrupted.
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


def _normalize_categorized_terms(value: Any) -> List[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [item for item in value if isinstance(item, str)]
    else:
        return []

    normalized: List[str] = []
    seen: set[str] = set()
    for item in candidates:
        text = " ".join(str(item).strip().lower().replace("_", " ").replace("-", " ").split())
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _merge_unique_terms(*groups: Any) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()
    for group in groups:
        for term in _normalize_categorized_terms(group):
            if term in seen:
                continue
            seen.add(term)
            merged.append(term)
    return merged


def _collect_relation_families(rs: Dict[str, Any]) -> List[str]:
    relation_families: List[str] = []
    seen: set[str] = set()

    relations = rs.get("relations") if isinstance(rs.get("relations"), list) else []
    for row in relations:
        if not isinstance(row, dict):
            continue
        family = row.get("pred") if isinstance(row.get("pred"), str) else row.get("type")
        for term in _normalize_categorized_terms(family):
            if term in seen:
                continue
            seen.add(term)
            relation_families.append(term)

    constraints = rs.get("constraints") if isinstance(rs.get("constraints"), list) else []
    for row in constraints:
        if not isinstance(row, dict):
            continue
        for term in _normalize_categorized_terms(row.get("type")):
            if term in seen:
                continue
            seen.add(term)
            relation_families.append(term)

    return relation_families


def _has_3d_scene_summary_bridge(relational_state: Dict[str, Any]) -> bool:
    bridge_outputs = relational_state.get("bridge_outputs") if isinstance(relational_state.get("bridge_outputs"), list) else []
    if any(isinstance(payload, dict) and payload.get("source") == "3d_scene_summary" for payload in bridge_outputs):
        return True
    relations = relational_state.get("relations") if isinstance(relational_state.get("relations"), list) else []
    return any(isinstance(row, dict) and row.get("source") == "3d_scene_summary" for row in relations)


def _reference_profile_from_composition_sidecars(record: Dict[str, Any]) -> Dict[str, List[str]]:
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    scene = artifacts.get("composition_scene_summary") if isinstance(artifacts.get("composition_scene_summary"), dict) else {}
    if not scene:
        scene = artifacts.get("scene_manifest") if isinstance(artifacts.get("scene_manifest"), dict) else {}
    recipe = artifacts.get("composition_recipe") if isinstance(artifacts.get("composition_recipe"), dict) else {}
    if not recipe:
        recipe = artifacts.get("recipe_sidecar") if isinstance(artifacts.get("recipe_sidecar"), dict) else {}
    validation = (
        artifacts.get("composition_validation_summary")
        if isinstance(artifacts.get("composition_validation_summary"), dict)
        else {}
    )
    if not validation:
        validation = artifacts.get("validation_summary") if isinstance(artifacts.get("validation_summary"), dict) else {}

    labels = _merge_unique_terms(
        recipe.get("ordered_context_references"),
        scene.get("scene_id"),
        recipe.get("recipe_id"),
        validation.get("request_id"),
    )
    aliases = _merge_unique_terms(scene.get("scene_name"), scene.get("active_camera"), scene.get("active_lights"))
    object_inventory = scene.get("object_inventory") if isinstance(scene.get("object_inventory"), list) else []
    object_types = [row.get("type") for row in object_inventory if isinstance(row, dict)]
    materials = [row.get("material") for row in object_inventory if isinstance(row, dict)]
    steps = recipe.get("steps") if isinstance(recipe.get("steps"), list) else []
    step_actions = [row.get("action") for row in steps if isinstance(row, dict)]
    exports = scene.get("exports") if isinstance(scene.get("exports"), list) else []
    export_formats = [row.get("format") for row in exports if isinstance(row, dict)]
    comparison_axes = _merge_unique_terms(object_types, materials, step_actions, export_formats)

    if not (labels or aliases or comparison_axes):
        return {}
    return {
        "labels": labels,
        "aliases": aliases,
        "comparison_axes": comparison_axes,
    }


def _reference_profile_from_record(
    record: Dict[str, Any],
    relational_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[str]]:
    profile = record.get("reference_label_profile") if isinstance(record.get("reference_label_profile"), dict) else {}
    labels = _merge_unique_terms(profile.get("labels"))
    aliases = _merge_unique_terms(profile.get("aliases"))
    comparison_axes = _merge_unique_terms(profile.get("comparison_axes"))
    if not (labels or aliases or comparison_axes):
        rs = relational_state if isinstance(relational_state, dict) else record.get("relational_state")
        if isinstance(rs, dict):
            derived = rs.get("derived") if isinstance(rs.get("derived"), dict) else {}
            derived_profile = (
                derived.get("sidecar_reference_label_profile")
                if isinstance(derived.get("sidecar_reference_label_profile"), dict)
                else {}
            )
            labels = _merge_unique_terms(derived_profile.get("labels"))
            aliases = _merge_unique_terms(derived_profile.get("aliases"))
            comparison_axes = _merge_unique_terms(derived_profile.get("comparison_axes"))
            if not (labels or aliases or comparison_axes) and _has_3d_scene_summary_bridge(rs):
                sidecar_profile = _reference_profile_from_composition_sidecars(record)
                labels = _merge_unique_terms(sidecar_profile.get("labels"))
                aliases = _merge_unique_terms(sidecar_profile.get("aliases"))
                comparison_axes = _merge_unique_terms(sidecar_profile.get("comparison_axes"))
    if not (labels or aliases or comparison_axes):
        return {}
    return {
        "labels": labels,
        "aliases": aliases,
        "comparison_axes": comparison_axes,
    }


def _build_categorized_context_reference_join_fields(
    record: Dict[str, Any],
    summary: Dict[str, Any],
    relational_state: Dict[str, Any],
) -> Dict[str, Any]:
    reference_profile = _reference_profile_from_record(record, relational_state)
    reference_labels = list(reference_profile.get("labels") or [])
    reference_aliases = list(reference_profile.get("aliases") or [])
    reference_axes = list(reference_profile.get("comparison_axes") or [])
    reference_profile_present = bool(reference_labels or reference_aliases or reference_axes)

    reference_use_breakdown = {
        "label_match_count": 0,
        "alias_match_count": 0,
        "comparison_axis_match_count": 0,
    }
    reference_use_score = 0.0
    join_status = "semantic_only" if str(summary.get("support_level") or "missing") != "missing" else "missing"

    if reference_profile_present:
        try:
            from module_retrieval import (
                measure_reference_label_support,
                summarize_categorized_context_coverage,
                summarize_categorized_context_join_quality,
            )

            query = {
                "reference_labels": list(reference_labels) + list(reference_aliases),
                "comparison_axes": list(reference_axes),
            }
            retrieval_record = {
                "record_id": str(record.get("id") or ""),
                "value": record,
                "reference_label_profile": reference_profile,
            }
            coverage = summarize_categorized_context_coverage(retrieval_record, query)
            used = coverage.get("used") if isinstance(coverage.get("used"), dict) else {}
            reference_use_breakdown = {
                "label_match_count": len([item for item in (used.get("labels") or []) if isinstance(item, str)]),
                "alias_match_count": len([item for item in (used.get("aliases") or []) if isinstance(item, str)]),
                "comparison_axis_match_count": len(
                    [item for item in (used.get("comparison_axes") or []) if isinstance(item, str)]
                ),
            }
            reference_use_score = float(measure_reference_label_support(retrieval_record, query))
            join_quality = summarize_categorized_context_join_quality(summary, reference_profile)
            join_status = str(join_quality.get("join_status") or join_status)
        except Exception:
            join_status = (
                "aligned"
                if str(summary.get("support_level") or "missing") == "strong"
                else "reference_backed_semantic_weak"
                if str(summary.get("support_level") or "missing") == "weak"
                else "reference_only"
            )

    return {
        "reference_record_id": _extract_composition_request_id_from_record(record, relational_state),
        "reference_profile_present": reference_profile_present,
        "reference_labels": reference_labels,
        "reference_aliases": reference_aliases,
        "reference_comparison_axes": reference_axes,
        "reference_use_score": round(float(reference_use_score), 6),
        "reference_use_breakdown": reference_use_breakdown,
        "join_status": join_status,
    }


def summarize_record_categorized_context(
    record: Dict[str, Any],
    relational_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "labels": [],
            "aliases": [],
            "comparison_axes": [],
            "relation_families": [],
            "bridge_sources": [],
            "scene_summary_present": False,
            "support_level": "missing",
            "reference_record_id": None,
            "reference_profile_present": False,
            "reference_labels": [],
            "reference_aliases": [],
            "reference_comparison_axes": [],
            "reference_use_score": 0.0,
            "reference_use_breakdown": {
                "label_match_count": 0,
                "alias_match_count": 0,
                "comparison_axis_match_count": 0,
            },
            "join_status": "missing",
        }

    rs = relational_state if isinstance(relational_state, dict) else record.get("relational_state")
    if not isinstance(rs, dict):
        rs = {}

    labels = _merge_unique_terms(record.get("label"), record.get("labels"), record.get("category"))
    aliases = _merge_unique_terms(record.get("aliases"))
    comparison_axes = _merge_unique_terms(
        record.get("comparison_axes"),
        record.get("comparison_focus"),
        record.get("topics"),
        record.get("scope_tags"),
        record.get("tags"),
    )

    bridge_sources: List[str] = []
    bridge_outputs = rs.get("bridge_outputs") if isinstance(rs.get("bridge_outputs"), list) else []
    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        source = payload.get("source") if isinstance(payload.get("source"), str) else None
        if isinstance(source, str):
            for term in _normalize_categorized_terms(source):
                if term not in bridge_sources:
                    bridge_sources.append(term)
        extras = payload.get("extras") if isinstance(payload.get("extras"), dict) else {}
        comparison_axes = _merge_unique_terms(
            comparison_axes,
            extras.get("comparison_axes"),
            extras.get("comparison_focus"),
            extras.get("scope_tags"),
            extras.get("tags"),
        )

    relation_families = _collect_relation_families(rs)
    scene_summary_present = "3d scene summary" in bridge_sources or any(
        isinstance(row, dict) and row.get("source") == "3d_scene_summary"
        for row in (rs.get("relations") if isinstance(rs.get("relations"), list) else [])
    )

    semantic_signal_count = sum(
        1 for flag in (bool(labels), bool(comparison_axes), bool(relation_families), bool(scene_summary_present)) if flag
    )
    if semantic_signal_count >= 3 or (scene_summary_present and relation_families):
        support_level = "strong"
    elif semantic_signal_count > 0:
        support_level = "weak"
    else:
        support_level = "missing"

    summary = {
        "labels": labels,
        "aliases": aliases,
        "comparison_axes": comparison_axes,
        "relation_families": relation_families,
        "bridge_sources": bridge_sources,
        "scene_summary_present": scene_summary_present,
        "support_level": support_level,
    }
    derived = rs.get("derived") if isinstance(rs.get("derived"), dict) else {}
    sidecar_profile = (
        derived.get("sidecar_reference_label_profile")
        if isinstance(derived.get("sidecar_reference_label_profile"), dict)
        else {}
    )
    if sidecar_profile:
        summary["sidecar_reference_label_profile"] = {
            "labels": list(sidecar_profile.get("labels") or []),
            "aliases": list(sidecar_profile.get("aliases") or []),
            "comparison_axes": list(sidecar_profile.get("comparison_axes") or []),
            "source": str(sidecar_profile.get("source") or "validated_composition_sidecars"),
        }
    summary.update(_build_categorized_context_reference_join_fields(record, summary, rs))
    return summary


def _persist_categorized_context_summary(rec: Dict[str, Any], rs: Dict[str, Any]) -> None:
    derived = rs.get("derived")
    if not isinstance(derived, dict):
        derived = {}
        rs["derived"] = derived
    explicit_profile = rec.get("reference_label_profile") if isinstance(rec.get("reference_label_profile"), dict) else {}
    if not explicit_profile and _has_3d_scene_summary_bridge(rs):
        sidecar_profile = _reference_profile_from_composition_sidecars(rec)
        if sidecar_profile:
            derived["sidecar_reference_label_profile"] = {
                "labels": list(sidecar_profile.get("labels") or []),
                "aliases": list(sidecar_profile.get("aliases") or []),
                "comparison_axes": list(sidecar_profile.get("comparison_axes") or []),
                "source": "validated_composition_sidecars",
            }
    derived["categorized_context_summary"] = summarize_record_categorized_context(rec, rs)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
    normalized = _normalize_bounds(measurement.get("bounds"))
    if normalized is not None:
        return normalized
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


def _build_spatial_entity(record_id: str, measurement: Dict[str, Any]) -> Dict[str, Any]:
    entity_id = f"{record_id}::spatial_object"
    bounds = _derive_bounds_from_measurement(measurement)
    return {
        "id": entity_id,
        "type": "spatial_object",
        "attributes": {
            "units": measurement.get("units"),
            "count": measurement.get("count"),
            "centroid": measurement.get("centroid"),
            "bounds": bounds,
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
    units = measurement.get("units") if isinstance(measurement.get("units"), str) else None
    bounds = _derive_bounds_from_measurement(measurement)
    volume = _coerce_float(measurement.get("volume"))
    constraints: List[Dict[str, Any]] = []
    if bounds is not None:
        args: Dict[str, Any] = {"entity_id": entity_id, "bounds": bounds}
        if units:
            args["units"] = units
        constraints.append(
            {
                "type": "spatial",
                "args": args,
                "severity": "hard",
                "source": "3d",
            }
        )
    if volume is not None:
        args = {"entity_id": entity_id, "volume": volume}
        if units:
            args["units"] = units
        constraints.append(
            {
                "type": "spatial",
                "args": args,
                "severity": "soft",
                "source": "3d",
            }
        )
    return constraints


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
    cap = _get_bridge_output_cap()
    if cap > 0 and len(outputs) > cap:
        del outputs[:-cap]


def _extract_request_id_from_bridge_output(payload: Dict[str, Any]) -> Optional[str]:
    direct = payload.get("request_id") if isinstance(payload.get("request_id"), str) else None
    if direct:
        return direct

    extras = payload.get("extras") if isinstance(payload.get("extras"), dict) else {}
    validation = extras.get("validation") if isinstance(extras.get("validation"), dict) else {}
    nested = validation.get("request_id") if isinstance(validation.get("request_id"), str) else None
    if nested:
        return nested

    composition_request = extras.get("composition_request") if isinstance(extras.get("composition_request"), dict) else {}
    nested_direct = composition_request.get("request_id") if isinstance(composition_request.get("request_id"), str) else None
    if nested_direct:
        return nested_direct
    return None


def _extract_composition_request_id_from_record(rec: Dict[str, Any], rs: Dict[str, Any]) -> Optional[str]:
    artifacts = rec.get("artifacts") if isinstance(rec.get("artifacts"), dict) else {}
    composition_request = artifacts.get("composition_request") if isinstance(artifacts.get("composition_request"), dict) else {}
    composition_response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else {}
    composition_validation_summary = artifacts.get("composition_validation_summary") if isinstance(artifacts.get("composition_validation_summary"), dict) else {}
    validation_summary = artifacts.get("validation_summary") if isinstance(artifacts.get("validation_summary"), dict) else {}
    for request_id in (
        composition_request.get("request_id"),
        composition_response.get("request_id"),
        composition_validation_summary.get("request_id"),
        validation_summary.get("request_id"),
    ):
        if isinstance(request_id, str) and request_id:
            return request_id

    bridge_outputs = rs.get("bridge_outputs") if isinstance(rs.get("bridge_outputs"), list) else []
    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        request_id = _extract_request_id_from_bridge_output(payload)
        if isinstance(request_id, str) and request_id:
            return request_id
    return None


def _runtime_measurement_status(*, ready: bool, blocked_reason: Optional[str]) -> str:
    if ready:
        return "ready"
    if blocked_reason:
        return "blocked"
    return "pending"


def _build_runtime_measurement_readiness_summary(
    *,
    record_id: str,
    cycle_id: str,
    record_path: str,
    measurement: Dict[str, Any],
    bridge_outputs: List[Dict[str, Any]],
    snapshot_result: Optional[Dict[str, Any]],
    composition_request_id: Optional[str],
) -> Dict[str, Any]:
    measurement_recorded = bool(isinstance(measurement, dict) and measurement)
    measurement_ok = measurement_recorded and measurement.get("ok") is not False
    bridge_present = bool(bridge_outputs)
    snapshot_present = bool(
        isinstance(snapshot_result, dict)
        and snapshot_result.get("status") == "ok"
        and snapshot_result.get("relative_path")
    )
    request_id_present = bool(isinstance(composition_request_id, str) and composition_request_id)

    blocked_reason = None
    if not measurement_recorded:
        blocked_reason = "missing_measurement"
    elif not measurement_ok:
        blocked_reason = "measurement_not_ok"
    elif not bridge_present:
        blocked_reason = "missing_bridge_outputs"
    elif not snapshot_present:
        blocked_reason = "missing_snapshot"

    ready_for_commit = measurement_ok and bridge_present and snapshot_present
    return {
        "status": _runtime_measurement_status(ready=ready_for_commit, blocked_reason=blocked_reason),
        "record_id": record_id,
        "cycle_id": cycle_id,
        "record_path": record_path,
        "measurement_recorded": measurement_recorded,
        "measurement_ok": measurement_ok,
        "bridge_present": bridge_present,
        "bridge_output_count": len(bridge_outputs),
        "snapshot_present": snapshot_present,
        "request_id_present": request_id_present,
        "ready_for_commit": ready_for_commit,
        "blocked_reason": blocked_reason,
    }


def _build_runtime_measurement_commitment_summary(
    *,
    record_id: str,
    cycle_id: str,
    measurement_hash: Optional[str],
    snapshot_result: Optional[Dict[str, Any]],
    bridge_outputs: List[Dict[str, Any]],
    composition_request_id: Optional[str],
    readiness_summary: Dict[str, Any],
) -> Dict[str, Any]:
    commitment = {
        "status": "committed" if readiness_summary.get("ready_for_commit") else "not_committed",
        "record_id": record_id,
        "cycle_id": cycle_id,
        "request_id": composition_request_id if isinstance(composition_request_id, str) and composition_request_id else None,
        "measurement_hash": measurement_hash if isinstance(measurement_hash, str) and measurement_hash else None,
        "snapshot_hash": (
            snapshot_result.get("hash")
            if isinstance(snapshot_result, dict) and isinstance(snapshot_result.get("hash"), str)
            else None
        ),
        "snapshot_relative_path": (
            snapshot_result.get("relative_path")
            if isinstance(snapshot_result, dict) and isinstance(snapshot_result.get("relative_path"), str)
            else None
        ),
        "bridge_output_count": len(bridge_outputs),
        "bridge_request_ids": _unique_bridge_request_ids(bridge_outputs),
        "ready_for_commit": bool(readiness_summary.get("ready_for_commit")),
    }
    commitment["commitment_hash"] = hashlib.sha256(canonical_json_bytes(commitment)).hexdigest()
    return commitment


def _unique_bridge_request_ids(bridge_outputs: List[Dict[str, Any]]) -> List[str]:
    request_ids: List[str] = []
    seen: set[str] = set()
    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        request_id = _extract_request_id_from_bridge_output(payload)
        if not isinstance(request_id, str) or not request_id or request_id in seen:
            continue
        seen.add(request_id)
        request_ids.append(request_id)
    return request_ids


def _build_runtime_measurement_provenance_chain(
    *,
    measurement_out: Dict[str, Any],
    measurement_hash: Optional[str],
    snapshot_result: Optional[Dict[str, Any]],
    commitment_summary: Dict[str, Any],
    readiness_summary: Dict[str, Any],
) -> Dict[str, Any]:
    events = [
        {
            "stage": "measurement",
            "status": str(measurement_out.get("status") or "unknown"),
            "evidence_ref": measurement_hash if isinstance(measurement_hash, str) and measurement_hash else None,
        },
        {
            "stage": "bridge_outputs",
            "status": "attached" if readiness_summary.get("bridge_present") else "missing",
            "evidence_ref": commitment_summary.get("request_id") or None,
        },
        {
            "stage": "snapshot",
            "status": "persisted" if readiness_summary.get("snapshot_present") else "missing",
            "evidence_ref": (
                snapshot_result.get("relative_path")
                if isinstance(snapshot_result, dict) and isinstance(snapshot_result.get("relative_path"), str)
                else None
            ),
        },
        {
            "stage": "commitment",
            "status": str(commitment_summary.get("status") or "unknown"),
            "evidence_ref": commitment_summary.get("commitment_hash") or None,
        },
        {
            "stage": "telemetry",
            "status": "recorded",
            "evidence_ref": measurement_hash if isinstance(measurement_hash, str) and measurement_hash else None,
        },
    ]
    return {
        "status": "present",
        "chain_event_count": len(events),
        "events": events,
    }


def _replace_relational_rows_for_source(
    rows: List[Dict[str, Any]],
    new_rows: List[Dict[str, Any]],
    *,
    source: str,
    record_id: str,
) -> None:
    rows[:] = [
        existing
        for existing in rows
        if not (
            isinstance(existing, dict)
            and existing.get("source") == source
            and existing.get("record_id") == record_id
        )
    ]
    rows.extend(deepcopy(new_rows))


def _existing_bridge_outputs(rs: Dict[str, Any]) -> List[Dict[str, Any]]:
    bridge_outputs = rs.get("bridge_outputs") if isinstance(rs.get("bridge_outputs"), list) else []
    return [deepcopy(payload) for payload in bridge_outputs if isinstance(payload, dict)]


def _ensure_composition_bridge_outputs_from_sidecars(
    rec: Dict[str, Any],
    rs: Dict[str, Any],
    *,
    record_id: str,
    record_path: str,
    determinism_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    existing = _existing_bridge_outputs(rs)
    if any(payload.get("source") == "3d_scene_summary" for payload in existing):
        return existing

    try:
        normalized_payloads = normalize_composition_record_for_bridge(
            rec,
            determinism_config=determinism_config,
        )
    except Exception:
        logger.exception("Failed to normalize composition sidecars for record %s", record_id)
        return existing

    normalized_payloads = [deepcopy(payload) for payload in normalized_payloads if isinstance(payload, dict)]
    if not normalized_payloads:
        return existing

    entities = rs.get("entities")
    relations = rs.get("relations")
    constraints = rs.get("constraints")
    if not isinstance(entities, list) or not isinstance(relations, list) or not isinstance(constraints, list):
        return existing

    canonical_rows: Dict[str, List[Dict[str, Any]]] = {
        "entities": [],
        "relations": [],
        "constraints": [],
    }
    for payload in normalized_payloads:
        _persist_bridge_outputs(rs, payload, record_id=record_id, record_path=record_path)
        mapped = composition_bridge_payload_to_relational_rows(record_id, payload)
        for key in canonical_rows:
            canonical_rows[key].extend(mapped.get(key) or [])

    _replace_relational_rows_for_source(
        entities,
        canonical_rows["entities"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    _replace_relational_rows_for_source(
        relations,
        canonical_rows["relations"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    _replace_relational_rows_for_source(
        constraints,
        canonical_rows["constraints"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    return _existing_bridge_outputs(rs)


def attach_composition_bridge_outputs(record_path: str, *, runtime_output_root: Optional[str] = None) -> Dict[str, Any]:
    """Persist normalized composition sidecars into bridge outputs and canonical relational lists."""

    try:
        with open(record_path, "r", encoding="utf-8") as handle:
            rec = json.load(handle)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "failed to load record"}

    if not isinstance(rec, dict):
        return {"record_path": record_path, "status": "error", "reason": "record_not_object"}

    try:
        normalized_payloads = normalize_composition_record_for_bridge(
            rec,
            determinism_config=get_3d_determinism_config(),
        )
    except Exception as exc:
        return {
            "record_path": record_path,
            "status": "error",
            "reason": f"composition_bridge_normalization_failed: {exc}",
        }

    if not normalized_payloads:
        return {"record_path": record_path, "status": "skipped", "reason": "no composition sidecars in record"}

    record_id = rec.get("id") if isinstance(rec.get("id"), str) and rec.get("id") else "unknown"
    rs = _ensure_relational_state(rec)

    entities = rs.get("entities")
    relations = rs.get("relations")
    constraints = rs.get("constraints")
    if not isinstance(entities, list) or not isinstance(relations, list) or not isinstance(constraints, list):
        return {"record_path": record_path, "status": "error", "reason": "relational_state lists invalid"}

    canonical_rows: Dict[str, List[Dict[str, Any]]] = {
        "entities": [],
        "relations": [],
        "constraints": [],
    }
    try:
        for payload in normalized_payloads:
            _persist_bridge_outputs(rs, payload, record_id=record_id, record_path=record_path)
            mapped = composition_bridge_payload_to_relational_rows(record_id, payload)
            for key in canonical_rows:
                canonical_rows[key].extend(mapped.get(key) or [])
    except Exception as exc:
        return {
            "record_path": record_path,
            "status": "error",
            "reason": f"composition_bridge_mapping_failed: {exc}",
        }

    _replace_relational_rows_for_source(
        entities,
        canonical_rows["entities"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    _replace_relational_rows_for_source(
        relations,
        canonical_rows["relations"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    _replace_relational_rows_for_source(
        constraints,
        canonical_rows["constraints"],
        source="3d_scene_summary",
        record_id=record_id,
    )
    _persist_categorized_context_summary(rec, rs)

    try:
        _atomic_write_json(record_path, rec)
    except Exception:
        return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    lineage_result: Dict[str, Any]
    try:
        lineage_result = materialize_runtime_lineage_for_semantic_record(
            record_path,
            output_root=runtime_output_root,
        )
    except Exception as exc:
        lineage_result = {
            "record_path": record_path,
            "status": "error",
            "reason": f"lineage_materialization_failed: {exc}",
        }

    return {
        "record_path": record_path,
        "status": "completed",
        "bridge_output_count": len(normalized_payloads),
        "entity_count": len(canonical_rows["entities"]),
        "relation_count": len(canonical_rows["relations"]),
        "constraint_count": len(canonical_rows["constraints"]),
        "lineage_status": lineage_result.get("status"),
        "lineage_reason": lineage_result.get("reason"),
        "lineage_path": lineage_result.get("lineage_path"),
            "lineage_event_id": lineage_result.get("lineage_event_id"),
    }


def attach_spatial_relational_state(record_path: str) -> Dict[str, Any]:
    """Attach AI_Brain 3D measurement mapped into a RelationalState.

    - If the record has no spatial asset path, returns status=skipped.
    - If measurement fails, returns status=error.
    - If measurement completes but ok=false, stores the measurement block and returns status=skipped.

    The updated relational_state is written back atomically.
    """
    now = time.time()
    _prune_stale_cycle_counters(now)

    try:
        with open(record_path, "r", encoding="utf-8") as handle:
            rec = json.load(handle)
    except Exception:
        _log_spatial_event(
            record_id=None,
            cycle_id=_DEFAULT_CYCLE_ID,
            record_path=record_path,
            status="error",
            reason="failed_to_load_record",
            measurement_out=None,
            measurement_hash=None,
            snapshot_result=None,
            extra={"record_path": record_path},
        )
        return {"record_path": record_path, "status": "error", "reason": "failed to load record"}

    if not isinstance(rec, dict):
        _log_spatial_event(
            record_id=None,
            cycle_id=_DEFAULT_CYCLE_ID,
            record_path=record_path,
            status="error",
            reason="record_not_object",
            measurement_out=None,
            measurement_hash=None,
            snapshot_result=None,
        )
        return {"record_path": record_path, "status": "error", "reason": "record_not_object"}

    record_id = rec.get("id") if isinstance(rec.get("id"), str) and rec.get("id") else "unknown"
    cycle_id = _derive_cycle_identifier(rec, record_path)

    rs = _ensure_relational_state(rec)
    determinism_config = get_3d_determinism_config()
    _ensure_composition_bridge_outputs_from_sidecars(
        rec,
        rs,
        record_id=record_id,
        record_path=record_path,
        determinism_config=determinism_config,
    )
    spatial_path = _extract_spatial_path_from_record(rec, rs)
    if not spatial_path:
        _log_spatial_event(
            record_id=record_id,
            cycle_id=cycle_id,
            record_path=record_path,
            status="skipped",
            reason="no_spatial_asset_path",
            measurement_out=None,
            measurement_hash=None,
            snapshot_result=None,
        )
        return {"record_path": record_path, "status": "skipped", "reason": "no spatial asset path in record"}

    units = _extract_units_from_record(rec)
    limits = get_3d_limits()
    max_calls = limits.get("3d_max_calls_per_cycle", 0)

    measurement_out = peek_cached_measurement(
        spatial_path,
        units=units,
        determinism_config=determinism_config,
        limits=limits,
    )

    cycle_tracker: Optional[Dict[str, Any]] = None

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
                _log_spatial_event(
                    record_id=record_id,
                    cycle_id=cycle_id,
                    record_path=record_path,
                    status="skipped",
                    reason="3d_call_limit_reached",
                    measurement_out=None,
                    measurement_hash=None,
                    snapshot_result=None,
                    extra={"limit": max_calls},
                )
                return {
                    "record_path": record_path,
                    "status": "skipped",
                    "reason": "3d_call_limit_reached",
                    "cycle_id": cycle_id,
                    "limit": max_calls,
                }
            cycle_tracker["count"] = cycle_tracker.get("count", 0) + 1

        measurement_record = deepcopy(rec)
        if not _extract_explicit_spatial_path_from_record(measurement_record):
            measurement_record["spatial_asset_path"] = spatial_path

        measurement_out = measure_ai_brain_for_record(
            record_path,
            record=measurement_record,
            determinism_config=determinism_config,
            units=units,
        )

        if cycle_tracker is not None:
            cycle_tracker["last_seen"] = time.time()
            if measurement_out.get("cache_hit"):
                cycle_tracker["count"] = max(0, cycle_tracker.get("count", 0) - 1)

    status = measurement_out.get("status")
    if status != "completed":
        _log_spatial_event(
            record_id=record_id,
            cycle_id=cycle_id,
            record_path=record_path,
            status=status or "error",
            reason=measurement_out.get("reason") or measurement_out.get("error") or "measurement_not_completed",
            measurement_out=measurement_out,
            measurement_hash=None,
            snapshot_result=None,
        )
        return {
            "record_path": record_path,
            "status": status or "error",
            "reason": measurement_out.get("reason") or measurement_out.get("error") or "measurement_not_completed",
        }

    measurement = measurement_out.get("measurement")
    if not isinstance(measurement, dict):
        _log_spatial_event(
            record_id=record_id,
            cycle_id=cycle_id,
            record_path=record_path,
            status="error",
            reason="missing_measurement_block",
            measurement_out=measurement_out,
            measurement_hash=None,
            snapshot_result=None,
        )
        return {"record_path": record_path, "status": "error", "reason": "missing measurement block"}

    normalized_payloads = measurement_out.get("bridge_normalized")
    if isinstance(normalized_payloads, dict):
        normalized_payloads_iter = [deepcopy(normalized_payloads)]
    elif isinstance(normalized_payloads, list):
        normalized_payloads_iter = [deepcopy(payload) for payload in normalized_payloads if isinstance(payload, dict)]
    else:
        normalized_payloads_iter = []

    for payload in normalized_payloads_iter:
        _persist_bridge_outputs(rs, payload, record_id=record_id, record_path=record_path)

    if not normalized_payloads_iter:
        normalized_payloads_iter = _existing_bridge_outputs(rs)

    # Always store the raw measurement (even if ok=false) as evidence.
    rs["spatial_measurement"] = measurement

    if measurement.get("ok") is False:
        try:
            _atomic_write_json(record_path, rec)
            _log_spatial_event(
                record_id=record_id,
                cycle_id=cycle_id,
                record_path=record_path,
                status="skipped",
                reason="measurement_ok_false",
                measurement_out=measurement_out,
                measurement_hash=None,
                snapshot_result=None,
            )
            return {"record_path": record_path, "status": "skipped", "reason": "measurement_ok_false"}
        except Exception:
            _log_spatial_event(
                record_id=record_id,
                cycle_id=cycle_id,
                record_path=record_path,
                status="error",
                reason="atomic_write_failed",
                measurement_out=measurement_out,
                measurement_hash=None,
                snapshot_result=None,
            )
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

    snapshot_payload: Optional[Dict[str, Any]] = None
    measurement_timestamp: Optional[str] = None
    meta_block = measurement.get("meta") if isinstance(measurement.get("meta"), dict) else None
    if isinstance(meta_block, dict):
        ts_candidate = meta_block.get("timestamp")
        if isinstance(ts_candidate, str) and ts_candidate:
            measurement_timestamp = ts_candidate
    spatial_asset_path = measurement_out.get("path") if isinstance(measurement_out.get("path"), str) else None
    snapshot_payload = {
        "schema_version": "1.0",
        "record_id": record_id,
        "cycle_id": cycle_id,
        "record_path": record_path,
        "timestamp": measurement_timestamp,
        "spatial_asset": {
            "path": spatial_asset_path,
            "format": measurement_out.get("format") if isinstance(measurement_out.get("format"), str) else None,
            "point_count": measurement_out.get("points") if isinstance(measurement_out.get("points"), (int, float)) else None,
            "units": units,
        },
        "latency_ms": float(measurement_out.get("latency_ms")) if isinstance(measurement_out.get("latency_ms"), (int, float)) else None,
        "cache_hit": bool(measurement_out.get("cache_hit")),
        "determinism": deepcopy(measurement_out.get("determinism")) if isinstance(measurement_out.get("determinism"), dict) else {},
        "measurement": deepcopy(measurement),
        "measurement_hash": None,
        "bridge_normalized": deepcopy(normalized_payloads_iter),
    }

    composition_request_id = _extract_composition_request_id_from_record(rec, rs)
    if isinstance(composition_request_id, str) and composition_request_id:
        snapshot_payload["request_id"] = composition_request_id

    measurement_hash: Optional[str] = None
    try:
        measurement_hash = hashlib.sha256(canonical_json_bytes(measurement)).hexdigest()
    except Exception:
        measurement_hash = None
    snapshot_payload["measurement_hash"] = measurement_hash

    derived = rs.get("derived")
    if not isinstance(derived, dict):
        derived = {}
        rs["derived"] = derived

    if isinstance(measurement_hash, str) and measurement_hash:
        derived["spatial_measurement_hash"] = measurement_hash
    else:
        derived.pop("spatial_measurement_hash", None)

    if isinstance(composition_request_id, str) and composition_request_id:
        derived["composition_request_id"] = composition_request_id
    else:
        derived.pop("composition_request_id", None)

    schema_version = measurement.get("version")
    if isinstance(schema_version, str) and schema_version:
        derived["spatial_measurement_schema_version"] = schema_version
    else:
        derived.pop("spatial_measurement_schema_version", None)

    snapshot_result: Optional[Dict[str, Any]] = None
    try:
        snapshot_result = persist_spatial_snapshot(
            snapshot_payload,
            record_id=record_id,
            cycle_id=cycle_id,
            snapshot_label=measurement_timestamp or record_id,
        )
    except Exception:
        logger.exception("Failed to persist spatial snapshot for record %s", record_id)
        snapshot_result = None

    readiness_summary = _build_runtime_measurement_readiness_summary(
        record_id=record_id,
        cycle_id=cycle_id,
        record_path=record_path,
        measurement=measurement,
        bridge_outputs=normalized_payloads_iter,
        snapshot_result=snapshot_result,
        composition_request_id=composition_request_id,
    )
    commitment_summary = _build_runtime_measurement_commitment_summary(
        record_id=record_id,
        cycle_id=cycle_id,
        measurement_hash=measurement_hash,
        snapshot_result=snapshot_result,
        bridge_outputs=normalized_payloads_iter,
        composition_request_id=composition_request_id,
        readiness_summary=readiness_summary,
    )
    provenance_chain = _build_runtime_measurement_provenance_chain(
        measurement_out=measurement_out,
        measurement_hash=measurement_hash,
        snapshot_result=snapshot_result,
        commitment_summary=commitment_summary,
        readiness_summary=readiness_summary,
    )
    derived["runtime_measurement_readiness_summary"] = readiness_summary
    derived["runtime_measurement_commitment_summary"] = commitment_summary
    derived["runtime_measurement_provenance_chain"] = provenance_chain

    if isinstance(snapshot_result, dict) and snapshot_result.get("status") == "ok" and snapshot_result.get("relative_path"):
        artifacts = rec.get("artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
            rec["artifacts"] = artifacts
        spatial_artifacts = artifacts.get("spatial_snapshots")
        if not isinstance(spatial_artifacts, dict):
            spatial_artifacts = {}
            artifacts["spatial_snapshots"] = spatial_artifacts

        history = spatial_artifacts.get("history")
        if not isinstance(history, list):
            history = []

        entry = {
            "hash": snapshot_result.get("hash"),
            "relative_path": snapshot_result.get("relative_path"),
            "timestamp": measurement_timestamp,
            "cycle_id": cycle_id,
        }

        existing_hashes = {item.get("hash") for item in history if isinstance(item, dict)}
        if entry["hash"] and entry["hash"] not in existing_hashes:
            history.append(entry)
            history.sort(key=lambda item: (item.get("timestamp") or "", item.get("hash") or ""))

        spatial_artifacts["history"] = history
        spatial_artifacts["latest"] = entry
        if measurement_hash:
            spatial_artifacts["measurement_hash"] = measurement_hash
        if isinstance(composition_request_id, str) and composition_request_id:
            spatial_artifacts["request_id"] = composition_request_id
        spatial_artifacts["count"] = len(history)

    _persist_categorized_context_summary(rec, rs)

    # 5) Atomic persist
    try:
        _atomic_write_json(record_path, rec)
    except Exception:
        _log_spatial_event(
            record_id=record_id,
            cycle_id=cycle_id,
            record_path=record_path,
            status="error",
            reason="atomic_write_failed",
            measurement_out=measurement_out,
            measurement_hash=measurement_hash,
            snapshot_result=snapshot_result,
        )
        return {"record_path": record_path, "status": "error", "reason": "atomic_write_failed"}

    _log_spatial_event(
        record_id=record_id,
        cycle_id=cycle_id,
        record_path=record_path,
        status="completed",
        reason=None,
        measurement_out=measurement_out,
        measurement_hash=measurement_hash,
        snapshot_result=snapshot_result,
    )

    return {
        "record_path": record_path,
        "status": "completed",
        "runtime_measurement_readiness_summary": readiness_summary,
        "runtime_measurement_commitment_summary": commitment_summary,
        "runtime_measurement_provenance_chain": provenance_chain,
    }


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
