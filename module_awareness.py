# module_awareness.py

"""module_awareness

How They Work Together
- Awareness Module:
- Detects repetition (occurrence_count > 1) and triggers information‑seeking.
- Validates responses against ideological correctness (stubbed for now).
- Scheduler Module:
- Flags records with labels.
- Adds a future_event_time into the JSON metadata, simulating scheduled review or synthesis.
"""

import datetime
import json
import os


def _now_ts() -> str:
    """Return a timestamp string.

    - If deterministic mode is enabled, returns the configured fixed timestamp.
    - Otherwise, returns a UTC Zulu timestamp.
    """
    try:
        from module_tools import _load_config
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def trigger_information_seeking_if(repetition, similarity, related, synthesis):
    """
    Trigger awareness if repetition, similarity, relatedness, or synthesis potential are present.
    """
    if repetition > 1 or similarity >= 0.8 or related or synthesis:
        return f"[{_now_ts()}] Awareness triggered: seeking more context"
    return f"[{_now_ts()}] Awareness not triggered"

def trigger_information_seeking(data_id, occurrence_count):
    """
    Trigger awareness when repetition patterns are detected.
    For now: if occurrence_count > 1, awareness is activated.
    """
    if occurrence_count > 1:
        return f"[{_now_ts()}] Awareness triggered: seeking more context for {data_id}"
    return f"[{_now_ts()}] No awareness triggered for {data_id}"

def validate_response(data_id):
    """
    Validate ideological correctness before responding.
    Placeholder: always returns validated.
    """
    return f"[{_now_ts()}] Response for {data_id} validated as ideologically correct"

def awareness_plan(data_id, signals, objectives):
    """
    Phase 10: Produce a structured plan object based on triggers.
    signals: dict with keys like repeat, similarity, contradiction, usefulness
    objectives: list of objective dicts or strings
    """
    repeat = signals.get('repeat', 0)
    similarity = signals.get('similarity', 0.0)
    contradiction = signals.get('contradiction', False)
    usefulness = signals.get('usefulness', 'not_useful')
    trigger_reasons = []
    if repeat > 1: trigger_reasons.append('repeat')
    if similarity >= 0.8: trigger_reasons.append('similarity')
    if contradiction: trigger_reasons.append('contradiction')
    if usefulness == 'useful_now': trigger_reasons.append('opportunity')

    # derive severity
    if contradiction:
        severity = 'severe'
    elif usefulness == 'useful_now' and similarity >= 0.8:
        severity = 'moderate'
    elif repeat > 1:
        severity = 'minor'
    else:
        severity = 'minor'

    information_to_seek = []
    tools_to_use = []
    plan_steps = []

    if contradiction:
        information_to_seek.append({'question': 'Resolve conflicting claims', 'target': data_id})
        tools_to_use.extend(['search_internet'])
        plan_steps.extend(['gather_evidence', 'compare_claims', 'update_registry'])
    if usefulness == 'useful_now':
        plan_steps.append('schedule_synthesis')
    if similarity >= 0.8:
        plan_steps.append('retrieve_related')

    # Validate against objectives (stub: ensure no forbidden labels)
    obj_texts = [o if isinstance(o, str) else o.get('objective', '') for o in (objectives or [])]
    if any('forbid' in str(t).lower() for t in obj_texts):
        # downgrade severity
        severity = 'minor'

    return {
        'data_id': data_id,
        'trigger_reasons': trigger_reasons,
        'information_to_seek': information_to_seek,
        'tools_to_use': tools_to_use,
        'plan_steps': plan_steps,
        'severity': severity,
        'validated': True,
        'timestamp': _now_ts()
    }