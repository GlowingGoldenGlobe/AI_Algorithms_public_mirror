# module_toggle.py
import shutil, os, json

from module_tools import sanitize_id, safe_join, _load_config

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
        with open(tgt_path, 'r+', encoding='utf-8') as f:
            rec = json.load(f)
            j = rec.setdefault('toggle_justifications', [])
            j.append({
                'policy_rule_id': policy_rule_id or 'default',
                'reason': reason or f'move {source}->{target}',
                'timestamp': __ts()
            })
            f.seek(0)
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception:
        pass
    return f"Moved {data_id} from {source} to {target}"

def toggle_space(space_name):
    return f"Toggled to {space_name} space."

def __ts():
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

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
        from module_tools import _load_config
        cfg = _load_config() or {}
        pol = (cfg.get('policy') or {}).get('activation', {})
        sel_min_ben_syn = float(pol.get('sel_min_ben_syn', 0.4))
        comp_activate = float(pol.get('composite_activate', 0.55))
    except Exception:
        sel_min_ben_syn = 0.4
        comp_activate = 0.55
    ben_syn = bool(policy_inputs.get('beneficial_and_synthesis', False))
    if contradiction:
        return 'HoldingSpace', {'policy_rule_id': 'quarantine_on_contradiction', 'reason': 'Contradictions present'}
    # Strong signal: both beneficial and synthesis_value present (with ranking/align support)
    # Gate by either modest selection score or explicit objective alignment
    if ben_syn and (sel_score >= sel_min_ben_syn or obj_align == 'aligned'):
        return 'ActiveSpace', {'policy_rule_id': 'activate_on_beneficial_synthesis_ranked', 'reason': f'Beneficial+synthesis; sel={round(sel_score,3)} align={obj_align}'}
    if (usefulness == 'useful_now' and maturity in ('stable','strong')) or comp >= comp_activate:
        return 'ActiveSpace', {'policy_rule_id': 'activate_on_composite', 'reason': f'Composite={round(comp,3)} sel={sel_score} sim={sim}'}
    if usefulness in ('useful_later','not_useful'):
        return 'HoldingSpace', {'policy_rule_id': 'hold_on_low_usefulness', 'reason': 'Deferred or uncertain value'}
    return 'HoldingSpace', {'policy_rule_id': 'default_hold', 'reason': 'Default policy'}
