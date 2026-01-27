from __future__ import annotations

from typing import Any, Dict, List


def _clamp01(value: Any, default: float = 0.5) -> float:
    try:
        x = float(value)
    except Exception:
        return float(default)
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute_focus_state(objectives: Any) -> Dict[str, Any]:
    """Compute a deterministic focus/concentration snapshot for a single cycle.

    This intentionally does NOT store global state. It returns a small object
    that can be passed through the cycle and optionally persisted into a record.

    objectives: expected to be a list of objective records (dicts) from
    module_objectives.get_objectives_by_label().
    """
    active_objectives: List[Dict[str, Any]] = []

    if isinstance(objectives, list):
        for obj in objectives:
            if not isinstance(obj, dict):
                continue
            objective_id = obj.get("id")
            if not isinstance(objective_id, str) or not objective_id:
                continue

            # Repo objective schema does not define priority; treat these fields as optional.
            weight = _clamp01(obj.get("priority", obj.get("weight", 0.5)), default=0.5)
            active_objectives.append(
                {
                    "objective_id": objective_id,
                    "weight": weight,
                    "reason": "objective_active",
                }
            )

    # Deterministic ordering by objective_id to avoid filesystem listing nondeterminism.
    active_objectives.sort(key=lambda x: x.get("objective_id", ""))

    focus_state: Dict[str, Any] = {
        "active_objectives": active_objectives,
        "attention_filters": {
            "required_tags": [],
            "required_categories": ["semantic"],
            "max_age_days": 30,
        },
        "focus_budget": {"max_items": 20, "max_tokens": 5000},
    }

    return focus_state
