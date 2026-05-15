#+#+#+#+ module_integration.py
import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict
from module_toggle import move
from module_awareness import trigger_information_seeking_if, trigger_information_seeking, validate_response, awareness_plan
from module_scheduler import flag_record
from module_current_activity import set_activity, persist_activity
from module_objectives import get_objectives_by_label
from module_storage import _atomic_write_json, store_information, resolve_path, store_and_get_path
from module_measure import measure_information
from module_scheduler import flag_record, schedule_synthesis
from datetime import datetime
from module_collector import collect_results
from module_tools import (
    similarity, familiarity, usefulness, synthesis_potential,
    compare_against_objectives, search_related, procedural_match,
    search_internet, query_llm, _load_config, describe, sanitize_id, safe_join,
    canonical_json_bytes,
)
from module_select import rank as rank_selection
from module_tier_families import (
    build_bounded_runtime_switch,
    build_guarded_shadow_descriptor_hook,
    build_tier_family_descriptor,
    is_real_tier_family_configured,
    summarize_bounded_runtime_switches,
)
from module_retrieval import summarize_categorized_context_join_quality, summarize_reference_use
import uuid

def _now_ts(deterministic_mode: bool, fixed_ts: Optional[str]) -> str:
    """Return deterministic timestamp when enabled; otherwise current time."""
    if deterministic_mode and fixed_ts:
        return str(fixed_ts)
    return datetime.fromtimestamp(time.time()).isoformat()


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reference_profile_from_record_or_derived(
    record: Dict[str, Any],
    derived: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    explicit = record.get("reference_label_profile") if isinstance(record.get("reference_label_profile"), dict) else {}
    if explicit:
        return explicit
    if isinstance(derived, dict):
        derived_block = derived
    else:
        relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
        derived_block = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    sidecar_profile = (
        derived_block.get("sidecar_reference_label_profile")
        if isinstance(derived_block.get("sidecar_reference_label_profile"), dict)
        else {}
    )
    if sidecar_profile:
        return sidecar_profile
    categorized = (
        derived_block.get("categorized_context_summary")
        if isinstance(derived_block.get("categorized_context_summary"), dict)
        else {}
    )
    if categorized:
        labels = categorized.get("reference_labels") if isinstance(categorized.get("reference_labels"), list) else []
        aliases = categorized.get("reference_aliases") if isinstance(categorized.get("reference_aliases"), list) else []
        axes = (
            categorized.get("reference_comparison_axes")
            if isinstance(categorized.get("reference_comparison_axes"), list)
            else []
        )
        if labels or aliases or axes:
            return {
                "labels": list(labels),
                "aliases": list(aliases),
                "comparison_axes": list(axes),
            }
    return {}


def _build_categorized_context_join_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from module_relational_adapter import summarize_record_categorized_context
    except Exception:
        summarize_record_categorized_context = None

    record_value = row.get("value") if isinstance(row.get("value"), dict) else {}
    if summarize_record_categorized_context is not None:
        semantic_summary = summarize_record_categorized_context(record_value)
    else:
        semantic_summary = {
            "labels": [],
            "aliases": [],
            "comparison_axes": [],
            "relation_families": [],
            "bridge_sources": [],
            "scene_summary_present": False,
            "support_level": "missing",
        }

    reference_profile = row.get("reference_label_profile") if isinstance(row.get("reference_label_profile"), dict) else {}
    if not reference_profile:
        reference_profile = (
            semantic_summary.get("sidecar_reference_label_profile")
            if isinstance(semantic_summary.get("sidecar_reference_label_profile"), dict)
            else {}
        )
    reference_labels = [str(item) for item in reference_profile.get("labels", []) if isinstance(item, str)]
    reference_aliases = [str(item) for item in reference_profile.get("aliases", []) if isinstance(item, str)]
    reference_axes = [str(item) for item in reference_profile.get("comparison_axes", []) if isinstance(item, str)]
    join_quality = summarize_categorized_context_join_quality(semantic_summary, reference_profile)

    out = {
        "labels": list(semantic_summary.get("labels") or []),
        "aliases": list(semantic_summary.get("aliases") or []),
        "comparison_axes": list(semantic_summary.get("comparison_axes") or []),
        "relation_families": list(semantic_summary.get("relation_families") or []),
        "bridge_sources": list(semantic_summary.get("bridge_sources") or []),
        "scene_summary_present": bool(semantic_summary.get("scene_summary_present")),
        "support_level": str(semantic_summary.get("support_level") or "missing"),
        "reference_profile_present": bool(join_quality.get("reference_profile_present")),
        "reference_labels": reference_labels,
        "reference_aliases": reference_aliases,
        "reference_comparison_axes": reference_axes,
        "join_status": str(join_quality.get("join_status") or "missing"),
        "join_quality": str(join_quality.get("join_quality") or "missing"),
        "persistence_status": str(join_quality.get("persistence_status") or "missing"),
        "follow_through_status": str(join_quality.get("follow_through_status") or "missing"),
        "matched_reference_labels": list(join_quality.get("matched_reference_labels") or []),
        "matched_reference_aliases": list(join_quality.get("matched_reference_aliases") or []),
        "matched_reference_comparison_axes": list(join_quality.get("matched_reference_comparison_axes") or []),
        "matched_reference_category_count": int(join_quality.get("matched_reference_category_count") or 0),
        "matched_reference_term_count": int(join_quality.get("matched_reference_term_count") or 0),
        "gap_reasons": list(join_quality.get("gap_reasons") or []),
    }
    return out


def _annotate_retrieval_rows_with_categorized_context(rows: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []

    annotated: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry = dict(row)
        entry["categorized_context_summary"] = _build_categorized_context_join_summary(entry)
        annotated.append(entry)
    return annotated


def _has_foundational_reference_support(
    *,
    reference_profile: Dict[str, Any],
    categorized_summary: Dict[str, Any],
    comprehension_summary: Dict[str, Any],
    readiness_summary: Dict[str, Any],
    foundational_hook_summary: Dict[str, Any],
) -> bool:
    has_reference_profile = any(
        isinstance(reference_profile.get(key), list) and bool(reference_profile.get(key))
        for key in ("labels", "aliases", "comparison_axes")
    )
    categorized_level = str(categorized_summary.get("support_level") or categorized_summary.get("level") or "missing")
    comprehension_level = str(comprehension_summary.get("level") or "missing")
    readiness_ready = bool(readiness_summary.get("ready"))
    readiness_status = str(readiness_summary.get("status") or "not_ready")
    hook_present = bool(foundational_hook_summary)

    return bool(
        has_reference_profile
        and (
            categorized_level != "missing"
            or comprehension_level != "missing"
            or readiness_ready
            or readiness_status == "ready"
            or hook_present
        )
    )


def _normalize_foundational_rejected_match_reason_items(reasoning: Any) -> List[Dict[str, Any]]:
    if isinstance(reasoning, dict):
        raw_items = reasoning.get("reason_items") if isinstance(reasoning.get("reason_items"), list) else []
    elif isinstance(reasoning, list):
        raw_items = reasoning
    else:
        raw_items = []

    normalized: List[Dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        reason_code = str(item.get("reason_code") or "").strip()
        reason_summary = str(item.get("reason_summary") or "").strip()
        if not reason_code or not reason_summary:
            continue
        evidence_type = str(item.get("evidence_type") or "comparison").strip() or "comparison"
        severity = str(item.get("severity") or "blocking").strip() or "blocking"
        evidence_ref = item.get("evidence_ref")
        if isinstance(evidence_ref, (dict, list)):
            evidence_ref = _canonical_to_obj(evidence_ref)
        elif evidence_ref is None:
            evidence_ref = ""
        else:
            evidence_ref = str(evidence_ref)
        normalized.append(
            {
                "reason_code": reason_code,
                "reason_summary": reason_summary,
                "evidence_type": evidence_type,
                "evidence_ref": evidence_ref,
                "severity": severity,
            }
        )

    normalized.sort(
        key=lambda row: (
            str(row.get("severity") or ""),
            str(row.get("reason_code") or ""),
            str(row.get("evidence_type") or ""),
            canonical_json_bytes(row.get("evidence_ref")).decode("utf-8") if isinstance(row.get("evidence_ref"), (dict, list)) else str(row.get("evidence_ref") or ""),
        )
    )
    return normalized


def _build_foundational_rejected_match_reasoning_inputs(
    foundational_summary: Dict[str, Any],
    *,
    categorized_summary: Dict[str, Any],
    comprehension_summary: Dict[str, Any],
    readiness_summary: Dict[str, Any],
    rejected_match_reasoning: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    explicit_reasoning = dict(rejected_match_reasoning or {})
    explicit_items = _normalize_foundational_rejected_match_reason_items(explicit_reasoning)
    if explicit_items:
        return {
            "result_state": str(explicit_reasoning.get("result_state") or "not_matching"),
            "result_reason_summary": str(
                explicit_reasoning.get("result_reason_summary")
                or "bounded foundational support rejected current relevance"
            ),
            "reason_items": explicit_items,
            "reference_window": explicit_reasoning.get("reference_window"),
            "query_state": str(explicit_reasoning.get("query_state") or "auto_considered"),
            "attention_hint": str(explicit_reasoning.get("attention_hint") or "optional_reference"),
        }

    reason_items: List[Dict[str, Any]] = []
    categorized_level = str(categorized_summary.get("support_level") or categorized_summary.get("level") or "missing")
    if categorized_level in {"missing", "weak"}:
        reason_items.append(
            {
                "reason_code": f"categorized_context_{categorized_level}",
                "reason_summary": f"categorized-context support is {categorized_level} for the current foundational window",
                "evidence_type": "comparison",
                "evidence_ref": foundational_summary.get("support_sources") or [],
                "severity": "blocking",
            }
        )

    comprehension_level = str(comprehension_summary.get("level") or "missing")
    if comprehension_level in {"missing", "weak"}:
        reason_items.append(
            {
                "reason_code": f"comprehension_review_{comprehension_level}",
                "reason_summary": f"comprehension review remains {comprehension_level} for the current foundational window",
                "evidence_type": "comparison",
                "evidence_ref": comprehension_summary.get("unresolved_gaps") or [],
                "severity": "blocking",
            }
        )

    readiness_status = str(readiness_summary.get("status") or "not_ready")
    if not bool(readiness_summary.get("ready")):
        reason_items.append(
            {
                "reason_code": f"learning_readiness_{readiness_status}",
                "reason_summary": str(
                    readiness_summary.get("reason")
                    or f"learning readiness is {readiness_status} for the current foundational window"
                ),
                "evidence_type": "query_gate",
                "evidence_ref": readiness_summary.get("unmet_conditions") or [],
                "severity": "blocking",
            }
        )

    normalized_items = _normalize_foundational_rejected_match_reason_items(reason_items)
    if not normalized_items:
        return {}

    return {
        "result_state": "not_matching",
        "result_reason_summary": "bounded foundational support rejected current relevance",
        "reason_items": normalized_items,
        "reference_window": {
            "labels": list(foundational_summary.get("reference_labels") or []),
            "aliases": list(foundational_summary.get("reference_aliases") or []),
            "comparison_axes": list(foundational_summary.get("reference_comparison_axes") or []),
        },
        "query_state": "auto_considered",
        "attention_hint": "optional_reference",
    }


def build_foundational_active_space_reference_summary(
    record: Dict[str, Any],
    *,
    family_id: str = "simultaneous_context_match",
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    categorized_summary = (
        derived.get("categorized_context_summary")
        if isinstance(derived.get("categorized_context_summary"), dict)
        else _build_categorized_context_join_summary(record)
    )
    comprehension_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else _build_comprehension_review_summary(record)
    )
    readiness_summary = record.get("learning_readiness") if isinstance(record.get("learning_readiness"), dict) else {}
    reference_profile = _reference_profile_from_record_or_derived(record, derived)
    foundational_hook_summary = (
        derived.get("foundational_tier_hook_summary")
        if isinstance(derived.get("foundational_tier_hook_summary"), dict)
        else {}
    )

    if not _has_foundational_reference_support(
        reference_profile=reference_profile,
        categorized_summary=categorized_summary if isinstance(categorized_summary, dict) else {},
        comprehension_summary=comprehension_summary if isinstance(comprehension_summary, dict) else {},
        readiness_summary=readiness_summary if isinstance(readiness_summary, dict) else {},
        foundational_hook_summary=foundational_hook_summary if isinstance(foundational_hook_summary, dict) else {},
    ):
        return {}

    activity_digest = _build_foundational_activity_digest(record)
    trigger_digest = _build_foundational_trigger_digest(record)

    summary = {
        "family_id": str(family_id),
        "integration_role": "foundational_active_space_reference_support",
        "authoritative": False,
        "current_serving": False,
        "consumption_mode": "bounded_reference_support",
        "active_space_entry_points": [
            "module_select.select_information",
            "module_select.rank",
        ],
        "reference_labels": [str(item) for item in reference_profile.get("labels", []) if isinstance(item, str)],
        "reference_aliases": [str(item) for item in reference_profile.get("aliases", []) if isinstance(item, str)],
        "reference_comparison_axes": [
            str(item) for item in reference_profile.get("comparison_axes", []) if isinstance(item, str)
        ],
        "guarded_foundational_hook_present": bool(foundational_hook_summary),
        "guarded_foundational_hook_state": str(foundational_hook_summary.get("candidate_state") or "absent"),
        "categorized_context_support": str(categorized_summary.get("support_level") or "missing"),
        "comprehension_review_level": str(comprehension_summary.get("level") or "missing"),
        "learning_readiness_status": str(readiness_summary.get("status") or "not_ready"),
        "learning_readiness_ready": bool(readiness_summary.get("ready")),
        "evidence_window": "current_active_space",
        "activity_digest": activity_digest,
        "trigger_digest": trigger_digest,
        "support_sources": [
            source
            for source, present in (
                ("guarded_foundational_hook", bool(foundational_hook_summary)),
                ("categorized_context", str(categorized_summary.get("support_level") or "missing") != "missing"),
                ("comprehension_review", str(comprehension_summary.get("level") or "missing") != "missing"),
                (
                    "learning_readiness",
                    bool(readiness_summary.get("ready")) or str(readiness_summary.get("status") or "") == "ready",
                ),
            )
            if present
        ],
        "rollback_mode": "remove_foundational_support_summary_only",
    }
    summary["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in summary.items()
            if key != "summary_hash"
        }
    )
    return summary


def build_foundational_optional_reference_non_match_artifact(
    record: Dict[str, Any],
    *,
    family_id: str = "simultaneous_context_match",
    rejected_match_reasoning: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    foundational_summary = (
        derived.get("foundational_active_space_reference_summary")
        if isinstance(derived.get("foundational_active_space_reference_summary"), dict)
        else build_foundational_active_space_reference_summary(record, family_id=family_id)
    )
    if not isinstance(foundational_summary, dict) or not foundational_summary:
        return {}

    categorized_summary = (
        derived.get("categorized_context_summary")
        if isinstance(derived.get("categorized_context_summary"), dict)
        else _build_categorized_context_join_summary(record)
    )
    comprehension_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else _build_comprehension_review_summary(record)
    )
    readiness_summary = record.get("learning_readiness") if isinstance(record.get("learning_readiness"), dict) else {}

    derived_reasoning = (
        derived.get("simultaneous_context_match_rejected_match_reasoning")
        if isinstance(derived.get("simultaneous_context_match_rejected_match_reasoning"), dict)
        else {}
    )
    reasoning_inputs = _build_foundational_rejected_match_reasoning_inputs(
        foundational_summary,
        categorized_summary=categorized_summary if isinstance(categorized_summary, dict) else {},
        comprehension_summary=comprehension_summary if isinstance(comprehension_summary, dict) else {},
        readiness_summary=readiness_summary if isinstance(readiness_summary, dict) else {},
        rejected_match_reasoning=(
            rejected_match_reasoning
            if isinstance(rejected_match_reasoning, dict)
            else derived_reasoning
        ),
    )
    reason_items = reasoning_inputs.get("reason_items") if isinstance(reasoning_inputs.get("reason_items"), list) else []
    if str(reasoning_inputs.get("result_state") or "") != "not_matching" or not reason_items:
        return {}

    artifact = {
        "family_id": str(family_id),
        "artifact_kind": "foundational_optional_reference_non_match",
        "source_result_state": "not_matching",
        "artifact_role": "optional_reference",
        "authoritative": False,
        "current_serving": False,
        "top_tier_authority": False,
        "dormant_by_default": True,
        "result_reason_summary": str(
            reasoning_inputs.get("result_reason_summary")
            or "bounded foundational support rejected current relevance"
        ),
        "reason_items": reason_items,
        "reason_comparison_summary": (
            f"{len(reason_items)} deterministic rejected-match reason(s) preserved for optional reference"
        ),
        "reference_window": (
            reasoning_inputs.get("reference_window")
            if isinstance(reasoning_inputs.get("reference_window"), dict)
            else {
                "labels": list(foundational_summary.get("reference_labels") or []),
                "aliases": list(foundational_summary.get("reference_aliases") or []),
                "comparison_axes": list(foundational_summary.get("reference_comparison_axes") or []),
            }
        ),
        "activity_digest": dict(foundational_summary.get("activity_digest") or {}),
        "trigger_digest": _build_foundational_trigger_digest(
            record,
            query_state=str(reasoning_inputs.get("query_state") or "auto_considered"),
        ),
        "support_summary_hash": str(foundational_summary.get("summary_hash") or ""),
        "support_sources": list(foundational_summary.get("support_sources") or []),
        "query_state": str(reasoning_inputs.get("query_state") or "auto_considered"),
        "attention_hint": "optional_reference",
        "expiry_rule": "stay_dormant_until_new_bounded_trigger",
        "rollback_mode": "remove_optional_reference_artifact_only",
    }
    artifact["artifact_hash"] = _stable_hash(
        {
            key: value
            for key, value in artifact.items()
            if key != "artifact_hash"
        }
    )
    return artifact


def _unique_non_empty_strings(values: Any) -> List[str]:
    items: List[str] = []
    seen: set[str] = set()
    if not isinstance(values, (list, tuple, set)):
        return items
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def _build_mirrored_parameter_review_surface(
    *,
    surface_id: str,
    family_id: str,
    surface_kind: str,
    configured: bool,
    present: bool,
    derivative_source: str,
    authority_mode: str,
    evidence_refs: Optional[List[str]] = None,
    value_summary: str = "",
    deterministic: bool = True,
    authoritative: bool = False,
    current_serving: bool = False,
) -> Dict[str, Any]:
    refs = _unique_non_empty_strings(evidence_refs or [])
    return {
        "surface_id": str(surface_id),
        "family_id": str(family_id),
        "surface_kind": str(surface_kind),
        "configured": bool(configured),
        "present": bool(present),
        "deterministic": bool(deterministic),
        "derivative_source": str(derivative_source),
        "authority_mode": str(authority_mode),
        "authoritative": bool(authoritative),
        "current_serving": bool(current_serving),
        "derivative_value": bool(present and deterministic),
        "evidence_refs": refs,
        "value_summary": str(value_summary or ""),
    }


def build_mirrored_parameter_review_summary(
    record: Optional[Dict[str, Any]],
    *,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    record = record if isinstance(record, dict) else {}
    cfg = cfg if isinstance(cfg, dict) else {}
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}

    mirror_cfg = _mirror_tier_config(cfg)
    schedule_cfg = mirror_cfg.get("schedule_mirror") if isinstance(mirror_cfg, dict) else {}
    schedule_routing = _tier_family_routing_state(
        family_id="schedule_mirror",
        family_cfg=schedule_cfg,
        passthrough_flags=["allow_advisory"],
    )
    schedule_tiers = schedule_routing.get("tiers") if isinstance(schedule_routing.get("tiers"), dict) else {}
    mirror_summary = derived.get("mirror_schedule_summary") if isinstance(derived.get("mirror_schedule_summary"), dict) else {}
    mirror_delta = derived.get("mirror_schedule_delta") if isinstance(derived.get("mirror_schedule_delta"), dict) else {}
    mirror_tier3 = (
        derived.get("schedule_mirror_tier3")
        if isinstance(derived.get("schedule_mirror_tier3"), dict)
        else (
            derived.get("mirror_schedule_tier3")
            if isinstance(derived.get("mirror_schedule_tier3"), dict)
            else {}
        )
    )

    foundational_hook_summary = (
        derived.get("foundational_tier_hook_summary")
        if isinstance(derived.get("foundational_tier_hook_summary"), dict)
        else _build_foundational_tier_hook_summary(cfg)
    )
    foundational_active_space_summary = (
        derived.get("foundational_active_space_reference_summary")
        if isinstance(derived.get("foundational_active_space_reference_summary"), dict)
        else {}
    )
    foundational_optional_reference_artifact = (
        derived.get("foundational_optional_reference_non_match_artifact")
        if isinstance(derived.get("foundational_optional_reference_non_match_artifact"), dict)
        else {}
    )
    simultaneous_configured = is_real_tier_family_configured(cfg, "simultaneous_context_match") or bool(
        foundational_hook_summary
        or foundational_active_space_summary
        or foundational_optional_reference_artifact
    )

    surface_reviews = [
        _build_mirrored_parameter_review_surface(
            surface_id="schedule_mirror_tier1_summary",
            family_id="schedule_mirror",
            surface_kind="mirror_summary",
            configured=bool(schedule_tiers.get("tier1_enabled")) or bool(mirror_summary),
            present=bool(mirror_summary),
            derivative_source="tier1_primary_selection",
            authority_mode="reporting_only",
            evidence_refs=[str(mirror_summary.get("mirror_schedule_summary_hash") or "")],
            value_summary=(
                f"bounded schedule summary preserved {int(mirror_summary.get('candidate_count') or 0)} candidate action(s)"
                if mirror_summary
                else "bounded schedule summary not recorded for the current review window"
            ),
        ),
        _build_mirrored_parameter_review_surface(
            surface_id="schedule_mirror_tier2_delta",
            family_id="schedule_mirror",
            surface_kind="mirror_delta",
            configured=bool(schedule_tiers.get("tier2_enabled")) or bool(mirror_delta),
            present=bool(mirror_delta),
            derivative_source="schedule_mirror_tier1_summary",
            authority_mode="reporting_only",
            evidence_refs=[str(mirror_delta.get("delta_hash") or "")],
            value_summary=(
                f"deterministic delta preserved {int(mirror_delta.get('change_count') or 0)} change dimension(s)"
                if mirror_delta
                else "bounded schedule delta not recorded for the current review window"
            ),
        ),
        _build_mirrored_parameter_review_surface(
            surface_id="schedule_mirror_tier3_checksum",
            family_id="schedule_mirror",
            surface_kind="mirror_checksum",
            configured=bool(schedule_tiers.get("tier3_enabled")) or bool(mirror_tier3),
            present=bool(mirror_tier3),
            derivative_source="schedule_mirror_tier2_delta",
            authority_mode="reporting_only",
            evidence_refs=[str(mirror_tier3.get("hash_value") or "")],
            value_summary=(
                "tier-3 checksum preserved deterministic derivative continuity"
                if mirror_tier3
                else "tier-3 checksum not recorded for the current review window"
            ),
        ),
        _build_mirrored_parameter_review_surface(
            surface_id="simultaneous_context_match_guarded_hook",
            family_id="simultaneous_context_match",
            surface_kind="guarded_hook",
            configured=bool(simultaneous_configured or foundational_hook_summary),
            present=bool(foundational_hook_summary),
            derivative_source="guarded_shadow_descriptor_hook",
            authority_mode="review_only",
            evidence_refs=[str(foundational_hook_summary.get("artifact_bundle_ref") or "")],
            value_summary=(
                f"guarded hook preserved {int((foundational_hook_summary.get('comparison_counts') or {}).get('considered') or 0)} bounded comparison(s)"
                if foundational_hook_summary
                else "guarded simultaneous-context hook not recorded for the current review window"
            ),
        ),
        _build_mirrored_parameter_review_surface(
            surface_id="simultaneous_context_match_active_space_summary",
            family_id="simultaneous_context_match",
            surface_kind="bounded_support_summary",
            configured=bool(simultaneous_configured or foundational_active_space_summary),
            present=bool(foundational_active_space_summary),
            derivative_source="current_activity_local_reference_window",
            authority_mode="review_only",
            evidence_refs=[str(foundational_active_space_summary.get("summary_hash") or "")],
            value_summary=(
                f"bounded support summary preserved {len(foundational_active_space_summary.get('support_sources') or [])} support source(s)"
                if foundational_active_space_summary
                else "bounded simultaneous-context support summary not recorded for the current review window"
            ),
        ),
        _build_mirrored_parameter_review_surface(
            surface_id="simultaneous_context_match_optional_reference_artifact",
            family_id="simultaneous_context_match",
            surface_kind="optional_reference_artifact",
            configured=bool(simultaneous_configured or foundational_optional_reference_artifact),
            present=bool(foundational_optional_reference_artifact),
            derivative_source="bounded_rejected_match_reasoning",
            authority_mode="review_only",
            evidence_refs=[str(foundational_optional_reference_artifact.get("artifact_hash") or "")],
            value_summary=(
                f"optional-reference artifact preserved {len(foundational_optional_reference_artifact.get('reason_items') or [])} rejected-match reason(s)"
                if foundational_optional_reference_artifact
                else "optional-reference rejected-match artifact not recorded for the current review window"
            ),
        ),
    ]

    review_surface_rows = [row for row in surface_reviews if str(row.get("authority_mode") or "") == "review_only"]
    inventoried_rows = [row for row in surface_reviews if str(row.get("authority_mode") or "") != "review_only"]
    configured_rows = [row for row in review_surface_rows if bool(row.get("configured"))]
    present_rows = [row for row in review_surface_rows if bool(row.get("present"))]
    useful_rows = [row for row in present_rows if bool(row.get("derivative_value"))]
    inventoried_present_rows = [row for row in inventoried_rows if bool(row.get("present"))]
    if useful_rows:
        derivative_value_status = "present"
        derivative_value_summary = (
            f"{len(useful_rows)} review-only mirrored surface(s) preserved derivative evidence without widening authority."
        )
    elif configured_rows:
        derivative_value_status = "configured_only"
        derivative_value_summary = (
            f"{len(configured_rows)} review-only mirrored surface(s) are configured, but no current derivative payload was persisted."
        )
    else:
        derivative_value_status = "absent"
        derivative_value_summary = "No review-only mirrored parameter surfaces were observed for the current bounded review window."

    summary = {
        "review_kind": "mirrored_parameter_review",
        "summary_version": 1,
        "review_family_id": "simultaneous_context_match",
        "visibility_mode": "family_shadow" if simultaneous_configured else "review_only",
        "supported_switch_kinds": ["review_only", "reject", "role_switch"],
        "review_surface_scope": "inventory_current_mirror_style_outputs_without_authority_promotion",
        "primary_authority": "tier1_primary_modules",
        "primary_authority_preserved": all(
            not bool(row.get("authoritative")) and not bool(row.get("current_serving"))
            for row in surface_reviews
        ),
        "derivative_value_status": derivative_value_status,
        "derivative_value_summary": derivative_value_summary,
        "configured_surface_count": len(configured_rows),
        "present_surface_count": len(present_rows),
        "useful_surface_count": len(useful_rows),
        "inventoried_surface_count": len(inventoried_rows),
        "inventoried_present_surface_count": len(inventoried_present_rows),
        "configured_family_ids": _unique_non_empty_strings(
            [str(row.get("family_id") or "") for row in configured_rows]
        ),
        "present_family_ids": _unique_non_empty_strings(
            [str(row.get("family_id") or "") for row in present_rows]
        ),
        "reviewed_surface_ids": [str(row.get("surface_id") or "") for row in surface_reviews],
        "review_surface_ids": [str(row.get("surface_id") or "") for row in review_surface_rows],
        "inventoried_surface_ids": [str(row.get("surface_id") or "") for row in inventoried_rows],
        "surface_reviews": surface_reviews,
        "review_surface_reviews": review_surface_rows,
        "authority_boundary": {
            "mirror_outputs_non_authoritative": True,
            "allocator_authority_unchanged": True,
            "speculative_promotion_allowed": False,
        },
        "guardrails": [
            "mirror outputs remain deterministic derivatives of primary modules",
            "review surfaces remain bounded, non-authoritative, and reversible",
            "no speculative promotion or allocator authority is granted by mirrored review outputs",
        ],
    }
    summary["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in summary.items()
            if key != "summary_hash"
        }
    )
    return summary


def build_multi_location_comprehension_review_summary(
    record: Optional[Dict[str, Any]],
    *,
    cfg: Optional[Dict[str, Any]] = None,
    mirrored_parameter_review_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    record = record if isinstance(record, dict) else {}
    cfg = cfg if isinstance(cfg, dict) else {}
    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    mirrored_review = (
        mirrored_parameter_review_summary
        if isinstance(mirrored_parameter_review_summary, dict)
        else build_mirrored_parameter_review_summary(record, cfg=cfg)
    )
    foundational_active_space_summary = (
        derived.get("foundational_active_space_reference_summary")
        if isinstance(derived.get("foundational_active_space_reference_summary"), dict)
        else {}
    )
    foundational_optional_reference_artifact = (
        derived.get("foundational_optional_reference_non_match_artifact")
        if isinstance(derived.get("foundational_optional_reference_non_match_artifact"), dict)
        else {}
    )
    activity_digest = (
        foundational_active_space_summary.get("activity_digest")
        if isinstance(foundational_active_space_summary.get("activity_digest"), dict)
        else _build_foundational_activity_digest(record)
    )
    trigger_digest = (
        foundational_active_space_summary.get("trigger_digest")
        if isinstance(foundational_active_space_summary.get("trigger_digest"), dict)
        else _build_foundational_trigger_digest(record)
    )
    reference_profile = _reference_profile_from_record_or_derived(record, derived)
    artifact_reference_window = (
        foundational_optional_reference_artifact.get("reference_window")
        if isinstance(foundational_optional_reference_artifact.get("reference_window"), dict)
        else {}
    )
    reference_window = {
        "labels": _unique_non_empty_strings(
            foundational_active_space_summary.get("reference_labels")
            or artifact_reference_window.get("labels")
            or reference_profile.get("labels")
        ),
        "aliases": _unique_non_empty_strings(
            foundational_active_space_summary.get("reference_aliases")
            or artifact_reference_window.get("aliases")
            or reference_profile.get("aliases")
        ),
        "comparison_axes": _unique_non_empty_strings(
            foundational_active_space_summary.get("reference_comparison_axes")
            or artifact_reference_window.get("comparison_axes")
            or reference_profile.get("comparison_axes")
        ),
    }
    support_sources = _unique_non_empty_strings(foundational_active_space_summary.get("support_sources"))
    reason_items = foundational_optional_reference_artifact.get("reason_items")
    reason_item_count = len(reason_items) if isinstance(reason_items, list) else 0
    present_surface_ids = [
        str(row.get("surface_id") or "")
        for row in (mirrored_review.get("review_surface_reviews") or mirrored_review.get("surface_reviews") or [])
        if isinstance(row, dict) and bool(row.get("present"))
    ]

    if support_sources or reason_item_count or bool(present_surface_ids):
        review_status = "reviewable_derivative"
        review_summary = (
            "bounded multi-location comprehension review is available as derivative evidence while primary understanding remains unchanged"
        )
    elif int(mirrored_review.get("configured_surface_count") or 0) > 0:
        review_status = "configured_only"
        review_summary = "multi-location comprehension surfaces are configured, but no current derivative review payload was persisted."
    else:
        review_status = "absent"
        review_summary = "no multi-location comprehension review surfaces were observed for the current bounded review window."

    review_locations = [
        {
            "location_id": "main_context",
            "present": bool(record),
            "role": "primary_locus",
            "derivative_only": False,
        },
        {
            "location_id": "scheduled_memory",
            "present": any(surface_id.startswith("schedule_mirror_") for surface_id in present_surface_ids),
            "role": "primary_locus",
            "derivative_only": False,
        },
        {
            "location_id": "bounded_reference_support",
            "present": bool(foundational_active_space_summary),
            "role": "review_only",
            "derivative_only": True,
        },
        {
            "location_id": "optional_reference_artifact",
            "present": bool(foundational_optional_reference_artifact),
            "role": "review_only",
            "derivative_only": True,
        },
    ]

    summary = {
        "review_kind": "multi_location_comprehension_review",
        "summary_version": 1,
        "review_family_id": str(mirrored_review.get("review_family_id") or "simultaneous_context_match"),
        "visibility_mode": str(mirrored_review.get("visibility_mode") or "review_only"),
        "supported_switch_kinds": list(mirrored_review.get("supported_switch_kinds") or ["review_only", "reject", "role_switch"]),
        "primary_loci": ["main_context", "scheduled_memory"],
        "primary_authority_preserved": bool(mirrored_review.get("primary_authority_preserved")),
        "review_status": review_status,
        "review_summary": review_summary,
        "current_activity_present": bool(activity_digest.get("current_activity_present")),
        "objective_link_count": int(activity_digest.get("objective_link_count") or 0),
        "explicit_query_present": bool(trigger_digest.get("explicit_query_present")),
        "trigger_mode": str(trigger_digest.get("trigger_mode") or "passive_auto"),
        "reference_window": reference_window,
        "support_source_count": len(support_sources),
        "support_sources": support_sources,
        "reason_item_count": reason_item_count,
        "derivative_surface_ids": present_surface_ids,
        "review_locations": review_locations,
        "guardrails": [
            "main context and scheduled memory remain the primary locus of understanding",
            "mirror-style comprehension surfaces stay derivative and non-authoritative",
            "optional-reference artifacts remain bounded review outputs rather than promotion signals",
        ],
    }
    summary["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in summary.items()
            if key != "summary_hash"
        }
    )
    return summary


def _has_learning_readiness_contract(summary: Any) -> bool:
    return bool(
        isinstance(summary, dict)
        and isinstance(summary.get("status"), str)
        and "ready" in summary
        and isinstance(summary.get("reason"), str)
        and isinstance(summary.get("reasons"), list)
        and isinstance(summary.get("unmet_conditions"), list)
        and isinstance(summary.get("observed_levels"), dict)
    )


def _surface_learning_readiness_state(summary: Any) -> Dict[str, Any]:
    readiness = summary if isinstance(summary, dict) else {}
    return {
        "status": str(readiness.get("status") or "not_ready"),
        "ready": bool(readiness.get("ready")),
        "reason": str(readiness.get("reason") or ""),
        "reasons": _unique_non_empty_strings(readiness.get("reasons")),
        "unmet_conditions": _unique_non_empty_strings(readiness.get("unmet_conditions")),
        "observed_levels": (
            dict(readiness.get("observed_levels"))
            if isinstance(readiness.get("observed_levels"), dict)
            else {}
        ),
    }


def _build_purpose_carrier_row(
    *,
    carrier_id: str,
    carrier_kind: str,
    engaged: bool,
    action_ids: Any,
    evidence_refs: Any = None,
    functionality_labels: Any = None,
    authoritative: bool = False,
    current_serving: bool = False,
    reporting_only: bool = False,
    review_only: bool = False,
    reason_summary: str = "",
    carrier_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_action_ids = _unique_non_empty_strings(action_ids)
    normalized_evidence_refs = _unique_non_empty_strings(evidence_refs)
    normalized_functionalities = _unique_non_empty_strings(functionality_labels)
    row = {
        "carrier_id": str(carrier_id or ""),
        "carrier_kind": str(carrier_kind or "support_group"),
        "engaged": bool(engaged and normalized_action_ids),
        "action_ids": normalized_action_ids,
        "action_count": len(normalized_action_ids),
        "evidence_refs": normalized_evidence_refs,
        "functionality_labels": normalized_functionalities,
        "authoritative": bool(authoritative),
        "current_serving": bool(current_serving),
        "reporting_only": bool(reporting_only),
        "review_only": bool(review_only),
        "reason_summary": str(reason_summary or ""),
    }
    if isinstance(carrier_context, dict) and carrier_context:
        row["carrier_context"] = dict(carrier_context)
    return row


def _latest_decision_signal(record: Dict[str, Any]) -> Dict[str, Any]:
    signals = record.get("decision_signals")
    if not isinstance(signals, list):
        return {}
    for item in reversed(signals):
        if isinstance(item, dict):
            return dict(item)
    return {}


def build_retrieval_quality_summary(
    record: Dict[str, Any],
    *,
    categorized_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}
    latest_signal = _latest_decision_signal(record)
    reference_profile = _reference_profile_from_record_or_derived(record)
    retrieval_components = (
        latest_signal.get("retrieval_components")
        if isinstance(latest_signal.get("retrieval_components"), dict)
        else {}
    )
    selection_migration_sandbox = (
        latest_signal.get("selection_migration_sandbox")
        if isinstance(latest_signal.get("selection_migration_sandbox"), dict)
        else {}
    )
    component_keys = _unique_non_empty_strings(list(retrieval_components.keys()))
    try:
        retrieval_score = (
            float(latest_signal.get("retrieval_score"))
            if latest_signal.get("retrieval_score") is not None
            else None
        )
    except Exception:
        retrieval_score = None
    try:
        retrieval_component_score = (
            float(latest_signal.get("retrieval_component_score"))
            if latest_signal.get("retrieval_component_score") is not None
            else None
        )
    except Exception:
        retrieval_component_score = None

    retrieval_signal_present = bool(
        retrieval_score is not None
        or retrieval_component_score is not None
        or retrieval_components
    )
    reference_profile_present = bool(
        _unique_non_empty_strings(reference_profile.get("labels"))
        or _unique_non_empty_strings(reference_profile.get("aliases"))
        or _unique_non_empty_strings(reference_profile.get("comparison_axes"))
    )
    join_quality_summary = summarize_categorized_context_join_quality(categorized, reference_profile)
    categorized_context_level = str(
        categorized.get("support_level")
        or categorized.get("level")
        or "missing"
    )

    return {
        "status": (
            "inspectable"
            if (retrieval_signal_present or reference_profile_present or categorized_context_level != "missing")
            else "unavailable"
        ),
        "retrieval_signal_present": retrieval_signal_present,
        "retrieval_score": retrieval_score,
        "retrieval_component_score": retrieval_component_score,
        "retrieval_component_keys": component_keys,
        "retrieval_component_count": len(component_keys),
        "categorized_context_level": categorized_context_level,
        "categorized_context_component_present": "categorized_context" in component_keys,
        "categorized_context_join_quality_summary": dict(join_quality_summary),
        "categorized_context_join_quality": str(join_quality_summary.get("join_quality") or "missing"),
        "categorized_context_follow_through_status": str(join_quality_summary.get("follow_through_status") or "missing"),
        "scene_summary_component_present": "scene_summary" in component_keys,
        "reference_label_component_present": "reference_label" in component_keys,
        "reference_profile_present": reference_profile_present,
        "selection_migration_sandbox": dict(selection_migration_sandbox),
    }


def build_comprehension_quality_summary(
    comprehension_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = comprehension_summary if isinstance(comprehension_summary, dict) else {}
    unresolved_gaps = _unique_non_empty_strings(summary.get("unresolved_gaps"))
    present = bool(summary.get("present")) or bool(summary)
    level = str(summary.get("level") or ("missing" if not present else "weak"))
    return {
        "status": "present" if present else "missing",
        "present": present,
        "level": level,
        "summary": str(summary.get("summary") or ""),
        "unresolved_gaps": unresolved_gaps,
        "unresolved_gap_count": len(unresolved_gaps),
        "supporting_evidence": (
            dict(summary.get("supporting_evidence"))
            if isinstance(summary.get("supporting_evidence"), dict)
            else {}
        ),
        "ready_for_learning_review": bool(level == "strong" and not unresolved_gaps),
    }


def build_validation_retention_evidence_summary(
    *,
    comprehension_summary: Optional[Dict[str, Any]] = None,
    deterministic_validation_gate: Optional[Dict[str, Any]] = None,
    retained_memory_follow_through_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    comprehension = comprehension_summary if isinstance(comprehension_summary, dict) else {}
    gate = deterministic_validation_gate if isinstance(deterministic_validation_gate, dict) else {}
    retained = (
        retained_memory_follow_through_summary
        if isinstance(retained_memory_follow_through_summary, dict)
        else {}
    )

    supporting_evidence = (
        comprehension.get("supporting_evidence")
        if isinstance(comprehension.get("supporting_evidence"), dict)
        else {}
    )
    validation_evidence = (
        supporting_evidence.get("validation_evidence")
        if isinstance(supporting_evidence.get("validation_evidence"), dict)
        else {}
    )
    retention_evidence = (
        supporting_evidence.get("retention_evidence")
        if isinstance(supporting_evidence.get("retention_evidence"), dict)
        else {}
    )
    telemetry_retention = (
        retained.get("telemetry_retention_summary")
        if isinstance(retained.get("telemetry_retention_summary"), dict)
        else {}
    )

    request_validation_passed = bool(gate.get("request_validation_passed"))
    schema_validation_status = str(gate.get("schema_validation_status") or "not_available")
    constraint_review_status = str(gate.get("constraint_review_status") or "not_available")
    deterministic_rejection_verdict = str(
        gate.get("deterministic_rejection_verdict") or "review_required"
    )
    scene_validation_failed = int(validation_evidence.get("scene_validation_failed") or 0)
    scene_validation_hard_failure = bool(validation_evidence.get("scene_validation_hard_failure"))
    record_id_present = bool(retention_evidence.get("record_id_present"))
    categorized_context_persisted = bool(retention_evidence.get("categorized_context_persisted"))
    comprehension_review_persisted = bool(retention_evidence.get("comprehension_review_persisted"))
    telemetry_retained = bool(telemetry_retention.get("telemetry_retained"))
    measurement_hash_present = bool(telemetry_retention.get("measurement_hash_present"))
    runtime_provenance_present = bool(telemetry_retention.get("runtime_provenance_present"))

    validation_ready = bool(
        request_validation_passed
        and schema_validation_status != "failed"
        and constraint_review_status != "failed"
        and deterministic_rejection_verdict == "pass"
        and scene_validation_failed <= 0
        and not scene_validation_hard_failure
    )
    retention_ready = bool(
        record_id_present
        and categorized_context_persisted
        and comprehension_review_persisted
        and telemetry_retained
    )
    evidence_trace_present = bool(measurement_hash_present or runtime_provenance_present)

    unresolved_gaps: List[str] = []
    if not request_validation_passed:
        unresolved_gaps.append("request_validation_missing")
    if schema_validation_status == "failed" or scene_validation_failed > 0 or scene_validation_hard_failure:
        unresolved_gaps.append("schema_validation_failures")
    if constraint_review_status == "failed":
        unresolved_gaps.append("constraint_review_failures")
    if deterministic_rejection_verdict == "reject":
        unresolved_gaps.append("deterministic_rejection_active")
    if not categorized_context_persisted:
        unresolved_gaps.append("categorized_context_not_persisted")
    if not comprehension_review_persisted:
        unresolved_gaps.append("comprehension_review_not_persisted")
    if not telemetry_retained:
        unresolved_gaps.append("telemetry_retention_missing")
    if not evidence_trace_present:
        unresolved_gaps.append("recheckable_trace_missing")

    present = bool(gate or retention_evidence or telemetry_retention)
    ready_for_recheckable_reasoning = bool(validation_ready and retention_ready and evidence_trace_present)
    if ready_for_recheckable_reasoning:
        status = "recheckable"
        summary = "validation and retention evidence are explicit and re-checkable"
    elif present:
        status = "partial"
        summary = "validation and retention evidence are only partially explicit"
    else:
        status = "missing"
        summary = "validation and retention evidence are missing"

    return {
        "status": status,
        "present": present,
        "validation_ready": validation_ready,
        "retention_ready": retention_ready,
        "evidence_trace_present": evidence_trace_present,
        "ready_for_recheckable_reasoning": ready_for_recheckable_reasoning,
        "summary": summary,
        "validation_state": {
            "request_validation_status": str(gate.get("request_validation_status") or "missing"),
            "schema_validation_status": schema_validation_status,
            "constraint_review_status": constraint_review_status,
            "deterministic_rejection_verdict": deterministic_rejection_verdict,
            "scene_validation_failed": scene_validation_failed,
            "scene_validation_hard_failure": scene_validation_hard_failure,
        },
        "retention_state": {
            "record_id_present": record_id_present,
            "categorized_context_persisted": categorized_context_persisted,
            "comprehension_review_persisted": comprehension_review_persisted,
            "telemetry_retained": telemetry_retained,
            "measurement_hash_present": measurement_hash_present,
            "runtime_provenance_present": runtime_provenance_present,
        },
        "unresolved_gaps": unresolved_gaps,
    }


def build_measurement_evidence_summary(
    *,
    measurement_summary: Optional[Dict[str, Any]] = None,
    categorized_summary: Optional[Dict[str, Any]] = None,
    runtime_measurement_readiness_summary: Optional[Dict[str, Any]] = None,
    runtime_measurement_provenance_chain: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    measurement = measurement_summary if isinstance(measurement_summary, dict) else {}
    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}
    runtime_readiness = (
        runtime_measurement_readiness_summary
        if isinstance(runtime_measurement_readiness_summary, dict)
        else {}
    )
    runtime_provenance = (
        runtime_measurement_provenance_chain
        if isinstance(runtime_measurement_provenance_chain, dict)
        else {}
    )

    signals = measurement.get("signals") if isinstance(measurement.get("signals"), dict) else {}
    bridge_sources = _unique_non_empty_strings(categorized.get("bridge_sources"))
    adequacy_level = str(measurement.get("level") or "missing")
    measurement_recorded = bool(
        signals.get("measurement_recorded")
        or adequacy_level not in {"missing", "absent"}
        or runtime_readiness
        or runtime_provenance
    )
    snapshot_present = bool(signals.get("snapshot_present"))
    measurement_hash_present = bool(signals.get("measurement_hash_present"))
    bridge_attachment_present = bool(
        signals.get("bridge_present")
        or bridge_sources
        or int(runtime_readiness.get("bridge_output_count") or 0) > 0
    )
    telemetry_completed_present = bool(signals.get("telemetry_completed_present"))
    provenance_chain_present = str(runtime_provenance.get("status") or "") == "present"
    ready_for_commit = bool(runtime_readiness.get("ready_for_commit"))
    evidence_trace_present = bool(measurement_hash_present or provenance_chain_present)

    unresolved_gaps: List[str] = []
    if not measurement_recorded:
        unresolved_gaps.append("measurement_not_recorded")
    if not bridge_attachment_present:
        unresolved_gaps.append("bridge_attachment_missing")
    if not evidence_trace_present:
        unresolved_gaps.append("measurement_trace_missing")

    present = bool(measurement or runtime_readiness or runtime_provenance or bridge_sources)
    if measurement_recorded and bridge_attachment_present and evidence_trace_present:
        status = "inspectable"
        summary = "measurement evidence is explicit and traceable"
    elif present:
        status = "partial"
        summary = "measurement evidence is only partially explicit"
    else:
        status = "missing"
        summary = "measurement evidence is missing"

    return {
        "status": status,
        "present": present,
        "adequacy_level": adequacy_level,
        "adequacy_reason": str(measurement.get("reason") or ""),
        "measurement_recorded": measurement_recorded,
        "bridge_attachment_present": bridge_attachment_present,
        "bridge_sources": bridge_sources,
        "bridge_output_count": int(runtime_readiness.get("bridge_output_count") or 0),
        "ready_for_commit": ready_for_commit,
        "evidence_trace_present": evidence_trace_present,
        "snapshot_present": snapshot_present,
        "measurement_hash_present": measurement_hash_present,
        "telemetry_completed_present": telemetry_completed_present,
        "provenance_chain_present": provenance_chain_present,
        "unresolved_gaps": unresolved_gaps,
        "summary": summary,
    }


def build_measurement_schema_trace_summary(
    *,
    schema_version: str = "",
    categorized_summary: Optional[Dict[str, Any]] = None,
    runtime_measurement_readiness_summary: Optional[Dict[str, Any]] = None,
    runtime_measurement_commitment_summary: Optional[Dict[str, Any]] = None,
    runtime_measurement_provenance_chain: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}
    runtime_readiness = (
        runtime_measurement_readiness_summary
        if isinstance(runtime_measurement_readiness_summary, dict)
        else {}
    )
    runtime_commitment = (
        runtime_measurement_commitment_summary
        if isinstance(runtime_measurement_commitment_summary, dict)
        else {}
    )
    runtime_provenance = (
        runtime_measurement_provenance_chain
        if isinstance(runtime_measurement_provenance_chain, dict)
        else {}
    )

    normalized_schema_version = str(schema_version or "").strip()
    bridge_sources = _unique_non_empty_strings(categorized.get("bridge_sources"))
    bridge_request_ids = _unique_non_empty_strings(
        list(runtime_commitment.get("bridge_request_ids") or [])
        + [runtime_commitment.get("request_id")]
    )
    provenance_events = (
        runtime_provenance.get("events")
        if isinstance(runtime_provenance.get("events"), list)
        else []
    )
    trace_stages = _unique_non_empty_strings(
        [item.get("stage") for item in provenance_events if isinstance(item, dict)]
    )
    bridge_output_count = int(runtime_readiness.get("bridge_output_count") or runtime_commitment.get("bridge_output_count") or 0)
    bridge_attachment_present = bool(runtime_readiness.get("bridge_present") or bridge_output_count > 0 or bridge_sources)
    provenance_chain_present = str(runtime_provenance.get("status") or "") == "present"

    unresolved_gaps: List[str] = []
    if not normalized_schema_version:
        unresolved_gaps.append("schema_version_missing")
    if not bridge_attachment_present:
        unresolved_gaps.append("bridge_attachment_missing")
    if not bridge_request_ids:
        unresolved_gaps.append("bridge_request_ids_missing")
    if not provenance_chain_present:
        unresolved_gaps.append("provenance_chain_missing")

    present = bool(
        normalized_schema_version
        or bridge_sources
        or bridge_output_count
        or bridge_request_ids
        or runtime_provenance
    )
    if normalized_schema_version and bridge_attachment_present and bridge_request_ids and provenance_chain_present:
        status = "inspectable"
        summary = "schema and bridge trace are explicit and reproducible"
    elif present:
        status = "partial"
        summary = "schema and bridge trace are only partially explicit"
    else:
        status = "missing"
        summary = "schema and bridge trace are missing"

    return {
        "status": status,
        "present": present,
        "schema_version": normalized_schema_version,
        "bridge_attachment_present": bridge_attachment_present,
        "bridge_sources": bridge_sources,
        "bridge_output_count": bridge_output_count,
        "bridge_request_ids": bridge_request_ids,
        "provenance_chain_present": provenance_chain_present,
        "trace_stage_count": len(trace_stages),
        "trace_stages": trace_stages,
        "unresolved_gaps": unresolved_gaps,
        "summary": summary,
    }


def build_operator_explanation_summary(
    *,
    preparation_state: Optional[Dict[str, Any]] = None,
    carrier_rows: Optional[List[Dict[str, Any]]] = None,
    comprehension_quality_summary: Optional[Dict[str, Any]] = None,
    validation_retention_evidence_summary: Optional[Dict[str, Any]] = None,
    measurement_evidence_summary: Optional[Dict[str, Any]] = None,
    measurement_schema_trace_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    preparation = preparation_state if isinstance(preparation_state, dict) else {}
    rows = carrier_rows if isinstance(carrier_rows, list) else []
    comprehension_quality = (
        comprehension_quality_summary
        if isinstance(comprehension_quality_summary, dict)
        else {}
    )
    validation_retention = (
        validation_retention_evidence_summary
        if isinstance(validation_retention_evidence_summary, dict)
        else {}
    )
    measurement_evidence = (
        measurement_evidence_summary
        if isinstance(measurement_evidence_summary, dict)
        else {}
    )
    schema_trace = (
        measurement_schema_trace_summary
        if isinstance(measurement_schema_trace_summary, dict)
        else {}
    )

    engaged_rows = [row for row in rows if isinstance(row, dict) and bool(row.get("engaged"))]
    carrier_reason_summaries = _unique_non_empty_strings(
        [row.get("reason_summary") for row in engaged_rows if isinstance(row, dict)]
    )
    readiness_state = (
        preparation.get("readiness_state")
        if isinstance(preparation.get("readiness_state"), dict)
        else {}
    )
    quality_snapshot = {
        "readiness_status": str(readiness_state.get("status") or "not_ready"),
        "comprehension_level": str(comprehension_quality.get("level") or "missing"),
        "validation_retention_status": str(validation_retention.get("status") or "missing"),
        "measurement_status": str(measurement_evidence.get("status") or "missing"),
        "schema_trace_status": str(schema_trace.get("status") or "missing"),
    }
    unresolved_gaps = _unique_non_empty_strings(
        [
            "validation_retention_incomplete"
            if quality_snapshot["validation_retention_status"] != "recheckable"
            else "",
            "measurement_evidence_incomplete"
            if quality_snapshot["measurement_status"] != "inspectable"
            else "",
            "schema_trace_incomplete"
            if quality_snapshot["schema_trace_status"] != "inspectable"
            else "",
        ]
    )
    present = bool(carrier_reason_summaries or any(value != "missing" for value in quality_snapshot.values()))
    summary = (
        f"operator explanation available from {len(engaged_rows)} engaged carriers and explicit quality surfaces"
        if carrier_reason_summaries
        else ("operator explanation is only partially explicit" if present else "operator explanation is missing")
    )
    return {
        "status": "present" if present else "missing",
        "summary": summary,
        "engaged_carrier_count": len(engaged_rows),
        "carrier_reason_summaries": carrier_reason_summaries,
        "quality_snapshot": quality_snapshot,
        "unresolved_gaps": unresolved_gaps,
    }


def _summarize_ai_brain_durable_memory_contract(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {"status": "missing"}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    contract = (
        derived.get("ai_brain_durable_memory_contract")
        if isinstance(derived.get("ai_brain_durable_memory_contract"), dict)
        else {}
    )
    alignment = contract.get("alignment") if isinstance(contract.get("alignment"), dict) else {}

    return {
        "status": str(contract.get("status") or "missing"),
        "alignment_status": str(alignment.get("status") or "missing"),
        "brain_state_present": bool(contract.get("brain_state_present")),
        "spatial_memory_present": bool(contract.get("spatial_memory_present")),
        "spatial_memory_measurement_count": int(contract.get("spatial_memory_measurement_count") or 0),
        "durable_contract_explicit": bool(alignment.get("durable_contract_explicit")),
        "validated_measurement_present": bool(alignment.get("validated_measurement_present")),
        "validated_measurement_preserved": bool(alignment.get("validated_measurement_preserved")),
        "measurement_hash_matches_semantic_record": bool(alignment.get("measurement_hash_matches_semantic_record")),
        "request_id_matches_semantic_record": bool(alignment.get("request_id_matches_semantic_record")),
        "record_id_matches_semantic_record": bool(alignment.get("record_id_matches_semantic_record")),
        "summary": str(alignment.get("summary") or contract.get("status") or "missing"),
    }


def build_ai_brain_durable_contract_alignment_summary(
    *,
    durable_memory_contract_summary: Optional[Dict[str, Any]] = None,
    categorized_context_follow_through_summary: Optional[Dict[str, Any]] = None,
    retained_memory_capability_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    contract = durable_memory_contract_summary if isinstance(durable_memory_contract_summary, dict) else {}
    follow_through = (
        categorized_context_follow_through_summary
        if isinstance(categorized_context_follow_through_summary, dict)
        else {}
    )
    capability = retained_memory_capability_summary if isinstance(retained_memory_capability_summary, dict) else {}

    durable_status = str(contract.get("status") or "missing")
    follow_status = str(follow_through.get("status") or "missing")
    persistence_status = str(follow_through.get("persistence_status") or "missing")
    capability_status = str(capability.get("status") or "missing")

    if (
        durable_status == "complete"
        and follow_status == "ready"
        and persistence_status == "persisted"
        and capability_status == "present"
    ):
        status = "aligned"
    elif all(value == "missing" for value in (durable_status, follow_status, persistence_status, capability_status)):
        status = "missing"
    else:
        status = "partial"

    return {
        "status": status,
        "durable_memory_contract_status": durable_status,
        "categorized_context_follow_through_status": follow_status,
        "persistence_status": persistence_status,
        "retained_memory_capability_status": capability_status,
        "spatial_memory_measurement_count": int(contract.get("spatial_memory_measurement_count") or 0),
        "gap_reasons": _unique_non_empty_strings(follow_through.get("gap_reasons")),
    }


def build_retained_memory_follow_through_summary(
    record: Dict[str, Any],
    *,
    categorized_summary: Optional[Dict[str, Any]] = None,
    comprehension_summary: Optional[Dict[str, Any]] = None,
    readiness_summary: Optional[Dict[str, Any]] = None,
    bounded_runtime_switch_inventory: Optional[Dict[str, Any]] = None,
    deterministic_validation_gate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
    spatial_snapshots = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}

    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}
    comprehension = comprehension_summary if isinstance(comprehension_summary, dict) else {}
    readiness = (
        dict(readiness_summary)
        if isinstance(readiness_summary, dict)
        else _build_learning_readiness_verdict_for_record(record)
    )
    switch_inventory = bounded_runtime_switch_inventory if isinstance(bounded_runtime_switch_inventory, dict) else {}
    runtime_provenance = (
        derived.get("runtime_measurement_provenance_chain")
        if isinstance(derived.get("runtime_measurement_provenance_chain"), dict)
        else {}
    )
    comprehension_quality_summary = build_comprehension_quality_summary(comprehension)
    latest_signal = _latest_decision_signal(record)
    selection_migration_sandbox = (
        latest_signal.get("selection_migration_sandbox")
        if isinstance(latest_signal.get("selection_migration_sandbox"), dict)
        else {}
    )
    reference_profile = _reference_profile_from_record_or_derived(record, derived)
    retrieval_quality_summary = build_retrieval_quality_summary(
        record,
        categorized_summary=categorized,
    )
    categorized_context_follow_through_summary = (
        retrieval_quality_summary.get("categorized_context_join_quality_summary")
        if isinstance(retrieval_quality_summary.get("categorized_context_join_quality_summary"), dict)
        else summarize_categorized_context_join_quality(categorized, reference_profile)
    )
    reference_use_seed = {
        "reference_use_score": float(categorized.get("reference_use_score", 0.0) or 0.0),
        "reference_use_breakdown": (
            dict(categorized.get("reference_use_breakdown"))
            if isinstance(categorized.get("reference_use_breakdown"), dict)
            else {
                "label_match_count": 0,
                "alias_match_count": 0,
                "comparison_axis_match_count": 0,
            }
        ),
        "matched_reference_category_count": int(categorized.get("matched_reference_category_count") or 0),
        "matched_reference_term_count": int(categorized.get("matched_reference_term_count") or 0),
    }
    if not reference_use_seed["reference_use_score"] and bool(
        _unique_non_empty_strings(reference_profile.get("labels"))
        or _unique_non_empty_strings(reference_profile.get("aliases"))
        or _unique_non_empty_strings(reference_profile.get("comparison_axes"))
    ):
        reference_use_seed.update(
            summarize_reference_use(
                record,
                {
                    "reference_labels": _unique_non_empty_strings(reference_profile.get("labels"))
                    + _unique_non_empty_strings(reference_profile.get("aliases")),
                    "comparison_axes": _unique_non_empty_strings(reference_profile.get("comparison_axes")),
                },
            )
        )
    capability_measurement_summary = build_retained_memory_capability_measurement_summary(
        retrieval_quality_summary=retrieval_quality_summary,
        categorized_summary={
            **categorized,
            "reference_use_score": float(reference_use_seed.get("reference_use_score", 0.0) or 0.0),
            "reference_use_breakdown": dict(reference_use_seed.get("reference_use_breakdown") or {}),
            "matched_reference_category_count": int(
                reference_use_seed.get("matched_reference_category_count")
                or categorized.get("matched_reference_category_count")
                or 0
            ),
            "matched_reference_term_count": int(
                reference_use_seed.get("matched_reference_term_count")
                or categorized.get("matched_reference_term_count")
                or 0
            ),
        },
        retained_memory_follow_through_summary={
            "categorized_context_follow_through_summary": {
                "status": str(categorized_context_follow_through_summary.get("follow_through_status") or "missing"),
                "join_status": str(categorized_context_follow_through_summary.get("join_status") or "missing"),
                "join_quality": str(categorized_context_follow_through_summary.get("join_quality") or "missing"),
                "reference_profile_present": bool(categorized_context_follow_through_summary.get("reference_profile_present")),
                "matched_reference_category_count": int(
                    categorized_context_follow_through_summary.get("matched_reference_category_count") or 0
                ),
                "matched_reference_term_count": int(
                    categorized_context_follow_through_summary.get("matched_reference_term_count") or 0
                ),
            },
        },
    )
    ai_brain_durable_memory_contract_summary = _summarize_ai_brain_durable_memory_contract(record)
    ai_brain_durable_contract_alignment_summary = build_ai_brain_durable_contract_alignment_summary(
        durable_memory_contract_summary=ai_brain_durable_memory_contract_summary,
        categorized_context_follow_through_summary={
            "status": str(categorized_context_follow_through_summary.get("follow_through_status") or "missing"),
            "persistence_status": str(categorized_context_follow_through_summary.get("persistence_status") or "missing"),
            "gap_reasons": _unique_non_empty_strings(categorized_context_follow_through_summary.get("gap_reasons")),
        },
        retained_memory_capability_summary=capability_measurement_summary,
    )

    relation_families = _unique_non_empty_strings(categorized.get("relation_families"))
    bridge_sources = _unique_non_empty_strings(categorized.get("bridge_sources"))
    retrieval_signal_present = bool(retrieval_quality_summary.get("retrieval_signal_present"))
    retrieval_ready = bool(
        retrieval_signal_present
        or _unique_non_empty_strings(reference_profile.get("labels"))
        or _unique_non_empty_strings(reference_profile.get("aliases"))
        or _unique_non_empty_strings(reference_profile.get("comparison_axes"))
        or relation_families
        or bridge_sources
        or str(comprehension.get("level") or "missing") != "missing"
    )

    switches = switch_inventory.get("switches") if isinstance(switch_inventory.get("switches"), list) else []
    scheduled_task_labels: List[str] = []
    for item in switches:
        if not isinstance(item, dict) or str(item.get("switch_kind") or "") != "schedule_follow_up":
            continue
        scheduled_task_labels.extend(_unique_non_empty_strings(item.get("scheduled_task_labels")))
    scheduled_task_labels = _unique_non_empty_strings(scheduled_task_labels)

    telemetry_retained = bool(
        runtime_provenance
        or spatial_snapshots.get("latest")
        or derived.get("spatial_measurement_hash")
        or spatial_snapshots.get("measurement_hash")
    )
    learning_gate_summary = _surface_learning_readiness_state(readiness)
    learning_gate_summary["selection_migration_sandbox"] = dict(selection_migration_sandbox)
    comprehension_supporting_evidence = (
        comprehension.get("supporting_evidence")
        if isinstance(comprehension.get("supporting_evidence"), dict)
        else {}
    )
    augmented_comprehension_summary = dict(comprehension)
    augmented_comprehension_summary["supporting_evidence"] = {
        **comprehension_supporting_evidence,
        "validation_evidence": {
            "scene_validation_failed": 0,
            "scene_validation_hard_failure": False,
            **(
                comprehension_supporting_evidence.get("validation_evidence")
                if isinstance(comprehension_supporting_evidence.get("validation_evidence"), dict)
                else {}
            ),
        },
        "retention_evidence": {
            "record_id_present": bool(record.get("id")),
            "categorized_context_persisted": bool(categorized),
            "comprehension_review_persisted": bool(comprehension),
            **(
                comprehension_supporting_evidence.get("retention_evidence")
                if isinstance(comprehension_supporting_evidence.get("retention_evidence"), dict)
                else {}
            ),
        },
    }
    validation_retention_evidence_summary = build_validation_retention_evidence_summary(
        comprehension_summary=augmented_comprehension_summary,
        deterministic_validation_gate=deterministic_validation_gate,
        retained_memory_follow_through_summary={
            "telemetry_retention_summary": {
                "telemetry_retained": telemetry_retained,
                "measurement_hash_present": bool(
                    derived.get("spatial_measurement_hash") or spatial_snapshots.get("measurement_hash")
                ),
                "runtime_provenance_present": bool(runtime_provenance),
            }
        },
    )
    active_surface_count = sum(
        1
        for present in (
            bool(relation_families or bridge_sources),
            telemetry_retained,
            bool(scheduled_task_labels),
            bool(validation_retention_evidence_summary.get("ready_for_recheckable_reasoning")),
            bool(capability_measurement_summary.get("reference_use_summary", {}).get("status") == "present"),
            bool(capability_measurement_summary.get("reference_use_summary", {}).get("retrieval_component_present")),
        )
        if present
    )
    pressure_score = round(float(active_surface_count) / 6.0, 6)
    if active_surface_count >= 5:
        pressure_state = "elevated"
        pressure_summary = "retained-memory follow-through pressure is elevated for the current record"
    elif active_surface_count >= 3:
        pressure_state = "active"
        pressure_summary = "retained-memory follow-through pressure is active for the current record"
    elif active_surface_count >= 1:
        pressure_state = "light"
        pressure_summary = "retained-memory follow-through pressure is present but light for the current record"
    else:
        pressure_state = "idle"
        pressure_summary = "retained-memory follow-through pressure is idle for the current record"
    summary = {
        "status": "present",
        "relational_attachment_summary": {
            "status": "attached" if (relation_families or bridge_sources) else "pending",
            "attachment_ready": bool(relation_families or bridge_sources),
            "relation_families": relation_families,
            "bridge_sources": bridge_sources,
        },
        "retrieval_readiness_summary": {
            "status": "ready" if retrieval_ready else "not_ready",
            "retrieval_ready": retrieval_ready,
            "retrieval_signal_present": retrieval_signal_present,
            "reference_profile_present": bool(
                _unique_non_empty_strings(reference_profile.get("labels"))
                or _unique_non_empty_strings(reference_profile.get("aliases"))
                or _unique_non_empty_strings(reference_profile.get("comparison_axes"))
            ),
            "selection_migration_sandbox": dict(selection_migration_sandbox),
        },
        "retrieval_quality_summary": retrieval_quality_summary,
        "categorized_context_follow_through_summary": {
            "status": str(categorized_context_follow_through_summary.get("follow_through_status") or "missing"),
            "join_status": str(categorized_context_follow_through_summary.get("join_status") or "missing"),
            "join_quality": str(categorized_context_follow_through_summary.get("join_quality") or "missing"),
            "persistence_status": str(categorized_context_follow_through_summary.get("persistence_status") or "missing"),
            "reference_profile_present": bool(categorized_context_follow_through_summary.get("reference_profile_present")),
            "matched_reference_category_count": int(
                categorized_context_follow_through_summary.get("matched_reference_category_count") or 0
            ),
            "matched_reference_term_count": int(
                categorized_context_follow_through_summary.get("matched_reference_term_count") or 0
            ),
            "gap_reasons": _unique_non_empty_strings(categorized_context_follow_through_summary.get("gap_reasons")),
            "retrieval_component_present": bool(retrieval_quality_summary.get("categorized_context_component_present")),
            "retrieval_ready": retrieval_ready,
        },
        "capability_measurement_summary": {
            **capability_measurement_summary,
            "retained_storage_pressure_summary": {
                **(
                    capability_measurement_summary.get("retained_storage_pressure_summary")
                    if isinstance(capability_measurement_summary.get("retained_storage_pressure_summary"), dict)
                    else {}
                ),
                "status": "present",
                "active_surface_count": active_surface_count,
                "scheduled_task_count": len(scheduled_task_labels),
                "relational_attachment_ready": bool(relation_families or bridge_sources),
                "telemetry_retained": telemetry_retained,
                "validation_retention_ready": bool(
                    validation_retention_evidence_summary.get("ready_for_recheckable_reasoning")
                ),
                "pressure_state": pressure_state,
                "pressure_score": pressure_score,
                "summary": pressure_summary,
            },
        },
        "comprehension_quality_summary": comprehension_quality_summary,
        "validation_retention_evidence_summary": validation_retention_evidence_summary,
        "ai_brain_durable_contract_alignment_summary": ai_brain_durable_contract_alignment_summary,
        "telemetry_retention_summary": {
            "status": "retained" if telemetry_retained else "missing",
            "telemetry_retained": telemetry_retained,
            "snapshot_present": bool(spatial_snapshots.get("latest")),
            "measurement_hash_present": bool(
                derived.get("spatial_measurement_hash") or spatial_snapshots.get("measurement_hash")
            ),
            "runtime_provenance_present": bool(runtime_provenance),
        },
        "follow_through_summary": {
            "status": "scheduled" if scheduled_task_labels else "not_scheduled",
            "scheduled": bool(scheduled_task_labels),
            "scheduled_task_labels": scheduled_task_labels,
            "engaged_switch_kinds": _unique_non_empty_strings(switch_inventory.get("engaged_switch_kinds")),
        },
        "learning_gate_summary": learning_gate_summary,
    }
    summary["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in summary.items()
            if key != "summary_hash"
        }
    )
    return summary


def build_retained_memory_capability_measurement_summary(
    *,
    retrieval_quality_summary: Optional[Dict[str, Any]] = None,
    categorized_summary: Optional[Dict[str, Any]] = None,
    retained_memory_follow_through_summary: Optional[Dict[str, Any]] = None,
    retained_storage_pressure: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    retrieval = retrieval_quality_summary if isinstance(retrieval_quality_summary, dict) else {}
    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}
    retained_follow = (
        retained_memory_follow_through_summary
        if isinstance(retained_memory_follow_through_summary, dict)
        else {}
    )
    storage = retained_storage_pressure if isinstance(retained_storage_pressure, dict) else {}
    follow_through = (
        retained_follow.get("categorized_context_follow_through_summary")
        if isinstance(retained_follow.get("categorized_context_follow_through_summary"), dict)
        else {}
    )
    retrieval_readiness = (
        retained_follow.get("retrieval_readiness_summary")
        if isinstance(retained_follow.get("retrieval_readiness_summary"), dict)
        else {}
    )
    telemetry_retention = (
        retained_follow.get("telemetry_retention_summary")
        if isinstance(retained_follow.get("telemetry_retention_summary"), dict)
        else {}
    )
    storage_metrics = storage.get("metrics") if isinstance(storage.get("metrics"), dict) else {}
    breakdown = (
        categorized.get("reference_use_breakdown")
        if isinstance(categorized.get("reference_use_breakdown"), dict)
        else {}
    )

    reference_profile_present = bool(
        categorized.get("reference_profile_present")
        or retrieval.get("reference_profile_present")
        or follow_through.get("reference_profile_present")
    )
    reference_use_score = 0.0
    try:
        reference_use_score = float(categorized.get("reference_use_score", 0.0) or 0.0)
    except Exception:
        reference_use_score = 0.0
    matched_reference_category_count = int(
        follow_through.get("matched_reference_category_count")
        or categorized.get("matched_reference_category_count")
        or 0
    )
    matched_reference_term_count = int(
        follow_through.get("matched_reference_term_count")
        or categorized.get("matched_reference_term_count")
        or 0
    )
    reference_use_present = bool(
        reference_profile_present or reference_use_score > 0.0 or matched_reference_term_count > 0
    )
    reference_use_summary = {
        "status": "present" if reference_use_present else "missing",
        "reference_profile_present": reference_profile_present,
        "retrieval_component_present": bool(retrieval.get("reference_label_component_present")),
        "reference_use_score": reference_use_score,
        "reference_use_breakdown": {
            "label_match_count": int(breakdown.get("label_match_count", 0) or 0),
            "alias_match_count": int(breakdown.get("alias_match_count", 0) or 0),
            "comparison_axis_match_count": int(breakdown.get("comparison_axis_match_count", 0) or 0),
        },
        "matched_reference_category_count": matched_reference_category_count,
        "matched_reference_term_count": matched_reference_term_count,
        "summary": (
            "reference-use evidence is explicit in retained categorized context"
            if reference_use_present
            else "reference-use evidence is not explicit in retained categorized context"
        ),
    }

    categorized_context_present = bool(
        categorized
        or retrieval.get("retrieval_signal_present")
        or retrieval_readiness.get("retrieval_ready")
        or follow_through
    )
    categorized_context_benefit_summary = {
        "status": "present" if categorized_context_present else "missing",
        "support_level": str(categorized.get("support_level") or categorized.get("level") or "missing"),
        "join_status": str(
            follow_through.get("join_status")
            or categorized.get("join_status")
            or retrieval.get("categorized_context_join_quality_summary", {}).get("join_status")
            or "missing"
        ),
        "join_quality": str(
            follow_through.get("join_quality")
            or categorized.get("join_quality")
            or retrieval.get("categorized_context_join_quality")
            or "missing"
        ),
        "follow_through_status": str(
            follow_through.get("status")
            or categorized.get("follow_through_status")
            or retrieval.get("categorized_context_follow_through_status")
            or "missing"
        ),
        "retrieval_signal_present": bool(retrieval.get("retrieval_signal_present")),
        "retrieval_ready": bool(retrieval_readiness.get("retrieval_ready")),
        "telemetry_retained": bool(telemetry_retention.get("telemetry_retained")),
        "relation_family_count": len(_unique_non_empty_strings(categorized.get("relation_families"))),
        "bridge_source_count": len(_unique_non_empty_strings(categorized.get("bridge_sources"))),
        "summary": (
            "categorized-context retention remains inspectable for retrieval follow-through"
            if categorized_context_present
            else "categorized-context benefit is not available in the current retained window"
        ),
    }

    retained_storage_available = bool(storage.get("available"))
    retained_storage_pressure_summary = {
        "status": "present" if retained_storage_available else "unavailable",
        "available": retained_storage_available,
        "retained_file_count": int(storage_metrics.get("retained_file_count", 0) or 0),
        "retained_total_bytes": int(storage_metrics.get("retained_total_bytes", 0) or 0),
        "candidate_partition_count": int(storage_metrics.get("candidate_partition_count", 0) or 0),
        "candidate_partition_roots": [
            str(item) for item in (storage_metrics.get("candidate_partition_roots") or []) if isinstance(item, str)
        ],
        "storage_density_bytes_per_file": float(storage_metrics.get("storage_density_bytes_per_file", 0.0) or 0.0),
        "largest_root_by_bytes": (
            dict(storage_metrics.get("largest_root_by_bytes"))
            if isinstance(storage_metrics.get("largest_root_by_bytes"), dict)
            else {}
        ),
        "metrics_hash": str(storage.get("metrics_hash") or "") if retained_storage_available else "",
        "inputs_hash": str(storage.get("inputs_hash") or "") if retained_storage_available else "",
        "summary": (
            "retained-storage pressure remains bounded and inspectable through existing metrics hooks"
            if retained_storage_available
            else str(storage.get("reason") or "retained-storage pressure metrics are unavailable")
        ),
    }

    present = bool(reference_use_present or categorized_context_present or retained_storage_available)
    payload = {
        "status": "present" if present else "missing",
        "reference_use_summary": reference_use_summary,
        "categorized_context_benefit_summary": categorized_context_benefit_summary,
        "retained_storage_pressure_summary": retained_storage_pressure_summary,
        "summary": (
            "retained-memory capability measurement composes reference use, categorized-context benefit, and bounded retained-storage pressure"
            if present
            else "retained-memory capability measurement is unavailable"
        ),
    }
    payload["measurement_hash"] = _stable_hash(payload)
    return payload


def _merge_retained_memory_follow_through_summary(
    persisted_summary: Optional[Dict[str, Any]],
    rebuilt_summary: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(persisted_summary, dict) or not persisted_summary:
        return rebuilt_summary

    merged = dict(rebuilt_summary)
    merged.update(persisted_summary)
    for key in (
        "relational_attachment_summary",
        "retrieval_readiness_summary",
        "retrieval_quality_summary",
        "categorized_context_follow_through_summary",
        "capability_measurement_summary",
        "comprehension_quality_summary",
        "validation_retention_evidence_summary",
        "ai_brain_durable_contract_alignment_summary",
        "telemetry_retention_summary",
        "follow_through_summary",
        "learning_gate_summary",
    ):
        rebuilt_value = rebuilt_summary.get(key)
        persisted_value = persisted_summary.get(key)
        if isinstance(rebuilt_value, dict) and isinstance(persisted_value, dict):
            merged[key] = {**rebuilt_value, **persisted_value}
    return merged


def build_reference_grounding_verification(
    *,
    reference_profile: Optional[Dict[str, Any]] = None,
    categorized_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    profile = reference_profile if isinstance(reference_profile, dict) else {}
    categorized = categorized_summary if isinstance(categorized_summary, dict) else {}

    reference_labels = _unique_non_empty_strings(profile.get("labels"))
    reference_aliases = _unique_non_empty_strings(profile.get("aliases"))
    comparison_axes = _unique_non_empty_strings(profile.get("comparison_axes"))

    scene_summary_present = bool(categorized.get("scene_summary_present"))
    asset_mapped = bool(reference_labels)
    environment_mapped = bool(reference_aliases or scene_summary_present)
    expansion_ready = bool(comparison_axes or reference_aliases)
    reference_profile_present = bool(reference_labels or reference_aliases or comparison_axes)

    grounding_verdict = "grounded"
    if not reference_profile_present:
        grounding_verdict = "unmapped"
    elif not (asset_mapped and environment_mapped):
        grounding_verdict = "partial"

    summary = {
        "reference_profile_present": reference_profile_present,
        "reference_labels_present": bool(reference_labels),
        "reference_aliases_present": bool(reference_aliases),
        "comparison_axes_present": bool(comparison_axes),
        "reference_label_count": len(reference_labels),
        "reference_alias_count": len(reference_aliases),
        "comparison_axis_count": len(comparison_axes),
        "scene_summary_present": scene_summary_present,
        "asset_mapped": asset_mapped,
        "environment_mapped": environment_mapped,
        "expansion_ready": expansion_ready,
        "grounding_verdict": grounding_verdict,
        "reference_labels": reference_labels,
        "reference_aliases": reference_aliases,
        "comparison_axes": comparison_axes,
    }
    summary["summary_hash"] = _stable_hash(summary)
    return summary


def build_deterministic_validation_gate(
    record: Dict[str, Any],
    *,
    readiness_summary: Optional[Dict[str, Any]] = None,
    scene_validation: Optional[Dict[str, Any]] = None,
    constraints_report: Optional[Dict[str, Any]] = None,
    optional_reason_items: Any = None,
    engaged_switch_kinds: Any = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    readiness = readiness_summary if isinstance(readiness_summary, dict) else {}
    scene = scene_validation if isinstance(scene_validation, dict) else {}
    constraints = constraints_report if isinstance(constraints_report, dict) else {}

    schema_version = str(record.get("schema_version") or "").strip()
    request_validation_status = "schema_version_present" if schema_version else "missing_schema_version"
    request_validation_passed = bool(schema_version)

    scene_failed_checks = _unique_non_empty_strings(scene.get("failed_checks"))
    scene_validation_present = bool(scene)
    scene_validation_hard_failure = bool(scene.get("has_hard_failure"))
    schema_validation_passed = bool(
        scene_validation_present
        and not scene_failed_checks
        and not scene_validation_hard_failure
    )
    schema_validation_status = (
        "failed"
        if scene_validation_present and not schema_validation_passed
        else ("passed" if scene_validation_present else "not_available")
    )

    raw_constraint_violations = constraints.get("violations")
    normalized_constraint_violations: List[str] = []
    if isinstance(raw_constraint_violations, list):
        for item in raw_constraint_violations:
            if isinstance(item, dict):
                normalized_constraint_violations.extend(
                    _unique_non_empty_strings(
                        [
                            item.get("code"),
                            item.get("kind"),
                            item.get("reason"),
                            item.get("summary"),
                        ]
                    )
                )
            else:
                normalized_constraint_violations.extend(_unique_non_empty_strings([item]))
    constraint_review_present = bool(constraints)
    constraint_review_hard_violation = bool(constraints.get("has_hard_violation"))
    constraint_review_passed = bool(
        constraint_review_present
        and not normalized_constraint_violations
        and not constraint_review_hard_violation
    )
    constraint_review_status = (
        "failed"
        if constraint_review_present and not constraint_review_passed
        else ("passed" if constraint_review_present else "not_available")
    )

    rejection_reason_codes: List[str] = []
    if isinstance(optional_reason_items, list):
        rejection_reason_codes = _unique_non_empty_strings(
            [
                item.get("reason_code")
                for item in optional_reason_items
                if isinstance(item, dict)
            ]
        )
    normalized_switch_kinds = _unique_non_empty_strings(engaged_switch_kinds)
    deterministic_rejection = bool("reject" in normalized_switch_kinds)

    gate_blocks_live_composition = bool(
        deterministic_rejection
        or (scene_validation_present and not schema_validation_passed)
        or (constraint_review_present and not constraint_review_passed)
    )

    deterministic_rejection_verdict = "reject" if (deterministic_rejection or gate_blocks_live_composition) else "pass"

    summary = {
        "request_validation_status": request_validation_status,
        "request_validation_passed": request_validation_passed,
        "request_validation_surface": "record.schema_version",
        "readiness_status": str(readiness.get("status") or "not_ready"),
        "readiness_ready": bool(readiness.get("ready")),
        "schema_validation_present": scene_validation_present,
        "schema_validation_status": schema_validation_status,
        "schema_validation_passed": schema_validation_passed,
        "schema_validation_failed_checks": scene_failed_checks,
        "constraint_review_present": constraint_review_present,
        "constraint_review_status": constraint_review_status,
        "constraint_review_passed": constraint_review_passed,
        "constraint_review_violations": normalized_constraint_violations,
        "deterministic_rejection_verdict": deterministic_rejection_verdict,
        "deterministic_rejection_reasons": rejection_reason_codes,
        "engaged_switch_kinds": normalized_switch_kinds,
        "gate_blocks_live_composition": gate_blocks_live_composition,
        "validation_surface_present": bool(
            request_validation_passed
            or scene_validation_present
            or constraint_review_present
            or deterministic_rejection
        ),
    }
    summary["summary_hash"] = _stable_hash(summary)
    return summary


def _build_preparation_state(
    *,
    record: Dict[str, Any],
    target_space: str,
    policy_rule_id: str,
    decision_trace: Dict[str, Any],
    activity_digest: Dict[str, Any],
    categorized_summary: Dict[str, Any],
    comprehension_summary: Dict[str, Any],
    readiness_summary: Dict[str, Any],
    measurement_summary: Dict[str, Any],
    reference_grounding_verification: Dict[str, Any],
    deterministic_validation_gate: Dict[str, Any],
    proposed_actions: Dict[str, Any],
    engaged_switch_kinds: List[str],
) -> Dict[str, Any]:
    objective_link_ids = _unique_non_empty_strings(activity_digest.get("objective_link_ids"))
    current_activity_present = bool(activity_digest.get("current_activity_present"))
    comprehension_level = str(comprehension_summary.get("level") or "missing")
    categorized_level = str(
        categorized_summary.get("support_level")
        or categorized_summary.get("level")
        or "missing"
    )
    measurement_level = str(measurement_summary.get("level") or "missing")
    proposed_action_count = len(proposed_actions.get("recommended_actions") or []) if isinstance(proposed_actions.get("recommended_actions"), list) else len(proposed_actions)

    if target_space == "DiscardSpace":
        prioritization_level = "discard"
        scheduling_intent = "deterministic_reject"
    elif target_space == "HoldingSpace":
        prioritization_level = "scheduled"
        scheduling_intent = "hold_for_follow_through"
    elif target_space == "ActiveSpace":
        prioritization_level = "active_now"
        scheduling_intent = "route_active_space"
    elif current_activity_present or objective_link_ids:
        prioritization_level = "review_now"
        scheduling_intent = "bounded_review"
    else:
        prioritization_level = "preparatory"
        scheduling_intent = "queue_for_readiness"

    ready_for_live_simulation = bool(
        target_space == "ActiveSpace"
        and not deterministic_validation_gate.get("gate_blocks_live_composition")
        and str(reference_grounding_verification.get("grounding_verdict") or "unmapped") == "grounded"
    )

    queue_admission = "unassigned"
    if target_space == "ActiveSpace":
        queue_admission = "admitted"
    elif target_space == "HoldingSpace":
        queue_admission = "holding"
    elif target_space == "DiscardSpace":
        queue_admission = "discarded"
    elif target_space:
        queue_admission = "queued"

    active_space_packet = {
        "carrier_source": "active_space_support",
        "queue_admission": queue_admission,
        "packet_state": (
            "ready_for_live_simulation"
            if ready_for_live_simulation
            else ("bounded_preparatory" if queue_admission != "unassigned" else "unassigned")
        ),
        "queue_target_space": target_space,
        "packet_preparation_ready": bool(
            target_space
            or reference_grounding_verification.get("reference_profile_present")
            or deterministic_validation_gate.get("validation_surface_present")
        ),
        "ready_not_ready_handoff": bool(
            queue_admission in {"holding", "discarded"}
            or not ready_for_live_simulation
        ),
    }

    tier1_decision = {
        "decision_source": "tier1_main_cognition",
        "selection_ranking": {
            "objective_alignment": str(activity_digest.get("objective_alignment") or "unknown"),
            "objective_link_ids": objective_link_ids,
            "objective_link_count": len(objective_link_ids),
            "current_activity_present": current_activity_present,
            "current_activity_id": str(activity_digest.get("current_activity_id") or ""),
            "decision_trace_present": bool(decision_trace),
            "policy_rule_id": policy_rule_id,
            "comprehension_level": comprehension_level,
        },
        "prioritization_level": prioritization_level,
        "scheduling_intent": scheduling_intent,
    }

    preparation_state = {
        "asset_support": {
            "asset_mapped": bool(reference_grounding_verification.get("asset_mapped")),
            "environment_mapped": bool(reference_grounding_verification.get("environment_mapped")),
            "grounding_verdict": str(reference_grounding_verification.get("grounding_verdict") or "unmapped"),
        },
        "routing_candidate": {
            "target_space": target_space,
            "policy_rule_id": policy_rule_id,
            "proposed_action_count": proposed_action_count,
            "decision_trace_present": bool(decision_trace),
        },
        "validation_state": {
            "request_validation_status": str(deterministic_validation_gate.get("request_validation_status") or "missing"),
            "schema_validation_status": str(deterministic_validation_gate.get("schema_validation_status") or "not_available"),
            "constraint_review_status": str(deterministic_validation_gate.get("constraint_review_status") or "not_available"),
            "deterministic_rejection_verdict": str(
                deterministic_validation_gate.get("deterministic_rejection_verdict") or "review_required"
            ),
            "gate_blocks_live_composition": bool(deterministic_validation_gate.get("gate_blocks_live_composition")),
        },
        "reference_support": {
            "reference_profile_present": bool(reference_grounding_verification.get("reference_profile_present")),
            "reference_label_count": int(reference_grounding_verification.get("reference_label_count") or 0),
            "reference_alias_count": int(reference_grounding_verification.get("reference_alias_count") or 0),
            "comparison_axis_count": int(reference_grounding_verification.get("comparison_axis_count") or 0),
            "grounding_verdict": str(reference_grounding_verification.get("grounding_verdict") or "unmapped"),
        },
        "readiness_state": _surface_learning_readiness_state(readiness_summary),
        "persistence_needs": {
            "measurement_level": measurement_level,
            "categorized_context_level": categorized_level,
            "comprehension_level": comprehension_level,
            "requires_persistence": bool(
                measurement_level != "missing"
                or categorized_level != "missing"
                or comprehension_level != "missing"
            ),
        },
        "follow_through_needs": {
            "target_space": target_space,
            "engaged_switch_kinds": list(engaged_switch_kinds),
            "proposed_action_count": proposed_action_count,
            "requires_follow_through": bool(
                target_space in {"HoldingSpace", "DiscardSpace"}
                or engaged_switch_kinds
                or proposed_action_count
            ),
        },
        "ready_for_live_simulation": ready_for_live_simulation,
        "tier1_decision": tier1_decision,
        "active_space_packet": active_space_packet,
        "reference_grounding_verification": dict(reference_grounding_verification),
        "deterministic_validation_gate": dict(deterministic_validation_gate),
    }
    preparation_state["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in preparation_state.items()
            if key != "summary_hash"
        }
    )
    return preparation_state


def prepare_cycle_window(
    record: Dict[str, Any],
    *,
    target_space: str = "",
    justification: Optional[Dict[str, Any]] = None,
    foundational_hook_summary: Optional[Dict[str, Any]] = None,
    foundational_active_space_summary: Optional[Dict[str, Any]] = None,
    foundational_optional_reference_artifact: Optional[Dict[str, Any]] = None,
    bounded_runtime_switch_inventory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    decision_trace = relational_state.get("decision_trace") if isinstance(relational_state.get("decision_trace"), dict) else {}
    if not decision_trace:
        fallback_trace = record.get("decision_trace")
        decision_trace = fallback_trace if isinstance(fallback_trace, dict) else {}

    categorized_summary = (
        derived.get("categorized_context_summary")
        if isinstance(derived.get("categorized_context_summary"), dict)
        else _build_categorized_context_join_summary(record)
    )
    comprehension_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else _build_comprehension_review_summary(record)
    )
    reference_profile = _reference_profile_from_record_or_derived(record, derived)
    measurement_summary = (
        derived.get("measurement_adequacy_summary")
        if isinstance(derived.get("measurement_adequacy_summary"), dict)
        else {}
    )
    readiness_summary = _build_learning_readiness_verdict_for_record(
        record,
        measurement_summary=measurement_summary,
    )
    runtime_measurement_readiness_summary = (
        derived.get("runtime_measurement_readiness_summary")
        if isinstance(derived.get("runtime_measurement_readiness_summary"), dict)
        else {}
    )
    runtime_measurement_commitment_summary = (
        derived.get("runtime_measurement_commitment_summary")
        if isinstance(derived.get("runtime_measurement_commitment_summary"), dict)
        else {}
    )
    runtime_measurement_provenance_chain = (
        derived.get("runtime_measurement_provenance_chain")
        if isinstance(derived.get("runtime_measurement_provenance_chain"), dict)
        else {}
    )
    spatial_measurement_schema_version = str(derived.get("spatial_measurement_schema_version") or "").strip()
    spatial_measurement_schema_version = str(derived.get("spatial_measurement_schema_version") or "").strip()
    scene_validation = (
        decision_trace.get("scene_validation")
        if isinstance(decision_trace.get("scene_validation"), dict)
        else {}
    )
    constraints_report = (
        decision_trace.get("constraints")
        if isinstance(decision_trace.get("constraints"), dict)
        else (
            decision_trace.get("constraints_report")
            if isinstance(decision_trace.get("constraints_report"), dict)
            else {}
        )
    )
    proposed_actions = (
        decision_trace.get("proposed_actions")
        if isinstance(decision_trace.get("proposed_actions"), dict)
        else {}
    )
    normalized_target_space = str(target_space or record.get("target_space") or "").strip()
    policy_rule_id = str((justification or {}).get("policy_rule_id") or "").strip()
    activity_digest = _build_foundational_activity_digest(record)
    engaged_switch_kinds = _unique_non_empty_strings(
        (bounded_runtime_switch_inventory or {}).get("engaged_switch_kinds")
    )
    optional_reason_items = (
        foundational_optional_reference_artifact.get("reason_items")
        if isinstance(foundational_optional_reference_artifact, dict)
        and isinstance(foundational_optional_reference_artifact.get("reason_items"), list)
        else []
    )

    reference_grounding_verification = build_reference_grounding_verification(
        reference_profile=reference_profile,
        categorized_summary=categorized_summary,
    )
    comprehension_quality_summary = build_comprehension_quality_summary(comprehension_summary)
    deterministic_validation_gate = build_deterministic_validation_gate(
        record,
        readiness_summary=readiness_summary,
        scene_validation=scene_validation,
        constraints_report=constraints_report,
        optional_reason_items=optional_reason_items,
        engaged_switch_kinds=engaged_switch_kinds,
    )
    retained_memory_follow_through_summary = _merge_retained_memory_follow_through_summary(
        derived.get("retained_memory_follow_through_summary")
        if isinstance(derived.get("retained_memory_follow_through_summary"), dict)
        else None,
        build_retained_memory_follow_through_summary(
            record,
            categorized_summary=categorized_summary,
            comprehension_summary=comprehension_summary,
            readiness_summary=readiness_summary,
            bounded_runtime_switch_inventory=bounded_runtime_switch_inventory,
            deterministic_validation_gate=deterministic_validation_gate,
        ),
    )
    measurement_evidence_summary = build_measurement_evidence_summary(
        measurement_summary=measurement_summary,
        categorized_summary=categorized_summary,
        runtime_measurement_readiness_summary=runtime_measurement_readiness_summary,
        runtime_measurement_provenance_chain=runtime_measurement_provenance_chain,
    )
    measurement_schema_trace_summary = build_measurement_schema_trace_summary(
        schema_version=spatial_measurement_schema_version,
        categorized_summary=categorized_summary,
        runtime_measurement_readiness_summary=runtime_measurement_readiness_summary,
        runtime_measurement_commitment_summary=runtime_measurement_commitment_summary,
        runtime_measurement_provenance_chain=runtime_measurement_provenance_chain,
    )
    validation_retention_evidence_summary = build_validation_retention_evidence_summary(
        comprehension_summary=comprehension_summary,
        deterministic_validation_gate=deterministic_validation_gate,
        retained_memory_follow_through_summary=retained_memory_follow_through_summary,
    )
    return _build_preparation_state(
        record=record,
        target_space=normalized_target_space,
        policy_rule_id=policy_rule_id,
        decision_trace=decision_trace,
        activity_digest=activity_digest,
        categorized_summary=categorized_summary,
        comprehension_summary=comprehension_summary,
        readiness_summary=readiness_summary,
        measurement_summary=measurement_summary,
        reference_grounding_verification=reference_grounding_verification,
        deterministic_validation_gate=deterministic_validation_gate,
        proposed_actions=proposed_actions,
        engaged_switch_kinds=engaged_switch_kinds,
    )


def build_purpose_carrier_summary(
    record: Dict[str, Any],
    *,
    target_space: str = "",
    justification: Optional[Dict[str, Any]] = None,
    mirror_summary: Optional[Dict[str, Any]] = None,
    foundational_hook_summary: Optional[Dict[str, Any]] = None,
    foundational_active_space_summary: Optional[Dict[str, Any]] = None,
    foundational_optional_reference_artifact: Optional[Dict[str, Any]] = None,
    bounded_runtime_switch_inventory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}
    decision_trace = relational_state.get("decision_trace") if isinstance(relational_state.get("decision_trace"), dict) else {}
    if not decision_trace:
        fallback_trace = record.get("decision_trace")
        decision_trace = fallback_trace if isinstance(fallback_trace, dict) else {}

    categorized_summary = (
        derived.get("categorized_context_summary")
        if isinstance(derived.get("categorized_context_summary"), dict)
        else _build_categorized_context_join_summary(record)
    )
    comprehension_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else _build_comprehension_review_summary(record)
    )
    reference_profile = _reference_profile_from_record_or_derived(record, derived)
    measurement_summary = (
        derived.get("measurement_adequacy_summary")
        if isinstance(derived.get("measurement_adequacy_summary"), dict)
        else {}
    )
    readiness_summary = _build_learning_readiness_verdict_for_record(
        record,
        measurement_summary=measurement_summary,
    )
    runtime_measurement_readiness_summary = (
        derived.get("runtime_measurement_readiness_summary")
        if isinstance(derived.get("runtime_measurement_readiness_summary"), dict)
        else {}
    )
    runtime_measurement_commitment_summary = (
        derived.get("runtime_measurement_commitment_summary")
        if isinstance(derived.get("runtime_measurement_commitment_summary"), dict)
        else {}
    )
    runtime_measurement_provenance_chain = (
        derived.get("runtime_measurement_provenance_chain")
        if isinstance(derived.get("runtime_measurement_provenance_chain"), dict)
        else {}
    )
    spatial_measurement_schema_version = str(derived.get("spatial_measurement_schema_version") or "").strip()
    scene_validation = (
        decision_trace.get("scene_validation")
        if isinstance(decision_trace.get("scene_validation"), dict)
        else {}
    )
    constraints_report = (
        decision_trace.get("constraints")
        if isinstance(decision_trace.get("constraints"), dict)
        else (
            decision_trace.get("constraints_report")
            if isinstance(decision_trace.get("constraints_report"), dict)
            else {}
        )
    )
    proposed_actions = (
        decision_trace.get("proposed_actions")
        if isinstance(decision_trace.get("proposed_actions"), dict)
        else {}
    )
    normalized_target_space = str(target_space or record.get("target_space") or "").strip()
    policy_rule_id = str((justification or {}).get("policy_rule_id") or "").strip()
    activity_digest = _build_foundational_activity_digest(record)
    trigger_digest = _build_foundational_trigger_digest(record)
    scene_summary_present = bool(categorized_summary.get("scene_summary_present")) or bool(scene_validation)
    comparison_axes = _unique_non_empty_strings(reference_profile.get("comparison_axes"))
    reference_labels = _unique_non_empty_strings(reference_profile.get("labels"))
    reference_aliases = _unique_non_empty_strings(reference_profile.get("aliases"))
    relation_families = _unique_non_empty_strings(categorized_summary.get("relation_families"))
    bridge_sources = _unique_non_empty_strings(categorized_summary.get("bridge_sources"))
    engaged_switch_kinds = _unique_non_empty_strings(
        (bounded_runtime_switch_inventory or {}).get("engaged_switch_kinds")
    )
    foundational_support_sources = _unique_non_empty_strings(
        (foundational_active_space_summary or {}).get("support_sources")
    )
    optional_reason_items = (
        foundational_optional_reference_artifact.get("reason_items")
        if isinstance(foundational_optional_reference_artifact, dict)
        and isinstance(foundational_optional_reference_artifact.get("reason_items"), list)
        else []
    )
    objective_link_ids = _unique_non_empty_strings(activity_digest.get("objective_link_ids"))
    current_activity_present = bool(activity_digest.get("current_activity_present"))
    comprehension_level = str(comprehension_summary.get("level") or "missing")
    categorized_level = str(
        categorized_summary.get("support_level")
        or categorized_summary.get("level")
        or "missing"
    )
    readiness_status = str(readiness_summary.get("status") or "not_ready")
    reference_grounding_verification = build_reference_grounding_verification(
        reference_profile=reference_profile,
        categorized_summary=categorized_summary,
    )
    comprehension_quality_summary = build_comprehension_quality_summary(comprehension_summary)
    deterministic_validation_gate = build_deterministic_validation_gate(
        record,
        readiness_summary=readiness_summary,
        scene_validation=scene_validation,
        constraints_report=constraints_report,
        optional_reason_items=optional_reason_items,
        engaged_switch_kinds=engaged_switch_kinds,
    )
    retained_memory_follow_through_summary = _merge_retained_memory_follow_through_summary(
        derived.get("retained_memory_follow_through_summary")
        if isinstance(derived.get("retained_memory_follow_through_summary"), dict)
        else None,
        build_retained_memory_follow_through_summary(
            record,
            categorized_summary=categorized_summary,
            comprehension_summary=comprehension_summary,
            readiness_summary=readiness_summary,
            bounded_runtime_switch_inventory=bounded_runtime_switch_inventory,
            deterministic_validation_gate=deterministic_validation_gate,
        ),
    )
    measurement_evidence_summary = build_measurement_evidence_summary(
        measurement_summary=measurement_summary,
        categorized_summary=categorized_summary,
        runtime_measurement_readiness_summary=runtime_measurement_readiness_summary,
        runtime_measurement_provenance_chain=runtime_measurement_provenance_chain,
    )
    measurement_schema_trace_summary = build_measurement_schema_trace_summary(
        schema_version=spatial_measurement_schema_version,
        categorized_summary=categorized_summary,
        runtime_measurement_readiness_summary=runtime_measurement_readiness_summary,
        runtime_measurement_commitment_summary=runtime_measurement_commitment_summary,
        runtime_measurement_provenance_chain=runtime_measurement_provenance_chain,
    )
    validation_retention_evidence_summary = build_validation_retention_evidence_summary(
        comprehension_summary=comprehension_summary,
        deterministic_validation_gate=deterministic_validation_gate,
        retained_memory_follow_through_summary=retained_memory_follow_through_summary,
    )
    preparation_state = _build_preparation_state(
        record=record,
        target_space=normalized_target_space,
        policy_rule_id=policy_rule_id,
        decision_trace=decision_trace,
        activity_digest=activity_digest,
        categorized_summary=categorized_summary,
        comprehension_summary=comprehension_summary,
        readiness_summary=readiness_summary,
        measurement_summary=measurement_summary,
        reference_grounding_verification=reference_grounding_verification,
        deterministic_validation_gate=deterministic_validation_gate,
        proposed_actions=proposed_actions,
        engaged_switch_kinds=engaged_switch_kinds,
    )
    tier1_decision = (
        preparation_state.get("tier1_decision")
        if isinstance(preparation_state.get("tier1_decision"), dict)
        else {}
    )
    active_space_packet = (
        preparation_state.get("active_space_packet")
        if isinstance(preparation_state.get("active_space_packet"), dict)
        else {}
    )

    carrier_rows = [
        _build_purpose_carrier_row(
            carrier_id="tier1_main_cognition",
            carrier_kind="support_group",
            engaged=bool(
                objective_link_ids
                or current_activity_present
                or normalized_target_space
                or policy_rule_id
                or decision_trace
                or comprehension_level != "missing"
            ),
            action_ids=[
                "bounded_objective_selection" if objective_link_ids else "",
                "current_activity_prioritization" if current_activity_present else "",
                "decision_selection" if decision_trace or policy_rule_id else "",
                "scheduling_intent" if normalized_target_space or proposed_actions else "",
                "relational_summary_review" if comprehension_level != "missing" else "",
            ],
            evidence_refs=objective_link_ids + [policy_rule_id, normalized_target_space],
            functionality_labels=[
                "primary_ai_brain_cognition",
                "scheduling",
                "decision_coordination",
                "workload_selection",
            ],
            reason_summary="top-tier cognition carries selection, decision, and scheduling intent for the current record",
            carrier_context=tier1_decision,
        ),
        _build_purpose_carrier_row(
            carrier_id="active_space_support",
            carrier_kind="support_group",
            engaged=bool(
                normalized_target_space
                or foundational_hook_summary
                or foundational_active_space_summary
                or scene_summary_present
                or engaged_switch_kinds
            ),
            action_ids=[
                "queue_admission" if active_space_packet.get("queue_admission") == "admitted" else "",
                "context_execution_support" if scene_summary_present else "",
                "simultaneous_context_carrier_support" if foundational_active_space_summary or foundational_hook_summary else "",
                "packet_preparation_support" if active_space_packet.get("packet_preparation_ready") else "",
                "ready_not_ready_handoff" if active_space_packet.get("ready_not_ready_handoff") or engaged_switch_kinds else "",
            ],
            evidence_refs=[normalized_target_space] + foundational_support_sources + engaged_switch_kinds,
            functionality_labels=[
                "active_space_support",
                "simultaneous_context_carrier",
                "context_execution_support",
            ],
            reason_summary="active-space support carries admission, packet preparation, and scene-side handoff for the current record",
            carrier_context=active_space_packet,
        ),
        _build_purpose_carrier_row(
            carrier_id="reference_grounding_support",
            carrier_kind="support_group",
            engaged=bool(reference_grounding_verification.get("reference_profile_present")),
            action_ids=[
                "reference_grounding" if reference_grounding_verification.get("reference_labels_present") else "",
                "asset_environment_grounding" if reference_grounding_verification.get("asset_mapped") or reference_grounding_verification.get("environment_mapped") else "",
                "reference_expansion_support" if reference_grounding_verification.get("expansion_ready") else "",
            ],
            evidence_refs=reference_labels + reference_aliases + comparison_axes,
            functionality_labels=[
                "reference_grounding",
                "asset_environment_grounding",
                "descriptor_alignment",
            ],
            reason_summary="reference grounding carries mapped labels, aliases, and comparison axes for the current record",
            carrier_context=reference_grounding_verification,
        ),
        _build_purpose_carrier_row(
            carrier_id="retained_memory_support",
            carrier_kind="support_group",
            engaged=bool(
                categorized_level != "missing"
                or comprehension_level != "missing"
                or normalized_target_space
                or engaged_switch_kinds
                or mirror_summary
            ),
            action_ids=[
                "persist_measurement_and_context" if categorized_level != "missing" else "",
                "retained_storage_remembering" if comprehension_level != "missing" or measurement_summary else "",
                "storage_follow_through" if normalized_target_space or engaged_switch_kinds else "",
                "later_retrieval_support" if reference_labels or comparison_axes or comprehension_level != "missing" else "",
                "relational_attachment_retention" if retained_memory_follow_through_summary.get("relational_attachment_summary", {}).get("attachment_ready") else "",
                "comprehension_quality_review" if comprehension_quality_summary.get("present") else "",
                "validation_retention_review" if validation_retention_evidence_summary.get("present") else "",
                "telemetry_retention" if retained_memory_follow_through_summary.get("telemetry_retention_summary", {}).get("telemetry_retained") else "",
                "learning_gate_review" if retained_memory_follow_through_summary.get("learning_gate_summary") else "",
                "follow_through_scheduling" if retained_memory_follow_through_summary.get("follow_through_summary", {}).get("scheduled") else "",
            ],
            evidence_refs=[normalized_target_space] + engaged_switch_kinds + reference_labels,
            functionality_labels=[
                "retained_memory_support",
                "persistence",
                "evidence_retention",
            ],
            reason_summary="retained-memory support carries persisted evidence, retention, and later follow-through for the current record",
            carrier_context=retained_memory_follow_through_summary,
        ),
        _build_purpose_carrier_row(
            carrier_id="correctness_constraint_verification_support",
            carrier_kind="support_group",
            engaged=bool(deterministic_validation_gate.get("validation_surface_present")),
            action_ids=[
                "request_validation" if deterministic_validation_gate.get("request_validation_passed") else "",
                "constraint_review" if deterministic_validation_gate.get("constraint_review_present") else "",
                "schema_review" if deterministic_validation_gate.get("schema_validation_present") else "",
                "deterministic_rejection" if deterministic_validation_gate.get("deterministic_rejection_verdict") == "reject" else "",
            ],
            evidence_refs=engaged_switch_kinds
            + _unique_non_empty_strings((scene_validation.get("failed_checks") if isinstance(scene_validation.get("failed_checks"), list) else [])),
            functionality_labels=[
                "correctness_verification",
                "constraint_review",
                "schema_validation",
            ],
            reason_summary="correctness support carries validation and deterministic rejection evidence for the current record",
            carrier_context=deterministic_validation_gate,
        ),
        _build_purpose_carrier_row(
            carrier_id="spatial_context_relation_support",
            carrier_kind="support_group",
            engaged=bool(
                scene_summary_present
                or relation_families
                or bridge_sources
                or measurement_summary
                or runtime_measurement_readiness_summary
                or runtime_measurement_commitment_summary
            ),
                action_ids=[
                    "scene_measurement_support" if scene_summary_present or measurement_summary else "",
                    "spatial_relation_derivation" if relation_families else "",
                    "relational_context_attachment" if bridge_sources or comprehension_level != "missing" else "",
                    "measurement_evidence_review" if measurement_evidence_summary.get("present") else "",
                    "schema_trace_review" if measurement_schema_trace_summary.get("present") else "",
                    "direct_3d_measurement_commit" if normalized_target_space == "ActiveSpace" and (scene_summary_present or measurement_summary) else "",
                    "routed_execution_readiness" if runtime_measurement_readiness_summary else "",
                    "measurement_provenance_chain" if runtime_measurement_provenance_chain.get("status") == "present" else "",
                ],
                evidence_refs=relation_families
            + bridge_sources
            + _unique_non_empty_strings(
                [
                    runtime_measurement_commitment_summary.get("request_id"),
                    runtime_measurement_commitment_summary.get("commitment_hash"),
                ]
            ),
            functionality_labels=[
                "spatial_context_relation_support",
                "measurement_support",
                "relational_attachment",
            ],
            reason_summary="spatial-context relation support carries scene measurement and relational attachment for the current record",
                carrier_context={
                    key: value
                    for key, value in {
                        "measurement_evidence_summary": measurement_evidence_summary,
                        "measurement_schema_trace_summary": measurement_schema_trace_summary,
                        "runtime_measurement_readiness_summary": runtime_measurement_readiness_summary,
                        "runtime_measurement_commitment_summary": runtime_measurement_commitment_summary,
                        "runtime_measurement_provenance_chain": runtime_measurement_provenance_chain,
                    }.items()
                    if isinstance(value, dict) and value
            },
        ),
        _build_purpose_carrier_row(
            carrier_id="schedule_mirror",
            carrier_kind="tier_family",
            engaged=bool(mirror_summary),
            action_ids=[
                "schedule_mirroring" if mirror_summary else "",
                "reporting_only_schedule_review" if mirror_summary else "",
            ],
            evidence_refs=_unique_non_empty_strings(
                [
                    (mirror_summary or {}).get("mirror_schedule_summary_hash"),
                    (derived.get("mirror_schedule_delta_hash") if isinstance(derived.get("mirror_schedule_delta_hash"), str) else ""),
                ]
            ),
            functionality_labels=[
                "schedule_mirroring",
                "delta_review",
                "checksum_verification",
            ],
            authoritative=False,
            current_serving=False,
            reporting_only=True,
            reason_summary="schedule_mirror remains a reporting-only carrier for the current record",
        ),
        _build_purpose_carrier_row(
            carrier_id="simultaneous_context_match",
            carrier_kind="tier_family",
            engaged=bool(
                foundational_hook_summary
                or foundational_active_space_summary
                or foundational_optional_reference_artifact
            ),
            action_ids=[
                "simultaneous_context_comparison" if foundational_active_space_summary or foundational_hook_summary else "",
                "optional_reference_shadow_review" if foundational_optional_reference_artifact else "",
                "bounded_rehearsal" if foundational_hook_summary else "",
            ],
            evidence_refs=foundational_support_sources
            + _unique_non_empty_strings(
                [
                    (foundational_hook_summary or {}).get("artifact_bundle_ref"),
                    (foundational_active_space_summary or {}).get("summary_hash"),
                    (foundational_optional_reference_artifact or {}).get("artifact_hash"),
                ]
            ),
            functionality_labels=[
                "simultaneous_context_comparison",
                "shadow_validation",
                "optional_reference_review",
            ],
            authoritative=False,
            current_serving=False,
            review_only=True,
            reason_summary="simultaneous_context_match remains a non-authoritative review carrier for the current record",
        ),
    ]
    engaged_rows = [row for row in carrier_rows if bool(row.get("engaged"))]
    engaged_carrier_ids = [str(row.get("carrier_id") or "") for row in engaged_rows if str(row.get("carrier_id") or "")]
    engaged_action_ids = _unique_non_empty_strings(
        [action_id for row in engaged_rows for action_id in (row.get("action_ids") or [])]
    )
    operator_explanation_summary = build_operator_explanation_summary(
        preparation_state=preparation_state,
        carrier_rows=carrier_rows,
        comprehension_quality_summary=comprehension_quality_summary,
        validation_retention_evidence_summary=validation_retention_evidence_summary,
        measurement_evidence_summary=measurement_evidence_summary,
        measurement_schema_trace_summary=measurement_schema_trace_summary,
    )
    summary = {
        "status": "present" if engaged_rows else "unavailable",
        "record_scope": "current_record",
        "target_space": normalized_target_space,
        "objective_alignment": str(activity_digest.get("objective_alignment") or "unknown"),
        "query_state": str(trigger_digest.get("query_state") or "auto_considered"),
        "configured_carrier_ids": [str(row.get("carrier_id") or "") for row in carrier_rows if str(row.get("carrier_id") or "")],
        "engaged_carrier_ids": engaged_carrier_ids,
        "engaged_carrier_count": len(engaged_carrier_ids),
        "engaged_action_ids": engaged_action_ids,
        "engaged_action_count": len(engaged_action_ids),
        "bounded_switch_kinds": engaged_switch_kinds,
        "preparation_state": preparation_state,
        "tier1_decision": tier1_decision,
        "active_space_packet": active_space_packet,
        "reference_grounding_verification": reference_grounding_verification,
        "deterministic_validation_gate": deterministic_validation_gate,
        "comprehension_quality_summary": comprehension_quality_summary,
        "measurement_evidence_summary": measurement_evidence_summary,
        "measurement_schema_trace_summary": measurement_schema_trace_summary,
        "validation_retention_evidence_summary": validation_retention_evidence_summary,
        "operator_explanation_summary": operator_explanation_summary,
        "retained_memory_follow_through_summary": retained_memory_follow_through_summary,
        "capability_measurement_summary": (
            dict(retained_memory_follow_through_summary.get("capability_measurement_summary"))
            if isinstance(retained_memory_follow_through_summary.get("capability_measurement_summary"), dict)
            else {}
        ),
        "runtime_measurement_readiness_summary": runtime_measurement_readiness_summary,
        "runtime_measurement_commitment_summary": runtime_measurement_commitment_summary,
        "runtime_measurement_provenance_chain": runtime_measurement_provenance_chain,
        "carrier_rows": carrier_rows,
    }
    summary["summary_hash"] = _stable_hash(
        {
            key: value
            for key, value in summary.items()
            if key != "summary_hash"
        }
    )
    return summary


def _build_foundational_activity_digest(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    current_activity = record.get("current_activity") if isinstance(record.get("current_activity"), dict) else {}
    if not current_activity:
        current_activity = (
            relational_state.get("current_activity")
            if isinstance(relational_state.get("current_activity"), dict)
            else {}
        )

    objective_links = record.get("objective_links")
    if not isinstance(objective_links, (dict, list)):
        objective_links = (
            relational_state.get("objective_links")
            if isinstance(relational_state.get("objective_links"), (dict, list))
            else {}
        )

    objective_link_ids: List[str] = []
    if isinstance(objective_links, dict):
        objective_link_ids = sorted(str(key) for key in objective_links.keys())
    elif isinstance(objective_links, list):
        seen: set[str] = set()
        for item in objective_links:
            candidate = None
            if isinstance(item, dict):
                candidate = item.get("objective_id") or item.get("id") or item.get("name")
            elif isinstance(item, (str, int, float)):
                candidate = item
            if candidate is None:
                continue
            candidate_text = str(candidate)
            if candidate_text and candidate_text not in seen:
                seen.add(candidate_text)
                objective_link_ids.append(candidate_text)

    objective_alignment = record.get("objective_alignment")
    if not isinstance(objective_alignment, str) or not objective_alignment:
        policy_snapshot = record.get("policy_snapshot") if isinstance(record.get("policy_snapshot"), dict) else {}
        objective_alignment = policy_snapshot.get("objective_alignment")
    if not isinstance(objective_alignment, str) or not objective_alignment:
        decision_trace = record.get("decision_trace") if isinstance(record.get("decision_trace"), dict) else {}
        policy_snapshot = decision_trace.get("policy_snapshot") if isinstance(decision_trace.get("policy_snapshot"), dict) else {}
        objective_alignment = policy_snapshot.get("objective_alignment")
    if not isinstance(objective_alignment, str) or not objective_alignment:
        objective_alignment = "unknown"

    activity_id = current_activity.get("activity_id") or current_activity.get("id")
    activity_label = (
        current_activity.get("description")
        or current_activity.get("summary")
        or current_activity.get("label")
    )

    return {
        "objective_alignment": str(objective_alignment or "unknown"),
        "objective_link_count": len(objective_link_ids),
        "objective_link_ids": objective_link_ids[:3],
        "current_activity_present": bool(activity_id or activity_label),
        "current_activity_id": str(activity_id or ""),
        "current_activity_label": str(activity_label or "")[:96],
    }


def _build_foundational_trigger_digest(
    record: Dict[str, Any],
    *,
    query_state: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        record = {}

    relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = relational_state.get("derived") if isinstance(relational_state.get("derived"), dict) else {}

    explicit_query = record.get("simultaneous_context_match_query")
    if explicit_query in (None, "", [], {}):
        explicit_query = record.get("explicit_query")
    if explicit_query in (None, "", [], {}):
        explicit_query = record.get("query_signal")
    if explicit_query in (None, "", [], {}):
        explicit_query = derived.get("simultaneous_context_match_query")

    objective_links = record.get("objective_links")
    if not isinstance(objective_links, (dict, list)):
        objective_links = relational_state.get("objective_links") if isinstance(relational_state.get("objective_links"), (dict, list)) else {}

    objective_link_count = 0
    if isinstance(objective_links, dict):
        objective_link_count = len(objective_links)
    elif isinstance(objective_links, list):
        objective_link_count = len(objective_links)

    normalized_query_state = str(query_state or record.get("query_state") or "auto_considered")
    explicit_query_present = explicit_query not in (None, "", [], {})
    objective_linked = objective_link_count > 0

    trigger_mode = "passive_auto"
    if explicit_query_present or normalized_query_state in {"explicit_query", "explicit_queried", "queried"}:
        trigger_mode = "explicit_query"
    elif objective_linked:
        trigger_mode = "objective_linked_auto"

    trigger_signals: List[str] = []
    if explicit_query_present:
        trigger_signals.append("explicit_query")
    if objective_linked:
        trigger_signals.append("objective_links")
    if normalized_query_state == "auto_considered" and not trigger_signals:
        trigger_signals.append("passive_auto_review")

    return {
        "query_state": normalized_query_state,
        "trigger_mode": trigger_mode,
        "explicit_query_present": explicit_query_present,
        "objective_linked": objective_linked,
        "trigger_signals": trigger_signals,
    }


def build_foundational_active_space_consumption_invariance_guard(
    family_id: str,
    *,
    consumption_summary_present: Optional[Dict[str, Any]] = None,
    consumption_summary_absent: Optional[Dict[str, Any]] = None,
    tier1_snapshot_present: Optional[Dict[str, Any]] = None,
    tier1_snapshot_absent: Optional[Dict[str, Any]] = None,
    scheduler_authority_present: Optional[Dict[str, Any]] = None,
    scheduler_authority_absent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary_present = dict(consumption_summary_present or {})
    summary_absent = dict(consumption_summary_absent or {})
    tier1_present = dict(tier1_snapshot_present or {})
    tier1_absent = dict(tier1_snapshot_absent or {})
    scheduler_present = dict(scheduler_authority_present or {})
    scheduler_absent = dict(scheduler_authority_absent or {})
    rollback_mode = str(summary_present.get("rollback_mode") or "remove_foundational_support_summary_only")

    return {
        "family_id": str(family_id),
        "guard_case": "simultaneous_context_match_active_space_consumption_invariance_guard",
        "consumption_hook_present": bool(summary_present),
        "consumption_hook_absent": bool(summary_absent),
        "consumption_summary_present_hash": _stable_hash(summary_present),
        "consumption_summary_absent_hash": _stable_hash(summary_absent),
        "tier1_decisions_identical": tier1_present == tier1_absent,
        "tier1_snapshot_present_hash": _stable_hash(tier1_present),
        "tier1_snapshot_absent_hash": _stable_hash(tier1_absent),
        "scheduler_authority_identical": scheduler_present == scheduler_absent,
        "scheduler_authority_present_hash": _stable_hash(scheduler_present),
        "scheduler_authority_absent_hash": _stable_hash(scheduler_absent),
        "bounded_integration_evidence_only": (
            summary_present.get("authoritative") is False and summary_present.get("current_serving") is False
        ),
        "rollback_removes_only_integration_evidence": (
            bool(summary_present)
            and not bool(summary_absent)
            and rollback_mode == "remove_foundational_support_summary_only"
        ),
        "rollback_mode": rollback_mode,
        "active_space_entry_points": list(summary_present.get("active_space_entry_points") or []),
        "invariance_expectations": [
            "active_space_consumption_stays_non_authoritative",
            "tier1_decisions_unchanged",
            "scheduler_authority_unchanged",
            "rollback_removes_only_integration_evidence",
        ],
    }


def _build_comprehension_review_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "present": False,
            "level": "missing",
            "summary": "comprehension review evidence missing",
            "supporting_evidence": {
                "description_entity_count": 0,
                "description_claim_count": 0,
                "question_count": 0,
                "proposed_action_count": 0,
                "contradiction_count": 0,
                "has_hard_constraint_violation": False,
                "scene_validation_present": False,
                "categorized_context_support": "missing",
                "validation_evidence": {
                    "scene_validation_failed": 0,
                    "scene_validation_hard_failure": False,
                },
                "measurement_evidence": {
                    "level": "missing",
                    "reason": "",
                    "measurement_recorded": False,
                },
                "categorized_context_evidence": {
                    "support_level": "missing",
                    "join_status": "missing",
                    "label_count": 0,
                    "alias_count": 0,
                    "comparison_axis_count": 0,
                    "relation_family_count": 0,
                    "bridge_source_count": 0,
                },
                "retention_evidence": {
                    "record_id_present": False,
                    "categorized_context_persisted": False,
                    "comprehension_review_persisted": False,
                },
            },
            "observed_levels": {
                "measurement_adequacy": "missing",
                "categorized_context": "missing",
                "validation_evidence": "missing",
            },
            "rationale": [],
            "unresolved_gaps": ["description_support_sparse", "no_review_actions"],
        }

    rs = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    desc = rs.get("description") if isinstance(rs.get("description"), dict) else {}
    dt = rs.get("decision_trace") if isinstance(rs.get("decision_trace"), dict) else {}
    derived = rs.get("derived") if isinstance(rs.get("derived"), dict) else {}

    desc_entities = desc.get("entities") if isinstance(desc.get("entities"), list) else []
    desc_claims = desc.get("claims") if isinstance(desc.get("claims"), list) else []
    desc_questions = desc.get("questions") if isinstance(desc.get("questions"), list) else []

    proposed_actions = dt.get("proposed_actions") if isinstance(dt.get("proposed_actions"), dict) else {}
    recommended_actions = (
        proposed_actions.get("recommended_actions") if isinstance(proposed_actions.get("recommended_actions"), list) else []
    )

    contradictions = dt.get("contradictions") if isinstance(dt.get("contradictions"), dict) else {}
    contradiction_rows = contradictions.get("contradictions") if isinstance(contradictions.get("contradictions"), list) else []
    contradiction_count = len([row for row in contradiction_rows if isinstance(row, dict)])

    constraints_report = dt.get("constraints") if isinstance(dt.get("constraints"), dict) else {}
    has_hard_constraint_violation = bool(constraints_report.get("has_hard_violation"))
    constraint_violation_count = len(
        [row for row in (constraints_report.get("violations") or []) if isinstance(row, dict)]
    )

    scene_validation = dt.get("scene_validation") if isinstance(dt.get("scene_validation"), dict) else {}
    scene_validation_present = bool(scene_validation.get("present"))
    scene_validation_failed = int(scene_validation.get("failed") or 0)
    scene_validation_hard_failure = bool(scene_validation.get("has_hard_failure"))

    categorized_context = (
        derived.get("categorized_context_summary") if isinstance(derived.get("categorized_context_summary"), dict) else {}
    )
    persisted_comprehension_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else {}
    )
    measurement_summary = (
        derived.get("measurement_adequacy_summary")
        if isinstance(derived.get("measurement_adequacy_summary"), dict)
        else (
            record.get("measurement_adequacy")
            if isinstance(record.get("measurement_adequacy"), dict)
            else {}
        )
    )
    runtime_measurement_readiness_summary = (
        derived.get("runtime_measurement_readiness_summary")
        if isinstance(derived.get("runtime_measurement_readiness_summary"), dict)
        else {}
    )
    runtime_measurement_provenance_chain = (
        derived.get("runtime_measurement_provenance_chain")
        if isinstance(derived.get("runtime_measurement_provenance_chain"), dict)
        else {}
    )
    measurement_evidence = build_measurement_evidence_summary(
        measurement_summary=measurement_summary,
        categorized_summary=categorized_context,
        runtime_measurement_readiness_summary=runtime_measurement_readiness_summary,
        runtime_measurement_provenance_chain=runtime_measurement_provenance_chain,
    )
    record_id_present = bool(
        (isinstance(record.get("id"), str) and str(record.get("id")).strip())
        or (isinstance(record.get("record_id"), str) and str(record.get("record_id")).strip())
    )
    categorized_context_support = str(categorized_context.get("support_level") or "missing")

    rationale: List[str] = []
    if desc_entities or desc_claims:
        rationale.append("description_evidence_present")
    if desc_questions:
        rationale.append("review_questions_present")
    if recommended_actions:
        rationale.append("review_actions_present")
    if categorized_context_support == "strong":
        rationale.append("categorized_context_strong")
    elif categorized_context_support == "weak":
        rationale.append("categorized_context_partial")
    if scene_validation_present and not scene_validation_hard_failure and scene_validation_failed <= 0:
        rationale.append("scene_validation_clear")

    unresolved_gaps: List[str] = []
    if not (desc_entities or desc_claims):
        unresolved_gaps.append("description_support_sparse")
    if not recommended_actions:
        unresolved_gaps.append("no_review_actions")
    if categorized_context_support == "missing":
        unresolved_gaps.append("categorized_context_missing")
    elif categorized_context_support == "weak":
        unresolved_gaps.append("categorized_context_partial")
    if contradiction_count > 0:
        unresolved_gaps.append("contradictions_present")
    if has_hard_constraint_violation:
        unresolved_gaps.append("hard_constraints_present")
    if scene_validation_hard_failure or scene_validation_failed > 0:
        unresolved_gaps.append("scene_validation_failures")

    positive_signals = sum(
        1
        for flag in (
            bool(desc_entities or desc_claims),
            bool(recommended_actions),
            categorized_context_support == "strong",
            scene_validation_present and not scene_validation_hard_failure and scene_validation_failed <= 0,
        )
        if flag
    )
    present = bool(positive_signals or unresolved_gaps)
    if positive_signals >= 3 and not unresolved_gaps:
        level = "strong"
        summary = "evidence-backed comprehension review available"
    elif present:
        level = "weak"
        summary = "partial comprehension review available"
    else:
        level = "missing"
        summary = "comprehension review evidence missing"

    validation_level = "missing"
    if scene_validation_present or contradiction_count > 0 or constraint_violation_count > 0:
        validation_level = (
            "clear"
            if (
                scene_validation_present
                and not scene_validation_hard_failure
                and scene_validation_failed <= 0
                and contradiction_count <= 0
                and constraint_violation_count <= 0
                and not has_hard_constraint_violation
            )
            else "issues_present"
        )

    return {
        "present": present,
        "level": level,
        "summary": summary,
        "supporting_evidence": {
            "description_entity_count": len(desc_entities),
            "description_claim_count": len(desc_claims),
            "question_count": len(desc_questions),
            "proposed_action_count": len([row for row in recommended_actions if isinstance(row, str)]),
            "contradiction_count": contradiction_count,
            "has_hard_constraint_violation": has_hard_constraint_violation,
            "scene_validation_present": scene_validation_present,
            "categorized_context_support": categorized_context_support,
            "validation_evidence": {
                "scene_validation_failed": int(scene_validation_failed),
                "scene_validation_hard_failure": bool(scene_validation_hard_failure),
                "constraint_violation_count": int(constraint_violation_count),
            },
            "measurement_evidence": {
                "level": str(measurement_summary.get("level") or "missing"),
                "reason": str(measurement_summary.get("reason") or ""),
                "measurement_recorded": bool(measurement_evidence.get("measurement_recorded")),
            },
            "categorized_context_evidence": {
                "support_level": categorized_context_support,
                "join_status": str(categorized_context.get("join_status") or "missing"),
                "label_count": len(categorized_context.get("labels") or []),
                "alias_count": len(categorized_context.get("aliases") or []),
                "comparison_axis_count": len(categorized_context.get("comparison_axes") or []),
                "relation_family_count": len(categorized_context.get("relation_families") or []),
                "bridge_source_count": len(categorized_context.get("bridge_sources") or []),
            },
            "retention_evidence": {
                "record_id_present": record_id_present,
                "categorized_context_persisted": bool(categorized_context),
                "comprehension_review_persisted": bool(persisted_comprehension_summary),
            },
        },
        "observed_levels": {
            "measurement_adequacy": str(measurement_summary.get("level") or "missing"),
            "categorized_context": categorized_context_support,
            "validation_evidence": validation_level,
        },
        "rationale": rationale,
        "unresolved_gaps": unresolved_gaps,
    }


def _build_learning_readiness_verdict_for_record(
    record: Dict[str, Any],
    *,
    measurement_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from module_metrics import build_learning_readiness_verdict

    measurement_payload = measurement_summary if isinstance(measurement_summary, dict) else {}
    if not measurement_payload:
        candidate = record.get('measurement_adequacy') if isinstance(record.get('measurement_adequacy'), dict) else {}
        measurement_payload = dict(candidate) if isinstance(candidate, dict) else {}

    relational_state = record.get('relational_state') if isinstance(record.get('relational_state'), dict) else {}
    derived = relational_state.get('derived') if isinstance(relational_state.get('derived'), dict) else {}

    categorized_summary: Dict[str, Any] = {}
    persisted_categorized = derived.get('categorized_context_summary') if isinstance(derived.get('categorized_context_summary'), dict) else {}
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

    persisted_comprehension = derived.get('comprehension_review_summary') if isinstance(derived.get('comprehension_review_summary'), dict) else {}
    if isinstance(persisted_comprehension, dict) and persisted_comprehension:
        comprehension_summary = dict(persisted_comprehension)
    else:
        comprehension_summary = _build_comprehension_review_summary(record)

    categorized_level = categorized_summary.get('level')
    if not isinstance(categorized_level, str) or not categorized_level:
        categorized_level = categorized_summary.get('support_level')

    comprehension_level = comprehension_summary.get('level')
    if not isinstance(comprehension_level, str) or not comprehension_level:
        comprehension_level = comprehension_summary.get('quality')

    return build_learning_readiness_verdict(
        measurement_adequacy={
            'level': measurement_payload.get('level'),
            'reason': measurement_payload.get('reason'),
        },
        categorized_context={
            'level': categorized_level,
            'counts': {
                'labels': len(categorized_summary.get('labels') or []),
                'aliases': len(categorized_summary.get('aliases') or []),
                'comparison_axes': len(categorized_summary.get('comparison_axes') or []),
                'relation_families': len(categorized_summary.get('relation_families') or []),
                'bridge_sources': len(categorized_summary.get('bridge_sources') or []),
            },
        },
        comprehension_review={
            'level': comprehension_level,
            'summary': comprehension_summary.get('summary'),
            'unresolved_gaps': comprehension_summary.get('unresolved_gaps'),
            'supporting_evidence': comprehension_summary.get('supporting_evidence'),
        },
    )


def _build_foundational_tier_hook_summary(cfg: Dict[str, Any]) -> Dict[str, Any]:
    hook = build_guarded_shadow_descriptor_hook(cfg)
    if not isinstance(hook, dict) or not hook.get('hook_enabled'):
        return {}

    review_row = hook.get('review_row') if isinstance(hook.get('review_row'), dict) else {}
    family_configured = is_real_tier_family_configured(cfg, 'simultaneous_context_match')
    return {
        'family_id': str(hook.get('family_id') or 'simultaneous_context_match'),
        'hook_kind': str(hook.get('hook_kind') or 'guarded_shadow_descriptor'),
        'support_role': 'foundational_active_space_support',
        'review_only': True,
        'authoritative': False,
        'current_serving': False,
        'scheduler_authority_path': False,
        'family_configured': family_configured,
        'family_activation_excluded': not family_configured,
        'family_activation_mode': 'non_serving_shadow_family' if family_configured else 'guarded_candidate_only',
        'hook_posture': str(hook.get('hook_posture') or 'shadow'),
        'candidate_state': str(review_row.get('candidate_state') or 'documentation_only'),
        'comparison_counts': dict(review_row.get('comparison_counts') or {}),
        'artifact_bundle_ref': str(review_row.get('artifact_bundle_ref') or ''),
        'active_space_support': {
            'immediate_reference_support': True,
            'bounded_compute_support': True,
            'consumption_surfaces': ['relational_state.derived', 'selection_rows'],
        },
        'rollback_mode': str(hook.get('rollback_mode') or 'documentation_only_remove_or_ignore'),
        'rollback_expectation': (
            'remove or disable the non-serving simultaneous_context_match family and its guarded shadow hook without '
            'changing Tier 1 decisions, scheduler authority, or schedule_mirror serving behavior'
            if family_configured
            else 'disable or remove tier_families.simultaneous_context_match.guarded_shadow_hook without changing '
            'Tier 1 decisions, scheduler authority, or active-family reporting'
        ),
    }


def build_bounded_runtime_switch_inventory(
    *,
    target_space: Any,
    justification: Any,
    mirror_routing: Optional[Dict[str, Any]] = None,
    mirror_summary: Optional[Dict[str, Any]] = None,
    foundational_hook_summary: Optional[Dict[str, Any]] = None,
    foundational_active_space_summary: Optional[Dict[str, Any]] = None,
    foundational_optional_reference_artifact: Optional[Dict[str, Any]] = None,
    scheduled_task_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    normalized_target_space = str(target_space or "")
    normalized_justification = justification if isinstance(justification, dict) else {}
    mirror_routing = mirror_routing if isinstance(mirror_routing, dict) else {}
    mirror_summary = mirror_summary if isinstance(mirror_summary, dict) else {}
    foundational_hook_summary = foundational_hook_summary if isinstance(foundational_hook_summary, dict) else {}
    foundational_active_space_summary = (
        foundational_active_space_summary if isinstance(foundational_active_space_summary, dict) else {}
    )
    foundational_optional_reference_artifact = (
        foundational_optional_reference_artifact
        if isinstance(foundational_optional_reference_artifact, dict)
        else {}
    )
    task_labels = [str(label) for label in (scheduled_task_labels or []) if str(label or "").strip()]

    switches = [
        build_bounded_runtime_switch(
            "review_only",
            family_id="simultaneous_context_match",
            configured=bool(foundational_hook_summary),
            engaged=bool(foundational_hook_summary),
            state=str(foundational_hook_summary.get("candidate_state") or "inactive"),
            reason_summary=(
                "guarded simultaneous-context support remains review-only and non-serving"
                if foundational_hook_summary
                else "review-only family switch not engaged for this record"
            ),
            evidence_refs=[str(foundational_hook_summary.get("artifact_bundle_ref") or "")],
        ),
        build_bounded_runtime_switch(
            "reject",
            family_id="simultaneous_context_match",
            configured=bool(foundational_active_space_summary or foundational_optional_reference_artifact),
            engaged=bool(foundational_optional_reference_artifact),
            state=str(foundational_optional_reference_artifact.get("source_result_state") or "inactive"),
            reason_summary=str(
                foundational_optional_reference_artifact.get("result_reason_summary")
                or "no bounded rejection artifact recorded for this record"
            ),
            evidence_refs=[
                str(item.get("reason_code") or "")
                for item in (foundational_optional_reference_artifact.get("reason_items") or [])
                if isinstance(item, dict)
            ],
        ),
        build_bounded_runtime_switch(
            "mirror",
            family_id="schedule_mirror",
            configured=bool(mirror_routing.get("config_snapshot") or mirror_summary),
            engaged=bool(mirror_summary),
            state=str(mirror_summary.get("selected_action_id") or mirror_routing.get("active_routing_state") or "inactive"),
            reason_summary=(
                "schedule_mirror preserved the bounded schedule summary for the current decision"
                if mirror_summary
                else "schedule_mirror did not record a bounded summary for this record"
            ),
            evidence_refs=[str(mirror_summary.get("mirror_schedule_summary_hash") or "")],
            target_space=normalized_target_space,
            policy_rule_id=str(normalized_justification.get("policy_rule_id") or ""),
        ),
        build_bounded_runtime_switch(
            "hold_defer",
            configured=True,
            engaged=normalized_target_space == "HoldingSpace",
            state="holding" if normalized_target_space == "HoldingSpace" else "pass_through",
            reason_summary=str(
                normalized_justification.get("reason")
                or "target did not require HoldingSpace defer"
            ),
            target_space=normalized_target_space,
            policy_rule_id=str(normalized_justification.get("policy_rule_id") or ""),
        ),
        build_bounded_runtime_switch(
            "schedule_follow_up",
            configured=True,
            engaged=bool(task_labels),
            state="queued" if task_labels else "not_scheduled",
            reason_summary=(
                f"scheduled follow-up remains bounded through {', '.join(sorted(dict.fromkeys(task_labels)))}"
                if task_labels
                else "no bounded follow-up tasks were added for this record"
            ),
            scheduled_task_labels=task_labels,
            target_space=normalized_target_space,
            policy_rule_id=str(normalized_justification.get("policy_rule_id") or ""),
        ),
        build_bounded_runtime_switch(
            "role_switch",
            family_id="simultaneous_context_match",
            configured=bool(foundational_hook_summary or foundational_active_space_summary),
            engaged=False,
            state="later_available" if (foundational_hook_summary or foundational_active_space_summary) else "inactive",
            reason_summary=(
                "bounded role-switch remains available for later storage or packet-preparation pressure, but is not preferred for the current record"
                if (foundational_hook_summary or foundational_active_space_summary)
                else "bounded role-switch path is not active for the current record"
            ),
        ),
    ]
    return summarize_bounded_runtime_switches(switches)


def _build_selection_migration_sandbox_report(
    selection_settings: Dict[str, Any],
    readiness_verdict: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    from module_metrics import build_learning_sandbox_activation_report

    sandbox_cfg = selection_settings.get('sandbox_activation') if isinstance(selection_settings, dict) else {}
    if not isinstance(sandbox_cfg, dict) or not sandbox_cfg:
        enabled = bool(selection_settings.get('enable')) if isinstance(selection_settings, dict) else False
        use_retrieval_scores = bool(selection_settings.get('use_retrieval_scores')) if isinstance(selection_settings, dict) else False
        use_retrieval_components = bool(selection_settings.get('use_retrieval_components')) if isinstance(selection_settings, dict) else False
        configured_paths = []
        if use_retrieval_scores:
            configured_paths.append('retrieval_score')
        if use_retrieval_components:
            configured_paths.append('retrieval_components')
        retrieval_component_weights = selection_settings.get('retrieval_component_weights') if isinstance(selection_settings, dict) else None
        try:
            retrieval_component_weight = float(selection_settings.get('retrieval_component_weight', 0.0) or 0.0) if isinstance(selection_settings, dict) else 0.0
        except Exception:
            retrieval_component_weight = 0.0
        if retrieval_component_weight < 0.0:
            retrieval_component_weight = 0.0
        if retrieval_component_weight > 1.0:
            retrieval_component_weight = 1.0
        blocked_reason = None
        if not enabled:
            blocked_reason = 'sandbox_disabled'
        elif not configured_paths:
            blocked_reason = 'no_update_path_configured'

        return {
            'version': 1,
            'sandbox': 'selection_migration',
            'status': 'active' if blocked_reason is None else ('disabled' if blocked_reason == 'sandbox_disabled' else 'blocked'),
            'active': blocked_reason is None,
            'blocked_reason': blocked_reason,
            'configured_paths': configured_paths,
            'active_paths': list(configured_paths) if blocked_reason is None else [],
            'read_only': True,
            'persistent_state': False,
            'mutable_weights': False,
            'readiness': {
                'status': None,
                'reason': None,
                'unmet_conditions': [],
            },
            'config_snapshot': {
                'enable': enabled,
                'use_retrieval_scores': use_retrieval_scores,
                'use_retrieval_components': use_retrieval_components,
                'retrieval_component_weight': float(retrieval_component_weight),
                'retrieval_component_weights_present': isinstance(retrieval_component_weights, dict),
            },
            'path_metadata': {
                'retrieval_score': {
                    'configured': use_retrieval_scores,
                    'weight': 1.0 if use_retrieval_scores else 0.0,
                },
                'retrieval_components': {
                    'configured': use_retrieval_components,
                    'weight': float(retrieval_component_weight) if use_retrieval_components else 0.0,
                    'weights_present': isinstance(retrieval_component_weights, dict),
                },
            },
            'activation_mode': 'legacy_enable_flags',
            'preserve_baseline_when_blocked': True,
        }

    report = build_learning_sandbox_activation_report(
        readiness_verdict=readiness_verdict,
        sandbox_settings=selection_settings,
        sandbox_name='selection_migration',
    )

    mode = sandbox_cfg.get('mode') if isinstance(sandbox_cfg, dict) else None
    preserve_baseline = True
    if isinstance(sandbox_cfg, dict):
        preserve_baseline = bool(sandbox_cfg.get('preserve_baseline_when_blocked', True))
    mode = str(mode or 'learning_readiness_gated')

    out = dict(report)
    out['activation_mode'] = mode
    out['preserve_baseline_when_blocked'] = preserve_baseline
    if mode != 'learning_readiness_gated':
        out['status'] = 'blocked'
        out['active'] = False
        out['blocked_reason'] = 'unsupported_activation_mode'
        out['active_paths'] = []
    return out


def _mirror_tier_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        return {}
    return cfg.get("mirror_tiers", {}) if isinstance(cfg.get("mirror_tiers", {}), dict) else {}


def _tier_family_activation_state(
    *,
    family_id: str,
    family_cfg: Any,
    level_flags: Optional[List[Tuple[int, str]]] = None,
    passthrough_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    descriptor = build_tier_family_descriptor(
        str(family_id),
        family_cfg,
        level_flags=level_flags,
        passthrough_flags=passthrough_flags,
    )
    return {
        "family_id": str(descriptor.get("family_id") or family_id),
        "tiers": dict(descriptor.get("tiers") or {}),
        "enabled_levels": list(descriptor.get("enabled_levels") or []),
        "flags": dict(descriptor.get("flags") or {}),
        "config_snapshot": dict(descriptor.get("config_snapshot") or {}),
    }


_TIER_ROUTING_ACTIVE_STATES = frozenset({"active"})
_TIER_ROUTING_SERVING_STATES = frozenset({"active", "draining"})
_TIER_ROUTING_ALLOWED_STATES = frozenset({"active", "shadow", "draining", "standby", "retired"})


def _normalize_tier_instance_levels(instance_cfg: Any, default_levels: List[int]) -> List[int]:
    if not isinstance(instance_cfg, dict):
        return list(default_levels)
    raw_levels = instance_cfg.get("enabled_levels")
    if not isinstance(raw_levels, list):
        return list(default_levels)

    normalized: List[int] = []
    allowed = set(default_levels)
    for value in raw_levels:
        try:
            level = int(value)
        except Exception:
            continue
        if level in allowed and level not in normalized:
            normalized.append(level)
    return normalized or list(default_levels)


def _tier_family_routing_state(
    *,
    family_id: str,
    family_cfg: Any,
    level_flags: Optional[List[Tuple[int, str]]] = None,
    passthrough_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    activation = _tier_family_activation_state(
        family_id=family_id,
        family_cfg=family_cfg,
        level_flags=level_flags,
        passthrough_flags=passthrough_flags,
    )
    enabled_levels = list(activation.get("enabled_levels") or [])
    enabled_tiers = dict(activation.get("tiers") or {})
    normalized_cfg = family_cfg if isinstance(family_cfg, dict) else {}
    raw_instances = normalized_cfg.get("instances") if isinstance(normalized_cfg.get("instances"), list) else []

    instances: List[Dict[str, Any]] = []
    primary_instance: Optional[Dict[str, Any]] = None
    fallback_serving_instance: Optional[Dict[str, Any]] = None
    for index, instance_cfg in enumerate(raw_instances):
        if not isinstance(instance_cfg, dict):
            continue
        instance_id = str(instance_cfg.get("instance_id") or instance_cfg.get("id") or f"{family_id}_{index + 1}")
        routing_state = str(instance_cfg.get("routing_state") or instance_cfg.get("state") or "standby").strip().lower()
        if routing_state not in _TIER_ROUTING_ALLOWED_STATES:
            routing_state = "standby"
        instance_levels = _normalize_tier_instance_levels(instance_cfg, enabled_levels)
        active_levels = list(instance_levels) if routing_state in _TIER_ROUTING_SERVING_STATES else []
        normalized_instance = {
            "instance_id": instance_id,
            "routing_state": routing_state,
            "enabled_levels": instance_levels,
            "active_levels": active_levels,
            "is_primary": False,
            "is_serving": routing_state in _TIER_ROUTING_SERVING_STATES,
        }
        instances.append(normalized_instance)
        if primary_instance is None and routing_state in _TIER_ROUTING_ACTIVE_STATES:
            primary_instance = normalized_instance
        if fallback_serving_instance is None and routing_state in _TIER_ROUTING_SERVING_STATES:
            fallback_serving_instance = normalized_instance

    selected_instance = primary_instance or fallback_serving_instance
    if isinstance(selected_instance, dict):
        selected_instance["is_primary"] = True
        active_levels = list(selected_instance.get("active_levels") or [])
        active_instance_id = str(selected_instance.get("instance_id") or "")
        active_routing_state = str(selected_instance.get("routing_state") or "")
        route_source = "instance_routing"
    else:
        active_levels = list(enabled_levels)
        active_instance_id = ""
        active_routing_state = "active" if enabled_levels else "retired"
        route_source = "family_flags"

    active_tiers = {
        tier_key: (int(tier_key.replace("tier", "").replace("_enabled", "")) in active_levels)
        for tier_key in enabled_tiers.keys()
    }
    return {
        "family_id": str(activation.get("family_id") or family_id),
        "tiers": enabled_tiers,
        "active_tiers": active_tiers,
        "enabled_levels": enabled_levels,
        "active_levels": active_levels,
        "flags": dict(activation.get("flags") or {}),
        "config_snapshot": dict(activation.get("config_snapshot") or {}),
        "route_source": route_source,
        "active_instance_id": active_instance_id,
        "active_routing_state": active_routing_state,
        "instance_count": len(instances),
        "instances": instances,
        "has_shadow_instance": any(str(item.get("routing_state") or "") == "shadow" for item in instances),
        "has_draining_instance": any(str(item.get("routing_state") or "") == "draining" for item in instances),
    }


def _normalize_action_list(actions: Any) -> List[str]:
    if not isinstance(actions, list):
        return []
    cleaned = [str(a) for a in actions if isinstance(a, str) and a]
    return sorted(set(cleaned))


def _build_mirror_schedule_summary(
    *,
    target_space: Any,
    justification: Any,
    accepted_actions: Any,
    rejected_actions: Any,
    policy_inputs: Any,
) -> Dict[str, Any]:
    reason = ""
    policy_rule_id = None
    if isinstance(justification, dict):
        reason = str(justification.get("reason") or "")
        policy_rule_id = justification.get("policy_rule_id")

    accepted = _normalize_action_list(accepted_actions)
    rejected = _normalize_action_list(rejected_actions)
    candidates = sorted(set(accepted + rejected))

    policy_snapshot = dict(policy_inputs) if isinstance(policy_inputs, dict) else {}
    policy_snapshot_hash = _stable_hash(policy_snapshot)

    return {
        "selected_action_id": str(target_space),
        "selection_reason": reason,
        "policy_rule_id": policy_rule_id,
        "candidate_count": len(candidates),
        "candidate_actions": candidates,
        "policy_snapshot_hash": policy_snapshot_hash,
        "selection_score": policy_snapshot.get("selection_score"),
        "objective_alignment": policy_snapshot.get("objective_alignment"),
    }


def _derive_advisory_tag(
    *,
    candidate_count_delta: int,
    selection_reason_change: bool,
    policy_hash_change: bool,
) -> str:
    changes = sum([bool(candidate_count_delta), bool(selection_reason_change), bool(policy_hash_change)])
    if changes == 0:
        return "no_change"
    if changes > 1:
        return "multi_shift"
    if candidate_count_delta:
        return "candidate_shift"
    if selection_reason_change:
        return "reason_shift"
    return "policy_shift"


def _build_mirror_schedule_delta(
    *,
    prior_summary: Dict[str, Any],
    current_summary: Dict[str, Any],
) -> Dict[str, Any]:
    prior_hash = str(prior_summary.get("mirror_schedule_summary_hash") or "")
    current_hash = str(current_summary.get("mirror_schedule_summary_hash") or "")
    prior_count = int(prior_summary.get("candidate_count") or 0)
    current_count = int(current_summary.get("candidate_count") or 0)
    selection_reason_change = str(prior_summary.get("selection_reason") or "") != str(
        current_summary.get("selection_reason") or ""
    )
    policy_hash_change = str(prior_summary.get("policy_snapshot_hash") or "") != str(
        current_summary.get("policy_snapshot_hash") or ""
    )
    prior_score = prior_summary.get("selection_score")
    current_score = current_summary.get("selection_score")
    try:
        prior_score_f = float(prior_score)
        current_score_f = float(current_score)
        selection_score_delta = float(current_score_f - prior_score_f)
        selection_score_change = bool(selection_score_delta != 0.0)
    except Exception:
        selection_score_delta = 0.0
        selection_score_change = False

    objective_alignment_change = str(prior_summary.get("objective_alignment") or "") != str(
        current_summary.get("objective_alignment") or ""
    )
    candidate_count_delta = int(current_count - prior_count)
    change_count = int(
        sum(
            [
                bool(candidate_count_delta),
                bool(selection_reason_change),
                bool(policy_hash_change),
                bool(selection_score_change),
                bool(objective_alignment_change),
            ]
        )
    )
    change_ratio = round(float(change_count) / 5.0, 6)
    advisory_tag = _derive_advisory_tag(
        candidate_count_delta=candidate_count_delta,
        selection_reason_change=selection_reason_change,
        policy_hash_change=policy_hash_change,
    )
    payload = {
        "prior_summary_hash": prior_hash,
        "current_summary_hash": current_hash,
        "candidate_count_delta": candidate_count_delta,
        "selection_reason_change": selection_reason_change,
        "policy_hash_change": policy_hash_change,
        "selection_score_delta": selection_score_delta,
        "selection_score_change": selection_score_change,
        "objective_alignment_change": objective_alignment_change,
        "change_count": change_count,
        "change_ratio": change_ratio,
        "advisory_tag": advisory_tag,
    }
    payload["delta_hash"] = _stable_hash(payload)
    return payload


def _derive_tier3_advisory(delta: Dict[str, Any]) -> str:
    tag = str(delta.get("advisory_tag") or "")
    if tag == "no_change":
        return "stable"
    if tag in {"candidate_shift", "reason_shift", "policy_shift"}:
        return "monitor"
    if tag == "multi_shift":
        return "review"
    return "unknown"


def _mirror_schedule_tier3_contract() -> Dict[str, Any]:
    return {
        "required_keys": {
            "tier2_hash",
            "summary",
            "delta_from_tier2",
            "hash_inputs",
            "hash_value",
        },
        "optional_keys": {"advisory"},
        "hash_inputs_order": ["tier2_hash", "summary", "delta_from_tier2"],
    }


def _validate_mirror_schedule_tier3_payload(payload: Any, allow_advisory: bool) -> bool:
    if not isinstance(payload, dict):
        return False

    contract = _mirror_schedule_tier3_contract()
    required = set(contract.get("required_keys") or [])
    optional = set(contract.get("optional_keys") or [])
    allowed = required | optional
    if not allow_advisory and "advisory" in payload:
        return False
    if not required.issubset(payload.keys()):
        return False
    if any(key not in allowed for key in payload.keys()):
        return False

    tier2_hash = payload.get("tier2_hash")
    summary = payload.get("summary")
    delta = payload.get("delta_from_tier2")
    hash_inputs = payload.get("hash_inputs")
    hash_value = payload.get("hash_value")

    if not isinstance(tier2_hash, str) or not isinstance(summary, str):
        return False
    if not isinstance(delta, dict) or not isinstance(hash_inputs, list) or not isinstance(hash_value, str):
        return False
    if "advisory" in payload and not isinstance(payload.get("advisory"), str):
        return False

    delta_adds = delta.get("adds")
    delta_removes = delta.get("removes")
    delta_reorder = delta.get("reorder_count")
    if not (isinstance(delta_adds, list) and isinstance(delta_removes, list) and isinstance(delta_reorder, int)):
        return False

    expected_hash_inputs = [tier2_hash, summary, delta]
    if hash_inputs != expected_hash_inputs:
        return False
    if _stable_hash(hash_inputs) != hash_value:
        return False
    return True


def _build_mirror_schedule_tier3(
    *,
    summary: Dict[str, Any],
    delta: Dict[str, Any],
    allow_advisory: bool,
) -> Dict[str, Any]:
    tier2_hash = str(delta.get("delta_hash") or "")
    summary_hash = str(summary.get("mirror_schedule_summary_hash") or "")
    summary_payload = {
        "tier2_summary_hash": summary_hash,
        "tier2_delta_hash": tier2_hash,
        "advisory_tag": delta.get("advisory_tag"),
        "change_ratio": delta.get("change_ratio"),
    }
    summary_text = json.dumps(summary_payload, sort_keys=True)
    delta_from_tier2 = {
        "adds": [],
        "removes": [],
        "reorder_count": int(delta.get("change_count") or 0),
    }
    hash_inputs = [tier2_hash, summary_text, delta_from_tier2]
    payload = {
        "tier2_hash": tier2_hash,
        "summary": summary_text,
        "delta_from_tier2": delta_from_tier2,
        "hash_inputs": hash_inputs,
        "hash_value": _stable_hash(hash_inputs),
    }
    if allow_advisory:
        payload["advisory"] = _derive_tier3_advisory(delta)
    return payload


def _build_tier_activation_audit(
    *,
    schedule_cfg: Dict[str, Any],
    deterministic_mode: bool,
    fixed_ts: Optional[str],
    run_id: Optional[str],
) -> Dict[str, Any]:
    activation = _tier_family_activation_state(
        family_id="schedule_mirror",
        family_cfg=schedule_cfg,
        passthrough_flags=["allow_advisory"],
    )
    tiers = activation.get("tiers") if isinstance(activation.get("tiers"), dict) else {}
    flags = activation.get("flags") if isinstance(activation.get("flags"), dict) else {}
    config_snapshot = activation.get("config_snapshot") if isinstance(activation.get("config_snapshot"), dict) else {}

    tier1_enabled = bool(tiers.get("tier1_enabled"))
    tier2_enabled = bool(tiers.get("tier2_enabled"))
    tier3_enabled = bool(tiers.get("tier3_enabled"))
    allow_advisory = bool(flags.get("allow_advisory"))

    audit: Dict[str, Any] = {
        "run_id": str(run_id) if run_id is not None else "",
        "deterministic_mode": bool(deterministic_mode),
        "fixed_timestamp": str(fixed_ts) if deterministic_mode and fixed_ts else None,
        "tiers": {
            "tier1_enabled": tier1_enabled,
            "tier2_enabled": tier2_enabled,
            "tier3_enabled": tier3_enabled,
        },
        "allow_advisory": allow_advisory,
        "config_hash": _stable_hash(config_snapshot),
    }
    audit["audit_hash"] = _stable_hash(audit)
    return audit

@dataclass(frozen=True)
class GraphSnapshot:
    tick_id: str
    nodes: Tuple[Tuple[str, Dict[str, Any]], ...]
    edges: Tuple[Tuple[str, str, str, str], ...]
    node_attrs: Dict[str, Dict[str, Any]]
    edge_attrs: Dict[str, Dict[str, Any]]
    snapshot_hash: str
    build_info: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_id": self.tick_id,
            "nodes": [
                {"id": node_id, "payload": payload}
                for node_id, payload in self.nodes
            ],
            "edges": [
                {
                    "source": src,
                    "target": dst,
                    "type": relation_type,
                    "payload_hash": payload_hash,
                    "attributes": self.edge_attrs.get(_make_edge_key(src, dst, relation_type, payload_hash), {}),
                }
                for (src, dst, relation_type, payload_hash) in self.edges
            ],
            "node_attrs": self.node_attrs,
            "edge_attrs": self.edge_attrs,
            "snapshot_hash": self.snapshot_hash,
            "build_info": self.build_info,
        }


def _make_edge_key(src: str, dst: str, relation_type: str, payload_hash: Optional[str] = None) -> str:
    if payload_hash:
        return f"{src}::{relation_type}::{dst}::{payload_hash}"
    return f"{src}::{relation_type}::{dst}"


def _canonical_to_obj(value: Any) -> Any:
    try:
        return json.loads(canonical_json_bytes(value).decode("utf-8"))
    except Exception:
        return value


def _normalize_entity(entity: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
    if not isinstance(entity, dict):
        return None
    raw_id = entity.get("id") if "id" in entity else entity.get("entity_id")
    if raw_id is None:
        return None
    node_id = str(raw_id).strip()
    if not node_id:
        return None
    payload = {k: entity[k] for k in entity.keys() if k not in {"id", "entity_id"}}
    normalized_payload = _canonical_to_obj(payload) if payload else {}
    return node_id, normalized_payload


def _normalize_relation(relation: Any) -> Optional[Tuple[Tuple[str, str, str, str], str, Dict[str, Any]]]:
    if not isinstance(relation, dict):
        return None
    raw_src = relation.get("subj") or relation.get("source") or relation.get("source_id")
    raw_dst = relation.get("obj") or relation.get("target") or relation.get("target_id")
    raw_type = relation.get("pred") or relation.get("type")
    if raw_src is None or raw_type is None:
        return None
    src = str(raw_src)
    relation_type = str(raw_type)
    if raw_dst is None:
        dst = ""
    elif isinstance(raw_dst, (dict, list)):
        dst = canonical_json_bytes(raw_dst).decode("utf-8")
    else:
        dst = str(raw_dst)
    excluded = {"subj", "source", "source_id", "obj", "target", "target_id", "pred", "type"}
    attrs_payload = {k: relation[k] for k in relation.keys() if k not in excluded}
    attrs_norm = _canonical_to_obj(attrs_payload) if attrs_payload else {}
    payload_for_hash = {
        "source": src,
        "target": dst,
        "type": relation_type,
        "attrs": attrs_norm,
    }
    payload_hash = hashlib.sha256(canonical_json_bytes(payload_for_hash)).hexdigest()
    edge_key = _make_edge_key(src, dst, relation_type, payload_hash)
    return (src, dst, relation_type, payload_hash), edge_key, attrs_norm


def _normalize_constraint(constraint: Any) -> Optional[str]:
    if not isinstance(constraint, dict):
        return None
    normalized = _canonical_to_obj(constraint)
    try:
        return hashlib.sha256(canonical_json_bytes(normalized)).hexdigest()
    except Exception:
        return None


def build_graph_snapshot(relational_state: Dict[str, Any], tick_id: str) -> Optional[GraphSnapshot]:
    if not isinstance(relational_state, dict):
        return None

    nodes_input = relational_state.get("entities")
    relations_input = relational_state.get("relations")
    constraints_input = relational_state.get("constraints")

    entity_rows = nodes_input if isinstance(nodes_input, list) else []
    relation_rows = relations_input if isinstance(relations_input, list) else []
    constraint_rows = constraints_input if isinstance(constraints_input, list) else []

    nodes: List[Tuple[str, Dict[str, Any]]] = []
    node_attrs: Dict[str, Dict[str, Any]] = {}
    for entity in entity_rows:
        normalized_entity = _normalize_entity(entity)
        if not normalized_entity:
            continue
        node_id, payload = normalized_entity
        nodes.append((node_id, payload))
        node_attrs[node_id] = payload
    nodes.sort(key=lambda row: row[0])
    nodes_tuple: Tuple[Tuple[str, Dict[str, Any]], ...] = tuple(nodes)

    edges: List[Tuple[str, str, str, str]] = []
    edge_attrs: Dict[str, Dict[str, Any]] = {}
    for relation in relation_rows:
        normalized_relation = _normalize_relation(relation)
        if not normalized_relation:
            continue
        edge_tuple, edge_key, attrs = normalized_relation
        edges.append(edge_tuple)
        edge_attrs[edge_key] = attrs
    edges.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    edges_tuple: Tuple[Tuple[str, str, str, str], ...] = tuple(edges)

    constraint_hashes: List[str] = []
    for constraint in constraint_rows:
        chash = _normalize_constraint(constraint)
        if chash:
            constraint_hashes.append(chash)
    constraint_hashes.sort()

    if not nodes_tuple and not edges_tuple and not constraint_hashes:
        return None

    snapshot_payload = {
        "tick_id": str(tick_id),
        "nodes": [
            {"id": node_id, "payload": payload}
            for node_id, payload in nodes_tuple
        ],
        "edges": [
            {
                "source": src,
                "target": dst,
                "type": relation_type,
                "payload_hash": payload_hash,
                "attributes": edge_attrs.get(_make_edge_key(src, dst, relation_type, payload_hash), {}),
            }
            for (src, dst, relation_type, payload_hash) in edges_tuple
        ],
        "constraint_hashes": constraint_hashes,
    }
    snapshot_hash = hashlib.sha256(canonical_json_bytes(snapshot_payload)).hexdigest()
    build_info = {
        "entity_count": len(nodes_tuple),
        "relation_count": len(edges_tuple),
        "constraint_count": len(constraint_hashes),
        "constraint_hashes": constraint_hashes,
        "builder": "module_integration.build_graph_snapshot",
    }

    return GraphSnapshot(
        tick_id=str(tick_id),
        nodes=nodes_tuple,
        edges=edges_tuple,
        node_attrs=node_attrs,
        edge_attrs=edge_attrs,
        snapshot_hash=snapshot_hash,
        build_info=build_info,
    )


def ProcessIncomingData(data_id, content, category="semantic"):
    """
    Integration Layer: orchestrates Storage → Measurement → Awareness → Scheduling
    while checking objectives and logging current activity.
    """
    objectives = get_objectives_by_label("measurement")
    if objectives:
        print("Measurement objective found, executing full loop...")

        # Storage
        set_activity("store", f"Storing {data_id}")
        print(store_information(data_id, content, category))

        # Measurement
        set_activity("measure", f"Measuring {data_id}")
        try:
            data_id_s = sanitize_id(data_id)
        except Exception as e:
            print(f"Invalid data_id: {e}")
            return
        file_path = safe_join(resolve_path(category), f"{data_id_s}.json")
        score = measure_information(file_path, threshold=1.0)
        print("Measurement result:", score)

        # Awareness
        set_activity("awareness", f"Awareness triggered for {data_id}")
        print(trigger_information_seeking(data_id, 2))
        print(validate_response(data_id))

        # Scheduling
        set_activity("schedule", f"Scheduling {data_id}")
        print(flag_record(file_path, "review", minutes_from_now=10))

        # Persist activity log at the end of the cycle
        persist_activity()

    else:
        print("No measurement objective found. Skipping loop.")

def RelationalMeasurement(data_id, content, category="semantic", subject_id="default"):
    # Phase 6.9: Cycle orchestrator
    cycle_id = None
    deterministic_mode = False
    fixed_ts = None
    # Load determinism settings from config, if enabled
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {})
        if det.get('deterministic_mode'):
            deterministic_mode = True
            fixed_ts = det.get('fixed_timestamp') or None
    except Exception:
        pass
    # Validate early to avoid unsafe paths (store also validates, but integration must not fall back)
    try:
        data_id_s = sanitize_id(data_id)
    except Exception as e:
        return ["error_invalid_id"]

    # Deterministic cycle_id when determinism is enabled; otherwise uuid.
    try:
        if deterministic_mode and fixed_ts:
            h = hashlib.sha256(f"{data_id_s}|{str(fixed_ts)}|{str(content)}".encode('utf-8')).hexdigest()[:16]
            cycle_id = f"cycle_{h}"
        else:
            cycle_id = str(uuid.uuid4())
    except Exception:
        cycle_id = str(uuid.uuid4())

    # Store + Repeat with description; get path deterministically
    store_status = store_and_get_path(data_id, content, category)

    # File path for scheduling (unified + safe)
    file_path = store_status.get("path") or safe_join(resolve_path(category), f"{data_id_s}.json")

    # Ensure semantic record exists before downstream steps
    try:
        if not os.path.exists(file_path):
            store_information(data_id, {"content": content, "module": "integration_fallback"}, category)
        # If still missing, write a minimal record to avoid scheduling errors
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": data_id,
                    "content": content,
                    "occurrence_count": 1,
                    "timestamps": [],
                    "labels": [],
                    "schema_version": "0.9"
                }, f, ensure_ascii=False, indent=2)
        elif os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                if not isinstance(existing, dict):
                    raise ValueError("semantic record is not an object")
            except Exception:
                from module_storage import _atomic_write_json
                _atomic_write_json(file_path, {
                    "id": data_id,
                    "content": content,
                    "occurrence_count": 1,
                    "timestamps": [],
                    "labels": [],
                    "schema_version": "0.9"
                })
    except Exception:
        pass

    # Optional: attach 3D measurement mapped into a canonical relational_state.
    # This is guarded and non-fatal; it only runs when a spatial asset path exists.
    adapter_log = None
    try:
        from module_relational_adapter import attach_composition_bridge_outputs, attach_spatial_relational_state

        composition_result = attach_composition_bridge_outputs(file_path)
        adapter_result = attach_spatial_relational_state(file_path)
        if isinstance(adapter_result, dict):
            adapter_log = {
                "status": adapter_result.get("status"),
                "reason": adapter_result.get("reason"),
                "composition_status": composition_result.get("status") if isinstance(composition_result, dict) else None,
                "composition_reason": composition_result.get("reason") if isinstance(composition_result, dict) else None,
                "composition_bridge_output_count": composition_result.get("bridge_output_count") if isinstance(composition_result, dict) else None,
                "composition_lineage_status": composition_result.get("lineage_status") if isinstance(composition_result, dict) else None,
                "composition_lineage_reason": composition_result.get("lineage_reason") if isinstance(composition_result, dict) else None,
                "composition_lineage_event_id": composition_result.get("lineage_event_id") if isinstance(composition_result, dict) else None,
            }
    except Exception:
        adapter_log = {"status": "error", "reason": "adapter_exception"}

    # Ensure the item appears in TemporaryQueue for toggling decisions
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = safe_join(base_dir, "TemporaryQueue")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = safe_join(base_dir, os.path.join("TemporaryQueue", f"{data_id_s}.json"))
        if not os.path.exists(tmp_path):
            if os.path.exists(file_path):
                shutil.copy(file_path, tmp_path)
            else:
                with open(tmp_path, 'w', encoding='utf-8') as tf:
                    json.dump({"id": data_id, "content": content, "category": category}, tf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Procedural matching plan (optional extension)
    objectives = get_objectives_by_label("measurement")

    # Focus/concentration snapshot for this cycle (deterministic, non-global).
    try:
        from module_focus import compute_focus_state
        focus_state = compute_focus_state(objectives)
    except Exception:
        focus_state = None

    # Optionally persist focus snapshot + objective links into the semantic record.
    try:
        if isinstance(focus_state, dict) and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            rs = rec.get('relational_state')
            if not isinstance(rs, dict):
                rs = {}
                rec['relational_state'] = rs
            rs.setdefault('entities', [])
            rs.setdefault('relations', [])
            rs.setdefault('constraints', [])
            rs.setdefault('objective_links', [])
            rs.setdefault('spatial_measurement', None)
            rs.setdefault('conceptual_measurement', None)
            rs.setdefault('decision_trace', {})
            rs.setdefault('focus_snapshot', None)
            rs.setdefault('description', None)
            rs.setdefault('derived', {})

            rs['focus_snapshot'] = focus_state

            # Merge/dedupe objective_links by objective_id.
            links = rs.get('objective_links')
            if not isinstance(links, list):
                links = []
                rs['objective_links'] = links
            existing = {l.get('objective_id') for l in links if isinstance(l, dict)}
            for ao in (focus_state.get('active_objectives') or []):
                if not isinstance(ao, dict):
                    continue
                oid = ao.get('objective_id')
                if not isinstance(oid, str) or not oid or oid in existing:
                    continue
                links.append({
                    'objective_id': oid,
                    'relevance': float(ao.get('weight', 0.5)) if ao.get('weight') is not None else 0.5,
                    'reason': 'focus_active',
                    'evidence': []
                })
                existing.add(oid)

            from module_storage import _atomic_write_json
            _atomic_write_json(file_path, rec)
    except Exception:
        pass
    plan = procedural_match(objectives, ["search"])

    # Optional: conceptual measurement (semantic/procedural) mapped into relational_state.
    # This is gated by config.json > measurement_migration.enable and is non-fatal.
    try:
        cfg = _load_config() or {}
        mig = cfg.get("measurement_migration", {}) if isinstance(cfg, dict) else {}
        if mig.get("enable") and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            from module_concept_measure import (
                measure_conceptual_content,
                attach_conceptual_measurement_to_relational_state,
            )
            cm = measure_conceptual_content(rec, objectives or [], now_ts=fixed_ts)
            rec = attach_conceptual_measurement_to_relational_state(rec, cm)
            from module_storage import _atomic_write_json
            _atomic_write_json(file_path, rec)
    except Exception:
        pass

    # Derive deterministic graph snapshot for downstream metrics when data exists.
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as fh:
                rec_graph = json.load(fh)
            rs_graph = rec_graph.get("relational_state")
            tick_source = None
            for candidate in (
                cycle_id,
                rs_graph.get("cycle_id") if isinstance(rs_graph, dict) else None,
                data_id_s,
                rec_graph.get("id"),
            ):
                if isinstance(candidate, str) and candidate:
                    tick_source = candidate
                    break
            if not isinstance(tick_source, str) or not tick_source:
                tick_source = "unknown"

            snapshot = build_graph_snapshot(rs_graph or {}, tick_id=str(tick_source))
            if not isinstance(rs_graph, dict):
                rs_graph = {}
                rec_graph["relational_state"] = rs_graph
            derived = rs_graph.get("derived") if isinstance(rs_graph.get("derived"), dict) else None
            if snapshot:
                if not isinstance(derived, dict):
                    derived = {}
                    rs_graph["derived"] = derived
                snapshot_dict = snapshot.to_dict()
                existing_snapshot = derived.get("graph_snapshot") if isinstance(derived.get("graph_snapshot"), dict) else None
                existing_hash = derived.get("graph_snapshot_hash")
                existing_info = derived.get("graph_snapshot_build_info") if isinstance(derived.get("graph_snapshot_build_info"), dict) else None
                if existing_snapshot != snapshot_dict or existing_hash != snapshot.snapshot_hash or existing_info != snapshot.build_info:
                    derived["graph_snapshot"] = snapshot_dict
                    derived["graph_snapshot_hash"] = snapshot.snapshot_hash
                    derived["graph_snapshot_build_info"] = snapshot.build_info
                    from module_storage import _atomic_write_json
                    _atomic_write_json(file_path, rec_graph)
            elif isinstance(derived, dict):
                if "graph_snapshot" in derived or "graph_snapshot_hash" in derived or "graph_snapshot_build_info" in derived:
                    derived.pop("graph_snapshot", None)
                    derived.pop("graph_snapshot_hash", None)
                    derived.pop("graph_snapshot_build_info", None)
                    from module_storage import _atomic_write_json
                    _atomic_write_json(file_path, rec_graph)
    except Exception:
        pass

    # Integration snippet: run collector immediately after plan creation
    try:
        collector_msg = collect_results(plan, data_id, content)
        print(collector_msg)
    except Exception as e:
        print(f"Collector error: {e}")

    # Run relational checks
    sim_score = similarity(content, subject_id, "long_term_index", exclude_id=data_id_s)
    fam = familiarity(data_id, 1, [])
    rel_items = search_related(content)  # now actually searches
    use = usefulness(content, objectives, "current_activity")
    syn = synthesis_potential(content, subject_id, rel_items, objectives, "long_term_index")
    obj_rel = compare_against_objectives(content, objectives)
    desc = describe(content, {"subject_id": subject_id})

    # Optional: persist search & LLM snippets based on config flags
    try:
        cfg = _load_config() or {}
        persist_cfg = cfg.get("persist", {})
        if persist_cfg.get("capture_search_snippets"):
            search = search_internet(content)
            snippets = (search.get("results") or [])[:3]
            # Phase 11: evidence capture linked to claims
            with open(file_path, "r+", encoding="utf-8") as f:
                data = json.load(f)
                ev = data.setdefault("evidence", [])
                ts = _now_ts(deterministic_mode, fixed_ts)
                for s in snippets:
                    ev.append({
                        "source": search.get("provider"),
                        "snippet": s.get("snippet"),
                        "url": s.get("link"),
                        "ts": ts,
                        "linked_claims": [c.get("subject") for c in (data.get("description", {}).get("claims", [])[:1])],
                        "rating": {"relevance": 0.5, "credibility": 0.5, "objective_alignment": 0.5}
                    })
                data["search_provider"] = search.get("provider")
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
        if persist_cfg.get("capture_llm_snippets"):
            llm = query_llm(f"Briefly summarize: {content}", max_tokens=150)
            text = (llm.get("text") or "")[:1000]
            with open(file_path, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data["llm_provider"] = llm.get("provider")
                data["llm_snippet"] = text
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
    except Exception:
        pass

    # Optional: selection ranking influences decisions when objectives provide keywords.
    # Default path uses module_select (legacy heuristic). An opt-in migration can blend
    # in conceptual-measurement objective alignment as a stronger signal.
    sel_rank = []
    sel_cfg = {}
    retrieval_score = None
    retrieval_components = None
    retrieval_component_score = None
    selection_migration_sandbox = None
    try:
        cfg = _load_config() or {}
        sel_cfg = cfg.get('selection_migration', {}) if isinstance(cfg, dict) else {}

        sel_items = [{"id": data_id, "content": content}]
        sel_rank = rank_selection(sel_items, objectives)

        if isinstance(sel_cfg, dict) and bool(sel_cfg.get('enable')) and bool(sel_cfg.get('use_concept_measure', True)):
            try:
                from module_concept_measure import measure_conceptual_content

                thr = float(sel_cfg.get('objective_alignment_threshold', 0.6) or 0.6)
                boost = float(sel_cfg.get('score_boost', 0.2) or 0.2)

                now_ts = (fixed_ts if (deterministic_mode and fixed_ts) else None)
                rec_for_cm = {
                    'id': data_id,
                    'category': category,
                    'content': content,
                    'occurrence_count': 1,
                    'timestamps': [now_ts] if isinstance(now_ts, str) and now_ts else [],
                }
                cm = measure_conceptual_content(rec_for_cm, objectives or [], now_ts=now_ts)
                scores = cm.get('objective_scores') if isinstance(cm, dict) else None
                best = 0.0
                if isinstance(scores, list):
                    for row in scores:
                        if not isinstance(row, dict):
                            continue
                        try:
                            best = max(best, float(row.get('overall_score') or 0.0))
                        except Exception:
                            continue

                if isinstance(sel_rank, list) and sel_rank:
                    top = sel_rank[0]
                    try:
                        top['relevance_score'] = round(min(1.0, float(top.get('relevance_score') or 0.0) + (boost * best)), 3)
                    except Exception:
                        pass
                    try:
                        rc = top.get('reason_codes')
                        if not isinstance(rc, list):
                            rc = []
                            top['reason_codes'] = rc
                        if 'concept_measure' not in rc:
                            rc.append('concept_measure')
                    except Exception:
                        pass
                    if best >= thr:
                        top['objective_alignment'] = 'aligned'
                        try:
                            rc = top.get('reason_codes')
                            if isinstance(rc, list) and 'objective_match' not in rc:
                                rc.append('objective_match')
                        except Exception:
                            pass
            except Exception:
                pass

        # Optional: retrieval-backed score components (Think Deeper) for selection_score.
        # This is additive and default-off; it does not change decisions unless enabled.
        if isinstance(sel_cfg, dict) and bool(sel_cfg.get('enable')) and (
            bool(sel_cfg.get('use_retrieval_scores')) or bool(sel_cfg.get('use_retrieval_components'))
        ):
            try:
                from module_retrieval import (
                    _record_from_semantic_json,
                    compute_retrieval_component_score,
                    compute_retrieval_score,
                )

                # Derive objective_id from current focus snapshot when available.
                objective_id = None
                try:
                    if isinstance(focus_state, dict):
                        aos = focus_state.get('active_objectives')
                        if isinstance(aos, list) and aos:
                            ao0 = aos[0] if isinstance(aos[0], dict) else None
                            if isinstance(ao0, dict) and isinstance(ao0.get('objective_id'), str):
                                objective_id = ao0.get('objective_id')
                except Exception:
                    objective_id = None

                # Build a minimal objective_links map from focus_state weights.
                objective_links = {}
                try:
                    if isinstance(focus_state, dict):
                        aos = focus_state.get('active_objectives')
                        if isinstance(aos, list):
                            for ao in aos:
                                if not isinstance(ao, dict):
                                    continue
                                oid = ao.get('objective_id')
                                if not isinstance(oid, str) or not oid:
                                    continue
                                try:
                                    w = float(ao.get('weight', 0.5))
                                except Exception:
                                    w = 0.5
                                if w < 0.0:
                                    w = 0.0
                                if w > 1.0:
                                    w = 1.0
                                objective_links[oid] = w
                except Exception:
                    objective_links = {}

                rrec = {}
                readiness_record = {}
                try:
                    if isinstance(file_path, str) and file_path and os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            raw_record = json.load(f)
                        if isinstance(raw_record, dict):
                            readiness_record = dict(raw_record)
                        existing_record = _record_from_semantic_json(file_path)
                        if isinstance(existing_record, dict):
                            rrec = dict(existing_record)
                except Exception:
                    rrec = {}
                    readiness_record = {}

                try:
                    readiness_verdict = _build_learning_readiness_verdict_for_record(readiness_record)
                except Exception:
                    readiness_verdict = None
                try:
                    sandbox_settings = dict(sel_cfg)
                    if not bool(sandbox_settings.get('use_retrieval_components')):
                        sandbox_settings = dict(sandbox_settings)
                        sandbox_settings.pop('sandbox_activation', None)
                    selection_migration_sandbox = _build_selection_migration_sandbox_report(sandbox_settings, readiness_verdict)
                except Exception:
                    selection_migration_sandbox = None
                sandbox_active = bool(
                    isinstance(selection_migration_sandbox, dict) and selection_migration_sandbox.get('active')
                )

                existing_links = rrec.get('objective_links') if isinstance(rrec.get('objective_links'), dict) else {}
                merged_links = dict(existing_links) if isinstance(existing_links, dict) else {}
                for key, value in objective_links.items():
                    try:
                        merged_links[str(key)] = max(float(merged_links.get(str(key)) or 0.0), float(value))
                    except Exception:
                        continue

                rrec['record_id'] = data_id
                rrec['objective_links'] = merged_links
                # For single-record selection, recurrence is only used when already present on the semantic record.
                if 'recurrence' not in rrec:
                    rrec['recurrence'] = 0.0
                q = {
                    'target_ids': [data_id],
                    'objective_id': objective_id,
                    'deterministic_mode': bool(deterministic_mode),
                }
                rs = compute_retrieval_score(rrec, q)
                rscore = float(rs.get('score') or 0.0)
                rcomp = rs.get('components') if isinstance(rs, dict) else None
                retrieval_score = float(rscore)
                retrieval_components = dict(rcomp) if isinstance(rcomp, dict) else None
                retrieval_component_score = None

                # Optional: compute an explicit component score for policy inputs.
                if isinstance(sel_cfg, dict) and bool(sel_cfg.get('use_retrieval_components')) and isinstance(retrieval_components, dict):
                    weights = sel_cfg.get('retrieval_component_weights') if isinstance(sel_cfg, dict) else None
                    comp_score = compute_retrieval_component_score(retrieval_components, weights)
                    retrieval_component_score = _clamp01(float(comp_score))

                if isinstance(sel_rank, list) and sel_rank:
                    top = sel_rank[0]
                    try:
                        prev = float(top.get('relevance_score') or 0.0)
                    except Exception:
                        prev = 0.0
                    try:
                        top['relevance_score'] = round(max(prev, rscore), 3)
                    except Exception:
                        pass
                    try:
                        rc = top.get('reason_codes')
                        if not isinstance(rc, list):
                            rc = []
                            top['reason_codes'] = rc
                        if 'retrieval_score' not in rc:
                            rc.append('retrieval_score')
                    except Exception:
                        pass

                    # Optionally upgrade objective_alignment based on retrieval objective component.
                    try:
                        thr = float(sel_cfg.get('retrieval_objective_alignment_threshold', 0.6) or 0.6)
                    except Exception:
                        thr = 0.6
                    obj_comp = 0.0
                    if isinstance(rcomp, dict):
                        try:
                            obj_comp = float(rcomp.get('objective') or 0.0)
                        except Exception:
                            obj_comp = 0.0
                    if obj_comp >= thr:
                        top['objective_alignment'] = 'aligned'
                        try:
                            rc = top.get('reason_codes')
                            if isinstance(rc, list) and 'objective_match' not in rc:
                                rc.append('objective_match')
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        sel_rank = []

    # Collector logic
    relation_labels = []
    if sim_score >= 0.8: relation_labels.append("match")
    if fam["recurs"] or fam["has_prior_useful_labels"]: relation_labels.append("familiar")
    if rel_items: relation_labels.append("related")
    if use == "useful_now": relation_labels.append("useful")
    if syn: relation_labels.append("synthesis_value")
    if obj_rel == "aligned":
        relation_labels.append("beneficial")
    elif obj_rel == "conflict":
        relation_labels.append("detrimental")

    # Boost labels if selection ranking aligns with objectives
    try:
        top = sel_rank[0] if isinstance(sel_rank, list) and sel_rank else None
        if top and top.get("objective_alignment") == "aligned":
            if "objective_match" in (top.get("reason_codes") or []):
                if "beneficial" not in relation_labels:
                    relation_labels.append("beneficial")
    except Exception:
        pass

    # Phase 9: measurement report drives decisions
    try:
        mrep = measure_information(file_path, threshold=1.0, objectives=objectives, focus_state=focus_state)
    except Exception:
        mrep = {}

    # Canonicalize usefulness from measurement report to avoid divergence between
    # cycle-level signals and collector module_measure outputs.
    try:
        m_use = (mrep.get('usefulness_signal') if isinstance(mrep, dict) else None)
        if m_use in ('useful_now', 'useful_later', 'not_useful'):
            use = m_use
    except Exception:
        pass

    # Keep labels consistent with canonical usefulness.
    try:
        if use == 'useful_now':
            if 'useful' not in relation_labels:
                relation_labels.append('useful')
        else:
            if 'useful' in relation_labels:
                relation_labels = [x for x in relation_labels if x != 'useful']
    except Exception:
        pass
    # Arbiter: resolve contradictions
    conflicts = []
    if obj_rel == "conflict" or mrep.get('contradiction_signal'):
        conflicts.append({"type": "objective_conflict", "severity": 0.7})

    # Deterministic reasoning operators: constraints, contradictions, proposed actions.
    constraint_report = None
    contradiction_report = None
    proposed_actions = None
    scene_validation_summary = None
    try:
        from module_reasoning import check_constraints, detect_contradictions, propose_actions, summarize_scene_validation_outcomes
        _rec_for_reasoning = None
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                _rec_for_reasoning = json.load(f)
        _rs = _rec_for_reasoning.get('relational_state') if isinstance(_rec_for_reasoning, dict) else None
        if isinstance(_rs, dict):
            constraint_report = check_constraints(_rs)
            contradiction_report = detect_contradictions(_rs)
            scene_validation_summary = summarize_scene_validation_outcomes(_rs, constraint_report)
            proposed_actions = propose_actions(_rs, {
                'similarity': sim_score,
                'usefulness': use,
                'synthesis': syn,
                'objective_relation': obj_rel
            })

            # Promote hard constraint violations into conflicts/policy decisions.
            if isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'):
                vcount = len(constraint_report.get('violations') or [])
                conflicts.append({
                    'type': 'hard_constraint_violation',
                    'severity': 1.0,
                    'details': {'violations': vcount}
                })

            # Promote relation contradictions into conflicts as well.
            if isinstance(contradiction_report, dict) and (contradiction_report.get('has_contradiction') or contradiction_report.get('contradiction')):
                ccount = len(contradiction_report.get('contradictions') or [])
                conflicts.append({
                    'type': 'relation_contradiction',
                    'severity': 1.0,
                    'details': {'contradictions': ccount}
                })

            # Merge proposed actions into measurement report (non-breaking).
            if isinstance(proposed_actions, dict) and isinstance(mrep, dict):
                pa_actions = proposed_actions.get('recommended_actions') or []
                if isinstance(pa_actions, list):
                    cur = mrep.get('recommended_actions')
                    if not isinstance(cur, list):
                        cur = []
                    merged = list(cur)
                    for a in pa_actions:
                        if isinstance(a, str) and a not in merged:
                            merged.append(a)
                    mrep['recommended_actions'] = merged
                pa_dec = proposed_actions.get('decisive_recommendation')
                if isinstance(pa_dec, str) and pa_dec:
                    mrep['decisive_recommendation'] = pa_dec
    except Exception:
        constraint_report = None
        contradiction_report = None
        proposed_actions = None
    
    # policy: detrimental overrides beneficial
    decisive = mrep.get('decisive_recommendation')
    accepted_actions = []
    rejected_actions = []
    # policy: detrimental overrides beneficial
    decisive = mrep.get('decisive_recommendation')
    if "detrimental" in relation_labels:
        rejected_actions.extend(["activate", "synthesize"])
        accepted_actions.append("quarantine")
        arbiter_rationale = "Detrimental label present; quarantine item"
    else:
        meas_recs = mrep.get('recommended_actions', [])
        # honor decisive recommendation first, then fall back
        if decisive == 'contradiction_resolve' or 'contradiction_resolve' in meas_recs:
            accepted_actions.append("hold")
            arbiter_rationale = "Measurement recommends contradiction resolution; hold"
        elif decisive == 'synthesis' or any(lbl in relation_labels for lbl in ["beneficial","synthesis_value","useful"]) or ('synthesis' in meas_recs):
            accepted_actions.append("activate")
            arbiter_rationale = "Beneficial/useful/synthesis signal; activate"
        elif decisive == 'review' or any(lbl in relation_labels for lbl in ["match","related","familiar"]):
            accepted_actions.append("hold")
            arbiter_rationale = "Related/match/familiar; hold for review"
        else:
            accepted_actions.append("hold")
            arbiter_rationale = "Default hold"

    # Atomic commit rule: apply decisions after arbiter using policy
    from module_toggle import decide_toggle

    base_selection_score = (sel_rank[0].get('relevance_score') if (isinstance(sel_rank, list) and sel_rank) else 0.0)
    try:
        base_selection_score = float(base_selection_score or 0.0)
    except Exception:
        base_selection_score = 0.0

    policy_selection_score = float(base_selection_score)
    # Optional: blend retrieval component score into policy selection score.
    if retrieval_component_score is not None and isinstance(selection_migration_sandbox, dict) and bool(selection_migration_sandbox.get('active')):
        try:
            comp_weight = float(sel_cfg.get('retrieval_component_weight', 0.0) or 0.0) if isinstance(sel_cfg, dict) else 0.0
        except Exception:
            comp_weight = 0.0
        if comp_weight < 0.0:
            comp_weight = 0.0
        if comp_weight > 1.0:
            comp_weight = 1.0
        if comp_weight > 0.0:
            policy_selection_score = _clamp01((1.0 - comp_weight) * policy_selection_score + comp_weight * float(retrieval_component_score))

    # Optional: apply bounded EVoI adjustment to policy selection score.
    want_evoi = None
    want_evoi_weight = None
    want_evoi_why = None
    try:
        cfg = _load_config() or {}
        want_cfg = cfg.get('want_migration', {}) if isinstance(cfg, dict) else {}
        if isinstance(want_cfg, dict) and bool(want_cfg.get('enable')) and bool(want_cfg.get('use_evoi')) and os.path.exists(file_path):
            from module_want import compute_measurement_gap, compute_evoi_with_why
            with open(file_path, 'r', encoding='utf-8') as f:
                rec_for_evoi = json.load(f)
            gap = compute_measurement_gap(data_id=data_id, record=rec_for_evoi)
            try:
                delta = float(gap.get('delta') or 0.0)
            except Exception:
                delta = 0.0
            if delta < 0.0:
                delta = 0.0
            if delta > 1.0:
                delta = 1.0
            cur = {'value': float(delta), 'variance': float(delta * delta), 'provenance': {'id': str(data_id), 'source': 'measurement_gap'}}
            imp_scale = float(want_cfg.get('evoi_improved_variance_scale', 0.25) or 0.25) if isinstance(want_cfg, dict) else 0.25
            if imp_scale < 0.0:
                imp_scale = 0.0
            if imp_scale > 1.0:
                imp_scale = 1.0
            improved = {'value': float(max(0.0, delta * 0.5)), 'variance': float(delta * delta * imp_scale), 'provenance': {'id': str(data_id), 'source': 'measurement_gap'}}
            n_samples = int(want_cfg.get('evoi_samples', 128) or 128) if isinstance(want_cfg, dict) else 128
            if n_samples <= 0:
                n_samples = 128
            activity = str(want_cfg.get('evoi_activity', 'measure')) if isinstance(want_cfg, dict) else 'measure'
            base_costs = want_cfg.get('evoi_costs') if isinstance(want_cfg, dict) else None
            evoi_out = compute_evoi_with_why(current=cur, improved=improved, baseline=0.0, activity=activity, target_ids=[str(data_id)], base_costs=base_costs, n_samples=n_samples)
            try:
                want_evoi = float(evoi_out.get('evoi') or 0.0)
            except Exception:
                want_evoi = 0.0
            want_evoi_why = evoi_out.get('why_vector') if isinstance(evoi_out, dict) else None
            try:
                want_evoi_weight = float(want_cfg.get('evoi_weight', 0.0) or 0.0)
            except Exception:
                want_evoi_weight = 0.0
            if want_evoi_weight < 0.0:
                want_evoi_weight = 0.0
            if want_evoi_weight > 1.0:
                want_evoi_weight = 1.0
            try:
                evoi_cap = float(want_cfg.get('evoi_cap', 0.0) or 0.0)
            except Exception:
                evoi_cap = 0.0
            if evoi_cap < 0.0:
                evoi_cap = 0.0
            if evoi_cap > 1.0:
                evoi_cap = 1.0
            if want_evoi is not None and want_evoi_weight and evoi_cap:
                evoi_norm = float(want_evoi)
                if evoi_norm > 1.0:
                    evoi_norm = 1.0
                if evoi_norm < -1.0:
                    evoi_norm = -1.0
                delta = evoi_norm * float(want_evoi_weight)
                if delta > evoi_cap:
                    delta = evoi_cap
                if delta < -evoi_cap:
                    delta = -evoi_cap
                policy_selection_score = _clamp01(float(policy_selection_score) + float(delta))
    except Exception:
        want_evoi = want_evoi

    policy_inputs = {
        'usefulness': use,
        'contradiction': bool(mrep.get('decisive_recommendation') == 'contradiction_resolve' or any(c.get('severity',0)>0.5 for c in conflicts)),
        'description_maturity': 'stable' if (desc.get('claims')) else 'unknown',
        'selection_score': float(policy_selection_score),
        'selection_score_base': float(base_selection_score),
        'retrieval_score': (float(retrieval_score) if retrieval_score is not None else None),
        'retrieval_components': (dict(retrieval_components) if isinstance(retrieval_components, dict) else None),
        'retrieval_component_score': (float(retrieval_component_score) if retrieval_component_score is not None else None),
        'want_evoi': (float(want_evoi) if want_evoi is not None else None),
        'want_evoi_weight': (float(want_evoi_weight) if want_evoi_weight is not None else None),
        'similarity': sim_score,
        'beneficial_and_synthesis': ((('beneficial' in relation_labels) and ('synthesis_value' in relation_labels))),
        'objective_alignment': ((sel_rank[0].get('objective_alignment') if (isinstance(sel_rank, list) and sel_rank) else 'unknown'))
    }

    soft_influence_info = None
    try:
        cfg = _load_config() or {}
        om_cfg = cfg.get('orchestration_migration', {}) if isinstance(cfg, dict) else {}
        si = om_cfg.get('soft_influence') if isinstance(om_cfg, dict) else None
        if isinstance(si, dict) and bool(si.get('enabled')):
            try:
                scale = float(si.get('scale', 0.1) or 0.1)
            except Exception:
                scale = 0.1
            try:
                max_delta = float(si.get('max_delta', 0.05) or 0.05)
            except Exception:
                max_delta = 0.05
            try:
                prevent_flip = bool(si.get('prevent_space_flip', True))
            except Exception:
                prevent_flip = True

            prev_vok = None
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        _rec_tmp = json.load(f)
                    _dt_tmp = (((_rec_tmp.get('relational_state') or {}).get('decision_trace') or {}))
                    _co = _dt_tmp.get('cycle_outcomes')
                    if isinstance(_co, dict):
                        prev_vok = _co.get('verifier_ok_rate')
            except Exception:
                prev_vok = None

            vok = None
            try:
                if prev_vok is not None:
                    vok = float(prev_vok)
            except Exception:
                vok = None

            delta = 0.0
            if vok is not None:
                try:
                    delta = (float(vok) - 0.5) * float(scale)
                except Exception:
                    delta = 0.0
                if delta > float(max_delta):
                    delta = float(max_delta)
                if delta < -float(max_delta):
                    delta = -float(max_delta)

            adjusted = _clamp01(float(policy_selection_score) + float(delta))

            policy_inputs_adj = dict(policy_inputs)
            policy_inputs_adj['selection_score'] = float(adjusted)

            base_space, base_just = decide_toggle(policy_inputs)
            adj_space, adj_just = decide_toggle(policy_inputs_adj)

            used_space = adj_space
            used_just = adj_just
            prevented = False
            if prevent_flip and (str(base_space) != str(adj_space)):
                used_space = base_space
                used_just = base_just
                prevented = True

            soft_influence_info = {
                'enabled': True,
                'verifier_ok_rate_prev': vok,
                'selection_score_base': round(float(policy_selection_score), 6),
                'selection_score_delta': round(float(delta), 6),
                'selection_score_adjusted': round(float(adjusted), 6),
                'target_space_base': str(base_space),
                'target_space_adjusted': str(adj_space),
                'target_space_final': str(used_space),
                'prevented_space_flip': bool(prevented),
            }

            target_space, justification = used_space, used_just
        else:
            target_space, justification = decide_toggle(policy_inputs)
    except Exception:
        target_space, justification = decide_toggle(policy_inputs)

    print(move(data_id_s, "TemporaryQueue", target_space, policy_rule_id=justification.get('policy_rule_id'), reason=justification.get('reason')))
    # Re-check existence before scheduling
    if target_space == 'ActiveSpace':
        if os.path.exists(file_path):
            print(schedule_synthesis(file_path, minutes_from_now=5))
        else:
            print(f"Semantic file missing for {data_id}; skipping synthesis schedule")
    # Phase 16: try procedure match for follow-up steps
    try:
        from module_tools import match_procedure
        mp = match_procedure(sim_score, use, any(c.get('severity',0)>0.5 for c in conflicts))
        # fallback heuristic: match template when similarity high and content hints usefulness
        if not mp and (sim_score >= 0.8) and ('useful' in str(content).lower()):
            tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LongTermStore', 'Procedural', 'procedure_template.json')
            if os.path.exists(tpl_path):
                with open(tpl_path, 'r', encoding='utf-8') as tf:
                    p = json.load(tf)
                mp = {"procedure": p, "path": tpl_path}
        if mp:
            # record matched procedure and increment success tracking
            with open(file_path, 'r+', encoding='utf-8') as f:
                rec = json.load(f)
                proc_ts = _now_ts(deterministic_mode, fixed_ts)
                rec.setdefault('matched_procedures', []).append({'id': mp['procedure'].get('id'), 'ts': proc_ts})
                f.seek(0)
                json.dump(rec, f, ensure_ascii=False, indent=2)
                f.truncate()
            # update procedure record refinement
            try:
                p = mp['procedure']
                p['last_used_ts'] = proc_ts
                # naive success_rate bump for demonstration
                p['success_rate'] = float(p.get('success_rate', 0.0)) + 0.05
                with open(mp['path'], 'w', encoding='utf-8') as pf:
                    json.dump(p, pf, ensure_ascii=False, indent=2)
            except Exception:
                pass
    except Exception:
        pass

    # Phase 15: reason chain construction + counterexample attempt
    hard_violation = bool(isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'))
    rel_contra = bool(isinstance(contradiction_report, dict) and (contradiction_report.get('has_contradiction') or contradiction_report.get('contradiction')))

    reason_chain = [{
        'premises': [
            {'similarity>=0.8': sim_score >= 0.8},
            {'useful_now': use == 'useful_now'},
            {'no_conflict': obj_rel != 'conflict'},
            {'no_hard_constraint_violation': (not hard_violation)},
            {'no_relation_contradiction': (not rel_contra)},
            {'proposed_decisive': (proposed_actions.get('decisive_recommendation') if isinstance(proposed_actions, dict) else None)}
        ],
        'inference_rule': 'AND→activate',
        'conclusion': 'activate' if target_space == 'ActiveSpace' else 'hold',
        'action': 'schedule_synthesis' if target_space == 'ActiveSpace' else 'review'
    }]

    # Copilot example alignment: when hard violation or relation contradiction exists,
    # add a leading rule explaining why the system chose contradiction_resolve/hold.
    if hard_violation or rel_contra or (isinstance(mrep, dict) and mrep.get('decisive_recommendation') == 'contradiction_resolve'):
        reason_chain.insert(0, {
            'premises': [
                {'hard_violation': hard_violation},
                {'contradiction': rel_contra or bool(obj_rel == 'conflict')},
                {'similarity>=0.8': sim_score >= 0.8},
                {'useful_now': use == 'useful_now'}
            ],
            'inference_rule': 'hard_violation OR contradiction → contradiction_resolve',
            'conclusion': 'contradiction_resolve',
            'action': 'hold'
        })
    # Counterexample attempt: if conflicts present, mark provisional
    provisional = any(c.get('severity', 0) > 0.5 for c in conflicts)
    if provisional:
        reason_chain[0]['conclusion'] = reason_chain[0]['conclusion'] + '_provisional'
        # schedule evidence gather
        try:
            from module_scheduler import schedule_task
            schedule_task(file_path, 'evidence_gather', 'high', [data_id], 'counterexample resolution')
        except Exception:
            pass

    # Awareness (keep original prints)
    print(trigger_information_seeking_if(1, sim_score, rel_items, syn))
    plan_obj = None
    try:
        cfg = _load_config() or {}
        want_cfg = cfg.get('want_migration', {}) if isinstance(cfg, dict) else {}
        if want_cfg.get('enable') and os.path.exists(file_path):
            from module_want import awareness_plan_from_record
            with open(file_path, 'r', encoding='utf-8') as f:
                rec_for_want = json.load(f)
            # Seed synthesis signal into decision_trace.signals (if missing) so module_want can read it deterministically.
            try:
                rs_tmp = rec_for_want.get('relational_state')
                if not isinstance(rs_tmp, dict):
                    rs_tmp = {}
                    rec_for_want['relational_state'] = rs_tmp
                dt_tmp = rs_tmp.get('decision_trace')
                if not isinstance(dt_tmp, dict):
                    dt_tmp = {}
                    rs_tmp['decision_trace'] = dt_tmp
                sig_tmp = dt_tmp.get('signals')
                if not isinstance(sig_tmp, dict):
                    sig_tmp = {}
                    dt_tmp['signals'] = sig_tmp
                sig_tmp.setdefault('synthesis', float(syn) if syn is not None else 0.0)
            except Exception:
                pass
            plan_obj = awareness_plan_from_record(
                data_id=data_id,
                record=rec_for_want,
                objectives=objectives,
                min_strength=float(want_cfg.get('min_strength', 0.35) or 0.35),
                max_wants=int(want_cfg.get('max_wants', 5) or 5),
            )
        else:
            plan_obj = awareness_plan(data_id, {
                'repeat': 1,
                'similarity': sim_score,
                'contradiction': any(c.get('severity',0)>0.5 for c in conflicts),
                'usefulness': use
            }, objectives)
    except Exception:
        plan_obj = awareness_plan(data_id, {
            'repeat': 1,
            'similarity': sim_score,
            'contradiction': any(c.get('severity',0)>0.5 for c in conflicts),
            'usefulness': use
        }, objectives)
    print(validate_response(data_id))

    # Schedule review (only if not activated decisively)
    if target_space != 'ActiveSpace':
        minutes = 10
        try:
            if obj_rel == 'conflict':
                minutes = 1
            elif obj_rel == 'aligned':
                minutes = 5
        except Exception:
            pass
        print(flag_record(file_path, "review", minutes_from_now=minutes))

    # Log with JSON plan
    # Persist single cycle_record
    cycle_record = {
        "cycle_id": cycle_id,
        "cycle_ts": fixed_ts if deterministic_mode and fixed_ts else None,
        "data_id": data_id,
        "inputs": {"content": content, "category": category},
        "signals": {
            "similarity": sim_score,
            "usefulness": use,
            "synthesis": syn,
            "objective_relation": obj_rel
        },
        "signals_provenance": {
            "similarity": "module_tools.similarity",
            "usefulness": "module_measure.usefulness_signal",
            "synthesis": "module_tools.synthesis_potential",
            "objective_relation": "module_tools.compare_against_objectives"
        },
        "description": desc,
        "relation_labels": relation_labels,
        "decisive_recommendation": mrep.get('decisive_recommendation') if isinstance(mrep, dict) else None,
        "arbiter": {
            "accepted_actions": accepted_actions,
            "rejected_actions": rejected_actions,
            "conflicts": conflicts,
            "rationale": arbiter_rationale
        },
        "spatial_adapter": adapter_log,
        "focus_state": focus_state,
        "reason_chain": reason_chain,
        "awareness_plan": plan_obj
    }
    set_activity("relational_measure", json.dumps(cycle_record))
    persist_activity()

    # Also update LongTermStore/ActiveSpace/activity.json with cycles and last_cycle_ts
    try:
        lt_active = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LongTermStore', 'ActiveSpace', 'activity.json')
        data = {}
        if os.path.exists(lt_active):
            with open(lt_active, 'r', encoding='utf-8') as f:
                data = json.load(f)
        cycles = data.get('cycles') or []
        cycles.append(cycle_record)
        data['cycles'] = cycles[-200:]
        if cycle_record.get('cycle_ts'):
            data['last_cycle_ts'] = cycle_record['cycle_ts']
        os.makedirs(os.path.dirname(lt_active), exist_ok=True)
        with open(lt_active + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(lt_active + '.tmp', lt_active)
    except Exception:
        pass

    # persist reason_chain and decision_signals to semantic record as well
    try:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            if not isinstance(rec, dict):
                raise ValueError("semantic record is not an object")
        except Exception:
            rec = {
                "id": data_id,
                "content": content,
                "occurrence_count": 1,
                "timestamps": [],
                "labels": [],
                "schema_version": "0.9",
            }

        # Persist deterministic reasoning into relational_state decision_trace.
        try:
            rs = rec.get('relational_state')
            if not isinstance(rs, dict):
                rs = {}
                rec['relational_state'] = rs
            rs.setdefault('entities', [])
            rs.setdefault('relations', [])
            rs.setdefault('constraints', [])
            rs.setdefault('objective_links', [])
            rs.setdefault('spatial_measurement', None)
            rs.setdefault('conceptual_measurement', None)
            rs.setdefault('focus_snapshot', None)
            if isinstance(desc, dict):
                rs['description'] = desc
            dt = rs.get('decision_trace')
            if not isinstance(dt, dict):
                dt = {}
                rs['decision_trace'] = dt
            if isinstance(constraint_report, dict):
                dt['constraints'] = constraint_report
                dt['constraints_report'] = constraint_report
            if isinstance(scene_validation_summary, dict):
                dt['scene_validation'] = scene_validation_summary
            if isinstance(contradiction_report, dict):
                dt['contradictions'] = contradiction_report
            if isinstance(proposed_actions, dict):
                dt['proposed_actions'] = proposed_actions
            # Persist want plan (if present) for downstream scheduling/retrieval.
            if isinstance(plan_obj, dict) and plan_obj.get('plan_id') and plan_obj.get('wants') is not None:
                dt['want_plan'] = plan_obj
            derived = rs.get('derived')
            if not isinstance(derived, dict):
                derived = {}
                rs['derived'] = derived
            derived['comprehension_review_summary'] = _build_comprehension_review_summary(rec)
        except Exception:
            pass

        # Mirror tiers: deterministic schedule summaries and deltas (optional).
        try:
            cfg = _load_config() or {}
            foundational_hook_summary = _build_foundational_tier_hook_summary(cfg)
            should_record_foundational_hook = bool(foundational_hook_summary)
            foundational_active_space_summary = build_foundational_active_space_reference_summary(rec)
            foundational_optional_reference_artifact = build_foundational_optional_reference_non_match_artifact(rec)
            mirror_cfg = _mirror_tier_config(cfg)
            schedule_cfg = mirror_cfg.get("schedule_mirror") if isinstance(mirror_cfg, dict) else {}
            routing = _tier_family_routing_state(
                family_id="schedule_mirror",
                family_cfg=schedule_cfg,
                passthrough_flags=["allow_advisory"],
            )
            active_tiers = routing.get("active_tiers") if isinstance(routing.get("active_tiers"), dict) else {}
            flags = routing.get("flags") if isinstance(routing.get("flags"), dict) else {}
            config_snapshot = routing.get("config_snapshot") if isinstance(routing.get("config_snapshot"), dict) else {}
            tier1_enabled = bool(active_tiers.get("tier1_enabled"))
            tier2_enabled = bool(active_tiers.get("tier2_enabled"))
            tier3_enabled = bool(active_tiers.get("tier3_enabled"))
            allow_advisory = bool(flags.get("allow_advisory"))
            should_record_audit = bool(config_snapshot)

            derived = rs.get('derived') if isinstance(rs.get('derived'), dict) else None
            if not isinstance(derived, dict):
                if not (tier1_enabled or tier2_enabled or tier3_enabled or should_record_audit or should_record_foundational_hook):
                    derived = None
                else:
                    derived = {}
                    rs['derived'] = derived

            if isinstance(derived, dict):
                if should_record_foundational_hook:
                    derived['foundational_tier_hook_summary'] = foundational_hook_summary
                    derived['foundational_active_space_reference_summary'] = foundational_active_space_summary
                    if foundational_optional_reference_artifact:
                        derived['foundational_optional_reference_non_match_artifact'] = foundational_optional_reference_artifact
                    else:
                        derived.pop('foundational_optional_reference_non_match_artifact', None)
                else:
                    derived.pop('foundational_tier_hook_summary', None)
                    derived.pop('foundational_active_space_reference_summary', None)
                    derived.pop('foundational_optional_reference_non_match_artifact', None)

            if should_record_audit and isinstance(derived, dict):
                audit_record = _build_tier_activation_audit(
                    schedule_cfg=schedule_cfg,
                    deterministic_mode=deterministic_mode,
                    fixed_ts=fixed_ts,
                    run_id=cycle_id,
                )
                derived["tier_activation_audit"] = audit_record
                derived["tier_activation_audit_hash"] = audit_record.get("audit_hash")

            prior_summary = None
            prior_summary_hash = ""
            if isinstance(derived, dict):
                prior_summary = derived.get("mirror_schedule_summary") if isinstance(derived.get("mirror_schedule_summary"), dict) else None
                prior_summary_hash = derived.get("mirror_schedule_summary_hash") if isinstance(derived.get("mirror_schedule_summary_hash"), str) else ""

            if tier1_enabled and isinstance(derived, dict):
                summary = _build_mirror_schedule_summary(
                    target_space=target_space,
                    justification=justification,
                    accepted_actions=accepted_actions,
                    rejected_actions=rejected_actions,
                    policy_inputs=policy_inputs,
                )
                summary_hash = _stable_hash(summary)
                summary["mirror_schedule_summary_hash"] = summary_hash
                derived["mirror_schedule_summary"] = summary
                derived["mirror_schedule_summary_hash"] = summary_hash
            elif isinstance(derived, dict):
                derived.pop("mirror_schedule_summary", None)
                derived.pop("mirror_schedule_summary_hash", None)
                derived.pop("mirror_schedule_delta", None)
                derived.pop("mirror_schedule_delta_hash", None)
                derived.pop("mirror_schedule_delta_noop_reason", None)
                derived.pop("mirror_schedule_tier3", None)
                derived.pop("mirror_schedule_tier3_hash", None)
                derived.pop("mirror_schedule_tier3_noop_reason", None)
                derived.pop("schedule_mirror_tier3", None)
                derived.pop("schedule_mirror_tier3_hash", None)
                derived.pop("schedule_mirror_tier3_noop_reason", None)

            if tier1_enabled and tier2_enabled and isinstance(derived, dict):
                if isinstance(prior_summary, dict) and prior_summary_hash:
                    prior_summary = dict(prior_summary)
                    prior_summary["mirror_schedule_summary_hash"] = prior_summary_hash
                    current_summary = derived.get("mirror_schedule_summary")
                    if isinstance(current_summary, dict):
                        current_summary["mirror_schedule_summary_hash"] = derived.get("mirror_schedule_summary_hash")
                        delta = _build_mirror_schedule_delta(
                            prior_summary=prior_summary,
                            current_summary=current_summary,
                        )
                        derived["mirror_schedule_delta"] = delta
                        derived["mirror_schedule_delta_hash"] = delta.get("delta_hash")
                        derived.pop("mirror_schedule_delta_noop_reason", None)
                    else:
                        derived["mirror_schedule_delta_noop_reason"] = "missing_current_summary"
                        derived.pop("mirror_schedule_delta", None)
                        derived.pop("mirror_schedule_delta_hash", None)
                else:
                    current_summary = derived.get("mirror_schedule_summary")
                    current_hash = derived.get("mirror_schedule_summary_hash")
                    if isinstance(current_summary, dict) and isinstance(current_hash, str) and current_hash:
                        prior_summary = dict(current_summary)
                        prior_summary["mirror_schedule_summary_hash"] = current_hash
                        current_summary["mirror_schedule_summary_hash"] = current_hash
                        delta = _build_mirror_schedule_delta(
                            prior_summary=prior_summary,
                            current_summary=current_summary,
                        )
                        derived["mirror_schedule_delta"] = delta
                        derived["mirror_schedule_delta_hash"] = delta.get("delta_hash")
                        derived.pop("mirror_schedule_delta_noop_reason", None)
                    else:
                        derived["mirror_schedule_delta_noop_reason"] = "missing_prior_summary"
                        derived.pop("mirror_schedule_delta", None)
                        derived.pop("mirror_schedule_delta_hash", None)
            elif isinstance(derived, dict):
                derived.pop("mirror_schedule_delta", None)
                derived.pop("mirror_schedule_delta_hash", None)
                derived.pop("mirror_schedule_delta_noop_reason", None)

            if tier1_enabled and tier2_enabled and tier3_enabled and isinstance(derived, dict):
                delta = derived.get("mirror_schedule_delta") if isinstance(derived.get("mirror_schedule_delta"), dict) else None
                delta_hash = derived.get("mirror_schedule_delta_hash") if isinstance(derived.get("mirror_schedule_delta_hash"), str) else ""
                summary = derived.get("mirror_schedule_summary") if isinstance(derived.get("mirror_schedule_summary"), dict) else None
                if isinstance(delta, dict) and delta_hash and isinstance(summary, dict):
                    tier3_payload = _build_mirror_schedule_tier3(
                        summary=summary,
                        delta=delta,
                        allow_advisory=allow_advisory,
                    )
                    derived["schedule_mirror_tier3"] = tier3_payload
                    derived["schedule_mirror_tier3_hash"] = tier3_payload.get("hash_value")
                    derived.pop("schedule_mirror_tier3_noop_reason", None)
                    derived.pop("mirror_schedule_tier3", None)
                    derived.pop("mirror_schedule_tier3_hash", None)
                    derived.pop("mirror_schedule_tier3_noop_reason", None)
                else:
                    derived["schedule_mirror_tier3_noop_reason"] = "missing_tier2_delta"
                    derived.pop("schedule_mirror_tier3", None)
                    derived.pop("schedule_mirror_tier3_hash", None)
                    derived.pop("mirror_schedule_tier3", None)
                    derived.pop("mirror_schedule_tier3_hash", None)
                    derived.pop("mirror_schedule_tier3_noop_reason", None)
            elif isinstance(derived, dict):
                derived.pop("schedule_mirror_tier3", None)
                derived.pop("schedule_mirror_tier3_hash", None)
                derived.pop("schedule_mirror_tier3_noop_reason", None)
                derived.pop("mirror_schedule_tier3", None)
                derived.pop("mirror_schedule_tier3_hash", None)
                derived.pop("mirror_schedule_tier3_noop_reason", None)

            # Best-effort telemetry events (deterministic sequence).
            try:
                from telemetry import collector as _telemetry

                seed_base = None
                if isinstance(derived, dict):
                    seed_base = derived.get("mirror_schedule_summary_hash")
                if not seed_base:
                    seed_base = prior_summary_hash or str(cycle_id or "")
                seed = 0
                if isinstance(seed_base, str) and seed_base:
                    try:
                        seed = int(seed_base[:16], 16) % 2147483647
                    except Exception:
                        seed = abs(hash(seed_base)) % 2147483647
                determinism_info = {"deterministic_mode": bool(deterministic_mode)}
                if deterministic_mode and fixed_ts:
                    determinism_info["fixed_timestamp"] = str(fixed_ts)

                if tier1_enabled and isinstance(derived, dict):
                    event = _telemetry.make_event(
                        run_id=str(cycle_id),
                        module="mirror_tier",
                        event_type="mirror_tier_evaluated",
                        seed=seed,
                        producer_version="1.0",
                        payload_ref=str(derived.get("mirror_schedule_summary_hash") or ""),
                        determinism=determinism_info,
                        extra={"tier": "schedule_mirror", "tier_level": 1},
                    )
                    _telemetry.append_event(event, timestamp_fallback=(fixed_ts if deterministic_mode and fixed_ts else None))

                if tier1_enabled and tier2_enabled and isinstance(derived, dict) and derived.get("mirror_schedule_delta_hash"):
                    event = _telemetry.make_event(
                        run_id=str(cycle_id),
                        module="mirror_tier",
                        event_type="mirror_tier_delta",
                        seed=seed,
                        producer_version="1.0",
                        payload_ref=str(derived.get("mirror_schedule_delta_hash") or ""),
                        determinism=determinism_info,
                        extra={"tier": "schedule_mirror", "tier_level": 2},
                    )
                    _telemetry.append_event(event, timestamp_fallback=(fixed_ts if deterministic_mode and fixed_ts else None))

                if tier1_enabled and tier2_enabled and tier3_enabled and isinstance(derived, dict) and derived.get("schedule_mirror_tier3_hash"):
                    event = _telemetry.make_event(
                        run_id=str(cycle_id),
                        module="mirror_tier",
                        event_type="mirror_tier_advisory",
                        seed=seed,
                        producer_version="1.0",
                        payload_ref=str(derived.get("schedule_mirror_tier3_hash") or ""),
                        determinism=determinism_info,
                        extra={"tier": "schedule_mirror", "tier_level": 3},
                    )
                    _telemetry.append_event(event, timestamp_fallback=(fixed_ts if deterministic_mode and fixed_ts else None))
            except Exception:
                pass
        except Exception:
            pass

        chains = rec.setdefault('reason_chain', [])
        chains.append(reason_chain[0])
        rec['reason_chain'] = chains[-50:]
        top_sel = (sel_rank[0] if (isinstance(sel_rank, list) and sel_rank) else {})
        hard_violation = bool(isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'))
        vio_count = int(len((constraint_report or {}).get('violations') or [])) if isinstance(constraint_report, dict) else 0
        decision_signals = {
            'selection_score': float(policy_selection_score),
            'selection_score_base': float(base_selection_score),
            'objective_alignment': top_sel.get('objective_alignment', 'unknown'),
            'similarity': float(sim_score),
            'usefulness': use,
            'beneficial_and_synthesis': ((('beneficial' in relation_labels) and ('synthesis_value' in relation_labels))),
            'contradiction': bool(mrep.get('decisive_recommendation') == 'contradiction_resolve' or any(c.get('severity', 0) > 0.5 for c in conflicts)),
            'constraint_hard_violation': hard_violation,
            'constraint_violation_count': vio_count,
            'description_maturity': ('stable' if (desc.get('claims')) else 'unknown'),
            'target_space': target_space,
            'policy_rule_id': justification.get('policy_rule_id'),
            'retrieval_score': (float(retrieval_score) if retrieval_score is not None else None),
            'retrieval_components': (dict(retrieval_components) if isinstance(retrieval_components, dict) else None),
            'retrieval_component_score': (float(retrieval_component_score) if retrieval_component_score is not None else None),
            'selection_migration_sandbox': (dict(selection_migration_sandbox) if isinstance(selection_migration_sandbox, dict) else None),
            'want_evoi': (float(want_evoi) if want_evoi is not None else None),
            'want_evoi_weight': (float(want_evoi_weight) if want_evoi_weight is not None else None),
            'want_evoi_why_vector': (list(want_evoi_why) if isinstance(want_evoi_why, list) else None),
        }
        if isinstance(soft_influence_info, dict):
            decision_signals['soft_influence'] = soft_influence_info
        rec.setdefault('decision_signals', []).append(decision_signals)
        rec['decision_signals'] = rec['decision_signals'][-100:]
        relational_state = rec.setdefault('relational_state', {})
        if not isinstance(relational_state, dict):
            relational_state = {}
            rec['relational_state'] = relational_state
        derived = relational_state.get('derived')
        if not isinstance(derived, dict):
            derived = {}
            relational_state['derived'] = derived
        cfg = _load_config() or {}
        mirror_cfg = _mirror_tier_config(cfg)
        schedule_cfg = mirror_cfg.get("schedule_mirror") if isinstance(mirror_cfg, dict) else {}
        mirror_routing = _tier_family_routing_state(
            family_id="schedule_mirror",
            family_cfg=schedule_cfg,
            passthrough_flags=["allow_advisory"],
        )
        scheduled_task_labels: List[str] = []
        if target_space == 'ActiveSpace':
            scheduled_task_labels.append('synthesis')
        if provisional:
            scheduled_task_labels.append('evidence_gather')
        derived['mirrored_parameter_review_summary'] = build_mirrored_parameter_review_summary(
            rec,
            cfg=cfg,
        )
        derived['multi_location_comprehension_review_summary'] = (
            build_multi_location_comprehension_review_summary(
                rec,
                cfg=cfg,
                mirrored_parameter_review_summary=(
                    derived.get('mirrored_parameter_review_summary')
                    if isinstance(derived.get('mirrored_parameter_review_summary'), dict)
                    else {}
                ),
            )
        )
        derived['bounded_runtime_switch_inventory'] = build_bounded_runtime_switch_inventory(
            target_space=target_space,
            justification=justification,
            mirror_routing=mirror_routing,
            mirror_summary=derived.get('mirror_schedule_summary') if isinstance(derived.get('mirror_schedule_summary'), dict) else {},
            foundational_hook_summary=(
                derived.get('foundational_tier_hook_summary')
                if isinstance(derived.get('foundational_tier_hook_summary'), dict)
                else {}
            ),
            foundational_active_space_summary=(
                derived.get('foundational_active_space_reference_summary')
                if isinstance(derived.get('foundational_active_space_reference_summary'), dict)
                else {}
            ),
            foundational_optional_reference_artifact=(
                derived.get('foundational_optional_reference_non_match_artifact')
                if isinstance(derived.get('foundational_optional_reference_non_match_artifact'), dict)
                else {}
            ),
            scheduled_task_labels=scheduled_task_labels,
        )
        derived['retained_memory_follow_through_summary'] = build_retained_memory_follow_through_summary(
            rec,
            categorized_summary=derived.get('categorized_context_summary') if isinstance(derived.get('categorized_context_summary'), dict) else {},
            comprehension_summary=derived.get('comprehension_review_summary') if isinstance(derived.get('comprehension_review_summary'), dict) else {},
            readiness_summary=_build_learning_readiness_verdict_for_record(
                rec,
                measurement_summary=(
                    derived.get('measurement_adequacy_summary')
                    if isinstance(derived.get('measurement_adequacy_summary'), dict)
                    else {}
                ),
            ),
            bounded_runtime_switch_inventory=derived.get('bounded_runtime_switch_inventory') if isinstance(derived.get('bounded_runtime_switch_inventory'), dict) else {},
        )
        derived['retained_memory_capability_measurement_summary'] = (
            dict(derived['retained_memory_follow_through_summary'].get('capability_measurement_summary'))
            if isinstance(derived['retained_memory_follow_through_summary'].get('capability_measurement_summary'), dict)
            else {}
        )
        derived['purpose_carrier_summary'] = build_purpose_carrier_summary(
            rec,
            target_space=target_space,
            justification=justification if isinstance(justification, dict) else {},
            mirror_summary=derived.get('mirror_schedule_summary') if isinstance(derived.get('mirror_schedule_summary'), dict) else {},
            foundational_hook_summary=(
                derived.get('foundational_tier_hook_summary')
                if isinstance(derived.get('foundational_tier_hook_summary'), dict)
                else {}
            ),
            foundational_active_space_summary=(
                derived.get('foundational_active_space_reference_summary')
                if isinstance(derived.get('foundational_active_space_reference_summary'), dict)
                else {}
            ),
            foundational_optional_reference_artifact=(
                derived.get('foundational_optional_reference_non_match_artifact')
                if isinstance(derived.get('foundational_optional_reference_non_match_artifact'), dict)
                else {}
            ),
            bounded_runtime_switch_inventory=(
                derived.get('bounded_runtime_switch_inventory')
                if isinstance(derived.get('bounded_runtime_switch_inventory'), dict)
                else {}
            ),
        )
        _atomic_write_json(file_path, rec)
    except Exception:
        pass

    # Optional orchestration migration: run Want -> ActivityQueue cycle for observability.
    # Default-off, bounded trace, and does not change selection/toggle decisions.
    try:
        cfg = _load_config() or {}
        om_cfg = cfg.get('orchestration_migration', {}) if isinstance(cfg, dict) else {}
        if isinstance(om_cfg, dict) and bool(om_cfg.get('enable')) and os.path.exists(file_path):
            try:
                steps = int(om_cfg.get('max_steps', 1) or 1)
            except Exception:
                steps = 1
            if steps < 1:
                steps = 1
            if steps > 10:
                steps = 10

            try:
                trace_cap = int(om_cfg.get('trace_cap', 20) or 20)
            except Exception:
                trace_cap = 20
            if trace_cap < 1:
                trace_cap = 1
            if trace_cap > 200:
                trace_cap = 200

            include_debug = True
            try:
                include_debug = bool(om_cfg.get('include_debug', True))
            except Exception:
                include_debug = True

            include_advisory = True
            try:
                include_advisory = bool(om_cfg.get('include_advisory', True))
            except Exception:
                include_advisory = True

            include_activity_queue_trace = False
            try:
                include_activity_queue_trace = bool(om_cfg.get('include_activity_queue_trace', False))
            except Exception:
                include_activity_queue_trace = False

            include_cycle_artifact = True
            try:
                include_cycle_artifact = bool(om_cfg.get('include_cycle_artifact', True))
            except Exception:
                include_cycle_artifact = True

            objm_cfg = None
            try:
                objm_cfg = om_cfg.get('objective_influence_metrics') if isinstance(om_cfg, dict) else None
            except Exception:
                objm_cfg = None
            include_objective_metrics = False
            try:
                include_objective_metrics = bool(isinstance(objm_cfg, dict) and objm_cfg.get('enabled'))
            except Exception:
                include_objective_metrics = False
            try:
                objm_top_k = int((objm_cfg or {}).get('top_k', 5) or 5)
            except Exception:
                objm_top_k = 5
            if objm_top_k < 1:
                objm_top_k = 1
            if objm_top_k > 25:
                objm_top_k = 25
            compute_retrieval_diff = True
            try:
                compute_retrieval_diff = bool((objm_cfg or {}).get('compute_retrieval_diff', True))
            except Exception:
                compute_retrieval_diff = True

            with open(file_path, 'r', encoding='utf-8') as f:
                _rec = json.load(f)

            # Build an awareness plan (prefer already computed plan_obj).
            plan = None
            if isinstance(plan_obj, dict) and plan_obj.get('plan_id') and plan_obj.get('wants') is not None:
                plan = plan_obj
            else:
                try:
                    from module_want import compute_awareness_plan

                    plan = compute_awareness_plan(
                        objectives=(objectives or []),
                        gaps=[],
                        errors=[],
                        opportunities=[],
                        plan_id=f"plan_rm_{data_id_s}",
                        min_strength=0.35,
                        max_wants=5,
                    )
                except Exception:
                    plan = {'plan_id': f"plan_rm_{data_id_s}", 'wants': [], 'suggested_activities': []}

            # Ensure at least one deterministic want so the cycle produces artifacts.
            wants = plan.get('wants') if isinstance(plan, dict) else None
            if not isinstance(wants, list) or not wants:
                if not isinstance(plan, dict):
                    plan = {'plan_id': f"plan_rm_{data_id_s}", 'wants': [], 'suggested_activities': []}
                plan['wants'] = [
                    {
                        'want_type': 'want_information',
                        'targets': [str(data_id)],
                        'strength': 0.35,
                        'reasons': ['orchestration_migration_fallback'],
                    }
                ]

            injected_error_resolution = False
            need_err_for_advisory = False

            # If the current cycle indicates a decisive contradiction / hard violation,
            # inject an error-resolution want (observability-only; no decision authority).
            try:
                existing = set()
                wants2 = plan.get('wants') if isinstance(plan, dict) else None
                if isinstance(wants2, list):
                    for w in wants2:
                        if isinstance(w, dict) and isinstance(w.get('want_type'), str):
                            existing.add(str(w.get('want_type')))

                need_err = False
                try:
                    need_err = bool(isinstance(mrep, dict) and mrep.get('decisive_recommendation') == 'contradiction_resolve')
                except Exception:
                    need_err = False
                if not need_err:
                    try:
                        need_err = bool(isinstance(mrep, dict) and bool(mrep.get('contradiction_signal')))
                    except Exception:
                        need_err = False
                if not need_err:
                    try:
                        recs = mrep.get('recommended_actions') if isinstance(mrep, dict) else None
                        need_err = bool(isinstance(recs, list) and ('contradiction_resolve' in recs))
                    except Exception:
                        need_err = False
                if not need_err:
                    try:
                        need_err = bool(isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'))
                    except Exception:
                        need_err = False
                if not need_err:
                    try:
                        need_err = bool(isinstance(contradiction_report, dict) and (contradiction_report.get('has_contradiction') or contradiction_report.get('contradiction')))
                    except Exception:
                        need_err = False

                need_err_for_advisory = bool(need_err)

                if need_err and 'want_error_resolution' not in existing:
                    plan.setdefault('wants', [])
                    if isinstance(plan.get('wants'), list):
                        # Insert at the front so the deterministic id salt is stable and
                        # the activity priority is not accidentally lower than info wants.
                        plan['wants'].insert(
                            0,
                            {
                                'want_type': 'want_error_resolution',
                                'targets': [str(data_id)],
                                'strength': 0.9,
                                'reasons': ['orchestration_migration_contradiction'],
                            },
                        )
                        injected_error_resolution = True
            except Exception:
                pass

            # Activity modules (minimal, deterministic, file-based).
            def _om_load_store(*, limit: int = 50) -> list[dict[str, Any]]:
                try:
                    lim = int(limit) if limit is not None else 50
                except Exception:
                    lim = 50
                if lim < 0:
                    lim = 0
                if lim > 500:
                    lim = 500

                try:
                    sem_dir = resolve_path('semantic')
                except Exception:
                    return []
                if not isinstance(sem_dir, str) or not os.path.isdir(sem_dir):
                    return []

                out: list[dict[str, Any]] = []
                try:
                    names = sorted([fn for fn in os.listdir(sem_dir) if isinstance(fn, str) and fn.endswith('.json')])
                except Exception:
                    names = []
                for fn in names:
                    try:
                        path = safe_join(sem_dir, fn)
                    except Exception:
                        continue
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            rec = json.load(f)
                    except Exception:
                        continue
                    if isinstance(rec, dict):
                        out.append(rec)
                    if lim and len(out) >= lim:
                        break
                return out

            def _om_measure(activity: dict[str, Any]):
                targets = activity.get('targets') if isinstance(activity, dict) else None
                if not isinstance(targets, list):
                    return []
                out = []
                try:
                    from module_measure import measure_information
                except Exception:
                    return []
                for t in sorted([x for x in targets if isinstance(x, str) and x]):
                    try:
                        t_s = sanitize_id(t)
                    except Exception:
                        continue
                    t_path = safe_join(resolve_path(category), f"{t_s}.json")
                    if os.path.exists(t_path):
                        try:
                            out.append(measure_information(t_path, threshold=1.0, objectives=objectives, focus_state=focus_state))
                        except Exception:
                            out.append({'ok': False, 'reason': 'measure_exception', 'target': t})
                return out

            def _om_retrieve(activity: dict[str, Any]):
                targets = activity.get('targets') if isinstance(activity, dict) else None
                if not isinstance(targets, list):
                    targets = []
                try:
                    store_lim = int((om_cfg or {}).get('store_limit', 50) or 50)
                except Exception:
                    store_lim = 50
                store = _om_load_store(limit=store_lim)
                try:
                    from module_retrieval import retrieve
                except Exception:
                    return []
                objective_id = None
                try:
                    if isinstance(focus_state, dict):
                        aos = focus_state.get('active_objectives')
                        if isinstance(aos, list) and aos:
                            ao0 = aos[0] if isinstance(aos[0], dict) else None
                            if isinstance(ao0, dict) and isinstance(ao0.get('objective_id'), str):
                                objective_id = ao0.get('objective_id')
                except Exception:
                    objective_id = None
                query = {
                    'target_ids': [t for t in targets if isinstance(t, str) and t],
                    'max_results': 10,
                }
                if isinstance(objective_id, str) and objective_id:
                    query['objective_id'] = objective_id
                try:
                    return _annotate_retrieval_rows_with_categorized_context(retrieve(store, query))
                except Exception:
                    return []

            def _om_error_resolution(activity: dict[str, Any]):
                # Observability-only: exercise module_error_resolution's rollback-capable
                # resolution engine using an in-memory record snapshot.
                targets = activity.get('targets') if isinstance(activity, dict) else None
                if not isinstance(targets, list):
                    targets = []
                rid = ''
                if targets:
                    try:
                        rid = str(sorted([t for t in targets if isinstance(t, str) and t])[0])
                    except Exception:
                        rid = ''
                if not rid:
                    rid = str(data_id)

                try:
                    import datetime as _dt
                    import module_error_resolution as _er
                except Exception:
                    return {'ok': False, 'reason': 'missing_error_resolution_module'}

                # Deterministic time for task artifacts.
                det_time = 0.0
                if deterministic_mode and fixed_ts:
                    try:
                        ts = str(fixed_ts)
                        if ts.endswith('Z'):
                            ts = ts[:-1] + '+00:00'
                        dt = _dt.datetime.fromisoformat(ts)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=_dt.timezone.utc)
                        det_time = float(dt.timestamp())
                    except Exception:
                        det_time = 0.0

                # Create a synthetic mismatch so detect_error produces a report.
                measurement = {
                    'value': 1.0,
                    'source_id': 'orchestration_migration',
                    'timestamp': float(det_time),
                    'context_id': 'semantic',
                    'uncertainty': {},
                }
                record0 = {
                    'record_id': str(rid),
                    'value': 0.0,
                    'context_id': 'semantic',
                    'links': {},
                    'derived': False,
                    'inputs': [],
                    'uncertainty': {},
                    'version': 0,
                }
                rep = _er.detect_error(measurement=measurement, record=record0)
                if not isinstance(rep, dict):
                    rep = {
                        'error_type': 'mis_description',
                        'measured_value': 1.0,
                        'stored_value': 0.0,
                        'delta': 1.0,
                        'severity': 1.0,
                        'target_record_id': str(rid),
                        'confidence': 0.5,
                        'uncertainty_measured': {},
                        'uncertainty_stored': {},
                    }

                prov: list[dict[str, Any]] = []
                try:
                    rep, prov = _er.log_error_report(
                        error_report=rep,
                        provenance_log=prov,
                        deterministic_mode=bool(deterministic_mode),
                        deterministic_time=float(det_time),
                    )
                except Exception:
                    pass

                try:
                    task, prov = _er.create_resolution_task(
                        error_report=rep,
                        resolution_strategy='re_measure',
                        provenance_log=prov,
                        deterministic_mode=bool(deterministic_mode),
                        deterministic_time=float(det_time),
                    )
                except Exception:
                    task = {
                        'task_id': '',
                        'activity': 'error_resolution',
                        'target_record_id': str(rid),
                        'error_type': rep.get('error_type') or 'mis_description',
                        'resolution_strategy': 're_measure',
                        'priority': float(rep.get('severity') or 0.0),
                        'created_ts': float(det_time),
                        'status': 'pending',
                        'error_report': rep,
                        'error_event_id': str(rep.get('event_id') or ''),
                    }

                # Execute in-memory (no side effects).
                store_box = {'rec': dict(record0)}

                def _lookup(rid2: str):
                    _ = rid2
                    return dict(store_box['rec'])

                def _measure(rid2: str):
                    _ = rid2
                    return dict(measurement)

                def _update(rec: dict[str, Any]) -> None:
                    store_box['rec'] = dict(rec)

                def _relink(rec: dict[str, Any], new_context_id: str):
                    r = dict(rec)
                    r['context_id'] = str(new_context_id)
                    return r

                def _recompute(rec: dict[str, Any]):
                    return dict(rec)

                try:
                    task2, prov2 = _er.execute_resolution_task(
                        task=task,
                        record_lookup_fn=_lookup,
                        measure_fn=_measure,
                        storage_update_fn=_update,
                        relink_fn=_relink,
                        recompute_fn=_recompute,
                        provenance_log=prov,
                        deterministic_mode=bool(deterministic_mode),
                        deterministic_time=float(det_time),
                        n_samples=32,
                    )
                except Exception:
                    task2, prov2 = task, prov

                return {
                    'ok': True,
                    'task_id': str((task2 or {}).get('task_id') or ''),
                    'status': str((task2 or {}).get('status') or ''),
                    'strategy': str((task2 or {}).get('resolution_strategy') or ''),
                    'validation': (task2 or {}).get('validation') if isinstance(task2, dict) else None,
                    'provenance_events': int(len([e for e in (prov2 or []) if isinstance(e, dict)])),
                }

            def _om_synthesize(activity: dict[str, Any]):
                targets = activity.get('targets') if isinstance(activity, dict) else None
                if not isinstance(targets, list):
                    targets = []
                try:
                    store_lim = int((om_cfg or {}).get('store_limit', 50) or 50)
                except Exception:
                    store_lim = 50
                store = _om_load_store(limit=store_lim)
                try:
                    import module_reasoning as _reasoning
                except Exception:
                    return {'ok': False, 'reason': 'missing_reasoning_module'}
                opp = {'target_ids': [t for t in targets if isinstance(t, str) and t], 'coherence_gain': 0.0}
                try:
                    return _reasoning.synthesize(records=store, opportunity=opp)
                except Exception:
                    return {'ok': False, 'reason': 'synthesize_exception'}

            activity_modules: dict[str, Any] = {
                'measure': _om_measure,
                'retrieve': _om_retrieve,
                'error_resolution': _om_error_resolution,
                'synthesize': _om_synthesize,
            }

            # Prefer using the verifier module to produce deterministic artifacts.
            verifier_state = {
                'records_map': {},
                'last_measure_ts': {},
                'provenance': [],
                'verifier_cfg': {},
                'verifier_policy': {},
                'deterministic_mode': bool(deterministic_mode),
            }
            try:
                import module_verifier as _vmod

                activity_modules['__verifier__'] = _vmod
            except Exception:
                pass

            try:
                import module_activity_manager as _am

                q0 = _am.new_queue()
                if deterministic_mode:
                    q0['deterministic_mode'] = True
                q1 = _am.run_activity_cycle(
                    awareness_plan=plan,  # type: ignore[arg-type]
                    queue=q0,
                    modules=activity_modules,
                    max_steps=steps,
                    state=verifier_state,
                )
            except Exception:
                q1 = None

            completed_min: list[dict[str, Any]] = []
            if isinstance(q1, dict):
                comp = q1.get('completed')
                if isinstance(comp, list):
                    for a in comp:
                        if not isinstance(a, dict):
                            continue
                        meta = a.get('metadata') if isinstance(a.get('metadata'), dict) else {}
                        res = meta.get('result') if isinstance(meta, dict) else None
                        start_ts = None
                        end_ts = None
                        verifier_ok = None
                        if isinstance(res, dict):
                            start_ts = res.get('start_ts')
                            end_ts = res.get('end_ts')
                            ver = res.get('verification')
                            if isinstance(ver, dict):
                                verifier_ok = ver.get('ok')
                        completed_min.append(
                            {
                                'activity_id': str(a.get('activity_id') or ''),
                                'activity_type': str(a.get('activity_type') or ''),
                                'start_ts': start_ts,
                                'end_ts': end_ts,
                                'verifier_ok': verifier_ok,
                            }
                        )
            completed_min.sort(key=lambda x: (str(x.get('activity_id') or ''), str(x.get('activity_type') or '')))

            completed_types: list[str] = []
            try:
                for row in completed_min:
                    if not isinstance(row, dict):
                        continue
                    at = row.get('activity_type')
                    if isinstance(at, str) and at:
                        completed_types.append(at)
            except Exception:
                completed_types = []
            completed_type_set = set(completed_types)

            verifier_ok_total = 0
            verifier_ok_true = 0
            try:
                for row in completed_min:
                    if not isinstance(row, dict):
                        continue
                    vok = row.get('verifier_ok')
                    if vok is None:
                        continue
                    verifier_ok_total += 1
                    if vok is True:
                        verifier_ok_true += 1
            except Exception:
                verifier_ok_total = 0
                verifier_ok_true = 0
            verifier_ok_rate = None
            if verifier_ok_total > 0:
                try:
                    verifier_ok_rate = round(float(verifier_ok_true) / float(verifier_ok_total), 3)
                except Exception:
                    verifier_ok_rate = None

            next_steps: list[str] = []
            try:
                # Deterministic priority order: resolve contradictions first.
                if need_err_for_advisory and ('error_resolution' not in completed_type_set):
                    next_steps.append('run_error_resolution')
                if 'retrieve' not in completed_type_set:
                    next_steps.append('run_retrieve')
                if 'measure' not in completed_type_set:
                    next_steps.append('run_measure')
                if 'synthesize' not in completed_type_set:
                    next_steps.append('consider_synthesis')
                if 'error_resolution' in completed_type_set:
                    next_steps.append('review_error_resolution')
                if 'synthesize' in completed_type_set:
                    next_steps.append('review_synthesis')
            except Exception:
                next_steps = []
            if not next_steps:
                next_steps = ['no_action']
            next_steps = next_steps[:5]

            advisory_summary = {
                'completed_activity_types': sorted(set([t for t in completed_types if isinstance(t, str) and t]))[:20],
                'steps_executed': int(len(completed_min)),
                'verifier_ok_rate': verifier_ok_rate,
            }

            want_types: list[str] = []
            try:
                wants3 = (plan or {}).get('wants') if isinstance(plan, dict) else None
                if isinstance(wants3, list):
                    for w in wants3:
                        if not isinstance(w, dict):
                            continue
                        wt = w.get('want_type')
                        if isinstance(wt, str) and wt:
                            want_types.append(wt)
            except Exception:
                want_types = []
            want_types = want_types[:10]

            pending_types: list[str] = []
            try:
                if isinstance(q1, dict):
                    pend = q1.get('pending')
                    if isinstance(pend, list):
                        for a in pend:
                            if not isinstance(a, dict):
                                continue
                            at = a.get('activity_type')
                            if isinstance(at, str) and at:
                                pending_types.append(at)
            except Exception:
                pending_types = []
            pending_types = sorted(set(pending_types))[:20]

            trace = {
                'plan_id': str((plan or {}).get('plan_id') or ''),
                'max_steps': int(steps),
                'deterministic_mode': bool(deterministic_mode),
                'completed': completed_min,
            }
            if include_debug:
                trace['debug'] = {
                    'injected_error_resolution': bool(injected_error_resolution),
                    'want_types': want_types,
                    'pending_activity_types': pending_types,
                }
            if include_advisory:
                trace['advisory'] = {
                    'next_steps': list(next_steps),
                    'summary': advisory_summary,
                }
            if deterministic_mode and fixed_ts:
                trace['fixed_timestamp'] = fixed_ts

            rs2 = _rec.get('relational_state') if isinstance(_rec, dict) else None
            if not isinstance(rs2, dict):
                rs2 = {}
                _rec['relational_state'] = rs2
            dt2 = rs2.get('decision_trace')
            if not isinstance(dt2, dict):
                dt2 = {}
                rs2['decision_trace'] = dt2

            if include_activity_queue_trace:
                try:
                    import module_activity_manager as _am

                    dt2['activity_queue_trace'] = _am.normalize_activity_queue_trace(
                        queue=q1 if isinstance(q1, dict) else {},
                        max_items=trace_cap,
                    )
                except Exception:
                    pass

            # Phase A: persist additive advisory outputs at a stable location.
            if include_advisory:
                dt2['next_steps_from_cycle'] = list(next_steps)
                dt2['cycle_outcomes'] = advisory_summary

            # Objective-centric influence metrics (additive, deterministic, does not affect decisions).
            if include_objective_metrics:
                active_obj_ids: list[str] = []
                try:
                    if isinstance(focus_state, dict):
                        aobs = focus_state.get('active_objectives')
                        if isinstance(aobs, list):
                            for ao in aobs:
                                if not isinstance(ao, dict):
                                    continue
                                oid = ao.get('objective_id')
                                if isinstance(oid, str) and oid:
                                    active_obj_ids.append(oid)
                except Exception:
                    active_obj_ids = []
                try:
                    active_obj_ids = sorted(set(active_obj_ids))[:10]
                except Exception:
                    active_obj_ids = []

                primary_oid = active_obj_ids[0] if active_obj_ids else None

                # Retrieval influence (compare base vs objective_id query) without altering actual retrieval.
                retrieval_metrics = {
                    'computed': bool(compute_retrieval_diff),
                    'primary_objective_id': primary_oid,
                    'base_top_ids': [],
                    'objective_top_ids': [],
                    'differs': False,
                    'overlap_jaccard': None,
                }
                try:
                    if compute_retrieval_diff and primary_oid and isinstance(q1, dict):
                        store_lim = 50
                        try:
                            store_lim = int((om_cfg or {}).get('store_limit', 50) or 50)
                        except Exception:
                            store_lim = 50
                        store = _om_load_store(limit=store_lim)
                        try:
                            from module_retrieval import retrieve as _retrieve
                        except Exception:
                            _retrieve = None

                        # Base query mirrors _om_retrieve (no objective_id).
                        base_ids: list[str] = []
                        obj_ids: list[str] = []
                        if _retrieve is not None:
                            q_base = {
                                'target_ids': [t for t in (targets or []) if isinstance(t, str) and t],
                                'max_results': int(objm_top_k),
                            }
                            try:
                                rows_base = _retrieve(store, q_base)
                            except Exception:
                                rows_base = []
                            for r in rows_base or []:
                                if not isinstance(r, dict):
                                    continue
                                rid = r.get('record_id')
                                if not isinstance(rid, str) or not rid:
                                    rid = r.get('id')
                                if isinstance(rid, str) and rid:
                                    base_ids.append(rid)

                            q_obj = dict(q_base)
                            q_obj['objective_id'] = str(primary_oid)
                            try:
                                rows_obj = _retrieve(store, q_obj)
                            except Exception:
                                rows_obj = []
                            for r in rows_obj or []:
                                if not isinstance(r, dict):
                                    continue
                                rid = r.get('record_id')
                                if not isinstance(rid, str) or not rid:
                                    rid = r.get('id')
                                if isinstance(rid, str) and rid:
                                    obj_ids.append(rid)

                        base_set = set([x for x in base_ids if isinstance(x, str) and x])
                        obj_set = set([x for x in obj_ids if isinstance(x, str) and x])
                        inter = len(base_set.intersection(obj_set))
                        union = len(base_set.union(obj_set))
                        jac = None
                        if union > 0:
                            try:
                                jac = round(float(inter) / float(union), 6)
                            except Exception:
                                jac = None

                        retrieval_metrics['base_top_ids'] = sorted(base_set)[:int(objm_top_k)]
                        retrieval_metrics['objective_top_ids'] = sorted(obj_set)[:int(objm_top_k)]
                        retrieval_metrics['differs'] = bool(base_set != obj_set)
                        retrieval_metrics['overlap_jaccard'] = jac
                except Exception:
                    pass

                # Selection/scheduling influence (based on actual policy path).
                sel_mig_enabled = False
                try:
                    _cfg2 = _load_config() or {}
                    sm = _cfg2.get('selection_migration', {}) if isinstance(_cfg2, dict) else {}
                    sel_mig_enabled = bool(isinstance(sm, dict) and sm.get('enable'))
                except Exception:
                    sel_mig_enabled = False

                obj_align = None
                try:
                    obj_align = (policy_inputs.get('objective_alignment') if isinstance(policy_inputs, dict) else None)
                except Exception:
                    obj_align = None

                selection_metrics = {
                    'selection_migration_enabled': bool(sel_mig_enabled),
                    'objective_alignment': obj_align,
                    'active_objective_ids': list(active_obj_ids),
                    'objective_alignment_used_by_policy': True,  # decide_toggle reads objective_alignment
                }
                scheduling_metrics = {
                    'scheduled_synthesis': bool(target_space == 'ActiveSpace'),
                    'scheduled_for_minutes_from_now': 5 if (target_space == 'ActiveSpace') else None,
                    'objective_alignment': obj_align,
                    'active_objective_ids': list(active_obj_ids),
                }

                dt2['objective_influence_metrics'] = {
                    'schema_version': '1.0',
                    'enabled': True,
                    'active_objective_ids': list(active_obj_ids),
                    'retrieval': retrieval_metrics,
                    'selection': selection_metrics,
                    'scheduling': scheduling_metrics,
                }

            # Canonical cycle artifact (Phase C groundwork): one bounded per-cycle summary tying
            # inputs -> plan -> activities -> decision -> verification -> scheduling.
            if include_cycle_artifact:
                # Bounded retrieval pointers.
                retrieved_ids: list[str] = []
                try:
                    if isinstance(q1, dict):
                        comp2 = q1.get('completed')
                        if isinstance(comp2, list):
                            for a in comp2:
                                if not isinstance(a, dict):
                                    continue
                                if str(a.get('activity_type') or '') != 'retrieve':
                                    continue
                                meta = a.get('metadata') if isinstance(a.get('metadata'), dict) else {}
                                res2 = meta.get('result') if isinstance(meta, dict) else None
                                if isinstance(res2, dict):
                                    rows = res2.get('result')
                                    if isinstance(rows, list):
                                        for r in rows:
                                            if not isinstance(r, dict):
                                                continue
                                            rid = r.get('record_id')
                                            if not isinstance(rid, str) or not rid:
                                                rid = r.get('id')
                                            if isinstance(rid, str) and rid:
                                                retrieved_ids.append(rid)
                except Exception:
                    retrieved_ids = []
                # Keep deterministic ordering.
                try:
                    retrieved_ids = sorted(set([x for x in retrieved_ids if isinstance(x, str) and x]))[:20]
                except Exception:
                    retrieved_ids = []

                # Scheduling summary (deterministic timestamp when available).
                sched = {'synthesis': {'scheduled': bool(target_space == 'ActiveSpace'), 'minutes_from_now': 5, 'scheduled_for_ts': None}}
                if deterministic_mode and fixed_ts and target_space == 'ActiveSpace':
                    try:
                        import datetime as _dt
                        ts = str(fixed_ts)
                        if ts.endswith('Z'):
                            ts = ts[:-1] + '+00:00'
                        dt = _dt.datetime.fromisoformat(ts)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=_dt.timezone.utc)
                        dt2s = dt + _dt.timedelta(minutes=5)
                        sched['synthesis']['scheduled_for_ts'] = dt2s.isoformat().replace('+00:00', 'Z')
                    except Exception:
                        pass

                # Minimal reasoning/decision pointers.
                try:
                    decisive = (proposed_actions.get('decisive_recommendation') if isinstance(proposed_actions, dict) else None)
                except Exception:
                    decisive = None
                contra = False
                try:
                    contra = bool(isinstance(contradiction_report, dict) and (contradiction_report.get('has_contradiction') or contradiction_report.get('contradiction')))
                except Exception:
                    contra = False
                hard_vio = False
                try:
                    hard_vio = bool(isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'))
                except Exception:
                    hard_vio = False

                # Stable content hash.
                try:
                    ch = hashlib.sha256(str(content).encode('utf-8')).hexdigest()
                except Exception:
                    ch = None

                cycle_artifact = {
                    'schema_version': '1.0',
                    'cycle_id': str(cycle_id or ''),
                    'fixed_timestamp': str(fixed_ts) if (deterministic_mode and fixed_ts) else None,
                    'record_ref': {'category': str(category), 'data_id': str(data_id_s)},
                    'inputs': {
                        'subject_id': str(subject_id),
                        'content_hash': ch,
                    },
                    'plan': {
                        'plan_id': str((plan or {}).get('plan_id') or ''),
                        'want_types': list(want_types),
                        'suggested_activities': list((plan or {}).get('suggested_activities') or []) if isinstance(plan, dict) else [],
                    },
                    'activities': {
                        'completed': list(completed_min),
                        'pending_activity_types': list(pending_types),
                        'next_steps': list(next_steps),
                    },
                    'retrieval': {
                        'result_ids': list(retrieved_ids),
                        'count': int(len(retrieved_ids)),
                    },
                    'reasoning': {
                        'has_contradiction': bool(contra),
                        'has_hard_violation': bool(hard_vio),
                        'decisive_recommendation': decisive,
                    },
                    'decision': {
                        'target_space': str(target_space),
                        'policy_rule_id': justification.get('policy_rule_id') if isinstance(justification, dict) else None,
                    },
                    'verification': dict(advisory_summary),
                    'scheduling': sched,
                }

                if isinstance(soft_influence_info, dict):
                    cycle_artifact['decision']['soft_influence'] = dict(soft_influence_info)

                dt2['cycle_artifact'] = cycle_artifact
                hist = dt2.get('cycle_artifacts')
                if not isinstance(hist, list):
                    hist = []
                hist.append(cycle_artifact)
                dt2['cycle_artifacts'] = hist[-trace_cap:]
            tlist = dt2.get('activity_cycle_trace')
            if not isinstance(tlist, list):
                tlist = []
                dt2['activity_cycle_trace'] = tlist
            tlist.append(trace)
            dt2['activity_cycle_trace'] = tlist[-trace_cap:]

            from module_storage import _atomic_write_json

            _atomic_write_json(file_path, _rec)
    except Exception:
        pass

    return relation_labels


def batch_relational_measure(items):
    """Run RelationalMeasurement over a list of (data_id, content, category) tuples.
    Logs brief summaries to stdout; returns list of relation_labels.
    """
    results = []
    for tup in items:
        try:
            data_id, content, category = tup
        except Exception:
            continue
        labels = RelationalMeasurement(data_id, content, category)
        print({"data_id": data_id, "labels": labels})
        results.append(labels)
    return results

# Initialization helpers (non-invasive)
def initialize_ai_brain(seed_dir=None, objectives_dir=None):
    """Load seed knowledge and list objectives if present.

    - SeedData: LongTermStore/SeedData/*.json (semantic category)
    - Objectives: LongTermStore/Objectives/*.json
    Idempotent storage via module_storage; does not touch temp_8.md.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    seed_dir = seed_dir or os.path.join(base, "LongTermStore", "SeedData")
    objectives_dir = objectives_dir or os.path.join(base, "LongTermStore", "Objectives")

    loaded = []
    objectives = []

    # Load SeedData
    if os.path.isdir(seed_dir):
        for fname in os.listdir(seed_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(seed_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    record = json.load(f)
                data_id = record.get("id") or os.path.splitext(fname)[0]
                payload = {
                    "run_id": None,
                    "module": "initialize_ai_brain",
                    "source_chain": ["SeedData"],
                    "tags": ["seed", "foundational"],
                    "content": record.get("content", record)
                }
                store_information(data_id, payload, category="semantic")
                loaded.append(data_id)
            except Exception:
                continue

    # List Objectives files
    if os.path.isdir(objectives_dir):
        for fname in os.listdir(objectives_dir):
            if fname.endswith(".json"):
                objectives.append(fname)

    return {
        "status": "initialized",
        "seed_loaded": loaded,
        "objectives_available": objectives
    }


class SystemState(TypedDict):
    relational_state: Any
    records: list[Any]
    objectives: list[Any]
    activity_queue: Any
    provenance_log: list[Any]
    feature_flags: dict[str, Any]


def initialize_system(storage_module) -> SystemState:
    relational_state: Any = {}
    records: list[Any] = []
    objectives: list[Any] = []
    try:
        if hasattr(storage_module, 'load_state') and callable(getattr(storage_module, 'load_state')):
            relational_state, records, objectives = storage_module.load_state()
    except Exception:
        relational_state, records, objectives = {}, [], []

    return {
        'relational_state': relational_state,
        'records': list(records or []),
        'objectives': list(objectives or []),
        'activity_queue': {
            'pending': [],
            'active': [],
            'completed': [],
        },
        'provenance_log': [],
        'feature_flags': {},
    }


def summarize_errors(error_reports: list[Any]) -> list[Any]:
    by_target: dict[str, dict[str, Any]] = {}
    for r in error_reports or []:
        if not isinstance(r, dict):
            continue
        tid = r.get('target_record_id')
        if not isinstance(tid, str) or not tid:
            continue
        cur = by_target.get(tid)
        if cur is None:
            cur = {'target_id': tid, 'error_count': 0, 'max_severity': 0.0}
            by_target[tid] = cur
        cur['error_count'] = int(cur.get('error_count') or 0) + 1
        try:
            sev = float(r.get('severity') or 0.0)
        except Exception:
            sev = 0.0
        if sev > float(cur.get('max_severity') or 0.0):
            cur['max_severity'] = float(sev)
    return [by_target[k] for k in sorted(by_target.keys())]


def update_record_in_list(records: list[Any]) -> Callable[[str, Any], Any]:
    def _update(record_id: str, new_value: Any):
        for r in records:
            if not isinstance(r, dict):
                continue
            rid = r.get('record_id') if isinstance(r.get('record_id'), str) else r.get('id')
            if rid == record_id:
                r['value'] = new_value
                return r
        raise KeyError(record_id)

    return _update


def relink_stub(record_id: str):
    raise NotImplementedError(record_id)


def recompute_stub(record_id: str):
    raise NotImplementedError(record_id)


def _is_relational_state_list(rs: Any) -> bool:
    if not isinstance(rs, dict):
        return False
    required = (
        'entities',
        'relations',
        'constraints',
        'objective_links',
        'spatial_measurement',
        'decision_trace',
    )
    for k in required:
        if k not in rs:
            return False
    if not isinstance(rs.get('entities'), list):
        return False
    if not isinstance(rs.get('relations'), list):
        return False
    if not isinstance(rs.get('constraints'), list):
        return False
    if not isinstance(rs.get('objective_links'), list):
        return False
    if not isinstance(rs.get('decision_trace'), dict):
        return False
    sm = rs.get('spatial_measurement')
    if sm is not None and not isinstance(sm, dict):
        return False
    return True


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _world_entity_id(*, context_id: str, object_id: str) -> str:
    return f"{context_id}::obj::{object_id}"


def _map_world_objects_to_entities(*, objects: list[Any], context_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for o in objects or []:
        if not isinstance(o, dict):
            continue
        oid = o.get('object_id')
        if not isinstance(oid, str) or not oid:
            continue
        ent_id = _world_entity_id(context_id=context_id, object_id=oid)
        out.append(
            {
                'id': ent_id,
                'type': 'world_object',
                'attributes': {
                    'object_id': oid,
                    'position': o.get('position'),
                    'rotation': o.get('rotation'),
                    'scale': o.get('scale'),
                    'properties': o.get('properties'),
                    'context_id': context_id,
                },
                'source': '3d_world',
            }
        )
    out.sort(key=lambda e: str(e.get('id') or ''))
    return out


def _map_world_relations_to_relations(*, relations: list[Any], context_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in relations or []:
        if not isinstance(r, dict):
            continue
        st = r.get('source_object_id')
        tt = r.get('target_object_id')
        pred = r.get('type')
        rid = r.get('relation_id')
        if not (isinstance(st, str) and st and isinstance(tt, str) and tt and isinstance(pred, str) and pred):
            continue
        subj = _world_entity_id(context_id=context_id, object_id=st)
        obj = _world_entity_id(context_id=context_id, object_id=tt)
        try:
            w = float(r.get('strength') or 0.0)
        except Exception:
            w = 0.0
        # Keep required subj/pred/obj; include confidence/evidence/source for downstream use.
        out.append(
            {
                'subj': subj,
                'pred': pred,
                'obj': obj,
                'confidence': _clamp01(w),
                'evidence': [f"ctx:{context_id}", str(rid) if isinstance(rid, str) and rid else ''],
                'source': '3d_world',
            }
        )
    out.sort(
        key=lambda rr: (
            str(rr.get('subj') or ''),
            str(rr.get('pred') or ''),
            str(rr.get('obj') or ''),
        )
    )
    return out


def _merge_world_into_relational_state_list(
    *,
    relational_state: dict[str, Any],
    objects: list[Any],
    relations: list[Any],
    context_id: str,
) -> dict[str, Any]:
    rs = relational_state
    ents = rs.get('entities')
    rels = rs.get('relations')
    if not isinstance(ents, list) or not isinstance(rels, list):
        return rs

    # Remove prior world rows for this context_id (do not touch spatial adapter rows with source '3d').
    def _is_world_entity_for_ctx(e: Any) -> bool:
        if not isinstance(e, dict):
            return False
        if e.get('source') != '3d_world':
            return False
        attrs = e.get('attributes')
        return isinstance(attrs, dict) and attrs.get('context_id') == context_id

    ents[:] = [e for e in ents if not _is_world_entity_for_ctx(e)]

    ctx_tag = f"ctx:{context_id}"
    def _is_world_relation_for_ctx(r: Any) -> bool:
        if not isinstance(r, dict):
            return False
        if r.get('source') != '3d_world':
            return False
        ev = r.get('evidence')
        return isinstance(ev, list) and ctx_tag in ev

    rels[:] = [r for r in rels if not _is_world_relation_for_ctx(r)]

    ents.extend(_map_world_objects_to_entities(objects=objects, context_id=context_id))
    rels.extend(_map_world_relations_to_relations(relations=relations, context_id=context_id))
    return rs


def run_cycle(
    state: SystemState,
    context_id: str,
    context_metadata: dict[str, Any],
    modules: dict[str, Any],
) -> SystemState:
    measure_mod = modules.get('measure')
    adapter_mod = modules.get('relational_adapter')
    error_mod = modules.get('error_resolution')
    want_mod = modules.get('want')
    activity_mod = modules.get('activity_manager')
    retrieval_mod = modules.get('retrieval')
    reasoning_mod = modules.get('reasoning')
    storage_mod = modules.get('storage')

    # Feature flag: rollback-capable resolution path (default false).
    use_rollback_resolution = False
    deterministic_mode = False
    deterministic_time = None
    adaptive_sampling = False
    adaptive_n_min = 32
    adaptive_n0 = None
    adaptive_n_max = None
    adaptive_growth_multiplier = 2.0
    adaptive_early_stop_margin = None
    adaptive_decision_multiplier = 10.0
    rollback_storm_enabled = False
    rollback_storm_max_rollbacks = 3
    verifier_cfg_for_error_resolution: dict[str, Any] = {}
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        deterministic_mode = bool(det.get('deterministic_mode'))
        if deterministic_mode:
            try:
                from module_provenance import now_ts as _prov_now_ts

                deterministic_time = float(_prov_now_ts())
            except Exception:
                deterministic_time = 0.0
        ff = cfg.get('feature_flags', {}) if isinstance(cfg, dict) else {}
        if isinstance(ff, dict):
            use_rollback_resolution = bool(ff.get('use_rollback_resolution'))

        verifier_cfg_for_error_resolution = cfg.get('verifier', {}) if isinstance(cfg, dict) else {}

        # Prefer verifier.adaptive_sampling (Copilot suggestion). Fall back to legacy error_resolution.adaptive_sampling.
        adapt = None
        if isinstance(verifier_cfg_for_error_resolution, dict):
            adapt = verifier_cfg_for_error_resolution.get('adaptive_sampling')

        if not isinstance(adapt, dict):
            er_cfg = cfg.get('error_resolution', {}) if isinstance(cfg, dict) else {}
            if isinstance(er_cfg, dict):
                adapt = er_cfg.get('adaptive_sampling')

        if isinstance(adapt, dict):
            if 'enabled' in adapt:
                adaptive_sampling = bool(adapt.get('enabled'))
            if 'n_min' in adapt:
                try:
                    adaptive_n_min = int(adapt.get('n_min'))
                except Exception:
                    adaptive_n_min = 32
            if 'n0' in adapt:
                try:
                    adaptive_n0 = int(adapt.get('n0'))
                except Exception:
                    adaptive_n0 = None
            if 'n_max' in adapt:
                try:
                    adaptive_n_max = int(adapt.get('n_max'))
                except Exception:
                    adaptive_n_max = None
            if 'multiplier' in adapt:
                try:
                    adaptive_growth_multiplier = float(adapt.get('multiplier'))
                except Exception:
                    adaptive_growth_multiplier = 2.0
            if 'early_stop_margin' in adapt:
                try:
                    adaptive_early_stop_margin = float(adapt.get('early_stop_margin'))
                except Exception:
                    adaptive_early_stop_margin = None
            # Backward compatible: allow decision multiplier if present.
            if 'decision_multiplier' in adapt:
                try:
                    adaptive_decision_multiplier = float(adapt.get('decision_multiplier'))
                except Exception:
                    adaptive_decision_multiplier = 10.0

        # Rollback-storm policy (optional).
        er_cfg2 = cfg.get('error_resolution', {}) if isinstance(cfg, dict) else {}
        if isinstance(er_cfg2, dict):
            rsp = er_cfg2.get('rollback_storm_policy')
            if isinstance(rsp, dict):
                if 'enabled' in rsp:
                    rollback_storm_enabled = bool(rsp.get('enabled'))
                if 'max_rollbacks' in rsp:
                    try:
                        rollback_storm_max_rollbacks = int(rsp.get('max_rollbacks'))
                    except Exception:
                        rollback_storm_max_rollbacks = 3
    except Exception:
        pass

    # Allow state override for tests/sandboxing.
    try:
        ff_state = state.get('feature_flags') if isinstance(state, dict) else None
        if isinstance(ff_state, dict) and 'use_rollback_resolution' in ff_state:
            use_rollback_resolution = bool(ff_state.get('use_rollback_resolution'))
    except Exception:
        pass

    # Load provenance log (prefer storage, fall back to state).
    provenance_log: list[dict[str, Any]] = []
    try:
        if hasattr(storage_mod, 'load_provenance_log') and callable(getattr(storage_mod, 'load_provenance_log')):
            provenance_log = list(storage_mod.load_provenance_log() or [])
        else:
            pl = state.get('provenance_log') if isinstance(state, dict) else None
            provenance_log = list(pl or []) if isinstance(pl, list) else []
    except Exception:
        provenance_log = []

    prov_box: dict[str, Any] = {'log': [e for e in provenance_log if isinstance(e, dict)]}

    objects, relations = measure_mod.measure_world(context_id)

    rs = state.get('relational_state')
    if _is_relational_state_list(rs):
        state['relational_state'] = _merge_world_into_relational_state_list(
            relational_state=rs,
            objects=objects,
            relations=relations,
            context_id=context_id,
        )
    elif isinstance(rs, dict) and isinstance(rs.get('entities'), dict) and isinstance(rs.get('links'), dict) and isinstance(rs.get('contexts'), dict):
        state['relational_state'] = adapter_mod.update_relational_state(
            rs,
            objects,
            relations,
            context_id,
            context_metadata,
        )
    else:
        state['relational_state'] = adapter_mod.build_relational_state(
            objects,
            relations,
            context_id,
            context_metadata,
        )

    error_reports: list[Any] = []
    measurement_gaps: list[Any] = []
    last_measure_ts: dict[str, float] = {}
    records = state.get('records') or []
    records_sorted = sorted(
        [r for r in records if isinstance(r, dict)],
        key=lambda r: str(r.get('record_id') or r.get('id') or ''),
    )
    for record in records_sorted:
        rid = record.get('record_id') if isinstance(record.get('record_id'), str) else record.get('id')
        if not isinstance(rid, str) or not rid:
            continue
        m = measure_mod.measure_record(rid)
        try:
            ts = float(m.get('timestamp') or 0.0) if isinstance(m, dict) else 0.0
        except Exception:
            ts = 0.0
        last_measure_ts[rid] = float(ts)
        report = error_mod.detect_error(measurement=m, record=record)
        if report is not None:
            error_reports.append(report)

    error_reports.sort(key=lambda r: (str((r or {}).get('target_record_id') or ''), str((r or {}).get('error_type') or '')))

    error_tasks = [error_mod.create_error_resolution_task(error_report=r) for r in error_reports]
    _ = error_tasks

    # When enabled, create rollback-capable resolution tasks and enqueue them directly.
    td_tasks_by_target: dict[str, dict[str, Any]] = {}
    if use_rollback_resolution:
        def _strategy_for_error_type(et: Any) -> str:
            s = str(et or '')
            if s == 'mis_measurement':
                return 're_measure'
            if s == 'mis_description':
                return 'update_description'
            if s == 'mis_association':
                return 'relink'
            if s == 'mis_inference':
                return 'recompute'
            return 're_measure'

        for rep in error_reports:
            if not isinstance(rep, dict):
                continue
            rid = rep.get('target_record_id')
            if not isinstance(rid, str) or not rid:
                continue

            rep2 = rep
            try:
                if hasattr(error_mod, 'log_error_report') and callable(getattr(error_mod, 'log_error_report')):
                    rep2, prov_box['log'] = error_mod.log_error_report(
                        error_report=rep,
                        provenance_log=prov_box['log'],
                        deterministic_mode=deterministic_mode,
                        deterministic_time=deterministic_time,
                    )
            except Exception:
                rep2 = rep

            try:
                if hasattr(error_mod, 'create_resolution_task') and callable(getattr(error_mod, 'create_resolution_task')):
                    task_out = error_mod.create_resolution_task(
                        error_report=rep2,
                        resolution_strategy=_strategy_for_error_type(rep2.get('error_type')),
                        provenance_log=prov_box['log'],
                        deterministic_mode=deterministic_mode,
                        deterministic_time=deterministic_time,
                    )
                    if isinstance(task_out, tuple) and len(task_out) == 2:
                        t, prov_box['log'] = task_out
                    else:
                        t = task_out
                    if isinstance(t, dict):
                        td_tasks_by_target[rid] = t
            except Exception:
                continue

        # Persist provenance after task creation.
        try:
            if hasattr(storage_mod, 'save_provenance_log') and callable(getattr(storage_mod, 'save_provenance_log')):
                storage_mod.save_provenance_log(prov_box['log'])
        except Exception:
            pass

        # Enqueue deterministic error_resolution activities with task payload.
        q0 = state.get('activity_queue') if isinstance(state, dict) else None
        if not isinstance(q0, dict):
            q0 = {'pending': [], 'active': [], 'completed': []}
        if deterministic_mode:
            q0['deterministic_mode'] = True

        pending = q0.get('pending')
        if not isinstance(pending, list):
            pending = []
            q0['pending'] = pending

        for rid in sorted(td_tasks_by_target.keys()):
            t = td_tasks_by_target[rid]
            aid = str(t.get('task_id') or f"err_{rid}")
            pending.append(
                {
                    'activity_id': aid,
                    'activity_type': 'error_resolution',
                    'targets': [rid],
                    'priority': float(t.get('priority') or 0.0),
                    'metadata': {'resolution_task': t},
                }
            )

        state['activity_queue'] = q0

    synthesis_opportunities: list[Any] = []

    awareness_plan = want_mod.compute_awareness_plan(
        state.get('objectives') or [],
        measurement_gaps,
        summarize_errors(error_reports),
        synthesis_opportunities,
        plan_id=f"plan_{context_id}",
    )

    def _measure_activity(activity: dict[str, Any]):
        targets = activity.get('targets') if isinstance(activity, dict) else None
        if not isinstance(targets, list):
            return []
        out = []
        for t in sorted([x for x in targets if isinstance(x, str) and x]):
            out.append(measure_mod.measure_record(t))
        return out

    def _retrieve_activity(activity: dict[str, Any]):
        targets = activity.get('targets') if isinstance(activity, dict) else None
        if not isinstance(targets, list):
            targets = []
        query = {
            'target_ids': [t for t in targets if isinstance(t, str) and t],
            'max_results': 10,
        }
        return _annotate_retrieval_rows_with_categorized_context(retrieval_mod.retrieve(state.get('records') or [], query))

    def _error_resolution_activity(activity: dict[str, Any]):
        # Feature-flagged rollback path.
        if use_rollback_resolution and hasattr(error_mod, 'execute_resolution_task'):
            meta = activity.get('metadata') if isinstance(activity, dict) else None
            resolution_task = None
            if isinstance(meta, dict):
                resolution_task = meta.get('resolution_task')

            # Fallback: look up task by target if metadata not present.
            targets = activity.get('targets') if isinstance(activity, dict) else None
            target_id = ''
            if isinstance(targets, list) and targets:
                target_id = str(sorted([t for t in targets if isinstance(t, str) and t])[0])
            if not isinstance(resolution_task, dict) and target_id:
                resolution_task = td_tasks_by_target.get(target_id)

            if not isinstance(resolution_task, dict) or not target_id:
                return {'ok': False, 'reason': 'missing_resolution_task'}

            # In-memory record store adapters (operate on state['records']).
            def _record_lookup_fn(rid: str):
                for r in (state.get('records') or []):
                    if not isinstance(r, dict):
                        continue
                    rrid = r.get('record_id') if isinstance(r.get('record_id'), str) else r.get('id')
                    if rrid == rid:
                        return dict(r)
                raise KeyError(rid)

            def _storage_update_fn(rec: dict[str, Any]) -> None:
                rid = rec.get('record_id') if isinstance(rec.get('record_id'), str) else rec.get('id')
                if not isinstance(rid, str) or not rid:
                    return
                records_list = state.get('records') or []
                for i, r in enumerate(records_list):
                    if not isinstance(r, dict):
                        continue
                    rrid = r.get('record_id') if isinstance(r.get('record_id'), str) else r.get('id')
                    if rrid == rid:
                        records_list[i] = dict(rec)
                        return
                records_list.append(dict(rec))

            def _relink_td(rec: dict[str, Any], new_context_id: str):
                out = dict(rec)
                out['context_id'] = new_context_id
                return out

            def _recompute_td(rec: dict[str, Any]):
                return dict(rec)

            try:
                alpha = 0.05
                min_effect_size = 1e-6
                if isinstance(verifier_cfg_for_error_resolution, dict):
                    try:
                        alpha = float(verifier_cfg_for_error_resolution.get('p_threshold', alpha))
                    except Exception:
                        alpha = 0.05
                    try:
                        min_effect_size = float(verifier_cfg_for_error_resolution.get('min_effect_size', min_effect_size))
                    except Exception:
                        min_effect_size = 1e-6

                exec_out = error_mod.execute_resolution_task(
                    task=resolution_task,
                    record_lookup_fn=_record_lookup_fn,
                    measure_fn=measure_mod.measure_record,
                    storage_update_fn=_storage_update_fn,
                    relink_fn=_relink_td,
                    recompute_fn=_recompute_td,
                    provenance_log=prov_box['log'],
                    deterministic_mode=deterministic_mode,
                    deterministic_time=deterministic_time,
                    alpha=alpha,
                    min_effect_size=min_effect_size,
                    adaptive_sampling=adaptive_sampling,
                    adaptive_n_min=adaptive_n_min,
                    adaptive_n0=adaptive_n0,
                    adaptive_n_max=adaptive_n_max,
                    adaptive_growth_multiplier=adaptive_growth_multiplier,
                    adaptive_early_stop_margin=adaptive_early_stop_margin,
                    adaptive_multiplier=adaptive_decision_multiplier,
                    rollback_storm_enabled=rollback_storm_enabled,
                    rollback_storm_max_rollbacks=rollback_storm_max_rollbacks,
                )
                if isinstance(exec_out, tuple) and len(exec_out) == 2:
                    out_task, prov_box['log'] = exec_out
                else:
                    out_task = exec_out

                # Persist updated task back into in-memory maps / activity payloads.
                try:
                    if isinstance(out_task, dict) and target_id:
                        td_tasks_by_target[target_id] = dict(out_task)
                        if isinstance(meta, dict):
                            meta['resolution_task'] = dict(out_task)
                except Exception:
                    pass

                # Best-effort persist updated task to storage (if supported).
                try:
                    if isinstance(out_task, dict) and hasattr(storage_mod, 'update_task') and callable(getattr(storage_mod, 'update_task')):
                        storage_mod.update_task(dict(out_task))
                except Exception:
                    pass

                # Persist provenance after execution.
                try:
                    if hasattr(storage_mod, 'save_provenance_log') and callable(getattr(storage_mod, 'save_provenance_log')):
                        storage_mod.save_provenance_log(prov_box['log'])
                except Exception:
                    pass

                return {'ok': True, 'resolution_task': out_task, 'provenance_events': len(prov_box['log'])}
            except Exception as e:
                return {'ok': False, 'reason': 'execute_exception', 'detail': str(e)}

        targets = activity.get('targets') if isinstance(activity, dict) else None
        if not isinstance(targets, list) or not targets:
            return {'ok': False, 'reason': 'missing_targets'}
        target_id = str(sorted([t for t in targets if isinstance(t, str) and t])[0])
        rep = None
        for r in error_reports:
            if isinstance(r, dict) and r.get('target_record_id') == target_id:
                rep = r
                break
        if rep is None:
            return {'ok': False, 'reason': 'no_error_report'}

        task = error_mod.create_error_resolution_task(error_report=rep)
        updater = update_record_in_list(state.get('records') or [])
        updated = error_mod.execute_error_resolution_task(
            task=task,
            measurement_fn=measure_mod.measure_record,
            update_record_fn=updater,
            relink_fn=relink_stub,
            recompute_fn=recompute_stub,
        )
        return {'ok': True, 'updated_record': updated}

    def _synthesize_activity(activity: dict[str, Any]):
        targets = activity.get('targets') if isinstance(activity, dict) else None
        if not isinstance(targets, list):
            targets = []
        opp = {'target_ids': [t for t in targets if isinstance(t, str) and t], 'coherence_gain': 0.0}
        return reasoning_mod.synthesize(records=state.get('records') or [], opportunity=opp)

    activity_modules: dict[str, Callable[[Any], Any]] = {
        'measure': _measure_activity,
        'retrieve': _retrieve_activity,
        'error_resolution': _error_resolution_activity,
        'synthesize': _synthesize_activity,
    }

    # Pass verifier module through the activity execution mapping (non-activity key).
    try:
        vmod = modules.get('verifier')
        if vmod is not None:
            activity_modules['__verifier__'] = vmod  # type: ignore[assignment]
    except Exception:
        pass

    # Verifier context for pre/post checks.
    verifier_cfg = {}
    verifier_policy = {}
    try:
        cfg = _load_config() or {}
        verifier_cfg = cfg.get('verifier', {}) if isinstance(cfg, dict) else {}
        verifier_policy = verifier_cfg
    except Exception:
        verifier_cfg = {}
        verifier_policy = {}

    records_map: dict[str, Any] = {}
    for r in (state.get('records') or []):
        if not isinstance(r, dict):
            continue
        rid = r.get('record_id') if isinstance(r.get('record_id'), str) else r.get('id')
        if isinstance(rid, str) and rid:
            records_map[rid] = r

    verifier_state = {
        'records_map': records_map,
        'last_measure_ts': last_measure_ts,
        'provenance': prov_box.get('log') or [],
        'verifier_cfg': verifier_cfg,
        'verifier_policy': verifier_policy,
        'deterministic_mode': deterministic_mode,
    }

    try:
        state['activity_queue'] = activity_mod.run_activity_cycle(
            awareness_plan=awareness_plan,
            queue=state.get('activity_queue') or {'pending': [], 'active': [], 'completed': []},
            modules=activity_modules,
            max_steps=1,
            state=verifier_state,
        )
    except TypeError:
        # Backward compatibility: some harness stubs don't accept the new kwarg.
        state['activity_queue'] = activity_mod.run_activity_cycle(
            awareness_plan=awareness_plan,
            queue=state.get('activity_queue') or {'pending': [], 'active': [], 'completed': []},
            modules=activity_modules,
            max_steps=1,
        )

    try:
        if hasattr(storage_mod, 'save_state') and callable(getattr(storage_mod, 'save_state')):
            storage_mod.save_state(state.get('relational_state'), state.get('records'), state.get('objectives'))
    except Exception:
        pass

    # Persist provenance log into state (and storage when available).
    try:
        state['provenance_log'] = list(prov_box.get('log') or [])
        if hasattr(storage_mod, 'save_provenance_log') and callable(getattr(storage_mod, 'save_provenance_log')):
            storage_mod.save_provenance_log(state['provenance_log'])
    except Exception:
        pass

    return state
