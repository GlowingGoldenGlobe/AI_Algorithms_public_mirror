"""module_reasoning.py

Deterministic, side-effect-free reasoning helpers.

This module is intentionally minimal and used primarily by the eval harness.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, TypedDict


class Record(TypedDict, total=False):
    record_id: str
    value: Any
    context_id: str
    conceptual_vector: list[float]
    objective_links: dict[str, float]
    derived: bool
    inputs: list[str]


class SynthesisOpportunity(TypedDict):
    target_ids: list[str]
    coherence_gain: float


class SynthesisResult(TypedDict):
    new_record_id: str
    value: Any
    conceptual_vector: list[float]
    inputs: list[str]
    coherence_gain: float


def _quantile_sorted(xs_sorted: list[float], q: float) -> Optional[float]:
    if not xs_sorted:
        return None
    if q <= 0.0:
        return float(xs_sorted[0])
    if q >= 1.0:
        return float(xs_sorted[-1])
    # Linear interpolation between adjacent ranks.
    pos = q * float(len(xs_sorted) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(xs_sorted[lo])
    frac = pos - float(lo)
    return float(xs_sorted[lo] * (1.0 - frac) + xs_sorted[hi] * frac)


def summarize_numeric_distribution(*, values: list[Any]) -> Dict[str, Any]:
    """Summarize numeric values deterministically.

    Returns JSON-friendly stats. Non-numeric values are ignored.
    """
    nums: list[float] = []
    for v in values or []:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            try:
                nums.append(float(v))
            except Exception:
                continue

    nums_sorted = sorted(nums)
    n = len(nums_sorted)
    if n <= 0:
        return {
            'n': 0,
            'mean': None,
            'stdev': None,
            'min': None,
            'max': None,
            'p05': None,
            'p50': None,
            'p95': None,
        }

    mean = float(sum(nums_sorted) / float(n))
    var = float(sum((x - mean) * (x - mean) for x in nums_sorted) / float(n))
    stdev = float(math.sqrt(var))
    return {
        'n': int(n),
        'mean': float(mean),
        'stdev': float(stdev),
        'min': float(nums_sorted[0]),
        'max': float(nums_sorted[-1]),
        'p05': _quantile_sorted(nums_sorted, 0.05),
        'p50': _quantile_sorted(nums_sorted, 0.50),
        'p95': _quantile_sorted(nums_sorted, 0.95),
    }


def _get_entity_by_id(relational_state: Dict[str, Any], entity_id: str) -> Optional[Dict[str, Any]]:
    entities = relational_state.get("entities")
    if not isinstance(entities, list):
        return None
    for e in entities:
        if isinstance(e, dict) and e.get("id") == entity_id:
            return e
    return None


def _get_numeric_attr(entity: Dict[str, Any], attr: str) -> Optional[float]:
    attrs = entity.get("attributes")
    if not isinstance(attrs, dict):
        return None
    v = attrs.get(attr)
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def check_constraints(relational_state: Dict[str, Any]) -> Dict[str, Any]:
    """Check constraints deterministically.

    Supported constraint forms (minimal):
    - {"type": "lt"|"gt"|"eq"|"neq", "args": {"entity_id": "A", "attribute": "volume", "value": 0.1}, "severity": "hard"|"soft"}

        Returns (backward-compatible superset):
            {
                "violations": [
                    {
                        "constraint": <original constraint>,
                        "reason": "<string>",
                        "severity": "hard"|"soft",
                        ...
                    }
                ],
                "has_hard_violation": bool,
                "has_soft_violation": bool,
                "contradiction": bool
            }
    """
    violations: List[Dict[str, Any]] = []
    constraints = relational_state.get("constraints")
    if not isinstance(constraints, list):
        constraints = []

    for i, c in enumerate(constraints):
        if not isinstance(c, dict):
            continue
        ctype = c.get("type")
        if ctype not in ("lt", "gt", "eq", "neq", "spatial"):
            continue
        args = c.get("args")
        if not isinstance(args, dict):
            continue
        entity_id = args.get("entity_id")
        severity = c.get("severity") if c.get("severity") in ("hard", "soft") else "soft"

        if not isinstance(entity_id, str) or not entity_id:
            continue

        if ctype == "spatial":
            # Minimal deterministic validation of spatial constraints.
            # Spec alignment: missing/malformed data is treated as SOFT violation;
            # explicit mismatches use the constraint severity.
            ent = _get_entity_by_id(relational_state, entity_id)
            bounds = args.get("bounds")
            units = args.get("units")
            volume_spec = args.get("volume")

            details: Dict[str, Any] = {}
            violated_missing_or_malformed = False
            violated_mismatch = False

            if units is not None and not isinstance(units, str):
                violated_missing_or_malformed = True
                details["units_invalid"] = True

            # Bounds: validate shape/order (and optionally compare to entity bounds structure).
            if bounds is not None:
                if not isinstance(bounds, dict):
                    violated_missing_or_malformed = True
                    details["bounds_invalid"] = True
                else:
                    mn = bounds.get("min")
                    mx = bounds.get("max")
                    if not (
                        isinstance(mn, (list, tuple))
                        and isinstance(mx, (list, tuple))
                        and len(mn) == 3
                        and len(mx) == 3
                    ):
                        violated_missing_or_malformed = True
                        details["bounds_shape_invalid"] = True
                    else:
                        try:
                            mnf = [float(mn[0]), float(mn[1]), float(mn[2])]
                            mxf = [float(mx[0]), float(mx[1]), float(mx[2])]
                            if any(mnf[d] > mxf[d] for d in range(3)):
                                violated_mismatch = True
                                details["bounds_order_invalid"] = True
                        except Exception:
                            violated_missing_or_malformed = True
                            details["bounds_numeric_invalid"] = True

            # Volume: support numeric, or range dict like {"min": 0.0, "max": 5.0}.
            if volume_spec is not None:
                if isinstance(volume_spec, (int, float)) and not isinstance(volume_spec, bool):
                    # Interpret as a non-negative validation only.
                    if float(volume_spec) < 0.0:
                        violated_mismatch = True
                        details["volume_negative"] = True
                elif isinstance(volume_spec, dict):
                    vmin = volume_spec.get("min")
                    vmax = volume_spec.get("max")
                    try:
                        vmin_f = float(vmin) if vmin is not None else None
                    except Exception:
                        vmin_f = None
                        details["volume_min_invalid"] = True
                    try:
                        vmax_f = float(vmax) if vmax is not None else None
                    except Exception:
                        vmax_f = None
                        details["volume_max_invalid"] = True

                    if (vmin is not None and vmin_f is None) or (vmax is not None and vmax_f is None):
                        violated_missing_or_malformed = True
                    else:
                        if vmin_f is not None and vmax_f is not None and vmin_f > vmax_f:
                            violated_mismatch = True
                            details["volume_range_invalid"] = True

                        if ent is None:
                            violated_missing_or_malformed = True
                            details["entity_missing"] = True
                        else:
                            actual = _get_numeric_attr(ent, "volume")
                            if actual is None:
                                violated_missing_or_malformed = True
                                details["entity_volume_missing"] = True
                            else:
                                if vmin_f is not None and actual < vmin_f:
                                    violated_mismatch = True
                                    details["volume_below_min"] = True
                                if vmax_f is not None and actual > vmax_f:
                                    violated_mismatch = True
                                    details["volume_above_max"] = True
                else:
                    violated_missing_or_malformed = True
                    details["volume_spec_invalid"] = True

            if ent is None and (bounds is not None or volume_spec is not None):
                violated_missing_or_malformed = True
                details.setdefault("entity_missing", True)

            if violated_missing_or_malformed or violated_mismatch:
                out_severity = "soft" if violated_missing_or_malformed else severity
                if violated_missing_or_malformed:
                    reason = "missing or malformed spatial data"
                else:
                    # Prefer a specific reason when the mismatch is a volume range breach.
                    if details.get("volume_above_max"):
                        reason = "volume exceeds allowed maximum"
                    elif details.get("volume_below_min"):
                        reason = "volume below allowed minimum"
                    elif details.get("bounds_order_invalid"):
                        reason = "bounds invalid (min greater than max)"
                    else:
                        reason = "spatial constraint mismatch"
                violations.append(
                    {
                        "index": i,
                        "type": ctype,
                        "severity": out_severity,
                        "entity_id": entity_id,
                        "constraint": c,
                        "reason": reason,
                        "details": details,
                    }
                )
            continue

        # Numeric attribute constraints.
        attr = args.get("attribute")
        value = args.get("value")
        if not isinstance(attr, str) or not attr:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        ent = _get_entity_by_id(relational_state, entity_id)
        if ent is None:
            # Spec alignment: missing/malformed data -> SOFT violation.
            violated = True
            actual = None
            out_severity = "soft"
        else:
            actual = _get_numeric_attr(ent, attr)
            violated = actual is None
            out_severity = severity
            if actual is not None:
                if ctype == "lt":
                    violated = not (actual < float(value))
                elif ctype == "gt":
                    violated = not (actual > float(value))
                elif ctype == "eq":
                    violated = not (actual == float(value))
                elif ctype == "neq":
                    violated = not (actual != float(value))
            else:
                out_severity = "soft"

        if violated:
            reason = "constraint_violation"
            if ent is None:
                reason = "entity_missing"
            elif actual is None:
                reason = "attribute_missing_or_non_numeric"
            violations.append(
                {
                    "index": i,
                    "type": ctype,
                    "severity": out_severity,
                    "entity_id": entity_id,
                    "attribute": attr,
                    "expected": float(value),
                    "actual": actual,
                    "constraint": c,
                    "reason": reason,
                }
            )

    violations.sort(key=lambda v: int(v.get("index", 0)))
    has_hard = any(v.get("severity") == "hard" for v in violations)
    has_soft = any(v.get("severity") == "soft" for v in violations)
    return {
        "violations": violations,
        "has_hard_violation": has_hard,
        "has_soft_violation": has_soft,
        "contradiction": bool(has_hard),
    }


def detect_contradictions(relational_state: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic contradiction detection.
    
    Rule (minimal): same subj + pred, different obj, both confidence >= 0.8.
    """

    relations = relational_state.get("relations")
    if not isinstance(relations, list):
        relations = []

    # Build (subj,pred) -> list[(idx,obj,conf)]
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for idx, r in enumerate(relations):
        if not isinstance(r, dict):
            continue
        subj = r.get("subj")
        pred = r.get("pred")
        obj = r.get("obj")
        conf = r.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 0.0
        except Exception:
            conf_f = 0.0
        if conf_f < 0.8:
            continue
        if not (isinstance(subj, str) and isinstance(pred, str) and isinstance(obj, str)):
            continue
        key = subj + "\u241f" + pred
        buckets.setdefault(key, []).append({"index": idx, "subj": subj, "pred": pred, "obj": obj, "confidence": conf_f})

    contradictions: List[Dict[str, Any]] = []
    # Deterministic iteration order.
    for key in sorted(buckets.keys()):
        rows = buckets[key]
        # Sort by index for stable pair generation.
        rows = sorted(rows, key=lambda x: int(x.get("index", 0)))
        seen_objs: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            o = row.get("obj")
            if not isinstance(o, str):
                continue
            if o not in seen_objs:
                seen_objs[o] = row

        objs = sorted(seen_objs.keys())
        if len(objs) <= 1:
            continue
        # Generate contradictions between the earliest-seen object and each different object.
        base_row = min(seen_objs.values(), key=lambda x: int(x.get("index", 0)))
        for o in objs:
            other_row = seen_objs[o]
            if other_row.get("obj") == base_row.get("obj"):
                continue
            r1 = relations[int(base_row.get("index", 0))] if isinstance(base_row.get("index"), int) and 0 <= int(base_row.get("index")) < len(relations) else {}
            r2 = relations[int(other_row.get("index", 0))] if isinstance(other_row.get("index"), int) and 0 <= int(other_row.get("index")) < len(relations) else {}
            contradictions.append(
                {
                    "type": "relation_conflict",
                    "entities": [base_row.get("subj")],
                    # Copilot example shape: relations as small descriptors.
                    "relations": [
                        {
                            "pred": r1.get("pred"),
                            "obj": r1.get("obj"),
                            "confidence": r1.get("confidence"),
                            "source": r1.get("source"),
                        },
                        {
                            "pred": r2.get("pred"),
                            "obj": r2.get("obj"),
                            "confidence": r2.get("confidence"),
                            "source": r2.get("source"),
                        },
                    ],
                    # Backward-compatible indices (useful for debugging).
                    "relation_indices": [base_row.get("index"), other_row.get("index")],
                    "reason": "conflicting values for same predicate",
                }
            )

    has_contradiction = bool(contradictions)
    return {
        "contradictions": contradictions,
        "has_contradiction": has_contradiction,
        # Backward-compatible flag.
        "contradiction": has_contradiction,
        "via": "relation_conflict" if has_contradiction else "none",
    }


