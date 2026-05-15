from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from module_create_tier_event import build_create_tier_family_factory_descriptor


_TIER_FLAG_RE = re.compile(r"^tier(\d+)_enabled$")
_SUPPORTED_ROUTING_STATES = ("active", "shadow", "draining", "standby", "retired")
_SUPPORTED_GUARDED_CANDIDATE_STATES = ("documentation_only", "shadow_review", "deferred")
_SUPPORTED_BOUNDED_SWITCH_KINDS = (
    "review_only",
    "hold_defer",
    "reject",
    "mirror",
    "schedule_follow_up",
    "role_switch",
)

_BOUNDED_SWITCH_METADATA: Dict[str, Dict[str, Any]] = {
    "review_only": {
        "switch_kind": "review_only",
        "switch_label": "review-only",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "review_only",
        "rollback_mode": "remove_review_surface_only",
    },
    "hold_defer": {
        "switch_kind": "hold_defer",
        "switch_label": "hold/defer",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "holding",
        "rollback_mode": "move_out_of_holding_space",
    },
    "reject": {
        "switch_kind": "reject",
        "switch_label": "reject",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "not_matching",
        "rollback_mode": "remove_optional_rejection_artifact_only",
    },
    "mirror": {
        "switch_kind": "mirror",
        "switch_label": "mirror",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "active",
        "rollback_mode": "disable_mirror_surface_only",
    },
    "schedule_follow_up": {
        "switch_kind": "schedule_follow_up",
        "switch_label": "schedule follow-up",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "queued",
        "rollback_mode": "cancel_follow_up_tasks_only",
    },
    "role_switch": {
        "switch_kind": "role_switch",
        "switch_label": "role-switch",
        "runtime_effect": "continue_runtime",
        "pause_required": False,
        "non_authoritative": True,
        "default_state": "later_available",
        "rollback_mode": "remove_non_serving_role_switch_path_only",
    },
}

_TIER_FAMILY_METADATA: Dict[str, Dict[str, Any]] = {
    "schedule_mirror": {
        "family_id": "schedule_mirror",
        "config_root": "mirror_tiers.schedule_mirror",
        "purpose": "Read-only mirror of Tier 1 schedule outputs with deterministic delta and checksum layers.",
        "level_specs": [
            {
                "level": 1,
                "flag": "enabled",
                "outputs": [
                    "relational_state.derived.mirror_schedule_summary",
                    "relational_state.derived.mirror_schedule_summary_hash",
                ],
            },
            {
                "level": 2,
                "flag": "tier2_enabled",
                "outputs": [
                    "relational_state.derived.mirror_schedule_delta",
                ],
            },
            {
                "level": 3,
                "flag": "tier3_enabled",
                "outputs": [
                    "relational_state.derived.schedule_mirror_tier3",
                    "relational_state.derived.schedule_mirror_tier3_hash",
                ],
            },
        ],
        "passthrough_flags": ["allow_advisory"],
        "supported_routing_states": list(_SUPPORTED_ROUTING_STATES),
        "supported_switch_kinds": ["mirror", "schedule_follow_up"],
        "invariants": [
            "read_only",
            "deterministic_hashes",
            "reversible_toggles",
        ],
        "verification": [
            "tests/test_mirror_tiers.py",
            "scripts/metrics_table.py --json",
            "scripts/ops_status_report.py --json",
            "AI Brain: eval",
        ],
    },
    "simultaneous_context_match": {
        "family_id": "simultaneous_context_match",
        "config_root": "tier_families.simultaneous_context_match",
        "purpose": "Non-authoritative simultaneous context family for bounded active review and standby comparison across foundational support and optional-reference artifact outputs.",
        "level_specs": [
            {
                "level": 1,
                "flag": "enabled",
                "outputs": [
                    "relational_state.derived.foundational_tier_hook_summary",
                    "relational_state.derived.foundational_active_space_reference_summary",
                ],
            },
            {
                "level": 2,
                "flag": "tier2_enabled",
                "outputs": [
                    "relational_state.derived.foundational_optional_reference_non_match_artifact",
                    "relational_state.derived.mirrored_parameter_review_summary",
                    "relational_state.derived.multi_location_comprehension_review_summary",
                ],
            },
        ],
        "passthrough_flags": [],
        "supported_routing_states": list(_SUPPORTED_ROUTING_STATES),
        "supported_switch_kinds": ["review_only", "reject", "role_switch"],
        "invariants": [
            "non_authoritative",
            "non_authoritative_active_review_or_standby_only",
            "reversible_additive_outputs",
        ],
        "verification": [
            "tests/test_mirror_tiers.py",
            "tests/test_ops_status_report_runtime.py",
            "scripts/ops_status_report.py --json",
            "AI Brain: eval",
        ],
    }
}

