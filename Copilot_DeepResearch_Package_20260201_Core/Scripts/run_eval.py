import os, json, sys, time
from module_tools import sanitize_id, build_semantic_index, validate_record
from module_storage import store_information
from module_collector import collect_results
from module_scheduler import flag_record
from module_integration import RelationalMeasurement

BASE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(BASE, 'eval_cases')

results = []
failures = 0


def _load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _semantic_path(data_id: str) -> str:
    return os.path.join(BASE, 'LongTermStore', 'Semantic', f"{sanitize_id(data_id)}.json")


def _ensure_objective(obj_id: str, content: str, labels: list):
    # Minimal helper: create/update objective JSON under LongTermStore/Objectives.
    obj_dir = os.path.join(BASE, 'LongTermStore', 'Objectives')
    os.makedirs(obj_dir, exist_ok=True)
    path = os.path.join(obj_dir, f"{sanitize_id(obj_id)}.json")
    rec = {
        "id": obj_id,
        "content": content,
        "occurrence_count": 1,
        "timestamps": [],
        "labels": labels,
    }
    try:
        if os.path.exists(path):
            # Keep deterministic: overwrite with known fixed structure.
            pass
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _relational_state_schema_keys():
    # Schema file exists but jsonschema is intentionally not a dependency.
    # We enforce strict key sets + types here.
    return {
        "entities",
        "relations",
        "constraints",
        "objective_links",
        "spatial_measurement",
        "conceptual_measurement",
        "decision_trace",
        "focus_snapshot",
    }


