# module_toggle.py
import shutil, os, json

from module_metrics import build_learning_sandbox_activation_report
from module_tools import sanitize_id, safe_join, _load_config, _ts
from module_storage import _atomic_write_json

def move(data_id, source, target, policy_rule_id=None, reason=None):
    """
    Move a file between spaces at the workspace root: TemporaryQueue, ActiveSpace,
    HoldingSpace, DiscardSpace. Falls back to LongTermStore/Semantic if source file
    is missing (first-time move after storage).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spaces_root = base_dir

    try:
        safe_id = sanitize_id(data_id)
    except Exception:
        return f"Invalid data_id for move(): {data_id}"

    src_path = safe_join(spaces_root, os.path.join(source, f"{safe_id}.json"))
    tgt_path = safe_join(spaces_root, os.path.join(target, f"{safe_id}.json"))
    os.makedirs(os.path.dirname(src_path), exist_ok=True)
    os.makedirs(os.path.dirname(tgt_path), exist_ok=True)

    if not os.path.exists(src_path):
        # Fallback: look under LongTermStore/Semantic as initial source
        candidate = safe_join(base_dir, os.path.join("LongTermStore", "Semantic", f"{safe_id}.json"))
        if os.path.exists(candidate):
            shutil.copy(candidate, src_path)

    shutil.move(src_path, tgt_path)
    # Justification annotation: append to target file
    try:
        with open(tgt_path, 'r', encoding='utf-8') as f:
            rec = json.load(f)
        j = rec.setdefault('toggle_justifications', [])
        j.append({
            'policy_rule_id': str(policy_rule_id or 'default'),
            'reason': str(reason or f'move {source}->{target}'),
            'timestamp': __ts()
        })
        _atomic_write_json(tgt_path, rec)
    except Exception:
        pass
    return f"Moved {data_id} from {source} to {target}"

def toggle_space(space_name):
    return f"Toggled to {space_name} space."

def __ts():
    return _ts()


def _build_policy_schedule_sandbox_state(policy_inputs, cfg, readiness_verdict):
    policy_cfg = (cfg.get('policy') or {}) if isinstance(cfg, dict) else {}
    activation_cfg = policy_cfg.get('activation') if isinstance(policy_cfg.get('activation'), dict) else {}
    determinism_cfg = cfg.get('determinism') if isinstance(cfg.get('determinism'), dict) else {}

    try:
        sel_min_ben_syn = float(activation_cfg.get('sel_min_ben_syn', 0.4))
    except Exception:
        sel_min_ben_syn = 0.4
    try:
        comp_activate = float(activation_cfg.get('composite_activate', 0.55))
    except Exception:
        comp_activate = 0.55

    gate_report = {
        'ready': False,
        'status': 'unknown',
        'reason': 'learning readiness verdict unavailable',
        'unmet_conditions': [],
        'deterministic_mode': bool(determinism_cfg.get('deterministic_mode', False)),
        'fixed_timestamp': determinism_cfg.get('fixed_timestamp') if determinism_cfg.get('deterministic_mode') else None,
    }
    if isinstance(readiness_verdict, dict):
        gate_report.update({
            'ready': bool(readiness_verdict.get('ready', False)),
            'status': readiness_verdict.get('status') if isinstance(readiness_verdict.get('status'), str) else ('ready' if readiness_verdict.get('ready') else 'not_ready'),
            'reason': readiness_verdict.get('reason') if isinstance(readiness_verdict.get('reason'), str) else None,
            'unmet_conditions': list(readiness_verdict.get('unmet_conditions') or []) if isinstance(readiness_verdict.get('unmet_conditions'), list) else [],
        })
    preserve_baseline = True
    activation_mode = 'learning_readiness_gated'

    if gate_report.get('status') == 'unknown':
        status = 'blocked'
        active = False
        blocked_reason = 'learning_readiness_verdict_unavailable'
    elif not bool(gate_report.get('ready')):
        status = 'blocked'
        active = False
        blocked_reason = 'learning_readiness_not_ready'
    else:
        status = 'active'
        active = True
        blocked_reason = None

    return {
        'version': 1,
        'sandbox': 'policy_schedule_priority',
        'status': status,
        'active': active,
        'blocked_reason': blocked_reason,
        'configured_paths': ['schedule_priority'],
        'active_paths': ['schedule_priority'] if active else [],
        'read_only': True,
        'persistent_state': False,
        'mutable_weights': False,
        'readiness': {
            'status': gate_report.get('status'),
            'reason': gate_report.get('reason'),
            'unmet_conditions': list(gate_report.get('unmet_conditions') or []),
        },
        'config_snapshot': {
            'policy_activation_present': bool(activation_cfg),
            'sel_min_ben_syn': float(sel_min_ben_syn),
            'composite_activate': float(comp_activate),
        },
        'path_metadata': {
            'schedule_priority': {
                'configured': True,
                'priority_source': 'policy.activation',
                'thresholds': {
                    'sel_min_ben_syn': float(sel_min_ben_syn),
                    'composite_activate': float(comp_activate),
                },
            },
        },
        'activation_mode': activation_mode,
        'preserve_baseline_when_blocked': preserve_baseline,
    }

def decide_toggle(policy_inputs):
    """Phase 13: policy-driven toggle decision.
    policy_inputs: dict with keys usefulness, contradiction, description_maturity
    Returns target space and justification.
    """
    usefulness = policy_inputs.get('usefulness')
    contradiction = policy_inputs.get('contradiction', False)
    maturity = policy_inputs.get('description_maturity', 'unknown')
    sel_score = float(policy_inputs.get('selection_score', 0.0))
    sim = float(policy_inputs.get('similarity', 0.0))
    obj_align = str(policy_inputs.get('objective_alignment', 'unknown')).lower()
    # Composite score: weighting selection and similarity; usefulness boosts
    comp = (0.5 * sel_score) + (0.4 * sim) + (0.1 if usefulness == 'useful_now' else 0.0)
    # Load optional thresholds from config
    try:
        cfg = _load_config() or {}
        pol = (cfg.get('policy') or {}).get('activation', {})
        sel_min_ben_syn = float(pol.get('sel_min_ben_syn', 0.4))
        comp_activate = float(pol.get('composite_activate', 0.55))
        sandbox_settings = cfg.get('selection_migration', {}) if isinstance(cfg, dict) else {}
    except Exception:
        sel_min_ben_syn = 0.4
        comp_activate = 0.55
        sandbox_settings = {}

    readiness_verdict = policy_inputs.get('learning_readiness') if isinstance(policy_inputs.get('learning_readiness'), dict) else None
    sandbox_state = policy_inputs.get('learning_sandbox_state') if isinstance(policy_inputs.get('learning_sandbox_state'), dict) else None
    if not isinstance(sandbox_state, dict):
        sandbox_state = build_learning_sandbox_activation_report(
            readiness_verdict=readiness_verdict,
            sandbox_settings=sandbox_settings,
            sandbox_name='selection_migration',
        )

    policy_sandbox_state = policy_inputs.get('policy_sandbox_state') if isinstance(policy_inputs.get('policy_sandbox_state'), dict) else None
    if not isinstance(policy_sandbox_state, dict):
        policy_sandbox_state = _build_policy_schedule_sandbox_state(policy_inputs, cfg, readiness_verdict)

    def _with_sandbox(justification):
        out = dict(justification)
        if isinstance(sandbox_state, dict):
            out['sandbox_state'] = sandbox_state
        if isinstance(policy_sandbox_state, dict):
            out['policy_sandbox_state'] = policy_sandbox_state
        return out

    ben_syn = bool(policy_inputs.get('beneficial_and_synthesis', False))
    if contradiction:
        return 'HoldingSpace', _with_sandbox({'policy_rule_id': 'quarantine_on_contradiction', 'reason': 'Contradictions present'})
    # Strong signal: both beneficial and synthesis_value present (with ranking/align support)
    # Gate by either modest selection score or explicit objective alignment
    if ben_syn and (sel_score >= sel_min_ben_syn or obj_align == 'aligned'):
        return 'ActiveSpace', _with_sandbox({'policy_rule_id': 'activate_on_beneficial_synthesis_ranked', 'reason': f'Beneficial+synthesis; sel={round(sel_score,3)} align={obj_align}'})
    if (usefulness == 'useful_now' and maturity in ('stable','strong')) or comp >= comp_activate:
        return 'ActiveSpace', _with_sandbox({'policy_rule_id': 'activate_on_composite', 'reason': f'Composite={round(comp,3)} sel={sel_score} sim={sim}'})
    if usefulness in ('useful_later','not_useful'):
        return 'HoldingSpace', _with_sandbox({'policy_rule_id': 'hold_on_low_usefulness', 'reason': 'Deferred or uncertain value'})
    return 'HoldingSpace', _with_sandbox({'policy_rule_id': 'default_hold', 'reason': 'Default policy'})