_GUARDED_FAMILY_CANDIDATE_METADATA: Dict[str, Dict[str, Any]] = {
    "simultaneous_context_match": {
        "family_id": "simultaneous_context_match",
        "config_root": "tier_families.simultaneous_context_match",
        "guarded_hook_root": "tier_families.simultaneous_context_match.guarded_shadow_hook",
        "default_candidate_state": "documentation_only",
        "first_rehearsal_state": "shadow",
        "later_dormant_state": "standby",
        "allowed_review_states": list(_SUPPORTED_GUARDED_CANDIDATE_STATES),
        "disallowed_promotions": [
            "live_serving_state",
            "scheduler_authority",
            "top_tier_authority",
            "routing_control",
            "current_match_authority",
        ],
        "rollback_mode": "documentation_only_remove_or_ignore",
        "non_authority_reason_summary": (
            "future family remains documentation-only and non-authoritative until a later guarded rehearsal "
            "is explicitly approved"
        ),
        "determinism_expectations": [
            "guard_row_stable_for_same_inputs",
            "tier1_activation_unchanged",
            "no_runtime_timestamp_dependency",
        ],
        "invariance_expectations": [
            "tier1_decisions_unchanged",
            "scheduler_authority_unchanged",
            "dashboard_health_unchanged",
            "descriptor_optional_to_runtime",
            "clean_rollback_when_absent",
        ],
    }
}


