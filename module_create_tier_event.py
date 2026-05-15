import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional

from module_tools import canonical_json_bytes, safe_join, sanitize_id


CREATE_TIER_EVENT_SCHEMA_VERSION = "create_tier_event_v1"
CREATE_TIER_APPLY_CHECKPOINT_SCHEMA_VERSION = "create_tier_apply_checkpoint_v1"
CREATE_TIER_ROLLBACK_SCHEMA_VERSION = "create_tier_rollback_contract_v1"
CREATE_TIER_FACTORY_DESCRIPTOR_SCHEMA_VERSION = "create_tier_family_factory_descriptor_v1"
CREATE_TIER_FACTORY_SCALING_PLAN_SCHEMA_VERSION = "create_tier_factory_scaling_plan_v1"
CREATE_TIER_BATCH_CREATION_MANIFEST_SCHEMA_VERSION = "create_tier_batch_creation_manifest_v1"
CREATE_TIER_BATCH_MATERIALIZATION_RESULT_SCHEMA_VERSION = "create_tier_batch_materialization_result_v1"
CREATE_TIER_SHARED_INTEGRATION_SUMMARY_SCHEMA_VERSION = "create_tier_shared_integration_summary_v1"
CREATE_TIER_WAVE_SHARED_INTEGRATION_SUMMARY_SCHEMA_VERSION = "create_tier_wave_shared_integration_summary_v1"
CREATE_TIER_WAVE_VALIDATION_SUMMARY_SCHEMA_VERSION = "create_tier_wave_validation_summary_v1"
CREATE_TIER_INITIAL_EVENT_SELECTION_SCHEMA_VERSION = "create_tier_initial_event_selection_v1"
CREATE_TIER_EVENT_SEQUENCE_REVIEW_SCHEMA_VERSION = "create_tier_event_sequence_review_v1"
CREATE_TIER_LIFECYCLE_REVIEW_SCHEMA_VERSION = "create_tier_lifecycle_review_v1"
CREATE_TIER_RUNTIME_GATE_REVIEW_SCHEMA_VERSION = "create_tier_runtime_gate_review_v1"
CREATE_TIER_COMPOSED_EVENT_REVIEW_SCHEMA_VERSION = "create_tier_composed_event_review_v1"
CREATE_TIER_REFERENCE_PARTITION_GROUP_REVIEW_SCHEMA_VERSION = "create_tier_reference_partition_group_review_v1"
CREATE_TIER_SIMULTANEOUS_CONTEXT_SHARD_GROUP_REVIEW_SCHEMA_VERSION = "create_tier_simultaneous_context_shard_group_review_v1"
CREATE_TIER_RETAINED_STORAGE_GROUP_REVIEW_SCHEMA_VERSION = "create_tier_retained_storage_group_review_v1"
CREATE_TIER_SPATIAL_CONTEXT_SUPPORT_GROUP_REVIEW_SCHEMA_VERSION = "create_tier_spatial_context_support_group_review_v1"
CREATE_TIER_CORRECTNESS_SUPPORT_GROUP_REVIEW_SCHEMA_VERSION = "create_tier_correctness_support_group_review_v1"

SUPPORTED_CREATE_TIER_EVENT_TYPES = (
    "create_family_group",
    "create_instance",
    "retire_instance",
    "promote_instance",
    "demote_instance",
    "garbage_collect_instance",
)

SUPPORTED_CREATE_TIER_INITIAL_STATES = ("created", "shadow", "standby")
SUPPORTED_CREATE_TIER_APPLY_STATUSES = ("queued", "claimed", "validating", "applied", "validated", "released")
SUPPORTED_CREATE_TIER_FACTORY_DEFAULT_STATES = ("shadow", "standby")
SUPPORTED_CREATE_TIER_ROLLOUT_STAGE_LABELS = ("new_group_creation", "existing_group_widening")
SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES = ("passed", "failed", "blocked", "skipped")
SUPPORTED_CREATE_TIER_SEQUENCE_ACTIONS = ("initial_event", "deepen_existing_group", "add_distinct_group")
SUPPORTED_CREATE_TIER_LIFECYCLE_ACTIONS = (
    "rollback_created_instances",
    "retire_created_instance",
    "garbage_collect_created_instance",
)
SUPPORTED_CREATE_TIER_RUNTIME_GATE_MODES = (
    "repo_eval_only",
    "safe_runtime_eval_required",
)

DEFAULT_CREATE_TIER_INVARIANCE_EXPECTATIONS = (
    "tier1_decisions_unchanged",
    "scheduler_authority_unchanged",
    "schedule_mirror_remains_serving_when_present",
    "created_units_start_non_authoritative",
)

_PRESSURE_KEYS = (
    "activity_pressure",
    "retained_storage_pressure",
    "reference_pressure",
    "category_breadth_pressure",
    "simultaneous_compute_pressure",
)

_DEFAULT_FACTORY_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 1,
    "scale_step_groups": 1,
    "scale_step_instances": 1,
    "max_concurrent_groups": 1,
    "max_concurrent_instances": 1,
}

INTERMEDIATE_WIDENING_TARGET_TOTAL = 1000

REFERENCE_PARTITION_FACTORY_ID = "reference_shard_factory"
REFERENCE_PARTITION_FAMILY_TEMPLATE_ID = "reference_shard"
REFERENCE_PARTITION_DEFAULT_PURPOSE = "bounded simultaneous reference partition growth"
REFERENCE_PARTITION_DEFAULT_SUPPORTED_PRESSURE_TYPES = (
    "reference_pressure",
    "activity_pressure",
)
REFERENCE_PARTITION_DEFAULT_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 3,
    "scale_step_groups": 1,
    "scale_step_instances": 1,
    "max_concurrent_groups": 3,
    "max_concurrent_instances": 4,
}
REFERENCE_PARTITION_DEFAULT_RESOURCE_PROFILE = {
    "storage_budget_mb": 64,
    "reference_window": 256,
}
REFERENCE_PARTITION_DEFAULT_OBSERVABILITY_REQUIREMENTS = (
    "ops_status.create_tier",
    "metrics.create_tier",
)
REFERENCE_PARTITION_DEFAULT_ROLLBACK_REQUIREMENTS = (
    "demote_before_remove",
    "preserve_event_record",
)
REFERENCE_PARTITION_VALIDATION_CASE_IDS = (
    "create_tier_factory_descriptor_truth",
    "create_tier_initial_event_selection_truth",
    "create_tier_event_sequence_truth",
    "create_tier_lifecycle_review_truth",
    "create_tier_runtime_gate_review_truth",
    "create_tier_composed_event_review_truth",
    "create_tier_factory_reporting_truth",
    "create_tier_proposal_review_truth",
    "runtime_lineage_integration_summary",
    "determinism_suite",
)
REFERENCE_GROUNDING_SUPPORT_GROUP_ID = "reference_grounding_support"
REFERENCE_GROUNDING_SUPPORT_DEFAULT_PURPOSE = "bounded reference-grounding support growth"
REFERENCE_GROUNDING_SUPPORT_FUNCTIONALITY_LABEL = "reference_grounding"
SIMULTANEOUS_CONTEXT_SHARD_FACTORY_ID = "simultaneous_context_shard_factory"
SIMULTANEOUS_CONTEXT_SHARD_FAMILY_TEMPLATE_ID = "simultaneous_context_match"
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_PURPOSE = "bounded simultaneous-context shard growth"
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_SUPPORTED_PRESSURE_TYPES = (
    "simultaneous_compute_pressure",
    "reference_pressure",
    "activity_pressure",
)
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 2,
    "scale_step_groups": 1,
    "scale_step_instances": 1,
    "max_concurrent_groups": 2,
    "max_concurrent_instances": 3,
}
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_RESOURCE_PROFILE = {
    "reference_window": 256,
    "standby_rehearsal_slots": 1,
    "simultaneous_context_window": 2,
}
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_OBSERVABILITY_REQUIREMENTS = (
    "ops_status.create_tier",
    "metrics.create_tier",
)
SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_ROLLBACK_REQUIREMENTS = (
    "demote_before_remove",
    "preserve_event_record",
)
SIMULTANEOUS_CONTEXT_SHARD_VALIDATION_CASE_IDS = (
    "create_tier_factory_descriptor_truth",
    "create_tier_initial_event_selection_truth",
    "create_tier_event_sequence_truth",
    "create_tier_lifecycle_review_truth",
    "create_tier_runtime_gate_review_truth",
    "create_tier_composed_event_review_truth",
    "create_tier_proposal_review_truth",
    "create_tier_simultaneous_context_group_truth",
    "runtime_lineage_integration_summary",
    "determinism_suite",
)
SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID = "spatial_context_relation_support"
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_PURPOSE = "bounded spatial-context relation support growth"
SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL = "spatial_context_relation"
ACTIVE_SPACE_SUPPORT_FACTORY_ID = "active_space_support_factory"
ACTIVE_SPACE_SUPPORT_FAMILY_TEMPLATE_ID = "active_space_support"
ACTIVE_SPACE_SUPPORT_RECEIVING_GROUP_ID = "active_space_support"
ACTIVE_SPACE_SUPPORT_FUNCTIONALITY_LABEL = "simultaneous_context_comparison"
ACTIVE_SPACE_SUPPORT_DEFAULT_PURPOSE = "bounded active-space simultaneous-context support growth"
ACTIVE_SPACE_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES = SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_SUPPORTED_PRESSURE_TYPES
ACTIVE_SPACE_SUPPORT_DEFAULT_CREATION_LIMITS = SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_CREATION_LIMITS
ACTIVE_SPACE_SUPPORT_DEFAULT_RESOURCE_PROFILE = SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_RESOURCE_PROFILE
ACTIVE_SPACE_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS = SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_OBSERVABILITY_REQUIREMENTS
ACTIVE_SPACE_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS = SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_ROLLBACK_REQUIREMENTS
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES = ACTIVE_SPACE_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 1,
    "scale_step_groups": 1,
    "scale_step_instances": 1,
    "max_concurrent_groups": 1,
    "max_concurrent_instances": 1,
}
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_RESOURCE_PROFILE = ACTIVE_SPACE_SUPPORT_DEFAULT_RESOURCE_PROFILE
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS = ACTIVE_SPACE_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS
SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS = ACTIVE_SPACE_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS
SPATIAL_CONTEXT_RELATION_SUPPORT_VALIDATION_CASE_IDS = (
    "create_tier_factory_descriptor_truth",
    "create_tier_initial_event_selection_truth",
    "create_tier_event_sequence_truth",
    "create_tier_lifecycle_review_truth",
    "create_tier_runtime_gate_review_truth",
    "create_tier_composed_event_review_truth",
    "create_tier_proposal_review_truth",
    "create_tier_spatial_context_support_group_truth",
    "runtime_lineage_integration_summary",
    "determinism_suite",
)
RETAINED_STORAGE_GROUP_FACTORY_ID = "retained_storage_tier1_factory"
RETAINED_STORAGE_GROUP_FAMILY_TEMPLATE_ID = "tier1_main_cognition"
RETAINED_STORAGE_GROUP_RECEIVING_GROUP_ID = "tier1_main_cognition"
RETAINED_STORAGE_GROUP_FUNCTIONALITY_LABEL = "retained_storage_remembering_and_implementation"
RETAINED_STORAGE_GROUP_DEFAULT_PURPOSE = "bounded retained-storage integration growth"
RETAINED_STORAGE_GROUP_DEFAULT_SUPPORTED_PRESSURE_TYPES = (
    "retained_storage_pressure",
    "activity_pressure",
    "category_breadth_pressure",
)
RETAINED_STORAGE_GROUP_DEFAULT_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 100,
    "scale_step_groups": 1,
    "scale_step_instances": 100,
    "max_concurrent_groups": 1,
    "max_concurrent_instances": 100,
}
RETAINED_STORAGE_GROUP_DEFAULT_RESOURCE_PROFILE = {
    "retained_partition_roots": 3,
    "review_surface": "tier1_main_cognition",
}
RETAINED_STORAGE_GROUP_DEFAULT_OBSERVABILITY_REQUIREMENTS = (
    "metrics.retained_storage_pressure",
    "ops_status.create_tier",
)
RETAINED_STORAGE_GROUP_DEFAULT_ROLLBACK_REQUIREMENTS = (
    "demote_before_remove",
    "preserve_event_record",
)
RETAINED_STORAGE_GROUP_VALIDATION_CASE_IDS = (
    "create_tier_factory_descriptor_truth",
    "create_tier_initial_event_selection_truth",
    "create_tier_event_sequence_truth",
    "create_tier_lifecycle_review_truth",
    "create_tier_runtime_gate_review_truth",
    "create_tier_composed_event_review_truth",
    "create_tier_proposal_review_truth",
    "create_tier_factory_reporting_truth",
    "create_tier_mass_quantity_modules_truth",
    "create_tier_batch_materialization_truth",
    "create_tier_retained_storage_group_truth",
    "runtime_lineage_integration_summary",
    "determinism_suite",
)
RETAINED_MEMORY_SUPPORT_GROUP_ID = "retained_memory_support"
RETAINED_MEMORY_SUPPORT_DEFAULT_PURPOSE = "bounded retained-memory support growth"
RETAINED_MEMORY_SUPPORT_FUNCTIONALITY_LABEL = "retained_memory"
CORRECTNESS_SUPPORT_FACTORY_ID = "correctness_constraint_verification_support_factory"
CORRECTNESS_SUPPORT_FAMILY_TEMPLATE_ID = "correctness_constraint_verification_support"
CORRECTNESS_SUPPORT_GROUP_ID = "correctness_constraint_verification_support"
CORRECTNESS_SUPPORT_DEFAULT_PURPOSE = "bounded correctness and constraint verification support growth"
CORRECTNESS_SUPPORT_FUNCTIONALITY_LABEL = "correctness_constraint_verification_support"
CORRECTNESS_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES = (
    "activity_pressure",
    "category_breadth_pressure",
)
CORRECTNESS_SUPPORT_DEFAULT_CREATION_LIMITS = {
    "initial_group_count": 1,
    "initial_instance_count": 1,
    "per_event_group_cap": 1,
    "per_event_instance_cap": 1,
    "scale_step_groups": 1,
    "scale_step_instances": 1,
    "max_concurrent_groups": 1,
    "max_concurrent_instances": 1,
}
CORRECTNESS_SUPPORT_DEFAULT_RESOURCE_PROFILE = {
    "verifier_surfaces": 1,
    "constraint_review_modes": ["math", "physics", "scene"],
}
CORRECTNESS_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS = (
    "ops_status.create_tier",
    "metrics.create_tier",
)
CORRECTNESS_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS = (
    "demote_before_remove",
    "preserve_event_record",
)
CORRECTNESS_SUPPORT_VALIDATION_CASE_IDS = (
    "create_tier_factory_descriptor_truth",
    "create_tier_initial_event_selection_truth",
    "create_tier_event_sequence_truth",
    "create_tier_lifecycle_review_truth",
    "create_tier_runtime_gate_review_truth",
    "create_tier_composed_event_review_truth",
    "create_tier_proposal_review_truth",
    "create_tier_correctness_support_group_truth",
    "runtime_lineage_integration_summary",
    "determinism_suite",
)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalize_string(value: Any) -> str:
    return str(value or "").strip()