def propose_actions(relational_state: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
    """Propose high-level actions deterministically from relational_state + signals."""
    rc = check_constraints(relational_state)
    cd = detect_contradictions(relational_state)

    has_hard = bool(rc.get("has_hard_violation"))
    has_contra = bool(cd.get("has_contradiction") or cd.get("contradiction"))

    similarity = signals.get("similarity")
    try:
        similarity_f = float(similarity)
    except Exception:
        similarity_f = 0.0
    usefulness = signals.get("usefulness")
    objective_relation = signals.get("objective_relation")

    recommended: List[str] = []
    reasons: List[str] = []
    decisive: Optional[str] = None

    # Candidate actions from signals (these may be overridden by contradictions).
    synthesis_candidate = (usefulness == "useful_now" and similarity_f >= 0.8)
    review_candidate = (objective_relation == "aligned")

    if has_hard or has_contra:
        recommended.append("contradiction_resolve")
        decisive = "contradiction_resolve"
        if has_hard:
            reasons.append("hard constraint violation")
        if has_contra:
            reasons.append("contradiction detected")
        # Include overridden candidates as recommended actions (example behavior).
        if review_candidate:
            recommended.append("review")
            reasons.append("objective alignment")
        if synthesis_candidate:
            recommended.append("synthesis")
            reasons.append("high similarity and usefulness")
    else:
        # Clean path: allow synthesis and include review as a secondary action when aligned.
        if synthesis_candidate:
            recommended.append("synthesis")
            decisive = "synthesis"
            reasons.append("high similarity and usefulness")
            if review_candidate:
                recommended.append("review")
                reasons.append("objective alignment")
            # Explicit clean-path reasons (golden trace expectations).
            reasons.append("no contradictions")
            reasons.append("no constraint violations")
        elif review_candidate:
            recommended.append("review")
            decisive = "review"
            reasons.append("objective alignment")
        else:
            recommended.append("review")
            decisive = None

    # Deduplicate deterministically while preserving order.
    seen = set()
    recommended_unique: List[str] = []
    for a in recommended:
        if a in seen:
            continue
        seen.add(a)
        recommended_unique.append(a)

    return {
        "recommended_actions": recommended_unique,
        "decisive_recommendation": decisive,
        "reasons": reasons,
        "constraints": rc,
        "contradictions": cd,
    }


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not (isinstance(v1, list) and isinstance(v2, list)):
        return 0.0
    if not v1 or not v2:
        return 0.0
    n = min(len(v1), len(v2))
    try:
        a = [float(v1[i]) for i in range(n)]
        b = [float(v2[i]) for i in range(n)]
    except Exception:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    cos = dot / (na * nb)
    return _clamp01(0.5 * (cos + 1.0))


def measure_coherence(*, vectors: list[list[float]]) -> float:
    """Compute coherence as average pairwise similarity."""
    if not isinstance(vectors, list):
        return 0.0
    vecs = [v for v in vectors if isinstance(v, list) and v]
    n = len(vecs)
    if n < 2:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += float(_cosine_similarity(vecs[i], vecs[j]))
            count += 1
    return float(total / float(count)) if count else 0.0


def combine_values(*, values: list[Any]) -> Any:
    """Deterministic synthesis of values.

    - All numeric scalars -> arithmetic mean
    - All strings -> join with '\n'
    - All dicts -> deterministic shallow merge by sorted keys (later items overwrite)
    - Otherwise -> list(values)
    """
    if not isinstance(values, list) or not values:
        return None

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        nums = [float(v) for v in values]
        return float(sum(nums) / float(len(nums)))

    if all(isinstance(v, str) for v in values):
        return "\n".join(values)

    if all(isinstance(v, dict) for v in values):
        merged: dict[str, Any] = {}
        # Deterministic: apply dicts in order; keys sorted on final output is caller concern.
        for d in values:
            for k in sorted(d.keys()):
                merged[k] = d[k]
        return merged

    return list(values)


def combine_vectors(*, vectors: list[list[float]]) -> list[float]:
    """Deterministic synthesis of conceptual vectors (elementwise mean)."""
    if not isinstance(vectors, list) or not vectors:
        return []
    vecs = [v for v in vectors if isinstance(v, list)]
    if not vecs:
        return []
    max_len = max((len(v) for v in vecs), default=0)
    if max_len <= 0:
        return []
    acc = [0.0] * max_len
    for v in vecs:
        for i in range(max_len):
            try:
                acc[i] += float(v[i]) if i < len(v) else 0.0
            except Exception:
                acc[i] += 0.0
    denom = float(len(vecs))
    return [float(x / denom) for x in acc]


def _vector_norm(v: list[float]) -> float:
    try:
        return float(math.sqrt(sum(float(x) * float(x) for x in (v or []))))
    except Exception:
        return 0.0


def evaluate_synthesis_gain(*, before: float, after: float) -> float:
    return float(after) - float(before)


def synthesize(*, records: list[Record], opportunity: SynthesisOpportunity) -> SynthesisResult:
    """Synthesize a new derived record from target records."""
    target_ids = list(opportunity.get('target_ids') or [])
    # Deterministic id: sorted target ids.
    tid_sorted = sorted([t for t in target_ids if isinstance(t, str) and t])
    targets = [r for r in (records or []) if isinstance(r, dict) and r.get('record_id') in tid_sorted]

    values = [t.get('value') for t in targets]
    vectors = [t.get('conceptual_vector') for t in targets if isinstance(t.get('conceptual_vector'), list)]
    vectors = [v for v in vectors if isinstance(v, list)]

    new_value = combine_values(values=values)
    new_vector = combine_vectors(vectors=vectors)

    before = measure_coherence(vectors=vectors)
    after = measure_coherence(vectors=[new_vector] + vectors)
    gain = evaluate_synthesis_gain(before=before, after=after)

    # Think-Deeper artifacts (additive): distributional summaries, counterfactuals, and a compact why vector.
    value_stats = summarize_numeric_distribution(values=values)
    norms = [_vector_norm(v) for v in vectors if isinstance(v, list)]
    norm_stats = summarize_numeric_distribution(values=norms)
    counterfactuals: list[dict[str, Any]] = []
    if len(tid_sorted) >= 2:
        for dropped in tid_sorted:
            kept_ids = [x for x in tid_sorted if x != dropped]
            kept_targets = [r for r in (records or []) if isinstance(r, dict) and r.get('record_id') in kept_ids]
            kept_values = [t.get('value') for t in kept_targets]
            kept_vectors = [t.get('conceptual_vector') for t in kept_targets if isinstance(t.get('conceptual_vector'), list)]
            kept_vectors = [v for v in kept_vectors if isinstance(v, list)]
            kept_new_vector = combine_vectors(vectors=kept_vectors)
            kept_before = measure_coherence(vectors=kept_vectors)
            kept_after = measure_coherence(vectors=[kept_new_vector] + kept_vectors)
            kept_gain = evaluate_synthesis_gain(before=kept_before, after=kept_after)
            counterfactuals.append(
                {
                    'type': 'drop_input',
                    'dropped_input': dropped,
                    'kept_inputs': kept_ids,
                    'coherence_before': float(kept_before),
                    'coherence_after': float(kept_after),
                    'coherence_gain': float(kept_gain),
                    'delta_gain_vs_full': float(kept_gain - float(gain)),
                }
            )
    # Deterministic ordering.
    counterfactuals = sorted(counterfactuals, key=lambda x: str(x.get('dropped_input') or ''))
    loo_gains = [float(cf.get('coherence_gain') or 0.0) for cf in counterfactuals]
    stability = {
        'leave_one_out_n': int(len(counterfactuals)),
        'leave_one_out_min_gain': float(min(loo_gains)) if loo_gains else None,
        'leave_one_out_max_gain': float(max(loo_gains)) if loo_gains else None,
        'sign_consistent_with_full': bool(all((g > 0.0) == (float(gain) > 0.0) for g in loo_gains)) if loo_gains else True,
    }

    why = {
        'version': 1,
        'inputs': list(tid_sorted),
        'value_stats': value_stats,
        'vector_norm_stats': norm_stats,
        'coherence': {
            'before': float(before),
            'after': float(after),
            'gain': float(gain),
            'stability': stability,
        },
    }

    return {
        'new_record_id': 'synth_' + '_'.join(tid_sorted),
        'value': new_value,
        'conceptual_vector': list(new_vector),
        'inputs': list(tid_sorted),
        'coherence_gain': float(gain),
        # Additive Think-Deeper artifacts (do not break existing callers).
        'why': why,
        'counterfactuals': counterfactuals,
    }


NextStep = Literal['measure', 'integrate', 're_evaluate']


def propose_next_steps(*, synthesis_result: SynthesisResult) -> list[NextStep]:
    """Propose next steps based on measurable coherence_gain."""
    try:
        gain = float(synthesis_result.get('coherence_gain') or 0.0)
    except Exception:
        gain = 0.0
    eps = 1e-12
    if gain > eps:
        return ['measure', 'integrate']
    if abs(gain) <= eps:
        return ['measure']
    return ['re_evaluate']
