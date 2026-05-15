import os
import json
import copy
from typing import Any, Dict, List, Optional

from module_integration import RelationalMeasurement
from module_tools import build_semantic_index, _load_config

BASE = os.path.dirname(os.path.abspath(__file__))

_LEARNING_READINESS_REQUIRED_LEVELS = {
    'measurement_adequacy': 'strong',
    'categorized_context': 'strong',
    'comprehension_review': 'strong',
}

_LEARNING_READINESS_VERDICT_HELPER = 'module_metrics.build_learning_readiness_verdict'


def _read_json(path: str) -> Any:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _strip_dynamic(obj: Any) -> Any:
    """Recursively remove dynamic fields that legitimately vary between runs."""
    dynamic_keys = {
        'cycle_id', 'start_ts', 'duration_ms', 'run_id', 'timestamp', 'end_ts'
    }
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in dynamic_keys:
                continue
            out[k] = _strip_dynamic(v)
        return out
    if isinstance(obj, list):
        return [_strip_dynamic(x) for x in obj]
    return obj


def _fixed_ts() -> str:
    cfg = _load_config() or {}
    det = cfg.get('determinism', {})
    if det.get('deterministic_mode'):
        return det.get('fixed_timestamp')
    return None


def get_determinism_settings():
    cfg = _load_config() or {}
    return cfg.get('determinism', {})


