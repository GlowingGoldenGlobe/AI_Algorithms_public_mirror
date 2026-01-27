#+#+#+#+ module_integration.py
import hashlib
import json
import os
import shutil
from typing import Any, Callable, TypedDict
from module_toggle import move
from module_awareness import trigger_information_seeking_if, trigger_information_seeking, validate_response, awareness_plan
from module_scheduler import flag_record
from module_current_activity import set_activity, persist_activity
from module_objectives import get_objectives_by_label
from module_storage import store_information, resolve_path, store_and_get_path
from module_measure import measure_information
from module_scheduler import flag_record, schedule_synthesis
from datetime import datetime
from module_collector import collect_results
from module_tools import (
    similarity, familiarity, usefulness, synthesis_potential,
    compare_against_objectives, search_related, procedural_match,
    search_internet, query_llm, _load_config, describe, sanitize_id, safe_join
)
from module_select import rank as rank_selection
import uuid

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
    except Exception:
        pass

    # Optional: attach 3D measurement mapped into a canonical relational_state.
    # This is guarded and non-fatal; it only runs when a spatial asset path exists.
    adapter_log = None
    try:
        from module_relational_adapter import attach_spatial_relational_state
        adapter_result = attach_spatial_relational_state(file_path)
        if isinstance(adapter_result, dict):
            adapter_log = {
                "status": adapter_result.get("status"),
                "reason": adapter_result.get("reason"),
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
            rs.setdefault('decision_trace', {})

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
                ts = (fixed_ts if (deterministic_mode and fixed_ts) else datetime.now().isoformat())
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
        if isinstance(sel_cfg, dict) and bool(sel_cfg.get('enable')) and bool(sel_cfg.get('use_retrieval_scores')):
            try:
                from module_retrieval import compute_retrieval_score

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

                rrec = {
                    'record_id': data_id,
                    'objective_links': objective_links,
                    # For single-record selection, recurrence is not currently modeled here.
                    'recurrence': 0.0,
                }
                q = {
                    'target_ids': [data_id],
                    'objective_id': objective_id,
                    'deterministic_mode': bool(deterministic_mode),
                }
                rs = compute_retrieval_score(rrec, q)
                rscore = float(rs.get('score') or 0.0)
                rcomp = rs.get('components') if isinstance(rs, dict) else None

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
    try:
        from module_reasoning import check_constraints, detect_contradictions, propose_actions
        _rec_for_reasoning = None
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                _rec_for_reasoning = json.load(f)
        _rs = _rec_for_reasoning.get('relational_state') if isinstance(_rec_for_reasoning, dict) else None
        if isinstance(_rs, dict):
            constraint_report = check_constraints(_rs)
            contradiction_report = detect_contradictions(_rs)
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

    policy_inputs = {
        'usefulness': use,
        'contradiction': bool(mrep.get('decisive_recommendation') == 'contradiction_resolve' or any(c.get('severity',0)>0.5 for c in conflicts)),
        'description_maturity': 'stable' if (desc.get('claims')) else 'unknown',
        'selection_score': base_selection_score,
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

            adjusted = _clamp01(float(base_selection_score) + float(delta))

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
                'selection_score_base': round(float(base_selection_score), 6),
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
                proc_ts = fixed_ts if (deterministic_mode and fixed_ts) else datetime.now().isoformat()
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
        with open(file_path, 'r+', encoding='utf-8') as f:
            rec = json.load(f)

            # Persist deterministic reasoning into relational_state decision_trace.
            try:
                rs = rec.get('relational_state')
                if not isinstance(rs, dict):
                    rs = {}
                    rec['relational_state'] = rs
                dt = rs.get('decision_trace')
                if not isinstance(dt, dict):
                    dt = {}
                    rs['decision_trace'] = dt
                if isinstance(constraint_report, dict):
                    dt['constraints'] = constraint_report
                    dt['constraints_report'] = constraint_report
                if isinstance(contradiction_report, dict):
                    dt['contradictions'] = contradiction_report
                if isinstance(proposed_actions, dict):
                    dt['proposed_actions'] = proposed_actions
                # Persist want plan (if present) for downstream scheduling/retrieval.
                if isinstance(plan_obj, dict) and plan_obj.get('plan_id') and plan_obj.get('wants') is not None:
                    dt['want_plan'] = plan_obj
            except Exception:
                pass

            chains = rec.setdefault('reason_chain', [])
            chains.append(reason_chain[0])
            rec['reason_chain'] = chains[-50:]
            top_sel = (sel_rank[0] if (isinstance(sel_rank, list) and sel_rank) else {})
            hard_violation = bool(isinstance(constraint_report, dict) and constraint_report.get('has_hard_violation'))
            vio_count = int(len((constraint_report or {}).get('violations') or [])) if isinstance(constraint_report, dict) else 0
            decision_signals = {
                'selection_score': float(top_sel.get('relevance_score') or 0.0),
                'objective_alignment': top_sel.get('objective_alignment', 'unknown'),
                'similarity': float(sim_score),
                'usefulness': use,
                'beneficial_and_synthesis': ((('beneficial' in relation_labels) and ('synthesis_value' in relation_labels))),
                'contradiction': bool(mrep.get('decisive_recommendation') == 'contradiction_resolve' or any(c.get('severity', 0) > 0.5 for c in conflicts)),
                'constraint_hard_violation': hard_violation,
                'constraint_violation_count': vio_count,
                'description_maturity': ('stable' if (desc.get('claims')) else 'unknown'),
                'target_space': target_space,
                'policy_rule_id': justification.get('policy_rule_id')
            }
            if isinstance(soft_influence_info, dict):
                decision_signals['soft_influence'] = soft_influence_info
            rec.setdefault('decision_signals', []).append(decision_signals)
            rec['decision_signals'] = rec['decision_signals'][-100:]
            f.seek(0)
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.truncate()
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
                query = {
                    'target_ids': [t for t in targets if isinstance(t, str) and t],
                    'max_results': 10,
                }
                try:
                    return retrieve(store, query)
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
        return retrieval_mod.retrieve(state.get('records') or [], query)

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
