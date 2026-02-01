# module_measure.py
from module_tools import similarity, familiarity, usefulness, synthesis_potential, compare_against_objectives
import json
import os

# Workspace root resolution (not currently used elsewhere in this module)
ROOT = os.path.dirname(os.path.abspath(__file__))

DEFAULT_WEIGHTS = {
    'similarity': 0.4,
    'usefulness': 0.4,
    'repeat': 0.1,
    'contradiction': -0.6,
    'synthesis_bias': 0.2,
    'review_bias': 0.1
}

def get_measurement_weights():
    cfg = {}
    try:
        with open(os.path.join(ROOT, 'config.json'), 'r', encoding='utf-8') as cf:
            cfg = json.load(cf)
    except Exception:
        cfg = {}
    raw = cfg.get('measurement_weights') or {}
    return {
        'similarity': float(raw.get('similarity', DEFAULT_WEIGHTS['similarity'])),
        'usefulness': float(raw.get('usefulness', DEFAULT_WEIGHTS['usefulness'])),
        'repeat': float(raw.get('repeat', DEFAULT_WEIGHTS['repeat'])),
        'contradiction': float(raw.get('contradiction', DEFAULT_WEIGHTS['contradiction'])),
        'synthesis_bias': float(raw.get('synthesis_bias', DEFAULT_WEIGHTS['synthesis_bias'])),
        'review_bias': float(raw.get('review_bias', DEFAULT_WEIGHTS['review_bias']))
    }

def print_weights():
    w = get_measurement_weights()
    print(json.dumps(w, indent=2))

def get_occurrence(data_path: str) -> int:
    """Return occurrence count from a stored record."""
    with open(data_path, "r", encoding="utf-8") as f:
        record = json.load(f)
    return record.get("occurrence_count", 0)

def analyzer_evaluate(data_path: str) -> float:
    """Evaluate data using occurrence count and placeholder logic."""
    occurrence = get_occurrence(data_path)
    # Example scoring: higher occurrence = higher relevance
    score = occurrence * 1.0
    return score

def scheduler_flag(data_path: str, label: str):
    """Flag a record with a label for future scheduling."""
    with open(data_path, "r+", encoding="utf-8") as f:
        record = json.load(f)
        record["labels"].append(label)
        f.seek(0)
        json.dump(record, f, indent=2)
        f.truncate()
    return f"Flagged {data_path} with label {label}"

"""
def measure_information(data_path: str, threshold: float = 2.0):
    #Measure information and decide whether to flag or discard.
    score = analyzer_evaluate(data_path)
    if score >= threshold:
        return scheduler_flag(data_path, "important")
    else:
        return f"Discarded {data_path} (score={score})"
"""