def _stable_review_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_tier_family_metadata(family_id: str) -> Dict[str, Any]:
    metadata = _TIER_FAMILY_METADATA.get(str(family_id), {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def get_guarded_family_candidate_metadata(family_id: str) -> Dict[str, Any]:
    metadata = _GUARDED_FAMILY_CANDIDATE_METADATA.get(str(family_id), {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def get_bounded_switch_metadata(switch_kind: str) -> Dict[str, Any]:
    metadata = _BOUNDED_SWITCH_METADATA.get(str(switch_kind), {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def build_bounded_runtime_switch(
    switch_kind: str,
    *,
    family_id: str = "",
    configured: bool = True,
    engaged: bool = False,
    state: str = "",
    reason_summary: str = "",
    evidence_refs: Optional[Iterable[Any]] = None,
    target_space: str = "",
    policy_rule_id: str = "",
    scheduled_task_labels: Optional[Iterable[Any]] = None,
) -> Dict[str, Any]:
    metadata = get_bounded_switch_metadata(str(switch_kind))
    if not metadata:
        raise KeyError(f"unsupported bounded runtime switch: {switch_kind}")

    normalized_evidence_refs = [str(value) for value in evidence_refs or [] if str(value or "").strip()]
    normalized_task_labels = [str(value) for value in scheduled_task_labels or [] if str(value or "").strip()]
    normalized_state = str(state or metadata.get("default_state") or "").strip()

    return {
        "switch_kind": str(metadata.get("switch_kind") or switch_kind),
        "switch_label": str(metadata.get("switch_label") or switch_kind),
        "family_id": str(family_id or ""),
        "configured": bool(configured),
        "engaged": bool(engaged),
        "state": normalized_state,
        "reason_summary": str(reason_summary or ""),
        "runtime_effect": str(metadata.get("runtime_effect") or "continue_runtime"),
        "pause_required": bool(metadata.get("pause_required", False)),
        "non_authoritative": bool(metadata.get("non_authoritative", True)),
        "target_space": str(target_space or ""),
        "policy_rule_id": str(policy_rule_id or ""),
        "scheduled_task_labels": sorted(dict.fromkeys(normalized_task_labels)),
        "evidence_refs": sorted(dict.fromkeys(normalized_evidence_refs)),
        "rollback_mode": str(metadata.get("rollback_mode") or ""),
    }


def summarize_bounded_runtime_switches(switch_rows: Optional[Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
    normalized_rows: List[Dict[str, Any]] = []
    configured_kinds: List[str] = []
    engaged_kinds: List[str] = []
    family_ids: List[str] = []

    for row in switch_rows or []:
        if not isinstance(row, dict):
            continue
        switch_kind = str(row.get("switch_kind") or "").strip()
        if not switch_kind:
            continue
        metadata = get_bounded_switch_metadata(switch_kind)
        if not metadata:
            continue
        normalized = build_bounded_runtime_switch(
            switch_kind,
            family_id=str(row.get("family_id") or ""),
            configured=bool(row.get("configured", True)),
            engaged=bool(row.get("engaged", False)),
            state=str(row.get("state") or metadata.get("default_state") or ""),
            reason_summary=str(row.get("reason_summary") or ""),
            evidence_refs=row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else [],
            target_space=str(row.get("target_space") or ""),
            policy_rule_id=str(row.get("policy_rule_id") or ""),
            scheduled_task_labels=(
                row.get("scheduled_task_labels") if isinstance(row.get("scheduled_task_labels"), list) else []
            ),
        )
        normalized_rows.append(normalized)
        if normalized["configured"] and switch_kind not in configured_kinds:
            configured_kinds.append(switch_kind)
        if normalized["engaged"] and switch_kind not in engaged_kinds:
            engaged_kinds.append(switch_kind)
        family_id = str(normalized.get("family_id") or "")
        if family_id and family_id not in family_ids:
            family_ids.append(family_id)

    normalized_rows.sort(key=lambda row: (str(row.get("family_id") or ""), str(row.get("switch_kind") or "")))
    configured_kinds.sort()
    engaged_kinds.sort()
    family_ids.sort()
    return {
        "switch_count": len(normalized_rows),
        "configured_switch_count": len(configured_kinds),
        "configured_switch_kinds": configured_kinds,
        "engaged_switch_count": len(engaged_kinds),
        "engaged_switch_kinds": engaged_kinds,
        "family_ids": family_ids,
        "pause_free_only": all(not bool(row.get("pause_required")) for row in normalized_rows),
        "switches": normalized_rows,
    }


def build_guarded_candidate_review_row(
    family_id: str,
    *,
    candidate_state: str = "documentation_only",
    comparison_counts: Optional[Dict[str, Any]] = None,
    artifact_bundle_ref: str = "",
) -> Dict[str, Any]:
    metadata = get_guarded_family_candidate_metadata(str(family_id))
    if not metadata:
        raise KeyError(f"unsupported guarded family candidate: {family_id}")

    allowed_states = metadata.get("allowed_review_states") or list(_SUPPORTED_GUARDED_CANDIDATE_STATES)
    normalized_state = str(candidate_state).strip().lower()
    if normalized_state not in allowed_states:
        normalized_state = str(metadata.get("default_candidate_state") or "documentation_only")

    normalized_counts = {
        "considered": 0,
        "matching": 0,
        "not_matching": 0,
        "not_queried": 0,
    }
    if isinstance(comparison_counts, dict):
        for key in list(normalized_counts):
            try:
                normalized_counts[key] = int(comparison_counts.get(key, 0) or 0)
            except Exception:
                normalized_counts[key] = 0

    return {
        "family_id": str(metadata.get("family_id") or family_id),
        "report_role": "guarded_candidate_review",
        "guard_path": "repo_eval",
        "guard_case": "simultaneous_context_match_non_authority_guard",
        "candidate_state": normalized_state,
        "authoritative": False,
        "current_serving": False,
        "top_tier_authority": False,
        "activation_dependency": False,
        "first_rehearsal_state": str(metadata.get("first_rehearsal_state") or "shadow"),
        "later_dormant_state": str(metadata.get("later_dormant_state") or "standby"),
        "comparison_counts": normalized_counts,
        "artifact_bundle_ref": str(artifact_bundle_ref or ""),
        "non_authority_reason_summary": str(metadata.get("non_authority_reason_summary") or ""),
        "disallowed_promotions": list(metadata.get("disallowed_promotions") or []),
        "rollback_mode": str(metadata.get("rollback_mode") or "documentation_only_remove_or_ignore"),
        "determinism_expectations": list(metadata.get("determinism_expectations") or []),
        "invariance_expectations": list(metadata.get("invariance_expectations") or []),
    }


def build_guarded_shadow_descriptor_hook(
    cfg: Dict[str, Any],
    family_id: str = "simultaneous_context_match",
) -> Dict[str, Any]:
    metadata = get_guarded_family_candidate_metadata(str(family_id))
    if not metadata:
        raise KeyError(f"unsupported guarded family candidate: {family_id}")

    tier_family_cfg: Dict[str, Any] = {}
    if isinstance(cfg, dict):
        tier_families_cfg = cfg.get("tier_families", {})
        if isinstance(tier_families_cfg, dict):
            raw_candidate_cfg = tier_families_cfg.get(str(family_id), {})
            if isinstance(raw_candidate_cfg, dict):
                tier_family_cfg = raw_candidate_cfg

    raw_hook = tier_family_cfg.get("guarded_shadow_hook", {})
    if not isinstance(raw_hook, dict):
        raw_hook = {}

    hook_enabled = bool(raw_hook.get("enabled"))
    candidate_state = raw_hook.get("candidate_state")
    if not isinstance(candidate_state, str) or not candidate_state.strip():
        candidate_state = "shadow_review" if hook_enabled else str(
            metadata.get("default_candidate_state") or "documentation_only"
        )

    review_row = build_guarded_candidate_review_row(
        str(family_id),
        candidate_state=str(candidate_state),
        comparison_counts=raw_hook.get("comparison_counts"),
        artifact_bundle_ref=str(raw_hook.get("artifact_bundle_ref") or ""),
    )

    return {
        "family_id": str(metadata.get("family_id") or family_id),
        "hook_kind": "guarded_shadow_descriptor",
        "config_root": str(metadata.get("config_root") or f"tier_families.{family_id}"),
        "hook_config_root": str(
            metadata.get("guarded_hook_root") or f"tier_families.{family_id}.guarded_shadow_hook"
        ),
        "hook_enabled": hook_enabled,
        "hook_posture": str(metadata.get("first_rehearsal_state") or "shadow"),
        "review_only": True,
        "authoritative": False,
        "current_serving": False,
        "scheduler_authority_path": False,
        "activation_dependency": False,
        "family_activation_excluded": True,
        "rollback_mode": str(metadata.get("rollback_mode") or "documentation_only_remove_or_ignore"),
        "review_row": review_row,
    }


def build_guarded_candidate_invariance_guard(
    family_id: str,
    *,
    tier1_snapshot_present: Optional[Dict[str, Any]] = None,
    tier1_snapshot_absent: Optional[Dict[str, Any]] = None,
    scheduler_authority_present: Optional[Dict[str, Any]] = None,
    scheduler_authority_absent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = get_guarded_family_candidate_metadata(str(family_id))
    if not metadata:
        raise KeyError(f"unsupported guarded family candidate: {family_id}")

    tier1_present = dict(tier1_snapshot_present or {})
    tier1_absent = dict(tier1_snapshot_absent or {})
    scheduler_present = dict(scheduler_authority_present or {})
    scheduler_absent = dict(scheduler_authority_absent or {})
    rollback_mode = str(metadata.get("rollback_mode") or "documentation_only_remove_or_ignore")

    return {
        "family_id": str(metadata.get("family_id") or family_id),
        "guard_path": "repo_eval",
        "guard_case": "simultaneous_context_match_tier1_invariance_guard",
        "descriptor_states_compared": ["present", "absent"],
        "tier1_snapshot_present_hash": _stable_review_hash(tier1_present),
        "tier1_snapshot_absent_hash": _stable_review_hash(tier1_absent),
        "tier1_decisions_identical": tier1_present == tier1_absent,
        "scheduler_authority_present_hash": _stable_review_hash(scheduler_present),
        "scheduler_authority_absent_hash": _stable_review_hash(scheduler_absent),
        "scheduler_authority_identical": scheduler_present == scheduler_absent,
        "clean_rollback": rollback_mode == "documentation_only_remove_or_ignore",
        "rollback_mode": rollback_mode,
        "invariance_expectations": list(metadata.get("invariance_expectations") or []),
    }


def _default_level_specs(family_cfg: Dict[str, Any]) -> List[Tuple[int, str]]:
    level_specs: List[Tuple[int, str]] = [(1, "enabled")]
    discovered = []
    for key in family_cfg:
        match = _TIER_FLAG_RE.match(str(key))
        if match:
            discovered.append((int(match.group(1)), str(key)))
    for level, flag_name in sorted(discovered):
        if (level, flag_name) not in level_specs:
            level_specs.append((level, flag_name))
    return level_specs


def _normalize_level_specs(
    family_cfg: Dict[str, Any],
    level_specs: Optional[Iterable[Tuple[int, str]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Tuple[int, str]]:
    if level_specs:
        return [(int(level), str(flag_name)) for level, flag_name in level_specs]
    if isinstance(metadata, dict):
        metadata_specs = metadata.get("level_specs")
        if isinstance(metadata_specs, list) and metadata_specs:
            normalized: List[Tuple[int, str]] = []
            for item in metadata_specs:
                if not isinstance(item, dict):
                    continue
                try:
                    normalized.append((int(item.get("level")), str(item.get("flag"))))
                except Exception:
                    continue
            if normalized:
                return normalized
    return _default_level_specs(family_cfg)


def _format_enabled_levels(levels: List[int]) -> str:
    if not levels:
        return "disabled"
    if levels == list(range(1, len(levels) + 1)):
        if len(levels) == 1:
            return "tier 1"
        return f"tier 1 thru tier {levels[-1]}"
    return ", ".join(f"tier {level}" for level in levels)


def _normalize_routing_state(value: Any, *, default: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _SUPPORTED_ROUTING_STATES:
            return normalized
    return default


def _normalize_instance_source(value: Any, *, default: str) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return str(default)


def _family_has_declared_runtime_shape(
    family_cfg: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    if not isinstance(family_cfg, dict) or not family_cfg:
        return False

    level_specs = _normalize_level_specs(family_cfg, metadata=metadata)
    if any(str(flag_name) in family_cfg for _, flag_name in level_specs):
        return True

    raw_instances = family_cfg.get("instances")
    if isinstance(raw_instances, list) and any(isinstance(item, dict) for item in raw_instances):
        return True

    active_instance_id = family_cfg.get("active_instance_id") or family_cfg.get("instance_id")
    if isinstance(active_instance_id, str) and active_instance_id.strip():
        return True

    routing_state = family_cfg.get("routing_state")
    return isinstance(routing_state, str) and bool(routing_state.strip())


def is_real_tier_family_configured(cfg: Dict[str, Any], family_id: str) -> bool:
    normalized_family_id = str(family_id)

    mirror_cfg = cfg.get("mirror_tiers", {}) if isinstance(cfg, dict) else {}
    if isinstance(mirror_cfg, dict):
        raw_family_cfg = mirror_cfg.get(normalized_family_id)
        if isinstance(raw_family_cfg, dict):
            return True

    metadata = get_tier_family_metadata(normalized_family_id)
    if not metadata:
        return False

    tier_families_cfg = cfg.get("tier_families", {}) if isinstance(cfg, dict) else {}
    if not isinstance(tier_families_cfg, dict):
        return False

    raw_family_cfg = tier_families_cfg.get(normalized_family_id)
    return _family_has_declared_runtime_shape(raw_family_cfg, metadata) if isinstance(raw_family_cfg, dict) else False


def _build_instance_descriptor(
    family_id: str,
    family_cfg: Dict[str, Any],
    instance_cfg: Dict[str, Any],
    *,
    index: int,
    level_specs: List[Tuple[int, str]],
    passthrough_flags: Iterable[str],
    default_routing_state: str,
    source: str,
) -> Dict[str, Any]:
    tiers: Dict[str, bool] = {}
    enabled_levels: List[int] = []
    flags: Dict[str, Any] = {}
    config_snapshot: Dict[str, Any] = {}

    for level, flag_name in level_specs:
        tier_key = f"tier{int(level)}_enabled"
        value = instance_cfg.get(flag_name, family_cfg.get(flag_name))
        enabled = bool(value)
        tiers[tier_key] = enabled
        config_snapshot[str(flag_name)] = enabled
        if enabled:
            enabled_levels.append(int(level))

    for flag_name in passthrough_flags:
        value = instance_cfg.get(flag_name, family_cfg.get(flag_name))
        flags[str(flag_name)] = value
        config_snapshot[str(flag_name)] = value

    instance_id = instance_cfg.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        instance_id = f"{family_id}_instance_{index}"
    instance_id = instance_id.strip()

    routing_state = _normalize_routing_state(
        instance_cfg.get("routing_state"),
        default=default_routing_state,
    )
    instance_source = _normalize_instance_source(instance_cfg.get("source"), default=source)

    return {
        "instance_id": instance_id,
        "family_id": family_id,
        "routing_state": routing_state,
        "source": instance_source,
        "enabled_levels": enabled_levels,
        "highest_enabled_level": int(enabled_levels[-1]) if enabled_levels else 0,
        "label": _format_enabled_levels(enabled_levels),
        "serving": bool(enabled_levels) and routing_state in ("active", "draining"),
        "tiers": tiers,
        "flags": flags,
        "config_snapshot": config_snapshot,
    }


def _build_family_instances(
    family_id: str,
    family_cfg: Dict[str, Any],
    *,
    level_specs: List[Tuple[int, str]],
    passthrough_flags: Iterable[str],
) -> List[Dict[str, Any]]:
    raw_instances = family_cfg.get("instances")
    instances: List[Dict[str, Any]] = []

    if isinstance(raw_instances, list):
        for index, raw_instance in enumerate(raw_instances, start=1):
            if not isinstance(raw_instance, dict):
                continue
            instances.append(
                _build_instance_descriptor(
                    family_id,
                    family_cfg,
                    raw_instance,
                    index=index,
                    level_specs=level_specs,
                    passthrough_flags=passthrough_flags,
                    default_routing_state="standby",
                    source="configured_instance",
                )
            )

    if instances:
        return instances

    legacy_instance_cfg: Dict[str, Any] = {}
    legacy_instance_id = family_cfg.get("active_instance_id") or family_cfg.get("instance_id")
    if isinstance(legacy_instance_id, str) and legacy_instance_id.strip():
        legacy_instance_cfg["instance_id"] = legacy_instance_id.strip()
    legacy_instance_cfg["routing_state"] = family_cfg.get("routing_state")

    return [
        _build_instance_descriptor(
            family_id,
            family_cfg,
            legacy_instance_cfg,
            index=1,
            level_specs=level_specs,
            passthrough_flags=passthrough_flags,
            default_routing_state="active",
            source="legacy_family_defaults",
        )
    ]


def _build_factory_descriptor(factory_id: str, factory_cfg: Dict[str, Any]) -> Dict[str, Any]:
    descriptor = build_create_tier_family_factory_descriptor(
        str(factory_id),
        family_template_id=str(factory_cfg.get("family_template_id") or ""),
        purpose=str(factory_cfg.get("purpose") or ""),
        supported_pressure_types=factory_cfg.get("supported_pressure_types"),
        creation_limits=factory_cfg.get("creation_limits"),
        resource_profile=factory_cfg.get("resource_profile"),
        default_state=str(factory_cfg.get("default_state") or "shadow"),
        promotion_rules=factory_cfg.get("promotion_rules"),
        retirement_rules=factory_cfg.get("retirement_rules"),
        gc_rules=factory_cfg.get("gc_rules"),
        observability_requirements=factory_cfg.get("observability_requirements"),
        rollback_requirements=factory_cfg.get("rollback_requirements"),
    )
    descriptor["configured"] = True
    descriptor["serving_capable_by_default"] = False
    return descriptor


def list_tier_family_factories(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_factories = cfg.get("tier_family_factories", {}) if isinstance(cfg, dict) else {}
    if not isinstance(raw_factories, dict):
        return []

    factories: List[Dict[str, Any]] = []
    for factory_id in sorted(raw_factories):
        factory_cfg = raw_factories.get(factory_id)
        if not isinstance(factory_cfg, dict):
            continue
        factories.append(_build_factory_descriptor(str(factory_id), factory_cfg))
    return factories


def _factory_descriptors_for_family(
    family_id: str,
    factory_descriptors: Optional[Iterable[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    matched: List[Dict[str, Any]] = []
    normalized_family_id = str(family_id)
    for descriptor in factory_descriptors or []:
        if not isinstance(descriptor, dict):
            continue
        if str(descriptor.get("family_template_id") or "") != normalized_family_id:
            continue
        matched.append(dict(descriptor))
    return matched


def build_tier_family_descriptor(
    family_id: str,
    family_cfg: Any,
    *,
    level_flags: Optional[Iterable[Tuple[int, str]]] = None,
    passthrough_flags: Optional[Iterable[str]] = None,
    factory_descriptors: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized_cfg = family_cfg if isinstance(family_cfg, dict) else {}
    metadata = get_tier_family_metadata(str(family_id))
    level_specs = _normalize_level_specs(normalized_cfg, level_flags, metadata)

    configured_passthrough_flags = passthrough_flags
    if configured_passthrough_flags is None:
        configured_passthrough_flags = metadata.get("passthrough_flags") or []
    configured_passthrough_flags = [str(flag_name) for flag_name in configured_passthrough_flags]

    tiers: Dict[str, bool] = {}
    level_flag_values: Dict[str, bool] = {}
    enabled_levels: List[int] = []
    config_snapshot: Dict[str, Any] = {}
    flags: Dict[str, Any] = {}

    for level, flag_name in level_specs:
        tier_key = f"tier{int(level)}_enabled"
        enabled = bool(normalized_cfg.get(flag_name))
        tiers[tier_key] = enabled
        level_flag_values[str(flag_name)] = enabled
        config_snapshot[str(flag_name)] = enabled
        if enabled:
            enabled_levels.append(int(level))

    for flag_name in configured_passthrough_flags:
        value = normalized_cfg.get(flag_name)
        flags[str(flag_name)] = value
        config_snapshot[str(flag_name)] = value

    family_instances = _build_family_instances(
        str(family_id),
        normalized_cfg,
        level_specs=level_specs,
        passthrough_flags=configured_passthrough_flags,
    )
    authoritative_serving_allowed = "non_authoritative" not in (metadata.get("invariants") or [])
    authority_mode = "authoritative" if authoritative_serving_allowed else "non_authoritative"
    for instance in family_instances:
        if not isinstance(instance, dict):
            continue
        instance["authority_mode"] = authority_mode
        if not authoritative_serving_allowed:
            instance["serving"] = False
    matched_factory_descriptors = _factory_descriptors_for_family(str(family_id), factory_descriptors)
    instance_source_counts: Dict[str, int] = {}
    for instance in family_instances:
        source_name = str(instance.get("source") or "unknown")
        instance_source_counts[source_name] = instance_source_counts.get(source_name, 0) + 1
    serving_instance_count = sum(1 for instance in family_instances if instance.get("serving"))
    non_serving_instance_count = sum(1 for instance in family_instances if not instance.get("serving"))
    active_instance_count = sum(1 for instance in family_instances if instance.get("routing_state") == "active")
    routing_state_counts = {
        state: sum(1 for instance in family_instances if instance.get("routing_state") == state)
        for state in _SUPPORTED_ROUTING_STATES
    }
    unknown_state_count = sum(
        1 for instance in family_instances if instance.get("routing_state") not in _SUPPORTED_ROUTING_STATES
    )
    if unknown_state_count:
        routing_state_counts["unknown"] = unknown_state_count

    factory_default_state_counts: Dict[str, int] = {}
    for descriptor in matched_factory_descriptors:
        state_name = str(descriptor.get("default_state") or "shadow")
        factory_default_state_counts[state_name] = factory_default_state_counts.get(state_name, 0) + 1

    return {
        "family": str(family_id),
        "family_id": str(family_id),
        "config_root": str(metadata.get("config_root") or f"mirror_tiers.{family_id}"),
        "purpose": str(metadata.get("purpose") or ""),
        "configured": bool(enabled_levels),
        "active": bool(enabled_levels) and bool(active_instance_count),
        "authority_mode": authority_mode,
        "enabled_levels": enabled_levels,
        "highest_enabled_level": int(enabled_levels[-1]) if enabled_levels else 0,
        "label": _format_enabled_levels(enabled_levels),
        "tiers": tiers,
        "level_flags": level_flag_values,
        "flags": flags,
        "config_snapshot": config_snapshot,
        "instance_contract": {
            "version": int(normalized_cfg.get("instance_contract_version") or 1),
            "supported_states": list(metadata.get("supported_routing_states") or list(_SUPPORTED_ROUTING_STATES)),
        },
        "instance_source_counts": dict(sorted(instance_source_counts.items())),
        "instance_count": len(family_instances),
        "serving_instance_count": serving_instance_count,
        "serving_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("serving")
        ],
        "non_serving_instance_count": non_serving_instance_count,
        "non_serving_instance_ids": [
            instance.get("instance_id") for instance in family_instances if not instance.get("serving")
        ],
        "active_instance_count": active_instance_count,
        "active_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("routing_state") == "active"
        ],
        "created_instance_count": sum(1 for instance in family_instances if instance.get("source") == "created_instance"),
        "created_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("source") == "created_instance"
        ],
        "configured_instance_count": sum(
            1 for instance in family_instances if instance.get("source") == "configured_instance"
        ),
        "configured_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("source") == "configured_instance"
        ],
        "shadow_instance_count": sum(1 for instance in family_instances if instance.get("routing_state") == "shadow"),
        "shadow_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("routing_state") == "shadow"
        ],
        "standby_instance_count": sum(1 for instance in family_instances if instance.get("routing_state") == "standby"),
        "standby_instance_ids": [
            instance.get("instance_id") for instance in family_instances if instance.get("routing_state") == "standby"
        ],
        "factory_descriptor_count": len(matched_factory_descriptors),
        "factory_descriptor_ids": [
            descriptor.get("factory_id") for descriptor in matched_factory_descriptors if descriptor.get("factory_id")
        ],
        "factory_default_state_counts": dict(sorted(factory_default_state_counts.items())),
        "future_created_instance_source": bool(matched_factory_descriptors),
        "routing_state_counts": routing_state_counts,
        "supported_switch_kinds": list(metadata.get("supported_switch_kinds") or []),
        "instances": family_instances,
        "invariants": list(metadata.get("invariants") or []),
        "outputs": list(metadata.get("level_specs") or []),
        "verification": list(metadata.get("verification") or []),
    }


def list_configured_tier_families(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    mirror_cfg = cfg.get("mirror_tiers", {}) if isinstance(cfg, dict) else {}
    factories = list_tier_family_factories(cfg)
    families: List[Dict[str, Any]] = []
    seen: set[str] = set()

    if isinstance(mirror_cfg, dict):
        for family_name in sorted(mirror_cfg):
            family_cfg = mirror_cfg.get(family_name)
            if not isinstance(family_cfg, dict):
                continue
            families.append(build_tier_family_descriptor(str(family_name), family_cfg, factory_descriptors=factories))
            seen.add(str(family_name))

    tier_families_cfg = cfg.get("tier_families", {}) if isinstance(cfg, dict) else {}
    if not isinstance(tier_families_cfg, dict):
        return families

    for family_name in sorted(tier_families_cfg):
        normalized_family_name = str(family_name)
        if normalized_family_name in seen:
            continue
        metadata = get_tier_family_metadata(normalized_family_name)
        family_cfg = tier_families_cfg.get(family_name)
        if not metadata or not isinstance(family_cfg, dict):
            continue
        if not _family_has_declared_runtime_shape(family_cfg, metadata):
            continue
        families.append(
            build_tier_family_descriptor(
                normalized_family_name,
                family_cfg,
                factory_descriptors=factories,
            )
        )
    return families


def tier_summary_label_from_families(families: List[Dict[str, Any]]) -> str:
    active_families = [family for family in families if family.get("active")]
    if not active_families:
        return "none"
    if len(active_families) == 1 and active_families[0].get("family") == "schedule_mirror":
        return str(active_families[0].get("label") or "tier 1")
    return "; ".join(
        f"{family.get('family')}: {family.get('label')}" for family in active_families
    )


def build_tier_activation_summary(cfg: Dict[str, Any]) -> Dict[str, Any]:
    families = list_configured_tier_families(cfg)
    factories = list_tier_family_factories(cfg)
    schedule_family = next(
        (family for family in families if family.get("family") == "schedule_mirror"),
        None,
    )
    schedule_flags = schedule_family.get("level_flags") if isinstance(schedule_family, dict) else {}
    schedule_descriptor = schedule_family if isinstance(schedule_family, dict) else {}
    instance_state_counts = {
        state: sum(
            int((family.get("routing_state_counts") or {}).get(state, 0) or 0)
            for family in families
        )
        for state in _SUPPORTED_ROUTING_STATES
    }
    unknown_instance_states = sum(
        int((family.get("routing_state_counts") or {}).get("unknown", 0) or 0)
        for family in families
    )
    if unknown_instance_states:
        instance_state_counts["unknown"] = unknown_instance_states

    instance_source_counts: Dict[str, int] = {}
    for family in families:
        for source_name, count in (family.get("instance_source_counts") or {}).items():
            normalized_source = str(source_name)
            instance_source_counts[normalized_source] = instance_source_counts.get(normalized_source, 0) + int(count or 0)

    factory_default_state_counts: Dict[str, int] = {}
    for factory in factories:
        state_name = str(factory.get("default_state") or "shadow")
        factory_default_state_counts[state_name] = factory_default_state_counts.get(state_name, 0) + 1

    configured_family_template_ids = [str(family.get("family_id") or family.get("family")) for family in families if family.get("family_id") or family.get("family")]
    factory_backed_family_template_ids = sorted(
        {
            str(factory.get("family_template_id"))
            for factory in factories
            if factory.get("family_template_id")
        }
    )
    serving_family_ids = [
        str(family.get("family_id") or family.get("family"))
        for family in families
        if int(family.get("serving_instance_count") or 0) > 0
    ]
    serving_instance_ids = [
        instance.get("instance_id")
        for family in families
        for instance in (family.get("instances") or [])
        if isinstance(instance, dict) and instance.get("serving") and instance.get("instance_id")
    ]
    non_serving_family_ids = [
        str(family.get("family_id") or family.get("family"))
        for family in families
        if int(family.get("non_serving_instance_count") or 0) > 0
    ]
    non_serving_instance_ids = [
        instance.get("instance_id")
        for family in families
        for instance in (family.get("instances") or [])
        if isinstance(instance, dict) and not instance.get("serving") and instance.get("instance_id")
    ]
    create_tier_visibility = {
        "configured_family_template_count": len(configured_family_template_ids),
        "configured_family_template_ids": configured_family_template_ids,
        "factory_descriptor_count": len(factories),
        "factory_descriptor_ids": [factory.get("factory_id") for factory in factories if factory.get("factory_id")],
        "factory_backed_family_template_count": len(factory_backed_family_template_ids),
        "factory_backed_family_template_ids": factory_backed_family_template_ids,
        "created_instance_family_count": sum(1 for family in families if int(family.get("created_instance_count") or 0) > 0),
        "created_instance_family_ids": [
            str(family.get("family_id") or family.get("family"))
            for family in families
            if int(family.get("created_instance_count") or 0) > 0
        ],
        "created_instance_count": sum(int(family.get("created_instance_count") or 0) for family in families),
        "created_instance_ids": [
            instance_id
            for family in families
            for instance_id in (family.get("created_instance_ids") or [])
            if instance_id
        ],
        "serving_family_count": len(serving_family_ids),
        "serving_family_ids": serving_family_ids,
        "serving_instance_count": len(serving_instance_ids),
        "serving_instance_ids": serving_instance_ids,
        "non_serving_family_count": len(non_serving_family_ids),
        "non_serving_family_ids": non_serving_family_ids,
        "non_serving_instance_count": len(non_serving_instance_ids),
        "non_serving_instance_ids": non_serving_instance_ids,
        "factory_default_state_counts": dict(sorted(factory_default_state_counts.items())),
        "template_source_separation_ok": not any(
            instance_id in set(serving_instance_ids)
            for instance_id in [
                instance_id
                for family in families
                for instance_id in (family.get("created_instance_ids") or [])
                if instance_id
            ]
        ),
        "family_reviews": [
            {
                "family_id": str(family.get("family_id") or family.get("family") or ""),
                "configured_template": True,
                "future_created_instance_source": bool(family.get("future_created_instance_source")),
                "factory_descriptor_count": int(family.get("factory_descriptor_count") or 0),
                "factory_descriptor_ids": list(family.get("factory_descriptor_ids") or []),
                "created_instance_count": int(family.get("created_instance_count") or 0),
                "created_instance_ids": list(family.get("created_instance_ids") or []),
                "serving_instance_count": int(family.get("serving_instance_count") or 0),
                "serving_instance_ids": list(family.get("serving_instance_ids") or []),
                "non_serving_instance_count": int(family.get("non_serving_instance_count") or 0),
                "non_serving_instance_ids": list(family.get("non_serving_instance_ids") or []),
            }
            for family in families
        ],
    }
    bounded_switch_reviews = summarize_bounded_runtime_switches(
        [
            build_bounded_runtime_switch(
                switch_kind,
                family_id=str(family.get("family_id") or family.get("family") or ""),
                configured=True,
                engaged=bool(family.get("active")) and switch_kind == "mirror",
                state=(
                    "active"
                    if bool(family.get("active")) and switch_kind == "mirror"
                    else "available"
                ),
                reason_summary=(
                    "configured family can continue work through a bounded switch"
                ),
            )
            for family in families
            for switch_kind in (family.get("supported_switch_kinds") or [])
            if isinstance(switch_kind, str) and switch_kind in _SUPPORTED_BOUNDED_SWITCH_KINDS
        ]
    )

    return {
        "tier1_enabled": bool(isinstance(schedule_flags, dict) and schedule_flags.get("enabled")),
        "tier2_enabled": bool(isinstance(schedule_flags, dict) and schedule_flags.get("tier2_enabled")),
        "tier3_enabled": bool(isinstance(schedule_flags, dict) and schedule_flags.get("tier3_enabled")),
        "allow_advisory": schedule_descriptor.get("flags", {}).get("allow_advisory") if isinstance(schedule_descriptor.get("flags"), dict) else None,
        "summary_label": tier_summary_label_from_families(families),
        "family_count": len(families),
        "active_family_count": sum(1 for family in families if family.get("active")),
        "active_families": [family.get("family") for family in families if family.get("active")],
        "serving_family_count": len(serving_family_ids),
        "serving_families": serving_family_ids,
        "instance_count": sum(int(family.get("instance_count") or 0) for family in families),
        "created_instance_count": sum(int(family.get("created_instance_count") or 0) for family in families),
        "created_instance_ids": [
            instance_id
            for family in families
            for instance_id in (family.get("created_instance_ids") or [])
            if instance_id
        ],
        "active_instance_count": sum(int(family.get("active_instance_count") or 0) for family in families),
        "active_instance_ids": [
            instance.get("instance_id")
            for family in families
            for instance in (family.get("instances") or [])
            if isinstance(instance, dict) and instance.get("routing_state") == "active"
        ],
        "serving_instance_count": len(serving_instance_ids),
        "serving_instance_ids": serving_instance_ids,
        "standby_instance_count": sum(int(family.get("standby_instance_count") or 0) for family in families),
        "standby_instance_ids": [
            instance.get("instance_id")
            for family in families
            for instance in (family.get("instances") or [])
            if isinstance(instance, dict) and instance.get("routing_state") == "standby"
        ],
        "supported_instance_states": list(_SUPPORTED_ROUTING_STATES),
        "instance_state_counts": instance_state_counts,
        "instance_source_counts": dict(sorted(instance_source_counts.items())),
        "family_factory_count": len(factories),
        "family_factory_ids": [factory.get("factory_id") for factory in factories if factory.get("factory_id")],
        "family_template_ids": sorted(
            {
                str(factory.get("family_template_id"))
                for factory in factories
                if factory.get("family_template_id")
            }
        ),
        "factory_default_state_counts": dict(sorted(factory_default_state_counts.items())),
        "bounded_switch_inventory": bounded_switch_reviews,
        "create_tier_visibility": create_tier_visibility,
        "family_factories": factories,
        "families": families,
    }
