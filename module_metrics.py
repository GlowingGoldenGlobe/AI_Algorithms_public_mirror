"""module_metrics.py

Tiny, dependency-free metrics counters.

This module is intentionally small and deterministic. It keeps metrics in-memory
for lightweight observability during runs and tests.

Public API:
- incr_counter(name, amount=1)
- add_counter(name, amount)
- get_metrics()
- reset_metrics()
- flush_metrics(path=None, category='temporary', filename='metrics.json')
"""

from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

_METRICS: dict[str, float] = {}


def incr_counter(name: str, amount: float = 1.0) -> None:
    try:
        key = str(name)
    except Exception:
        return
    try:
        inc = float(amount)
    except Exception:
        inc = 1.0
    _METRICS[key] = float(_METRICS.get(key, 0.0) + inc)


def add_counter(name: str, amount: float) -> None:
    incr_counter(name, amount)


def get_metrics() -> Dict[str, Any]:
    return dict(_METRICS)


def reset_metrics() -> None:
    _METRICS.clear()


def flush_metrics(
    *,
    path: Optional[str] = None,
    category: str = "temporary",
    filename: str = "metrics.json",
) -> str:
    """Persist current metrics to disk and return the absolute path.

    - Default target: TemporaryQueue/metrics.json (via module_storage.resolve_path).
    - If `path` is provided, it is treated as a workspace-relative path and is
      validated with `safe_join`.
    - Writes deterministically (sorted keys). Includes determinism info when available.
    """
    try:
        from module_storage import ROOT as _ROOT, resolve_path
        from module_tools import safe_join, _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        deterministic_mode = bool(det.get("deterministic_mode"))
        fixed_timestamp = det.get("fixed_timestamp") if deterministic_mode else None

        if path is not None:
            target_path = safe_join(str(_ROOT), str(path))
        else:
            out_dir = resolve_path(str(category))
            os.makedirs(out_dir, exist_ok=True)
            target_path = safe_join(out_dir, str(filename))

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        mirror_cfg = cfg.get("mirror_tiers", {}) if isinstance(cfg, dict) else {}
        schedule_cfg = mirror_cfg.get("schedule_mirror") if isinstance(mirror_cfg, dict) else {}
        tier1_enabled = bool(isinstance(schedule_cfg, dict) and schedule_cfg.get("enabled"))
        tier2_enabled = bool(isinstance(schedule_cfg, dict) and schedule_cfg.get("tier2_enabled"))
        tier3_enabled = bool(isinstance(schedule_cfg, dict) and schedule_cfg.get("tier3_enabled"))
        if tier1_enabled and tier2_enabled and tier3_enabled:
            tiers_label = "tier 1 thru tier 3"
        elif tier1_enabled and tier2_enabled:
            tiers_label = "tier 1 thru tier 2"
        else:
            tiers_label = "tier 1"

        payload: Dict[str, Any] = {
            "schema_version": "1.0",
            "deterministic_mode": bool(deterministic_mode),
            "fixed_timestamp": str(fixed_timestamp) if fixed_timestamp else None,
            "tiers": tiers_label,
            "metrics": get_metrics(),
        }
        # Atomic write.
        tmp_path = target_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, target_path)
        return str(target_path)
    except Exception:
        return ""