def measure_information(file_path, threshold=1.0, objectives=None, focus_state=None):
    """
    Phase 9: Produce a structured measurement report with signals,
    recommended_actions, conflicts, and reasons.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    content = data.get("content", "")
    data_id = data.get("id", os.path.basename(file_path))

    if objectives is None:
        try:
            from module_objectives import get_objectives_by_label
            objectives = get_objectives_by_label("measurement") or ["measurement"]
        except Exception:
            objectives = ["measurement"]

    sim_score = similarity(content, "current_subject", "long_term_index", exclude_id=data_id)
    fam = familiarity(data_id, data.get("occurrence_count", 0), data.get("labels", []))
    use = usefulness(content, objectives, "current_activity")
    syn = synthesis_potential(content, "current_subject", [], objectives, "long_term_index")
    obj_rel = compare_against_objectives(content, objectives)

    repeat_signal = {
        "count": data.get("occurrence_count", 0),
        "stability": ((data.get("repetition_profile") or {}).get("stability_score", 0.5))
    }
    similarity_signal = sim_score
    usefulness_signal = use
    contradiction_signal = (obj_rel == "conflict")

    # Optional focus/concentration nudges (deterministic, small, and capped).
    # This does not change behavior unless focus_state is explicitly provided.
    try:
        if isinstance(focus_state, dict):
            active = focus_state.get("active_objectives")
            if isinstance(active, list) and active:
                # If we have any active objectives and we're already aligned, bias usefulness to useful_now.
                if obj_rel == "aligned":
                    usefulness_signal = "useful_now"
                # Small similarity boost when focus is active.
                similarity_signal = min(1.0, float(similarity_signal) + 0.1)
                # Increase contradiction sensitivity only when explicitly conflicting.
                contradiction_signal = bool(obj_rel == "conflict")
    except Exception:
        pass

    # Weighted arbiter inputs (tolerant to missing keys)
    wcfg = get_measurement_weights()
    recommended_actions = []
    reasons = []
    if contradiction_signal:
        recommended_actions.append("contradiction_resolve")
        reasons.append("Objective conflict detected")
    if usefulness_signal == "useful_now" and similarity_signal >= 0.8:
        recommended_actions.append("synthesis")
        reasons.append("High similarity and immediate usefulness")
    if repeat_signal["count"] > 1 and repeat_signal["stability"] >= 0.6:
        recommended_actions.append("review")
        reasons.append("Stable repeats warrant reinforcement")

    conflicts = []
    # conflict: synthesis and contradiction_resolve at same time
    if "synthesis" in recommended_actions and "contradiction_resolve" in recommended_actions:
        conflicts.append({"actions": ["synthesis","contradiction_resolve"], "reason": "mutually exclusive"})

    # Compute weighted score for decisive recommendation
    score = (
        wcfg['similarity'] * float(similarity_signal) +
        wcfg['usefulness'] * (1.0 if usefulness_signal == 'useful_now' else 0.0) +
        wcfg['repeat'] * float(repeat_signal.get('stability', 0.0)) +
        wcfg['contradiction'] * (1.0 if contradiction_signal else 0.0)
    )
    if 'synthesis' in recommended_actions:
        score += wcfg.get('synthesis_bias', 0.0)
    if 'review' in recommended_actions:
        score += wcfg.get('review_bias', 0.0)
    decisive = None
    if contradiction_signal and score < 0:
        decisive = 'contradiction_resolve'
    elif (usefulness_signal == 'useful_now' and similarity_signal >= 0.8) and score >= 0.6:
        decisive = 'synthesis'
    elif score >= 0.3:
        decisive = 'review'
    return {
        "repeat_signal": repeat_signal,
        "similarity_signal": similarity_signal,
        "usefulness_signal": usefulness_signal,
        "contradiction_signal": contradiction_signal,
        "recommended_actions": recommended_actions,
        "decisive_recommendation": decisive,
        "weighted_score": score,
        "reasons": reasons,
        "conflicts": conflicts,
        "objective_relation": obj_rel,
        # Optional additive field: uncertainty payloads for numeric signals.
        # JSON-friendly: { value, variance, provenance }
        "uncertainties": _build_uncertainties(
            data_id=data_id,
            similarity_signal=similarity_signal,
            weighted_score=score,
            repeat_stability=float(repeat_signal.get('stability', 0.0)),
        ),
    }


def _build_uncertainties(*, data_id: str, similarity_signal: float, weighted_score: float, repeat_stability: float):
    """Create deterministic, structure-only uncertainty objects for numeric signals."""
    try:
        from module_uncertainty import now_ts

        ts = float(now_ts())
    except Exception:
        ts = 0.0

    def _u(value: float, sigma: float, metric: str):
        s = max(0.0, float(sigma))
        return {
            'value': float(value),
            'variance': float(s * s),
            'provenance': {
                'metric': str(metric),
                'target_id': str(data_id),
                'ts': float(ts),
                'method': 'heuristic',
            },
        }

    # Heuristic uncertainty: higher certainty near extremes for similarity; moderate baseline for score.
    sim = float(similarity_signal)
    sim_sigma = 0.05 + 0.15 * float(min(sim, 1.0 - sim))
    score_sigma = 0.15
    rep_sigma = 0.10

    return {
        'similarity_signal': _u(sim, sim_sigma, 'similarity_signal'),
        'weighted_score': _u(float(weighted_score), score_sigma, 'weighted_score'),
        'repeat_stability': _u(float(repeat_stability), rep_sigma, 'repeat_stability'),
    }