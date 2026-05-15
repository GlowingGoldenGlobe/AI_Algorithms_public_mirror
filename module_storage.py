import hashlib
import os
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from module_tools import (
    validate_record,
    validate_relational_state,
    sanitize_id,
    safe_join,
    _load_config,
    canonical_json_bytes,
    _ts,
)

# Resolve workspace root dynamically from this file's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = BASE_DIR

RETAINED_STORAGE_ROOTS = (
    ("semantic", os.path.join("LongTermStore", "Semantic")),
    ("procedural", os.path.join("LongTermStore", "Procedural")),
    ("event", os.path.join("LongTermStore", "Events")),
    ("backup", os.path.join("LongTermStore", "Backups")),
    ("provenance_artifact", os.path.join("LongTermStore", "Provenance", "Artifacts")),
)


def _load_json_dict(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _ensure_relational_state(record: Dict[str, Any]) -> None:
    """Ensure a canonical, empty relational_state exists on the record.

    This is Stage-1 safe: it adds structure but does not change decisions.
    """
    rs = record.get("relational_state")
    if not isinstance(rs, dict):
        rs = {}
        record["relational_state"] = rs
    rs.setdefault("entities", [])
    rs.setdefault("relations", [])
    rs.setdefault("constraints", [])
    rs.setdefault("objective_links", [])
    rs.setdefault("spatial_measurement", None)
    rs.setdefault("decision_trace", {})
    rs.setdefault("focus_snapshot", None)


def _now_ts() -> str:
    """Return a timestamp string (deterministic when enabled)."""
    return _ts()


def _get_retention_limits() -> Dict[str, int]:
    cfg = _load_config() or {}
    block = cfg.get("retention_limits", {}) if isinstance(cfg, dict) else {}
    if not isinstance(block, dict):
        block = {}
    max_timestamps = block.get("max_record_timestamps", 128)
    try:
        max_timestamps = int(max_timestamps)
    except Exception:
        max_timestamps = 128
    return {
        "max_record_timestamps": max(0, max_timestamps),
    }


def resolve_path(category: str) -> str:
    """Map category to subdirectory under ROOT."""
    mapping = {
        "temporary": "TemporaryQueue",
        "temporary_root": "TemporaryQueue",
        "active": "ActiveSpace",
        "active_space_dir": "ActiveSpace",
        "holding": "LongTermStore",
        "event": os.path.join("LongTermStore", "Events"),
        "semantic": os.path.join("LongTermStore", "Semantic"),
        "procedural": os.path.join("LongTermStore", "Procedural"),
    }
    relative_path = mapping.get(category, "LongTermStore")
    cfg = _load_config() or {}
    failover = cfg.get("storage_failover", {}) if isinstance(cfg, dict) else {}
    if (
        isinstance(failover, dict)
        and bool(failover.get("enabled", False))
        and str(failover.get("mode") or "local").lower() == "external"
        and category in {"holding", "semantic", "procedural", "event"}
    ):
        external_root = str(failover.get("external_root") or "").strip()
        if external_root:
            return safe_join(os.path.abspath(external_root), relative_path)
    return os.path.join(ROOT, relative_path)

def _atomic_write_json(target_path: str, data: Dict[str, Any]) -> None:
    tmp_path = target_path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, target_path)