def build_retained_storage_pressure_metrics(
    *,
    snapshot: Optional[Dict[str, Any]] = None,
    root_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Compose deterministic metric primitives from the retained-storage snapshot."""

    snapshot_payload = snapshot if isinstance(snapshot, dict) else None
    if not isinstance(snapshot_payload, dict):
        try:
            from module_storage import build_retained_storage_pressure_snapshot

            snapshot_payload = build_retained_storage_pressure_snapshot(root_path=root_path)
        except Exception:
            snapshot_payload = None

    if not isinstance(snapshot_payload, dict):
        return {"available": False, "metrics": {}, "reason": "retained_storage_snapshot_unavailable"}

    totals = snapshot_payload.get("totals") if isinstance(snapshot_payload.get("totals"), dict) else {}
    largest_root = (
        snapshot_payload.get("largest_root_by_bytes")
        if isinstance(snapshot_payload.get("largest_root_by_bytes"), dict)
        else None
    )

    metrics = {
        "retained_root_count": _to_int(totals.get("root_count", 0)),
        "retained_file_count": _to_int(totals.get("file_count", 0)),
        "retained_json_file_count": _to_int(totals.get("json_file_count", 0)),
        "retained_total_bytes": _to_int(totals.get("total_bytes", 0)),
        "candidate_partition_count": _to_int(snapshot_payload.get("candidate_partition_count", 0)),
        "storage_density_bytes_per_file": _round_float(snapshot_payload.get("storage_density_bytes_per_file", 0.0)),
        "candidate_partition_roots": [
            str(item) for item in (snapshot_payload.get("candidate_partition_roots") or []) if isinstance(item, str)
        ],
    }
    if largest_root:
        metrics["largest_root_by_bytes"] = {
            "root_id": str(largest_root.get("root_id") or ""),
            "total_bytes": _to_int(largest_root.get("total_bytes", 0)),
            "file_count": _to_int(largest_root.get("file_count", 0)),
        }

    metrics = {key: value for key, value in metrics.items() if value is not None}
    payload: Dict[str, Any] = {"available": True, "metrics": metrics}
    metrics_hash = _canonical_hash(metrics)
    if isinstance(metrics_hash, str) and metrics_hash:
        payload["metrics_hash"] = metrics_hash
    snapshot_hash = snapshot_payload.get("snapshot_hash")
    if isinstance(snapshot_hash, str) and snapshot_hash:
        payload["inputs_hash"] = snapshot_hash
    return payload


def _extract_graph_snapshot(relational_state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return the stored graph_snapshot dict if present and well-formed."""
    if not isinstance(relational_state, dict):
        return None
    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None
    snapshot = derived.get("graph_snapshot")
    if not isinstance(snapshot, dict):
        return None
    # Basic shape checks (nodes/edges lists) to avoid downstream errors.
    nodes = snapshot.get("nodes")
    edges = snapshot.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None
    return snapshot


def _build_relation_type_counts(edges: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for edge in edges:
        relation_type = edge.get("type")
        if not isinstance(relation_type, str):
            continue
        counts[relation_type] = counts.get(relation_type, 0) + 1
    return sorted(counts.items(), key=lambda item: item[0])


def _build_degree_table(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    degrees: Dict[str, Dict[str, int]] = {}
    for node in nodes:
        node_id = node.get("id")
        if isinstance(node_id, str):
            degrees[node_id] = {"in_degree": 0, "out_degree": 0}

    for edge in edges:
        src = edge.get("source")
        dst = edge.get("target")
        if isinstance(src, str) and src in degrees:
            degrees[src]["out_degree"] = degrees[src].get("out_degree", 0) + 1
        if isinstance(dst, str) and dst in degrees:
            degrees[dst]["in_degree"] = degrees[dst].get("in_degree", 0) + 1

    table: List[Dict[str, Any]] = []
    for node_id in sorted(degrees.keys()):
        entry = degrees[node_id]
        table.append(
            {
                "node_id": node_id,
                "in_degree": int(entry.get("in_degree", 0)),
                "out_degree": int(entry.get("out_degree", 0)),
                "total_degree": int(entry.get("in_degree", 0)) + int(entry.get("out_degree", 0)),
            }
        )
    return table


def _to_int(value: Any) -> int:
    try:
        if isinstance(value, bool):
            return int(value)
        return int(value)
    except Exception:
        return 0


def _round_float(value: float, places: int = 6) -> float:
    try:
        return round(float(value), places)
    except Exception:
        return 0.0


def _compute_density(edge_count: int, node_count: int) -> float:
    if node_count <= 1:
        return 0.0
    max_edges = node_count * (node_count - 1)
    if max_edges <= 0:
        return 0.0
    return _round_float(edge_count / max_edges)


def _select_top_nodes_by_degree(degree_table: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    rows: List[Tuple[str, int, int, int]] = []
    for entry in degree_table:
        if not isinstance(entry, dict):
            continue
        node_id = entry.get("node_id")
        if not isinstance(node_id, str):
            continue
        in_deg = _to_int(entry.get("in_degree", 0))
        out_deg = _to_int(entry.get("out_degree", 0))
        total = entry.get("total_degree")
        total_deg = _to_int(total) if total is not None else in_deg + out_deg
        rows.append((node_id, in_deg, out_deg, total_deg))

    rows.sort(key=lambda item: (-item[3], item[0]))
    top_rows: List[Dict[str, Any]] = []
    for node_id, in_deg, out_deg, total_deg in rows[: max(0, limit)]:
        top_rows.append(
            {
                "node_id": node_id,
                "in_degree": int(in_deg),
                "out_degree": int(out_deg),
                "total_degree": int(total_deg),
            }
        )
    return top_rows


def _calculate_relation_share(relation_types: List[Dict[str, Any]], total_edges: int) -> Optional[Dict[str, Any]]:
    if total_edges <= 0:
        return None
    best: Optional[Tuple[str, int]] = None
    for entry in relation_types:
        if not isinstance(entry, dict):
            continue
        relation_type = entry.get("relation_type")
        count_value = entry.get("edge_count")
        if not isinstance(relation_type, str):
            continue
        count = _to_int(count_value)
        if count <= 0:
            continue
        candidate = (relation_type, count)
        if best is None or count > best[1] or (count == best[1] and relation_type < best[0]):
            best = candidate
    if best is None:
        return None
    relation_type, count = best
    return {
        "relation_type": relation_type,
        "edge_count": int(count),
        "share": _round_float(count / total_edges),
    }


def build_graph_metric_inputs(relational_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Produce deterministic metric primitives from a stored GraphSnapshot.

    Returns a structure safe for metric composition consumers. When no snapshot is
    available, returns `{"available": False, "metrics": {}}`.
    """

    snapshot = _extract_graph_snapshot(relational_state)
    if snapshot is None:
        return {"available": False, "metrics": {}}

    nodes = snapshot.get("nodes") or []
    edges = snapshot.get("edges") or []
    build_info = snapshot.get("build_info") if isinstance(snapshot.get("build_info"), dict) else {}

    relation_counts = _build_relation_type_counts(edges if isinstance(edges, list) else [])
    degree_table = _build_degree_table(nodes if isinstance(nodes, list) else [], edges if isinstance(edges, list) else [])

    metrics: Dict[str, Any] = {
        "snapshot_hash": str(snapshot.get("snapshot_hash")) if snapshot.get("snapshot_hash") is not None else None,
        "tick_id": str(snapshot.get("tick_id")) if snapshot.get("tick_id") is not None else None,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "constraint_count": int(build_info.get("constraint_count", len(build_info.get("constraint_hashes", [])))) if isinstance(build_info, dict) else 0,
        "relation_types": [
            {"relation_type": relation_type, "edge_count": count}
            for relation_type, count in relation_counts
        ],
        "node_degrees": degree_table,
    }

    # Remove None values to keep serialization compact/deterministic.
    metrics = {k: v for k, v in metrics.items() if v is not None}

    metrics_hash = None
    try:
        from module_tools import canonical_json_bytes

        metrics_hash = hashlib.sha256(canonical_json_bytes(metrics)).hexdigest()
    except Exception:
        metrics_hash = None

    payload: Dict[str, Any] = {"available": True, "metrics": metrics}
    if metrics_hash:
        payload["metrics_hash"] = metrics_hash
    return payload


def build_composed_graph_metrics(
    relational_state: Optional[Dict[str, Any]],
    *,
    metrics_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compose higher-level graph metrics from stored primitives.

    Uses `build_graph_metric_inputs` when `metrics_payload` is not supplied. When
    no inputs are available, returns `{ "available": False, "metrics": {} }`.
    """

    base_payload = metrics_payload if isinstance(metrics_payload, dict) else build_graph_metric_inputs(relational_state)
    if not isinstance(base_payload, dict) or not base_payload.get("available"):
        return {"available": False, "metrics": {}}

    metrics_inputs = base_payload.get("metrics")
    if not isinstance(metrics_inputs, dict):
        return {"available": False, "metrics": {}}

    node_count = max(0, _to_int(metrics_inputs.get("node_count", 0)))
    edge_count = max(0, _to_int(metrics_inputs.get("edge_count", 0)))
    degree_table = metrics_inputs.get("node_degrees") if isinstance(metrics_inputs.get("node_degrees"), list) else []
    relation_types = metrics_inputs.get("relation_types") if isinstance(metrics_inputs.get("relation_types"), list) else []

    total_in = 0
    total_out = 0
    total_degree = 0
    for entry in degree_table:
        if not isinstance(entry, dict):
            continue
        total_in += _to_int(entry.get("in_degree", 0))
        total_out += _to_int(entry.get("out_degree", 0))
        total_degree += _to_int(entry.get("total_degree", 0))

    average_in = _round_float(total_in / node_count) if node_count else 0.0
    average_out = _round_float(total_out / node_count) if node_count else 0.0
    average_total = _round_float(total_degree / node_count) if node_count else 0.0
    density = _compute_density(edge_count, node_count)

    dominant_relation = _calculate_relation_share(relation_types, edge_count)
    top_nodes = _select_top_nodes_by_degree(degree_table)

    composed_metrics: Dict[str, Any] = {
        "source_snapshot_hash": metrics_inputs.get("snapshot_hash"),
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "average_total_degree": average_total,
        "average_in_degree": average_in,
        "average_out_degree": average_out,
        "top_nodes_by_total_degree": top_nodes,
    }
    if dominant_relation:
        composed_metrics["dominant_relation_type"] = dominant_relation

    # Remove None values while preserving deterministic ordering of lists/dicts.
    composed_metrics = {k: v for k, v in composed_metrics.items() if v is not None}

    try:
        from module_tools import canonical_json_bytes

        metrics_hash = hashlib.sha256(canonical_json_bytes(composed_metrics)).hexdigest()
    except Exception:
        metrics_hash = None

    payload: Dict[str, Any] = {"available": True, "metrics": composed_metrics}
    if metrics_hash:
        payload["metrics_hash"] = metrics_hash
    inputs_hash = base_payload.get("metrics_hash")
    if isinstance(inputs_hash, str) and inputs_hash:
        payload["inputs_hash"] = inputs_hash
    return payload


def _canonical_hash(payload: Any) -> Optional[str]:
    try:
        from module_tools import canonical_json_bytes

        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    except Exception:
        return None


def _load_metric_definitions(relational_state: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(relational_state, dict):
        return []
    definitions = relational_state.get("metrics_definitions")
    if isinstance(definitions, list):
        return [definition for definition in definitions if isinstance(definition, dict)]
    return []


def _lookup_path(data: Any, path: Sequence[Union[str, int]]) -> Any:
    current = data
    for component in path:
        if isinstance(current, dict) and isinstance(component, str):
            current = current.get(component)
        elif isinstance(current, list) and isinstance(component, int):
            if component < 0 or component >= len(current):
                return None
            current = current[component]
        else:
            return None
    return current


def _decimal_from_value(value: Any) -> Optional[Decimal]:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except Exception:
            return None
    return None


def _format_decimal(value: Decimal, precision: int) -> Tuple[str, float]:
    precision = max(0, int(precision))
    quant = Decimal(1).scaleb(-precision)
    quantized = value.quantize(quant, rounding=ROUND_HALF_UP)
    if precision > 0:
        string_value = format(quantized, f".{precision}f")
    else:
        string_value = format(quantized, "f")
    return string_value, float(quantized)


def _sanitize_definition_for_hash(definition: Dict[str, Any], *, supported_keys: Sequence[str]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key in supported_keys:
        value = definition.get(key)
        if value is not None:
            sanitized[key] = value
    return sanitized


def _collect_validation_issue(
    bucket: List[Dict[str, Any]],
    *,
    code: str,
    field: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    entry: Dict[str, Any] = {"code": str(code)}
    if field:
        entry["field"] = str(field)
    if message:
        entry["message"] = str(message)
    bucket.append(entry)


def _validate_precision_field(definition: Dict[str, Any], errors: List[Dict[str, Any]]) -> None:
    if "precision" not in definition:
        return
    precision_raw = definition.get("precision")
    try:
        precision_value = int(precision_raw)
        if precision_value < 0:
            raise ValueError("negative precision")
    except Exception:
        _collect_validation_issue(errors, code="invalid_precision", field="precision")


def _validate_scale_offset_fields(definition: Dict[str, Any], errors: List[Dict[str, Any]]) -> None:
    if "scale" in definition:
        if _decimal_from_value(definition.get("scale")) is None:
            _collect_validation_issue(errors, code="invalid_scale", field="scale")
    if "offset" in definition:
        if _decimal_from_value(definition.get("offset")) is None:
            _collect_validation_issue(errors, code="invalid_offset", field="offset")


def _normalize_metric_id(value: Any) -> str:
    if value is None:
        return ""
    try:
        candidate = str(value).strip()
    except Exception:
        return ""
    return candidate


def _normalize_readiness_level(value: Any, *, default: str = "missing") -> str:
    candidate = _normalize_metric_id(value).lower()
    return candidate or default


def build_learning_readiness_verdict(
    *,
    measurement_adequacy: Optional[Dict[str, Any]] = None,
    categorized_context: Optional[Dict[str, Any]] = None,
    comprehension_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compose a deterministic read-only learning readiness verdict.

    The gate is intentionally narrow: learning is considered ready only when the
    existing truth surfaces report strong measurement adequacy, strong
    categorized-context support, and strong comprehension review.
    """

    measurement_summary = measurement_adequacy if isinstance(measurement_adequacy, dict) else {}
    categorized_context_summary = categorized_context if isinstance(categorized_context, dict) else {}
    comprehension_summary = comprehension_review if isinstance(comprehension_review, dict) else {}

    measurement_level = _normalize_readiness_level(measurement_summary.get("level"), default="absent")
    categorized_context_level = _normalize_readiness_level(categorized_context_summary.get("level"), default="missing")
    comprehension_level = _normalize_readiness_level(comprehension_summary.get("level"), default="missing")

    observed_levels = {
        "measurement_adequacy": measurement_level,
        "categorized_context": categorized_context_level,
        "comprehension_review": comprehension_level,
    }

    unmet_conditions: List[str] = []
    if measurement_level != "strong":
        unmet_conditions.append("measurement_adequacy_strong")
    if categorized_context_level != "strong":
        unmet_conditions.append("categorized_context_strong")
    if comprehension_level != "strong":
        unmet_conditions.append("comprehension_review_strong")

    reasons = [
        f"measurement_adequacy={measurement_level}",
        f"categorized_context={categorized_context_level}",
        f"comprehension_review={comprehension_level}",
    ]

    ready = not unmet_conditions
    if ready:
        reason = (
            "learning readiness gate satisfied: measurement adequacy, categorized context, "
            "and comprehension review are all strong"
        )
    else:
        reason = "learning readiness gate blocked: " + ", ".join(unmet_conditions)

    return {
        "version": 1,
        "read_only": True,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "reason": reason,
        "reasons": reasons,
        "unmet_conditions": unmet_conditions,
        "evidence": {
            "measurement_adequacy": {
                "level": measurement_level,
                "reason": measurement_summary.get("reason") if isinstance(measurement_summary.get("reason"), str) else None,
            },
            "categorized_context": {
                "level": categorized_context_level,
                "counts": categorized_context_summary.get("counts") if isinstance(categorized_context_summary.get("counts"), dict) else {},
            },
            "comprehension_review": {
                "level": comprehension_level,
                "summary": comprehension_summary.get("summary") if isinstance(comprehension_summary.get("summary"), str) else None,
                "unresolved_gaps": list(comprehension_summary.get("unresolved_gaps") or []) if isinstance(comprehension_summary.get("unresolved_gaps"), list) else [],
                "supporting_evidence": (
                    dict(comprehension_summary.get("supporting_evidence"))
                    if isinstance(comprehension_summary.get("supporting_evidence"), dict)
                    else {}
                ),
            },
        },
        "observed_levels": observed_levels,
    }


def _build_learning_readiness_surface(readiness_verdict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    readiness = readiness_verdict if isinstance(readiness_verdict, dict) else {}
    return {
        "status": readiness.get("status") if isinstance(readiness.get("status"), str) else None,
        "ready": bool(readiness.get("ready")),
        "reason": readiness.get("reason") if isinstance(readiness.get("reason"), str) else None,
        "reasons": [str(item) for item in readiness.get("reasons") if isinstance(item, str)]
        if isinstance(readiness.get("reasons"), list)
        else [],
        "unmet_conditions": [str(item) for item in readiness.get("unmet_conditions") if isinstance(item, str)]
        if isinstance(readiness.get("unmet_conditions"), list)
        else [],
        "observed_levels": (
            dict(readiness.get("observed_levels"))
            if isinstance(readiness.get("observed_levels"), dict)
            else {}
        ),
    }


def build_learning_sandbox_activation_report(
    *,
    readiness_verdict: Optional[Dict[str, Any]] = None,
    sandbox_settings: Optional[Dict[str, Any]] = None,
    sandbox_name: str = "selection_migration",
) -> Dict[str, Any]:
    """Report whether the bounded retrieval-weighting sandbox is active or blocked."""

    settings = sandbox_settings if isinstance(sandbox_settings, dict) else {}
    sandbox_id = _normalize_metric_id(sandbox_name) or "selection_migration"

    enabled = bool(settings.get("enable"))
    use_retrieval_scores = bool(settings.get("use_retrieval_scores"))
    use_retrieval_components = bool(settings.get("use_retrieval_components"))

    try:
        retrieval_component_weight = float(settings.get("retrieval_component_weight", 0.0) or 0.0)
    except Exception:
        retrieval_component_weight = 0.0
    if retrieval_component_weight < 0.0:
        retrieval_component_weight = 0.0
    if retrieval_component_weight > 1.0:
        retrieval_component_weight = 1.0

    configured_paths: List[str] = []
    if use_retrieval_scores:
        configured_paths.append("retrieval_score")
    if use_retrieval_components:
        configured_paths.append("retrieval_components")

    path_metadata = {
        "retrieval_score": {
            "configured": use_retrieval_scores,
            "weight": 1.0 if use_retrieval_scores else 0.0,
        },
        "retrieval_components": {
            "configured": use_retrieval_components,
            "weight": float(retrieval_component_weight) if use_retrieval_components else 0.0,
            "weights_present": isinstance(settings.get("retrieval_component_weights"), dict),
        },
    }

    if not enabled:
        status = "disabled"
        active = False
        blocked_reason = "sandbox_disabled"
    elif not configured_paths:
        status = "blocked"
        active = False
        blocked_reason = "no_update_path_configured"
    elif not isinstance(readiness_verdict, dict):
        status = "blocked"
        active = False
        blocked_reason = "learning_readiness_verdict_unavailable"
    elif not bool(readiness_verdict.get("ready")):
        status = "blocked"
        active = False
        blocked_reason = "learning_readiness_not_ready"
    else:
        status = "active"
        active = True
        blocked_reason = None

    return {
        "version": 1,
        "sandbox": sandbox_id,
        "status": status,
        "active": active,
        "blocked_reason": blocked_reason,
        "configured_paths": configured_paths,
        "active_paths": list(configured_paths) if active else [],
        "read_only": True,
        "persistent_state": False,
        "mutable_weights": False,
        "readiness": _build_learning_readiness_surface(readiness_verdict),
        "config_snapshot": {
            "enable": enabled,
            "use_retrieval_scores": use_retrieval_scores,
            "use_retrieval_components": use_retrieval_components,
            "retrieval_component_weight": float(retrieval_component_weight),
        },
        "path_metadata": path_metadata,
    }


def build_policy_schedule_sandbox_activation_report(
    *,
    readiness_verdict: Optional[Dict[str, Any]] = None,
    sandbox_settings: Optional[Dict[str, Any]] = None,
    sandbox_name: str = "policy_schedule_priority",
) -> Dict[str, Any]:
    """Report whether the bounded schedule-priority sandbox is active or blocked."""

    settings = sandbox_settings if isinstance(sandbox_settings, dict) else {}
    sandbox_id = _normalize_metric_id(sandbox_name) or "policy_schedule_priority"

    enabled = bool(settings.get("enable"))
    mode = _normalize_metric_id(settings.get("mode") or "learning_readiness_gated") or "learning_readiness_gated"
    preserve_baseline_when_blocked = bool(settings.get("preserve_baseline_when_blocked", True))
    allow_priority_updates = bool(settings.get("allow_priority_updates"))
    allow_toggle_policy = bool(settings.get("allow_toggle_policy"))

    priority_levels = settings.get("priority_levels") if isinstance(settings.get("priority_levels"), list) else []
    normalized_priority_levels = [
        str(item) for item in priority_levels if isinstance(item, str) and str(item).strip()
    ]
    normalized_priority_levels = sorted(set(normalized_priority_levels))

    policy_activation = settings.get("policy_activation") if isinstance(settings.get("policy_activation"), dict) else {}
    configured_paths: List[str] = []
    if allow_priority_updates:
        configured_paths.append("schedule_priority")
    if allow_toggle_policy:
        configured_paths.append("toggle_policy")

    path_metadata = {
        "schedule_priority": {
            "configured": allow_priority_updates,
            "priority_levels": normalized_priority_levels,
        },
        "toggle_policy": {
            "configured": allow_toggle_policy,
            "policy_activation_present": bool(policy_activation),
            "policy_activation_keys": sorted(str(key) for key in policy_activation.keys()),
        },
    }

    if not enabled:
        status = "disabled"
        active = False
        blocked_reason = "sandbox_disabled"
    elif not configured_paths:
        status = "blocked"
        active = False
        blocked_reason = "no_update_path_configured"
    elif not isinstance(readiness_verdict, dict):
        status = "blocked"
        active = False
        blocked_reason = "learning_readiness_verdict_unavailable"
    elif not bool(readiness_verdict.get("ready")):
        status = "blocked"
        active = False
        blocked_reason = "learning_readiness_not_ready"
    else:
        status = "active"
        active = True
        blocked_reason = None

    return {
        "version": 1,
        "sandbox": sandbox_id,
        "status": status,
        "active": active,
        "blocked_reason": blocked_reason,
        "configured_paths": configured_paths,
        "active_paths": list(configured_paths) if active else [],
        "read_only": True,
        "persistent_state": False,
        "hidden_policy_mutation": False,
        "readiness": _build_learning_readiness_surface(readiness_verdict),
        "config_snapshot": {
            "enable": enabled,
            "mode": mode,
            "preserve_baseline_when_blocked": preserve_baseline_when_blocked,
            "allow_priority_updates": allow_priority_updates,
            "allow_toggle_policy": allow_toggle_policy,
        },
        "path_metadata": path_metadata,
    }


def _validate_aggregate_definition_shape(
    definition: Dict[str, Any],
    *,
    metric_id: str,
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> None:
    entries_raw = definition.get("metrics")
    if not isinstance(entries_raw, list):
        entries_raw = definition.get("terms")
    if not isinstance(entries_raw, list) or not entries_raw:
        _collect_validation_issue(errors, code="missing_metrics", field="metrics")
    else:
        for entry in entries_raw:
            if isinstance(entry, str):
                ref_id = _normalize_metric_id(entry)
                if not ref_id:
                    _collect_validation_issue(errors, code="missing_metric_reference", field="metrics")
                    continue
                if metric_id and ref_id == metric_id:
                    _collect_validation_issue(errors, code="circular_reference", field="metrics")
            elif isinstance(entry, dict):
                ref_candidate = entry.get("metric") or entry.get("metric_id") or entry.get("source_metric")
                ref_id = _normalize_metric_id(ref_candidate)
                if not ref_id:
                    _collect_validation_issue(errors, code="missing_metric_reference", field="metrics")
                elif metric_id and ref_id == metric_id:
                    _collect_validation_issue(errors, code="circular_reference", field="metrics")

                if "default" in entry and _decimal_from_value(entry.get("default")) is None:
                    _collect_validation_issue(errors, code="invalid_default", field="metrics")
            else:
                _collect_validation_issue(errors, code="invalid_metric_entry", field="metrics")

    operator_raw = _normalize_metric_id(definition.get("operator") or "mean").lower()
    if not operator_raw:
        operator_raw = "mean"
    operator_mode = _AGGREGATE_OPERATORS.get(operator_raw)
    if not operator_mode:
        _collect_validation_issue(errors, code="unsupported_operator", field="operator")

    _validate_scale_offset_fields(definition, errors)
    _validate_precision_field(definition, errors)


def _validate_ratio_definition_shape(
    definition: Dict[str, Any],
    *,
    metric_id: str,
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> None:
    numerator_ref = _normalize_metric_id(
        definition.get("numerator")
        or definition.get("numerator_metric")
        or definition.get("numerator_source")
    )
    denominator_ref = _normalize_metric_id(
        definition.get("denominator")
        or definition.get("denominator_metric")
        or definition.get("denominator_source")
    )

    if not numerator_ref:
        _collect_validation_issue(errors, code="missing_numerator_metric", field="numerator")
    if not denominator_ref:
        _collect_validation_issue(errors, code="missing_denominator_metric", field="denominator")
    if metric_id and (numerator_ref == metric_id or denominator_ref == metric_id):
        _collect_validation_issue(errors, code="circular_reference", field="metric_id")

    if "numerator_default" in definition and _decimal_from_value(definition.get("numerator_default")) is None:
        _collect_validation_issue(errors, code="invalid_numerator_default", field="numerator_default")
    if "default_numerator" in definition and _decimal_from_value(definition.get("default_numerator")) is None:
        _collect_validation_issue(errors, code="invalid_numerator_default", field="default_numerator")

    if "denominator_default" in definition and _decimal_from_value(definition.get("denominator_default")) is None:
        _collect_validation_issue(errors, code="invalid_denominator_default", field="denominator_default")
    if "default_denominator" in definition and _decimal_from_value(definition.get("default_denominator")) is None:
        _collect_validation_issue(errors, code="invalid_denominator_default", field="default_denominator")

    tolerance_candidate = definition.get("tolerance") or definition.get("denominator_tolerance")
    if tolerance_candidate is not None:
        tolerance_decimal = _decimal_from_value(tolerance_candidate)
        if tolerance_decimal is None:
            _collect_validation_issue(errors, code="invalid_tolerance", field="tolerance")
        elif tolerance_decimal < Decimal(0):
            _collect_validation_issue(errors, code="negative_tolerance", field="tolerance")

    if "fallback_value" in definition and _decimal_from_value(definition.get("fallback_value")) is None:
        _collect_validation_issue(errors, code="invalid_fallback", field="fallback_value")
    if "zero_fallback" in definition and _decimal_from_value(definition.get("zero_fallback")) is None:
        _collect_validation_issue(errors, code="invalid_fallback", field="zero_fallback")

    _validate_scale_offset_fields(definition, errors)
    _validate_precision_field(definition, errors)


def _validate_custom_definition_shape(
    definition: Dict[str, Any],
    *,
    metric_id: str,
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> None:
    mode_raw = definition.get("mode") or definition.get("function") or "validation"
    mode = _normalize_metric_id(mode_raw).lower() or "validation"

    if mode == "constant":
        if _decimal_from_value(
            definition.get("value")
            or definition.get("constant")
            or definition.get("constant_value")
            or definition.get("value_numeric")
        ) is None:
            _collect_validation_issue(errors, code="missing_constant_value", field="value")
        _validate_scale_offset_fields(definition, errors)
        _validate_precision_field(definition, errors)
        return

    validation_block = definition.get("validation")
    if validation_block is None:
        validation_block = {}
    if not isinstance(validation_block, dict):
        _collect_validation_issue(errors, code="invalid_validation_block", field="validation")
        validation_block = {}

    required_inputs = validation_block.get("required_inputs")
    if required_inputs is not None:
        if not isinstance(required_inputs, list):
            _collect_validation_issue(errors, code="invalid_required_inputs", field="validation.required_inputs")
        else:
            for item in required_inputs:
                candidate = _normalize_metric_id(item)
                if not candidate:
                    _collect_validation_issue(errors, code="invalid_required_input", field="validation.required_inputs")
                elif metric_id and candidate == metric_id:
                    _collect_validation_issue(errors, code="circular_reference", field="validation.required_inputs")

    tolerance_default = validation_block.get("tolerance")
    if tolerance_default is not None:
        tolerance_decimal = _decimal_from_value(tolerance_default)
        if tolerance_decimal is None:
            _collect_validation_issue(errors, code="invalid_tolerance", field="validation.tolerance")
        elif tolerance_decimal < Decimal(0):
            _collect_validation_issue(errors, code="negative_tolerance", field="validation.tolerance")

    checks = definition.get("checks")
    if not isinstance(checks, list) or not checks:
        _collect_validation_issue(errors, code="missing_checks", field="checks")
        return

    for check in checks:
        if not isinstance(check, dict):
            _collect_validation_issue(errors, code="invalid_check", field="checks")
            continue
        ref_candidate = check.get("metric") or check.get("metric_id")
        ref_id = _normalize_metric_id(ref_candidate)
        if not ref_id:
            _collect_validation_issue(errors, code="missing_metric_reference", field="checks")
        elif metric_id and ref_id == metric_id:
            _collect_validation_issue(errors, code="circular_reference", field="checks")

        comparator = _normalize_metric_id(check.get("comparison") or ">=")
        if comparator not in _COMPARISON_OPERATORS:
            _collect_validation_issue(errors, code="unsupported_comparison", field="checks")

        if _decimal_from_value(check.get("value")) is None:
            _collect_validation_issue(errors, code="invalid_threshold", field="checks")

        if "tolerance" in check:
            tolerance_decimal = _decimal_from_value(check.get("tolerance"))
            if tolerance_decimal is None:
                _collect_validation_issue(errors, code="invalid_tolerance", field="checks")
            elif tolerance_decimal < Decimal(0):
                _collect_validation_issue(errors, code="negative_tolerance", field="checks")


_VALIDATION_HASH_KEYS: Dict[str, Tuple[str, ...]] = {
    "aggregate": (
        "metric_id",
        "version",
        "type",
        "metrics",
        "terms",
        "operator",
        "precision",
        "scale",
        "offset",
    ),
    "ratio": (
        "metric_id",
        "version",
        "type",
        "numerator",
        "numerator_metric",
        "denominator",
        "denominator_metric",
        "numerator_default",
        "denominator_default",
        "tolerance",
        "fallback_value",
        "precision",
        "scale",
        "offset",
    ),
    "custom": (
        "metric_id",
        "version",
        "type",
        "mode",
        "function",
        "checks",
        "validation",
        "value",
        "precision",
        "scale",
        "offset",
    ),
}


def validate_metric_definition(definition: Any) -> Dict[str, Any]:
    if not isinstance(definition, dict):
        errors: List[Dict[str, Any]] = []
        _collect_validation_issue(errors, code="invalid_definition", message="definition must be a dict")
        return {
            "metric_id": "",
            "definition_type": "",
            "valid": False,
            "errors": errors,
            "warnings": [],
            "definition_hash": None,
        }

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    metric_id = _normalize_metric_id(definition.get("metric_id"))
    if not metric_id:
        _collect_validation_issue(errors, code="missing_metric_id", field="metric_id")

    definition_type = _normalize_metric_id(definition.get("type"))

    dispatch = {
        "aggregate": _validate_aggregate_definition_shape,
        "ratio": _validate_ratio_definition_shape,
        "custom": _validate_custom_definition_shape,
    }

    validator = dispatch.get(definition_type)
    if validator is not None:
        validator(definition, metric_id=metric_id, errors=errors, warnings=warnings)

    hash_keys = _VALIDATION_HASH_KEYS.get(definition_type)
    if hash_keys:
        definition_hash = _canonical_hash(_sanitize_definition_for_hash(definition, supported_keys=hash_keys))
    else:
        definition_hash = _canonical_hash(_sanitize_definition_for_hash(definition, supported_keys=("metric_id", "version", "type")))

    return {
        "metric_id": metric_id,
        "definition_type": definition_type,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "definition_hash": definition_hash,
    }


def validate_metric_definitions(definitions: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    definitions_list = definitions if isinstance(definitions, list) else []
    results: List[Dict[str, Any]] = []
    all_valid = True

    for definition in definitions_list:
        validation = validate_metric_definition(definition)
        results.append(validation)
        if not validation.get("valid", False):
            all_valid = False

    return {
        "valid": all_valid,
        "definition_count": len(results),
        "results": results,
    }


def _evaluate_graph_metric_definition(
    definition: Dict[str, Any],
    composed_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "source",
                "path",
                "scale",
                "offset",
                "precision",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    if not isinstance(composed_payload, dict) or not composed_payload.get("available"):
        result["reason"] = "graph_metrics_composed_unavailable"
        return result

    metrics_body = composed_payload.get("metrics")
    if not isinstance(metrics_body, dict):
        result["reason"] = "graph_metrics_body_missing"
        return result

    path_value = definition.get("path")
    if isinstance(path_value, list):
        path: List[Union[str, int]] = []
        for component in path_value:
            if isinstance(component, int):
                path.append(component)
            elif isinstance(component, str):
                path.append(component)
            else:
                result["reason"] = "invalid_path_component"
                return result
    else:
        result["reason"] = "missing_path"
        return result

    extracted = _lookup_path(metrics_body, path)
    extracted_decimal = _decimal_from_value(extracted)
    if extracted_decimal is None:
        result["reason"] = "non_numeric_value"
        result["path"] = path
        return result

    scale_decimal = _decimal_from_value(definition.get("scale", 1)) or Decimal(1)
    offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
    precision = definition.get("precision", 6)
    try:
        precision_int = int(precision)
    except Exception:
        precision_int = 6

    calculated = (extracted_decimal * scale_decimal) + offset_decimal
    value_string, value_float = _format_decimal(calculated, precision_int)

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_float,
            "path": path,
            "precision": precision_int,
            "scale": float(scale_decimal),
            "offset": float(offset_decimal),
            "source": "graph_metrics_composed",
        }
    )

    inputs_hash = composed_payload.get("metrics_hash")
    if isinstance(inputs_hash, str) and inputs_hash:
        result["inputs_hash"] = inputs_hash

    return result


def _normalize_precision(value: Any, default: int = 6) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return max(0, int(default))


def _resolve_metric_reference(
    metric_id: str,
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    metric_id_str = str(metric_id)
    payload: Optional[Dict[str, Any]] = None

    if metric_id_str in results_so_far:
        candidate = results_so_far.get(metric_id_str)
        if isinstance(candidate, dict):
            payload = candidate
    if payload is None and isinstance(relational_state, dict):
        metrics_store = relational_state.get("metrics")
        if isinstance(metrics_store, dict):
            candidate = metrics_store.get(metric_id_str)
            if isinstance(candidate, dict):
                payload = candidate

    if payload is None:
        return None

    value_decimal = None
    if "value_numeric" in payload:
        value_decimal = _decimal_from_value(payload.get("value_numeric"))
    if value_decimal is None and "value" in payload:
        value_decimal = _decimal_from_value(payload.get("value"))
    if value_decimal is None:
        return None

    descriptor = {
        "metric_id": metric_id_str,
        "payload": dict(payload),
        "value": value_decimal,
    }

    inputs_hash = payload.get("inputs_hash") or payload.get("definition_hash")
    descriptor["inputs_hash"] = inputs_hash
    return descriptor


def _evaluate_identity_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "source_metric",
                "scale",
                "offset",
                "precision",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    source_metric = definition.get("source_metric") or definition.get("metric")
    source_metric_id = str(source_metric) if source_metric is not None else ""
    if not source_metric_id:
        result["reason"] = "missing_source_metric"
        return result

    if source_metric_id == metric_id:
        result["reason"] = "circular_reference"
        return result

    reference = _resolve_metric_reference(
        source_metric_id,
        relational_state=relational_state,
        results_so_far=results_so_far,
    )
    if reference is None:
        result["reason"] = "source_metric_unavailable"
        return result

    scale_decimal = _decimal_from_value(definition.get("scale", 1)) or Decimal(1)
    offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
    precision_int = _normalize_precision(definition.get("precision", 6))

    transformed = (reference["value"] * scale_decimal) + offset_decimal
    value_string, value_float = _format_decimal(transformed, precision_int)

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_float,
            "precision": precision_int,
            "scale": float(scale_decimal),
            "offset": float(offset_decimal),
            "source": "identity",
            "source_metric": source_metric_id,
        }
    )

    descriptor = {
        "metric_id": source_metric_id,
        "value": float(reference["value"]),
        "scale": float(scale_decimal),
        "offset": float(offset_decimal),
    }
    if reference.get("inputs_hash"):
        descriptor["inputs_hash"] = reference["inputs_hash"]
    inputs_hash = _canonical_hash({"identity": descriptor})
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    return result


def _evaluate_weighted_sum_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "terms",
                "offset",
                "precision",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    terms = definition.get("terms")
    if not isinstance(terms, list) or not terms:
        result["reason"] = "missing_terms"
        return result

    total = Decimal(0)
    descriptor_terms: List[Dict[str, Any]] = []

    for term in terms:
        if not isinstance(term, dict):
            result["reason"] = "invalid_term"
            return result
        ref = term.get("metric") or term.get("metric_id")
        ref_id = str(ref) if ref is not None else ""
        if not ref_id:
            result["reason"] = "missing_metric_reference"
            return result
        if ref_id == metric_id:
            result["reason"] = "circular_reference"
            return result

        weight_decimal = _decimal_from_value(term.get("weight", 1))
        if weight_decimal is None:
            result["reason"] = "invalid_weight"
            return result

        reference = _resolve_metric_reference(
            ref_id,
            relational_state=relational_state,
            results_so_far=results_so_far,
        )
        if reference is None:
            if "default" in term:
                default_decimal = _decimal_from_value(term.get("default"))
                if default_decimal is None:
                    result["reason"] = "invalid_default"
                    return result
                value_decimal = default_decimal
                reference_inputs_hash = None
            else:
                result["reason"] = "metric_unavailable"
                result["missing_metric"] = ref_id
                return result
        else:
            value_decimal = reference["value"]
            reference_inputs_hash = reference.get("inputs_hash")

        contribution = value_decimal * weight_decimal
        total += contribution

        descriptor: Dict[str, Any] = {
            "metric": ref_id,
            "weight": float(weight_decimal),
            "value": float(value_decimal),
        }
        if reference_inputs_hash:
            descriptor["inputs_hash"] = reference_inputs_hash
        descriptor_terms.append(descriptor)

    offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
    precision_int = _normalize_precision(definition.get("precision", 6))

    calculated = total + offset_decimal
    value_string, value_float = _format_decimal(calculated, precision_int)

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_float,
            "precision": precision_int,
            "offset": float(offset_decimal),
            "source": "weighted_sum",
        }
    )

    inputs_hash = _canonical_hash({"terms": descriptor_terms, "offset": float(offset_decimal)})
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    result["dependencies"] = [term.get("metric") or term.get("metric_id") for term in terms if isinstance(term, dict)]
    return result


_AGGREGATE_OPERATORS = {
    "sum": "sum",
    "total": "sum",
    "mean": "mean",
    "average": "mean",
    "avg": "mean",
    "min": "min",
    "max": "max",
}


def _evaluate_aggregate_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "metrics",
                "terms",
                "operator",
                "precision",
                "scale",
                "offset",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    entries_raw = definition.get("metrics")
    if not isinstance(entries_raw, list):
        entries_raw = definition.get("terms")
    if not isinstance(entries_raw, list) or not entries_raw:
        result["reason"] = "missing_metrics"
        return result

    operator_key = str(definition.get("operator", "mean")).strip().lower()
    operator_mode = _AGGREGATE_OPERATORS.get(operator_key)
    if not operator_mode:
        result["reason"] = "unsupported_operator"
        return result

    values: List[Decimal] = []
    descriptor_entries: List[Dict[str, Any]] = []
    dependencies: List[str] = []

    for entry in entries_raw:
        if isinstance(entry, str):
            ref_id = entry
            default_value = None
        elif isinstance(entry, dict):
            ref_candidate = entry.get("metric") or entry.get("metric_id") or entry.get("source_metric")
            ref_id = str(ref_candidate) if ref_candidate is not None else ""
            default_value = _decimal_from_value(entry.get("default")) if "default" in entry else None
        else:
            result["reason"] = "invalid_metric_entry"
            return result

        ref_id = str(ref_id)
        if not ref_id:
            result["reason"] = "missing_metric_reference"
            return result

        if ref_id == metric_id:
            result["reason"] = "circular_reference"
            return result

        reference = _resolve_metric_reference(
            ref_id,
            relational_state=relational_state,
            results_so_far=results_so_far,
        )

        if reference is None:
            if default_value is None:
                result["reason"] = "metric_unavailable"
                result["missing_metric"] = ref_id
                return result
            value_decimal = default_value
            inputs_hash = None
            source_kind = "default"
        else:
            value_decimal = reference["value"]
            inputs_hash = reference.get("inputs_hash")
            source_kind = "metric"

        values.append(value_decimal)
        dependencies.append(ref_id)
        entry_descriptor: Dict[str, Any] = {
            "metric": ref_id,
            "value": float(value_decimal),
            "source": source_kind,
        }
        if inputs_hash:
            entry_descriptor["inputs_hash"] = inputs_hash
        descriptor_entries.append(entry_descriptor)

    if not values:
        result["reason"] = "no_values"
        return result

    aggregate_value: Optional[Decimal]
    if operator_mode == "sum":
        total = Decimal(0)
        for val in values:
            total += val
        aggregate_value = total
    elif operator_mode == "mean":
        total = Decimal(0)
        for val in values:
            total += val
        count = len(values)
        if count == 0:
            result["reason"] = "no_values"
            return result
        aggregate_value = total / Decimal(count)
    elif operator_mode == "min":
        aggregate_value = min(values)
    elif operator_mode == "max":
        aggregate_value = max(values)
    else:
        aggregate_value = None

    if aggregate_value is None:
        result["reason"] = "no_values"
        return result

    scale_decimal = _decimal_from_value(definition.get("scale", 1)) or Decimal(1)
    offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
    precision_int = _normalize_precision(definition.get("precision", 6))

    transformed = (aggregate_value * scale_decimal) + offset_decimal
    value_string, value_float = _format_decimal(transformed, precision_int)

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_float,
            "precision": precision_int,
            "source": "aggregate",
            "operator": operator_mode,
        }
    )

    if scale_decimal != Decimal(1):
        result["scale"] = float(scale_decimal)
    if offset_decimal != Decimal(0):
        result["offset"] = float(offset_decimal)

    result["dependencies"] = dependencies

    inputs_hash = _canonical_hash(
        {
            "operator": operator_mode,
            "entries": descriptor_entries,
            "scale": float(scale_decimal),
            "offset": float(offset_decimal),
        }
    )
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    return result


def _evaluate_ratio_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "numerator",
                "numerator_metric",
                "denominator",
                "denominator_metric",
                "numerator_default",
                "denominator_default",
                "tolerance",
                "fallback_value",
                "precision",
                "scale",
                "offset",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    numerator_ref_raw = definition.get("numerator") or definition.get("numerator_metric") or definition.get("numerator_source")
    denominator_ref_raw = definition.get("denominator") or definition.get("denominator_metric") or definition.get("denominator_source")

    numerator_ref = str(numerator_ref_raw) if numerator_ref_raw is not None else ""
    denominator_ref = str(denominator_ref_raw) if denominator_ref_raw is not None else ""

    if not numerator_ref:
        result["reason"] = "missing_numerator_metric"
        return result
    if not denominator_ref:
        result["reason"] = "missing_denominator_metric"
        return result
    if numerator_ref == metric_id or denominator_ref == metric_id:
        result["reason"] = "circular_reference"
        return result

    numerator_default = _decimal_from_value(definition.get("numerator_default") or definition.get("default_numerator"))
    denominator_default = _decimal_from_value(definition.get("denominator_default") or definition.get("default_denominator"))
    tolerance_decimal = _decimal_from_value(definition.get("tolerance") or definition.get("denominator_tolerance")) or Decimal(0)
    if tolerance_decimal < Decimal(0):
        tolerance_decimal = Decimal(0)

    numerator_reference = _resolve_metric_reference(
        numerator_ref,
        relational_state=relational_state,
        results_so_far=results_so_far,
    )
    denominator_reference = _resolve_metric_reference(
        denominator_ref,
        relational_state=relational_state,
        results_so_far=results_so_far,
    )

    if numerator_reference is None:
        if numerator_default is None:
            result["reason"] = "numerator_metric_unavailable"
            result["missing_metric"] = numerator_ref
            return result
        numerator_value = numerator_default
        numerator_inputs_hash = None
        numerator_source = "default"
    else:
        numerator_value = numerator_reference["value"]
        numerator_inputs_hash = numerator_reference.get("inputs_hash")
        numerator_source = "metric"

    if denominator_reference is None:
        if denominator_default is None:
            result["reason"] = "denominator_metric_unavailable"
            result["missing_metric"] = denominator_ref
            return result
        denominator_value = denominator_default
        denominator_inputs_hash = None
        denominator_source = "default"
    else:
        denominator_value = denominator_reference["value"]
        denominator_inputs_hash = denominator_reference.get("inputs_hash")
        denominator_source = "metric"

    fallback_ratio = _decimal_from_value(definition.get("fallback_value") or definition.get("zero_fallback"))

    ratio_mode = "computed"
    try:
        if abs(denominator_value) <= tolerance_decimal:
            if fallback_ratio is None:
                result["reason"] = "division_by_zero"
                return result
            ratio_value = fallback_ratio
            ratio_mode = "fallback"
        else:
            ratio_value = numerator_value / denominator_value
    except Exception:
        if fallback_ratio is None:
            result["reason"] = "division_failed"
            return result
        ratio_value = fallback_ratio
        ratio_mode = "fallback"

    scale_decimal = _decimal_from_value(definition.get("scale", 1)) or Decimal(1)
    offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
    precision_int = _normalize_precision(definition.get("precision", 6))

    transformed = (ratio_value * scale_decimal) + offset_decimal
    value_string, value_float = _format_decimal(transformed, precision_int)

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_float,
            "precision": precision_int,
            "source": "ratio",
            "numerator_metric": numerator_ref,
            "denominator_metric": denominator_ref,
            "mode": ratio_mode,
        }
    )

    if scale_decimal != Decimal(1):
        result["scale"] = float(scale_decimal)
    if offset_decimal != Decimal(0):
        result["offset"] = float(offset_decimal)

    descriptor = {
        "numerator": {
            "metric": numerator_ref,
            "value": float(numerator_value),
            "source": numerator_source,
        },
        "denominator": {
            "metric": denominator_ref,
            "value": float(denominator_value),
            "source": denominator_source,
        },
        "tolerance": float(tolerance_decimal),
        "fallback": float(fallback_ratio) if fallback_ratio is not None else None,
        "scale": float(scale_decimal),
        "offset": float(offset_decimal),
        "mode": ratio_mode,
    }
    if numerator_inputs_hash:
        descriptor["numerator"]["inputs_hash"] = numerator_inputs_hash
    if denominator_inputs_hash:
        descriptor["denominator"]["inputs_hash"] = denominator_inputs_hash

    inputs_hash = _canonical_hash(descriptor)
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    result["dependencies"] = [numerator_ref, denominator_ref]

    return result


_COMPARISON_OPERATORS = {
    ">": lambda lhs, rhs: lhs > rhs,
    ">=": lambda lhs, rhs: lhs >= rhs,
    "<": lambda lhs, rhs: lhs < rhs,
    "<=": lambda lhs, rhs: lhs <= rhs,
    "==": lambda lhs, rhs: lhs == rhs,
    "!=": lambda lhs, rhs: lhs != rhs,
}


def _compare_with_tolerance(value: Decimal, comparator: str, threshold: Decimal, tolerance: Decimal) -> bool:
    if tolerance < Decimal(0):
        tolerance = Decimal(0)
    if comparator == "==":
        return abs(value - threshold) <= tolerance
    if comparator == "!=":
        return abs(value - threshold) > tolerance
    if comparator == ">":
        return value > (threshold - tolerance)
    if comparator == ">=":
        return value >= (threshold - tolerance)
    if comparator == "<":
        return value < (threshold + tolerance)
    if comparator == "<=":
        return value <= (threshold + tolerance)
    return False


def _evaluate_logical_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "operator",
                "conditions",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    operator_raw = str(definition.get("operator", "and")).lower()
    if operator_raw not in ("and", "or"):
        result["reason"] = "unsupported_operator"
        return result

    conditions = definition.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        result["reason"] = "missing_conditions"
        return result

    evaluations: List[Dict[str, Any]] = []
    bool_results: List[bool] = []

    for condition in conditions:
        if not isinstance(condition, dict):
            result["reason"] = "invalid_condition"
            return result
        ref = condition.get("metric") or condition.get("metric_id")
        ref_id = str(ref) if ref is not None else ""
        if not ref_id:
            result["reason"] = "missing_metric_reference"
            return result
        if ref_id == metric_id:
            result["reason"] = "circular_reference"
            return result

        comparator = str(condition.get("comparison", ">=")).strip()
        if comparator not in _COMPARISON_OPERATORS:
            result["reason"] = "unsupported_comparison"
            return result

        threshold_decimal = _decimal_from_value(condition.get("value"))
        if threshold_decimal is None:
            result["reason"] = "invalid_threshold"
            return result

        reference = _resolve_metric_reference(
            ref_id,
            relational_state=relational_state,
            results_so_far=results_so_far,
        )
        if reference is None:
            result["reason"] = "metric_unavailable"
            result["missing_metric"] = ref_id
            return result

        comparison_result = _COMPARISON_OPERATORS[comparator](reference["value"], threshold_decimal)
        bool_results.append(bool(comparison_result))

        condition_descriptor: Dict[str, Any] = {
            "metric": ref_id,
            "comparison": comparator,
            "threshold": float(threshold_decimal),
            "value": float(reference["value"]),
        }
        if reference.get("inputs_hash"):
            condition_descriptor["inputs_hash"] = reference["inputs_hash"]
        evaluations.append(condition_descriptor)

    if operator_raw == "and":
        aggregate = all(bool_results)
    else:
        aggregate = any(bool_results)

    precision_int = 0
    value_string = "true" if aggregate else "false"
    value_numeric = 1.0 if aggregate else 0.0

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_numeric,
            "precision": precision_int,
            "source": "logical",
            "operator": operator_raw,
        }
    )

    inputs_hash = _canonical_hash({"conditions": evaluations, "operator": operator_raw})
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    result["dependencies"] = [condition.get("metric") or condition.get("metric_id") for condition in conditions if isinstance(condition, dict)]
    return result


def _evaluate_custom_definition(
    definition: Dict[str, Any],
    *,
    relational_state: Optional[Dict[str, Any]],
    results_so_far: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    metric_id = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""
    result: Dict[str, Any] = {
        "metric_id": metric_id,
        "definition_type": str(definition.get("type")),
        "available": False,
    }

    if not metric_id:
        result["reason"] = "missing_metric_id"
        return result

    definition_hash = _canonical_hash(
        _sanitize_definition_for_hash(
            definition,
            supported_keys=(
                "metric_id",
                "version",
                "type",
                "mode",
                "function",
                "checks",
                "validation",
                "value",
                "precision",
                "scale",
                "offset",
            ),
        )
    )
    if definition_hash:
        result["definition_hash"] = definition_hash

    mode_raw = definition.get("mode") or definition.get("function") or "validation"
    mode = str(mode_raw).lower()

    if mode == "constant":
        constant_value = _decimal_from_value(
            definition.get("value")
            or definition.get("constant")
            or definition.get("constant_value")
            or definition.get("value_numeric")
        )
        if constant_value is None:
            result["reason"] = "missing_constant_value"
            return result

        scale_decimal = _decimal_from_value(definition.get("scale", 1)) or Decimal(1)
        offset_decimal = _decimal_from_value(definition.get("offset", 0)) or Decimal(0)
        precision_int = _normalize_precision(definition.get("precision", 6))

        transformed = (constant_value * scale_decimal) + offset_decimal
        value_string, value_float = _format_decimal(transformed, precision_int)

        result.update(
            {
                "available": True,
                "value": value_string,
                "value_numeric": value_float,
                "precision": precision_int,
                "source": "custom_constant",
                "mode": "constant",
            }
        )

        if scale_decimal != Decimal(1):
            result["scale"] = float(scale_decimal)
        if offset_decimal != Decimal(0):
            result["offset"] = float(offset_decimal)

        inputs_hash = _canonical_hash(
            {
                "mode": "constant",
                "value": float(constant_value),
                "scale": float(scale_decimal),
                "offset": float(offset_decimal),
            }
        )
        if inputs_hash:
            result["inputs_hash"] = inputs_hash
        result["dependencies"] = []
        return result

    # Default: validation checks
    validation_block = definition.get("validation") if isinstance(definition.get("validation"), dict) else {}
    required_inputs = validation_block.get("required_inputs")
    required_list: List[str] = []
    if isinstance(required_inputs, list):
        for item in required_inputs:
            if isinstance(item, str) and item:
                required_list.append(item)

    tolerance_default = _decimal_from_value(validation_block.get("tolerance")) or Decimal(0)
    if tolerance_default < Decimal(0):
        tolerance_default = Decimal(0)

    missing_required: List[str] = []
    for ref_id in required_list:
        reference = _resolve_metric_reference(
            ref_id,
            relational_state=relational_state,
            results_so_far=results_so_far,
        )
        if reference is None:
            missing_required.append(ref_id)

    if missing_required:
        result["reason"] = "required_metric_unavailable"
        result["missing_metric"] = missing_required[0]
        return result

    checks = definition.get("checks")
    if not isinstance(checks, list) or not checks:
        result["reason"] = "missing_checks"
        return result

    evaluations: List[Dict[str, Any]] = []
    bool_results: List[bool] = []
    dependencies: List[str] = list(required_list)

    for check in checks:
        if not isinstance(check, dict):
            result["reason"] = "invalid_check"
            return result
        ref_candidate = check.get("metric") or check.get("metric_id")
        ref_id = str(ref_candidate) if ref_candidate is not None else ""
        if not ref_id:
            result["reason"] = "missing_metric_reference"
            return result
        if ref_id == metric_id:
            result["reason"] = "circular_reference"
            return result

        comparator = str(check.get("comparison", ">=")).strip()
        if comparator not in _COMPARISON_OPERATORS:
            result["reason"] = "unsupported_comparison"
            return result

        threshold_decimal = _decimal_from_value(check.get("value"))
        if threshold_decimal is None:
            result["reason"] = "invalid_threshold"
            return result

        tolerance_decimal = _decimal_from_value(check.get("tolerance"))
        if tolerance_decimal is None:
            tolerance_decimal = tolerance_default
        if tolerance_decimal < Decimal(0):
            tolerance_decimal = Decimal(0)

        reference = _resolve_metric_reference(
            ref_id,
            relational_state=relational_state,
            results_so_far=results_so_far,
        )
        if reference is None:
            result["reason"] = "metric_unavailable"
            result["missing_metric"] = ref_id
            return result

        value_decimal = reference["value"]
        passed = _compare_with_tolerance(value_decimal, comparator, threshold_decimal, tolerance_decimal)
        bool_results.append(bool(passed))

        evaluation_entry: Dict[str, Any] = {
            "metric": ref_id,
            "comparison": comparator,
            "threshold": float(threshold_decimal),
            "value": float(value_decimal),
            "tolerance": float(tolerance_decimal),
            "passed": bool(passed),
        }
        if reference.get("inputs_hash"):
            evaluation_entry["inputs_hash"] = reference["inputs_hash"]
        evaluations.append(evaluation_entry)
        dependencies.append(ref_id)

    all_pass = all(bool_results) if bool_results else False
    value_string = "pass" if all_pass else "fail"
    value_numeric = 1.0 if all_pass else 0.0

    result.update(
        {
            "available": True,
            "value": value_string,
            "value_numeric": value_numeric,
            "precision": 0,
            "source": "custom_validation",
            "mode": "validation",
            "checks": evaluations,
            "checks_passed": int(sum(1 for v in bool_results if v)),
            "checks_total": len(bool_results),
        }
    )

    inputs_hash = _canonical_hash({"mode": "validation", "evaluations": evaluations})
    if inputs_hash:
        result["inputs_hash"] = inputs_hash

    result["dependencies"] = dependencies
    return result


def evaluate_metric_definitions(
    relational_state: Optional[Dict[str, Any]],
    *,
    definitions: Optional[List[Dict[str, Any]]] = None,
    composed_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    definitions_list = definitions if isinstance(definitions, list) else _load_metric_definitions(relational_state)
    if not definitions_list:
        return {
            "available": False,
            "results": {},
            "results_hash": None,
            "definition_count": 0,
            "validation_summary": {"valid": True, "definition_count": 0, "results": []},
        }

    validation_summary = validate_metric_definitions(definitions_list)
    validation_results_list = validation_summary.get("results") if isinstance(validation_summary.get("results"), list) else []

    results: Dict[str, Dict[str, Any]] = {}
    for index, definition in enumerate(definitions_list):
        validation_payload = None
        if index < len(validation_results_list):
            candidate = validation_results_list[index]
            if isinstance(candidate, dict):
                validation_payload = candidate

        if not isinstance(definition, dict):
            if validation_payload:
                metric_id_candidate = validation_payload.get("metric_id") or ""
                definition_type = validation_payload.get("definition_type") or ""
                errors = validation_payload.get("errors") or []
                reason = errors[0].get("code") if errors and isinstance(errors[0], dict) and errors[0].get("code") else "invalid_definition"
                evaluated = {
                    "metric_id": metric_id_candidate,
                    "definition_type": definition_type,
                    "available": False,
                    "reason": reason,
                }
                definition_hash = validation_payload.get("definition_hash")
                if definition_hash:
                    evaluated["definition_hash"] = definition_hash
                if errors:
                    evaluated["validation_errors"] = errors
                warnings = validation_payload.get("warnings")
                if warnings:
                    evaluated["validation_warnings"] = warnings
                if metric_id_candidate:
                    results[metric_id_candidate] = evaluated
            continue

        raw_type = definition.get("type")
        definition_type = str(raw_type) if raw_type is not None else ""
        metric_id_candidate = str(definition.get("metric_id")) if definition.get("metric_id") is not None else ""

        if validation_payload and not validation_payload.get("valid", False):
            errors = validation_payload.get("errors") or []
            reason = errors[0].get("code") if errors and isinstance(errors[0], dict) and errors[0].get("code") else "validation_failed"
            evaluated = {
                "metric_id": metric_id_candidate,
                "definition_type": definition_type,
                "available": False,
                "reason": reason,
            }
            definition_hash = validation_payload.get("definition_hash")
            if definition_hash:
                evaluated["definition_hash"] = definition_hash
            if errors:
                evaluated["validation_errors"] = errors
            warnings = validation_payload.get("warnings")
            if warnings:
                evaluated["validation_warnings"] = warnings
            if metric_id_candidate:
                results[metric_id_candidate] = evaluated
            continue

        if definition_type == "graph_metric":
            evaluated = _evaluate_graph_metric_definition(definition, composed_payload)
        elif definition_type == "identity":
            evaluated = _evaluate_identity_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        elif definition_type == "weighted_sum":
            evaluated = _evaluate_weighted_sum_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        elif definition_type == "aggregate":
            evaluated = _evaluate_aggregate_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        elif definition_type == "ratio":
            evaluated = _evaluate_ratio_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        elif definition_type == "logical":
            evaluated = _evaluate_logical_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        elif definition_type == "custom":
            evaluated = _evaluate_custom_definition(
                definition,
                relational_state=relational_state,
                results_so_far=results,
            )
        else:
            evaluated = {
                "metric_id": metric_id_candidate,
                "definition_type": definition_type,
                "available": False,
                "reason": "unsupported_definition_type",
            }
            if metric_id_candidate:
                definition_hash = _canonical_hash(
                    _sanitize_definition_for_hash(
                        definition,
                        supported_keys=("metric_id", "version", "type"),
                    )
                )
                if definition_hash:
                    evaluated["definition_hash"] = definition_hash

        if validation_payload:
            warnings = validation_payload.get("warnings") or []
            if warnings:
                evaluated["validation_warnings"] = warnings
            if "definition_hash" not in evaluated:
                definition_hash = validation_payload.get("definition_hash")
                if definition_hash:
                    evaluated["definition_hash"] = definition_hash

        metric_id = evaluated.get("metric_id")
        if metric_id:
            results[metric_id] = evaluated

    results_hash = _canonical_hash(results)
    available_any = any(result.get("available") for result in results.values())
    return {
        "available": available_any,
        "results": results,
        "results_hash": results_hash,
        "definition_count": len(results),
        "validation_summary": validation_summary,
    }