def _bounded_id_fragment(value: Any, *, max_len: int = 32, default: str = "create_tier") -> str:
    normalized = _normalize_string(value) or default
    return sanitize_id(normalized[:max_len], max_len=max_len)


def _normalize_string_list(values: Optional[Iterable[Any]]) -> List[str]:
    items = []
    for value in values or []:
        normalized = _normalize_string(value)
        if normalized:
            items.append(normalized)
    return sorted(dict.fromkeys(items))


def _normalize_int_list(values: Optional[Iterable[Any]]) -> List[int]:
    items: List[int] = []
    for value in values or []:
        try:
            normalized = int(value)
        except Exception:
            continue
        if normalized not in items:
            items.append(normalized)
    return sorted(items)


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(value[key]) for key in sorted(value.keys(), key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _annotate_factory_descriptor(
    descriptor: Dict[str, Any],
    *,
    canonical_support_group: str,
    canonical_support_scope: str,
    canonical_purpose: str = "",
    canonical_functionality_labels: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    payload = dict(descriptor or {})
    payload["canonical_support_group"] = _normalize_string(canonical_support_group)
    payload["canonical_support_scope"] = _normalize_string(canonical_support_scope)
    if canonical_purpose:
        payload["canonical_purpose"] = _normalize_string(canonical_purpose)
    normalized_functionality_labels = _normalize_string_list(canonical_functionality_labels)
    if normalized_functionality_labels:
        payload["canonical_functionality_labels"] = normalized_functionality_labels

    core_payload = dict(payload)
    core_payload.pop("descriptor_id", None)
    core_payload.pop("descriptor_hash", None)
    normalized_factory_id = _normalize_string(payload.get("factory_id")) or "create_tier_factory"
    payload["descriptor_id"] = (
        f"ctfac_{_bounded_id_fragment(normalized_factory_id, max_len=32)}_{_stable_hash(core_payload)[:12]}"
    )
    payload["descriptor_hash"] = _stable_hash(payload)
    return payload


def _normalize_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        normalized = int(value)
    except Exception:
        normalized = default
    return max(minimum, normalized)


def _merge_normalized_dict(defaults: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(defaults)
    for key, value in (overrides or {}).items():
        payload[str(key)] = value
    return payload


def _normalize_pressure_snapshot(snapshot: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for key in _PRESSURE_KEYS:
        value = snapshot.get(key, {}) if isinstance(snapshot, dict) else {}
        normalized[key] = _normalize_json_value(value) if isinstance(value, dict) else {}
    return normalized


def _normalize_rollout_stage_label(value: Any) -> str:
    normalized = _normalize_string(value) or "new_group_creation"
    if normalized not in SUPPORTED_CREATE_TIER_ROLLOUT_STAGE_LABELS:
        raise ValueError(f"unsupported create-tier rollout_stage_label: {normalized}")
    return normalized


def _normalize_integration_result_state(value: Any) -> str:
    normalized = _normalize_string(value) or "blocked"
    if normalized not in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES:
        raise ValueError(f"unsupported create-tier integration result state: {normalized}")
    return normalized


def _normalize_result_rows(rows: Optional[Iterable[Dict[str, Any]]], *, require_instance_id: bool) -> List[Dict[str, Any]]:
    normalized_rows: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            raise TypeError("integration result rows must be dicts")
        task_id = _normalize_string(row.get("task_id")) or "task"
        state = _normalize_integration_result_state(row.get("state"))
        payload = {
            "task_id": task_id,
            "state": state,
            "detail": _normalize_string(row.get("detail")),
        }
        if require_instance_id:
            instance_id = _normalize_string(row.get("instance_id"))
            if not instance_id:
                raise ValueError("per-instance integration results require instance_id")
            payload["instance_id"] = instance_id
        normalized_rows.append(payload)
    normalized_rows.sort(
        key=lambda item: (
            item.get("instance_id", ""),
            item.get("task_id", ""),
            item.get("state", ""),
            item.get("detail", ""),
        )
    )
    return normalized_rows


def _classify_existing_group_widening_phase(*, target_total_quantity: int) -> str:
    if 0 < target_total_quantity <= INTERMEDIATE_WIDENING_TARGET_TOTAL:
        return "intermediate_widen_to_1000"
    return "purpose_based_higher_target"


def _max_existing_instance_index(existing_instance_ids: Iterable[str], *, expected_prefix: str) -> int:
    max_index = 0
    for instance_id in existing_instance_ids:
        normalized_instance_id = _normalize_string(instance_id)
        if not normalized_instance_id.startswith(expected_prefix):
            continue
        suffix = normalized_instance_id[len(expected_prefix):]
        if not suffix.isdigit():
            continue
        try:
            max_index = max(max_index, int(suffix))
        except Exception:
            continue
    return max_index


def _write_json_atomic(target_path: str, payload: Dict[str, Any]) -> None:
    parent_dir = os.path.dirname(target_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    tmp_path = f"{target_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, target_path)


def _normalize_supported_pressure_types(values: Optional[Iterable[Any]]) -> List[str]:
    allowed = set(_PRESSURE_KEYS)
    normalized = [value for value in _normalize_string_list(values) if value in allowed]
    return normalized or list(_PRESSURE_KEYS)


def _normalize_creation_limits(creation_limits: Optional[Dict[str, Any]]) -> Dict[str, int]:
    source = creation_limits or {}
    normalized = {
        "initial_group_count": _normalize_int(source.get("initial_group_count"), default=1, minimum=0),
        "initial_instance_count": _normalize_int(source.get("initial_instance_count"), default=1, minimum=0),
        "per_event_group_cap": _normalize_int(source.get("per_event_group_cap"), default=1, minimum=1),
        "per_event_instance_cap": _normalize_int(source.get("per_event_instance_cap"), default=1, minimum=1),
        "scale_step_groups": _normalize_int(source.get("scale_step_groups"), default=1, minimum=1),
        "scale_step_instances": _normalize_int(source.get("scale_step_instances"), default=1, minimum=1),
        "max_concurrent_groups": _normalize_int(source.get("max_concurrent_groups"), default=1, minimum=1),
        "max_concurrent_instances": _normalize_int(source.get("max_concurrent_instances"), default=1, minimum=1),
    }

    normalized["initial_group_count"] = min(normalized["initial_group_count"], normalized["per_event_group_cap"])
    normalized["initial_instance_count"] = min(normalized["initial_instance_count"], normalized["per_event_instance_cap"])
    normalized["per_event_group_cap"] = min(normalized["per_event_group_cap"], normalized["max_concurrent_groups"])
    normalized["per_event_instance_cap"] = min(normalized["per_event_instance_cap"], normalized["max_concurrent_instances"])
    normalized["scale_step_groups"] = min(normalized["scale_step_groups"], normalized["per_event_group_cap"])
    normalized["scale_step_instances"] = min(normalized["scale_step_instances"], normalized["per_event_instance_cap"])
    return normalized


def _normalize_created_instance_ids(instance_id: str, created_instance_ids: Optional[Iterable[Any]]) -> List[str]:
    values = list(created_instance_ids or [])
    if instance_id:
        values.append(instance_id)
    return _normalize_string_list(values)


def build_create_tier_event_contract(
    factory_id: str,
    *,
    family_id: str = "",
    instance_id: str = "",
    created_instance_ids: Optional[Iterable[Any]] = None,
    event_type: str = "create_instance",
    created_at_ts: str = "",
    trigger_reason_summary: str = "",
    bounded_objective: str = "",
    pressure_snapshot: Optional[Dict[str, Any]] = None,
    tier_levels: Optional[Iterable[Any]] = None,
    initial_state: str = "shadow",
    authority_level: str = "non_authoritative",
    verification_gate: str = "",
    rollback_mode: str = "remove_created_units_and_additive_artifacts_only",
    retention_policy_id: str = "",
    origin_review_ref: str = "",
    creation_limits: Optional[Dict[str, Any]] = None,
    invariance_expectations: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    normalized_factory_id = _normalize_string(factory_id)
    if not normalized_factory_id:
        raise ValueError("factory_id is required")

    normalized_event_type = _normalize_string(event_type) or "create_instance"
    if normalized_event_type not in SUPPORTED_CREATE_TIER_EVENT_TYPES:
        raise ValueError(f"unsupported create-tier event_type: {normalized_event_type}")

    normalized_initial_state = _normalize_string(initial_state) or "shadow"
    if normalized_initial_state not in SUPPORTED_CREATE_TIER_INITIAL_STATES:
        raise ValueError(f"unsupported create-tier initial_state: {normalized_initial_state}")

    normalized_family_id = _normalize_string(family_id) or normalized_factory_id
    normalized_instance_id = _normalize_string(instance_id)
    normalized_created_ids = _normalize_created_instance_ids(normalized_instance_id, created_instance_ids)
    normalized_tier_levels = _normalize_int_list(tier_levels)
    normalized_pressure = _normalize_pressure_snapshot(pressure_snapshot)

    payload = {
        "schema_version": CREATE_TIER_EVENT_SCHEMA_VERSION,
        "event_type": normalized_event_type,
        "factory_id": normalized_factory_id,
        "family_id": normalized_family_id,
        "instance_id": normalized_instance_id,
        "created_instance_ids": normalized_created_ids,
        "created_at_ts": _normalize_string(created_at_ts),
        "trigger_reason_summary": _normalize_string(trigger_reason_summary),
        "bounded_objective": _normalize_string(bounded_objective),
        "pressure_snapshot": normalized_pressure,
        "tier_levels": normalized_tier_levels,
        "initial_state": normalized_initial_state,
        "authority_level": _normalize_string(authority_level) or "non_authoritative",
        "authoritative": False,
        "current_serving": False,
        "verification_gate": _normalize_string(verification_gate),
        "rollback_mode": _normalize_string(rollback_mode) or "remove_created_units_and_additive_artifacts_only",
        "retention_policy_id": _normalize_string(retention_policy_id),
        "origin_review_ref": _normalize_string(origin_review_ref),
        "creation_limits": _normalize_json_value(creation_limits or {}),
        "invariance_expectations": _normalize_string_list(invariance_expectations or DEFAULT_CREATE_TIER_INVARIANCE_EXPECTATIONS),
    }
    payload["event_id"] = f"ctevt_{_bounded_id_fragment(normalized_family_id, max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["contract_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_apply_checkpoint(
    event_contract: Dict[str, Any],
    status: str = "validated",
    *,
    pre_state: Optional[Dict[str, Any]] = None,
    post_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_status = _normalize_string(status) or "validated"
    if normalized_status not in SUPPORTED_CREATE_TIER_APPLY_STATUSES:
        raise ValueError(f"unsupported create-tier apply status: {normalized_status}")
    if not isinstance(event_contract, dict):
        raise TypeError("event_contract must be a dict")

    normalized_pre = _normalize_json_value(pre_state or {})
    normalized_post = _normalize_json_value(post_state or {})
    pre_active_families = _normalize_string_list((pre_state or {}).get("active_families"))
    post_active_families = _normalize_string_list((post_state or {}).get("active_families"))
    pre_active_instances = _normalize_string_list((pre_state or {}).get("active_instance_ids"))
    post_active_instances = _normalize_string_list((post_state or {}).get("active_instance_ids"))
    pre_tier1 = _normalize_json_value((pre_state or {}).get("tier1", {}))
    post_tier1 = _normalize_json_value((post_state or {}).get("tier1", {}))

    checkpoint = {
        "schema_version": CREATE_TIER_APPLY_CHECKPOINT_SCHEMA_VERSION,
        "event_id": _normalize_string(event_contract.get("event_id")),
        "family_id": _normalize_string(event_contract.get("family_id")),
        "status": normalized_status,
        "authoritative": False,
        "current_serving": False,
        "pre_state_hash": _stable_hash(normalized_pre),
        "post_state_hash": _stable_hash(normalized_post),
        "tier1_decisions_unchanged": pre_tier1 == post_tier1,
        "scheduler_authority_unchanged": pre_active_families == post_active_families and pre_active_instances == post_active_instances,
        "schedule_mirror_serving_preserved": ("schedule_mirror" in post_active_families) or (pre_active_families == post_active_families),
        "invariance_expectations": _normalize_string_list(
            event_contract.get("invariance_expectations") or DEFAULT_CREATE_TIER_INVARIANCE_EXPECTATIONS
        ),
    }
    checkpoint["checkpoint_id"] = (
        f"ctchk_{_bounded_id_fragment(checkpoint.get('family_id'), max_len=32)}_{_stable_hash(checkpoint)[:12]}"
    )
    checkpoint["checkpoint_hash"] = _stable_hash(checkpoint)
    checkpoint["invariance_passed"] = bool(
        checkpoint["tier1_decisions_unchanged"]
        and checkpoint["scheduler_authority_unchanged"]
        and checkpoint["schedule_mirror_serving_preserved"]
        and checkpoint["authoritative"] is False
        and checkpoint["current_serving"] is False
    )
    return checkpoint


def build_create_tier_rollback_contract(
    event_contract: Dict[str, Any],
    *,
    artifact_cleanup_paths: Optional[Iterable[Any]] = None,
    gc_after_rollback: bool = False,
) -> Dict[str, Any]:
    if not isinstance(event_contract, dict):
        raise TypeError("event_contract must be a dict")

    created_ids = _normalize_string_list(event_contract.get("created_instance_ids") or [])
    rollback = {
        "schema_version": CREATE_TIER_ROLLBACK_SCHEMA_VERSION,
        "event_id": _normalize_string(event_contract.get("event_id")),
        "family_id": _normalize_string(event_contract.get("family_id")),
        "rollback_mode": _normalize_string(event_contract.get("rollback_mode")) or "remove_created_units_and_additive_artifacts_only",
        "remove_created_instance_ids": created_ids,
        "artifact_cleanup_paths": _normalize_string_list(artifact_cleanup_paths),
        "retention_policy_id": _normalize_string(event_contract.get("retention_policy_id")),
        "gc_after_rollback": bool(gc_after_rollback),
        "authoritative": False,
        "current_serving": False,
        "rollback_invariance_expectations": _normalize_string_list(
            event_contract.get("invariance_expectations") or DEFAULT_CREATE_TIER_INVARIANCE_EXPECTATIONS
        ),
    }
    rollback["rollback_id"] = (
        f"ctrbk_{_bounded_id_fragment(rollback.get('family_id'), max_len=32)}_{_stable_hash(rollback)[:12]}"
    )
    rollback["rollback_hash"] = _stable_hash(rollback)
    return rollback


def build_create_tier_family_factory_descriptor(
    factory_id: str,
    *,
    family_template_id: str = "",
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    normalized_factory_id = _normalize_string(factory_id)
    if not normalized_factory_id:
        raise ValueError("factory_id is required")

    normalized_default_state = _normalize_string(default_state) or "shadow"
    if normalized_default_state not in SUPPORTED_CREATE_TIER_FACTORY_DEFAULT_STATES:
        raise ValueError(f"unsupported create-tier factory default_state: {normalized_default_state}")

    payload = {
        "schema_version": CREATE_TIER_FACTORY_DESCRIPTOR_SCHEMA_VERSION,
        "factory_id": normalized_factory_id,
        "family_template_id": _normalize_string(family_template_id) or normalized_factory_id,
        "purpose": _normalize_string(purpose),
        "supported_pressure_types": _normalize_supported_pressure_types(supported_pressure_types),
        "creation_limits": _normalize_creation_limits(creation_limits or _DEFAULT_FACTORY_CREATION_LIMITS),
        "resource_profile": _normalize_json_value(resource_profile or {}),
        "default_state": normalized_default_state,
        "promotion_rules": _normalize_json_value(promotion_rules or {}),
        "retirement_rules": _normalize_json_value(retirement_rules or {}),
        "gc_rules": _normalize_json_value(gc_rules or {}),
        "observability_requirements": _normalize_string_list(observability_requirements),
        "rollback_requirements": _normalize_string_list(rollback_requirements),
        "authoritative": False,
        "current_serving": False,
    }
    payload["descriptor_id"] = (
        f"ctfac_{_bounded_id_fragment(normalized_factory_id, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["descriptor_hash"] = _stable_hash(payload)
    return payload


def build_reference_partition_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        REFERENCE_PARTITION_FACTORY_ID,
        family_template_id=REFERENCE_PARTITION_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or REFERENCE_PARTITION_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or REFERENCE_PARTITION_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(REFERENCE_PARTITION_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(REFERENCE_PARTITION_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or REFERENCE_PARTITION_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or REFERENCE_PARTITION_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=REFERENCE_GROUNDING_SUPPORT_GROUP_ID,
        canonical_support_scope="early_phase_support",
        canonical_purpose=REFERENCE_GROUNDING_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[REFERENCE_GROUNDING_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_reference_partition_group_review(
    *,
    target_total_quantity: int = 0,
    current_total_quantity: int = 0,
    existing_instance_ids: Optional[Iterable[Any]] = None,
    requested_group_count: int = 1,
    requested_instance_count: int = 1,
    materially_pressured: bool = True,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    existing_instance_count: int = 0,
    prior_event_validated: bool = True,
    prior_event_utilized: bool = True,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_reference_partition_group_factory_descriptor(
        creation_limits=creation_limits,
        resource_profile=resource_profile,
    )
    normalized_requested_instances = _normalize_int(requested_instance_count, default=1, minimum=0)
    normalized_existing_instance_ids = _normalize_string_list(existing_instance_ids)
    normalized_current_total = _normalize_int(
        max(current_total_quantity, len(normalized_existing_instance_ids)),
        default=0,
        minimum=0,
    )
    approved_target_total = _normalize_int(
        target_total_quantity,
        default=normalized_current_total + normalized_requested_instances,
        minimum=normalized_current_total,
    )
    selection = build_create_tier_initial_event_selection(
        descriptor,
        requested_group_count=requested_group_count,
        requested_instance_count=max(0, approved_target_total - normalized_current_total),
        materially_pressured=materially_pressured,
        explicit_paired_purpose=explicit_paired_purpose,
        explicit_three_instance_justification=explicit_three_instance_justification,
        reason_summary=reason_summary,
        existing_group_count=existing_group_count,
        existing_instance_count=max(existing_instance_count, normalized_current_total),
    )
    bootstrap = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="initial_event",
        materially_pressured=materially_pressured,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
        reason_summary=reason_summary,
    )
    approved_group_count = int(selection.get("approved_group_count") or 0)
    approved_instance_count = int(selection.get("approved_instance_count") or 0)
    deepen = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="deepen_existing_group",
        materially_pressured=materially_pressured,
        prior_event_validated=prior_event_validated,
        prior_event_utilized=prior_event_utilized,
        strongest_no_new_tier_alternative_sufficient=strongest_no_new_tier_alternative_sufficient,
        retirement_candidate_count=retirement_candidate_count,
        existing_group_count=max(existing_group_count, approved_group_count),
        existing_instance_count=max(
            normalized_current_total,
            1 if approved_group_count else 0,
            normalized_current_total + approved_instance_count,
        ),
        reason_summary=reason_summary or "same group still needs one alternate shard",
    )
    rollout_preview_manifest = build_create_tier_batch_creation_manifest(
        descriptor,
        receiving_group_id=REFERENCE_GROUNDING_SUPPORT_GROUP_ID,
        target_total_quantity=approved_target_total,
        current_total_quantity=normalized_current_total,
        existing_instance_ids=normalized_existing_instance_ids,
        functionality_labels=[REFERENCE_GROUNDING_SUPPORT_FUNCTIONALITY_LABEL],
        rollout_stage_label="new_group_creation" if normalized_current_total == 0 else "existing_group_widening",
    )
    payload = {
        "schema_version": CREATE_TIER_REFERENCE_PARTITION_GROUP_REVIEW_SCHEMA_VERSION,
        "family_group": "reference_partition",
        "canonical_support_group": REFERENCE_GROUNDING_SUPPORT_GROUP_ID,
        "canonical_support_scope": "early_phase_support",
        "receiving_group_id": REFERENCE_GROUNDING_SUPPORT_GROUP_ID,
        "functionality_label": REFERENCE_GROUNDING_SUPPORT_FUNCTIONALITY_LABEL,
        "canonical_functionality_label": REFERENCE_GROUNDING_SUPPORT_FUNCTIONALITY_LABEL,
        "factory_descriptor": descriptor,
        "materially_pressured": bool(materially_pressured),
        "initial_event_selection": selection,
        "bootstrap_sequence_review": bootstrap,
        "deepen_before_broaden_sequence_review": deepen,
        "rollout_preview_manifest": rollout_preview_manifest,
        "planned_created_instance_ids": rollout_preview_manifest.get("planned_created_instance_ids") or [],
        "proposal_mode": "reference_partition_group_review",
        "validation_surfaces": {
            "focused_pytest_target": "tests/test_create_tier_event.py",
            "repo_eval_case_ids": list(REFERENCE_PARTITION_VALIDATION_CASE_IDS),
        },
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = (
        f"ctrpg_{_bounded_id_fragment(REFERENCE_PARTITION_FACTORY_ID, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_simultaneous_context_shard_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        SIMULTANEOUS_CONTEXT_SHARD_FACTORY_ID,
        family_template_id=SIMULTANEOUS_CONTEXT_SHARD_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or SIMULTANEOUS_CONTEXT_SHARD_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        canonical_support_scope="narrow_candidate_family",
        canonical_purpose=SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_simultaneous_context_shard_group_review(
    *,
    requested_group_count: int = 1,
    requested_instance_count: int = 1,
    materially_pressured: bool = True,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    existing_instance_count: int = 0,
    prior_event_validated: bool = True,
    prior_event_utilized: bool = True,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_simultaneous_context_shard_group_factory_descriptor(
        creation_limits=creation_limits,
        resource_profile=resource_profile,
    )
    selection = build_create_tier_initial_event_selection(
        descriptor,
        requested_group_count=requested_group_count,
        requested_instance_count=requested_instance_count,
        materially_pressured=materially_pressured,
        explicit_paired_purpose=explicit_paired_purpose,
        explicit_three_instance_justification=explicit_three_instance_justification,
        reason_summary=reason_summary,
        existing_group_count=existing_group_count,
        existing_instance_count=existing_instance_count,
    )
    bootstrap = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="initial_event",
        materially_pressured=materially_pressured,
        existing_group_count=existing_group_count,
        existing_instance_count=existing_instance_count,
        reason_summary=reason_summary,
    )
    approved_group_count = int(selection.get("approved_group_count") or 0)
    approved_instance_count = int(selection.get("approved_instance_count") or 0)
    deepen = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="deepen_existing_group",
        materially_pressured=materially_pressured,
        prior_event_validated=prior_event_validated,
        prior_event_utilized=prior_event_utilized,
        strongest_no_new_tier_alternative_sufficient=strongest_no_new_tier_alternative_sufficient,
        retirement_candidate_count=retirement_candidate_count,
        existing_group_count=max(existing_group_count, approved_group_count),
        existing_instance_count=max(existing_instance_count, 1 if approved_group_count else 0, approved_instance_count),
        reason_summary=reason_summary or "same simultaneous-context shard group still needs one alternate rehearsal shard",
    )

    planned_created_instance_ids: List[str] = []
    shadow_index = 0
    standby_index = 0
    for index in range(1, approved_instance_count + 1):
        if index == 2 and explicit_paired_purpose:
            standby_index += 1
            planned_created_instance_ids.append(
                f"{SIMULTANEOUS_CONTEXT_SHARD_FAMILY_TEMPLATE_ID}_standby_proposal_{standby_index:02d}"
            )
            continue
        shadow_index += 1
        planned_created_instance_ids.append(
            f"{SIMULTANEOUS_CONTEXT_SHARD_FAMILY_TEMPLATE_ID}_shadow_proposal_{shadow_index:02d}"
        )

    payload = {
        "schema_version": CREATE_TIER_SIMULTANEOUS_CONTEXT_SHARD_GROUP_REVIEW_SCHEMA_VERSION,
        "family_group": "simultaneous_context_shard",
        "canonical_support_group": SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        "canonical_support_scope": "narrow_candidate_family",
        "canonical_functionality_label": SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL,
        "factory_descriptor": descriptor,
        "initial_event_selection": selection,
        "bootstrap_sequence_review": bootstrap,
        "deepen_before_broaden_sequence_review": deepen,
        "planned_created_instance_ids": planned_created_instance_ids,
        "state_relationships": {
            "bootstrap_state": "shadow",
            "paired_rehearsal_state": "standby" if approved_instance_count >= 2 and explicit_paired_purpose else "",
            "paired_rehearsal_requires_explicit_paired_purpose": True,
            "created_instances_non_serving": True,
            "schedule_mirror_serving_preserved": True,
        },
        "proposal_mode": "simultaneous_context_shard_group_review",
        "validation_surfaces": {
            "focused_pytest_target": "tests/test_create_tier_event.py",
            "repo_eval_case_ids": list(SIMULTANEOUS_CONTEXT_SHARD_VALIDATION_CASE_IDS),
        },
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = (
        f"ctscg_{_bounded_id_fragment(SIMULTANEOUS_CONTEXT_SHARD_FACTORY_ID, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_retained_storage_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        RETAINED_STORAGE_GROUP_FACTORY_ID,
        family_template_id=RETAINED_STORAGE_GROUP_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or RETAINED_STORAGE_GROUP_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or RETAINED_STORAGE_GROUP_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(RETAINED_STORAGE_GROUP_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(RETAINED_STORAGE_GROUP_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or RETAINED_STORAGE_GROUP_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or RETAINED_STORAGE_GROUP_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=RETAINED_MEMORY_SUPPORT_GROUP_ID,
        canonical_support_scope="early_phase_support",
        canonical_purpose=RETAINED_MEMORY_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[RETAINED_MEMORY_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_active_space_support_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        ACTIVE_SPACE_SUPPORT_FACTORY_ID,
        family_template_id=ACTIVE_SPACE_SUPPORT_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or ACTIVE_SPACE_SUPPORT_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or ACTIVE_SPACE_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(ACTIVE_SPACE_SUPPORT_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(ACTIVE_SPACE_SUPPORT_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or ACTIVE_SPACE_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or ACTIVE_SPACE_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        canonical_support_scope="current_rollout_support_carrier",
        canonical_purpose=SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_spatial_context_relation_support_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        ACTIVE_SPACE_SUPPORT_FACTORY_ID,
        family_template_id=ACTIVE_SPACE_SUPPORT_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        canonical_support_scope="early_phase_support",
        canonical_purpose=SPATIAL_CONTEXT_RELATION_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_correctness_support_group_factory_descriptor(
    *,
    purpose: str = "",
    supported_pressure_types: Optional[Iterable[Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
    default_state: str = "shadow",
    promotion_rules: Optional[Dict[str, Any]] = None,
    retirement_rules: Optional[Dict[str, Any]] = None,
    gc_rules: Optional[Dict[str, Any]] = None,
    observability_requirements: Optional[Iterable[Any]] = None,
    rollback_requirements: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        CORRECTNESS_SUPPORT_FACTORY_ID,
        family_template_id=CORRECTNESS_SUPPORT_FAMILY_TEMPLATE_ID,
        purpose=_normalize_string(purpose) or CORRECTNESS_SUPPORT_DEFAULT_PURPOSE,
        supported_pressure_types=supported_pressure_types or CORRECTNESS_SUPPORT_DEFAULT_SUPPORTED_PRESSURE_TYPES,
        creation_limits=_merge_normalized_dict(CORRECTNESS_SUPPORT_DEFAULT_CREATION_LIMITS, creation_limits),
        resource_profile=_merge_normalized_dict(CORRECTNESS_SUPPORT_DEFAULT_RESOURCE_PROFILE, resource_profile),
        default_state=default_state,
        promotion_rules=promotion_rules,
        retirement_rules=retirement_rules,
        gc_rules=gc_rules,
        observability_requirements=observability_requirements or CORRECTNESS_SUPPORT_DEFAULT_OBSERVABILITY_REQUIREMENTS,
        rollback_requirements=rollback_requirements or CORRECTNESS_SUPPORT_DEFAULT_ROLLBACK_REQUIREMENTS,
    )
    return _annotate_factory_descriptor(
        descriptor,
        canonical_support_group=CORRECTNESS_SUPPORT_GROUP_ID,
        canonical_support_scope="early_phase_support",
        canonical_purpose=CORRECTNESS_SUPPORT_DEFAULT_PURPOSE,
        canonical_functionality_labels=[CORRECTNESS_SUPPORT_FUNCTIONALITY_LABEL],
    )


def build_reference_grounding_support_factory_descriptor(**kwargs: Any) -> Dict[str, Any]:
    return build_reference_partition_group_factory_descriptor(**kwargs)


def build_reference_grounding_support_review(**kwargs: Any) -> Dict[str, Any]:
    return build_reference_partition_group_review(**kwargs)


def build_retained_memory_support_factory_descriptor(**kwargs: Any) -> Dict[str, Any]:
    return build_retained_storage_group_factory_descriptor(**kwargs)


def build_retained_memory_support_review(**kwargs: Any) -> Dict[str, Any]:
    return build_retained_storage_group_review(**kwargs)


def build_spatial_context_relation_support_factory_descriptor(**kwargs: Any) -> Dict[str, Any]:
    return build_active_space_support_group_factory_descriptor(**kwargs)


def build_spatial_context_relation_support_review(
    *,
    target_total_quantity: int = 0,
    current_total_quantity: int = 0,
    existing_instance_ids: Optional[Iterable[Any]] = None,
    materially_pressured: bool = True,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    prior_event_validated: bool = True,
    prior_event_utilized: bool = True,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_spatial_context_relation_support_group_factory_descriptor(
        creation_limits=creation_limits,
        resource_profile=resource_profile,
    )
    normalized_existing_instance_ids = _normalize_string_list(existing_instance_ids)
    normalized_current_total = _normalize_int(
        max(current_total_quantity, len(normalized_existing_instance_ids)),
        default=0,
        minimum=0,
    )
    approved_target_total = _normalize_int(
        target_total_quantity,
        default=normalized_current_total + 1,
        minimum=normalized_current_total,
    )
    reason = _normalize_string(reason_summary) or (
        "bounded spatial-context relation pressure remains materially measurable"
    )

    selection = build_create_tier_initial_event_selection(
        descriptor,
        requested_group_count=1,
        requested_instance_count=1 if approved_target_total > normalized_current_total else 0,
        materially_pressured=materially_pressured,
        explicit_paired_purpose=explicit_paired_purpose,
        explicit_three_instance_justification=explicit_three_instance_justification,
        reason_summary=reason,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
    )
    bootstrap = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="initial_event",
        materially_pressured=materially_pressured,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
        reason_summary=reason,
    )
    deepen = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="deepen_existing_group",
        materially_pressured=materially_pressured,
        prior_event_validated=prior_event_validated,
        prior_event_utilized=prior_event_utilized,
        strongest_no_new_tier_alternative_sufficient=strongest_no_new_tier_alternative_sufficient,
        retirement_candidate_count=retirement_candidate_count,
        existing_group_count=max(existing_group_count, 1 if selection.get("approved_group_count") else 0),
        existing_instance_count=max(normalized_current_total, 1 if selection.get("approved_instance_count") else 0),
        reason_summary=reason or "spatial-context relation support still needs one bounded non-serving review unit",
    )
    rollout_preview_manifest = build_create_tier_batch_creation_manifest(
        descriptor,
        receiving_group_id=SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        target_total_quantity=approved_target_total,
        current_total_quantity=normalized_current_total,
        existing_instance_ids=normalized_existing_instance_ids,
        functionality_labels=[SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL],
        rollout_stage_label="new_group_creation" if normalized_current_total == 0 else "existing_group_widening",
    )

    payload = {
        "schema_version": CREATE_TIER_SPATIAL_CONTEXT_SUPPORT_GROUP_REVIEW_SCHEMA_VERSION,
        "family_group": "spatial_context_relation_support",
        "canonical_support_group": SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        "canonical_support_scope": "early_phase_support",
        "receiving_group_id": SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID,
        "functionality_label": SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL,
        "canonical_functionality_label": SPATIAL_CONTEXT_RELATION_SUPPORT_FUNCTIONALITY_LABEL,
        "factory_descriptor": descriptor,
        "materially_pressured": bool(materially_pressured),
        "initial_event_selection": selection,
        "bootstrap_sequence_review": bootstrap,
        "deepen_before_broaden_sequence_review": deepen,
        "rollout_preview_manifest": rollout_preview_manifest,
        "planned_created_instance_ids": rollout_preview_manifest.get("planned_created_instance_ids") or [],
        "proposal_mode": "spatial_context_relation_support_group_review",
        "validation_surfaces": {
            "focused_pytest_target": "tests/test_create_tier_event.py",
            "repo_eval_case_ids": list(SPATIAL_CONTEXT_RELATION_SUPPORT_VALIDATION_CASE_IDS),
        },
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = (
        f"ctscs_{_bounded_id_fragment(SPATIAL_CONTEXT_RELATION_SUPPORT_GROUP_ID, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_correctness_constraint_verification_support_factory_descriptor(**kwargs: Any) -> Dict[str, Any]:
    return build_correctness_support_group_factory_descriptor(**kwargs)


def build_correctness_constraint_verification_support_review(**kwargs: Any) -> Dict[str, Any]:
    return build_correctness_support_group_review(**kwargs)


def _normalize_retained_storage_pressure_metrics(
    *,
    retained_storage_pressure_snapshot: Optional[Dict[str, Any]] = None,
    retained_storage_pressure_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metrics_payload = retained_storage_pressure_metrics if isinstance(retained_storage_pressure_metrics, dict) else None
    if not isinstance(metrics_payload, dict):
        try:
            from module_metrics import build_retained_storage_pressure_metrics

            metrics_payload = build_retained_storage_pressure_metrics(snapshot=retained_storage_pressure_snapshot)
        except Exception:
            metrics_payload = {"available": False, "metrics": {}, "reason": "retained_storage_metrics_unavailable"}

    if not isinstance(metrics_payload, dict):
        metrics_payload = {"available": False, "metrics": {}, "reason": "retained_storage_metrics_unavailable"}

    metrics = metrics_payload.get("metrics") if isinstance(metrics_payload.get("metrics"), dict) else {}
    largest_root = metrics.get("largest_root_by_bytes") if isinstance(metrics.get("largest_root_by_bytes"), dict) else None
    normalized = {
        "available": bool(metrics_payload.get("available")),
        "metrics_hash": _normalize_string(metrics_payload.get("metrics_hash")),
        "inputs_hash": _normalize_string(metrics_payload.get("inputs_hash")),
        "reason": _normalize_string(metrics_payload.get("reason")),
        "metrics": {
            "retained_root_count": _normalize_int(metrics.get("retained_root_count"), default=0, minimum=0),
            "retained_file_count": _normalize_int(metrics.get("retained_file_count"), default=0, minimum=0),
            "retained_json_file_count": _normalize_int(metrics.get("retained_json_file_count"), default=0, minimum=0),
            "retained_total_bytes": _normalize_int(metrics.get("retained_total_bytes"), default=0, minimum=0),
            "candidate_partition_count": _normalize_int(metrics.get("candidate_partition_count"), default=0, minimum=0),
            "candidate_partition_roots": _normalize_string_list(metrics.get("candidate_partition_roots") or []),
            "storage_density_bytes_per_file": float(metrics.get("storage_density_bytes_per_file") or 0.0),
            "largest_root_by_bytes": {
                "root_id": _normalize_string(largest_root.get("root_id")),
                "total_bytes": _normalize_int(largest_root.get("total_bytes"), default=0, minimum=0),
                "file_count": _normalize_int(largest_root.get("file_count"), default=0, minimum=0),
            }
            if largest_root
            else None,
        },
    }
    return normalized


def _derive_retained_storage_pressure_reason(metrics_payload: Dict[str, Any]) -> str:
    metrics = metrics_payload.get("metrics") if isinstance(metrics_payload.get("metrics"), dict) else {}
    retained_file_count = _normalize_int(metrics.get("retained_file_count"), default=0, minimum=0)
    retained_total_bytes = _normalize_int(metrics.get("retained_total_bytes"), default=0, minimum=0)
    candidate_partition_count = _normalize_int(metrics.get("candidate_partition_count"), default=0, minimum=0)
    return (
        f"retained storage pressure is measurable: {retained_file_count} files / "
        f"{retained_total_bytes} bytes across {candidate_partition_count} candidate partition roots"
    )


def build_retained_storage_group_review(
    *,
    target_total_quantity: int = 0,
    current_total_quantity: int = 0,
    existing_instance_ids: Optional[Iterable[Any]] = None,
    materially_pressured: Optional[bool] = None,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    prior_event_validated: bool = True,
    prior_event_utilized: bool = True,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    retained_storage_pressure_snapshot: Optional[Dict[str, Any]] = None,
    retained_storage_pressure_metrics: Optional[Dict[str, Any]] = None,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_retained_storage_group_factory_descriptor(
        creation_limits=creation_limits,
        resource_profile=resource_profile,
    )
    pressure_metrics = _normalize_retained_storage_pressure_metrics(
        retained_storage_pressure_snapshot=retained_storage_pressure_snapshot,
        retained_storage_pressure_metrics=retained_storage_pressure_metrics,
    )
    metrics = pressure_metrics["metrics"]
    derived_material_pressure = bool(
        metrics.get("retained_total_bytes")
        or metrics.get("retained_file_count")
        or metrics.get("candidate_partition_count")
    )
    materially_pressured_flag = derived_material_pressure if materially_pressured is None else bool(materially_pressured)
    normalized_existing_instance_ids = _normalize_string_list(existing_instance_ids)
    normalized_current_total = _normalize_int(
        max(current_total_quantity, len(normalized_existing_instance_ids)),
        default=0,
        minimum=0,
    )
    approved_target_total = _normalize_int(
        target_total_quantity,
        default=normalized_current_total + 1,
        minimum=normalized_current_total,
    )
    reason = _normalize_string(reason_summary) or _derive_retained_storage_pressure_reason(pressure_metrics)

    selection = build_create_tier_initial_event_selection(
        descriptor,
        requested_group_count=1,
        requested_instance_count=1 if approved_target_total > normalized_current_total else 0,
        materially_pressured=materially_pressured_flag,
        explicit_paired_purpose=explicit_paired_purpose,
        explicit_three_instance_justification=explicit_three_instance_justification,
        reason_summary=reason,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
    )
    bootstrap = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="initial_event",
        materially_pressured=materially_pressured_flag,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
        reason_summary=reason,
    )
    deepen = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="deepen_existing_group",
        materially_pressured=materially_pressured_flag,
        prior_event_validated=prior_event_validated,
        prior_event_utilized=prior_event_utilized,
        strongest_no_new_tier_alternative_sufficient=strongest_no_new_tier_alternative_sufficient,
        retirement_candidate_count=retirement_candidate_count,
        existing_group_count=max(existing_group_count, 1 if selection.get("approved_group_count") else 0),
        existing_instance_count=max(normalized_current_total, 1 if selection.get("approved_instance_count") else 0),
        reason_summary=reason or "retained storage still needs additional Tier 1 review capacity",
    )
    rollout_preview_manifest = build_create_tier_batch_creation_manifest(
        descriptor,
        receiving_group_id=RETAINED_MEMORY_SUPPORT_GROUP_ID,
        target_total_quantity=approved_target_total,
        current_total_quantity=normalized_current_total,
        existing_instance_ids=normalized_existing_instance_ids,
        functionality_labels=[RETAINED_MEMORY_SUPPORT_FUNCTIONALITY_LABEL],
        rollout_stage_label="new_group_creation" if normalized_current_total == 0 else "existing_group_widening",
    )

    payload = {
        "schema_version": CREATE_TIER_RETAINED_STORAGE_GROUP_REVIEW_SCHEMA_VERSION,
        "family_group": "retained_storage_integration",
        "canonical_support_group": RETAINED_MEMORY_SUPPORT_GROUP_ID,
        "canonical_support_scope": "early_phase_support",
        "receiving_group_id": RETAINED_MEMORY_SUPPORT_GROUP_ID,
        "functionality_label": RETAINED_MEMORY_SUPPORT_FUNCTIONALITY_LABEL,
        "canonical_functionality_label": RETAINED_MEMORY_SUPPORT_FUNCTIONALITY_LABEL,
        "factory_descriptor": descriptor,
        "pressure_metrics": pressure_metrics,
        "materially_pressured": materially_pressured_flag,
        "initial_event_selection": selection,
        "bootstrap_sequence_review": bootstrap,
        "deepen_before_broaden_sequence_review": deepen,
        "rollout_preview_manifest": rollout_preview_manifest,
        "planned_created_instance_ids": rollout_preview_manifest.get("planned_created_instance_ids") or [],
        "proposal_mode": "retained_storage_group_review",
        "validation_surfaces": {
            "focused_pytest_target": "tests/test_create_tier_event.py",
            "repo_eval_case_ids": list(RETAINED_STORAGE_GROUP_VALIDATION_CASE_IDS),
        },
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = (
        f"ctrsg_{_bounded_id_fragment(RETAINED_STORAGE_GROUP_FACTORY_ID, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_correctness_support_group_review(
    *,
    target_total_quantity: int = 0,
    current_total_quantity: int = 0,
    existing_instance_ids: Optional[Iterable[Any]] = None,
    materially_pressured: bool = True,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    prior_event_validated: bool = True,
    prior_event_utilized: bool = True,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    creation_limits: Optional[Dict[str, Any]] = None,
    resource_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    descriptor = build_correctness_support_group_factory_descriptor(
        creation_limits=creation_limits,
        resource_profile=resource_profile,
    )
    normalized_existing_instance_ids = _normalize_string_list(existing_instance_ids)
    normalized_current_total = _normalize_int(
        max(current_total_quantity, len(normalized_existing_instance_ids)),
        default=0,
        minimum=0,
    )
    approved_target_total = _normalize_int(
        target_total_quantity,
        default=normalized_current_total + 1,
        minimum=normalized_current_total,
    )
    reason = _normalize_string(reason_summary) or (
        "bounded correctness and constraint verification pressure remains materially measurable"
    )

    selection = build_create_tier_initial_event_selection(
        descriptor,
        requested_group_count=1,
        requested_instance_count=1 if approved_target_total > normalized_current_total else 0,
        materially_pressured=materially_pressured,
        explicit_paired_purpose=explicit_paired_purpose,
        explicit_three_instance_justification=explicit_three_instance_justification,
        reason_summary=reason,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
    )
    bootstrap = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="initial_event",
        materially_pressured=materially_pressured,
        existing_group_count=existing_group_count,
        existing_instance_count=normalized_current_total,
        reason_summary=reason,
    )
    deepen = build_create_tier_event_sequence_review(
        descriptor,
        requested_action="deepen_existing_group",
        materially_pressured=materially_pressured,
        prior_event_validated=prior_event_validated,
        prior_event_utilized=prior_event_utilized,
        strongest_no_new_tier_alternative_sufficient=strongest_no_new_tier_alternative_sufficient,
        retirement_candidate_count=retirement_candidate_count,
        existing_group_count=max(existing_group_count, 1 if selection.get("approved_group_count") else 0),
        existing_instance_count=max(normalized_current_total, 1 if selection.get("approved_instance_count") else 0),
        reason_summary=reason or "correctness support still needs one bounded non-serving verification unit",
    )
    rollout_preview_manifest = build_create_tier_batch_creation_manifest(
        descriptor,
        receiving_group_id=CORRECTNESS_SUPPORT_GROUP_ID,
        target_total_quantity=approved_target_total,
        current_total_quantity=normalized_current_total,
        existing_instance_ids=normalized_existing_instance_ids,
        functionality_labels=[CORRECTNESS_SUPPORT_FUNCTIONALITY_LABEL],
        rollout_stage_label="new_group_creation" if normalized_current_total == 0 else "existing_group_widening",
    )

    payload = {
        "schema_version": CREATE_TIER_CORRECTNESS_SUPPORT_GROUP_REVIEW_SCHEMA_VERSION,
        "family_group": "correctness_constraint_verification",
        "canonical_support_group": CORRECTNESS_SUPPORT_GROUP_ID,
        "canonical_support_scope": "early_phase_support",
        "receiving_group_id": CORRECTNESS_SUPPORT_GROUP_ID,
        "functionality_label": CORRECTNESS_SUPPORT_FUNCTIONALITY_LABEL,
        "canonical_functionality_label": CORRECTNESS_SUPPORT_FUNCTIONALITY_LABEL,
        "factory_descriptor": descriptor,
        "materially_pressured": bool(materially_pressured),
        "initial_event_selection": selection,
        "bootstrap_sequence_review": bootstrap,
        "deepen_before_broaden_sequence_review": deepen,
        "rollout_preview_manifest": rollout_preview_manifest,
        "planned_created_instance_ids": rollout_preview_manifest.get("planned_created_instance_ids") or [],
        "proposal_mode": "correctness_support_group_review",
        "validation_surfaces": {
            "focused_pytest_target": "tests/test_create_tier_event.py",
            "repo_eval_case_ids": list(CORRECTNESS_SUPPORT_VALIDATION_CASE_IDS),
        },
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = (
        f"ctcsg_{_bounded_id_fragment(CORRECTNESS_SUPPORT_FACTORY_ID, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_factory_scaling_plan(
    factory_descriptor: Dict[str, Any],
    *,
    existing_group_count: int = 0,
    existing_instance_count: int = 0,
) -> Dict[str, Any]:
    if not isinstance(factory_descriptor, dict):
        raise TypeError("factory_descriptor must be a dict")

    creation_limits = _normalize_creation_limits(factory_descriptor.get("creation_limits") or _DEFAULT_FACTORY_CREATION_LIMITS)
    normalized_existing_groups = _normalize_int(existing_group_count, default=0, minimum=0)
    normalized_existing_instances = _normalize_int(existing_instance_count, default=0, minimum=0)

    remaining_groups = max(0, creation_limits["max_concurrent_groups"] - normalized_existing_groups)
    remaining_instances = max(0, creation_limits["max_concurrent_instances"] - normalized_existing_instances)
    initial_event = normalized_existing_groups == 0 and normalized_existing_instances == 0

    planned_group_count = min(
        creation_limits["initial_group_count"] if initial_event else creation_limits["scale_step_groups"],
        creation_limits["per_event_group_cap"],
        remaining_groups,
    )
    planned_instance_count = min(
        creation_limits["initial_instance_count"] if initial_event else creation_limits["scale_step_instances"],
        creation_limits["per_event_instance_cap"],
        remaining_instances,
    )

    payload = {
        "schema_version": CREATE_TIER_FACTORY_SCALING_PLAN_SCHEMA_VERSION,
        "factory_id": _normalize_string(factory_descriptor.get("factory_id")),
        "family_template_id": _normalize_string(factory_descriptor.get("family_template_id")),
        "phase": "initial_event" if initial_event else "repeat_event",
        "default_state": _normalize_string(factory_descriptor.get("default_state")) or "shadow",
        "existing_group_count": normalized_existing_groups,
        "existing_instance_count": normalized_existing_instances,
        "planned_group_count": planned_group_count,
        "planned_instance_count": planned_instance_count,
        "remaining_group_capacity": remaining_groups,
        "remaining_instance_capacity": remaining_instances,
        "creation_limits": creation_limits,
        "observability_requirements": _normalize_string_list(factory_descriptor.get("observability_requirements") or []),
        "rollback_requirements": _normalize_string_list(factory_descriptor.get("rollback_requirements") or []),
        "authoritative": False,
        "current_serving": False,
        "bounded": planned_group_count <= creation_limits["per_event_group_cap"] and planned_instance_count <= creation_limits["per_event_instance_cap"],
        "at_capacity": remaining_groups == 0 or remaining_instances == 0,
    }
    payload["plan_id"] = f"ctplan_{_bounded_id_fragment(payload.get('factory_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["plan_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_batch_creation_manifest(
    factory_descriptor: Dict[str, Any],
    *,
    receiving_group_id: str,
    target_total_quantity: int,
    current_total_quantity: int = 0,
    existing_instance_ids: Optional[Iterable[Any]] = None,
    functionality_labels: Optional[Iterable[Any]] = None,
    rollout_stage_label: str = "new_group_creation",
    file_path_root: str = "TemporaryQueue/create_tier/generated",
) -> Dict[str, Any]:
    if not isinstance(factory_descriptor, dict):
        raise TypeError("factory_descriptor must be a dict")

    normalized_receiving_group_id = _normalize_string(receiving_group_id)
    if not normalized_receiving_group_id:
        raise ValueError("receiving_group_id is required")

    normalized_stage = _normalize_rollout_stage_label(rollout_stage_label)
    normalized_existing_ids = _normalize_string_list(existing_instance_ids)
    normalized_current_total = _normalize_int(
        max(current_total_quantity, len(normalized_existing_ids)),
        default=0,
        minimum=0,
    )
    normalized_target_total = _normalize_int(target_total_quantity, default=0, minimum=0)
    if normalized_target_total < normalized_current_total:
        raise ValueError("target_total_quantity cannot be below current_total_quantity")

    creation_limits = _normalize_creation_limits(factory_descriptor.get("creation_limits") or _DEFAULT_FACTORY_CREATION_LIMITS)
    bounded_max_target_total = _normalize_int(
        creation_limits.get("max_concurrent_instances"),
        default=0,
        minimum=0,
    )
    if bounded_max_target_total and normalized_target_total > bounded_max_target_total:
        raise ValueError("target_total_quantity exceeds bounded max_concurrent_instances")

    family_template_id = _normalize_string(factory_descriptor.get("family_template_id")) or _normalize_string(factory_descriptor.get("factory_id"))
    initial_state = _normalize_string(factory_descriptor.get("default_state")) or "shadow"
    group_fragment = sanitize_id(normalized_receiving_group_id)
    family_fragment = sanitize_id(family_template_id)
    state_fragment = sanitize_id(initial_state)
    existing_id_set = set(normalized_existing_ids)
    missing_quantity = normalized_target_total - normalized_current_total
    instance_id_prefix = f"{group_fragment}_{family_fragment}_{state_fragment}_"
    max_existing_index = _max_existing_instance_index(
        normalized_existing_ids,
        expected_prefix=instance_id_prefix,
    )

    planned_created_instance_ids: List[str] = []
    candidate_index = max(normalized_current_total, max_existing_index) + 1
    while len(planned_created_instance_ids) < missing_quantity:
        candidate_id = f"{group_fragment}_{family_fragment}_{state_fragment}_{candidate_index:05d}"
        if candidate_id not in existing_id_set:
            planned_created_instance_ids.append(candidate_id)
        candidate_index += 1

    normalized_root = _normalize_string(file_path_root).rstrip("/")
    planned_instance_records = [
        {
            "instance_id": instance_id,
            "relative_file_path": f"{normalized_root}/{group_fragment}/{instance_id}.json",
            "initial_state": initial_state,
            "receiving_group_id": normalized_receiving_group_id,
            "family_template_id": family_template_id,
            "authoritative": False,
            "current_serving": False,
        }
        for instance_id in planned_created_instance_ids
    ]

    payload = {
        "schema_version": CREATE_TIER_BATCH_CREATION_MANIFEST_SCHEMA_VERSION,
        "factory_id": _normalize_string(factory_descriptor.get("factory_id")),
        "family_template_id": family_template_id,
        "receiving_group_id": normalized_receiving_group_id,
        "functionality_labels": _normalize_string_list(functionality_labels),
        "rollout_stage_label": normalized_stage,
        "target_total_quantity": normalized_target_total,
        "current_total_quantity": normalized_current_total,
        "missing_quantity": missing_quantity,
        "bounded_max_target_total": bounded_max_target_total,
        "initial_state": initial_state,
        "existing_instance_ids": normalized_existing_ids,
        "planned_created_instance_ids": planned_created_instance_ids,
        "planned_instance_records": planned_instance_records,
        "authoritative": False,
        "current_serving": False,
    }
    payload["manifest_id"] = (
        f"ctbatch_{group_fragment}_{_stable_hash(payload)[:12]}"
    )
    payload["manifest_hash"] = _stable_hash(payload)
    return payload


def materialize_create_tier_batch_creation_manifest(
    batch_creation_manifest: Dict[str, Any],
    *,
    repo_root: str = "",
    created_at_ts: str = "",
) -> Dict[str, Any]:
    if not isinstance(batch_creation_manifest, dict):
        raise TypeError("batch_creation_manifest must be a dict")

    normalized_repo_root = os.path.abspath(repo_root or os.path.dirname(os.path.abspath(__file__)))
    manifest_id = _normalize_string(batch_creation_manifest.get("manifest_id"))
    manifest_hash = _normalize_string(batch_creation_manifest.get("manifest_hash"))
    receiving_group_id = _normalize_string(batch_creation_manifest.get("receiving_group_id"))
    rollout_stage_label = _normalize_rollout_stage_label(batch_creation_manifest.get("rollout_stage_label"))
    functionality_labels = _normalize_string_list(batch_creation_manifest.get("functionality_labels") or [])
    planned_records = batch_creation_manifest.get("planned_instance_records") or []
    if not isinstance(planned_records, list):
        raise TypeError("planned_instance_records must be a list")

    materialized_instance_ids: List[str] = []
    materialized_relative_paths: List[str] = []
    already_present_instance_ids: List[str] = []
    already_present_relative_paths: List[str] = []

    for record in planned_records:
        if not isinstance(record, dict):
            raise TypeError("planned_instance_records entries must be dicts")
        instance_id = _normalize_string(record.get("instance_id"))
        relative_file_path = _normalize_string(record.get("relative_file_path"))
        if not instance_id or not relative_file_path:
            raise ValueError("planned instance record requires instance_id and relative_file_path")

        target_path = safe_join(normalized_repo_root, relative_file_path.replace("/", os.sep))
        if os.path.exists(target_path):
            already_present_instance_ids.append(instance_id)
            already_present_relative_paths.append(relative_file_path)
            continue

        instance_payload = {
            "schema_version": "create_tier_generated_instance_record_v1",
            "instance_id": instance_id,
            "manifest_id": manifest_id,
            "manifest_hash": manifest_hash,
            "receiving_group_id": receiving_group_id,
            "family_template_id": _normalize_string(record.get("family_template_id")),
            "functionality_labels": functionality_labels,
            "rollout_stage_label": rollout_stage_label,
            "target_total_quantity": _normalize_int(batch_creation_manifest.get("target_total_quantity"), default=0, minimum=0),
            "initial_state": _normalize_string(record.get("initial_state")) or _normalize_string(batch_creation_manifest.get("initial_state")) or "shadow",
            "relative_file_path": relative_file_path,
            "created_at_ts": _normalize_string(created_at_ts),
            "authoritative": False,
            "current_serving": False,
            "rollback_metadata": {
                "cleanup_relative_path": relative_file_path,
                "removal_mode": "delete_generated_instance_record",
                "preserve_manifest_ref": True,
            },
        }
        instance_payload["instance_record_hash"] = _stable_hash(instance_payload)
        _write_json_atomic(target_path, instance_payload)
        materialized_instance_ids.append(instance_id)
        materialized_relative_paths.append(relative_file_path)

    payload = {
        "schema_version": CREATE_TIER_BATCH_MATERIALIZATION_RESULT_SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "manifest_hash": manifest_hash,
        "receiving_group_id": receiving_group_id,
        "rollout_stage_label": rollout_stage_label,
        "target_total_quantity": _normalize_int(batch_creation_manifest.get("target_total_quantity"), default=0, minimum=0),
        "requested_missing_quantity": _normalize_int(batch_creation_manifest.get("missing_quantity"), default=0, minimum=0),
        "materialized_instance_ids": materialized_instance_ids,
        "materialized_relative_paths": materialized_relative_paths,
        "already_present_instance_ids": already_present_instance_ids,
        "already_present_relative_paths": already_present_relative_paths,
        "written_count": len(materialized_instance_ids),
        "skipped_existing_count": len(already_present_instance_ids),
        "rollback_cleanup_relative_paths": materialized_relative_paths,
        "authoritative": False,
        "current_serving": False,
    }
    payload["result_id"] = f"ctmat_{_bounded_id_fragment(receiving_group_id, max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["result_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_shared_integration_summary(
    batch_creation_manifest: Dict[str, Any],
    *,
    per_instance_results: Optional[Iterable[Dict[str, Any]]] = None,
    shared_task_results: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if not isinstance(batch_creation_manifest, dict):
        raise TypeError("batch_creation_manifest must be a dict")

    planned_created_instance_ids = _normalize_string_list(batch_creation_manifest.get("planned_created_instance_ids") or [])
    normalized_per_instance_results = _normalize_result_rows(per_instance_results, require_instance_id=True)
    normalized_shared_task_results = _normalize_result_rows(shared_task_results, require_instance_id=False)

    per_instance_status_counts = {state: 0 for state in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES}
    shared_task_status_counts = {state: 0 for state in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES}
    latest_instance_state: Dict[str, str] = {}
    for row in normalized_per_instance_results:
        state = row["state"]
        instance_id = row["instance_id"]
        per_instance_status_counts[state] += 1
        latest_instance_state[instance_id] = state

    latest_shared_task_state: Dict[str, str] = {}
    for row in normalized_shared_task_results:
        state = row["state"]
        task_id = row["task_id"]
        shared_task_status_counts[state] += 1
        latest_shared_task_state[task_id] = state

    passed_instance_ids = sorted(
        instance_id for instance_id, state in latest_instance_state.items() if state == "passed"
    )
    failed_instance_ids = sorted(
        instance_id for instance_id, state in latest_instance_state.items() if state == "failed"
    )
    blocked_instance_ids = sorted(
        instance_id for instance_id, state in latest_instance_state.items() if state == "blocked"
    )
    failed_shared_task_ids = sorted(
        task_id for task_id, state in latest_shared_task_state.items() if state == "failed"
    )
    blocked_shared_task_ids = sorted(
        task_id for task_id, state in latest_shared_task_state.items() if state == "blocked"
    )

    missing_instance_result_ids = [
        instance_id for instance_id in planned_created_instance_ids if latest_instance_state.get(instance_id) != "passed"
    ]
    ready_for_next_stage = not failed_instance_ids and not blocked_instance_ids and not failed_shared_task_ids and not blocked_shared_task_ids and not missing_instance_result_ids

    payload = {
        "schema_version": CREATE_TIER_SHARED_INTEGRATION_SUMMARY_SCHEMA_VERSION,
        "manifest_id": _normalize_string(batch_creation_manifest.get("manifest_id")),
        "receiving_group_id": _normalize_string(batch_creation_manifest.get("receiving_group_id")),
        "rollout_stage_label": _normalize_rollout_stage_label(batch_creation_manifest.get("rollout_stage_label")),
        "current_total_quantity": _normalize_int(batch_creation_manifest.get("current_total_quantity"), default=0, minimum=0),
        "target_total_quantity": _normalize_int(batch_creation_manifest.get("target_total_quantity"), default=0, minimum=0),
        "missing_quantity": _normalize_int(batch_creation_manifest.get("missing_quantity"), default=0, minimum=0),
        "planned_created_instance_ids": planned_created_instance_ids,
        "parallelizable_task_count": len(normalized_per_instance_results),
        "serialized_task_count": len(normalized_shared_task_results),
        "per_instance_results": normalized_per_instance_results,
        "shared_task_results": normalized_shared_task_results,
        "per_instance_status_counts": per_instance_status_counts,
        "shared_task_status_counts": shared_task_status_counts,
        "passed_instance_ids": passed_instance_ids,
        "failed_instance_ids": failed_instance_ids,
        "blocked_instance_ids": blocked_instance_ids,
        "failed_shared_task_ids": failed_shared_task_ids,
        "blocked_shared_task_ids": blocked_shared_task_ids,
        "missing_instance_result_ids": missing_instance_result_ids,
        "ready_for_next_stage": ready_for_next_stage,
        "shared_surfaces_serialized": True,
        "authoritative": False,
        "current_serving": False,
    }
    payload["summary_id"] = (
        f"ctint_{_bounded_id_fragment(payload.get('receiving_group_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    if payload["rollout_stage_label"] == "existing_group_widening":
        payload["widening_phase"] = _classify_existing_group_widening_phase(
            target_total_quantity=payload["target_total_quantity"]
        )
    payload["summary_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_wave_shared_integration_summary(
    group_summaries: Optional[Iterable[Dict[str, Any]]],
    *,
    wave_id: str = "",
    rollout_stage_label: str = "new_group_creation",
    required_receiving_group_ids: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    normalized_stage_label = _normalize_rollout_stage_label(rollout_stage_label)
    normalized_required_group_ids = _normalize_string_list(required_receiving_group_ids)

    normalized_group_summaries: List[Dict[str, Any]] = []
    for summary in group_summaries or []:
        if not isinstance(summary, dict):
            raise TypeError("group_summaries must contain dict payloads")
        receiving_group_id = _normalize_string(summary.get("receiving_group_id"))
        if not receiving_group_id:
            raise ValueError("group summaries require receiving_group_id")
        normalized_group_summaries.append(_normalize_json_value(summary))

    normalized_group_summaries.sort(
        key=lambda item: (
            _normalize_string(item.get("receiving_group_id")),
            _normalize_string(item.get("summary_id")),
        )
    )

    summaries_by_group = {
        _normalize_string(summary.get("receiving_group_id")): summary
        for summary in normalized_group_summaries
    }
    reported_group_ids = sorted(summaries_by_group.keys())
    selected_group_ids = normalized_required_group_ids or reported_group_ids
    missing_required_group_ids = [
        group_id for group_id in selected_group_ids if group_id not in summaries_by_group
    ]

    per_instance_status_counts = {state: 0 for state in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES}
    shared_task_status_counts = {state: 0 for state in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES}
    manifest_ids: List[str] = []
    group_summary_ids: List[str] = []
    planned_created_instance_ids: List[str] = []
    ready_group_ids: List[str] = []
    blocked_group_ids: List[str] = []
    group_ready_map: Dict[str, bool] = {}
    parallelizable_task_count = 0
    serialized_task_count = 0
    current_total_quantity_sum = 0
    target_total_quantity_sum = 0
    max_target_total_quantity = 0

    for group_id in selected_group_ids:
        summary = summaries_by_group.get(group_id)
        if not isinstance(summary, dict):
            continue
        manifest_ids.append(_normalize_string(summary.get("manifest_id")))
        group_summary_ids.append(_normalize_string(summary.get("summary_id")))
        planned_created_instance_ids.extend(summary.get("planned_created_instance_ids") or [])
        parallelizable_task_count += _normalize_int(summary.get("parallelizable_task_count"), default=0, minimum=0)
        serialized_task_count += _normalize_int(summary.get("serialized_task_count"), default=0, minimum=0)
        current_total_quantity_sum += _normalize_int(summary.get("current_total_quantity"), default=0, minimum=0)
        normalized_target_total_quantity = _normalize_int(summary.get("target_total_quantity"), default=0, minimum=0)
        target_total_quantity_sum += normalized_target_total_quantity
        max_target_total_quantity = max(max_target_total_quantity, normalized_target_total_quantity)

        for state in SUPPORTED_CREATE_TIER_INTEGRATION_RESULT_STATES:
            per_instance_status_counts[state] += _normalize_int(
                (summary.get("per_instance_status_counts") or {}).get(state),
                default=0,
                minimum=0,
            )
            shared_task_status_counts[state] += _normalize_int(
                (summary.get("shared_task_status_counts") or {}).get(state),
                default=0,
                minimum=0,
            )

        ready = bool(summary.get("ready_for_next_stage"))
        group_ready_map[group_id] = ready
        if ready:
            ready_group_ids.append(group_id)
        else:
            blocked_group_ids.append(group_id)

    ready_for_validation = (
        bool(selected_group_ids)
        and not missing_required_group_ids
        and len(ready_group_ids) == len(selected_group_ids)
    )

    payload = {
        "schema_version": CREATE_TIER_WAVE_SHARED_INTEGRATION_SUMMARY_SCHEMA_VERSION,
        "wave_id": _normalize_string(wave_id),
        "rollout_stage_label": normalized_stage_label,
        "required_receiving_group_ids": selected_group_ids,
        "reported_receiving_group_ids": reported_group_ids,
        "missing_required_group_ids": missing_required_group_ids,
        "manifest_ids": _normalize_string_list(manifest_ids),
        "group_summary_ids": _normalize_string_list(group_summary_ids),
        "group_summaries": normalized_group_summaries,
        "planned_created_instance_ids": _normalize_string_list(planned_created_instance_ids),
        "planned_created_instance_total": len(_normalize_string_list(planned_created_instance_ids)),
        "current_total_quantity_sum": current_total_quantity_sum,
        "target_total_quantity_sum": target_total_quantity_sum,
        "max_target_total_quantity": max_target_total_quantity,
        "parallelizable_task_count": parallelizable_task_count,
        "serialized_task_count": serialized_task_count,
        "per_instance_status_counts": per_instance_status_counts,
        "shared_task_status_counts": shared_task_status_counts,
        "group_ready_map": group_ready_map,
        "ready_group_ids": ready_group_ids,
        "blocked_group_ids": blocked_group_ids,
        "ready_for_validation": ready_for_validation,
        "ready_for_next_stage": ready_for_validation,
        "shared_surfaces_serialized": True,
        "authoritative": False,
        "current_serving": False,
    }
    payload["summary_id"] = (
        f"ctwave_{_bounded_id_fragment(payload.get('wave_id') or normalized_stage_label, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    if normalized_stage_label == "existing_group_widening":
        payload["widening_phase"] = _classify_existing_group_widening_phase(
            target_total_quantity=max_target_total_quantity
        )
    payload["summary_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_wave_validation_summary(
    *,
    rollout_stage_label: str,
    group_results: Optional[Iterable[Dict[str, Any]]],
) -> Dict[str, Any]:
    normalized_stage_label = _normalize_rollout_stage_label(rollout_stage_label)

    normalized_group_results: List[Dict[str, Any]] = []
    for item in group_results or []:
        if not isinstance(item, dict):
            raise TypeError("group_results must contain dict payloads")

        receiving_group_id = _normalize_string(item.get("receiving_group_id"))
        functionality_label = _normalize_string(item.get("functionality_label"))
        shared_integration_ready = bool(item.get("shared_integration_ready"))
        blocking_reasons = _normalize_string_list(item.get("blocking_reasons") or [])
        raw_target_total_quantity = item.get("target_total_quantity")
        target_total_quantity = _normalize_int(raw_target_total_quantity, default=0, minimum=0)

        normalized_item = {
            "receiving_group_id": receiving_group_id,
            "functionality_label": functionality_label,
            "shared_integration_ready": shared_integration_ready,
        }
        if raw_target_total_quantity is not None:
            normalized_item["target_total_quantity"] = target_total_quantity

        if normalized_stage_label == "new_group_creation":
            group_review_ready = bool(item.get("group_review_ready"))
            validation_passed = bool(group_review_ready and shared_integration_ready)
            if not blocking_reasons:
                if not group_review_ready:
                    blocking_reasons.append("group_review_not_ready")
                if not shared_integration_ready:
                    blocking_reasons.append("shared_integration_not_ready")
            normalized_item.update(
                {
                    "group_review_ready": group_review_ready,
                    "validation_passed": validation_passed,
                    "blocking_reasons": blocking_reasons,
                }
            )
        else:
            widening_manifest_ready = bool(item.get("widening_manifest_ready"))
            validation_passed = bool(widening_manifest_ready and shared_integration_ready)
            if not blocking_reasons:
                if not widening_manifest_ready:
                    blocking_reasons.append("widening_manifest_not_ready")
                if not shared_integration_ready:
                    blocking_reasons.append("shared_integration_not_ready")
            normalized_item.update(
                {
                    "widening_manifest_ready": widening_manifest_ready,
                    "validation_passed": validation_passed,
                    "blocking_reasons": blocking_reasons,
                }
            )

        normalized_group_results.append(normalized_item)

    selected_group_ids = [item["receiving_group_id"] for item in normalized_group_results]
    passed_group_ids = sorted(
        item["receiving_group_id"] for item in normalized_group_results if item["validation_passed"]
    )
    blocked_group_ids = sorted(
        item["receiving_group_id"] for item in normalized_group_results if not item["validation_passed"]
    )
    wave_gate_result = "passed" if not blocked_group_ids and selected_group_ids else "blocked"

    payload = {
        "schema_version": CREATE_TIER_WAVE_VALIDATION_SUMMARY_SCHEMA_VERSION,
        "rollout_stage_label": normalized_stage_label,
        "selected_group_ids": selected_group_ids,
        "group_results": normalized_group_results,
        "passed_group_ids": passed_group_ids,
        "blocked_group_ids": blocked_group_ids,
        "wave_gate_result": wave_gate_result,
        "authoritative": False,
        "current_serving": False,
    }
    if normalized_stage_label == "new_group_creation":
        payload["ready_for_safe_eval"] = wave_gate_result == "passed"
        payload["ready_for_stage_c"] = wave_gate_result == "passed"
    else:
        widening_phase = _classify_existing_group_widening_phase(
            target_total_quantity=max(
                (
                    _normalize_int(item.get("target_total_quantity"), default=0, minimum=0)
                    for item in normalized_group_results
                ),
                default=0,
            )
        )
        payload["widening_phase"] = widening_phase
        if widening_phase == "intermediate_widen_to_1000":
            payload["ready_for_safe_eval"] = wave_gate_result == "passed"
            payload["ready_for_higher_target_widening"] = wave_gate_result == "passed"
        else:
            payload["ready_for_parent_release"] = wave_gate_result == "passed"

    payload["summary_id"] = (
        f"ctwaveval_{_bounded_id_fragment(normalized_stage_label, max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["summary_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_initial_event_selection(
    factory_descriptor: Dict[str, Any],
    *,
    requested_group_count: int = 1,
    requested_instance_count: int = 1,
    materially_pressured: bool = True,
    explicit_paired_purpose: bool = False,
    explicit_three_instance_justification: bool = False,
    reason_summary: str = "",
    existing_group_count: int = 0,
    existing_instance_count: int = 0,
) -> Dict[str, Any]:
    if not isinstance(factory_descriptor, dict):
        raise TypeError("factory_descriptor must be a dict")

    creation_limits = _normalize_creation_limits(factory_descriptor.get("creation_limits") or _DEFAULT_FACTORY_CREATION_LIMITS)
    normalized_existing_groups = _normalize_int(existing_group_count, default=0, minimum=0)
    normalized_existing_instances = _normalize_int(existing_instance_count, default=0, minimum=0)
    normalized_requested_groups = _normalize_int(requested_group_count, default=1, minimum=0)
    normalized_requested_instances = _normalize_int(requested_instance_count, default=1, minimum=0)
    normalized_reason_summary = _normalize_string(reason_summary)

    initial_event = normalized_existing_groups == 0 and normalized_existing_instances == 0
    recommended_group_count = 1 if materially_pressured and creation_limits["max_concurrent_groups"] > 0 else 0
    recommended_instance_count = 1 if materially_pressured and creation_limits["max_concurrent_instances"] > 0 else 0
    rejection_reasons: List[str] = []

    if not initial_event:
        rejection_reasons.append("initial_event_guard_requires_zero_existing_counts")

    if not materially_pressured:
        if normalized_requested_groups > 0 or normalized_requested_instances > 0:
            rejection_reasons.append("unpressured_groups_must_remain_zero")
    else:
        if normalized_requested_groups > 1:
            rejection_reasons.append("initial_event_group_count_exceeds_one")
        if normalized_requested_instances == 2 and not explicit_paired_purpose:
            rejection_reasons.append("second_instance_requires_explicit_paired_purpose")
        if normalized_requested_instances >= 3 and not explicit_three_instance_justification:
            rejection_reasons.append("third_instance_requires_stronger_justification")
        if normalized_requested_instances > creation_limits["per_event_instance_cap"]:
            rejection_reasons.append("requested_instances_exceed_per_event_cap")
        if normalized_requested_groups > creation_limits["per_event_group_cap"]:
            rejection_reasons.append("requested_groups_exceed_per_event_cap")
        if normalized_requested_instances > creation_limits["max_concurrent_instances"]:
            rejection_reasons.append("requested_instances_exceed_max_concurrent_instances")
        if normalized_requested_groups > creation_limits["max_concurrent_groups"]:
            rejection_reasons.append("requested_groups_exceed_max_concurrent_groups")

    accepted = not rejection_reasons
    approved_group_count = min(normalized_requested_groups, creation_limits["per_event_group_cap"], creation_limits["max_concurrent_groups"]) if accepted else 0
    approved_instance_count = min(
        normalized_requested_instances,
        creation_limits["per_event_instance_cap"],
        creation_limits["max_concurrent_instances"],
    ) if accepted else 0
    if accepted and not materially_pressured:
        approved_group_count = 0
        approved_instance_count = 0

    payload = {
        "schema_version": CREATE_TIER_INITIAL_EVENT_SELECTION_SCHEMA_VERSION,
        "factory_id": _normalize_string(factory_descriptor.get("factory_id")),
        "family_template_id": _normalize_string(factory_descriptor.get("family_template_id")),
        "phase": "initial_event_guard" if initial_event else "repeat_event_rejected",
        "materially_pressured": bool(materially_pressured),
        "requested_group_count": normalized_requested_groups,
        "requested_instance_count": normalized_requested_instances,
        "approved_group_count": approved_group_count,
        "approved_instance_count": approved_instance_count,
        "recommended_group_count": recommended_group_count,
        "recommended_instance_count": recommended_instance_count,
        "explicit_paired_purpose": bool(explicit_paired_purpose),
        "explicit_three_instance_justification": bool(explicit_three_instance_justification),
        "reason_summary": normalized_reason_summary,
        "creation_limits": creation_limits,
        "accepted": accepted,
        "rejection_reasons": rejection_reasons,
        "authoritative": False,
        "current_serving": False,
        "bounded": approved_group_count <= creation_limits["per_event_group_cap"] and approved_instance_count <= creation_limits["per_event_instance_cap"],
    }
    payload["selection_id"] = (
        f"ctsel_{_bounded_id_fragment(payload.get('factory_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    )
    payload["selection_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_event_sequence_review(
    factory_descriptor: Dict[str, Any],
    *,
    requested_action: str = "initial_event",
    materially_pressured: bool = True,
    prior_event_validated: bool = False,
    prior_event_utilized: bool = False,
    strongest_no_new_tier_alternative_sufficient: bool = False,
    retirement_candidate_count: int = 0,
    existing_group_count: int = 0,
    existing_instance_count: int = 0,
    reason_summary: str = "",
) -> Dict[str, Any]:
    if not isinstance(factory_descriptor, dict):
        raise TypeError("factory_descriptor must be a dict")

    normalized_action = _normalize_string(requested_action) or "initial_event"
    if normalized_action not in SUPPORTED_CREATE_TIER_SEQUENCE_ACTIONS:
        raise ValueError(f"unsupported create-tier sequence action: {normalized_action}")

    creation_limits = _normalize_creation_limits(factory_descriptor.get("creation_limits") or _DEFAULT_FACTORY_CREATION_LIMITS)
    normalized_existing_groups = _normalize_int(existing_group_count, default=0, minimum=0)
    normalized_existing_instances = _normalize_int(existing_instance_count, default=0, minimum=0)
    normalized_retirement_candidates = _normalize_int(retirement_candidate_count, default=0, minimum=0)
    normalized_reason_summary = _normalize_string(reason_summary)

    remaining_groups = max(0, creation_limits["max_concurrent_groups"] - normalized_existing_groups)
    remaining_instances = max(0, creation_limits["max_concurrent_instances"] - normalized_existing_instances)
    refusal_reasons: List[str] = []
    planned_group_count = 0
    planned_instance_count = 0

    if normalized_action == "initial_event":
        selection = build_create_tier_initial_event_selection(
            factory_descriptor,
            requested_group_count=1 if materially_pressured else 0,
            requested_instance_count=1 if materially_pressured else 0,
            materially_pressured=materially_pressured,
            reason_summary=normalized_reason_summary,
            existing_group_count=normalized_existing_groups,
            existing_instance_count=normalized_existing_instances,
        )
        planned_group_count = int(selection.get("approved_group_count") or 0)
        planned_instance_count = int(selection.get("approved_instance_count") or 0)
        refusal_reasons.extend(list(selection.get("rejection_reasons") or []))
    elif normalized_action == "deepen_existing_group":
        if normalized_existing_groups <= 0:
            refusal_reasons.append("deepen_requires_existing_group")
        if not prior_event_validated:
            refusal_reasons.append("deepen_requires_prior_event_validated")
        if not prior_event_utilized:
            refusal_reasons.append("deepen_requires_prior_event_utilization")
        if not materially_pressured:
            refusal_reasons.append("deepen_requires_material_pressure")
        if strongest_no_new_tier_alternative_sufficient:
            refusal_reasons.append("deepen_deferred_to_stronger_no_new_tier_alternative")
        if remaining_instances <= 0:
            refusal_reasons.append("deepen_blocked_at_instance_capacity")
        if not refusal_reasons:
            planned_group_count = 0
            planned_instance_count = min(
                creation_limits["scale_step_instances"],
                creation_limits["per_event_instance_cap"],
                remaining_instances,
            )
    else:
        if normalized_existing_groups <= 0:
            refusal_reasons.append("next_group_requires_prior_group")
        if not prior_event_validated:
            refusal_reasons.append("next_group_requires_prior_event_validated")
        if not prior_event_utilized:
            refusal_reasons.append("next_group_requires_prior_event_utilization")
        if not materially_pressured:
            refusal_reasons.append("next_group_requires_material_pressure")
        if strongest_no_new_tier_alternative_sufficient:
            refusal_reasons.append("next_group_blocked_by_stronger_no_new_tier_alternative")
        if normalized_retirement_candidates > 0:
            refusal_reasons.append("next_group_requires_retirement_review_first")
        if remaining_groups <= 0:
            refusal_reasons.append("next_group_blocked_at_group_capacity")
        if remaining_instances <= 0:
            refusal_reasons.append("next_group_blocked_at_instance_capacity")
        if not refusal_reasons:
            planned_group_count = min(1, creation_limits["per_event_group_cap"], remaining_groups)
            planned_instance_count = min(
                creation_limits["initial_instance_count"],
                creation_limits["per_event_instance_cap"],
                remaining_instances,
            )

    accepted = not refusal_reasons
    payload = {
        "schema_version": CREATE_TIER_EVENT_SEQUENCE_REVIEW_SCHEMA_VERSION,
        "factory_id": _normalize_string(factory_descriptor.get("factory_id")),
        "family_template_id": _normalize_string(factory_descriptor.get("family_template_id")),
        "requested_action": normalized_action,
        "materially_pressured": bool(materially_pressured),
        "prior_event_validated": bool(prior_event_validated),
        "prior_event_utilized": bool(prior_event_utilized),
        "strongest_no_new_tier_alternative_sufficient": bool(strongest_no_new_tier_alternative_sufficient),
        "retirement_candidate_count": normalized_retirement_candidates,
        "existing_group_count": normalized_existing_groups,
        "existing_instance_count": normalized_existing_instances,
        "remaining_group_capacity": remaining_groups,
        "remaining_instance_capacity": remaining_instances,
        "planned_group_count": planned_group_count if accepted else 0,
        "planned_instance_count": planned_instance_count if accepted else 0,
        "reason_summary": normalized_reason_summary,
        "accepted": accepted,
        "refusal_reasons": refusal_reasons,
        "creation_limits": creation_limits,
        "authoritative": False,
        "current_serving": False,
        "bounded": (planned_group_count if accepted else 0) <= creation_limits["per_event_group_cap"] and (planned_instance_count if accepted else 0) <= creation_limits["per_event_instance_cap"],
    }
    payload["review_id"] = f"ctseq_{_bounded_id_fragment(payload.get('factory_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_lifecycle_review(
    event_contract: Dict[str, Any],
    *,
    requested_action: str = "rollback_created_instances",
    rollback_contract: Optional[Dict[str, Any]] = None,
    retirement_reason: str = "",
    lineage_preserved: bool = False,
    audit_trace_present: bool = False,
    shared_template_mutation_detected: bool = False,
    tier1_decisions_changed: bool = False,
) -> Dict[str, Any]:
    if not isinstance(event_contract, dict):
        raise TypeError("event_contract must be a dict")

    normalized_action = _normalize_string(requested_action) or "rollback_created_instances"
    if normalized_action not in SUPPORTED_CREATE_TIER_LIFECYCLE_ACTIONS:
        raise ValueError(f"unsupported create-tier lifecycle action: {normalized_action}")

    normalized_rollback = rollback_contract if isinstance(rollback_contract, dict) else {}
    created_instance_ids = _normalize_string_list(
        normalized_rollback.get("remove_created_instance_ids")
        or event_contract.get("created_instance_ids")
        or []
    )
    artifact_cleanup_paths = _normalize_string_list(normalized_rollback.get("artifact_cleanup_paths") or [])
    normalized_retirement_reason = _normalize_string(retirement_reason)
    refusal_reasons: List[str] = []

    if not created_instance_ids:
        refusal_reasons.append("created_instance_ids_required")
    if shared_template_mutation_detected:
        refusal_reasons.append("shared_template_mutation_detected")
    if tier1_decisions_changed:
        refusal_reasons.append("tier1_decisions_changed")

    if normalized_action == "rollback_created_instances":
        if not artifact_cleanup_paths:
            refusal_reasons.append("rollback_requires_artifact_cleanup_paths")
    elif normalized_action == "retire_created_instance":
        if not lineage_preserved:
            refusal_reasons.append("retirement_requires_lineage_preserved")
        if not normalized_retirement_reason:
            refusal_reasons.append("retirement_reason_required")
    else:
        if not lineage_preserved:
            refusal_reasons.append("garbage_collection_requires_lineage_preserved")
        if not audit_trace_present:
            refusal_reasons.append("garbage_collection_requires_audit_trace")

    accepted = not refusal_reasons
    payload = {
        "schema_version": CREATE_TIER_LIFECYCLE_REVIEW_SCHEMA_VERSION,
        "event_id": _normalize_string(event_contract.get("event_id")),
        "factory_id": _normalize_string(event_contract.get("factory_id")),
        "family_id": _normalize_string(event_contract.get("family_id")),
        "requested_action": normalized_action,
        "created_instance_ids": created_instance_ids,
        "artifact_cleanup_paths": artifact_cleanup_paths,
        "retirement_reason": normalized_retirement_reason,
        "lineage_preserved": bool(lineage_preserved),
        "audit_trace_present": bool(audit_trace_present),
        "shared_template_mutation_detected": bool(shared_template_mutation_detected),
        "tier1_decisions_changed": bool(tier1_decisions_changed),
        "accepted": accepted,
        "refusal_reasons": refusal_reasons,
        "planned_cleanup_instance_ids": created_instance_ids if accepted else [],
        "planned_artifact_cleanup_paths": artifact_cleanup_paths if accepted else [],
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = f"ctlife_{_bounded_id_fragment(payload.get('family_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_runtime_gate_review(
    event_contract: Dict[str, Any],
    *,
    runtime_sensitive: bool = False,
    focused_pytest_passed: bool = False,
    repo_eval_passed: bool = False,
    hardware_preflight_ok: bool = False,
    serving_family_truth_unchanged: bool = False,
    safe_eval_artifact_present: bool = False,
    safe_eval_ok: bool = False,
    safe_eval_state_restored: bool = False,
    ops_status_ok: bool = False,
) -> Dict[str, Any]:
    if not isinstance(event_contract, dict):
        raise TypeError("event_contract must be a dict")

    runtime_gate_mode = "safe_runtime_eval_required" if runtime_sensitive else "repo_eval_only"
    required_gate_names = [
        "focused_pytest",
        "repo_eval",
        "hardware_preflight",
        "serving_family_truth",
    ]
    if runtime_gate_mode == "safe_runtime_eval_required":
        required_gate_names.extend([
            "safe_runtime_eval_artifact",
            "safe_runtime_eval_ok",
            "safe_runtime_eval_state_restored",
            "ops_status",
        ])

    satisfied_gate_names: List[str] = []
    refusal_reasons: List[str] = []

    if focused_pytest_passed:
        satisfied_gate_names.append("focused_pytest")
    else:
        refusal_reasons.append("focused_pytest_required")

    if repo_eval_passed:
        satisfied_gate_names.append("repo_eval")
    else:
        refusal_reasons.append("repo_eval_required")

    if hardware_preflight_ok:
        satisfied_gate_names.append("hardware_preflight")
    else:
        refusal_reasons.append("hardware_preflight_required")

    if serving_family_truth_unchanged:
        satisfied_gate_names.append("serving_family_truth")
    else:
        refusal_reasons.append("serving_family_truth_drift_detected")

    if runtime_gate_mode == "safe_runtime_eval_required":
        if safe_eval_artifact_present:
            satisfied_gate_names.append("safe_runtime_eval_artifact")
        else:
            refusal_reasons.append("safe_runtime_eval_evidence_missing")

        if safe_eval_ok:
            satisfied_gate_names.append("safe_runtime_eval_ok")
        else:
            refusal_reasons.append("safe_runtime_eval_failed")

        if safe_eval_state_restored:
            satisfied_gate_names.append("safe_runtime_eval_state_restored")
        else:
            refusal_reasons.append("safe_runtime_eval_state_not_restored")

        if ops_status_ok:
            satisfied_gate_names.append("ops_status")
        else:
            refusal_reasons.append("ops_status_required")

    accepted = not refusal_reasons
    payload = {
        "schema_version": CREATE_TIER_RUNTIME_GATE_REVIEW_SCHEMA_VERSION,
        "event_id": _normalize_string(event_contract.get("event_id")),
        "factory_id": _normalize_string(event_contract.get("factory_id")),
        "family_id": _normalize_string(event_contract.get("family_id")),
        "runtime_gate_mode": runtime_gate_mode,
        "runtime_sensitive": bool(runtime_sensitive),
        "focused_pytest_passed": bool(focused_pytest_passed),
        "repo_eval_passed": bool(repo_eval_passed),
        "hardware_preflight_ok": bool(hardware_preflight_ok),
        "serving_family_truth_unchanged": bool(serving_family_truth_unchanged),
        "safe_eval_artifact_present": bool(safe_eval_artifact_present),
        "safe_eval_ok": bool(safe_eval_ok),
        "safe_eval_state_restored": bool(safe_eval_state_restored),
        "ops_status_ok": bool(ops_status_ok),
        "required_gate_names": required_gate_names,
        "satisfied_gate_names": satisfied_gate_names,
        "accepted": accepted,
        "refusal_reasons": refusal_reasons,
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = f"ctgate_{_bounded_id_fragment(payload.get('family_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["review_hash"] = _stable_hash(payload)
    return payload


def build_create_tier_composed_event_review(
    event_contract: Dict[str, Any],
    *,
    initial_selection_review: Optional[Dict[str, Any]] = None,
    apply_checkpoint_review: Optional[Dict[str, Any]] = None,
    sequence_review: Optional[Dict[str, Any]] = None,
    lifecycle_review: Optional[Dict[str, Any]] = None,
    runtime_gate_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(event_contract, dict):
        raise TypeError("event_contract must be a dict")

    stage_reviews = {
        "initial_selection": initial_selection_review if isinstance(initial_selection_review, dict) else {},
        "apply_checkpoint": apply_checkpoint_review if isinstance(apply_checkpoint_review, dict) else {},
        "sequence_review": sequence_review if isinstance(sequence_review, dict) else {},
        "lifecycle_review": lifecycle_review if isinstance(lifecycle_review, dict) else {},
        "runtime_gate": runtime_gate_review if isinstance(runtime_gate_review, dict) else {},
    }
    stage_order = [
        "initial_selection",
        "apply_checkpoint",
        "sequence_review",
        "lifecycle_review",
        "runtime_gate",
    ]

    stage_results = {
        "initial_selection": bool(stage_reviews["initial_selection"].get("accepted")),
        "apply_checkpoint": bool(stage_reviews["apply_checkpoint"].get("invariance_passed")),
        "sequence_review": bool(stage_reviews["sequence_review"].get("accepted")),
        "lifecycle_review": bool(stage_reviews["lifecycle_review"].get("accepted")),
        "runtime_gate": bool(stage_reviews["runtime_gate"].get("accepted")),
    }

    stage_reason_map = {
        "initial_selection": _normalize_string_list(stage_reviews["initial_selection"].get("rejection_reasons") or []),
        "apply_checkpoint": _normalize_string_list(
            [] if stage_results["apply_checkpoint"] else ["apply_checkpoint_invariance_failed"]
        ),
        "sequence_review": _normalize_string_list(stage_reviews["sequence_review"].get("refusal_reasons") or []),
        "lifecycle_review": _normalize_string_list(stage_reviews["lifecycle_review"].get("refusal_reasons") or []),
        "runtime_gate": _normalize_string_list(stage_reviews["runtime_gate"].get("refusal_reasons") or []),
    }

    blocking_stage = ""
    refusal_reasons: List[str] = []
    for stage_name in stage_order:
        if not stage_results[stage_name]:
            if not blocking_stage:
                blocking_stage = stage_name
            refusal_reasons.extend(stage_reason_map[stage_name])

    accepted = not blocking_stage
    payload = {
        "schema_version": CREATE_TIER_COMPOSED_EVENT_REVIEW_SCHEMA_VERSION,
        "event_id": _normalize_string(event_contract.get("event_id")),
        "factory_id": _normalize_string(event_contract.get("factory_id")),
        "family_id": _normalize_string(event_contract.get("family_id")),
        "stage_order": stage_order,
        "stage_results": stage_results,
        "stage_reason_map": stage_reason_map,
        "blocking_stage": blocking_stage,
        "accepted": accepted,
        "refusal_reasons": _normalize_string_list(refusal_reasons),
        "authoritative": False,
        "current_serving": False,
    }
    payload["review_id"] = f"ctcomp_{_bounded_id_fragment(payload.get('family_id'), max_len=32)}_{_stable_hash(payload)[:12]}"
    payload["review_hash"] = _stable_hash(payload)
    return payload