def _backup_existing(file_path: str) -> None:
    if not os.path.exists(file_path):
        return
    base = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base, 'LongTermStore', 'Backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = None
    try:
        ts_str = _now_ts()
        parsed = None
        try:
            ts_norm = ts_str.replace('Z', '+00:00') if isinstance(ts_str, str) else ''
            parsed = datetime.fromisoformat(ts_norm) if ts_norm else None
        except Exception:
            parsed = None
        if parsed is None:
            parsed = datetime.fromtimestamp(time.time(), timezone.utc)
        ts = parsed.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    except Exception:
        ts = datetime.fromtimestamp(time.time(), timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = os.path.basename(file_path)
    backup_name = f"{name}.{ts}.bak"
    backup_path = os.path.join(backup_dir, backup_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    except Exception:
        pass


def _collect_directory_storage_stats(directory_path: str) -> Dict[str, Any]:
    exists = os.path.isdir(directory_path)
    if not exists:
        return {
            "exists": False,
            "file_count": 0,
            "json_file_count": 0,
            "total_bytes": 0,
        }

    file_count = 0
    json_file_count = 0
    total_bytes = 0
    for root, dirnames, filenames in os.walk(directory_path):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            file_count += 1
            if filename.lower().endswith(".json"):
                json_file_count += 1
            file_path = os.path.join(root, filename)
            try:
                total_bytes += int(os.path.getsize(file_path))
            except OSError:
                continue

    return {
        "exists": True,
        "file_count": int(file_count),
        "json_file_count": int(json_file_count),
        "total_bytes": int(total_bytes),
    }


def build_retained_storage_pressure_snapshot(*, root_path: Optional[str] = None) -> Dict[str, Any]:
    base_root = os.path.abspath(root_path or ROOT)
    roots = []
    total_file_count = 0
    total_json_file_count = 0
    total_bytes = 0

    for root_id, relative_path in RETAINED_STORAGE_ROOTS:
        absolute_path = safe_join(base_root, relative_path)
        stats = _collect_directory_storage_stats(absolute_path)
        entry = {
            "root_id": root_id,
            "relative_path": str(relative_path).replace("\\", "/"),
            "exists": bool(stats["exists"]),
            "file_count": int(stats["file_count"]),
            "json_file_count": int(stats["json_file_count"]),
            "total_bytes": int(stats["total_bytes"]),
        }
        roots.append(entry)
        total_file_count += entry["file_count"]
        total_json_file_count += entry["json_file_count"]
        total_bytes += entry["total_bytes"]

    candidate_partition_roots = [entry["root_id"] for entry in roots if entry["file_count"] > 0]
    largest_root = None
    for entry in roots:
        if largest_root is None or entry["total_bytes"] > largest_root["total_bytes"] or (
            entry["total_bytes"] == largest_root["total_bytes"] and entry["root_id"] < largest_root["root_id"]
        ):
            largest_root = entry

    snapshot = {
        "schema_version": "retained_storage_pressure_snapshot_v1",
        "snapshot_role": "retained_storage_pressure",
        "authoritative": False,
        "current_serving": False,
        "additive_only": True,
        "roots": roots,
        "totals": {
            "root_count": len(roots),
            "file_count": int(total_file_count),
            "json_file_count": int(total_json_file_count),
            "total_bytes": int(total_bytes),
        },
        "candidate_partition_roots": candidate_partition_roots,
        "candidate_partition_count": len(candidate_partition_roots),
        "storage_density_bytes_per_file": round(total_bytes / total_file_count, 6) if total_file_count else 0.0,
        "largest_root_by_bytes": {
            "root_id": largest_root["root_id"],
            "relative_path": largest_root["relative_path"],
            "file_count": largest_root["file_count"],
            "total_bytes": largest_root["total_bytes"],
        } if isinstance(largest_root, dict) else None,
        "retention_window_summary": {
            "roots_with_files": len(candidate_partition_roots),
            "empty_roots": len([entry for entry in roots if entry["file_count"] == 0]),
        },
    }
    snapshot["snapshot_hash"] = hashlib.sha256(
        canonical_json_bytes({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    ).hexdigest()
    return snapshot


def _extract_measurement_hash_from_record(record: Dict[str, Any]) -> str:
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    spatial_snapshots = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}

    for candidate in (
        derived.get("spatial_measurement_hash"),
        spatial_snapshots.get("measurement_hash"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    measurement = relational_state.get("spatial_measurement")
    if isinstance(measurement, dict) and measurement:
        try:
            return hashlib.sha256(canonical_json_bytes(measurement)).hexdigest()
        except Exception:
            return ""
    return ""


def _extract_request_id_from_record(record: Dict[str, Any]) -> str:
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    composition_request = artifacts.get("composition_request") if isinstance(artifacts.get("composition_request"), dict) else {}
    composition_response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else {}

    for candidate in (
        derived.get("composition_request_id"),
        composition_request.get("request_id"),
        composition_response.get("request_id"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _extract_scene_validation_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    decision_trace = relational_state.get("decision_trace") if isinstance(relational_state.get("decision_trace"), dict) else {}
    scene_validation = (
        decision_trace.get("scene_validation")
        if isinstance(decision_trace.get("scene_validation"), dict)
        else {}
    )
    if not scene_validation:
        artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
        validation_summary = None
        for key in ("composition_validation_summary", "validation_summary"):
            candidate = artifacts.get(key)
            if isinstance(candidate, dict):
                validation_summary = candidate
                break
        checks = validation_summary.get("checks") if isinstance(validation_summary, dict) and isinstance(validation_summary.get("checks"), list) else []
        failed = len([item for item in checks if isinstance(item, dict) and str(item.get("status") or "") == "fail"])
        warnings = len([item for item in checks if isinstance(item, dict) and str(item.get("status") or "") == "warn"])
        passed = len([item for item in checks if isinstance(item, dict) and str(item.get("status") or "") == "pass"])
        return {
            "present": isinstance(validation_summary, dict),
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
            "warnings": max(
                warnings,
                len(validation_summary.get("warnings") or [])
                if isinstance(validation_summary, dict) and isinstance(validation_summary.get("warnings"), list)
                else 0,
            ),
            "has_hard_failure": bool(isinstance(validation_summary, dict) and str(validation_summary.get("status") or "") == "fail"),
        }
    return {
        "present": bool(scene_validation.get("present")),
        "total_checks": int(scene_validation.get("total_checks", 0) or 0),
        "passed": int(scene_validation.get("passed", 0) or 0),
        "failed": int(scene_validation.get("failed", 0) or 0),
        "warnings": int(scene_validation.get("warnings", 0) or 0),
        "has_hard_failure": bool(scene_validation.get("has_hard_failure")),
    }


def _validation_summary_is_passed(summary: Dict[str, Any]) -> bool:
    return bool(summary.get("present")) and not bool(summary.get("has_hard_failure")) and int(summary.get("failed", 0) or 0) <= 0


def _extract_bridge_output_source(record: Dict[str, Any]) -> Optional[str]:
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    bridge_outputs = relational_state.get("bridge_outputs") if isinstance(relational_state.get("bridge_outputs"), list) else []
    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        source = payload.get("source")
        if isinstance(source, str) and source.strip():
            return source.strip()
    return None


def _extract_snapshot_relative_path(record: Dict[str, Any]) -> Optional[str]:
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    spatial_snapshots = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
    latest = spatial_snapshots.get("latest") if isinstance(spatial_snapshots.get("latest"), dict) else {}
    relative_path = latest.get("relative_path")
    if isinstance(relative_path, str) and relative_path.strip():
        return relative_path.replace("\\", "/")
    return None


def _extract_latest_spatial_memory_measurement(spatial_memory_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(spatial_memory_payload, dict):
        return None
    measurements = spatial_memory_payload.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return None
    latest = measurements[-1]
    return latest if isinstance(latest, dict) else None


def build_ai_brain_durable_memory_contract_snapshot(
    *,
    root_path: Optional[str] = None,
    measurement_record: Optional[Dict[str, Any]] = None,
    joined_provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_root = os.path.abspath(root_path or ROOT)
    ai_brain_dir = safe_join(base_root, "AI_Brain")
    brain_state_path = safe_join(ai_brain_dir, "brain_state.json")
    spatial_memory_dir = safe_join(ai_brain_dir, "memory")
    spatial_memory_path = safe_join(spatial_memory_dir, "spatial_memory.json")

    brain_state = _load_json_dict(brain_state_path)
    spatial_memory = _load_json_dict(spatial_memory_path)
    latest_measurement = _extract_latest_spatial_memory_measurement(spatial_memory)
    joined = joined_provenance if isinstance(joined_provenance, dict) else {}
    record = measurement_record if isinstance(measurement_record, dict) else {}

    summary: Dict[str, Any] = {
        "status": "missing",
        "brain_state_present": False,
        "spatial_memory_present": False,
        "spatial_memory_measurement_count": 0,
        "contract_paths": {
            "brain_state": os.path.relpath(brain_state_path, base_root).replace("\\", "/"),
            "spatial_memory": os.path.relpath(spatial_memory_path, base_root).replace("\\", "/"),
        },
        "alignment": {
            "status": "missing",
            "durable_contract_explicit": False,
            "validated_measurement_present": False,
            "validated_measurement_preserved": False,
            "measurement_hash_matches_semantic_record": False,
            "request_id_matches_semantic_record": False,
            "record_id_matches_semantic_record": False,
            "brain_state_measurement_hash_present": False,
            "spatial_memory_measurement_hash_present": False,
            "validation_summary_present": False,
            "validation_passed": False,
            "bridge_output_present": False,
            "snapshot_present": False,
            "summary": "durable spatial-memory contract is not present",
        },
    }

    brain_last_measurement = brain_state.get("last_measurement") if isinstance(brain_state, dict) and isinstance(brain_state.get("last_measurement"), dict) else None
    if brain_last_measurement:
        summary["brain_state_present"] = True

    if isinstance(spatial_memory, dict):
        summary["spatial_memory_present"] = True
        measurements = spatial_memory.get("measurements")
        if isinstance(measurements, list):
            summary["spatial_memory_measurement_count"] = len(measurements)

    if summary["brain_state_present"] and summary["spatial_memory_present"]:
        summary["status"] = "complete"
    elif summary["brain_state_present"] or summary["spatial_memory_present"]:
        summary["status"] = "partial"

    semantic_record_id = str(record.get("id") or "").strip()
    semantic_measurement_hash = _extract_measurement_hash_from_record(record)
    semantic_request_id = _extract_request_id_from_record(record)
    validation_summary = _extract_scene_validation_summary(record)
    validation_passed = _validation_summary_is_passed(validation_summary)
    bridge_output_source = _extract_bridge_output_source(record)
    snapshot_relative_path = _extract_snapshot_relative_path(record)

    joined_measurement_hash = joined.get("measurement_hash") if isinstance(joined.get("measurement_hash"), str) else None
    joined_request_id = (
        joined.get("join_key")
        if str(joined.get("join_key_type") or "") == "request_id" and isinstance(joined.get("join_key"), str)
        else None
    )
    joined_bridge_source = joined.get("bridge_output_source") if isinstance(joined.get("bridge_output_source"), str) else None

    expected_measurement_hash = joined_measurement_hash or semantic_measurement_hash
    expected_request_id = joined_request_id or semantic_request_id

    brain_measurement_hash = ""
    if isinstance(brain_state, dict):
        brain_measurement_hash = str(brain_state.get("last_measurement_hash") or "").strip()
        if not brain_measurement_hash and isinstance(brain_last_measurement, dict) and brain_last_measurement:
            try:
                brain_measurement_hash = hashlib.sha256(canonical_json_bytes(brain_last_measurement)).hexdigest()
            except Exception:
                brain_measurement_hash = ""
    spatial_measurement_hash = ""
    if isinstance(latest_measurement, dict):
        spatial_measurement_hash = str(latest_measurement.get("measurement_hash") or "").strip()
        if not spatial_measurement_hash:
            try:
                spatial_measurement_hash = hashlib.sha256(
                    canonical_json_bytes(
                        {
                            key: value
                            for key, value in latest_measurement.items()
                            if key
                            not in {
                                "measurement_hash",
                                "record_id",
                                "request_id",
                                "commit_ts",
                                "validation_summary",
                                "bridge_output_source",
                                "snapshot_relative_path",
                                "durable_contract",
                            }
                        }
                    )
                ).hexdigest()
            except Exception:
                spatial_measurement_hash = ""

    brain_request_id = str(brain_state.get("last_measurement_request_id") or "").strip() if isinstance(brain_state, dict) else ""
    spatial_request_id = str(latest_measurement.get("request_id") or "").strip() if isinstance(latest_measurement, dict) else ""
    brain_record_id = str(brain_state.get("last_measurement_record_id") or "").strip() if isinstance(brain_state, dict) else ""
    spatial_record_id = str(latest_measurement.get("record_id") or "").strip() if isinstance(latest_measurement, dict) else ""

    explicit_in_brain_state = bool(brain_measurement_hash and brain_request_id and brain_record_id)
    explicit_in_spatial_memory = bool(
        isinstance(latest_measurement, dict)
        and spatial_measurement_hash
        and spatial_request_id
        and spatial_record_id
        and isinstance(latest_measurement.get("validation_summary"), dict)
    )

    measurement_hash_matches = bool(
        expected_measurement_hash
        and brain_measurement_hash
        and spatial_measurement_hash
        and expected_measurement_hash == brain_measurement_hash == spatial_measurement_hash
    )
    request_id_matches = bool(
        expected_request_id
        and brain_request_id
        and spatial_request_id
        and expected_request_id == brain_request_id == spatial_request_id
    )
    record_id_matches = bool(
        semantic_record_id
        and brain_record_id
        and spatial_record_id
        and semantic_record_id == brain_record_id == spatial_record_id
    )
    validated_measurement_present = bool(validation_summary.get("present"))
    validation_summary_present = bool(
        isinstance(latest_measurement, dict)
        and isinstance(latest_measurement.get("validation_summary"), dict)
    )
    latest_validation_summary = (
        latest_measurement.get("validation_summary")
        if isinstance(latest_measurement, dict) and isinstance(latest_measurement.get("validation_summary"), dict)
        else {}
    )
    validated_measurement_preserved = bool(
        summary["brain_state_present"]
        and summary["spatial_memory_present"]
        and validated_measurement_present
        and validation_passed
        and validation_summary_present
        and _validation_summary_is_passed(latest_validation_summary)
        and (measurement_hash_matches or request_id_matches)
        and record_id_matches
    )

    if validated_measurement_preserved:
        alignment_status = "aligned"
        alignment_summary = "validated measurement is explicitly preserved in brain_state.json and spatial_memory.json"
    elif summary["status"] == "complete" and (measurement_hash_matches or request_id_matches or record_id_matches):
        alignment_status = "partial"
        alignment_summary = "durable files are present and linked to the semantic measurement, but validation preservation is not fully explicit"
    elif summary["status"] != "missing":
        alignment_status = "partial"
        alignment_summary = "durable files are present, but semantic measurement alignment remains incomplete"
    else:
        alignment_status = "missing"
        alignment_summary = "durable spatial-memory contract is not present"

    summary["alignment"] = {
        "status": alignment_status,
        "durable_contract_explicit": bool(explicit_in_brain_state and explicit_in_spatial_memory),
        "validated_measurement_present": validated_measurement_present,
        "validated_measurement_preserved": validated_measurement_preserved,
        "measurement_hash_matches_semantic_record": measurement_hash_matches,
        "request_id_matches_semantic_record": request_id_matches,
        "record_id_matches_semantic_record": record_id_matches,
        "brain_state_measurement_hash_present": bool(brain_measurement_hash),
        "spatial_memory_measurement_hash_present": bool(spatial_measurement_hash),
        "validation_summary_present": validation_summary_present,
        "validation_passed": bool(validation_passed and _validation_summary_is_passed(latest_validation_summary)),
        "bridge_output_present": bool(bridge_output_source or joined_bridge_source),
        "snapshot_present": bool(snapshot_relative_path or joined.get("snapshot_path")),
        "brain_state_request_id": brain_request_id or None,
        "spatial_memory_request_id": spatial_request_id or None,
        "brain_state_record_id": brain_record_id or None,
        "spatial_memory_record_id": spatial_record_id or None,
        "measurement_hash": expected_measurement_hash or None,
        "bridge_output_source": bridge_output_source or joined_bridge_source,
        "snapshot_relative_path": snapshot_relative_path or joined.get("snapshot_path"),
        "summary": alignment_summary,
    }
    return summary

def store_information(data_id: str, content, category: str):
    """Store information permanently, increment occurrence count if already exists.
    Includes schema_version, validation, atomic writes, and backups.
    """
    data_id = sanitize_id(data_id)
    path = resolve_path(category)
    os.makedirs(path, exist_ok=True)
    file_path = safe_join(path, f"{data_id}.json")

    schema_name = 'semantic' if category == 'semantic' else ('event' if category == 'event' else 'semantic')

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            record = json.load(f)
        record["occurrence_count"] = int(record.get("occurrence_count", 0)) + 1
        # ensure category present for schema validation
        record.setdefault("category", category)
        now_ts = _now_ts()
        timestamps = record.get("timestamps")
        if not isinstance(timestamps, list):
            timestamps = []
            record["timestamps"] = timestamps
        timestamps.append(now_ts)
        max_timestamps = _get_retention_limits().get("max_record_timestamps", 128)
        if max_timestamps > 0 and len(timestamps) > max_timestamps:
            del timestamps[:-max_timestamps]
        # repetition profile basics
        rp = record.setdefault("repetition_profile", {})
        rp["first_seen_ts"] = rp.get("first_seen_ts") or now_ts
        rp["last_seen_ts"] = now_ts
        # simplistic stability: increase slightly on repeat
        rp["stability_score"] = min(1.0, float(rp.get("stability_score", 0.5)) + 0.05)
        # intervals summary (requires previous timestamp)
        prev_ts = record["timestamps"][max(0, len(record["timestamps"]) - 2)] if len(record["timestamps"]) >= 2 else now_ts
        try:
            from datetime import datetime as _dt
            dt_prev = _dt.fromisoformat(prev_ts.replace('Z',''))
            dt_now = _dt.fromisoformat(now_ts.replace('Z',''))
            interval_sec = int((dt_now - dt_prev).total_seconds())
            arr = rp.setdefault("intervals_sec", [])
            arr.append(interval_sec)
            if len(arr) > 20:
                arr[:] = arr[-20:]
            rp["intervals_summary"] = {
                "min": min(arr) if arr else 0,
                "avg": (sum(arr)/len(arr)) if arr else 0,
                "max": max(arr) if arr else 0
            }
        except Exception:
            pass
        # contradictions registry stub
        record.setdefault("contradictions", [])
        record.setdefault("schema_version", "1.0")

        if schema_name == 'semantic':
            _ensure_relational_state(record)
            if not validate_relational_state(record.get('relational_state')):
                return f"Validation failed for relational_state: {data_id}"
        # description upgrade (simple merge)
        try:
            from module_tools import describe
            desc = describe(content, context=None)
            prev = record.get("description", {})
            # merge claims (unique by tuple)
            prev_claims = {(c.get('subject'), c.get('predicate'), c.get('object')) for c in prev.get('claims', [])}
            new_claims = [c for c in desc.get('claims', []) if (c.get('subject'), c.get('predicate'), c.get('object')) not in prev_claims]
            prev.setdefault('claims', []).extend(new_claims)
            record["description"] = prev
            record["description_ts"] = now_ts
        except Exception:
            pass
        _backup_existing(file_path)
        if not validate_record(record, schema_name):
            return f"Validation failed for existing record: {data_id}"
        _atomic_write_json(file_path, record)
        # incremental index update for semantic records
        if category == 'semantic':
            try:
                from module_tools import build_semantic_index
                build_semantic_index()
            except Exception:
                pass
    else:
        record = {
            "id": data_id,
            "category": category,
            "content": content,
            "occurrence_count": 1,
            "timestamps": [_now_ts()],
            "labels": [],
            "schema_version": "1.0"
        }

        if schema_name == 'semantic':
            _ensure_relational_state(record)
            if not validate_relational_state(record.get('relational_state')):
                return f"Validation failed for relational_state: {data_id}"
        # initial description
        try:
            from module_tools import describe
            record["description"] = describe(content, context=None)
            record["description_ts"] = record["timestamps"][0]
        except Exception:
            pass
        if isinstance(content, dict):
            provenance = {
                "run_id": content.get("run_id"),
                "module": content.get("module")
            }
            record["metadata"] = {
                "source_chain": content.get("source_chain", []),
                "labels": content.get("tags", []),
                "provenance": provenance
            }
        else:
            # minimal provenance when content is primitive
            record["metadata"] = {
                "source_chain": [],
                "labels": [],
                "provenance": {"run_id": None, "module": None}
            }
        if not validate_record(record, schema_name):
            return f"Validation failed for new record: {data_id}"
        _atomic_write_json(file_path, record)
        if category == 'semantic':
            try:
                from module_tools import build_semantic_index
                build_semantic_index()
            except Exception:
                pass

    return f"Stored {data_id} in {path}"

def retrieve_information(criteria: str):
    """Retrieve information by criteria (recent, current, or search)."""
    # For simplicity, just demonstrate search in LongTermStore
    search_path = os.path.join(ROOT, "LongTermStore")
    results = []
    for root, _, files in os.walk(search_path):
        for file in files:
            if criteria.lower() in file.lower():
                results.append(os.path.join(root, file))
    return results


def store_and_get_path(data_id: str, content, category: str) -> Dict[str, Any]:
    """Wrapper that stores information and returns a structured status with path.

    Does not change store_information signature for existing callers.
    Returns: {status: 'ok'|'error', path: <file_path>, message: <text>}
    """
    try:
        msg = store_information(data_id, content, category)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = safe_join(resolve_path(category), f"{sanitize_id(data_id)}.json")
        status = 'ok' if isinstance(msg, str) and msg.startswith('Stored') else 'ok'
        return {"status": status, "path": path, "message": msg}
    except Exception as e:
        return {"status": "error", "path": None, "message": str(e)}


def _provenance_log_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prov_dir = safe_join(base_dir, os.path.join('LongTermStore', 'Provenance'))
    os.makedirs(prov_dir, exist_ok=True)
    return safe_join(prov_dir, 'provenance_log.json')


def load_provenance_log() -> list[dict[str, Any]]:
    """Load the global provenance log.

    Returns an empty list if missing or unreadable.
    """
    path = _provenance_log_path()
    try:
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict)]
    except Exception:
        pass
    return []


def save_provenance_log(log: list[dict[str, Any]]) -> None:
    """Persist the global provenance log with atomic write."""
    path = _provenance_log_path()
    tmp_path = path + '.tmp'
    data = [e for e in (log or []) if isinstance(e, dict)]
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _provenance_artifacts_root() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    artifacts_dir = safe_join(base_dir, os.path.join('LongTermStore', 'Provenance', 'Artifacts'))
    os.makedirs(artifacts_dir, exist_ok=True)
    return artifacts_dir


def _sanitize_for_artifact(component: Optional[str], *, fallback: str) -> str:
    candidate = str(component) if isinstance(component, str) and component else fallback
    try:
        return sanitize_id(candidate)
    except Exception:
        digest = hashlib.sha256(candidate.encode('utf-8')).hexdigest()[:24]
        return sanitize_id(digest)


def _cleanup_empty_dirs(start_dir: str, root_stop: str) -> None:
    current = os.path.abspath(start_dir)
    stop = os.path.abspath(root_stop)
    while current.startswith(stop):
        if current == stop:
            break
        try:
            os.rmdir(current)
        except OSError:
            break
        current = os.path.dirname(current)


def write_provenance_artifact(
    *,
    target_id: str,
    artifact_name: str,
    payload: Optional[Any],
    tick_id: Optional[str] = None,
) -> Optional[str]:
    """Persist or remove a canonical provenance artifact.

    - Canonical location: LongTermStore/Provenance/Artifacts/<target>/<tick>/<artifact>.json
    - Uses canonical_json_bytes for deterministic serialization when payload provided.
    - Removes the artifact file (and prunes empty directories) when payload is None.
    """

    try:
        artifacts_root = _provenance_artifacts_root()
        safe_target = _sanitize_for_artifact(target_id, fallback='unknown')
        safe_tick = _sanitize_for_artifact(tick_id, fallback=safe_target) if tick_id else safe_target
        safe_artifact = _sanitize_for_artifact(artifact_name, fallback='artifact')
        target_dir = safe_join(artifacts_root, os.path.join(safe_target, safe_tick))
        file_path = safe_join(target_dir, f"{safe_artifact}.json")

        if payload is None:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    return None
            _cleanup_empty_dirs(target_dir, artifacts_root)
            return None

        os.makedirs(target_dir, exist_ok=True)

        serialized = canonical_json_bytes(payload)
        try:
            with open(file_path, 'rb') as existing:
                if existing.read() == serialized:
                    return file_path
        except FileNotFoundError:
            pass

        tmp_path = file_path + '.tmp'
        with open(tmp_path, 'wb') as fh:
            fh.write(serialized)
        os.replace(tmp_path, file_path)
        return file_path
    except Exception:
        return None
