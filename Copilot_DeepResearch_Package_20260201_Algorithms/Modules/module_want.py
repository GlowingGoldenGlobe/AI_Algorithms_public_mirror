"""module_want.py

Want Awareness / Want Information.

Goal: compute when the AI Brain "wants" next actions (information, error resolution,
synthesis) from measurements + comparisons + objectives.

This module is deterministic: no clocks unless a timestamp is explicitly provided.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


WantType = Literal[
    "want_information",
    "want_error_resolution",
    "want_synthesis",
]


class Objective(TypedDict, total=False):
    objective_id: str
    description: str
    target_state: Any
    priority: float


class MeasurementGap(TypedDict):
    target_id: str
    delta: float
    has_measurement: bool
    has_description: bool


class ErrorSummary(TypedDict):
    target_id: str
    error_count: int
    max_severity: float


class SynthesisOpportunity(TypedDict):
    target_ids: list[str]
    coherence_gain: float


class WantSignal(TypedDict):
    want_type: WantType
    strength: float
    reason: str
    targets: list[str]


class AwarenessPlan(TypedDict):
    plan_id: str
    wants: list[WantSignal]
    suggested_activities: list[str]


class WhyVectorItem(TypedDict, total=False):
    key: str
    value: Any
    unit: str
    source: str
    note: str


def _to_uncertainty(u: Any):
    """Best-effort conversion from dict/tuple-like into module_uncertainty.Uncertainty."""
    try:
        from module_uncertainty import Uncertainty

        if isinstance(u, Uncertainty):
            return u
        if isinstance(u, dict):
            value = float(u.get('value') or 0.0)
            variance = float(u.get('variance') or 0.0)
            prov = u.get('provenance')
            provenance = dict(prov) if isinstance(prov, dict) else {}
            if variance < 0.0:
                variance = 0.0
            return Uncertainty(value, variance, provenance)
    except Exception:
        pass
    return None


def compute_expected_value_of_information(
    *,
    current: Any,
    improved: Any,
    baseline: float,
    cost: float = 0.0,
    n_samples: int = 128,
) -> float:
    """Compute Expected Value of Information (EVoI) deterministically.

    Interprets "value" as expected reduction in absolute error to a baseline:
    EVoI = E[|X_current - b|] - E[|X_improved - b|] - cost

    Uses deterministic Monte Carlo sampling via module_uncertainty.sample_distribution.
    """
    try:
        from module_uncertainty import sample_distribution

        u0 = _to_uncertainty(current)
        u1 = _to_uncertainty(improved)
        if u0 is None or u1 is None:
            return 0.0

        n = int(n_samples)
        if n <= 0:
            return 0.0
        b = float(baseline)

        s0 = sample_distribution(u0, n)
        s1 = sample_distribution(u1, n)
        if not s0 or not s1:
            return 0.0

        l0 = sum(abs(float(x) - b) for x in s0) / float(len(s0))
        l1 = sum(abs(float(x) - b) for x in s1) / float(len(s1))
        return float(l0 - l1 - float(cost))
    except Exception:
        return 0.0


def estimate_information_cost(
    *,
    activity: str,
    target_ids: list[str],
    base_costs: Optional[dict[str, float]] = None,
) -> float:
    """Deterministic cost model for acquiring information.

    Default model is intentionally simple and caller-overridable.
    """
    defaults: dict[str, float] = {
        'retrieve': 0.15,
        'measure': 0.35,
        'search': 0.75,
        'synthesize': 0.60,
        'error_resolution': 0.80,
    }
    costs = dict(defaults)
    if isinstance(base_costs, dict):
        for k, v in base_costs.items():
            try:
                costs[str(k)] = float(v)
            except Exception:
                continue
    try:
        base = float(costs.get(str(activity), 0.35))
    except Exception:
        base = 0.35

    n = 1
    if isinstance(target_ids, list):
        n = max(1, sum(1 for t in target_ids if isinstance(t, str) and t))
    return float(base * float(n))


def compute_evoi_with_why(
    *,
    current: Any,
    improved: Any,
    baseline: float,
    activity: str = 'measure',
    target_ids: Optional[list[str]] = None,
    base_costs: Optional[dict[str, float]] = None,
    n_samples: int = 128,
) -> dict[str, Any]:
    """Compute EVoI and emit a deterministic "why vector".

    Returns a dict:
    - evoi
    - expected_loss_current
    - expected_loss_improved
    - cost
    - why_vector
    """
    try:
        from module_uncertainty import sample_distribution

        u0 = _to_uncertainty(current)
        u1 = _to_uncertainty(improved)
        if u0 is None or u1 is None:
            return {'evoi': 0.0, 'expected_loss_current': 0.0, 'expected_loss_improved': 0.0, 'cost': 0.0, 'why_vector': []}

        n = int(n_samples)
        if n <= 0:
            return {'evoi': 0.0, 'expected_loss_current': 0.0, 'expected_loss_improved': 0.0, 'cost': 0.0, 'why_vector': []}

        tids = list(target_ids) if isinstance(target_ids, list) else []
        cost = estimate_information_cost(activity=str(activity), target_ids=tids, base_costs=base_costs)
        b = float(baseline)

        s0 = sample_distribution(u0, n)
        s1 = sample_distribution(u1, n)
        if not s0 or not s1:
            return {'evoi': 0.0, 'expected_loss_current': 0.0, 'expected_loss_improved': 0.0, 'cost': float(cost), 'why_vector': []}

        l0 = sum(abs(float(x) - b) for x in s0) / float(len(s0))
        l1 = sum(abs(float(x) - b) for x in s1) / float(len(s1))
        evoi = float(l0 - l1 - float(cost))

        why: list[WhyVectorItem] = [
            {'key': 'activity', 'value': str(activity), 'source': 'cost_model'},
            {'key': 'target_ids', 'value': list(tids), 'source': 'caller'},
            {'key': 'baseline', 'value': float(b), 'unit': 'value', 'source': 'caller'},
            {'key': 'n_samples', 'value': int(n), 'source': 'deterministic_sampling'},
            {'key': 'current.variance', 'value': float(u0.variance), 'unit': 'value^2', 'source': 'uncertainty'},
            {'key': 'improved.variance', 'value': float(u1.variance), 'unit': 'value^2', 'source': 'uncertainty'},
            {'key': 'expected_loss_current', 'value': float(l0), 'unit': 'abs_error', 'source': 'monte_carlo'},
            {'key': 'expected_loss_improved', 'value': float(l1), 'unit': 'abs_error', 'source': 'monte_carlo'},
            {'key': 'cost', 'value': float(cost), 'unit': 'cost', 'source': 'cost_model'},
            {'key': 'evoi', 'value': float(evoi), 'unit': 'value', 'source': 'formula'},
            {'key': 'provenance_current', 'value': dict(u0.provenance) if isinstance(u0.provenance, dict) else {}, 'source': 'uncertainty'},
            {'key': 'provenance_improved', 'value': dict(u1.provenance) if isinstance(u1.provenance, dict) else {}, 'source': 'uncertainty'},
        ]

        return {
            'evoi': float(evoi),
            'expected_loss_current': float(l0),
            'expected_loss_improved': float(l1),
            'cost': float(cost),
            'why_vector': why,
        }
    except Exception:
        return {'evoi': 0.0, 'expected_loss_current': 0.0, 'expected_loss_improved': 0.0, 'cost': 0.0, 'why_vector': []}


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _normalize_objectives(objectives: Any) -> list[Objective]:
    out: list[Objective] = []
    if not isinstance(objectives, list):
        return out
    for o in objectives:
        if not isinstance(o, dict):
            continue
        oid = o.get("objective_id") or o.get("id")
        desc = o.get("description") or o.get("content")
        pr = o.get("priority")
        obj: Objective = {}
        if isinstance(oid, str) and oid:
            obj["objective_id"] = oid
        if isinstance(desc, str) and desc:
            obj["description"] = desc
        if pr is not None:
            try:
                obj["priority"] = float(pr)
            except Exception:
                pass
        # target_state is optional and currently not used.
        out.append(obj)
    return out


def compute_want_information(*, objectives: list[Objective], gaps: list[MeasurementGap]) -> list[WantSignal]:
    """Compute want_information signals from measurement gaps.

    Pure numeric logic:
    - missing measurement or description -> strong signal
    - larger delta -> stronger signal
    """
    _ = objectives
    out: list[WantSignal] = []
    for g in (gaps or []):
        if not isinstance(g, dict):
            continue
        tid = g.get('target_id')
        if not isinstance(tid, str) or not tid:
            continue
        try:
            delta = float(g.get('delta') or 0.0)
        except Exception:
            delta = 0.0
        has_m = bool(g.get('has_measurement'))
        has_d = bool(g.get('has_description'))
        if (not has_m) or (not has_d):
            strength = 1.0
            reason = 'missing measurement or description'
        else:
            strength = _clamp01(delta)
            reason = 'measurement/description delta'
        out.append({'want_type': 'want_information', 'strength': float(strength), 'reason': reason, 'targets': [tid]})
    return out


def compute_want_error_resolution(*, errors: list[ErrorSummary]) -> list[WantSignal]:
    """Compute want_error_resolution signals from error summaries.

    Pure numeric logic:
    - more errors -> stronger
    - higher max_severity -> stronger
    """
    out: list[WantSignal] = []
    for e in (errors or []):
        if not isinstance(e, dict):
            continue
        tid = e.get('target_id')
        if not isinstance(tid, str) or not tid:
            continue
        try:
            c = int(e.get('error_count') or 0)
        except Exception:
            c = 0
        try:
            s = float(e.get('max_severity') or 0.0)
        except Exception:
            s = 0.0
        # Normalize error_count into [0..1] with a small cap.
        c_norm = _clamp01(float(c) / 5.0)
        strength = _clamp01(0.5 * c_norm + 0.5 * _clamp01(s))
        if c > 0:
            out.append(
                {
                    'want_type': 'want_error_resolution',
                    'strength': float(strength),
                    'reason': 'errors present (count/severity)',
                    'targets': [tid],
                }
            )
    return out


def compute_want_synthesis(*, opportunities: list[SynthesisOpportunity]) -> list[WantSignal]:
    """Compute want_synthesis signals from synthesis opportunities."""
    out: list[WantSignal] = []
    for o in (opportunities or []):
        if not isinstance(o, dict):
            continue
        tids = o.get('target_ids')
        if not isinstance(tids, list) or not tids or not all(isinstance(t, str) and t for t in tids):
            continue
        try:
            c = float(o.get('coherence_gain') or 0.0)
        except Exception:
            c = 0.0
        strength = _clamp01(c)
        out.append(
            {
                'want_type': 'want_synthesis',
                'strength': float(strength),
                'reason': 'coherence gain opportunity',
                'targets': list(tids),
            }
        )
    return out


def aggregate_wants(
    *,
    info_wants: list[WantSignal],
    error_wants: list[WantSignal],
    synth_wants: list[WantSignal],
    plan_id: str,
    min_strength: float = 0.35,
    max_wants: int = 5,
) -> AwarenessPlan:
    """Merge and rank wants; map wants to suggested activities deterministically."""
    wants: list[WantSignal] = []
    for arr in (info_wants, error_wants, synth_wants):
        for w in (arr or []):
            if not isinstance(w, dict):
                continue
            try:
                if float(w.get('strength') or 0.0) < float(min_strength):
                    continue
            except Exception:
                continue
            wants.append(w)

    wants.sort(key=lambda w: (-float(w.get('strength') or 0.0), str(w.get('want_type') or '')))
    if max_wants > 0:
        wants = wants[: int(max_wants)]

    # Suggested mapping (pure mapping, deterministic).
    mapping: dict[str, list[str]] = {
        'want_information': ['retrieve', 'measure'],
        'want_error_resolution': ['error_resolution', 'measure'],
        'want_synthesis': ['synthesize', 'retrieve', 'measure'],
    }
    activities: list[str] = []
    seen: set[str] = set()
    for w in wants:
        wt = str(w.get('want_type') or '')
        for act in mapping.get(wt, []):
            if act not in seen:
                activities.append(act)
                seen.add(act)

    return {'plan_id': str(plan_id), 'wants': wants, 'suggested_activities': activities}


def compute_awareness_plan(
    *,
    objectives: list[Objective],
    gaps: list[MeasurementGap],
    errors: list[ErrorSummary],
    opportunities: list[SynthesisOpportunity],
    plan_id: str,
    min_strength: float = 0.35,
    max_wants: int = 5,
) -> AwarenessPlan:
    """High-level entrypoint: compute wants then aggregate."""
    info = compute_want_information(objectives=objectives, gaps=gaps)
    err = compute_want_error_resolution(errors=errors)
    syn = compute_want_synthesis(opportunities=opportunities)
    return aggregate_wants(
        info_wants=info,
        error_wants=err,
        synth_wants=syn,
        plan_id=plan_id,
        min_strength=min_strength,
        max_wants=max_wants,
    )


def compute_measurement_gap(*, data_id: str, record: dict[str, Any]) -> MeasurementGap:
    """Compute a deterministic "gap" between measurement and description.

    Interpretation used here:
    - "measurement" = conceptual_measurement or spatial_measurement exists
    - "description" = record.description has at least one claim or summary text
    - delta = normalized mismatch proxy based on unique_tokens vs claim_count
    """
    rs = record.get("relational_state") if isinstance(record, dict) else None
    cm = (rs or {}).get("conceptual_measurement") if isinstance(rs, dict) else None
    sm = (rs or {}).get("spatial_measurement") if isinstance(rs, dict) else None

    has_measurement = bool(isinstance(cm, dict) and cm) or bool(sm)

    desc = record.get("description") if isinstance(record, dict) else None
    claim_count = 0
    if isinstance(desc, dict):
        claims = desc.get("claims")
        if isinstance(claims, list):
            claim_count = sum(1 for c in claims if isinstance(c, dict))
        if claim_count == 0:
            # fallback: any non-empty description fields count as present
            has_description = any(bool(str(v).strip()) for v in desc.values() if isinstance(v, (str, int, float)))
        else:
            has_description = True
    else:
        has_description = False

    unique_tokens = 0
    if isinstance(cm, dict):
        try:
            unique_tokens = int(cm.get("unique_tokens") or 0)
        except Exception:
            unique_tokens = 0

    # Deterministic mismatch proxy in [0..1].
    denom = max(1, unique_tokens)
    delta = abs(float(unique_tokens) - float(claim_count)) / float(denom)
    if not has_measurement and not has_description:
        delta = 1.0
    elif has_measurement and has_description and unique_tokens == 0 and claim_count == 0:
        delta = 0.0

    return {
        "target_id": data_id,
        "delta": float(delta),
        "has_measurement": bool(has_measurement),
        "has_description": bool(has_description),
    }


def compute_error_summary(*, data_id: str, record: dict[str, Any]) -> ErrorSummary:
    """Summarize errors from decision_trace + constraint reports.

    This is error-driven, but remains compatible with existing contradiction reporting.
    """
    rs = record.get("relational_state") if isinstance(record, dict) else None
    dt = (rs or {}).get("decision_trace") if isinstance(rs, dict) else None
    cons = (dt or {}).get("constraints") if isinstance(dt, dict) else None

    violations = (cons or {}).get("violations") if isinstance(cons, dict) else None
    error_count = 0
    if isinstance(violations, list):
        error_count += sum(1 for v in violations if isinstance(v, dict))

    contras = (dt or {}).get("contradictions") if isinstance(dt, dict) else None
    if isinstance(contras, dict) and contras.get("has_contradiction"):
        error_count += 1

    max_severity = 0.0
    if isinstance(violations, list):
        for v in violations:
            if not isinstance(v, dict):
                continue
            try:
                max_severity = max(max_severity, float(v.get("severity") or 0.0))
            except Exception:
                continue
    if isinstance(contras, dict) and contras.get("has_contradiction"):
        max_severity = max(max_severity, 1.0)

    return {"target_id": data_id, "error_count": int(error_count), "max_severity": float(max_severity)}


def compute_synthesis_opportunity(*, data_id: str, record: dict[str, Any]) -> Optional[SynthesisOpportunity]:
    """Estimate synthesis opportunity using existing signals when present."""
    rs = record.get("relational_state") if isinstance(record, dict) else None
    dt = (rs or {}).get("decision_trace") if isinstance(rs, dict) else None
    sig = (dt or {}).get("signals") if isinstance(dt, dict) else None
    syn = None
    if isinstance(sig, dict):
        syn = sig.get("synthesis")
    try:
        syn_f = float(syn) if syn is not None else 0.0
    except Exception:
        syn_f = 0.0
    if syn_f <= 0.0:
        return None
    return {"target_ids": [data_id], "coherence_gain": _clamp01(syn_f)}


def awareness_plan_from_record(
    *,
    data_id: str,
    record: dict[str, Any],
    objectives: Any = None,
    plan_id: Optional[str] = None,
    min_strength: float = 0.35,
    max_wants: int = 5,
) -> AwarenessPlan:
    """Create an AwarenessPlan containing want signals + suggested activities."""
    pid = plan_id or f"want_{data_id}"
    obj = _normalize_objectives(objectives)
    gaps = [compute_measurement_gap(data_id=data_id, record=record)]
    errs = [compute_error_summary(data_id=data_id, record=record)]
    opps: list[SynthesisOpportunity] = []
    syn = compute_synthesis_opportunity(data_id=data_id, record=record)
    if syn is not None:
        opps.append(syn)
    return compute_awareness_plan(
        objectives=obj,
        gaps=gaps,
        errors=errs,
        opportunities=opps,
        plan_id=pid,
        min_strength=min_strength,
        max_wants=max_wants,
    )


# Backwards-compatible entrypoint: keep the old name used by scaffolding/tests.
def compute_want_signals(*, record: dict[str, Any], objectives: Any = None) -> list[dict[str, Any]]:
    data_id = str(record.get("id") or "unknown")
    plan = awareness_plan_from_record(data_id=data_id, record=record, objectives=objectives)
    wants = plan.get('wants') if isinstance(plan, dict) else []
    return [dict(w) for w in wants if isinstance(w, dict)]
