def _extract_scene_validation_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("scene_validation_summary"), dict):
        return dict(source.get("scene_validation_summary") or {})

    decision_trace = source.get("decision_trace")
    if not isinstance(decision_trace, dict):
        relational_state = source.get("relational_state")
        if isinstance(relational_state, dict):
            decision_trace = relational_state.get("decision_trace")
    if not isinstance(decision_trace, dict):
        return None

    summary = decision_trace.get("scene_validation")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_comprehension_review_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("comprehension_review_summary"), dict):
        return dict(source.get("comprehension_review_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("comprehension_review_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_foundational_tier_hook_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("foundational_tier_hook_summary"), dict):
        return dict(source.get("foundational_tier_hook_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("foundational_tier_hook_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_foundational_active_space_reference_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("foundational_active_space_reference_summary"), dict):
        return dict(source.get("foundational_active_space_reference_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("foundational_active_space_reference_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_foundational_optional_reference_non_match_artifact(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("foundational_optional_reference_non_match_artifact"), dict):
        return dict(source.get("foundational_optional_reference_non_match_artifact") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    artifact = derived.get("foundational_optional_reference_non_match_artifact")
    return dict(artifact) if isinstance(artifact, dict) else None


def _extract_mirrored_parameter_review_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("mirrored_parameter_review_summary"), dict):
        return dict(source.get("mirrored_parameter_review_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("mirrored_parameter_review_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_multi_location_comprehension_review_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("multi_location_comprehension_review_summary"), dict):
        return dict(source.get("multi_location_comprehension_review_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("multi_location_comprehension_review_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_purpose_carrier_summary(source):
    if not isinstance(source, dict):
        return None

    if isinstance(source.get("purpose_carrier_summary"), dict):
        return dict(source.get("purpose_carrier_summary") or {})

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("purpose_carrier_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _build_simultaneous_context_explanations(
    foundational_active_space_reference_summary,
    foundational_optional_reference_non_match_artifact,
):
    explanations = []

    if isinstance(foundational_active_space_reference_summary, dict):
        activity_digest = (
            foundational_active_space_reference_summary.get("activity_digest")
            if isinstance(foundational_active_space_reference_summary.get("activity_digest"), dict)
            else {}
        )
        trigger_digest = (
            foundational_active_space_reference_summary.get("trigger_digest")
            if isinstance(foundational_active_space_reference_summary.get("trigger_digest"), dict)
            else {}
        )
        explanations.append(
            {
                "family_id": str(foundational_active_space_reference_summary.get("family_id") or "simultaneous_context_match"),
                "surface_kind": "foundational_support",
                "summary": "bounded simultaneous-context support is available for current AI activity",
                "trigger_mode": str(trigger_digest.get("trigger_mode") or "passive_auto"),
                "query_state": str(trigger_digest.get("query_state") or "auto_considered"),
                "objective_alignment": str(activity_digest.get("objective_alignment") or "unknown"),
                "current_activity_present": bool(activity_digest.get("current_activity_present")),
                "current_activity_id": str(activity_digest.get("current_activity_id") or ""),
                "authoritative": False,
                "current_serving": False,
            }
        )

    if isinstance(foundational_optional_reference_non_match_artifact, dict):
        activity_digest = (
            foundational_optional_reference_non_match_artifact.get("activity_digest")
            if isinstance(foundational_optional_reference_non_match_artifact.get("activity_digest"), dict)
            else {}
        )
        trigger_digest = (
            foundational_optional_reference_non_match_artifact.get("trigger_digest")
            if isinstance(foundational_optional_reference_non_match_artifact.get("trigger_digest"), dict)
            else {}
        )
        explanations.append(
            {
                "family_id": str(foundational_optional_reference_non_match_artifact.get("family_id") or "simultaneous_context_match"),
                "surface_kind": "optional_reference_artifact",
                "summary": str(
                    foundational_optional_reference_non_match_artifact.get("result_reason_summary")
                    or "bounded simultaneous-context support rejected current relevance"
                ),
                "trigger_mode": str(trigger_digest.get("trigger_mode") or "passive_auto"),
                "query_state": str(trigger_digest.get("query_state") or "auto_considered"),
                "objective_alignment": str(activity_digest.get("objective_alignment") or "unknown"),
                "current_activity_present": bool(activity_digest.get("current_activity_present")),
                "current_activity_id": str(activity_digest.get("current_activity_id") or ""),
                "authoritative": False,
                "current_serving": False,
            }
        )

    return explanations


def _build_mirror_review_explanations(
    mirrored_parameter_review_summary,
    multi_location_comprehension_review_summary,
):
    explanations = []

    if isinstance(mirrored_parameter_review_summary, dict):
        explanations.append(
            {
                "family_id": str(mirrored_parameter_review_summary.get("review_family_id") or "simultaneous_context_match"),
                "surface_kind": "mirrored_parameter_review",
                "summary": str(
                    mirrored_parameter_review_summary.get("derivative_value_summary")
                    or "review-only mirrored parameter inventory is available"
                ),
                "visibility_mode": str(mirrored_parameter_review_summary.get("visibility_mode") or "review_only"),
                "derivative_value_status": str(mirrored_parameter_review_summary.get("derivative_value_status") or "absent"),
                "present_surface_count": int(mirrored_parameter_review_summary.get("present_surface_count") or 0),
                "authoritative": False,
                "current_serving": False,
            }
        )

    if isinstance(multi_location_comprehension_review_summary, dict):
        explanations.append(
            {
                "family_id": str(
                    multi_location_comprehension_review_summary.get("review_family_id") or "simultaneous_context_match"
                ),
                "surface_kind": "multi_location_comprehension_review",
                "summary": str(
                    multi_location_comprehension_review_summary.get("review_summary")
                    or "multi-location comprehension review is unavailable"
                ),
                "visibility_mode": str(multi_location_comprehension_review_summary.get("visibility_mode") or "review_only"),
                "review_status": str(multi_location_comprehension_review_summary.get("review_status") or "absent"),
                "current_activity_present": bool(
                    multi_location_comprehension_review_summary.get("current_activity_present")
                ),
                "authoritative": False,
                "current_serving": False,
            }
        )

    return explanations


def _extract_measurement_adequacy_summary(source):
    if not isinstance(source, dict):
        return None

    direct = source.get("measurement_adequacy_summary")
    if isinstance(direct, dict):
        return dict(direct)

    direct = source.get("measurement_adequacy")
    if isinstance(direct, dict):
        return dict(direct)

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("measurement_adequacy_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_categorized_context_summary(source):
    if not isinstance(source, dict):
        return None

    direct = source.get("categorized_context_summary")
    if isinstance(direct, dict):
        return dict(direct)

    direct = source.get("categorized_context")
    if isinstance(direct, dict):
        return dict(direct)

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    summary = derived.get("categorized_context_summary")
    return dict(summary) if isinstance(summary, dict) else None


def _extract_learning_readiness_summary(source):
    if not isinstance(source, dict):
        return None

    direct = source.get("learning_readiness_summary")
    direct_summary = dict(direct) if isinstance(direct, dict) else None

    if direct_summary is None:
        direct = source.get("learning_readiness")
        direct_summary = dict(direct) if isinstance(direct, dict) else None

    measurement_summary = _extract_measurement_adequacy_summary(source)
    categorized_summary = _extract_categorized_context_summary(source)
    comprehension_summary = _extract_comprehension_review_summary(source)
    if (
        isinstance(direct_summary, dict)
        and isinstance(direct_summary.get("status"), str)
        and "ready" in direct_summary
        and isinstance(direct_summary.get("reason"), str)
        and isinstance(direct_summary.get("reasons"), list)
        and isinstance(direct_summary.get("unmet_conditions"), list)
        and isinstance(direct_summary.get("observed_levels"), dict)
    ):
        return direct_summary
    if not (isinstance(measurement_summary, dict) and isinstance(categorized_summary, dict) and isinstance(comprehension_summary, dict)):
        return direct_summary

    from module_metrics import build_learning_readiness_verdict

    categorized_level = categorized_summary.get("level")
    if not isinstance(categorized_level, str) or not categorized_level:
        categorized_level = categorized_summary.get("support_level")

    comprehension_level = comprehension_summary.get("level")
    if not isinstance(comprehension_level, str) or not comprehension_level:
        comprehension_level = comprehension_summary.get("quality")

    return build_learning_readiness_verdict(
        measurement_adequacy={
            "level": measurement_summary.get("level"),
            "reason": measurement_summary.get("reason"),
        },
        categorized_context={
            "level": categorized_level,
            "counts": categorized_summary.get("counts") if isinstance(categorized_summary.get("counts"), dict) else {},
        },
        comprehension_review={
            "level": comprehension_level,
            "summary": comprehension_summary.get("summary"),
            "unresolved_gaps": comprehension_summary.get("unresolved_gaps"),
        },
    )


def _extract_learning_sandbox_state(source):
    if not isinstance(source, dict):
        return None

    direct = source.get("learning_sandbox_state")
    if isinstance(direct, dict):
        return dict(direct)

    direct = source.get("sandbox_state")
    if isinstance(direct, dict):
        return dict(direct)

    readiness_summary = _extract_learning_readiness_summary(source)

    from module_metrics import build_learning_sandbox_activation_report
    from module_tools import _load_config

    cfg = _load_config() or {}
    sandbox_settings = cfg.get("selection_migration", {}) if isinstance(cfg, dict) else {}
    return build_learning_sandbox_activation_report(
        readiness_verdict=readiness_summary,
        sandbox_settings=sandbox_settings,
        sandbox_name="selection_migration",
    )


def _extract_categorized_context_follow_through_summary(source):
    if not isinstance(source, dict):
        return None

    direct = source.get("categorized_context_follow_through_summary")
    if isinstance(direct, dict):
        return dict(direct)

    retained = source.get("retained_memory_follow_through_summary")
    if isinstance(retained, dict):
        summary = retained.get("categorized_context_follow_through_summary")
        if isinstance(summary, dict):
            return dict(summary)

    relational_state = source.get("relational_state")
    if not isinstance(relational_state, dict):
        return None

    derived = relational_state.get("derived")
    if not isinstance(derived, dict):
        return None

    retained = derived.get("retained_memory_follow_through_summary")
    if not isinstance(retained, dict):
        return None

    summary = retained.get("categorized_context_follow_through_summary")
    return dict(summary) if isinstance(summary, dict) else None


def select_information(source):
    """Select and rank information from a semantic file or content.
    Returns dict with ranking entries including relevance_score and reason_codes.
    """
    import json, os
    ranking = []
    try:
        # If source is a file path, load it; else treat as string content
        if os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                record = json.load(f)
            content = str(record.get("content", ""))
            data_id = record.get("id", os.path.basename(source))
            scene_validation_summary = _extract_scene_validation_summary(record)
            comprehension_review_summary = _extract_comprehension_review_summary(record)
            foundational_tier_hook_summary = _extract_foundational_tier_hook_summary(record)
            foundational_active_space_reference_summary = _extract_foundational_active_space_reference_summary(record)
            foundational_optional_reference_non_match_artifact = _extract_foundational_optional_reference_non_match_artifact(record)
            mirrored_parameter_review_summary = _extract_mirrored_parameter_review_summary(record)
            multi_location_comprehension_review_summary = _extract_multi_location_comprehension_review_summary(record)
            purpose_carrier_summary = _extract_purpose_carrier_summary(record)
            learning_sandbox_state = _extract_learning_sandbox_state(record)
            categorized_context_follow_through_summary = _extract_categorized_context_follow_through_summary(record)
        else:
            content = str(source)
            data_id = "unknown"
            scene_validation_summary = None
            comprehension_review_summary = None
            foundational_tier_hook_summary = None
            foundational_active_space_reference_summary = None
            foundational_optional_reference_non_match_artifact = None
            mirrored_parameter_review_summary = None
            multi_location_comprehension_review_summary = None
            purpose_carrier_summary = None
            learning_sandbox_state = None
            categorized_context_follow_through_summary = None
        # Simple scoring: length and keyword presence
        relevance_score = min(len(content), 100) / 100.0
        reason_codes = []
        for kw in ("synthesis", "useful", "beneficial"):
            if kw in content.lower():
                reason_codes.append(kw)
        row = {
            "id": data_id,
            "relevance_score": relevance_score,
            "reason_codes": reason_codes,
            "objective_alignment": "aligned" if "beneficial" in reason_codes else "unknown"
        }
        if isinstance(scene_validation_summary, dict):
            row["scene_validation_summary"] = scene_validation_summary
        if isinstance(comprehension_review_summary, dict):
            row["comprehension_review_summary"] = comprehension_review_summary
        if isinstance(foundational_tier_hook_summary, dict):
            row["foundational_tier_hook_summary"] = foundational_tier_hook_summary
        if isinstance(foundational_active_space_reference_summary, dict):
            row["foundational_active_space_reference_summary"] = foundational_active_space_reference_summary
        if isinstance(foundational_optional_reference_non_match_artifact, dict):
            row["foundational_optional_reference_non_match_artifact"] = foundational_optional_reference_non_match_artifact
        if isinstance(mirrored_parameter_review_summary, dict):
            row["mirrored_parameter_review_summary"] = mirrored_parameter_review_summary
        if isinstance(multi_location_comprehension_review_summary, dict):
            row["multi_location_comprehension_review_summary"] = multi_location_comprehension_review_summary
        if isinstance(purpose_carrier_summary, dict):
            row["purpose_carrier_summary"] = purpose_carrier_summary
        simultaneous_context_explanations = _build_simultaneous_context_explanations(
            foundational_active_space_reference_summary,
            foundational_optional_reference_non_match_artifact,
        )
        if simultaneous_context_explanations:
            row["simultaneous_context_explanations"] = simultaneous_context_explanations
        mirror_review_explanations = _build_mirror_review_explanations(
            mirrored_parameter_review_summary,
            multi_location_comprehension_review_summary,
        )
        if mirror_review_explanations:
            row["mirror_review_explanations"] = mirror_review_explanations
        if isinstance(learning_sandbox_state, dict):
            row["learning_sandbox_state"] = learning_sandbox_state
        if isinstance(categorized_context_follow_through_summary, dict):
            row["categorized_context_follow_through_summary"] = categorized_context_follow_through_summary
        ranking.append(row)
        return {"ranking": ranking[:10]}
    except Exception as e:
        return {"error": str(e)}


def rank(items, objectives=None):
    """Rank a list of items against optional objectives.

    items: list of dicts or strings. If dict, expects keys {id, content}.
    objectives: list of objective dicts with optional keywords.

    Returns list of {id, relevance_score, reason_codes, objective_alignment}.
    """
    ranked = []
    obj_keywords = set()
    try:
        for o in (objectives or []):
            kws = o.get("keywords") if isinstance(o, dict) else None
            if isinstance(kws, list):
                for k in kws:
                    obj_keywords.add(str(k).lower())
        for it in items:
            if isinstance(it, dict):
                data_id = it.get("id", "unknown")
                content = str(it.get("content", ""))
                scene_validation_summary = _extract_scene_validation_summary(it)
                comprehension_review_summary = _extract_comprehension_review_summary(it)
                foundational_tier_hook_summary = _extract_foundational_tier_hook_summary(it)
                foundational_active_space_reference_summary = _extract_foundational_active_space_reference_summary(it)
                foundational_optional_reference_non_match_artifact = _extract_foundational_optional_reference_non_match_artifact(it)
                mirrored_parameter_review_summary = _extract_mirrored_parameter_review_summary(it)
                multi_location_comprehension_review_summary = _extract_multi_location_comprehension_review_summary(it)
                purpose_carrier_summary = _extract_purpose_carrier_summary(it)
                learning_sandbox_state = _extract_learning_sandbox_state(it)
                categorized_context_follow_through_summary = _extract_categorized_context_follow_through_summary(it)
            else:
                data_id = "unknown"
                content = str(it)
                scene_validation_summary = None
                comprehension_review_summary = None
                foundational_tier_hook_summary = None
                foundational_active_space_reference_summary = None
                foundational_optional_reference_non_match_artifact = None
                mirrored_parameter_review_summary = None
                multi_location_comprehension_review_summary = None
                purpose_carrier_summary = None
                learning_sandbox_state = None
                categorized_context_follow_through_summary = None
            base_score = min(len(content), 200) / 200.0
            reasons = []
            for kw in ("synthesis", "useful", "beneficial"):
                if kw in content.lower():
                    reasons.append(kw)
            # objective keyword boost
            alignment = "unknown"
            if obj_keywords:
                hits = sum(1 for k in obj_keywords if k in content.lower())
                if hits:
                    base_score = min(1.0, base_score + min(hits * 0.1, 0.3))
                    alignment = "aligned"
                    reasons.append("objective_match")
            row = {
                "id": data_id,
                "relevance_score": round(base_score, 3),
                "reason_codes": reasons,
                "objective_alignment": alignment
            }
            if isinstance(scene_validation_summary, dict):
                row["scene_validation_summary"] = scene_validation_summary
            if isinstance(comprehension_review_summary, dict):
                row["comprehension_review_summary"] = comprehension_review_summary
            if isinstance(foundational_tier_hook_summary, dict):
                row["foundational_tier_hook_summary"] = foundational_tier_hook_summary
            if isinstance(foundational_active_space_reference_summary, dict):
                row["foundational_active_space_reference_summary"] = foundational_active_space_reference_summary
            if isinstance(foundational_optional_reference_non_match_artifact, dict):
                row["foundational_optional_reference_non_match_artifact"] = foundational_optional_reference_non_match_artifact
            if isinstance(mirrored_parameter_review_summary, dict):
                row["mirrored_parameter_review_summary"] = mirrored_parameter_review_summary
            if isinstance(multi_location_comprehension_review_summary, dict):
                row["multi_location_comprehension_review_summary"] = multi_location_comprehension_review_summary
            if isinstance(purpose_carrier_summary, dict):
                row["purpose_carrier_summary"] = purpose_carrier_summary
            simultaneous_context_explanations = _build_simultaneous_context_explanations(
                foundational_active_space_reference_summary,
                foundational_optional_reference_non_match_artifact,
            )
            if simultaneous_context_explanations:
                row["simultaneous_context_explanations"] = simultaneous_context_explanations
            mirror_review_explanations = _build_mirror_review_explanations(
                mirrored_parameter_review_summary,
                multi_location_comprehension_review_summary,
            )
            if mirror_review_explanations:
                row["mirror_review_explanations"] = mirror_review_explanations
            if isinstance(learning_sandbox_state, dict):
                row["learning_sandbox_state"] = learning_sandbox_state
            if isinstance(categorized_context_follow_through_summary, dict):
                row["categorized_context_follow_through_summary"] = categorized_context_follow_through_summary
            ranked.append(row)
        # Top-N
        ranked.sort(key=lambda x: x["relevance_score"], reverse=True)
        return ranked[:10]
    except Exception as e:
        return [{"error": str(e)}]
