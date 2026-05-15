# module_scheduler.py
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any

from module_metrics import build_learning_readiness_verdict, build_learning_sandbox_activation_report
from module_tools import safe_join, validate_record

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_cfg():
    try:
        with open(os.path.join(_BASE_DIR, 'config.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _deterministic_now():
    cfg = _load_cfg() or {}
    det = cfg.get('determinism', {})
    if det.get('deterministic_mode'):
        fixed = det.get('fixed_timestamp')
        if fixed:
            ts = str(fixed)
            # Accept Zulu by converting Z to +00:00
            if ts.endswith('Z'):
                ts = ts[:-1] + '+00:00'
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                return datetime(1970, 1, 1)
        return datetime(1970, 1, 1)
    return datetime.fromtimestamp(time.time())

ROOT = _BASE_DIR
TASK_TYPES = {"synthesis","review","evidence_gather","contradiction_resolve","objective_refine"}
MAPPED_COMPOSITION_SLICES = {
    "work_selection_queue_admission",
    "asset_environment_grounding",
    "retained_memory_persistence",
    "validation_constraint_review",
    "scene_execution_measurement",
    "active_space_execution",
}
COMPOSITION_ROUTING_TARGET_ALIASES = {
    "3d_composition",
    "blender_composition",
    "composition_request",
    "composition_runtime",
    "mapped_workload",
}
_PRIORITY_RANK = {"high": 0, "normal": 1, "low": 2}
_MAPPED_SLICE_FALLBACK_CARRIER_IDS = {
    "work_selection_queue_admission": ["tier1_main_cognition", "active_space_support"],
    "asset_environment_grounding": ["reference_grounding_support", "retained_memory_support"],
    "retained_memory_persistence": ["retained_memory_support", "tier1_main_cognition", "schedule_mirror"],
    "validation_constraint_review": ["correctness_constraint_verification_support"],
    "scene_execution_measurement": ["active_space_support", "spatial_context_relation_support"],
    "active_space_execution": ["active_space_support", "spatial_context_relation_support"],
}
_PILOT_FALLBACK_CARRIER_IDS = [
    "tier1_main_cognition",
    "active_space_support",
    "spatial_context_relation_support",
]
_PILOT_FALLBACK_ACTION_IDS = [
    "bounded_objective_selection",
    "packet_preparation_support",
    "scene_execution_measurement",
]


def _normalize_route_token(value: Any, *, default: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip().lower()).strip("_")
    return normalized or default


def _atomic_write_record(file_path: str, record: dict[str, Any]) -> None:
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    _replace_with_retry(tmp_path, file_path)


def _replace_with_retry(
    tmp_path: str,
    target_path: str,
    *,
    attempts: int = 10,
    base_delay_sec: float = 0.05,
    max_delay_sec: float = 0.25,
) -> None:
    last_error: PermissionError | None = None
    for attempt in range(attempts):
        try:
            os.replace(tmp_path, target_path)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt >= attempts - 1:
                raise
            delay_sec = min(float(max_delay_sec), float(base_delay_sec) * (2 ** attempt))
            time.sleep(delay_sec)
    if last_error is not None:
        raise last_error


def _routing_targets(task: dict[str, Any]) -> list[str]:
    normalized: list[str] = []
    targets = task.get("targets")
    if not isinstance(targets, list):
        return normalized
    for raw in targets:
        if not isinstance(raw, str) or not raw.strip():
            continue
        normalized.append(_normalize_route_token(raw, default="target"))
    return normalized


def _task_priority_rank(task: dict[str, Any]) -> tuple[int, str]:
    priority = _normalize_route_token(task.get("priority"), default="normal")
    return (_PRIORITY_RANK.get(priority, 99), priority)


def _record_objective_text(record: dict[str, Any], *, task: dict[str, Any] | None = None) -> str:
    parts: list[str] = []
    for key in ("content", "summary", "title", "category"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    labels = record.get("labels")
    if isinstance(labels, list):
        parts.extend(str(value).strip() for value in labels if isinstance(value, str) and value.strip())
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("objective", "objective_hint", "scene_context"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    if isinstance(task, dict):
        why = task.get("why")
        if isinstance(why, str) and why.strip():
            parts.append(why.strip())
        parts.extend(_routing_targets(task))
    deduped: list[str] = []
    seen: set[str] = set()
    for value in parts:
        normalized = str(value).strip()
        folded = normalized.lower()
        if normalized and folded not in seen:
            seen.add(folded)
            deduped.append(normalized)
    return " ".join(deduped).strip() or str(record.get("id") or "scheduled composition route")


def _resolve_runtime_output_root(path_value: str | None) -> str:
    if isinstance(path_value, str) and path_value.strip():
        candidate = path_value.strip().replace("/", os.sep)
        if os.path.isabs(candidate):
            return candidate
        return safe_join(ROOT, candidate)
    return safe_join(ROOT, os.path.join("TemporaryQueue", "stage7_scheduler_composition_routing"))


def _purpose_carrier_summary(record: dict[str, Any]) -> dict[str, Any]:
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    summary = derived.get("purpose_carrier_summary")
    return dict(summary) if isinstance(summary, dict) else {}


def _normalized_nonempty_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    rows: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            rows.append(normalized)
    return rows


def _subject_object_id_hint(index: int, total: int) -> str:
    normalized_total = max(1, int(total))
    return "subject" if normalized_total == 1 else f"subject_{index:05d}"


def _build_object_activity_controls(
    record: dict[str, Any],
    task: dict[str, Any],
    *,
    asset_template_ids: list[str],
    mapped_slice: str,
    task_id: str,
    task_type: str,
) -> list[dict[str, Any]]:
    purpose_summary = _purpose_carrier_summary(record)
    controlling_carrier_ids = _normalized_nonempty_str_list(purpose_summary.get("engaged_carrier_ids"))
    if not controlling_carrier_ids:
        controlling_carrier_ids = list(_MAPPED_SLICE_FALLBACK_CARRIER_IDS.get(mapped_slice, []))
    controlling_action_ids = _normalized_nonempty_str_list(purpose_summary.get("engaged_action_ids"))
    if not controlling_action_ids:
        controlling_action_ids = _routing_targets(task) or [mapped_slice]
    semantic_record_id = str(record.get("id") or "")
    total = max(1, len(asset_template_ids))
    return [
        {
            "object_id_hint": _subject_object_id_hint(index, total),
            "asset_template_id": asset_template_id,
            "semantic_record_id": semantic_record_id,
            "mapped_slice": mapped_slice,
            "scheduled_task_id": task_id,
            "scheduled_task_type": task_type,
            "controlling_carrier_ids": list(controlling_carrier_ids),
            "controlling_action_ids": list(controlling_action_ids),
        }
        for index, asset_template_id in enumerate(asset_template_ids)
    ]


def _template_by_id(registry_payload: dict[str, Any], group: str, template_id: str) -> dict[str, Any] | None:
    registry = registry_payload.get("registry") if isinstance(registry_payload.get("registry"), dict) else {}
    for row in registry.get(group) or []:
        if isinstance(row, dict) and str(row.get("id") or "") == template_id:
            return dict(row)
    return None


def _selection_for_mapped_frontier(
    registry_payload: dict[str, Any],
    *,
    objective_text: str,
    mapped_frontier: dict[str, Any],
    top_assets: int = 3,
) -> dict[str, Any]:
    from scripts.composition_template_registry import select_template_bundle

    selection = select_template_bundle(registry_payload, objective_text=objective_text, top_assets=top_assets)
    environment_id = str(mapped_frontier.get("environment_id") or "")
    asset_id = str(mapped_frontier.get("asset_id") or "")
    lighting_id = str(mapped_frontier.get("lighting_id") or "")

    environment_template = _template_by_id(registry_payload, "environment_templates", environment_id)
    if environment_template:
        selection["environment_template"] = environment_template

    if lighting_id:
        lighting_template = _template_by_id(registry_payload, "lighting_templates", lighting_id)
        if lighting_template:
            selection["lighting_template"] = lighting_template

    if asset_id:
        chosen_asset = _template_by_id(registry_payload, "asset_templates", asset_id)
        existing_assets = [
            dict(item)
            for item in selection.get("asset_templates") or []
            if isinstance(item, dict) and str(item.get("id") or "") != asset_id
        ]
        if chosen_asset:
            selection["asset_templates"] = [chosen_asset] + existing_assets[: max(0, top_assets - 1)]
    return selection


def _build_scheduled_compose_request(
    record: dict[str, Any],
    task: dict[str, Any],
    *,
    task_index: int,
    selection: dict[str, Any],
    mapped_frontier: dict[str, Any],
    runtime_output_root: str,
) -> dict[str, Any]:
    import cli as cli_module
    from module_composition_contracts import compute_composition_request_id, validate_composition_request

    cfg = _load_cfg() or {}
    environment = selection.get("environment_template") if isinstance(selection.get("environment_template"), dict) else {}
    export_template = selection.get("export_template") if isinstance(selection.get("export_template"), dict) else {}
    lighting = selection.get("lighting_template") if isinstance(selection.get("lighting_template"), dict) else {}
    camera = selection.get("camera_template") if isinstance(selection.get("camera_template"), dict) else {}
    material = selection.get("material_template") if isinstance(selection.get("material_template"), dict) else {}
    asset_templates = [row for row in selection.get("asset_templates") or [] if isinstance(row, dict)]
    record_id = _normalize_route_token(record.get("id"), default="scheduled_record")
    task_id = _normalize_route_token(task.get("task_id"), default=f"task_{task_index}")
    scene_id = _normalize_route_token(
        environment.get("environment_id") or environment.get("id") or f"{record_id}_scene",
        default=f"{record_id}_scene",
    )[:80]
    recipe_id = _normalize_route_token(
        f"stage7_route_{record_id}_{task_id}_{task.get('task_type') or 'task'}",
        default=f"stage7_route_{record_id}_{task_id}",
    )[:80]
    export_format = str(export_template.get("format") or "ply").lower()
    runtime_root_rel = os.path.relpath(runtime_output_root, ROOT).replace("\\", "/")
    payload = cli_module._build_compose_request_payload(
        cfg,
        "export_scene",
        scene_id,
        recipe_id,
        "0.1.0",
        export_format,
        runtime_root_rel,
        task_plan_id="07",
    )
    request_body = payload.get("request") if isinstance(payload.get("request"), dict) else {}
    action_args = request_body.get("action_args") if isinstance(request_body.get("action_args"), dict) else {}
    action_args["environment_id"] = str(environment.get("environment_id") or environment.get("id") or scene_id)
    action_args["lighting_id"] = str(lighting.get("id") or "")
    action_args["camera_id"] = str(camera.get("id") or "")
    action_args["material_id"] = str(material.get("id") or "")
    action_args["asset_template_ids"] = [str(row.get("id") or "") for row in asset_templates if str(row.get("id") or "")]
    action_args["object_count"] = max(1, len(action_args["asset_template_ids"]))
    action_args["mapped_slice"] = str(mapped_frontier.get("mapped_slice") or "")
    action_args["semantic_record_id"] = str(record.get("id") or record_id)
    action_args["scheduled_task_type"] = str(task.get("task_type") or "")
    action_args["scheduled_task_id"] = task_id
    action_args["object_activity_controls"] = _build_object_activity_controls(
        record,
        task,
        asset_template_ids=list(action_args["asset_template_ids"]),
        mapped_slice=str(action_args["mapped_slice"] or ""),
        task_id=task_id,
        task_type=str(action_args["scheduled_task_type"] or ""),
    )
    request_body["action_args"] = action_args
    payload["request"] = request_body
    payload["task_plan_id"] = "stage7_scheduler_composition_routing"
    payload["request_id"] = compute_composition_request_id(payload)
    validate_composition_request(payload)
    return payload


def route_scheduled_composition_workload(
    file_path: str,
    *,
    runtime_output_root: str | None = None,
    max_requests: int = 1,
    carrier_rate_limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    if not os.path.exists(file_path):
        return {"status": "error", "error": "file_not_found", "file": file_path}
    try:
        max_requests = max(1, int(max_requests))
    except Exception:
        max_requests = 1
    rate_limits = {
        _normalize_route_token(key, default="mapped_slice"): max(1, int(value))
        for key, value in (carrier_rate_limits or {}).items()
        if isinstance(key, str)
    }
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except Exception as exc:
        return {"status": "error", "error": "invalid_record", "detail": str(exc), "file": file_path}
    if not isinstance(record, dict):
        return {"status": "error", "error": "invalid_record_root", "file": file_path}

    scheduled_tasks = record.get("scheduled_tasks")
    if not isinstance(scheduled_tasks, list) or not scheduled_tasks:
        return {
            "status": "skipped",
            "reason": "no_scheduled_tasks",
            "file": file_path,
            "record_id": record.get("id"),
        }

    from scripts import blender_composition_receiver
    from scripts.composition_template_registry import build_template_registry
    from scripts.spatial_asset_coverage_report import _mapped_frontier_candidates

    registry_payload = build_template_registry(repo_root=ROOT)
    mapped_frontiers = _mapped_frontier_candidates(record, registry_payload, record_path=file_path)
    if not mapped_frontiers:
        return {
            "status": "skipped",
            "reason": "mapped_frontier_not_grounded",
            "file": file_path,
            "record_id": record.get("id"),
            "mapped_frontier": {},
        }
    primary_frontier = next(
        (row for row in mapped_frontiers if str(row.get("selection_mode") or "") == "primary"),
        mapped_frontiers[0],
    )
    frontier_by_slice = {str(row.get("mapped_slice") or ""): row for row in mapped_frontiers}

    runtime_root = _resolve_runtime_output_root(runtime_output_root)
    os.makedirs(runtime_root, exist_ok=True)
    eligible: list[dict[str, Any]] = []
    skipped_tasks: list[dict[str, Any]] = []
    mapped_slice = str(primary_frontier.get("mapped_slice") or "")

    for index, task in enumerate(scheduled_tasks):
        if not isinstance(task, dict):
            continue
        targets = _routing_targets(task)
        explicit_slice = next((target for target in targets if target in MAPPED_COMPOSITION_SLICES), None)
        alias_target = next((target for target in targets if target in COMPOSITION_ROUTING_TARGET_ALIASES), None)
        route_frontier = frontier_by_slice.get(explicit_slice) if explicit_slice else (primary_frontier if alias_target else None)
        if explicit_slice and route_frontier is None:
            skipped_tasks.append(
                {
                    "task_index": index,
                    "task_type": task.get("task_type"),
                    "reason": "target_slice_mismatch",
                    "target_slice": explicit_slice,
                    "mapped_slice": mapped_slice,
                }
            )
            continue
        route_target = str(route_frontier.get("mapped_slice") or "") if isinstance(route_frontier, dict) else None
        if route_target is None:
            continue
        prior_route = task.get("composition_routing") if isinstance(task.get("composition_routing"), dict) else {}
        prior_status = _normalize_route_token(prior_route.get("status"), default="")
        if prior_status in {"completed", "duplicate_replay"}:
            skipped_tasks.append(
                {
                    "task_index": index,
                    "task_type": task.get("task_type"),
                    "reason": "already_routed",
                    "status": prior_status,
                }
            )
            continue
        priority_rank, normalized_priority = _task_priority_rank(task)
        eligible.append(
            {
                "task_index": index,
                "task": task,
                "route_target": route_target,
                "mapped_frontier": route_frontier,
                "priority_rank": priority_rank,
                "priority": normalized_priority,
                "created_ts": str(task.get("created_ts") or ""),
            }
        )

    eligible.sort(key=lambda row: (row["priority_rank"], row["created_ts"], row["task_index"]))
    if not eligible:
        return {
            "status": "skipped",
            "reason": "no_explicit_composition_targets",
            "file": file_path,
            "record_id": record.get("id"),
            "mapped_frontier": primary_frontier,
            "skipped_tasks": skipped_tasks,
        }

    results: list[dict[str, Any]] = []
    routed_per_slice: dict[str, int] = {}
    for row in eligible:
        if len(results) >= max_requests:
            break
        route_target = str(row["route_target"] or "")
        slice_cap = max(1, int(rate_limits.get(route_target, max_requests)))
        if routed_per_slice.get(route_target, 0) >= slice_cap:
            skipped_tasks.append(
                {
                    "task_index": int(row["task_index"]),
                    "task_type": row["task"].get("task_type"),
                    "reason": "carrier_rate_limited",
                    "mapped_slice": route_target,
                    "slice_cap": slice_cap,
                }
            )
            continue
        task = row["task"]
        objective_text = _record_objective_text(record, task=task)
        selection = _selection_for_mapped_frontier(
            registry_payload,
            objective_text=objective_text,
            mapped_frontier=row["mapped_frontier"],
            top_assets=3,
        )
        request_payload = _build_scheduled_compose_request(
            record,
            task,
            task_index=int(row["task_index"]),
            selection=selection,
            mapped_frontier=row["mapped_frontier"],
            runtime_output_root=runtime_root,
        )
        receiver_result = blender_composition_receiver.process_request_payload(
            request_payload,
            output_root=runtime_root,
            semantic_record_path=file_path,
        )
        runtime_response = receiver_result.get("runtime_response") if isinstance(receiver_result.get("runtime_response"), dict) else {}
        trigger_result = receiver_result.get("trigger_result") if isinstance(receiver_result.get("trigger_result"), dict) else {}
        ai_brain_commit = (
            trigger_result.get("ai_brain_commit")
            if isinstance(trigger_result.get("ai_brain_commit"), dict)
            else {}
        )
        routing_status = (
            "duplicate_replay"
            if bool(receiver_result.get("duplicate_replay"))
            else str(runtime_response.get("status") or receiver_result.get("receiver_decision") or "accepted")
        )
        task["composition_routing"] = {
            "status": routing_status,
            "receiver_decision": receiver_result.get("receiver_decision"),
            "runtime_status": runtime_response.get("status"),
            "runtime_mode": receiver_result.get("runtime_mode"),
            "request_id": receiver_result.get("request_id"),
            "mapped_slice": row["route_target"],
            "environment_template_id": selection.get("environment_template", {}).get("id"),
            "asset_template_ids": [item.get("id") for item in selection.get("asset_templates") or [] if isinstance(item, dict)],
            "trigger_status": trigger_result.get("status"),
            "ai_brain_commit_status": ai_brain_commit.get("status"),
            "ai_brain_commit_record_id": ai_brain_commit.get("record_id"),
            "ai_brain_commit_request_id": ai_brain_commit.get("request_id"),
            "routed_at": _deterministic_now().isoformat(),
            "output_root": runtime_root,
        }
        results.append(
            {
                "task_index": int(row["task_index"]),
                "task_type": task.get("task_type"),
                "priority": row["priority"],
                "request_id": receiver_result.get("request_id"),
                "receiver_decision": receiver_result.get("receiver_decision"),
                "runtime_status": runtime_response.get("status"),
                "trigger_status": trigger_result.get("status"),
                "ai_brain_commit_status": ai_brain_commit.get("status"),
                "ai_brain_commit_record_id": ai_brain_commit.get("record_id"),
                "ai_brain_commit_request_id": ai_brain_commit.get("request_id"),
                "mapped_slice": row["route_target"],
                "environment_template_id": selection.get("environment_template", {}).get("id"),
                "asset_template_ids": [item.get("id") for item in selection.get("asset_templates") or [] if isinstance(item, dict)],
            }
        )
        routed_per_slice[route_target] = routed_per_slice.get(route_target, 0) + 1

    summary_frontier = eligible[0]["mapped_frontier"] if eligible else primary_frontier
    record["composition_routing"] = {
        "status": "completed",
        "record_id": record.get("id"),
        "last_routed_at": _deterministic_now().isoformat(),
        "mapped_frontier": {
            "mapped_slice": summary_frontier.get("mapped_slice"),
            "environment_id": summary_frontier.get("environment_id"),
            "asset_id": summary_frontier.get("asset_id"),
            "total_score": summary_frontier.get("total_score"),
        },
        "eligible_count": len(eligible),
        "routed_count": len(results),
        "max_requests": max_requests,
        "carrier_rate_limits": {
            "default_max_requests": max_requests,
            "mapped_slice_caps": rate_limits,
            "routed_per_slice": routed_per_slice,
        },
        "runtime_output_root": runtime_root,
        "results": results,
        "skipped_tasks": skipped_tasks,
    }
    record.setdefault("schema_version", "1.0")
    try:
        validate_record(record, "semantic")
    except Exception:
        pass
    _atomic_write_record(file_path, record)
    return {
        "status": "completed",
        "file": file_path,
        "record_id": record.get("id"),
        "mapped_frontier": summary_frontier,
        "eligible_count": len(eligible),
        "routed_count": len(results),
        "carrier_rate_limits": {
            "default_max_requests": max_requests,
            "mapped_slice_caps": rate_limits,
            "routed_per_slice": routed_per_slice,
        },
        "results": results,
        "skipped_tasks": skipped_tasks,
        "runtime_output_root": runtime_root,
    }


def _build_learning_readiness_verdict_for_record(record, *, measurement_summary=None):
    measurement_payload = measurement_summary if isinstance(measurement_summary, dict) else {}
    if not measurement_payload:
        candidate = record.get("measurement_adequacy") if isinstance(record.get("measurement_adequacy"), dict) else {}
        measurement_payload = dict(candidate) if isinstance(candidate, dict) else {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}

    categorized_summary = {}
    persisted_categorized = derived.get("categorized_context_summary") if isinstance(derived.get("categorized_context_summary"), dict) else {}
    if isinstance(persisted_categorized, dict) and persisted_categorized:
        categorized_summary = dict(persisted_categorized)
    else:
        try:
            from module_relational_adapter import summarize_record_categorized_context

            categorized_summary = summarize_record_categorized_context(record)
            if not isinstance(categorized_summary, dict):
                categorized_summary = {}
        except Exception:
            categorized_summary = {}

    persisted_comprehension = derived.get("comprehension_review_summary") if isinstance(derived.get("comprehension_review_summary"), dict) else {}
    if isinstance(persisted_comprehension, dict) and persisted_comprehension:
        comprehension_summary = dict(persisted_comprehension)
    else:
        comprehension_summary = {
            "level": record.get("comprehension_review", {}).get("level") if isinstance(record.get("comprehension_review"), dict) else None,
            "summary": record.get("comprehension_review", {}).get("summary") if isinstance(record.get("comprehension_review"), dict) else None,
            "unresolved_gaps": record.get("comprehension_review", {}).get("unresolved_gaps") if isinstance(record.get("comprehension_review"), dict) else [],
        }

    categorized_level = categorized_summary.get("level")
    if not isinstance(categorized_level, str) or not categorized_level:
        categorized_level = categorized_summary.get("support_level")

    comprehension_level = comprehension_summary.get("level")
    if not isinstance(comprehension_level, str) or not comprehension_level:
        comprehension_level = comprehension_summary.get("quality")

    return build_learning_readiness_verdict(
        measurement_adequacy={
            "level": measurement_payload.get("level"),
            "reason": measurement_payload.get("reason"),
        },
        categorized_context={
            "level": categorized_level,
            "counts": {
                "labels": len(categorized_summary.get("labels") or []),
                "aliases": len(categorized_summary.get("aliases") or []),
                "comparison_axes": len(categorized_summary.get("comparison_axes") or []),
                "relation_families": len(categorized_summary.get("relation_families") or []),
                "bridge_sources": len(categorized_summary.get("bridge_sources") or []),
            },
        },
        comprehension_review={
            "level": comprehension_level,
            "summary": comprehension_summary.get("summary"),
            "unresolved_gaps": comprehension_summary.get("unresolved_gaps"),
        },
    )


def _get_schedule_priority_sandbox_settings(config=None):
    cfg = config if isinstance(config, dict) else (_load_cfg() or {})
    policy_cfg = cfg.get("policy") if isinstance(cfg.get("policy"), dict) else {}
    sandbox_settings = policy_cfg.get("schedule_priority_sandbox") if isinstance(policy_cfg.get("schedule_priority_sandbox"), dict) else {}
    return dict(sandbox_settings) if isinstance(sandbox_settings, dict) else {}


def _build_schedule_priority_sandbox_report(record, *, priority, config=None):
    sandbox_settings = _get_schedule_priority_sandbox_settings(config=config)
    sandbox_cfg = sandbox_settings.get("sandbox_activation") if isinstance(sandbox_settings.get("sandbox_activation"), dict) else {}
    preserve_baseline = bool(sandbox_cfg.get("preserve_baseline_when_blocked", True))
    activation_mode = str(sandbox_cfg.get("mode") or "learning_readiness_gated")
    enabled = bool(sandbox_settings.get("enable"))
    use_priority_labels = bool(sandbox_settings.get("use_priority_labels", True))

    readiness_verdict = None
    if enabled:
        readiness_verdict = _build_learning_readiness_verdict_for_record(record)

    report = build_learning_sandbox_activation_report(
        readiness_verdict=readiness_verdict,
        sandbox_settings={
            "enable": enabled,
            "use_retrieval_scores": use_priority_labels,
            "use_retrieval_components": False,
            "retrieval_component_weight": 0.0,
        },
        sandbox_name="schedule_priority",
    )

    active = bool(report.get("active")) and activation_mode == "learning_readiness_gated"
    configured_paths = ["schedule_priority"] if use_priority_labels else []

    return {
        "version": 1,
        "sandbox": "schedule_priority",
        "status": "active" if active else report.get("status"),
        "active": active,
        "blocked_reason": None if active else report.get("blocked_reason"),
        "configured_paths": configured_paths,
        "active_paths": list(configured_paths) if active else [],
        "read_only": True,
        "persistent_state": False,
        "mutable_weights": False,
        "readiness": dict(report.get("readiness") or {}),
        "config_snapshot": {
            "enable": enabled,
            "use_priority_labels": use_priority_labels,
        },
        "path_metadata": {
            "schedule_priority": {
                "configured": use_priority_labels,
                "requested_priority": priority,
            },
        },
        "activation_mode": activation_mode,
        "preserve_baseline_when_blocked": preserve_baseline,
    }


def _persist_future_event_time(file_path, minutes_from_now=5, label=None):
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"

    with open(file_path, "r", encoding="utf-8") as f:
        record = json.load(f)

    future_time = (_deterministic_now() + timedelta(minutes=minutes_from_now)).isoformat()
    record["future_event_time"] = future_time
    if isinstance(label, str) and label:
        record.setdefault("labels", []).append(label)
    record.setdefault("schema_version", "1.0")
    try:
        validate_record(record, 'semantic')
    except Exception:
        pass

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return future_time, None

def flag_record(file_path, label, minutes_from_now=5):
    """
    Flag a record with a label and schedule a future event time.
    """
    future_time, error = _persist_future_event_time(file_path, minutes_from_now=minutes_from_now, label=label)
    if error:
        return error

    return f"Flagged {file_path} with label '{label}', scheduled for {future_time}"

def schedule_task(file_path: str, task_type: str, priority: str = "normal", targets=None, why: str = ""):
    """Phase 14: schedule typed tasks with priority and explicit targets/why."""
    if task_type not in TASK_TYPES:
        return {"status": "error", "error": "invalid_task_type", "task_type": task_type}
    if not os.path.exists(file_path):
        return {"status": "error", "error": "file_not_found", "file": file_path}
    try:
        with open(file_path, "r+", encoding="utf-8") as f:
            record = json.load(f)
            tasks = record.setdefault("scheduled_tasks", [])
            task_counter = 0
            try:
                task_counter = max(0, int(record.get("scheduled_task_counter") or 0))
            except Exception:
                task_counter = 0
            if task_counter <= 0 and isinstance(tasks, list):
                task_counter = len(tasks)
            task_counter += 1
            task = {
                "task_id": f"scheduled_task_{task_counter}",
                "task_type": task_type,
                "priority": priority,
                "targets": targets or [],
                "why": why,
                "created_ts": _deterministic_now().isoformat(),
                "schema_version": "1.0"
            }
            tasks.append(task)
            record["scheduled_tasks"] = tasks[-50:]
            record["scheduled_task_counter"] = task_counter
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "task": task}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def schedule_synthesis(file_path, minutes_from_now=5):
    """
    Flag a record for synthesis in ActiveSpace.
    """
    future_time, error = _persist_future_event_time(file_path, minutes_from_now=minutes_from_now)
    if error:
        return error
    return f"Scheduled synthesis for {file_path} at {future_time}"

def reschedule_task(semantic_file: str, new_time_minutes: int):
    """Reschedule a record's future_event_time by new_time_minutes.
    Returns JSON with status, new_time, and task_id.
    """
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            new_time = (_deterministic_now() + timedelta(minutes=new_time_minutes)).isoformat()
            record["future_event_time"] = new_time
            record.setdefault("schema_version", "1.0")
            task_id = record.get("id", os.path.basename(semantic_file))
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "new_time": new_time, "task_id": task_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def cancel_task(semantic_file: str, task_id: str):
    """Cancel a scheduled task by clearing future_event_time; returns JSON."""
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            record.pop("future_event_time", None)
            record.setdefault("schema_version", "1.0")
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def set_priority(semantic_file: str, task_id: str, priority: str):
    """Set a priority label on the record; returns JSON."""
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            labels = record.setdefault("labels", [])
            if priority not in labels:
                labels.append(priority)
            sandbox_report = _build_schedule_priority_sandbox_report(record, priority=priority)
            record["schedule_priority_sandbox"] = sandbox_report
            if sandbox_report.get("active"):
                record["schedule_priority_update"] = {
                    "task_id": task_id,
                    "priority": priority,
                    "applied": True,
                    "updated_ts": _deterministic_now().isoformat(),
                    "source": "set_priority",
                }
            elif bool(sandbox_report.get("preserve_baseline_when_blocked", True)):
                record.pop("schedule_priority_update", None)
            record.setdefault("schema_version", "1.0")
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {
            "status": "completed",
            "task_id": task_id,
            "priority": priority,
            "priority_update_applied": bool(sandbox_report.get("active")),
            "schedule_priority_sandbox": sandbox_report,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