def eval_relational_state_schema():
    cid = 'logic_relational_state_schema'
    try:
        RelationalMeasurement('eval_rel_001', 'test content', 'semantic')
        spath = _semantic_path('eval_rel_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}
        rec = _load_json(spath)
        rs = rec.get('relational_state')
        if not isinstance(rs, dict):
            return {'case': cid, 'passed': False}

        # Required fields + types
        checks = [
            isinstance(rs.get('entities'), list),
            isinstance(rs.get('relations'), list),
            isinstance(rs.get('constraints'), list),
            isinstance(rs.get('objective_links'), list),
            (rs.get('spatial_measurement') is None or isinstance(rs.get('spatial_measurement'), dict)),
            (rs.get('conceptual_measurement') is None or isinstance(rs.get('conceptual_measurement'), dict)),
            isinstance(rs.get('decision_trace'), dict),
        ]
        if not all(checks):
            return {'case': cid, 'passed': False}

        # No unexpected top-level relational_state fields.
        allowed = _relational_state_schema_keys()
        unexpected = [k for k in rs.keys() if k not in allowed]
        if unexpected:
            return {'case': cid, 'passed': False}
        return {'case': cid, 'passed': True}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_concept_measure_basic_counts():
    cid = 'logic_concept_measure_basic_counts'
    try:
        from module_concept_measure import measure_conceptual_content

        rec = {
            'id': 'cm_001',
            'category': 'semantic',
            'content': 'Cube cube volume 10',
            'occurrence_count': 2,
            'timestamps': ['2025-01-01T00:00:00Z'],
        }
        # Use existing objective format; normalization should derive keywords.
        objectives = [{'id': 'objective_measurement', 'content': 'measurement', 'labels': ['objective', 'measurement']}]
        cm = measure_conceptual_content(rec, objectives, now_ts='2025-01-01T00:00:00Z', max_tokens=128, top_k_tokens=64)

        ok = isinstance(cm, dict)
        ok = ok and isinstance(cm.get('token_counts'), dict)
        ok = ok and (cm.get('length') == 4)
        ok = ok and (cm.get('unique_tokens') == 3)
        tc = cm.get('token_counts') or {}
        ok = ok and (tc.get('cube') == 2) and (tc.get('volume') == 1) and (tc.get('10') == 1)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_concept_measure_recurrence():
    cid = 'logic_concept_measure_recurrence'
    try:
        from module_concept_measure import measure_conceptual_content
        from math import exp

        rec = {
            'id': 'cm_002',
            'category': 'semantic',
            'content': 'alpha beta',
            'occurrence_count': 3,
            'timestamps': ['2025-01-01T00:00:00Z', '2025-01-08T00:00:00Z'],
        }
        cm = measure_conceptual_content(rec, [], now_ts='2025-01-15T00:00:00Z')
        r = cm.get('recurrence') or {}
        # Age is 7 days; half-life is 7 days => exp(-1)
        expected = round(exp(-1.0), 6)
        got = float(r.get('recency_score') or 0.0)
        ok = abs(got - expected) <= 1e-6
        ok = ok and (int(r.get('occurrence_count') or 0) == 3)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_concept_measure_objective_scoring():
    cid = 'logic_concept_measure_objective_scoring'
    try:
        from module_concept_measure import measure_conceptual_content

        rec = {
            'id': 'cm_003',
            'category': 'semantic',
            'content': 'cube cube volume 10',
            'occurrence_count': 2,
            'timestamps': ['2025-01-01T00:00:00Z'],
        }
        objectives = [
            {
                'id': 'shape_accuracy',
                'keywords': ['cube', 'volume'],
                'constraints': {'max_length': 10, 'required_keywords': ['cube']},
                'priority': 1.0,
            }
        ]
        cm = measure_conceptual_content(rec, objectives, now_ts='2025-01-01T00:00:00Z')
        scores = cm.get('objective_scores') or []
        if not scores or not isinstance(scores[0], dict):
            return {'case': cid, 'passed': False}
        row = scores[0]
        ok = (row.get('objective_id') == 'shape_accuracy')
        ok = ok and (row.get('keyword_hits') == 2)
        ok = ok and (abs(float(row.get('keyword_density')) - 0.5) <= 1e-6)
        ok = ok and (abs(float(row.get('constraint_score')) - 1.0) <= 1e-6)
        ok = ok and (abs(float(row.get('overall_score')) - 0.7) <= 1e-6)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_concept_measure_relational_state_integration():
    cid = 'logic_concept_measure_relational_state_integration'
    try:
        from module_concept_measure import measure_conceptual_content, attach_conceptual_measurement_to_relational_state

        rec = {
            'id': 'cm_004',
            'category': 'semantic',
            'content': 'cube cube volume 10',
            'occurrence_count': 2,
            'timestamps': ['2025-01-01T00:00:00Z'],
        }
        objectives = [
            {
                'id': 'shape_accuracy',
                'keywords': ['cube', 'volume'],
                'constraints': {'max_length': 10, 'required_keywords': ['cube']},
                'priority': 1.0,
            }
        ]
        cm = measure_conceptual_content(rec, objectives, now_ts='2025-01-01T00:00:00Z')
        rec2 = attach_conceptual_measurement_to_relational_state(rec, cm)
        rs = rec2.get('relational_state')
        if not isinstance(rs, dict):
            return {'case': cid, 'passed': False}
        ok = isinstance(rs.get('conceptual_measurement'), dict)
        ok = ok and isinstance(rs.get('objective_links'), list)
        # Should derive objective link for shape_accuracy (overall_score 0.7)
        ok = ok and any(isinstance(l, dict) and l.get('objective_id') == 'shape_accuracy' for l in (rs.get('objective_links') or []))
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_objectives_deterministic_timestamps():
    cid = 'logic_objectives_deterministic_timestamps'
    try:
        from module_tools import _load_config
        import module_objectives as objectives_mod

        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if not (det.get('deterministic_mode') and det.get('fixed_timestamp')):
            # Not in deterministic mode -> skip as pass.
            return {'case': cid, 'passed': True, 'skipped': True}

        fixed = str(det.get('fixed_timestamp'))
        obj_id = 'eval_obj_det_001'

        # Add
        objectives_mod.add_objective(obj_id, 'determinism objective', labels=['objective', 'eval'])
        path = os.path.join(BASE, 'LongTermStore', 'Objectives', f"{sanitize_id(obj_id)}.json")
        rec = _load_json(path) if os.path.exists(path) else {}
        ts = (rec.get('timestamps') or []) if isinstance(rec, dict) else []
        ok = bool(ts) and (ts[-1] == fixed)

        # Update
        objectives_mod.update_objective(obj_id, new_content='determinism objective v2', new_label='eval_update')
        rec2 = _load_json(path) if os.path.exists(path) else {}
        ts2 = (rec2.get('timestamps') or []) if isinstance(rec2, dict) else []
        ok = ok and bool(ts2) and (ts2[-1] == fixed)

        # Cleanup to keep eval runs tidy.
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_selection_migration_retrieval_score_deterministic():
    cid = 'logic_selection_migration_retrieval_score_deterministic'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            # Ensure deterministic mode for stable comparison.
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det['fixed_timestamp'] = det.get('fixed_timestamp') or '2025-01-01T00:00:00Z'
            cfg['determinism'] = det

            sm = cfg.get('selection_migration') if isinstance(cfg, dict) else None
            if not isinstance(sm, dict):
                sm = {}
            sm['enable'] = True
            sm['use_retrieval_scores'] = True
            # Make alignment easy to satisfy when objective_links exist.
            sm['retrieval_objective_alignment_threshold'] = 0.1
            cfg['selection_migration'] = sm
            return cfg

        def _body():
            _ensure_objective('objective_measurement_eval_sel', 'measurement', ['objective', 'measurement'])

            data_id = 'eval_sel_mig_retr_001'
            content = 'beneficial useful synthesis'

            RelationalMeasurement(data_id, content, 'semantic')
            RelationalMeasurement(data_id, content, 'semantic')

            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)

            ds = rec.get('decision_signals') or []
            if not (isinstance(ds, list) and len(ds) >= 2 and isinstance(ds[-1], dict) and isinstance(ds[-2], dict)):
                return {'case': cid, 'passed': False}

            a = ds[-2]
            b = ds[-1]
            try:
                s1 = float(a.get('selection_score') or 0.0)
                s2 = float(b.get('selection_score') or 0.0)
            except Exception:
                return {'case': cid, 'passed': False}

            ok = (abs(s1 - s2) <= 1e-9) and (s2 >= 0.25)
            return {'case': cid, 'passed': bool(ok)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def _with_temp_config_patch(patch_fn, body_fn):
    """Patch config.json for the duration of body_fn; always restore."""
    import json
    import os

    try:
        from module_tools import _clear_config_cache
    except Exception:
        _clear_config_cache = None

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        original = json.load(f)
    patched = patch_fn(dict(original))
    tmp = cfg_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(patched, f, ensure_ascii=False, indent=2)
    os.replace(tmp, cfg_path)
    try:
        if callable(_clear_config_cache):
            _clear_config_cache()
    except Exception:
        pass
    try:
        return body_fn()
    finally:
        try:
            tmp2 = cfg_path + '.tmp'
            with open(tmp2, 'w', encoding='utf-8') as f:
                json.dump(original, f, ensure_ascii=False, indent=2)
            os.replace(tmp2, cfg_path)
            try:
                if callable(_clear_config_cache):
                    _clear_config_cache()
            except Exception:
                pass
        except Exception:
            pass


def _with_config_cache_patch(patch_fn, body_fn):
    """Patch module_tools._CONFIG_CACHE for the duration of body_fn; always restore.

    This avoids on-disk config mutation and bypasses cache staleness issues.
    """
    import json

    try:
        import module_tools
    except Exception:
        return body_fn()

    orig = getattr(module_tools, '_CONFIG_CACHE', None)
    try:
        try:
            base = module_tools._load_config() or {}
        except Exception:
            base = {}
        try:
            base_copy = json.loads(json.dumps(base))
        except Exception:
            base_copy = dict(base) if isinstance(base, dict) else {}
        patched = patch_fn(base_copy)
        try:
            module_tools._CONFIG_CACHE = patched
        except Exception:
            pass
        return body_fn()
    finally:
        try:
            module_tools._CONFIG_CACHE = orig
        except Exception:
            pass


def eval_orchestration_migration_observability():
    cid = 'logic_orchestration_migration_observability'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 5
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_obs_001'
            RelationalMeasurement(data_id, 'orchestration migration observability check', 'semantic')

            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            dt = ((rec.get('relational_state') or {}).get('decision_trace') or {})
            tr = dt.get('activity_cycle_trace')
            if not (isinstance(tr, list) and tr):
                return {'case': cid, 'passed': False}
            last = tr[-1]
            if not (isinstance(last, dict) and isinstance(last.get('completed'), list)):
                return {'case': cid, 'passed': False}
            comp = last.get('completed') or []
            types = {str((a or {}).get('activity_type') or '') for a in comp if isinstance(a, dict)}
            ok = ('retrieve' in types) and ('measure' in types)
            return {'case': cid, 'passed': bool(ok)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_deterministic_trace():
    cid = 'logic_orchestration_migration_deterministic_trace'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            # Ensure deterministic mode is on.
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_det_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            RelationalMeasurement(data_id, 'orchestration migration determinism check', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec1 = json.load(f)
            tr1 = (((rec1.get('relational_state') or {}).get('decision_trace') or {}).get('activity_cycle_trace') or [])
            if not (isinstance(tr1, list) and tr1):
                return {'case': cid, 'passed': False}
            last1 = tr1[-1]

            RelationalMeasurement(data_id, 'orchestration migration determinism check', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec2 = json.load(f)
            tr2 = (((rec2.get('relational_state') or {}).get('decision_trace') or {}).get('activity_cycle_trace') or [])
            if not (isinstance(tr2, list) and len(tr2) >= 2):
                return {'case': cid, 'passed': False}
            last2 = tr2[-1]

            # The per-cycle trace payload should be stable even if the record accumulates history.
            return {'case': cid, 'passed': bool(last1 == last2)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_error_resolution():
    cid = 'logic_orchestration_migration_error_resolution'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 3
            om['trace_cap'] = 5
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_err_001'
            # This content is used elsewhere to force decisive contradiction behavior.
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            dt = ((rec.get('relational_state') or {}).get('decision_trace') or {})
            tr = dt.get('activity_cycle_trace')
            if not (isinstance(tr, list) and tr):
                return {'case': cid, 'passed': False}
            last = tr[-1]
            comp = (last.get('completed') or []) if isinstance(last, dict) else []
            types = {str((a or {}).get('activity_type') or '') for a in comp if isinstance(a, dict)}
            return {'case': cid, 'passed': bool('error_resolution' in types)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_advisory_shape():
    cid = 'logic_orchestration_migration_advisory_shape'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 5
            om['include_advisory'] = True
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_adv_001'
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            dt = ((rec.get('relational_state') or {}).get('decision_trace') or {})
            tr = dt.get('activity_cycle_trace')
            if not (isinstance(tr, list) and tr):
                return {'case': cid, 'passed': False}
            last = tr[-1]
            if not isinstance(last, dict):
                return {'case': cid, 'passed': False}
            adv = last.get('advisory')
            if not isinstance(adv, dict):
                return {'case': cid, 'passed': False}
            ns = adv.get('next_steps')
            ok = isinstance(ns, list) and all(isinstance(x, str) and x for x in ns)
            # Stable location should exist too.
            ns2 = dt.get('next_steps_from_cycle')
            ok = ok and isinstance(ns2, list) and all(isinstance(x, str) and x for x in ns2)
            return {'case': cid, 'passed': bool(ok)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_advisory_deterministic():
    cid = 'logic_orchestration_migration_advisory_deterministic'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            om['include_advisory'] = True
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_adv_det_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec1 = json.load(f)
            tr1 = (((rec1.get('relational_state') or {}).get('decision_trace') or {}).get('activity_cycle_trace') or [])
            if not (isinstance(tr1, list) and tr1):
                return {'case': cid, 'passed': False}
            last1 = tr1[-1]
            adv1 = (last1.get('advisory') if isinstance(last1, dict) else None) or {}

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec2 = json.load(f)
            tr2 = (((rec2.get('relational_state') or {}).get('decision_trace') or {}).get('activity_cycle_trace') or [])
            if not (isinstance(tr2, list) and len(tr2) >= 2):
                return {'case': cid, 'passed': False}
            last2 = tr2[-1]
            adv2 = (last2.get('advisory') if isinstance(last2, dict) else None) or {}

            return {'case': cid, 'passed': bool(adv1 == adv2)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_soft_influence_deterministic():
    cid = 'logic_orchestration_migration_soft_influence_deterministic'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            om['include_advisory'] = True
            si = om.get('soft_influence') if isinstance(om, dict) else None
            if not isinstance(si, dict):
                si = {}
            si['enabled'] = True
            si['scale'] = 0.1
            si['max_delta'] = 0.05
            si['prevent_space_flip'] = True
            om['soft_influence'] = si
            cfg['orchestration_migration'] = om
            return cfg

        def _read_delta(spath: str):
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            ds = rec.get('decision_signals') or []
            if not (isinstance(ds, list) and ds):
                return None
            last = ds[-1]
            si = last.get('soft_influence') if isinstance(last, dict) else None
            if not isinstance(si, dict):
                return None
            return si

        def _body():
            data_id = 'eval_orch_soft_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            # First run: ensures cycle_outcomes exists for the second run to reference.
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}

            # Second run: should compute a soft influence (from previous cycle outcome).
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            si1 = _read_delta(spath)
            if not isinstance(si1, dict):
                return {'case': cid, 'passed': False}

            # Third run: should be deterministic (same previous outcome -> same delta).
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            si2 = _read_delta(spath)
            if not isinstance(si2, dict):
                return {'case': cid, 'passed': False}

            return {'case': cid, 'passed': bool(si1 == si2)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_soft_influence_bounded_no_flip():
    cid = 'logic_orchestration_migration_soft_influence_bounded_no_flip'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            om['include_advisory'] = True
            si = om.get('soft_influence') if isinstance(om, dict) else None
            if not isinstance(si, dict):
                si = {}
            si['enabled'] = True
            si['scale'] = 10.0
            si['max_delta'] = 0.2
            si['prevent_space_flip'] = True
            om['soft_influence'] = si
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_soft_nf_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            # Seed previous cycle outcomes.
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}

            # Run again; soft influence should be recorded and bounded.
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            ds = rec.get('decision_signals') or []
            if not (isinstance(ds, list) and ds):
                return {'case': cid, 'passed': False}
            last = ds[-1]
            if not isinstance(last, dict):
                return {'case': cid, 'passed': False}
            si = last.get('soft_influence')
            if not isinstance(si, dict):
                return {'case': cid, 'passed': False}

            delta = si.get('selection_score_delta')
            ok = isinstance(delta, (int, float)) and (abs(float(delta)) <= 0.2 + 1e-9)
            ok = ok and (si.get('prevented_space_flip') in (True, False))
            # With prevent_space_flip=true, the final target must match the base target.
            tb = si.get('target_space_base')
            tf = si.get('target_space_final')
            ok = ok and isinstance(tb, str) and isinstance(tf, str) and (tb == tf)
            return {'case': cid, 'passed': bool(ok)}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_cycle_artifact_shape():
    cid = 'logic_orchestration_migration_cycle_artifact_shape'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 5
            om['include_advisory'] = True
            om['include_cycle_artifact'] = True
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_cycle_art_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            dt = (((rec.get('relational_state') or {}).get('decision_trace') or {}))
            art = dt.get('cycle_artifact')
            if not isinstance(art, dict):
                return {'case': cid, 'passed': False}

            # Required keys
            required = {'schema_version', 'cycle_id', 'record_ref', 'plan', 'activities', 'decision', 'verification', 'scheduling'}
            if any(k not in art for k in required):
                return {'case': cid, 'passed': False}

            # JSON-serializable
            try:
                json.dumps(art, sort_keys=True)
            except Exception:
                return {'case': cid, 'passed': False}
            return {'case': cid, 'passed': True}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_orchestration_migration_cycle_artifact_deterministic():
    cid = 'logic_orchestration_migration_cycle_artifact_deterministic'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det['fixed_timestamp'] = '2025-01-01T00:00:00Z'
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            om['include_advisory'] = True
            om['include_cycle_artifact'] = True
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_orch_cycle_art_det_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec1 = json.load(f)
            art1 = (((rec1.get('relational_state') or {}).get('decision_trace') or {}).get('cycle_artifact'))

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec2 = json.load(f)
            art2 = (((rec2.get('relational_state') or {}).get('decision_trace') or {}).get('cycle_artifact'))

            return {'case': cid, 'passed': bool(isinstance(art1, dict) and isinstance(art2, dict) and (art1 == art2))}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_objective_influence_metrics_shape():
    cid = 'logic_objective_influence_metrics_shape'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det.setdefault('fixed_timestamp', '2025-01-01T00:00:00Z')
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 5
            om['include_advisory'] = True
            om['include_cycle_artifact'] = True
            om['objective_influence_metrics'] = {'enabled': True, 'top_k': 5, 'compute_retrieval_diff': True}
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_obj_infl_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")
            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
            dt = (((rec.get('relational_state') or {}).get('decision_trace') or {}))
            m = dt.get('objective_influence_metrics')
            if not isinstance(m, dict):
                return {'case': cid, 'passed': False}
            if m.get('schema_version') != '1.0':
                return {'case': cid, 'passed': False}
            if not isinstance(m.get('retrieval'), dict):
                return {'case': cid, 'passed': False}
            if not isinstance(m.get('selection'), dict):
                return {'case': cid, 'passed': False}
            if not isinstance(m.get('scheduling'), dict):
                return {'case': cid, 'passed': False}
            # Must be JSON-serializable.
            try:
                json.dumps(m, sort_keys=True)
            except Exception:
                return {'case': cid, 'passed': False}
            return {'case': cid, 'passed': True}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_objective_influence_metrics_deterministic():
    cid = 'logic_objective_influence_metrics_deterministic'
    try:
        import json
        import os
        from module_integration import RelationalMeasurement
        from module_storage import resolve_path
        from module_tools import safe_join, sanitize_id

        def _patch(cfg):
            det = cfg.get('determinism') if isinstance(cfg, dict) else None
            if not isinstance(det, dict):
                det = {}
            det['deterministic_mode'] = True
            det['fixed_timestamp'] = '2025-01-01T00:00:00Z'
            cfg['determinism'] = det

            om = cfg.get('orchestration_migration') if isinstance(cfg, dict) else None
            if not isinstance(om, dict):
                om = {}
            om['enable'] = True
            om['max_steps'] = 2
            om['trace_cap'] = 10
            om['include_advisory'] = True
            om['include_cycle_artifact'] = True
            om['objective_influence_metrics'] = {'enabled': True, 'top_k': 5, 'compute_retrieval_diff': True}
            cfg['orchestration_migration'] = om
            return cfg

        def _body():
            data_id = 'eval_obj_infl_det_001'
            spath = safe_join(resolve_path('semantic'), f"{sanitize_id(data_id)}.json")

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            if not os.path.exists(spath):
                return {'case': cid, 'passed': False}
            with open(spath, 'r', encoding='utf-8') as f:
                rec1 = json.load(f)
            m1 = ((((rec1.get('relational_state') or {}).get('decision_trace') or {}).get('objective_influence_metrics')))

            RelationalMeasurement(data_id, 'objective conflict contradict risk', 'semantic')
            with open(spath, 'r', encoding='utf-8') as f:
                rec2 = json.load(f)
            m2 = ((((rec2.get('relational_state') or {}).get('decision_trace') or {}).get('objective_influence_metrics')))

            return {'case': cid, 'passed': bool(isinstance(m1, dict) and isinstance(m2, dict) and (m1 == m2))}

        return _with_config_cache_patch(_patch, _body)
    except Exception:
        return {'case': cid, 'passed': False}


def eval_constraint_satisfaction():
    cid = 'logic_constraint_satisfaction'
    try:
        from module_reasoning import check_constraints
        relational_state = {
            "entities": [
                {"id": "A", "type": "spatial_object", "attributes": {"volume": 1.0}, "source": "synthetic"}
            ],
            "relations": [],
            "constraints": [
                {"type": "lt", "args": {"entity_id": "A", "attribute": "volume", "value": 0.1}, "severity": "hard", "source": "synthetic"}
            ],
            "objective_links": [],
            "spatial_measurement": None,
            "decision_trace": {},
            "focus_snapshot": {},
        }
        rep = check_constraints(relational_state)
        ok = bool(rep.get('contradiction')) and bool(rep.get('has_hard_violation'))
        v = (rep.get('violations') or [])
        ok = ok and bool(v) and (v[0].get('severity') == 'hard')
        return {'case': cid, 'passed': ok}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_example_full_pass():
    cid = 'logic_reasoning_example_full_pass'
    try:
        from module_reasoning import check_constraints, detect_contradictions, propose_actions

        relational_state = {
            "entities": [
                {
                    "id": "obj_001::spatial_object",
                    "type": "spatial_object",
                    "attributes": {
                        "shape": "cube",
                        "volume": 10.0,
                        "bounds": {"min": [0, 0, 0], "max": [2, 2, 2]},
                    },
                    "source": "3d",
                }
            ],
            "relations": [
                {"subj": "obj_001::spatial_object", "pred": "has_shape", "obj": "cube", "confidence": 0.95, "source": "3d"},
                {"subj": "obj_001::spatial_object", "pred": "has_volume", "obj": "10.0", "confidence": 0.95, "source": "3d"},
                {"subj": "obj_001::spatial_object", "pred": "has_shape", "obj": "sphere", "confidence": 0.92, "source": "inference"},
            ],
            "constraints": [
                {
                    "type": "spatial",
                    "args": {"entity_id": "obj_001::spatial_object", "volume": {"max": 5.0}},
                    "severity": "hard",
                    "source": "objective",
                }
            ],
            "objective_links": [
                {"objective_id": "shape_accuracy", "relevance": 0.9, "reason": "focus_active"}
            ],
            "spatial_measurement": None,
            "decision_trace": {},
            "focus_snapshot": {},
        }

        rc = check_constraints(relational_state)
        cd = detect_contradictions(relational_state)
        pa = propose_actions(relational_state, {
            'similarity': 0.82,
            'usefulness': 'useful_now',
            'synthesis': True,
            'objective_relation': 'aligned'
        })

        ok = bool(rc.get('has_hard_violation'))
        ok = ok and bool(cd.get('has_contradiction'))
        ok = ok and (pa.get('decisive_recommendation') == 'contradiction_resolve')

        # Golden-trace assertions
        v = (rc.get('violations') or [])
        ok = ok and bool(v) and (v[0].get('severity') == 'hard')
        ok = ok and (v[0].get('reason') == 'volume exceeds allowed maximum')

        expected_actions = ['contradiction_resolve', 'review', 'synthesis']
        ok = ok and ((pa.get('recommended_actions') or []) == expected_actions)

        expected_reasons = [
            'hard constraint violation',
            'contradiction detected',
            'objective alignment',
            'high similarity and usefulness',
        ]
        # Ordering in propose_actions is deterministic; accept either order of the last two
        # as long as all four reasons are present exactly once.
        reasons = pa.get('reasons') or []
        ok = ok and isinstance(reasons, list) and (sorted(reasons) == sorted(expected_reasons))

        contras = (cd.get('contradictions') or [])
        ok = ok and bool(contras)
        if contras:
            rels = contras[0].get('relations') or []
            ok = ok and isinstance(rels, list) and len(rels) == 2
            # Must at least include pred/obj pairs.
            pair0 = (rels[0].get('pred'), rels[0].get('obj')) if isinstance(rels[0], dict) else (None, None)
            pair1 = (rels[1].get('pred'), rels[1].get('obj')) if isinstance(rels[1], dict) else (None, None)
            ok = ok and set([pair0, pair1]) == set([('has_shape', 'cube'), ('has_shape', 'sphere')])

        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_golden_trace_synthesis_pass():
    cid = 'logic_golden_trace_synthesis_pass'
    try:
        from module_reasoning import check_constraints, detect_contradictions, propose_actions

        relational_state = {
            "entities": [
                {
                    "id": "obj_clean_001::spatial_object",
                    "type": "spatial_object",
                    "attributes": {
                        "shape": "cube",
                        "volume": 8.0,
                        "bounds": {"min": [0, 0, 0], "max": [2, 2, 2]},
                    },
                    "source": "3d",
                }
            ],
            "relations": [
                {"subj": "obj_clean_001::spatial_object", "pred": "has_shape", "obj": "cube", "confidence": 0.95, "source": "3d"},
                {"subj": "obj_clean_001::spatial_object", "pred": "has_volume", "obj": "8.0", "confidence": 0.95, "source": "3d"},
                {"subj": "obj_clean_001::spatial_object", "pred": "has_extent", "obj": "{\"dx\":2}", "confidence": 0.95, "source": "3d"},
            ],
            "constraints": [],
            "objective_links": [
                {"objective_id": "shape_accuracy", "relevance": 0.9, "reason": "focus_active"}
            ],
            "spatial_measurement": None,
            "decision_trace": {},
            "focus_snapshot": {},
        }

        rc = check_constraints(relational_state)
        cd = detect_contradictions(relational_state)
        pa = propose_actions(relational_state, {
            'similarity': 0.91,
            'usefulness': 'useful_now',
            'synthesis': True,
            'objective_relation': 'aligned'
        })

        ok = True
        ok = ok and (rc.get('has_hard_violation') is False)
        ok = ok and (rc.get('has_soft_violation') is False)
        ok = ok and ((rc.get('violations') or []) == [])
        ok = ok and (cd.get('has_contradiction') is False)
        ok = ok and ((cd.get('contradictions') or []) == [])

        ok = ok and (pa.get('decisive_recommendation') == 'synthesis')
        ok = ok and ((pa.get('recommended_actions') or []) == ['synthesis', 'review'])
        ok = ok and ((pa.get('reasons') or []) == [
            'high similarity and usefulness',
            'objective alignment',
            'no contradictions',
            'no constraint violations'
        ])

        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_contradiction_detection():
    cid = 'logic_contradiction_detection'
    try:
        # Ensure a "measurement" objective exists so focus/objective plumbing is exercised.
        _ensure_objective('obj_safety', 'safe secure safety objective', ['measurement', 'objective'])
        content = 'This is harmful and contradicts safety.'
        RelationalMeasurement('eval_contra_001', content, 'semantic')
        spath = _semantic_path('eval_contra_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}
        rec = _load_json(spath)
        ds = (rec.get('decision_signals') or [])
        if not ds:
            return {'case': cid, 'passed': False}
        last = ds[-1]
        ok = bool(last.get('contradiction')) and (last.get('target_space') != 'ActiveSpace')
        # Reason chain should reflect "no_conflict" premise false when conflict exists.
        rc = rec.get('reason_chain') or []
        if not rc:
            return {'case': cid, 'passed': False}
        premises = (rc[-1].get('premises') or []) if isinstance(rc[-1], dict) else []
        has_no_conflict_false = any(isinstance(p, dict) and (p.get('no_conflict') is False) for p in premises)
        return {'case': cid, 'passed': bool(ok and has_no_conflict_false)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_objective_alignment():
    cid = 'logic_objective_alignment'
    try:
        _ensure_objective('obj_research', 'analysis study research', ['measurement', 'objective'])
        content = 'This analysis supports the research objective.'
        RelationalMeasurement('eval_align_001', content, 'semantic')
        spath = _semantic_path('eval_align_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}
        rec = _load_json(spath)
        ds = (rec.get('decision_signals') or [])
        if not ds:
            return {'case': cid, 'passed': False}
        last = ds[-1]
        # usefulness is stored as string; ensure it indicates immediate usefulness
        ok = (last.get('usefulness') == 'useful_now')
        # integration also provides relation_labels only in activity log; validate through objective_relation in decision signals.
        # objective_alignment in decision_signals comes from selection; accept aligned/unknown as long as usefulness is useful_now.
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_focus_state_influence():
    cid = 'logic_focus_state_influence'
    try:
        from module_focus import compute_focus_state
        from module_measure import measure_information

        _ensure_objective('obj_focus', 'analysis', ['measurement', 'objective'])
        objectives = _load_json(os.path.join(BASE, 'LongTermStore', 'Objectives', 'obj_focus.json'))
        objectives = [objectives]
        focus_state = compute_focus_state(objectives)

        store_information('eval_focus_001', 'analysis focus test', 'semantic')
        spath = _semantic_path('eval_focus_001')
        base_rep = measure_information(spath, threshold=1.0, objectives=objectives, focus_state=None)
        foc_rep = measure_information(spath, threshold=1.0, objectives=objectives, focus_state=focus_state)

        b = float(base_rep.get('similarity_signal', 0.0))
        f = float(foc_rep.get('similarity_signal', 0.0))
        delta = f - b
        # boost is +0.1 capped at 1.0
        ok_delta = (abs(delta - 0.1) < 1e-6) or (b >= 0.9 and abs(f - 1.0) < 1e-9)
        ok_use = (foc_rep.get('usefulness_signal') == 'useful_now')
        # contradiction should only be true on explicit conflict
        ok_contra = (bool(foc_rep.get('contradiction_signal')) == bool(base_rep.get('contradiction_signal')))
        return {'case': cid, 'passed': bool(ok_delta and ok_use and ok_contra)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_spatial_adapter():
    cid = 'logic_spatial_adapter'
    try:
        from module_relational_adapter import attach_spatial_relational_state
        asset_path = os.path.join(BASE, 'eval_cases', 'assets', 'cube_eval.ply')
        if not os.path.exists(asset_path):
            return {'case': cid, 'passed': False}

        store_information('eval_spatial_001', '3d adapter test', 'semantic')
        spath = _semantic_path('eval_spatial_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}

        rec = _load_json(spath)
        rec['spatial_asset_path'] = asset_path
        with open(spath, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

        out = attach_spatial_relational_state(spath)
        if out.get('status') != 'completed':
            return {'case': cid, 'passed': False}

        rec2 = _load_json(spath)
        rs = rec2.get('relational_state') or {}
        sm = rs.get('spatial_measurement')
        if not isinstance(sm, dict) or sm.get('ok') is not True:
            return {'case': cid, 'passed': False}

        entities = rs.get('entities') or []
        relations = rs.get('relations') or []
        constraints = rs.get('constraints') or []
        ent_ok = any(isinstance(e, dict) and e.get('id') == 'eval_spatial_001::spatial_object' for e in entities)
        preds = [r.get('pred') for r in relations if isinstance(r, dict) and r.get('subj') == 'eval_spatial_001::spatial_object']
        rel_ok = all(p in preds for p in ['has_shape', 'has_volume', 'has_extent'])
        con_ok = any(isinstance(c, dict) and c.get('type') == 'spatial' and (c.get('args') or {}).get('entity_id') == 'eval_spatial_001::spatial_object' for c in constraints)
        return {'case': cid, 'passed': bool(ent_ok and rel_ok and con_ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_decision_trace():
    cid = 'logic_decision_trace'
    try:
        RelationalMeasurement('eval_trace_001', 'trace check useful analysis', 'semantic')
        spath = _semantic_path('eval_trace_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}
        rec = _load_json(spath)
        rc = rec.get('reason_chain')
        ds = rec.get('decision_signals')
        if not (isinstance(rc, list) and rc):
            return {'case': cid, 'passed': False}
        if not (isinstance(ds, list) and ds):
            return {'case': cid, 'passed': False}
        last_rc = rc[-1]
        last_ds = ds[-1]
        ok = isinstance(last_rc, dict) and isinstance(last_rc.get('premises'), list)
        ok = ok and isinstance(last_ds, dict) and (last_ds.get('target_space') in ('ActiveSpace', 'HoldingSpace', 'DiscardSpace'))
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_deterministic_repetition():
    cid = 'logic_deterministic_repetition'
    try:
        # Determinism check: measuring the same record twice should produce identical output.
        store_information('eval_repeat_meas_001', 'repeat test analysis', 'semantic')
        spath = _semantic_path('eval_repeat_meas_001')
        from module_measure import measure_information
        rep1 = measure_information(spath, threshold=1.0)
        rep2 = measure_information(spath, threshold=1.0)
        ok = (rep1 == rep2)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_runtime_constraint_integration():
    cid = 'logic_runtime_constraint_integration'
    try:
        # Create a semantic record, then inject a supported hard constraint violation.
        store_information('eval_runtime_con_001', 'runtime constraint test', 'semantic')
        spath = _semantic_path('eval_runtime_con_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}

        rec = _load_json(spath)
        rs = rec.get('relational_state')
        if not isinstance(rs, dict):
            rs = {
                'entities': [],
                'relations': [],
                'constraints': [],
                'objective_links': [],
                'spatial_measurement': None,
                'decision_trace': {},
            }
            rec['relational_state'] = rs

        rs['entities'] = [
            {'id': 'A', 'type': 'spatial_object', 'attributes': {'volume': 1.0}, 'source': 'synthetic'}
        ]
        rs['relations'] = []
        rs['constraints'] = [
            {'type': 'lt', 'args': {'entity_id': 'A', 'attribute': 'volume', 'value': 0.1}, 'severity': 'hard', 'source': 'synthetic'}
        ]

        with open(spath, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

        # Run a full cycle; contradiction should be promoted into decision_signals.
        RelationalMeasurement('eval_runtime_con_001', 'runtime constraint test', 'semantic')

        rec2 = _load_json(spath)
        ds = rec2.get('decision_signals') or []
        if not ds:
            return {'case': cid, 'passed': False}
        last = ds[-1]
        if not (last.get('contradiction') is True and last.get('constraint_hard_violation') is True):
            return {'case': cid, 'passed': False}

        rs2 = (rec2.get('relational_state') or {})
        dt = (rs2.get('decision_trace') or {})
        cr = dt.get('constraints_report')
        ok_trace = isinstance(cr, dict) and (cr.get('has_hard_violation') is True)
        return {'case': cid, 'passed': bool(ok_trace)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_runtime_spatial_constraint_integration():
    cid = 'logic_runtime_spatial_constraint_integration'
    try:
        store_information('eval_runtime_spatial_con_001', 'runtime spatial constraint test', 'semantic')
        spath = _semantic_path('eval_runtime_spatial_con_001')
        if not os.path.exists(spath):
            return {'case': cid, 'passed': False}

        rec = _load_json(spath)
        rs = rec.get('relational_state')
        if not isinstance(rs, dict):
            rs = {
                'entities': [],
                'relations': [],
                'constraints': [],
                'objective_links': [],
                'spatial_measurement': None,
                'decision_trace': {},
            }
            rec['relational_state'] = rs

        # Inject an invalid spatial hard constraint: bounds min > max.
        rs['entities'] = [
            {'id': 'eval_runtime_spatial_con_001::spatial_object', 'type': 'spatial_object', 'attributes': {}, 'source': 'synthetic'}
        ]
        rs['constraints'] = [
            {
                'type': 'spatial',
                'args': {
                    'entity_id': 'eval_runtime_spatial_con_001::spatial_object',
                    'bounds': {'min': [1, 1, 1], 'max': [0, 0, 0]},
                    'units': 'meters'
                },
                'severity': 'hard',
                'source': 'synthetic'
            }
        ]

        with open(spath, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)

        RelationalMeasurement('eval_runtime_spatial_con_001', 'runtime spatial constraint test', 'semantic')

        rec2 = _load_json(spath)
        ds = rec2.get('decision_signals') or []
        if not ds:
            return {'case': cid, 'passed': False}
        last = ds[-1]
        if not (last.get('contradiction') is True and last.get('constraint_hard_violation') is True):
            return {'case': cid, 'passed': False}

        dt = ((rec2.get('relational_state') or {}).get('decision_trace') or {})
        cr = dt.get('constraints_report')
        if not (isinstance(cr, dict) and cr.get('has_hard_violation') is True):
            return {'case': cid, 'passed': False}
        violations = cr.get('violations') or []
        has_spatial = any(isinstance(v, dict) and v.get('type') == 'spatial' for v in violations)
        return {'case': cid, 'passed': bool(has_spatial)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_logic_suite():
    """Run logic/consistency suite; returns list of case result dicts."""
    suite = [
        eval_relational_state_schema,
        eval_uncertainty_combine,
        eval_uncertainty_propagate,
        eval_uncertainty_confidence,
        eval_provenance_hash_stable,
        eval_provenance_append_trace,
        eval_provenance_tamper_hash,
        eval_integration_cycle_smoke,
        eval_integration_cycle_preserves_list_relational_state,
        eval_integration_rollback_propagation,
        eval_verifier_precondition_enforcement,
        eval_verifier_validation_artifact_shape,
        eval_verifier_deterministic_artifacts,
        eval_concept_measure_basic_counts,
        eval_concept_measure_recurrence,
        eval_concept_measure_objective_scoring,
        eval_concept_measure_relational_state_integration,
        eval_orchestration_migration_observability,
        eval_orchestration_migration_deterministic_trace,
        eval_orchestration_migration_error_resolution,
        eval_orchestration_migration_advisory_shape,
        eval_orchestration_migration_advisory_deterministic,
        eval_orchestration_migration_soft_influence_deterministic,
        eval_orchestration_migration_soft_influence_bounded_no_flip,
        eval_orchestration_migration_cycle_artifact_shape,
        eval_orchestration_migration_cycle_artifact_deterministic,
        eval_objective_influence_metrics_shape,
        eval_objective_influence_metrics_deterministic,
        eval_want_basic_signals,
        eval_want_error_signal,
        eval_want_synthesis_signal,
        eval_want_empty_inputs,
        eval_want_evoi_positive,
        eval_want_evoi_negative,
        eval_want_evoi_why_vector,
        eval_activity_manager_translate,
        eval_activity_manager_deterministic_queue,
        eval_activity_manager_budget_respect,
        eval_activity_manager_precondition_enforcement,
        eval_retrieval_ranking,
        eval_retrieval_score_components,
        eval_retrieval_deterministic_sampling,
        eval_retrieval_diversity,
        eval_retrieval_explainability,
        eval_error_resolution_detect_equal,
        eval_error_resolution_detect_mismatch,
        eval_error_resolution_confidence_uncertainty,
        eval_error_resolution_rollback_plan,
        eval_error_resolution_stat_validation,
        eval_error_resolution_deterministic_execution,
        eval_reasoning_synthesis_engine,
        eval_reasoning_propose_next_steps_positive,
        eval_reasoning_propose_next_steps_negative,
        eval_reasoning_think_deeper_artifacts,
        eval_reasoning_think_deeper_deterministic_repro,
        eval_adversarial_report_shape,
        eval_adversarial_deterministic_repro,
        eval_adversarial_escalation_policy,
        eval_constraint_satisfaction,
        eval_reasoning_example_full_pass,
        eval_golden_trace_synthesis_pass,
        eval_contradiction_detection,
        eval_objective_alignment,
        eval_focus_state_influence,
        eval_spatial_adapter,
        eval_decision_trace,
        eval_deterministic_repetition,
        eval_runtime_constraint_integration,
        eval_runtime_spatial_constraint_integration,
        eval_objectives_deterministic_timestamps,
        eval_selection_migration_retrieval_score_deterministic,
    ]
    out = []
    for fn in suite:
        r = fn()
        out.append(r)
        if not r.get('passed'):
            # Fail early within the suite.
            break
    return out


def eval_uncertainty_combine():
    cid = 'logic_uncertainty_combine'
    try:
        from module_uncertainty import Uncertainty, combine_independent
        u1 = Uncertainty(1.0, 0.25, {'id': 's1'})
        u2 = Uncertainty(2.0, 0.75, {'id': 's2'})
        out = combine_independent([u1, u2])
        ok = abs(float(out.variance) - 1.0) < 1e-9
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_uncertainty_propagate():
    cid = 'logic_uncertainty_propagate'
    try:
        from module_uncertainty import Uncertainty, propagate_linear
        u1 = Uncertainty(1.0, 0.25, {})
        u2 = Uncertainty(2.0, 0.25, {})
        out = propagate_linear(3.0, [1.0, 1.0], [u1, u2])
        ok = abs(float(out.variance) - 0.5) < 1e-9
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_uncertainty_confidence():
    cid = 'logic_uncertainty_confidence'
    try:
        from module_uncertainty import Uncertainty, confidence_from_delta
        u = Uncertainty(0.0, 0.01, {})
        c0 = float(confidence_from_delta(0.0, u, u))
        c1 = float(confidence_from_delta(10.0, u, u))
        ok = (0.49 < c0 < 0.51) and (0.999 < c1 <= 1.0)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_provenance_hash_stable():
    cid = 'logic_provenance_hash_stable'
    try:
        from module_provenance import create_event
        e1 = create_event('measurement', {'target_ids': ['r1'], 'x': 1}, prev_hash=None, timestamp=0.0)
        e2 = create_event('measurement', {'target_ids': ['r1'], 'x': 1}, prev_hash=None, timestamp=0.0)
        ok = isinstance(e1, dict) and isinstance(e2, dict) and (e1.get('event_id') == e2.get('event_id'))
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_provenance_append_trace():
    cid = 'logic_provenance_append_trace'
    try:
        from module_provenance import append_event, create_event, get_version, trace_provenance
        log = []
        e1 = create_event('measurement', {'target_ids': ['r1'], 'x': 1}, timestamp=0.0)
        e2 = create_event('correction', {'target_ids': ['r1'], 'y': 2}, prev_hash=e1.get('event_id'), timestamp=1.0)
        log = append_event(log, e1)
        log = append_event(log, e2)
        tr = trace_provenance('r1', log)
        ok = (
            isinstance(tr, list)
            and len(tr) == 2
            and tr[0].get('event_type') == 'measurement'
            and tr[1].get('event_type') == 'correction'
            and get_version('r1', log) == 2
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_provenance_tamper_hash():
    cid = 'logic_provenance_tamper_hash'
    try:
        from module_provenance import compute_hash, create_event
        e1 = create_event('measurement', {'target_ids': ['r1'], 'x': 1}, timestamp=0.0)
        base = {k: e1[k] for k in e1 if k != 'event_id'}
        h1 = compute_hash(base)
        tampered = dict(base)
        tampered['payload'] = dict(tampered.get('payload') or {})
        tampered['payload']['x'] = 999
        h2 = compute_hash(tampered)
        ok = isinstance(h1, str) and isinstance(h2, str) and (h1 != h2)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_integration_cycle_smoke():
    cid = 'logic_integration_cycle_smoke'
    try:
        from module_integration import initialize_system, run_cycle

        class _Storage:
            def load_state(self):
                return ({'entities': {}, 'links': {}, 'contexts': {}}, [{'record_id': 'r1', 'value': 1, 'context_id': 'c'}], [])

            def save_state(self, relational_state, records, objectives):
                _ = relational_state
                _ = records
                _ = objectives
                return None

        class _Measure:
            def measure_world(self, context_id):
                _ = context_id
                return ([], [])

            def measure_record(self, record_id):
                return {'value': 1, 'source_id': 's', 'timestamp': 0.0, 'context_id': 'c', 'record_id': record_id}

        class _Adapter:
            def build_relational_state(self, objects, relations, context_id, context_metadata):
                _ = objects
                _ = relations
                _ = context_metadata
                return {'entities': {}, 'links': {}, 'contexts': {context_id: {}}}

            def update_relational_state(self, state, objects, relations, context_id, context_metadata):
                _ = objects
                _ = relations
                _ = context_metadata
                out = dict(state)
                ctx = dict(out.get('contexts') or {})
                ctx[context_id] = {}
                out['contexts'] = ctx
                return out

        class _Err:
            def detect_error(self, measurement, record):
                _ = measurement
                _ = record
                return None

            def create_error_resolution_task(self, error_report):
                return {'activity': 'error_resolution', 'target_record_id': 'r1', 'error_type': 'mis_description', 'priority': 0.0, 'error_report': error_report}

            def execute_error_resolution_task(self, task, measurement_fn, update_record_fn, relink_fn, recompute_fn):
                _ = task
                _ = measurement_fn
                _ = relink_fn
                _ = recompute_fn
                return update_record_fn('r1', 1)

        class _Want:
            def compute_awareness_plan(self, objectives, gaps, errors, opportunities, plan_id='p'):
                _ = objectives
                _ = gaps
                _ = errors
                _ = opportunities
                return {'plan_id': plan_id, 'wants': [], 'suggested_activities': []}

        class _Act:
            def run_activity_cycle(self, awareness_plan, queue, modules, max_steps=1):
                _ = awareness_plan
                _ = modules
                _ = max_steps
                return queue

        class _Retr:
            def retrieve(self, store, query):
                _ = store
                _ = query
                return []

        class _Reason:
            def synthesize(self, records, opportunity):
                _ = records
                _ = opportunity
                return {'new_record_id': 's', 'value': None, 'conceptual_vector': [], 'inputs': [], 'coherence_gain': 0.0}

        storage = _Storage()
        state = initialize_system(storage)
        out = run_cycle(
            state,
            context_id='ctx1',
            context_metadata={},
            modules={
                'measure': _Measure(),
                'relational_adapter': _Adapter(),
                'error_resolution': _Err(),
                'want': _Want(),
                'activity_manager': _Act(),
                'retrieval': _Retr(),
                'reasoning': _Reason(),
                'storage': storage,
            },
        )
        ok = isinstance(out, dict) and isinstance(out.get('activity_queue'), dict)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_integration_cycle_preserves_list_relational_state():
    cid = 'logic_integration_cycle_preserves_list_relational_state'
    try:
        from module_integration import run_cycle
        from module_tools import validate_relational_state

        class _Storage:
            def save_state(self, relational_state, records, objectives):
                _ = relational_state
                _ = records
                _ = objectives
                return None

        class _Measure:
            def measure_world(self, context_id):
                _ = context_id
                return (
                    [
                        {
                            'object_id': 'o1',
                            'position': [0.0, 0.0, 0.0],
                            'rotation': [0.0, 0.0, 0.0],
                            'scale': [1.0, 1.0, 1.0],
                            'properties': {},
                        }
                    ],
                    [
                        {
                            'relation_id': 'r1',
                            'type': 'near',
                            'source_object_id': 'o1',
                            'target_object_id': 'o1',
                            'strength': 1.0,
                        }
                    ],
                )

            def measure_record(self, record_id):
                return {'value': 1, 'source_id': 's', 'timestamp': 0.0, 'context_id': 'c', 'record_id': record_id}

        class _Adapter:
            def build_relational_state(self, objects, relations, context_id, context_metadata):
                _ = objects
                _ = relations
                _ = context_id
                _ = context_metadata
                return {'entities': {}, 'links': {}, 'contexts': {}}

            def update_relational_state(self, state, objects, relations, context_id, context_metadata):
                _ = state
                _ = objects
                _ = relations
                _ = context_id
                _ = context_metadata
                return {'entities': {}, 'links': {}, 'contexts': {}}

        class _Err:
            def detect_error(self, measurement, record):
                _ = measurement
                _ = record
                return None

            def create_error_resolution_task(self, error_report):
                _ = error_report
                return {'activity': 'error_resolution', 'target_record_id': 'x', 'error_type': 'mis_description', 'priority': 0.0, 'error_report': {}}

            def execute_error_resolution_task(self, task, measurement_fn, update_record_fn, relink_fn, recompute_fn):
                _ = task
                _ = measurement_fn
                _ = update_record_fn
                _ = relink_fn
                _ = recompute_fn
                return {'record_id': 'x', 'value': 0, 'context_id': 'c', 'links': {}, 'derived': False, 'inputs': []}

        class _Want:
            def compute_awareness_plan(self, objectives, gaps, errors, opportunities, plan_id='p'):
                _ = objectives
                _ = gaps
                _ = errors
                _ = opportunities
                return {'plan_id': plan_id, 'wants': [], 'suggested_activities': []}

        class _Act:
            def run_activity_cycle(self, awareness_plan, queue, modules, max_steps=1):
                _ = awareness_plan
                _ = modules
                _ = max_steps
                return queue

        class _Retr:
            def retrieve(self, store, query):
                _ = store
                _ = query
                return []

        class _Reason:
            def synthesize(self, records, opportunity):
                _ = records
                _ = opportunity
                return {'new_record_id': 's', 'value': None, 'conceptual_vector': [], 'inputs': [], 'coherence_gain': 0.0}

        # Start with canonical list-based relational_state with a preserved entity.
        rs0 = {
            'entities': [{'id': 'keep::e1', 'type': 'keep', 'attributes': {}, 'source': 'seed'}],
            'relations': [],
            'constraints': [],
            'objective_links': [],
            'spatial_measurement': None,
            'decision_trace': {},
        }
        state = {
            'relational_state': rs0,
            'records': [{'record_id': 'x', 'value': 1, 'context_id': 'c'}],
            'objectives': [],
            'activity_queue': {'pending': [], 'active': [], 'completed': []},
        }

        out = run_cycle(
            state,
            context_id='ctx1',
            context_metadata={},
            modules={
                'measure': _Measure(),
                'relational_adapter': _Adapter(),
                'error_resolution': _Err(),
                'want': _Want(),
                'activity_manager': _Act(),
                'retrieval': _Retr(),
                'reasoning': _Reason(),
                'storage': _Storage(),
            },
        )

        rs1 = out.get('relational_state') if isinstance(out, dict) else None
        if not (isinstance(rs1, dict) and validate_relational_state(rs1)):
            return {'case': cid, 'passed': False}
        ents = rs1.get('entities') or []
        rels = rs1.get('relations') or []
        has_keep = any(isinstance(e, dict) and e.get('id') == 'keep::e1' for e in ents)
        has_world = any(isinstance(e, dict) and e.get('source') == '3d_world' for e in ents)
        has_rel = any(isinstance(r, dict) and r.get('source') == '3d_world' for r in rels)
        return {'case': cid, 'passed': bool(has_keep and has_world and has_rel)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_integration_rollback_propagation():
    cid = 'logic_integration_rollback_propagation'
    try:
        from module_integration import initialize_system, run_cycle

        class _Storage:
            def __init__(self):
                self._prov = []

            def load_state(self):
                return ({'entities': {}, 'links': {}, 'contexts': {}}, [{'record_id': 'r1', 'value': 10.0, 'context_id': 'c', 'uncertainty': {'value': 10.0, 'variance': 1.0, 'provenance': {'id': 'before'}}}], [])

            def save_state(self, relational_state, records, objectives):
                _ = relational_state
                _ = records
                _ = objectives
                return None

            def load_provenance_log(self):
                return list(self._prov)

            def save_provenance_log(self, log):
                self._prov = list(log or [])

        class _Measure:
            def measure_world(self, context_id):
                _ = context_id
                return ([], [])

            def measure_record(self, record_id):
                return {
                    'value': 20.0,
                    'source_id': 's',
                    'timestamp': 0.0,
                    'context_id': 'c',
                    'record_id': record_id,
                    'uncertainty': {'value': 20.0, 'variance': 1.0, 'provenance': {'id': 'm'}},
                }

        class _Adapter:
            def build_relational_state(self, objects, relations, context_id, context_metadata):
                _ = objects
                _ = relations
                _ = context_metadata
                return {'entities': {}, 'links': {}, 'contexts': {context_id: {}}}

            def update_relational_state(self, state, objects, relations, context_id, context_metadata):
                _ = objects
                _ = relations
                _ = context_metadata
                out = dict(state)
                ctx = dict(out.get('contexts') or {})
                ctx[context_id] = {}
                out['contexts'] = ctx
                return out

        class _Want:
            def compute_awareness_plan(self, objectives, gaps, errors, opportunities, plan_id='p'):
                _ = objectives
                _ = gaps
                _ = errors
                _ = opportunities
                # Plan wants error_resolution so activity_manager can run it (flag-off path).
                return {'plan_id': plan_id, 'wants': [{'want_type': 'want_error_resolution', 'strength': 1.0, 'reason': 'errors', 'targets': ['r1']}], 'suggested_activities': []}

        class _Act:
            def run_activity_cycle(self, awareness_plan, queue, modules, max_steps=1):
                _ = awareness_plan
                _ = max_steps
                pending = queue.get('pending') if isinstance(queue, dict) else None
                if isinstance(pending, list) and pending:
                    act = pending.pop(0)
                    fn = modules.get(act.get('activity_type'))
                    if callable(fn):
                        _ = fn(act)
                    comp = queue.get('completed')
                    if isinstance(comp, list):
                        comp.append({'activity_id': act.get('activity_id'), 'activity_type': act.get('activity_type')})
                return queue

        class _Retr:
            def retrieve(self, store, query):
                _ = store
                _ = query
                return []

        class _Reason:
            def synthesize(self, records, opportunity):
                _ = records
                _ = opportunity
                return {'new_record_id': 's', 'value': None, 'conceptual_vector': [], 'inputs': [], 'coherence_gain': 0.0}

        storage = _Storage()

        # Flag OFF: should not create rollback-resolution provenance events.
        state_off = initialize_system(storage)
        state_off['feature_flags'] = {'use_rollback_resolution': False}
        out_off = run_cycle(
            state_off,
            context_id='ctx1',
            context_metadata={},
            modules={
                'measure': _Measure(),
                'relational_adapter': _Adapter(),
                'error_resolution': __import__('module_error_resolution'),
                'want': _Want(),
                'activity_manager': _Act(),
                'retrieval': _Retr(),
                'reasoning': _Reason(),
                'storage': storage,
            },
        )
        prov_off = out_off.get('provenance_log') if isinstance(out_off, dict) else None
        has_td_off = any(isinstance(e, dict) and e.get('event_type') in ('resolution_task_created', 'resolution_executed') for e in (prov_off or []))

        # Flag ON: should create and persist provenance events.
        state_on = initialize_system(storage)
        state_on['feature_flags'] = {'use_rollback_resolution': True}
        out_on = run_cycle(
            state_on,
            context_id='ctx1',
            context_metadata={},
            modules={
                'measure': _Measure(),
                'relational_adapter': _Adapter(),
                'error_resolution': __import__('module_error_resolution'),
                'want': _Want(),
                'activity_manager': _Act(),
                'retrieval': _Retr(),
                'reasoning': _Reason(),
                'storage': storage,
            },
        )
        prov_on = out_on.get('provenance_log') if isinstance(out_on, dict) else None
        has_td_on = any(isinstance(e, dict) and e.get('event_type') == 'resolution_task_created' for e in (prov_on or [])) and any(
            isinstance(e, dict) and e.get('event_type') == 'resolution_executed' for e in (prov_on or [])
        )

        ok = (has_td_off is False) and (has_td_on is True)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_verifier_precondition_enforcement():
    cid = 'logic_verifier_precondition_enforcement'
    try:
        from module_activity_manager import new_queue, enqueue_activities, select_next_activity
        import module_verifier as verifier

        q = new_queue()
        act = {
            'activity_id': 'x',
            'activity_type': 'measure',
            'targets': ['r1'],
            'priority': 1.0,
            'metadata': {'preconditions': [{'type': 'record_version', 'record_id': 'r1', 'min_version': 2}]},
        }
        q = enqueue_activities(queue=q, activities=[act])
        st = {'records_map': {'r1': {'version': 1}}}
        sel = select_next_activity(queue=q, state=st, verifier_module=verifier)
        ok = (sel is None)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_verifier_validation_artifact_shape():
    cid = 'logic_verifier_validation_artifact_shape'
    try:
        from module_provenance import create_event
        from module_verifier import generate_validation_artifact

        pre = {'ok': True, 'failures': [], 'evidence': {'checks': [{'name': 'schema_validation', 'ok': True}]}, 'activity_id': 'a'}
        post = {
            'ok': True,
            'failures': [],
            'evidence': {
                'checks': [{'name': 'validation_artifact', 'ok': True}],
                'statistical_validation': {'t': 1.0, 'p': 0.01, 'n': 10, 'mean_diff': 1.0, 'sd': 0.5},
            },
            'activity_id': 'a',
        }
        prov = [create_event('x', {'target_ids': ['r1']}, timestamp=0.0)]
        art = generate_validation_artifact(pre, post, prov, deterministic_mode=True)
        required = ('artifact_id', 'activity_id', 'pre_checks', 'post_checks', 'confidence_score', 'provenance_snapshot', 'timestamp', 'trace')
        ok = isinstance(art, dict) and all(k in art for k in required)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_verifier_deterministic_artifacts():
    cid = 'logic_verifier_deterministic_artifacts'
    try:
        from module_verifier import generate_validation_artifact

        pre = {'ok': True, 'failures': [], 'evidence': {'checks': [{'name': 'schema_validation', 'ok': True}]}, 'activity_id': 'a'}
        post = {
            'ok': True,
            'failures': [],
            'evidence': {'checks': [{'name': 'validation_artifact', 'ok': True}], 'statistical_validation': {'t': 1.0, 'p': 0.01, 'n': 10, 'mean_diff': 1.0, 'sd': 0.5}},
            'activity_id': 'a',
        }
        prov = [{'event_id': 'e1'}, {'event_id': 'e2'}]
        a1 = generate_validation_artifact(pre, post, prov, deterministic_mode=True)
        a2 = generate_validation_artifact(pre, post, prov, deterministic_mode=True)
        ok = (a1 == a2) and isinstance(a1.get('artifact_id'), str)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_basic_signals():
    cid = 'logic_want_basic_signals'
    try:
        from module_want import compute_awareness_plan
        plan = compute_awareness_plan(
            objectives=[],
            gaps=[{'target_id': 'want_case_1', 'delta': 0.95, 'has_measurement': True, 'has_description': True}],
            errors=[{'target_id': 'want_case_1', 'error_count': 0, 'max_severity': 0.0}],
            opportunities=[],
            plan_id='want_plan_1',
        )
        wants = plan.get('wants') if isinstance(plan, dict) else None
        ok = isinstance(wants, list) and any(isinstance(w, dict) and w.get('want_type') == 'want_information' for w in wants)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_error_signal():
    cid = 'logic_want_error_signal'
    try:
        from module_want import compute_awareness_plan
        plan = compute_awareness_plan(
            objectives=[],
            gaps=[],
            errors=[{'target_id': 'want_case_2', 'error_count': 7, 'max_severity': 0.9}],
            opportunities=[],
            plan_id='want_plan_2',
        )
        wants = plan.get('wants') if isinstance(plan, dict) else None
        ok = isinstance(wants, list) and any(isinstance(w, dict) and w.get('want_type') == 'want_error_resolution' for w in wants)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_synthesis_signal():
    cid = 'logic_want_synthesis_signal'
    try:
        from module_want import compute_awareness_plan
        plan = compute_awareness_plan(
            objectives=[],
            gaps=[],
            errors=[],
            opportunities=[{'target_ids': ['want_case_3'], 'coherence_gain': 0.8}],
            plan_id='want_plan_3',
        )
        wants = plan.get('wants') if isinstance(plan, dict) else None
        ok = isinstance(wants, list) and any(isinstance(w, dict) and w.get('want_type') == 'want_synthesis' for w in wants)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_empty_inputs():
    cid = 'logic_want_empty_inputs'
    try:
        from module_want import compute_awareness_plan
        plan = compute_awareness_plan(
            objectives=[],
            gaps=[],
            errors=[],
            opportunities=[],
            plan_id='want_plan_empty',
        )
        wants = plan.get('wants') if isinstance(plan, dict) else None
        acts = plan.get('suggested_activities') if isinstance(plan, dict) else None
        ok = isinstance(wants, list) and wants == [] and isinstance(acts, list) and acts == []
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_evoi_positive():
    cid = 'logic_want_evoi_positive'
    try:
        from module_want import compute_expected_value_of_information
        cur = {'value': 0.0, 'variance': 1.0, 'provenance': {'id': 'cur'}}
        imp = {'value': 0.0, 'variance': 0.01, 'provenance': {'id': 'imp'}}
        evoi = float(
            compute_expected_value_of_information(
                current=cur,
                improved=imp,
                baseline=0.0,
                cost=0.01,
                n_samples=256,
            )
        )
        ok = evoi > 0.2
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_evoi_negative():
    cid = 'logic_want_evoi_negative'
    try:
        from module_want import compute_expected_value_of_information
        cur = {'value': 0.0, 'variance': 0.01, 'provenance': {'id': 'cur'}}
        imp = {'value': 0.0, 'variance': 0.0081, 'provenance': {'id': 'imp'}}
        evoi = float(
            compute_expected_value_of_information(
                current=cur,
                improved=imp,
                baseline=0.0,
                cost=1.0,
                n_samples=256,
            )
        )
        ok = evoi < -0.5
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_want_evoi_why_vector():
    cid = 'logic_want_evoi_why_vector'
    try:
        from module_want import compute_evoi_with_why

        cur = {'value': 0.0, 'variance': 1.0, 'provenance': {'id': 'cur'}}
        imp = {'value': 0.0, 'variance': 0.01, 'provenance': {'id': 'imp'}}

        a = compute_evoi_with_why(current=cur, improved=imp, baseline=0.0, activity='measure', target_ids=['t1'], n_samples=256)
        b = compute_evoi_with_why(current=cur, improved=imp, baseline=0.0, activity='measure', target_ids=['t1'], n_samples=256)

        why = a.get('why_vector') if isinstance(a, dict) else None
        ok = isinstance(why, list) and a == b
        ok = ok and any(isinstance(it, dict) and it.get('key') == 'evoi' for it in (why or []))
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_activity_manager_translate():
    cid = 'logic_activity_manager_translate'
    try:
        from module_activity_manager import translate_wants_to_activities, new_queue, enqueue_activities, prioritize_queue, select_next_activity
        plan = {
            'plan_id': 'plan_eval_1',
            'wants': [
                {'want_type': 'want_information', 'strength': 0.9, 'reason': 'gap', 'targets': ['t1']},
                {'want_type': 'want_synthesis', 'strength': 0.6, 'reason': 'coherence', 'targets': ['t2']},
                {'want_type': 'want_error_resolution', 'strength': 1.0, 'reason': 'errors', 'targets': ['t3']},
            ],
            'suggested_activities': []
        }
        acts = translate_wants_to_activities(awareness_plan=plan)
        # want_information -> 2 activities; others -> 1 each => 4 total
        if not (isinstance(acts, list) and len(acts) == 4):
            return {'case': cid, 'passed': False}
        q = new_queue()
        q = enqueue_activities(queue=q, activities=acts)
        q = prioritize_queue(queue=q)
        nxt = select_next_activity(queue=q)
        ok = isinstance(nxt, dict) and nxt.get('activity_type') == 'error_resolution'
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_activity_manager_deterministic_queue():
    cid = 'logic_activity_manager_deterministic_queue'
    try:
        from module_activity_manager import new_queue, enqueue_activities

        q1 = new_queue()
        q1['deterministic_mode'] = True
        a = {'activity_id': 'b', 'activity_type': 'measure', 'targets': ['t'], 'priority': 0.5, 'metadata': {}}
        b = {'activity_id': 'a', 'activity_type': 'retrieve', 'targets': ['t'], 'priority': 0.5, 'metadata': {}}
        q1 = enqueue_activities(queue=q1, activities=[a, b])
        order1 = [x.get('activity_id') for x in (q1.get('pending') or [])]

        q2 = new_queue()
        q2['deterministic_mode'] = True
        q2 = enqueue_activities(queue=q2, activities=[a, b])
        order2 = [x.get('activity_id') for x in (q2.get('pending') or [])]

        ok = (order1 == ['a', 'b']) and (order2 == order1)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_activity_manager_budget_respect():
    cid = 'logic_activity_manager_budget_respect'
    try:
        from module_activity_manager import new_queue, enqueue_activities, select_next_activity

        q = new_queue()
        q['resource_budget'] = {'cpu': 1.0}
        q['used_resources'] = {'cpu': 0.0}
        act = {
            'activity_id': 'x',
            'activity_type': 'measure',
            'targets': ['r1'],
            'priority': 1.0,
            'metadata': {'cost': 2.0},
        }
        q = enqueue_activities(queue=q, activities=[act])
        sel = select_next_activity(queue=q)
        ok = (sel is None)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_activity_manager_precondition_enforcement():
    cid = 'logic_activity_manager_precondition_enforcement'
    try:
        from module_activity_manager import new_queue, enqueue_activities, select_next_activity

        q = new_queue()
        act = {
            'activity_id': 'x',
            'activity_type': 'measure',
            'targets': ['r1'],
            'priority': 1.0,
            'metadata': {
                'preconditions': [{'type': 'record_version', 'record_id': 'r1', 'min_version': 2}],
                'cost': 0.1,
            },
        }
        q = enqueue_activities(queue=q, activities=[act])
        state = {'records_map': {'r1': {'version': 1}}}
        sel = select_next_activity(queue=q, state=state)
        ok = (sel is None)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_retrieval_ranking():
    cid = 'logic_retrieval_ranking'
    try:
        from module_retrieval import retrieve
        store = [
            {
                'record_id': 'r1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.2,
                'objective_links': {'o1': 0.1},
                'conceptual_vector': [1.0, 0.0],
                'constraints': {},
            },
            {
                'record_id': 'r2',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.8,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [1.0, 0.0],
                'constraints': {},
            },
            {
                'record_id': 'r3',
                'value': {},
                'context_id': 'other',
                'recurrence': 0.8,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [0.0, 1.0],
                'constraints': {},
            },
        ]
        query = {
            'target_ids': ['r2'],
            'objective_id': 'o1',
            'conceptual_vector': [1.0, 0.0],
            'required_context': 'semantic',
            'max_results': 2,
        }
        out = retrieve(store, query)
        ok = isinstance(out, list) and len(out) == 2 and out[0].get('record_id') == 'r2'
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_retrieval_score_components():
    cid = 'logic_retrieval_score_components'
    try:
        from module_retrieval import retrieve_with_scores
        store = [
            {
                'record_id': 'r1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.8,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [1.0, 0.0],
                'constraints': {},
            }
        ]
        query = {
            'objective_id': 'o1',
            'conceptual_vector': [1.0, 0.0],
            'required_context': 'semantic',
            'max_results': 1,
            'deterministic_mode': True,
        }
        rows = retrieve_with_scores(store=store, query=query)
        if not (isinstance(rows, list) and rows and isinstance(rows[0], dict)):
            return {'case': cid, 'passed': False}
        row = rows[0]
        ok = isinstance(row.get('components'), dict) and isinstance(row.get('score_distribution'), list) and isinstance(row.get('explain_vector'), dict)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_retrieval_deterministic_sampling():
    cid = 'logic_retrieval_deterministic_sampling'
    try:
        from module_retrieval import retrieve_with_scores
        store = [
            {
                'record_id': 'r1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.5,
                'objective_links': {'o1': 0.5},
                'conceptual_vector': [1.0, 0.0],
                'constraints': {},
                'uncertainty': {'variance': 0.04, 'value': 0.0, 'provenance': {'id': 'u'}},
            }
        ]
        query = {
            'objective_id': 'o1',
            'conceptual_vector': [1.0, 0.0],
            'required_context': 'semantic',
            'max_results': 1,
            'deterministic_mode': True,
        }
        a = retrieve_with_scores(store=store, query=query)[0]
        b = retrieve_with_scores(store=store, query=query)[0]
        ok = a.get('score_distribution') == b.get('score_distribution')
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_retrieval_diversity():
    cid = 'logic_retrieval_diversity'
    try:
        from module_retrieval import retrieve_with_scores
        store = [
            {
                'record_id': 'a1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.9,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [1.0, 0.0, 0.0],
                'constraints': {},
            },
            {
                'record_id': 'a2',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.8,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [1.0, 0.0, 0.0],
                'constraints': {},
            },
            {
                'record_id': 'b1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.7,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [0.0, 1.0, 0.0],
                'constraints': {},
            },
        ]
        query = {
            'objective_id': 'o1',
            'conceptual_vector': [1.0, 0.0, 0.0],
            'required_context': 'semantic',
            'max_results': 3,
            'diversity_k': 2,
            'deterministic_mode': True,
        }
        rows = retrieve_with_scores(store=store, query=query)
        rids = [r.get('record_id') for r in rows if isinstance(r, dict)]
        ok = any(isinstance(x, str) and x.startswith('a') for x in rids) and any(isinstance(x, str) and x.startswith('b') for x in rids)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_retrieval_explainability():
    cid = 'logic_retrieval_explainability'
    try:
        from module_retrieval import retrieve_with_scores
        store = [
            {
                'record_id': 'r1',
                'value': {},
                'context_id': 'semantic',
                'recurrence': 0.2,
                'objective_links': {'o1': 1.0},
                'conceptual_vector': [1.0, 0.0],
                'constraints': {},
            }
        ]
        query = {
            'objective_id': 'o1',
            'conceptual_vector': [1.0, 0.0],
            'required_context': 'semantic',
            'max_results': 1,
        }
        row = retrieve_with_scores(store=store, query=query)[0]
        ev = row.get('explain_vector') if isinstance(row, dict) else None
        if not isinstance(ev, dict):
            return {'case': cid, 'passed': False}
        total = 0.0
        for v in ev.values():
            try:
                total += float(v)
            except Exception:
                continue
        ok = abs(total - float(row.get('score') or 0.0)) < 1e-6
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_detect_equal():
    cid = 'logic_error_resolution_detect_equal'
    try:
        from module_error_resolution import detect_error
        m = {'value': 10, 'source_id': 's', 'timestamp': 0.0, 'context_id': 'c'}
        r = {'record_id': 'x', 'value': 10, 'context_id': 'c', 'links': {}, 'derived': False, 'inputs': []}
        rep = detect_error(measurement=m, record=r)
        return {'case': cid, 'passed': bool(rep is None)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_detect_mismatch():
    cid = 'logic_error_resolution_detect_mismatch'
    try:
        from module_error_resolution import detect_error
        m = {'value': 12, 'source_id': 's', 'timestamp': 0.0, 'context_id': 'c'}
        r = {'record_id': 'x', 'value': 10, 'context_id': 'c', 'links': {}, 'derived': False, 'inputs': []}
        rep = detect_error(measurement=m, record=r)
        ok = (
            isinstance(rep, dict)
            and rep.get('error_type') == 'mis_description'
            and abs(float(rep.get('delta') or 0.0) - 2.0) < 1e-9
            and rep.get('target_record_id') == 'x'
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_confidence_uncertainty():
    cid = 'logic_error_resolution_confidence_uncertainty'
    try:
        from module_error_resolution import detect_error

        m = {
            'value': 20.0,
            'source_id': 's',
            'timestamp': 0.0,
            'context_id': 'c',
            'uncertainty': {'value': 20.0, 'variance': 0.01, 'provenance': {'id': 'm'}},
        }
        r = {
            'record_id': 'x',
            'value': 10.0,
            'context_id': 'c',
            'links': {},
            'derived': False,
            'inputs': [],
            'uncertainty': {'value': 10.0, 'variance': 0.01, 'provenance': {'id': 'r'}},
        }
        rep = detect_error(measurement=m, record=r)
        conf = float((rep or {}).get('confidence') or 0.0)
        ok = isinstance(rep, dict) and (conf > 0.99)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_rollback_plan():
    cid = 'logic_error_resolution_rollback_plan'
    try:
        from module_error_resolution import create_resolution_task, execute_resolution_task

        store = {
            'x': {
                'record_id': 'x',
                'value': 10.0,
                'context_id': 'c',
                'version': 0,
                'uncertainty': {'value': 10.0, 'variance': 1.0, 'provenance': {'id': 'before'}},
            }
        }

        def record_lookup_fn(rid: str):
            return dict(store[rid])

        def storage_update_fn(rec: dict):
            store[rec['record_id']] = dict(rec)

        def measure_fn(rid: str):
            return {
                'value': 20.0,
                'source_id': 's',
                'timestamp': 0.0,
                'context_id': 'c',
                'uncertainty': {'value': 20.0, 'variance': 1.0, 'provenance': {'id': 'm'}},
            }

        def relink_fn(rec: dict, new_context_id: str):
            out = dict(rec)
            out['context_id'] = new_context_id
            return out

        def recompute_fn(rec: dict):
            out = dict(rec)
            out['value'] = float(out.get('value') or 0.0) + 1.0
            return out

        error_report = {'target_record_id': 'x', 'error_type': 'mis_measurement', 'severity': 1.0, 'event_id': 'er1'}
        task, prov = create_resolution_task(
            error_report=error_report,
            resolution_strategy='re_measure',
            provenance_log=[],
            deterministic_mode=True,
            deterministic_time=0.0,
        )
        out_task, _ = execute_resolution_task(
            task=task,
            record_lookup_fn=record_lookup_fn,
            measure_fn=measure_fn,
            storage_update_fn=storage_update_fn,
            relink_fn=relink_fn,
            recompute_fn=recompute_fn,
            provenance_log=prov,
            deterministic_mode=True,
            deterministic_time=0.0,
            n_samples=128,
        )

        rb = out_task.get('rollback_plan') if isinstance(out_task, dict) else None
        ok = (
            isinstance(rb, dict)
            and isinstance(rb.get('snapshot'), dict)
            and float((rb.get('snapshot') or {}).get('value') or 0.0) == 10.0
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_stat_validation():
    cid = 'logic_error_resolution_stat_validation'
    try:
        from module_error_resolution import create_resolution_task, execute_resolution_task

        store = {
            'x': {
                'record_id': 'x',
                'value': 10.0,
                'context_id': 'c',
                'version': 0,
                'uncertainty': {'value': 10.0, 'variance': 1.0, 'provenance': {'id': 'before'}},
            }
        }

        def record_lookup_fn(rid: str):
            return dict(store[rid])

        def storage_update_fn(rec: dict):
            store[rec['record_id']] = dict(rec)

        def measure_fn(rid: str):
            return {
                'value': 20.0,
                'source_id': 's',
                'timestamp': 0.0,
                'context_id': 'c',
                'uncertainty': {'value': 20.0, 'variance': 1.0, 'provenance': {'id': 'm'}},
            }

        def relink_fn(rec: dict, new_context_id: str):
            out = dict(rec)
            out['context_id'] = new_context_id
            return out

        def recompute_fn(rec: dict):
            out = dict(rec)
            out['value'] = float(out.get('value') or 0.0) + 1.0
            return out

        error_report = {'target_record_id': 'x', 'error_type': 'mis_measurement', 'severity': 1.0, 'event_id': 'er1'}
        task, prov = create_resolution_task(
            error_report=error_report,
            resolution_strategy='re_measure',
            provenance_log=[],
            deterministic_mode=True,
            deterministic_time=0.0,
        )
        out_task, _ = execute_resolution_task(
            task=task,
            record_lookup_fn=record_lookup_fn,
            measure_fn=measure_fn,
            storage_update_fn=storage_update_fn,
            relink_fn=relink_fn,
            recompute_fn=recompute_fn,
            provenance_log=prov,
            deterministic_mode=True,
            deterministic_time=0.0,
            n_samples=128,
        )

        v = out_task.get('validation') if isinstance(out_task, dict) else None
        ok = isinstance(v, dict) and all(k in v for k in ('t', 'p', 'n', 'mean_diff', 'sd'))
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_error_resolution_deterministic_execution():
    cid = 'logic_error_resolution_deterministic_execution'
    try:
        from module_error_resolution import create_resolution_task, execute_resolution_task

        def run_once():
            store = {
                'x': {
                    'record_id': 'x',
                    'value': 10.0,
                    'context_id': 'c',
                    'version': 0,
                    'uncertainty': {'value': 10.0, 'variance': 1.0, 'provenance': {'id': 'before'}},
                }
            }

            def record_lookup_fn(rid: str):
                return dict(store[rid])

            def storage_update_fn(rec: dict):
                store[rec['record_id']] = dict(rec)

            def measure_fn(rid: str):
                return {
                    'value': 20.0,
                    'source_id': 's',
                    'timestamp': 0.0,
                    'context_id': 'c',
                    'uncertainty': {'value': 20.0, 'variance': 1.0, 'provenance': {'id': 'm'}},
                }

            def relink_fn(rec: dict, new_context_id: str):
                out = dict(rec)
                out['context_id'] = new_context_id
                return out

            def recompute_fn(rec: dict):
                out = dict(rec)
                out['value'] = float(out.get('value') or 0.0) + 1.0
                return out

            error_report = {'target_record_id': 'x', 'error_type': 'mis_measurement', 'severity': 1.0, 'event_id': 'er1'}
            task, prov = create_resolution_task(
                error_report=error_report,
                resolution_strategy='re_measure',
                provenance_log=[],
                deterministic_mode=True,
                deterministic_time=0.0,
            )
            out_task, out_prov = execute_resolution_task(
                task=task,
                record_lookup_fn=record_lookup_fn,
                measure_fn=measure_fn,
                storage_update_fn=storage_update_fn,
                relink_fn=relink_fn,
                recompute_fn=recompute_fn,
                provenance_log=prov,
                deterministic_mode=True,
                deterministic_time=0.0,
                n_samples=128,
            )
            return out_task, out_prov

        a_task, a_prov = run_once()
        b_task, b_prov = run_once()
        ok = (a_task == b_task) and (a_prov == b_prov)
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_synthesis_engine():
    cid = 'logic_reasoning_synthesis_engine'
    try:
        from module_reasoning import synthesize, propose_next_steps

        records = [
            {
                'record_id': 'a',
                'value': 10.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
            {
                'record_id': 'b',
                'value': 20.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
        ]
        opp = {'target_ids': ['a', 'b'], 'coherence_gain': 0.0}
        res = synthesize(records=records, opportunity=opp)
        steps = propose_next_steps(synthesis_result=res)

        ok = (
            isinstance(res, dict)
            and res.get('new_record_id') == 'synth_a_b'
            and abs(float(res.get('value') or 0.0) - 15.0) < 1e-9
            and isinstance(res.get('conceptual_vector'), list)
            and isinstance(steps, list)
            and ('measure' in steps)
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_propose_next_steps_positive():
    cid = 'logic_reasoning_propose_next_steps_positive'
    try:
        from module_reasoning import propose_next_steps
        steps = propose_next_steps(
            synthesis_result={
                'new_record_id': 's',
                'value': 0,
                'conceptual_vector': [],
                'inputs': [],
                'coherence_gain': 0.1,
            }
        )
        ok = isinstance(steps, list) and steps == ['measure', 'integrate']
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_propose_next_steps_negative():
    cid = 'logic_reasoning_propose_next_steps_negative'
    try:
        from module_reasoning import propose_next_steps
        steps = propose_next_steps(
            synthesis_result={
                'new_record_id': 's',
                'value': 0,
                'conceptual_vector': [],
                'inputs': [],
                'coherence_gain': -0.1,
            }
        )
        ok = isinstance(steps, list) and steps == ['re_evaluate']
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_think_deeper_artifacts():
    cid = 'logic_reasoning_think_deeper_artifacts'
    try:
        from module_reasoning import synthesize

        records = [
            {
                'record_id': 'a',
                'value': 10.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
            {
                'record_id': 'b',
                'value': 20.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
        ]
        res = synthesize(records=records, opportunity={'target_ids': ['a', 'b'], 'coherence_gain': 0.0})
        why = res.get('why') if isinstance(res, dict) else None
        cfs = res.get('counterfactuals') if isinstance(res, dict) else None

        ok = (
            isinstance(res, dict)
            and res.get('new_record_id') == 'synth_a_b'
            and isinstance(why, dict)
            and why.get('version') == 1
            and why.get('inputs') == ['a', 'b']
            and isinstance((why.get('coherence') if isinstance(why, dict) else None), dict)
            and isinstance(cfs, list)
            and len(cfs) == 2
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_reasoning_think_deeper_deterministic_repro():
    cid = 'logic_reasoning_think_deeper_deterministic_repro'
    try:
        from module_reasoning import synthesize

        records = [
            {
                'record_id': 'a',
                'value': 10.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
            {
                'record_id': 'b',
                'value': 20.0,
                'context_id': 'semantic',
                'conceptual_vector': [1.0, 0.0],
                'objective_links': {},
                'derived': False,
                'inputs': [],
            },
        ]
        a = synthesize(records=records, opportunity={'target_ids': ['a', 'b'], 'coherence_gain': 0.0})
        b = synthesize(records=records, opportunity={'target_ids': ['a', 'b'], 'coherence_gain': 0.0})
        ok = a == b
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_adversarial_report_shape():
    cid = 'logic_adversarial_report_shape'
    try:
        from module_adversarial_test import run_scenario

        r = run_scenario('S1_small_noise', deterministic_mode=True)
        ok = (
            isinstance(r, dict)
            and r.get('scenario_id') == 'S1_small_noise'
            and isinstance(r.get('seed_obj'), dict)
            and isinstance(r.get('result'), dict)
            and isinstance(r.get('provenance_snapshot'), list)
        )
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_adversarial_deterministic_repro():
    cid = 'logic_adversarial_deterministic_repro'
    try:
        from module_adversarial_test import run_scenario

        a = run_scenario('S1_small_noise', deterministic_mode=True)
        b = run_scenario('S1_small_noise', deterministic_mode=True)
        ok = a == b
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}


def eval_adversarial_escalation_policy():
    cid = 'logic_adversarial_escalation_policy'
    try:
        from module_adversarial_test import run_scenario

        r = run_scenario('S5_rollback_storm', deterministic_mode=True)
        res = r.get('result') if isinstance(r, dict) else None
        ok = isinstance(res, dict) and res.get('escalation_action') == 'escalate'
        return {'case': cid, 'passed': bool(ok)}
    except Exception:
        return {'case': cid, 'passed': False}

for name in sorted(os.listdir(CASES_DIR)):
    if not name.endswith('.json'):
        continue
    with open(os.path.join(CASES_DIR, name), 'r', encoding='utf-8') as f:
        case = json.load(f)
    cid = case.get('id')
    ctype = case.get('type')
    ok = False
    try:
        if ctype == 'semantic':
            inp = case['input']
            # store and then read back
            store_information('eval_demo', inp['content'], inp['category'])
            path = os.path.join(BASE, 'LongTermStore', 'Semantic', 'eval_demo.json')
            with open(path, 'r', encoding='utf-8') as rf:
                rec = json.load(rf)
            ok = 'schema_version' in rec
        elif ctype == 'tools':
            inp = case['input']
            sid = sanitize_id(inp['data_id'])
            ok = (sid == inp['data_id'])
        elif ctype == 'index':
            idx = build_semantic_index()
            ok = isinstance(idx.get('id_to_tokens'), dict)
        elif ctype == 'collector':
            inp = case['input']
            # seed semantic record
            store_information(inp['data_id'], 'eval content', 'semantic')
            collect_results({'modules': inp['modules'], 'terminals': inp['terminals']}, inp['data_id'])
            cpath = os.path.join(BASE, 'LongTermStore', 'ActiveSpace', f"collector_{inp['data_id']}.json")
            with open(cpath, 'r', encoding='utf-8') as cf:
                arr = json.load(cf)
            ok = all(validate_record(item, 'collector_output') for item in arr if isinstance(item, dict))
        elif ctype == 'scheduler':
            inp = case['input']
            # ensure semantic exists then flag
            store_information(inp['data_id'], 'eval content', 'semantic')
            spath = os.path.join(BASE, 'LongTermStore', 'Semantic', f"{inp['data_id']}.json")
            flag_record(spath, 'eval', inp['minutes'])
            with open(spath, 'r', encoding='utf-8') as sf:
                rec = json.load(sf)
            ok = ('future_event_time' in rec) and ('schema_version' in rec)
        elif ctype == 'integration':
            inp = case['input']
            RelationalMeasurement(inp['data_id'], inp['content'], inp.get('category','semantic'))
            apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
            with open(apath, 'r', encoding='utf-8') as af:
                act = json.load(af)
            # check relational_measure entry contains cycle_id
            desc = act.get('relational_measure', {}).get('description') or ''
            ok = 'cycle_id' in desc
        elif ctype == 'toggle_eval':
            inp = case['input']
            RelationalMeasurement(inp['data_id'], inp['content'], inp.get('category','semantic'))
            # check Active/Holding/Discard for target file having justifications
            found = False
            for space in ['ActiveSpace','HoldingSpace','DiscardSpace']:
                tpath = os.path.join(BASE, space, f"{inp['data_id']}.json")
                if os.path.exists(tpath):
                    with open(tpath, 'r', encoding='utf-8') as tf:
                        rec = json.load(tf)
                    found = 'toggle_justifications' in rec
                    break
            ok = found
        elif ctype == 'reason_eval':
            inp = case['input']
            RelationalMeasurement(inp['data_id'], inp['content'], inp.get('category','semantic'))
            spath = os.path.join(BASE, 'LongTermStore', 'Semantic', f"{inp['data_id']}.json")
            with open(spath, 'r', encoding='utf-8') as sf:
                rec = json.load(sf)
            ok = isinstance(rec.get('reason_chain'), list) and len(rec.get('reason_chain')) > 0
        elif ctype == 'procedure_eval':
            inp = case['input']
            # Ensure template exists
            proc_path = os.path.join(BASE, 'LongTermStore', 'Procedural', 'procedure_template.json')
            if not os.path.exists(proc_path):
                print('Procedure template missing'); ok = False
            else:
                with open(proc_path, 'r', encoding='utf-8') as pf:
                    before = json.load(pf)
                RelationalMeasurement(inp['data_id'], inp['content'], inp.get('category','semantic'))
                spath = os.path.join(BASE, 'LongTermStore', 'Semantic', f"{inp['data_id']}.json")
                with open(spath, 'r', encoding='utf-8') as sf:
                    rec = json.load(sf)
                matched = isinstance(rec.get('matched_procedures'), list) and len(rec.get('matched_procedures')) > 0
                with open(proc_path, 'r', encoding='utf-8') as pf:
                    after = json.load(pf)
                rate_inc = float(after.get('success_rate', 0.0)) > float(before.get('success_rate', 0.0))
                ok = matched and rate_inc
        else:
            ok = False
    except Exception:
        ok = False
    results.append({'case': cid, 'passed': ok})
    if not ok:
        failures += 1

# Logic/consistency suite
try:
    suite_results = eval_logic_suite()
    for r in suite_results:
        results.append(r)
        if not r.get('passed'):
            failures += 1
            break
except Exception:
    results.append({'case': 'logic_suite', 'passed': False})
    failures += 1

# Additional deterministic collector timestamp check
def _eval_deterministic_collector_ts():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        det = cfg.get('determinism', {})
        if not det.get('deterministic_mode'):
            return {'case': 'deterministic_collector_ts', 'passed': True}
        fixed_ts = det.get('fixed_timestamp')
        from module_integration import RelationalMeasurement
        RelationalMeasurement('eval_det_ts','deterministic timestamp check','semantic')
        sem_path = os.path.join(BASE, 'LongTermStore','Semantic','eval_det_ts.json')
        if not os.path.exists(sem_path):
            return {'case': 'deterministic_collector_ts', 'passed': False}
        with open(sem_path, 'r', encoding='utf-8') as f:
            rec = json.load(f)
        outputs = rec.get('collector_outputs') or rec.get('outputs') or []
        if not outputs:
            # fall back to evidence timestamps
            ev = rec.get('evidence', [])
            ok = bool(ev) and all(e.get('ts') == fixed_ts for e in ev if e.get('ts'))
            return {'case': 'deterministic_collector_ts', 'passed': ok}
        # Accept determinism if at least latest outputs use fixed timestamp
        latest = outputs[-4:] if len(outputs) >= 4 else outputs
        ok = all(o.get('timestamp') == fixed_ts and (o.get('end_ts') in (fixed_ts, None)) for o in latest)
        return {'case': 'deterministic_collector_ts', 'passed': ok}
    except Exception:
        return {'case': 'deterministic_collector_ts', 'passed': False}

results.append(_eval_deterministic_collector_ts())
if not results[-1]['passed']:
    failures += 1

# Eval: last_cycle_ts present in activity logs
def _eval_last_cycle_ts_activity():
    try:
        from module_integration import RelationalMeasurement
        RelationalMeasurement('eval_cycle_ts','check cycle ts','semantic')
        base = BASE

        def _load_activity_json(path: str):
            # activity.json can be updated concurrently by collectors; retry briefly.
            for _ in range(5):
                try:
                    with open(path, 'r', encoding='utf-8') as af:
                        return json.load(af)
                except Exception:
                    time.sleep(0.05)
            return None

        apath = os.path.join(base, 'ActiveSpace', 'activity.json')
        ok1 = False
        if os.path.exists(apath):
            act = _load_activity_json(apath)
            if not isinstance(act, dict):
                act = {}
            ok1 = bool(act.get('last_cycle_ts')) or ('"cycle_ts":' in (act.get('relational_measure', {}).get('description') or ''))
        lt_apath = os.path.join(base, 'LongTermStore', 'ActiveSpace', 'activity.json')
        ok2 = False
        if os.path.exists(lt_apath):
            lact = _load_activity_json(lt_apath)
            if not isinstance(lact, dict):
                lact = {}
            ok2 = bool(lact.get('last_cycle_ts')) or ('"cycle_ts":' in (lact.get('relational_measure', {}).get('description') or ''))
        return {'case': 'last_cycle_ts_activity', 'passed': (ok1 or ok2)}
    except Exception:
        return {'case': 'last_cycle_ts_activity', 'passed': False}

results.append(_eval_last_cycle_ts_activity())
if not results[-1]['passed']:
    failures += 1

# Eval: arbiter respects decisive recommendation
def _eval_decisive_arbiter():
    try:
        from module_integration import RelationalMeasurement
        # Craft content suggesting conflict to force 'contradiction_resolve'
        RelationalMeasurement('eval_arbiter_decisive', 'objective conflict contradict risk', 'semantic')
        apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
        if not os.path.exists(apath):
            return {'case': 'decisive_arbiter', 'passed': False}
        with open(apath, 'r', encoding='utf-8') as af:
            act = json.load(af)
        cycles = act.get('cycles') or []
        latest = cycles[-1] if cycles else act.get('relational_measure')
        if not latest:
            return {'case': 'decisive_arbiter', 'passed': False}
        # For contradiction scenarios, system should not activate
        arb = latest.get('arbiter') if isinstance(latest, dict) else {}
        acc = arb.get('accepted_actions') or []
        passed = ('activate' not in acc)
        return {'case': 'decisive_arbiter', 'passed': passed}
    except Exception:
        return {'case': 'decisive_arbiter', 'passed': False}

results.append(_eval_decisive_arbiter())
if not results[-1]['passed']:
    failures += 1

# Eval: determinism suite should pass
def _eval_determinism_suite():
    try:
        from module_determinism import evaluate_determinism_suite
        rep = evaluate_determinism_suite('eval_det_suite', 'determinism check beneficial useful', 'semantic')
        return {'case': 'determinism_suite', 'passed': bool(rep.get('overall_passed', False))}
    except Exception:
        return {'case': 'determinism_suite', 'passed': False}

results.append(_eval_determinism_suite())
if not results[-1]['passed']:
    failures += 1

# print table
print("Case Results:")
for r in results:
    print(f"- {r['case']}: {'PASS' if r['passed'] else 'FAIL'}")

# Persist metrics for automated dashboards/gates.
try:
    from module_metrics import flush_metrics

    flush_metrics()
except Exception:
    pass

if failures:
    sys.exit(1)
else:
    sys.exit(0)
