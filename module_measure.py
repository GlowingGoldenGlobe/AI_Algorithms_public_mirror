# module_measure.py
from module_concept_measure import classify_measurement_adequacy_level
from module_metrics import build_graph_metric_inputs, build_composed_graph_metrics, evaluate_metric_definitions
from module_tools import similarity, familiarity, usefulness, synthesis_potential, compare_against_objectives, canonical_json_bytes
import json
import os
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Workspace root resolution (not currently used elsewhere in this module)
ROOT = os.path.dirname(os.path.abspath(__file__))

DEFAULT_WEIGHTS = {
    'similarity': 0.4,
    'usefulness': 0.4,
    'repeat': 0.1,
    'contradiction': -0.6,
    'synthesis_bias': 0.2,
    'review_bias': 0.1
}


def build_measurement_adequacy_snapshot_row(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one semantic record into the bounded adequacy-input row shape."""

    from module_spatial_snapshots import summarize_spatial_snapshot_record

    return summarize_spatial_snapshot_record(record)


def build_measurement_adequacy_inputs(
    *,
    spatial_records: Optional[Iterable[Dict[str, Any]]] = None,
    telemetry_events: Optional[Iterable[Dict[str, Any]]] = None,
    telemetry_summary: Optional[Dict[str, Any]] = None,
    measurement_recorded: Optional[bool] = None,
    measurement_hash_present: Optional[bool] = None,
    bridge_present: Optional[bool] = None,
    telemetry_completed_present: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build reusable adequacy counts and supporting signals from snapshot and telemetry evidence."""

    from module_spatial_telemetry import summarize_spatial_telemetry_events

    normalized_rows: List[Dict[str, Any]] = []
    for item in list(spatial_records or []):
        if not isinstance(item, dict):
            continue
        if {"measurement_recorded", "snapshot_present", "measurement_hash_present", "graph_metrics_present", "bridge_present"}.issubset(item.keys()):
            normalized_rows.append(
                {
                    "record_id": item.get("record_id"),
                    "cycle_id": item.get("cycle_id"),
                    "measurement_recorded": bool(item.get("measurement_recorded")),
                    "snapshot_present": bool(item.get("snapshot_present")),
                    "snapshot_relative_path": item.get("snapshot_relative_path"),
                    "snapshot_hash": item.get("snapshot_hash"),
                    "measurement_hash_present": bool(item.get("measurement_hash_present")),
                    "measurement_hash": item.get("measurement_hash"),
                    "graph_metrics_present": bool(item.get("graph_metrics_present")),
                    "bridge_present": bool(item.get("bridge_present")),
                }
            )
        else:
            normalized_rows.append(build_measurement_adequacy_snapshot_row(item))

    telemetry_payload = (
        telemetry_summary
        if isinstance(telemetry_summary, dict)
        else summarize_spatial_telemetry_events(list(telemetry_events or []))
    )
    telemetry_counts = telemetry_payload.get("status_counts") if isinstance(telemetry_payload.get("status_counts"), dict) else {}

    measured_records = sum(1 for row in normalized_rows if row.get("measurement_recorded"))
    snapshot_linked_records = sum(1 for row in normalized_rows if row.get("snapshot_present"))
    graph_metric_records = sum(1 for row in normalized_rows if row.get("graph_metrics_present"))
    completed_events = int(telemetry_counts.get("completed") or telemetry_payload.get("completed_event_count") or 0)
    skipped_events = int(telemetry_counts.get("skipped") or telemetry_payload.get("skipped_event_count") or 0)
    failed_events = int(telemetry_counts.get("failed") or telemetry_payload.get("failed_event_count") or 0)

    measurement_signal = bool(measured_records) if measurement_recorded is None else bool(measurement_recorded)
    snapshot_signal = bool(snapshot_linked_records)
    graph_signal = bool(graph_metric_records)
    hash_signal = (
        any(bool(row.get("measurement_hash_present")) for row in normalized_rows)
        if measurement_hash_present is None
        else bool(measurement_hash_present)
    )
    bridge_signal = (
        any(bool(row.get("bridge_present")) for row in normalized_rows)
        if bridge_present is None
        else bool(bridge_present)
    )
    telemetry_signal = bool(completed_events) if telemetry_completed_present is None else bool(telemetry_completed_present)

    return {
        "spatial_rows": normalized_rows,
        "telemetry": telemetry_payload,
        "counts": {
            "measured_records": measured_records,
            "snapshot_linked_records": snapshot_linked_records,
            "graph_metric_records": graph_metric_records,
            "completed_events": completed_events,
            "skipped_events": skipped_events,
            "failed_events": failed_events,
        },
        "signals": {
            "measurement_recorded": measurement_signal,
            "snapshot_present": snapshot_signal,
            "graph_metrics_present": graph_signal,
            "measurement_hash_present": hash_signal,
            "bridge_present": bridge_signal,
            "telemetry_completed_present": telemetry_signal,
        },
    }


def summarize_measurement_adequacy(
    *,
    spatial_overview: Optional[Dict[str, Any]] = None,
    spatial_telemetry: Optional[Dict[str, Any]] = None,
    measurement_recorded: Optional[bool] = None,
    snapshot_present: Optional[bool] = None,
    measurement_hash_present: Optional[bool] = None,
    bridge_present: Optional[bool] = None,
    telemetry_completed_present: Optional[bool] = None,
) -> Dict[str, Any]:
    overview_records = spatial_overview.get("records") if isinstance(spatial_overview, dict) else []
    if not isinstance(overview_records, list):
        overview_records = []

    telemetry_counts = spatial_telemetry.get("status_counts") if isinstance(spatial_telemetry, dict) else {}
    if not isinstance(telemetry_counts, dict):
        telemetry_counts = {}

    measured_records = len(overview_records)
    snapshot_linked_records = sum(
        1
        for row in overview_records
        if isinstance(row, dict) and (row.get("snapshot_hash") or row.get("snapshot_relative_path"))
    )
    graph_metric_records = sum(
        1
        for row in overview_records
        if isinstance(row, dict)
        and isinstance(row.get("graph_metrics"), dict)
        and row["graph_metrics"].get("available") is True
    )
    completed_events = int(telemetry_counts.get("completed") or 0)
    skipped_events = int(telemetry_counts.get("skipped") or 0)
    failed_events = int(telemetry_counts.get("failed") or 0)

    measurement_signal = bool(measured_records) if measurement_recorded is None else bool(measurement_recorded)
    snapshot_signal = bool(snapshot_linked_records) if snapshot_present is None else bool(snapshot_present)
    graph_signal = bool(graph_metric_records)
    hash_signal = bool(measurement_hash_present)
    bridge_signal = bool(bridge_present)
    telemetry_signal = bool(completed_events) if telemetry_completed_present is None else bool(telemetry_completed_present)

    supporting_signals = sum(
        1
        for flag in (snapshot_signal, graph_signal, hash_signal, bridge_signal, telemetry_signal)
        if flag
    )
    verdict = classify_measurement_adequacy_level(
        measurement_recorded=measurement_signal,
        supporting_signal_count=supporting_signals,
        completed_events=completed_events,
        skipped_events=skipped_events,
    )

    return {
        "level": verdict["level"],
        "reason": verdict["reason"],
        "counts": {
            "measured_records": measured_records,
            "snapshot_linked_records": snapshot_linked_records,
            "graph_metric_records": graph_metric_records,
            "completed_events": completed_events,
            "skipped_events": skipped_events,
            "failed_events": failed_events,
        },
        "signals": {
            "measurement_recorded": measurement_signal,
            "snapshot_present": snapshot_signal,
            "graph_metrics_present": graph_signal,
            "measurement_hash_present": hash_signal,
            "bridge_present": bridge_signal,
            "telemetry_completed_present": telemetry_signal,
        },
    }


def _append_provenance_events(events: Iterable[Tuple[str, Dict[str, Any]]]) -> None:
    event_list: List[Tuple[str, Dict[str, Any]]] = []
    for event_type, payload in events:
        if not isinstance(event_type, str):
            continue
        if not isinstance(payload, dict):
            continue
        event_list.append((event_type, dict(payload)))
    if not event_list:
        return
    try:
        from module_storage import load_provenance_log, save_provenance_log
        from module_provenance import append_event, create_event

        log = load_provenance_log()
        prev_hash: Optional[str] = None
        if log:
            last = log[-1]
            if isinstance(last, dict):
                prev_candidate = last.get("event_id")
                if isinstance(prev_candidate, str) and prev_candidate:
                    prev_hash = prev_candidate
        for event_type, payload in event_list:
            target_payload = dict(payload)
            event = create_event(event_type, target_payload, prev_hash=prev_hash)
            event_id = event.get("event_id") if isinstance(event, dict) else None
            prev_hash = str(event_id) if isinstance(event_id, str) and event_id else prev_hash
            log = append_event(log, event)
        save_provenance_log(log)
    except Exception:
        pass


def _build_graph_snapshot_event_payload(
    target_id: str,
    derived: Dict[str, Any],
    artifact_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    snapshot = derived.get("graph_snapshot") if isinstance(derived.get("graph_snapshot"), dict) else None
    if not isinstance(snapshot, dict):
        return None
    build_info = derived.get("graph_snapshot_build_info") if isinstance(derived.get("graph_snapshot_build_info"), dict) else {}
    nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
    edges = snapshot.get("edges") if isinstance(snapshot.get("edges"), list) else []
    target = str(target_id) if isinstance(target_id, str) else ""
    payload: Dict[str, Any] = {
        "target_ids": [target] if target else [],
        "tick_id": str(snapshot.get("tick_id") or ""),
        "snapshot_hash": str(snapshot.get("snapshot_hash") or derived.get("graph_snapshot_hash") or ""),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "constraint_count": int(build_info.get("constraint_count", 0)),
    }
    duration = build_info.get("build_duration_ms")
    if isinstance(duration, (int, float)):
        payload["duration_ms"] = float(duration)
    inputs_hash = derived.get("graph_metrics_inputs_hash")
    if isinstance(inputs_hash, str) and inputs_hash:
        payload["inputs_hash"] = inputs_hash
    if artifact_path:
        payload["artifact_path"] = artifact_path
    return payload


def _build_graph_metrics_event_payload(
    target_id: str,
    derived: Dict[str, Any],
    reason: Optional[str] = None,
    artifact_path: Optional[str] = None,
) -> Dict[str, Any]:
    target = str(target_id) if isinstance(target_id, str) else ""
    metrics_body = derived.get("graph_metrics_composed") if isinstance(derived.get("graph_metrics_composed"), dict) else None
    payload: Dict[str, Any] = {
        "target_ids": [target] if target else [],
        "available": bool(isinstance(metrics_body, dict)),
    }
    snapshot_hash = derived.get("graph_snapshot_hash")
    if isinstance(snapshot_hash, str) and snapshot_hash:
        payload["snapshot_hash"] = snapshot_hash
    metrics_hash = derived.get("graph_metrics_composed_hash")
    if isinstance(metrics_hash, str) and metrics_hash:
        payload["metrics_hash"] = metrics_hash
    inputs_hash = derived.get("graph_metrics_composed_inputs_hash")
    if isinstance(inputs_hash, str) and inputs_hash:
        payload["inputs_hash"] = inputs_hash
    if isinstance(metrics_body, dict):
        payload["metrics"] = metrics_body
        if reason:
            payload["reason"] = reason
    else:
        payload["reason"] = reason or "graph_metrics_unavailable"
        payload["metrics"] = {}
    if artifact_path:
        payload["artifact_path"] = artifact_path
    return payload


def _build_metric_event_payloads(
    target_id: str,
    metric_payloads: Dict[str, Dict[str, Any]],
    metric_ids: Iterable[str],
    artifact_path: Optional[str] = None,
) -> List[Tuple[str, Dict[str, Any]]]:
    events: List[Tuple[str, Dict[str, Any]]] = []
    target = str(target_id) if isinstance(target_id, str) else ""
    target_list = [target] if target else []
    seen: Set[str] = set()
    for metric_id in metric_ids:
        mid = str(metric_id)
        if not mid or mid in seen:
            continue
        seen.add(mid)
        payload = dict(metric_payloads.get(mid) or {})
        available = bool(payload.get("available"))
        event_payload: Dict[str, Any] = {
            "target_ids": target_list,
            "metric_id": mid,
            "available": available,
        }
        for key in ("value", "value_numeric", "definition_hash", "inputs_hash", "source", "precision", "reason"):
            value = payload.get(key)
            if value is not None:
                event_payload[key] = value
        if artifact_path:
            event_payload["artifact_path"] = artifact_path
        events.append(("metric_evaluated", event_payload))
    return events


def _persist_provenance_artifacts(
    *,
    target_id: str,
    relational_state: Optional[Dict[str, Any]],
) -> Dict[str, Optional[str]]:
    artifact_paths: Dict[str, Optional[str]] = {}
    if not isinstance(relational_state, dict):
        return artifact_paths

    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else None
    metrics_store = relational_state.get("metrics") if isinstance(relational_state.get("metrics"), dict) else None

    try:
        from module_storage import write_provenance_artifact
    except Exception:
        return artifact_paths

    if not callable(write_provenance_artifact):
        return artifact_paths

    tick_candidate = None
    if isinstance(derived, dict):
        snapshot = derived.get("graph_snapshot")
        if isinstance(snapshot, dict):
            candidate = snapshot.get("tick_id")
            if isinstance(candidate, str) and candidate:
                tick_candidate = candidate
    tick_id = tick_candidate if isinstance(tick_candidate, str) and tick_candidate else target_id

    def _relpath(path: Optional[str]) -> Optional[str]:
        if not isinstance(path, str) or not path:
            return None
        try:
            rel = os.path.relpath(path, ROOT)
            return rel.replace("\\", "/")
        except Exception:
            return None

    snapshot_payload = derived.get("graph_snapshot") if isinstance(derived, dict) else None
    snapshot_path = write_provenance_artifact(
        target_id=target_id,
        tick_id=tick_id,
        artifact_name="graph_snapshot",
        payload=snapshot_payload if isinstance(snapshot_payload, dict) else None,
    )
    artifact_paths["graph_snapshot"] = _relpath(snapshot_path)

    inputs_payload: Optional[Dict[str, Any]] = None
    if isinstance(derived, dict):
        inputs_metrics = derived.get("graph_metrics_inputs")
        if isinstance(inputs_metrics, dict):
            inputs_payload = {
                "available": True,
                "metrics": inputs_metrics,
            }
            inputs_hash = derived.get("graph_metrics_inputs_hash")
            if isinstance(inputs_hash, str) and inputs_hash:
                inputs_payload["metrics_hash"] = inputs_hash
    inputs_path = write_provenance_artifact(
        target_id=target_id,
        tick_id=tick_id,
        artifact_name="graph_metrics_inputs",
        payload=inputs_payload,
    )
    artifact_paths["graph_metrics_inputs"] = _relpath(inputs_path)

    composed_payload: Optional[Dict[str, Any]] = None
    if isinstance(derived, dict):
        composed_metrics = derived.get("graph_metrics_composed")
        if isinstance(composed_metrics, dict):
            composed_payload = {
                "available": True,
                "metrics": composed_metrics,
            }
            composed_hash = derived.get("graph_metrics_composed_hash")
            if isinstance(composed_hash, str) and composed_hash:
                composed_payload["metrics_hash"] = composed_hash
            composed_inputs_hash = derived.get("graph_metrics_composed_inputs_hash")
            if isinstance(composed_inputs_hash, str) and composed_inputs_hash:
                composed_payload["inputs_hash"] = composed_inputs_hash
    composed_path = write_provenance_artifact(
        target_id=target_id,
        tick_id=tick_id,
        artifact_name="graph_metrics_composed",
        payload=composed_payload,
    )
    artifact_paths["graph_metrics_composed"] = _relpath(composed_path)

    results_payload: Optional[Dict[str, Any]] = None
    if isinstance(metrics_store, dict) and metrics_store:
        results_payload = {
            "available": True,
            "metrics": metrics_store,
        }
        if isinstance(derived, dict):
            for key in ("metrics_results_hash", "metrics_definition_count", "metrics_available"):
                value = derived.get(key)
                if value is not None:
                    results_payload[key] = value
    results_path = write_provenance_artifact(
        target_id=target_id,
        tick_id=tick_id,
        artifact_name="metrics_results",
        payload=results_payload,
    )
    artifact_paths["metrics_results"] = _relpath(results_path)

    definitions_payload: Optional[Dict[str, Any]] = None
    if isinstance(relational_state, dict):
        definitions_list = relational_state.get("metrics_definitions")
        if isinstance(definitions_list, list):
            definitions_payload = {
                "definitions": definitions_list,
            }
            if isinstance(derived, dict):
                definition_hashes = derived.get("metrics_definition_hashes")
                if isinstance(definition_hashes, dict) and definition_hashes:
                    definitions_payload["definition_hashes"] = definition_hashes
    definitions_path = write_provenance_artifact(
        target_id=target_id,
        tick_id=tick_id,
        artifact_name="metrics_definitions",
        payload=definitions_payload,
    )
    artifact_paths["metrics_definitions"] = _relpath(definitions_path)

    return artifact_paths

def get_measurement_weights():
    cfg = {}
    try:
        with open(os.path.join(ROOT, 'config.json'), 'r', encoding='utf-8') as cf:
            cfg = json.load(cf)
    except Exception:
        cfg = {}
    raw = cfg.get('measurement_weights') or {}
    return {
        'similarity': float(raw.get('similarity', DEFAULT_WEIGHTS['similarity'])),
        'usefulness': float(raw.get('usefulness', DEFAULT_WEIGHTS['usefulness'])),
        'repeat': float(raw.get('repeat', DEFAULT_WEIGHTS['repeat'])),
        'contradiction': float(raw.get('contradiction', DEFAULT_WEIGHTS['contradiction'])),
        'synthesis_bias': float(raw.get('synthesis_bias', DEFAULT_WEIGHTS['synthesis_bias'])),
        'review_bias': float(raw.get('review_bias', DEFAULT_WEIGHTS['review_bias']))
    }

def print_weights():
    w = get_measurement_weights()
    print(json.dumps(w, indent=2))

def get_occurrence(data_path: str) -> int:
    """Return occurrence count from a stored record."""
    with open(data_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    return record.get("occurrence_count", 0)

def analyzer_evaluate(data_path: str) -> float:
    """Evaluate data using occurrence count and placeholder logic."""
    occurrence = get_occurrence(data_path)
    # Example scoring: higher occurrence = higher relevance
    score = occurrence * 1.0
    return score

def scheduler_flag(data_path: str, label: str):
    """Flag a record with a label for future scheduling."""
    with open(data_path, "r+", encoding="utf-8") as f:
        record = json.load(f)
        record["labels"].append(label)
        f.seek(0)
        json.dump(record, f, indent=2)
        f.truncate()
    return f"Flagged {data_path} with label {label}"

"""
def measure_information(data_path: str, threshold: float = 2.0):
    #Measure information and decide whether to flag or discard.
    score = analyzer_evaluate(data_path)
    if score >= threshold:
        return scheduler_flag(data_path, "important")
    else:
        return f"Discarded {data_path} (score={score})"
"""

def measure_information(file_path, threshold=1.0, objectives=None, focus_state=None):
    """
    Phase 9: Produce a structured measurement report with signals,
    recommended_actions, conflicts, and reasons.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    content = data.get("content", "")
    data_id = str(data.get("id") or os.path.basename(file_path))

    # Persist deterministic graph snapshot for downstream consumers.
    snapshot_written = False
    graph_snapshot_changed = False
    graph_metrics_composed_changed = False
    graph_metrics_change_reason: Optional[str] = None
    metric_results_changed = False
    metrics_changed_ids: Set[str] = set()
    metrics_event_payloads: Dict[str, Dict[str, Any]] = {}
    previous_definition_hashes: Dict[str, str] = {}
    current_definition_hashes: Dict[str, str] = {}
    definition_changes: List[Dict[str, Any]] = []
    try:
        from module_integration import build_graph_snapshot

        rs = data.get("relational_state")
        if isinstance(rs, dict):
            derived_existing = rs.get("derived") if isinstance(rs.get("derived"), dict) else None
            if isinstance(derived_existing, dict):
                existing_definition_hashes = (
                    derived_existing.get("metrics_definition_hashes")
                    if isinstance(derived_existing.get("metrics_definition_hashes"), dict)
                    else None
                )
                if isinstance(existing_definition_hashes, dict):
                    for metric_id, hash_value in existing_definition_hashes.items():
                        metric_key = str(metric_id) if metric_id is not None else ""
                        if not metric_key:
                            continue
                        hash_str = hash_value if isinstance(hash_value, str) and hash_value else None
                        if hash_str:
                            previous_definition_hashes[metric_key] = hash_str
        tick_source = None
        for candidate in (
            data.get("cycle_id"),
            rs.get("cycle_id") if isinstance(rs, dict) else None,
            data_id,
        ):
            if isinstance(candidate, str) and candidate:
                tick_source = candidate
                break
        if not isinstance(tick_source, str) or not tick_source:
            tick_source = os.path.basename(file_path)

        snapshot = build_graph_snapshot(rs if isinstance(rs, dict) else {}, str(tick_source))
        if snapshot:
            if not isinstance(rs, dict):
                rs = {}
                data["relational_state"] = rs
            derived = rs.get("derived")
            if not isinstance(derived, dict):
                derived = {}
                rs["derived"] = derived
            spatial_measurement = rs.get("spatial_measurement")
            if isinstance(spatial_measurement, dict):
                try:
                    sm_hash = hashlib.sha256(canonical_json_bytes(spatial_measurement)).hexdigest()
                except Exception:
                    sm_hash = None
                if isinstance(sm_hash, str) and sm_hash:
                    if derived.get("spatial_measurement_hash") != sm_hash:
                        derived["spatial_measurement_hash"] = sm_hash
                        snapshot_written = True
                schema_version = spatial_measurement.get("version")
                if isinstance(schema_version, str):
                    if derived.get("spatial_measurement_schema_version") != schema_version:
                        derived["spatial_measurement_schema_version"] = schema_version
                        snapshot_written = True
            else:
                if "spatial_measurement_hash" in derived or "spatial_measurement_schema_version" in derived:
                    derived.pop("spatial_measurement_hash", None)
                    derived.pop("spatial_measurement_schema_version", None)
                    snapshot_written = True
            snapshot_dict = snapshot.to_dict()
            existing_snapshot = derived.get("graph_snapshot") if isinstance(derived.get("graph_snapshot"), dict) else None
            existing_hash = derived.get("graph_snapshot_hash")
            existing_info = derived.get("graph_snapshot_build_info") if isinstance(derived.get("graph_snapshot_build_info"), dict) else None

            if existing_snapshot != snapshot_dict or existing_hash != snapshot.snapshot_hash or existing_info != snapshot.build_info:
                derived["graph_snapshot"] = snapshot_dict
                derived["graph_snapshot_hash"] = snapshot.snapshot_hash
                derived["graph_snapshot_build_info"] = snapshot.build_info
                snapshot_written = True
                graph_snapshot_changed = True

            metrics_payload = build_graph_metric_inputs(rs)
            metrics_available = bool(metrics_payload.get("available"))
            if metrics_available:
                metrics_body = metrics_payload.get("metrics") if isinstance(metrics_payload.get("metrics"), dict) else {}
                metrics_hash = metrics_payload.get("metrics_hash")
                existing_metrics = derived.get("graph_metrics_inputs") if isinstance(derived.get("graph_metrics_inputs"), dict) else None
                existing_metrics_hash = derived.get("graph_metrics_inputs_hash") if isinstance(derived.get("graph_metrics_inputs_hash"), str) else None

                if existing_metrics != metrics_body or existing_metrics_hash != metrics_hash:
                    derived["graph_metrics_inputs"] = metrics_body
                    if isinstance(metrics_hash, str) and metrics_hash:
                        derived["graph_metrics_inputs_hash"] = metrics_hash
                    else:
                        derived.pop("graph_metrics_inputs_hash", None)
                    snapshot_written = True
            else:
                if "graph_metrics_inputs" in derived or "graph_metrics_inputs_hash" in derived:
                    derived.pop("graph_metrics_inputs", None)
                    derived.pop("graph_metrics_inputs_hash", None)
                    snapshot_written = True

            composed_payload = build_composed_graph_metrics(rs, metrics_payload=metrics_payload if metrics_available else None)
            composed_available = bool(composed_payload.get("available"))
            if composed_available:
                composed_body = composed_payload.get("metrics") if isinstance(composed_payload.get("metrics"), dict) else {}
                composed_hash = composed_payload.get("metrics_hash")
                composed_inputs_hash = composed_payload.get("inputs_hash") if isinstance(composed_payload.get("inputs_hash"), str) else None

                existing_composed = derived.get("graph_metrics_composed") if isinstance(derived.get("graph_metrics_composed"), dict) else None
                existing_composed_hash = derived.get("graph_metrics_composed_hash") if isinstance(derived.get("graph_metrics_composed_hash"), str) else None
                existing_composed_inputs_hash = derived.get("graph_metrics_composed_inputs_hash") if isinstance(derived.get("graph_metrics_composed_inputs_hash"), str) else None

                if (
                    existing_composed != composed_body
                    or existing_composed_hash != composed_hash
                    or existing_composed_inputs_hash != composed_inputs_hash
                ):
                    derived["graph_metrics_composed"] = composed_body
                    if isinstance(composed_hash, str) and composed_hash:
                        derived["graph_metrics_composed_hash"] = composed_hash
                    else:
                        derived.pop("graph_metrics_composed_hash", None)
                    if composed_inputs_hash:
                        derived["graph_metrics_composed_inputs_hash"] = composed_inputs_hash
                    else:
                        derived.pop("graph_metrics_composed_inputs_hash", None)
                    snapshot_written = True
                    graph_metrics_composed_changed = True
                    graph_metrics_change_reason = None
            else:
                removed = False
                if "graph_metrics_composed" in derived:
                    derived.pop("graph_metrics_composed", None)
                    removed = True
                if "graph_metrics_composed_hash" in derived:
                    derived.pop("graph_metrics_composed_hash", None)
                    removed = True
                if "graph_metrics_composed_inputs_hash" in derived:
                    derived.pop("graph_metrics_composed_inputs_hash", None)
                    removed = True
                if removed:
                    snapshot_written = True
                    graph_metrics_composed_changed = True
                    graph_metrics_change_reason = "graph_metrics_removed"

            definitions_payload = evaluate_metric_definitions(
                rs,
                composed_payload=composed_payload if composed_available else None,
            )
            definitions_results = definitions_payload.get("results") if isinstance(definitions_payload.get("results"), dict) else {}

            validation_summary = definitions_payload.get("validation_summary") if isinstance(definitions_payload.get("validation_summary"), dict) else None
            if validation_summary and validation_summary.get("definition_count", 0):
                existing_summary = derived.get("metrics_validation_summary") if isinstance(derived.get("metrics_validation_summary"), dict) else None
                existing_hash = derived.get("metrics_validation_hash") if isinstance(derived.get("metrics_validation_hash"), str) else None
                try:
                    summary_hash = hashlib.sha256(canonical_json_bytes(validation_summary)).hexdigest()
                except Exception:
                    summary_hash = None

                if existing_summary != validation_summary or existing_hash != summary_hash:
                    derived["metrics_validation_summary"] = validation_summary
                    if summary_hash:
                        derived["metrics_validation_hash"] = summary_hash
                    else:
                        derived.pop("metrics_validation_hash", None)
                    snapshot_written = True
            else:
                if "metrics_validation_summary" in derived or "metrics_validation_hash" in derived:
                    derived.pop("metrics_validation_summary", None)
                    derived.pop("metrics_validation_hash", None)
                    snapshot_written = True

            current_definition_hashes = {}
            for metric_id, metric_payload in definitions_results.items():
                metric_key = str(metric_id) if metric_id is not None else ""
                if not metric_key:
                    continue
                hash_value = metric_payload.get("definition_hash") if isinstance(metric_payload, dict) else None
                if isinstance(hash_value, str) and hash_value:
                    current_definition_hashes[metric_key] = hash_value
            if definitions_results:
                metrics_store = rs.get("metrics") if isinstance(rs.get("metrics"), dict) else {}
                if not isinstance(rs.get("metrics"), dict):
                    rs["metrics"] = metrics_store
                updated_keys = set()
                for metric_id, metric_payload in definitions_results.items():
                    if metric_payload.get("available"):
                        previous = metrics_store.get(metric_id)
                        if previous != metric_payload:
                            metrics_store[metric_id] = metric_payload
                            snapshot_written = True
                            metric_results_changed = True
                            metrics_changed_ids.add(metric_id)
                    else:
                        if metric_id in metrics_store:
                            metrics_store.pop(metric_id, None)
                            snapshot_written = True
                            metric_results_changed = True
                            metrics_changed_ids.add(metric_id)
                    metrics_event_payloads[metric_id] = dict(metric_payload)
                    updated_keys.add(metric_id)

                # Remove leftover metrics that correspond to definitions no longer present
                for existing_metric in list(metrics_store.keys()):
                    if existing_metric not in updated_keys:
                        metrics_store.pop(existing_metric, None)
                        snapshot_written = True
                        metric_results_changed = True
                        metrics_changed_ids.add(existing_metric)
                        payload = dict(metrics_event_payloads.get(existing_metric) or {})
                        payload["metric_id"] = existing_metric
                        payload["available"] = False
                        payload.setdefault("reason", "definition_removed")
                        metrics_event_payloads[existing_metric] = payload

                derived["metrics_results_hash"] = definitions_payload.get("results_hash")
                derived["metrics_definition_count"] = definitions_payload.get("definition_count", 0)
                derived["metrics_available"] = bool(definitions_payload.get("available"))
            else:
                metrics_store = rs.get("metrics") if isinstance(rs.get("metrics"), dict) else None
                if isinstance(metrics_store, dict):
                    removed_any = False
                    for metric_id in list(metrics_store.keys()):
                        payload = metrics_store.get(metric_id)
                        if isinstance(payload, dict) and payload.get("source") == "graph_metrics_composed":
                            metrics_store.pop(metric_id, None)
                            removed_any = True
                            metric_results_changed = True
                            metrics_changed_ids.add(metric_id)
                            metrics_event_payloads[metric_id] = {
                                "metric_id": metric_id,
                                "available": False,
                                "reason": "metric_removed",
                            }
                    if removed_any:
                        snapshot_written = True
                        if not metrics_store:
                            rs.pop("metrics", None)
                for key in ("metrics_results_hash", "metrics_definition_count", "metrics_available"):
                    if key in derived:
                        derived.pop(key, None)
                        snapshot_written = True

            if current_definition_hashes:
                existing_hashes = derived.get("metrics_definition_hashes") if isinstance(derived.get("metrics_definition_hashes"), dict) else None
                if existing_hashes != current_definition_hashes:
                    derived["metrics_definition_hashes"] = dict(current_definition_hashes)
                    snapshot_written = True
            else:
                if isinstance(derived, dict) and "metrics_definition_hashes" in derived:
                    derived.pop("metrics_definition_hashes", None)
                    snapshot_written = True

            definition_keys = sorted(set(previous_definition_hashes.keys()) | set(current_definition_hashes.keys()))
            for metric_id in definition_keys:
                prev_hash = previous_definition_hashes.get(metric_id)
                curr_hash = current_definition_hashes.get(metric_id)
                if prev_hash == curr_hash:
                    continue
                if prev_hash is None and curr_hash is not None:
                    change_type = "added"
                elif prev_hash is not None and curr_hash is None:
                    change_type = "removed"
                else:
                    change_type = "updated"
                change_entry: Dict[str, Any] = {
                    "metric_id": metric_id,
                    "change_type": change_type,
                }
                if prev_hash is not None:
                    change_entry["previous_hash"] = prev_hash
                if curr_hash is not None:
                    change_entry["current_hash"] = curr_hash
                definition_changes.append(change_entry)
        else:
            if isinstance(rs, dict):
                derived = rs.get("derived") if isinstance(rs.get("derived"), dict) else None
                if isinstance(derived, dict):
                    removed_any = False
                    removed_composed = False
                    for key in (
                        "graph_snapshot",
                        "graph_snapshot_hash",
                        "graph_snapshot_build_info",
                    ):
                        if key in derived:
                            derived.pop(key, None)
                            removed_any = True
                    if "graph_metrics_inputs" in derived or "graph_metrics_inputs_hash" in derived:
                        derived.pop("graph_metrics_inputs", None)
                        derived.pop("graph_metrics_inputs_hash", None)
                        removed_any = True
                    for key in (
                        "graph_metrics_composed",
                        "graph_metrics_composed_hash",
                        "graph_metrics_composed_inputs_hash",
                    ):
                        if key in derived:
                            derived.pop(key, None)
                            removed_any = True
                            removed_composed = True
                    if removed_any:
                        snapshot_written = True
                    if removed_composed:
                        graph_metrics_composed_changed = True
                        graph_metrics_change_reason = "graph_snapshot_missing"
    except Exception:
        snapshot_written = False

    write_success = False
    if snapshot_written:
        try:
            from module_storage import _atomic_write_json

            _atomic_write_json(file_path, data)
            write_success = True
        except Exception:
            write_success = False

    if write_success:
        events: List[Tuple[str, Dict[str, Any]]] = []
        try:
            rs_current = data.get("relational_state")
            derived_current = rs_current.get("derived") if isinstance(rs_current, dict) else None
            target_id_str = data_id
            artifact_paths = _persist_provenance_artifacts(
                target_id=target_id_str,
                relational_state=rs_current if isinstance(rs_current, dict) else None,
            )
            if graph_snapshot_changed and isinstance(derived_current, dict):
                snapshot_event = _build_graph_snapshot_event_payload(
                    target_id_str,
                    derived_current,
                    artifact_paths.get("graph_snapshot"),
                )
                if snapshot_event:
                    events.append(("graph_snapshot_created", snapshot_event))
            if graph_metrics_composed_changed and isinstance(derived_current, dict):
                metrics_event = _build_graph_metrics_event_payload(
                    target_id_str,
                    derived_current,
                    graph_metrics_change_reason,
                    artifact_paths.get("graph_metrics_composed"),
                )
                events.append(("graph_metrics_computed", metrics_event))
            if metric_results_changed:
                metrics_store_current: Dict[str, Any] = {}
                if isinstance(rs_current, dict):
                    existing_metrics = rs_current.get("metrics")
                    if isinstance(existing_metrics, dict):
                        metrics_store_current = {k: dict(v) if isinstance(v, dict) else {} for k, v in existing_metrics.items()}
                for mid in list(metrics_changed_ids):
                    if mid not in metrics_event_payloads:
                        payload = metrics_store_current.get(mid, {})
                        if isinstance(payload, dict) and payload:
                            payload_copy = dict(payload)
                            payload_copy["metric_id"] = mid
                            metrics_event_payloads[mid] = payload_copy
                        else:
                            metrics_event_payloads[mid] = {
                                "metric_id": mid,
                                "available": False,
                                "reason": "metric_removed",
                            }
                events.extend(
                    _build_metric_event_payloads(
                        target_id_str,
                        metrics_event_payloads,
                        metrics_changed_ids,
                        artifact_paths.get("metrics_results"),
                    )
                )
            if definition_changes:
                target_ids = [target_id_str] if target_id_str else []
                definitions_artifact = artifact_paths.get("metrics_definitions")
                for change in definition_changes:
                    metric_id = str(change.get("metric_id", ""))
                    if not metric_id:
                        continue
                    event_payload: Dict[str, Any] = {
                        "target_ids": target_ids,
                        "metric_id": metric_id,
                        "change_type": str(change.get("change_type", "")),
                    }
                    prev_hash = change.get("previous_hash")
                    curr_hash = change.get("current_hash")
                    if isinstance(prev_hash, str) and prev_hash:
                        event_payload["previous_hash"] = prev_hash
                    if isinstance(curr_hash, str) and curr_hash:
                        event_payload["current_hash"] = curr_hash
                    if definitions_artifact:
                        event_payload["artifact_path"] = definitions_artifact
                    events.append(("metric_definition_changed", event_payload))
        except Exception:
            events = []
        if events:
            _append_provenance_events(events)

    if objectives is None:
        try:
            from module_objectives import get_objectives_by_label
            objectives = get_objectives_by_label("measurement") or ["measurement"]
        except Exception:
            objectives = ["measurement"]

    sim_score = similarity(content, "current_subject", "long_term_index", exclude_id=data_id)
    fam = familiarity(data_id, data.get("occurrence_count", 0), data.get("labels", []))
    use = usefulness(content, objectives, "current_activity")
    syn = synthesis_potential(content, "current_subject", [], objectives, "long_term_index")
    obj_rel = compare_against_objectives(content, objectives)

    repeat_signal = {
        "count": data.get("occurrence_count", 0),
        "stability": ((data.get("repetition_profile") or {}).get("stability_score", 0.5))
    }
    similarity_signal = sim_score
    usefulness_signal = use
    contradiction_signal = (obj_rel == "conflict")

    # Optional focus/concentration nudges (deterministic, small, and capped).
    # This does not change behavior unless focus_state is explicitly provided.
    try:
        if isinstance(focus_state, dict):
            active = focus_state.get("active_objectives")
            if isinstance(active, list) and active:
                # If we have any active objectives and we're already aligned, bias usefulness to useful_now.
                if obj_rel == "aligned":
                    usefulness_signal = "useful_now"
                # Small similarity boost when focus is active.
                similarity_signal = min(1.0, float(similarity_signal) + 0.1)
                # Increase contradiction sensitivity only when explicitly conflicting.
                contradiction_signal = bool(obj_rel == "conflict")
    except Exception:
        pass

    # Weighted arbiter inputs (tolerant to missing keys)
    wcfg = get_measurement_weights()
    recommended_actions = []
    reasons = []
    if contradiction_signal:
        recommended_actions.append("contradiction_resolve")
        reasons.append("Objective conflict detected")
    if usefulness_signal == "useful_now" and similarity_signal >= 0.8:
        recommended_actions.append("synthesis")
        reasons.append("High similarity and immediate usefulness")
    if repeat_signal["count"] > 1 and repeat_signal["stability"] >= 0.6:
        recommended_actions.append("review")
        reasons.append("Stable repeats warrant reinforcement")

    conflicts = []
    # conflict: synthesis and contradiction_resolve at same time
    if "synthesis" in recommended_actions and "contradiction_resolve" in recommended_actions:
        conflicts.append({"actions": ["synthesis","contradiction_resolve"], "reason": "mutually exclusive"})

    # Compute weighted score for decisive recommendation
    score = (
        wcfg['similarity'] * float(similarity_signal) +
        wcfg['usefulness'] * (1.0 if usefulness_signal == 'useful_now' else 0.0) +
        wcfg['repeat'] * float(repeat_signal.get('stability', 0.0)) +
        wcfg['contradiction'] * (1.0 if contradiction_signal else 0.0)
    )
    if 'synthesis' in recommended_actions:
        score += wcfg.get('synthesis_bias', 0.0)
    if 'review' in recommended_actions:
        score += wcfg.get('review_bias', 0.0)
    decisive = None
    if contradiction_signal and score < 0:
        decisive = 'contradiction_resolve'
    elif (usefulness_signal == 'useful_now' and similarity_signal >= 0.8) and score >= 0.6:
        decisive = 'synthesis'
    elif score >= 0.3:
        decisive = 'review'
    return {
        "repeat_signal": repeat_signal,
        "similarity_signal": similarity_signal,
        "usefulness_signal": usefulness_signal,
        "contradiction_signal": contradiction_signal,
        "recommended_actions": recommended_actions,
        "decisive_recommendation": decisive,
        "weighted_score": score,
        "reasons": reasons,
        "conflicts": conflicts,
        "objective_relation": obj_rel,
        # Optional additive field: uncertainty payloads for numeric signals.
        # JSON-friendly: { value, variance, provenance }
        "uncertainties": _build_uncertainties(
            data_id=data_id,
            similarity_signal=similarity_signal,
            weighted_score=score,
            repeat_stability=float(repeat_signal.get('stability', 0.0)),
        ),
    }


def _build_uncertainties(*, data_id: str, similarity_signal: float, weighted_score: float, repeat_stability: float):
    """Create deterministic, structure-only uncertainty objects for numeric signals."""
    try:
        from module_uncertainty import now_ts

        ts = float(now_ts())
    except Exception:
        ts = 0.0

    def _u(value: float, sigma: float, metric: str):
        s = max(0.0, float(sigma))
        return {
            'value': float(value),
            'variance': float(s * s),
            'provenance': {
                'metric': str(metric),
                'target_id': str(data_id),
                'ts': float(ts),
                'method': 'heuristic',
            },
        }

    # Heuristic uncertainty: higher certainty near extremes for similarity; moderate baseline for score.
    sim = float(similarity_signal)
    sim_sigma = 0.05 + 0.15 * float(min(sim, 1.0 - sim))
    score_sigma = 0.15
    rep_sigma = 0.10

    return {
        'similarity_signal': _u(sim, sim_sigma, 'similarity_signal'),
        'weighted_score': _u(float(weighted_score), score_sigma, 'weighted_score'),
        'repeat_stability': _u(float(repeat_stability), rep_sigma, 'repeat_stability'),
    }