def get_learning_readiness_gate_settings(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config if isinstance(config, dict) else (_load_config() or {})
    determinism = cfg.get('determinism', {}) if isinstance(cfg.get('determinism'), dict) else {}
    readiness = cfg.get('learning_readiness', {}) if isinstance(cfg.get('learning_readiness'), dict) else {}

    return {
        'version': 1,
        'enabled': bool(readiness.get('enabled', True)),
        'read_only': True,
        'allow_updates': False,
        'activation_allowed': False,
        'activation_blocked_reason': 'learning_readiness_gate_is_read_only',
        'verdict_helper': _LEARNING_READINESS_VERDICT_HELPER,
        'required_levels': copy.deepcopy(_LEARNING_READINESS_REQUIRED_LEVELS),
        'deterministic_mode': bool(determinism.get('deterministic_mode', False)),
        'fixed_timestamp': determinism.get('fixed_timestamp') if determinism.get('deterministic_mode') else None,
    }


def build_learning_readiness_gate_report(
    verdict: Optional[Dict[str, Any]] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    settings = get_learning_readiness_gate_settings(config=config)
    report = copy.deepcopy(settings)

    if not isinstance(verdict, dict):
        report.update({
            'ready': False,
            'status': 'unknown',
            'reason': 'learning readiness verdict unavailable',
            'reasons': [],
            'unmet_conditions': [],
            'observed_levels': {},
            'evidence': {},
        })
        return report

    report.update({
        'ready': bool(verdict.get('ready', False)),
        'status': verdict.get('status') if isinstance(verdict.get('status'), str) else ('ready' if verdict.get('ready') else 'not_ready'),
        'reason': verdict.get('reason') if isinstance(verdict.get('reason'), str) else None,
        'reasons': list(verdict.get('reasons') or []) if isinstance(verdict.get('reasons'), list) else [],
        'unmet_conditions': list(verdict.get('unmet_conditions') or []) if isinstance(verdict.get('unmet_conditions'), list) else [],
        'observed_levels': copy.deepcopy(verdict.get('observed_levels')) if isinstance(verdict.get('observed_levels'), dict) else {},
        'evidence': copy.deepcopy(verdict.get('evidence')) if isinstance(verdict.get('evidence'), dict) else {},
    })
    return report


def print_determinism():
    import json as _json
    print(_json.dumps(get_determinism_settings(), indent=2))


def check_collector_timestamps(data_id: str) -> Dict[str, Any]:
    sem_path = os.path.join(BASE, 'LongTermStore', 'Semantic', f'{data_id}.json')
    rec = _read_json(sem_path) or {}
    fixed = _fixed_ts()
    outputs: List[Dict[str, Any]] = rec.get('collector_outputs') or []
    ok_outputs = True
    if outputs and fixed:
        latest = outputs[-4:] if len(outputs) >= 4 else outputs
        ok_outputs = all(o.get('timestamp') == fixed and (o.get('end_ts') in (fixed, None)) for o in latest)
    ev = rec.get('evidence') or []
    ok_evidence = True
    if ev and fixed:
        ok_evidence = all(e.get('ts') == fixed for e in ev if isinstance(e, dict) and e.get('ts'))
    return {
        'check': 'collector_timestamps',
        'passed': bool(ok_outputs and ok_evidence),
        'details': {'outputs_checked': len(outputs), 'evidence_checked': len(ev)}
    }


def check_index_stability() -> Dict[str, Any]:
    idx1 = build_semantic_index()
    idx2 = build_semantic_index()
    fixed = _fixed_ts()
    ok_ts = True
    if fixed:
        ok_ts = (idx1.get('last_build_ts') == fixed and idx2.get('last_build_ts') == fixed)
    ok_map = (idx1.get('id_to_tokens') == idx2.get('id_to_tokens'))
    return {
        'check': 'index_stability',
        'passed': bool(ok_ts and ok_map),
        'details': {'ids': len((idx1.get('id_to_tokens') or {}))}
    }


def check_cycle_record_stability(data_id: Optional[str] = None) -> Dict[str, Any]:
    act_path = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    act = _read_json(act_path) or {}
    cycles: List[Dict[str, Any]] = act.get('cycles') or []
    if isinstance(data_id, str) and data_id:
        cycles = [c for c in cycles if isinstance(c, dict) and c.get('data_id') == data_id]
    if len(cycles) < 2:
        # Not enough cycles captured; treat as pass with note
        return {'check': 'cycle_record_stability', 'passed': True, 'details': {'note': 'Insufficient cycles to compare'}}
    a = _strip_dynamic(copy.deepcopy(cycles[-1]))
    b = _strip_dynamic(copy.deepcopy(cycles[-2]))
    return {
        'check': 'cycle_record_stability',
        'passed': (a == b),
        'details': {'compared': 2}
    }


def evaluate_determinism_suite(data_id: str = 'det_suite', content: str = 'determinism check useful beneficial', category: str = 'semantic') -> Dict[str, Any]:
    fixed = _fixed_ts()
    # Run two cycles to capture state and compare
    RelationalMeasurement(data_id, content, category)
    RelationalMeasurement(data_id, content, category)
    checks = []
    checks.append(check_collector_timestamps(data_id))
    checks.append(check_index_stability())
    checks.append(check_cycle_record_stability(data_id))
    # Scheduler determinism: future_event_time should be stable when deterministic
    try:
        sem_path = os.path.join(BASE, 'LongTermStore', 'Semantic', f'{data_id}.json')
        rec = _read_json(sem_path) or {}
        fet1 = rec.get('future_event_time')
        # trigger one more flag to be sure
        RelationalMeasurement(data_id, content, category)
        rec2 = _read_json(sem_path) or {}
        fet2 = rec2.get('future_event_time')
        sched_ok = True
        if fixed:
            sched_ok = bool(fet1 and fet2 and fet1 == fet2)
        checks.append({'check': 'scheduler_future_event_time', 'passed': sched_ok, 'details': {'fet1': fet1, 'fet2': fet2}})
    except Exception:
        checks.append({'check': 'scheduler_future_event_time', 'passed': False})
    overall = all(c.get('passed') for c in checks)
    report = {
        'deterministic_mode': bool(fixed is not None),
        'fixed_timestamp': fixed,
        'overall_passed': overall,
        'checks': checks
    }
    # Persist report to ActiveSpace for auditing
    out_path = os.path.join(BASE, 'ActiveSpace', f'determinism_report_{data_id}.json')
    _write_json(out_path, report)
    return report


if __name__ == '__main__':
    rep = evaluate_determinism_suite()
    print(json.dumps(rep, indent=2))
