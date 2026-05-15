"""module_retrieval.py

Objective-driven deterministic retrieval engine.

Retrieval is computed as a numeric measurement and comparison problem:
each record receives component scores (measurement/target match, objective,
recurrence, conceptual similarity, constraint/context match), combined into a
single score and ranked deterministically.
"""

from __future__ import annotations

import math
import random
import hashlib
import os
import json
from typing import Any, Callable, Literal, Optional, TypedDict

from module_storage import resolve_path, safe_join


class Record(TypedDict, total=False):
    record_id: str
    value: Any
    context_id: str
    recurrence: float
    objective_links: dict[str, float]
    conceptual_vector: list[float]
    constraints: dict[str, Any]
    scene_summary_profile: dict[str, Any]
    reference_label_profile: dict[str, Any]


class RetrievalQuery(TypedDict, total=False):
    target_ids: list[str]
    objective_id: Optional[str]
    conceptual_vector: Optional[list[float]]
    required_context: Optional[str]
    reference_labels: Optional[list[str]]
    comparison_axes: Optional[list[str]]
    max_results: int
    diversity_k: int
    deterministic_mode: bool
    return_scores: bool


class RetrievalScore(TypedDict):
    record_id: str
    score: float
    components: dict[str, float]
    score_distribution: list[float]
    explain_vector: dict[str, float]


RETRIEVAL_COMPONENT_POLICY_DEFAULT_WEIGHTS: dict[str, float] = {
    'measurement': 0.25,
    'objective': 0.25,
    'recurrence': 0.15,
    'conceptual': 0.25,
    'constraint': 0.10,
    'categorized_context': 0.10,
    'scene_summary': 0.10,
    'reference_label': 0.10,
}


def stable_seed(obj: Any) -> int:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = str(obj)
    return int(hashlib.sha256(s.encode('utf-8')).hexdigest()[:16], 16)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Cosine similarity in [-1..1]."""
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
    return float(dot / (na * nb))


def map_cosine_to_unit(cos: float) -> float:
    return _clamp01(0.5 * (float(cos) + 1.0))


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def measure_similarity(v1: list[float], v2: list[float]) -> float:
    """Cosine similarity in [0..1] for non-negative vectors; 0 if invalid."""
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
    # Map from [-1..1] to [0..1] safely.
    return _clamp01(0.5 * (cos + 1.0))


def _get_uncertainty_penalty(record: Record) -> float:
    """Map record uncertainty into a [0..1] penalty.

    Supported forms:
    - record['uncertainty'] as float (already a penalty)
    - record['uncertainty'] as dict with 'variance' (penalty ~ stddev clamped)
    """
    u = record.get('uncertainty')  # type: ignore[typeddict-item]
    if isinstance(u, (int, float)) and not isinstance(u, bool):
        return _clamp01(float(u))
    if isinstance(u, dict):
        try:
            var = float(u.get('variance') or 0.0)
        except Exception:
            var = 0.0
        if var < 0.0:
            var = 0.0
        # Penalty is a bounded proxy of stddev.
        return _clamp01(math.sqrt(var))
    return 0.0


def compute_components_td(
    *,
    record: Record,
    query: RetrievalQuery,
    conceptual_similarity_fn: Optional[Callable[[list[float], list[float]], float]] = None,
    objective_relevance_fn: Optional[Callable[[Record, Optional[str]], float]] = None,
    constraint_evaluator: Optional[Callable[[Record, RetrievalQuery], float]] = None,
    recurrence_norm_fn: Optional[Callable[[float], float]] = None,
) -> dict[str, float]:
    """Compute Think Deeper component scores in [0..1]."""
    qv = query.get('conceptual_vector')
    rv = record.get('conceptual_vector')
    if isinstance(qv, list) and isinstance(rv, list) and qv and rv:
        fn = conceptual_similarity_fn or cosine_similarity
        s_c = map_cosine_to_unit(fn(qv, rv))
    else:
        s_c = 0.0

    fn_obj = objective_relevance_fn or measure_objective_relevance
    s_o = _clamp01(float(fn_obj(record, query.get('objective_id'))))

    rec = float(record.get('recurrence') or 0.0)
    s_r = _clamp01(float(recurrence_norm_fn(rec) if callable(recurrence_norm_fn) else rec))

    fn_con = constraint_evaluator or measure_constraint_satisfaction
    s_q = _clamp01(float(fn_con(record, query)))
    s_l = measure_reference_label_support(record, query)
    s_ctx = measure_categorized_context_support(record, query)

    u = _get_uncertainty_penalty(record)
    return {
        'conceptual': float(s_c),
        'objective': float(s_o),
        'recurrence': float(s_r),
        'constraint': float(s_q),
        'reference_label': float(s_l),
        'categorized_context': float(s_ctx),
        'uncertainty': float(u),
    }


def compute_score_td(*, components: dict[str, float], weights: Optional[dict[str, float]] = None) -> float:
    """Weighted score with uncertainty penalty."""
    w = weights or {
        'conceptual': 0.30,
        'objective': 0.25,
        'recurrence': 0.15,
        'constraint': 0.10,
        'reference_label': 0.10,
        'categorized_context': 0.10,
        'uncertainty': 0.20,
    }
    return float(
        float(w.get('conceptual', 0.0)) * float(components.get('conceptual', 0.0))
        + float(w.get('objective', 0.0)) * float(components.get('objective', 0.0))
        + float(w.get('recurrence', 0.0)) * float(components.get('recurrence', 0.0))
        + float(w.get('constraint', 0.0)) * float(components.get('constraint', 0.0))
        + float(w.get('reference_label', 0.0)) * float(components.get('reference_label', 0.0))
        + float(w.get('categorized_context', 0.0)) * float(components.get('categorized_context', 0.0))
        - float(w.get('uncertainty', 0.0)) * float(components.get('uncertainty', 0.0))
    )


def _score_distribution_for_record(
    *,
    base_score: float,
    record: Record,
    query: RetrievalQuery,
    n_samples: int = 32,
) -> list[float]:
    """Deterministic sampling around base score when uncertainty is present."""
    n = int(n_samples)
    if n <= 0:
        return [float(base_score)]

    # Prefer a variance signal if present.
    var = 0.0
    u = record.get('uncertainty')  # type: ignore[typeddict-item]
    if isinstance(u, dict):
        try:
            var = float(u.get('variance') or 0.0)
        except Exception:
            var = 0.0
    elif isinstance(u, (int, float)) and not isinstance(u, bool):
        # Interpret a [0..1] penalty as a variance proxy.
        var = float(max(0.0, float(u))) ** 2

    if var <= 0.0:
        return [float(base_score)]

    prov = {'record_id': str(record.get('record_id') or ''), 'query': query}
    try:
        from module_uncertainty import Uncertainty, sample_distribution

        uu = Uncertainty(float(base_score), float(var), prov)
        # sample_distribution is already deterministic; provenance binds to query.
        return [float(x) for x in sample_distribution(uu, n)]
    except Exception:
        # Fallback deterministic RNG.
        seed_obj = {'record_id': str(record.get('record_id') or ''), 'query': query, 'var': var}
        rng = random.Random(stable_seed(seed_obj)) if bool(query.get('deterministic_mode')) else random.Random()
        sigma = math.sqrt(max(0.0, float(var)))
        return [float(rng.gauss(float(base_score), sigma)) for _ in range(n)]


def _explain_vector(*, components: dict[str, float], weights: dict[str, float]) -> dict[str, float]:
    return {
        'conceptual': float(weights.get('conceptual', 0.0)) * float(components.get('conceptual', 0.0)),
        'objective': float(weights.get('objective', 0.0)) * float(components.get('objective', 0.0)),
        'recurrence': float(weights.get('recurrence', 0.0)) * float(components.get('recurrence', 0.0)),
        'constraint': float(weights.get('constraint', 0.0)) * float(components.get('constraint', 0.0)),
        'reference_label': float(weights.get('reference_label', 0.0)) * float(components.get('reference_label', 0.0)),
        'categorized_context': float(weights.get('categorized_context', 0.0)) * float(components.get('categorized_context', 0.0)),
        'uncertainty_penalty': -float(weights.get('uncertainty', 0.0)) * float(components.get('uncertainty', 0.0)),
    }


def _cluster_key_for_record(record: Record) -> str:
    vec = record.get('conceptual_vector')
    if not isinstance(vec, list) or not vec:
        return 'cluster_none'
    try:
        head = [float(x) for x in vec[:3]]
    except Exception:
        head = []
    payload = {'head': head}
    return stable_hash(payload)[:8]


def apply_diversity_td(*, scored: list[RetrievalScore], store: list[Record], diversity_k: int) -> list[RetrievalScore]:
    """Deterministic diversity: round-robin across simple vector-hash clusters."""
    k = int(diversity_k)
    if k <= 1:
        return scored

    by_id: dict[str, Record] = {str(r.get('record_id') or ''): r for r in (store or []) if isinstance(r, dict)}
    clusters: dict[str, list[RetrievalScore]] = {}
    for s in scored:
        rid = str(s.get('record_id') or '')
        r = by_id.get(rid)
        ckey = _cluster_key_for_record(r) if isinstance(r, dict) else 'cluster_none'
        clusters.setdefault(ckey, []).append(s)

    keys = sorted(clusters.keys())
    out: list[RetrievalScore] = []
    idx = 0
    while True:
        progressed = False
        for _ in range(len(keys)):
            ckey = keys[idx % len(keys)]
            idx += 1
            bucket = clusters.get(ckey) or []
            if bucket:
                out.append(bucket.pop(0))
                progressed = True
            if len(out) >= len(scored):
                return out
        if not progressed:
            break
    return out


def rank_records_td(
    *,
    store: list[Record],
    query: RetrievalQuery,
    weights: Optional[dict[str, float]] = None,
    n_samples: int = 32,
) -> list[RetrievalScore]:
    """Think Deeper retrieval: returns scored rows (not raw records)."""
    w = weights or {
        'conceptual': 0.30,
        'objective': 0.25,
        'recurrence': 0.15,
        'constraint': 0.10,
        'reference_label': 0.10,
        'categorized_context': 0.10,
        'uncertainty': 0.20,
    }

    rows: list[RetrievalScore] = []
    for rec in store or []:
        if not isinstance(rec, dict):
            continue
        comps = compute_components_td(record=rec, query=query)
        base = compute_score_td(components=comps, weights=w)
        dist = _score_distribution_for_record(base_score=base, record=rec, query=query, n_samples=n_samples)
        mean_score = sum(dist) / float(len(dist)) if dist else float(base)
        rows.append(
            {
                'record_id': str(rec.get('record_id') or ''),
                'score': float(mean_score),
                'components': dict(comps),
                'score_distribution': list(dist),
                'explain_vector': _explain_vector(components=comps, weights=w),
            }
        )

    rows.sort(key=lambda s: (-float(s.get('score') or 0.0), str(s.get('record_id') or '')))

    div_k = query.get('diversity_k')
    if div_k is not None:
        try:
            rows = apply_diversity_td(scored=rows, store=store, diversity_k=int(div_k))
        except Exception:
            pass
    return rows


def measure_objective_relevance(record: Record, objective_id: Optional[str]) -> float:
    if not objective_id:
        return 0.0
    links = record.get('objective_links')
    if not isinstance(links, dict):
        return 0.0
    v = links.get(objective_id)
    try:
        return _clamp01(float(v) if v is not None else 0.0)
    except Exception:
        return 0.0


def measure_recurrence(record: Record) -> float:
    try:
        return _clamp01(float(record.get('recurrence') or 0.0))
    except Exception:
        return 0.0


def measure_constraint_satisfaction(record: Record, query: RetrievalQuery) -> float:
    """Context match score in [0..1].

    If required_context is None: returns 0 (no constraint contribution).
    If provided: returns 1 when record.context_id matches, else 0.
    """
    req = query.get('required_context')
    if req is None:
        return 0.0
    if not isinstance(req, str) or not req:
        return 0.0
    ctx = record.get('context_id')
    return 1.0 if (isinstance(ctx, str) and ctx == req) else 0.0


def _normalize_reference_terms(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = [item for item in value if isinstance(item, str)]
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = " ".join(str(item).strip().lower().replace('_', ' ').replace('-', ' ').split())
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _merge_reference_terms(target: list[str], *values: Any) -> list[str]:
    seen = set(target)
    for value in values:
        for term in _normalize_reference_terms(value):
            if term in seen:
                continue
            seen.add(term)
            target.append(term)
    return target


def _normalize_reference_mapping_values(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []

    normalized: list[str] = []
    for key in sorted(value.keys()):
        _merge_reference_terms(normalized, value.get(key))
    return normalized


def _normalize_structured_comparison_axes(value: Any) -> list[str]:
    if isinstance(value, dict):
        items = [value]
    elif isinstance(value, list):
        normalized = _normalize_reference_terms([item for item in value if isinstance(item, str)])
        items = [item for item in value if isinstance(item, dict)]
    else:
        return _normalize_reference_terms(value)

    if not isinstance(value, list):
        normalized = []
    for item in items:
        _merge_reference_terms(
            normalized,
            item.get('axis'),
            item.get('value'),
            item.get('label'),
            item.get('name'),
        )
    return normalized


def _categorized_context_summary_from_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    direct = value.get('categorized_context_summary')
    if isinstance(direct, dict):
        return direct

    rs = value.get('relational_state') if isinstance(value.get('relational_state'), dict) else None
    derived = rs.get('derived') if isinstance(rs, dict) and isinstance(rs.get('derived'), dict) else None
    nested = derived.get('categorized_context_summary') if isinstance(derived, dict) else None
    if isinstance(nested, dict):
        return nested

    nested_value = value.get('value')
    if isinstance(nested_value, dict) and nested_value is not value:
        return _categorized_context_summary_from_value(nested_value)
    return {}


def _scene_relation_families_from_value(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    rs = value.get('relational_state') if isinstance(value.get('relational_state'), dict) else None
    if not isinstance(rs, dict):
        return []

    families: list[str] = []
    seen: set[str] = set()

    relations = rs.get('relations')
    if isinstance(relations, list):
        for row in relations:
            if not isinstance(row, dict) or row.get('source') != '3d_scene_summary':
                continue
            pred = row.get('pred') if isinstance(row.get('pred'), str) else None
            for term in _normalize_reference_terms(pred):
                if term not in seen:
                    seen.add(term)
                    families.append(term)

    constraints = rs.get('constraints')
    if isinstance(constraints, list):
        for row in constraints:
            if not isinstance(row, dict) or row.get('source') != '3d_scene_summary':
                continue
            constraint_type = row.get('type') if isinstance(row.get('type'), str) else None
            for term in _normalize_reference_terms(constraint_type):
                if term not in seen:
                    seen.add(term)
                    families.append(term)

    return families


def _reference_label_profile_from_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    labels: list[str] = []
    _merge_reference_terms(labels, value.get('label'), value.get('labels'))
    _merge_reference_terms(labels, _normalize_reference_mapping_values(value.get('labels')))

    object_hints = value.get('object_hints')
    if isinstance(object_hints, list):
        for item in object_hints:
            if not isinstance(item, dict):
                continue
            _merge_reference_terms(labels, item.get('label'))

    aliases: list[str] = []
    _merge_reference_terms(aliases, value.get('aliases'))

    comparison_axes: list[str] = []
    _merge_reference_terms(comparison_axes, _normalize_structured_comparison_axes(value.get('comparison_axes')))
    for extra_axes in ('comparison_focus', 'topics', 'scope_tags', 'tags'):
        _merge_reference_terms(comparison_axes, value.get(extra_axes))

    categorized_summary = _categorized_context_summary_from_value(value)
    if categorized_summary:
        _merge_reference_terms(labels, categorized_summary.get('labels'))
        _merge_reference_terms(aliases, categorized_summary.get('aliases'))
        _merge_reference_terms(comparison_axes, categorized_summary.get('comparison_axes'))

    if not (labels or aliases or comparison_axes):
        return {}

    return {
        'id': str(value.get('id') or ''),
        'labels': labels,
        'aliases': aliases,
        'comparison_axes': comparison_axes,
    }


def build_categorized_context_profile(record_or_value: Any) -> dict[str, Any]:
    record = record_or_value if isinstance(record_or_value, dict) else {}
    value = record.get('value') if isinstance(record.get('value'), dict) else record_or_value

    reference_profile = record.get('reference_label_profile') if isinstance(record.get('reference_label_profile'), dict) else None
    if not isinstance(reference_profile, dict) or not reference_profile:
        reference_profile = _reference_label_profile_from_value(value)

    scene_profile = record.get('scene_summary_profile') if isinstance(record.get('scene_summary_profile'), dict) else None
    if not isinstance(scene_profile, dict) or not scene_profile:
        scene_profile = _scene_summary_profile_from_value(value)

    relation_families = _scene_relation_families_from_value(value)
    categorized_summary = _categorized_context_summary_from_value(record) or _categorized_context_summary_from_value(value)
    source_kinds: list[str] = []
    if reference_profile:
        source_kinds.append('reference_label_profile')
    if scene_profile:
        source_kinds.append('scene_summary_profile')
    if categorized_summary:
        source_kinds.append('categorized_context_summary')

    return {
        'id': str((reference_profile or {}).get('id') or record.get('record_id') or ''),
        'labels': list((reference_profile or {}).get('labels') or []),
        'aliases': list((reference_profile or {}).get('aliases') or []),
        'comparison_axes': list((reference_profile or {}).get('comparison_axes') or []),
        'relation_families': relation_families,
        'source_kinds': source_kinds,
    }


def summarize_categorized_context_join_quality(
    categorized_summary: Any,
    reference_profile: Any,
) -> dict[str, Any]:
    semantic_summary = categorized_summary if isinstance(categorized_summary, dict) else {}
    reference = reference_profile if isinstance(reference_profile, dict) else {}

    semantic_labels = set(_normalize_reference_terms(semantic_summary.get('labels')))
    semantic_aliases = set(_normalize_reference_terms(semantic_summary.get('aliases')))
    semantic_axes = set(_normalize_reference_terms(semantic_summary.get('comparison_axes')))
    reference_labels = set(_normalize_reference_terms(reference.get('labels')))
    reference_aliases = set(_normalize_reference_terms(reference.get('aliases')))
    reference_axes = set(_normalize_reference_terms(reference.get('comparison_axes')))

    reference_present = bool(reference_labels or reference_aliases or reference_axes)
    support_level = str(semantic_summary.get('support_level') or semantic_summary.get('level') or 'missing').lower()
    relation_families = set(_normalize_reference_terms(semantic_summary.get('relation_families')))
    bridge_sources = set(_normalize_reference_terms(semantic_summary.get('bridge_sources')))
    semantic_present = bool(
        semantic_labels
        or semantic_aliases
        or semantic_axes
        or relation_families
        or bridge_sources
        or bool(semantic_summary.get('scene_summary_present'))
        or support_level != 'missing'
    )

    matched_reference_labels = sorted((semantic_labels | semantic_aliases).intersection(reference_labels))
    matched_reference_aliases = sorted((semantic_labels | semantic_aliases).intersection(reference_aliases))
    matched_reference_axes = sorted(semantic_axes.intersection(reference_axes))
    matched_category_count = sum(
        1 for values in (matched_reference_labels, matched_reference_aliases, matched_reference_axes) if values
    )
    matched_term_count = (
        len(matched_reference_labels)
        + len(matched_reference_aliases)
        + len(matched_reference_axes)
    )

    if reference_present and support_level == 'strong':
        join_status = 'aligned'
    elif reference_present and support_level == 'weak':
        join_status = 'reference_backed_semantic_weak'
    elif reference_present:
        join_status = 'reference_only'
    elif support_level != 'missing' or semantic_present:
        join_status = 'semantic_only'
    else:
        join_status = 'missing'

    if join_status == 'aligned':
        join_quality = 'strong'
    elif join_status in {'reference_backed_semantic_weak', 'semantic_only'}:
        join_quality = 'partial'
    elif join_status == 'reference_only':
        join_quality = 'weak'
    else:
        join_quality = 'missing'

    if semantic_present:
        persistence_status = 'persisted'
    elif reference_present:
        persistence_status = 'reference_only'
    else:
        persistence_status = 'missing'

    if join_quality == 'strong':
        follow_through_status = 'ready'
    elif join_quality in {'partial', 'weak'}:
        follow_through_status = 'monitor'
    else:
        follow_through_status = 'missing'

    gap_reasons: list[str] = []
    if not semantic_present:
        gap_reasons.append('categorized_context_not_persisted')
    if reference_present and matched_term_count <= 0 and join_status in {'reference_only', 'missing'}:
        gap_reasons.append('reference_join_overlap_missing')
    if join_status == 'reference_backed_semantic_weak':
        gap_reasons.append('categorized_context_support_weak')

    return {
        'join_status': join_status,
        'join_quality': join_quality,
        'persistence_status': persistence_status,
        'follow_through_status': follow_through_status,
        'reference_profile_present': reference_present,
        'matched_reference_labels': matched_reference_labels,
        'matched_reference_aliases': matched_reference_aliases,
        'matched_reference_comparison_axes': matched_reference_axes,
        'matched_reference_category_count': matched_category_count,
        'matched_reference_term_count': matched_term_count,
        'gap_reasons': gap_reasons,
    }


def summarize_categorized_context_coverage(record: Record, query: RetrievalQuery) -> dict[str, Any]:
    profile = build_categorized_context_profile(record)
    query_labels = _normalize_reference_terms(query.get('reference_labels'))
    query_axes = _normalize_reference_terms(query.get('comparison_axes'))

    label_set = set(_normalize_reference_terms(profile.get('labels')))
    alias_set = set(_normalize_reference_terms(profile.get('aliases')))
    axis_set = set(_normalize_reference_terms(profile.get('comparison_axes')))
    relation_family_set = set(_normalize_reference_terms(profile.get('relation_families')))

    used_labels = sorted(label_set.intersection(query_labels))
    used_aliases = sorted(alias_set.intersection(query_labels))
    used_axes = sorted(axis_set.intersection(query_axes))

    reference_support = measure_reference_label_support(record, query)
    scene_support = measure_scene_summary_support(
        record,
        query,
        measurement=_measurement_target_match(record, query),
        objective=measure_objective_relevance(record, query.get('objective_id')),
        conceptual=(measure_similarity(record.get('conceptual_vector'), query.get('conceptual_vector')) if (isinstance(record.get('conceptual_vector'), list) and isinstance(query.get('conceptual_vector'), list)) else 0.0),
        constraint=measure_constraint_satisfaction(record, query),
    )
    used_relation_families = sorted(relation_family_set) if scene_support > 0.0 else []

    used_categories = sum(
        1 for values in (used_labels, used_aliases, used_axes, used_relation_families) if values
    )
    available_categories = sum(
        1 for values in (label_set, alias_set, axis_set, relation_family_set) if values
    )

    if used_categories >= 2 or (reference_support > 0.75 and used_categories >= 1) or scene_support > 0.75:
        level = 'strong'
    else:
        level = 'weak'

    return {
        'level': level,
        'available': {
            'labels': sorted(label_set),
            'aliases': sorted(alias_set),
            'comparison_axes': sorted(axis_set),
            'relation_families': sorted(relation_family_set),
        },
        'used': {
            'labels': used_labels,
            'aliases': used_aliases,
            'comparison_axes': used_axes,
            'relation_families': used_relation_families,
        },
        'counts': {
            'available_categories': available_categories,
            'used_categories': used_categories,
        },
        'support': {
            'reference_label': float(reference_support),
            'scene_summary': float(scene_support),
        },
        'source_kinds': list(profile.get('source_kinds') or []),
    }


def summarize_reference_use(record: Record, query: RetrievalQuery) -> dict[str, Any]:
    coverage = summarize_categorized_context_coverage(record, query)
    used = coverage.get('used') if isinstance(coverage.get('used'), dict) else {}
    counts = coverage.get('counts') if isinstance(coverage.get('counts'), dict) else {}

    label_match_count = len([item for item in (used.get('labels') or []) if isinstance(item, str)])
    alias_match_count = len([item for item in (used.get('aliases') or []) if isinstance(item, str)])
    comparison_axis_match_count = len(
        [item for item in (used.get('comparison_axes') or []) if isinstance(item, str)]
    )
    relation_family_match_count = len(
        [item for item in (used.get('relation_families') or []) if isinstance(item, str)]
    )
    used_category_count = 0
    for values in (
        used.get('labels'),
        used.get('aliases'),
        used.get('comparison_axes'),
        used.get('relation_families'),
    ):
        if isinstance(values, list) and any(isinstance(item, str) for item in values):
            used_category_count += 1

    reference_use_score = float(measure_reference_label_support(record, query))
    available_category_count = 0
    try:
        available_category_count = int(counts.get('available_categories') or 0)
    except Exception:
        available_category_count = 0

    if reference_use_score >= 0.75 and used_category_count >= 2:
        utilization_state = 'strong'
        summary = 'reference-use evidence strongly overlaps retained categorized context'
    elif reference_use_score > 0.0 or used_category_count > 0:
        utilization_state = 'partial'
        summary = 'reference-use evidence partially overlaps retained categorized context'
    elif query.get('reference_labels') or query.get('comparison_axes'):
        utilization_state = 'weak'
        summary = 'reference-use evidence is requested but not supported by retained categorized context'
    else:
        utilization_state = 'missing'
        summary = 'reference-use evidence was not requested for the current retained context'

    return {
        'utilization_state': utilization_state,
        'reference_use_score': reference_use_score,
        'reference_use_breakdown': {
            'label_match_count': label_match_count,
            'alias_match_count': alias_match_count,
            'comparison_axis_match_count': comparison_axis_match_count,
        },
        'relation_family_match_count': relation_family_match_count,
        'used_category_count': used_category_count,
        'available_category_count': available_category_count,
        'coverage_level': str(coverage.get('level') or 'missing'),
        'support': dict(coverage.get('support') or {}),
        'source_kinds': list(coverage.get('source_kinds') or []),
        'summary': summary,
    }


def measure_categorized_context_support(record: Record, query: RetrievalQuery) -> float:
    summary = summarize_categorized_context_coverage(record, query)
    counts = summary.get('counts') if isinstance(summary.get('counts'), dict) else {}
    try:
        available_categories = int(counts.get('available_categories') or 0)
    except Exception:
        available_categories = 0
    try:
        used_categories = int(counts.get('used_categories') or 0)
    except Exception:
        used_categories = 0
    if available_categories <= 0 or used_categories <= 0:
        return 0.0

    coverage_ratio = min(float(used_categories) / float(available_categories), 1.0)
    level = str(summary.get('level') or 'missing').lower()
    if level == 'strong':
        level_factor = 1.0
    elif level == 'weak':
        level_factor = 0.5
    else:
        level_factor = 0.0
    return _clamp01(float(coverage_ratio) * float(level_factor))


def measure_reference_label_support(record: Record, query: RetrievalQuery) -> float:
    profile = record.get('reference_label_profile')
    if not isinstance(profile, dict) or not profile:
        profile = _reference_label_profile_from_value(record.get('value'))
    if not isinstance(profile, dict) or not profile:
        return 0.0

    query_labels = _normalize_reference_terms(query.get('reference_labels'))
    query_axes = _normalize_reference_terms(query.get('comparison_axes'))
    if not query_labels and not query_axes:
        return 0.0

    active_scores: list[float] = []
    if query_labels:
        profile_labels = set(_normalize_reference_terms(profile.get('labels')) + _normalize_reference_terms(profile.get('aliases')))
        active_scores.append((len(profile_labels.intersection(query_labels)) / float(len(query_labels))) if profile_labels else 0.0)
    if query_axes:
        profile_axes = set(_normalize_reference_terms(profile.get('comparison_axes')))
        active_scores.append((len(profile_axes.intersection(query_axes)) / float(len(query_axes))) if profile_axes else 0.0)
    return _clamp01((sum(active_scores) / float(len(active_scores))) if active_scores else 0.0)


def _scene_summary_profile_from_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    rs = value.get('relational_state') if isinstance(value.get('relational_state'), dict) else None
    if not isinstance(rs, dict):
        return {}

    def _rows(key: str) -> list[dict[str, Any]]:
        items = rs.get(key)
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict) and item.get('source') == '3d_scene_summary']

    entities = _rows('entities')
    relations = _rows('relations')
    constraints = _rows('constraints')
    validation_rows = [
        row for row in constraints
        if row.get('type') == 'scene_validation'
    ]
    if not (entities or relations or constraints):
        return {}

    validation_quality = 0.0
    if validation_rows:
        scored = []
        for row in validation_rows:
            status = str(row.get('status') or '').lower()
            if status == 'pass':
                scored.append(1.0)
            elif status == 'warn':
                scored.append(0.5)
            else:
                scored.append(0.0)
        validation_quality = sum(scored) / float(len(scored)) if scored else 0.0

    evidence_strength = _clamp01(
        0.35 * min(len(entities), 5) / 5.0
        + 0.20 * min(len(relations), 3) / 3.0
        + 0.25 * min(len(constraints), 4) / 4.0
        + 0.20 * validation_quality
    )

    check_names = []
    for row in validation_rows:
        args = row.get('args') if isinstance(row.get('args'), dict) else {}
        check_name = args.get('check_name') if isinstance(args.get('check_name'), str) else None
        if check_name:
            check_names.append(check_name)
    check_names = sorted(set(check_names))

    return {
        'entity_count': len(entities),
        'relation_count': len(relations),
        'constraint_count': len(constraints),
        'validation_count': len(validation_rows),
        'validation_quality': float(validation_quality),
        'evidence_strength': float(evidence_strength),
        'check_names': check_names,
        'relation_families': _scene_relation_families_from_value(value),
    }


def measure_scene_summary_support(
    record: Record,
    query: RetrievalQuery,
    *,
    measurement: float,
    objective: float,
    conceptual: float,
    constraint: float,
) -> float:
    profile = record.get('scene_summary_profile')
    if not isinstance(profile, dict) or not profile:
        profile = _scene_summary_profile_from_value(record.get('value'))
    if not isinstance(profile, dict) or not profile:
        return 0.0

    try:
        evidence_strength = float(profile.get('evidence_strength') or 0.0)
    except Exception:
        evidence_strength = 0.0
    try:
        validation_quality = float(profile.get('validation_quality') or 0.0)
    except Exception:
        validation_quality = 0.0

    query_strength = max(float(measurement), float(objective), float(conceptual), float(constraint))
    if query_strength <= 0.0:
        return 0.0

    support = (0.7 * evidence_strength + 0.3 * validation_quality) * query_strength
    return _clamp01(float(support))


def _measurement_target_match(record: Record, query: RetrievalQuery) -> float:
    targets = query.get('target_ids')
    if not isinstance(targets, list) or not targets:
        return 0.0
    rid = record.get('record_id')
    if not isinstance(rid, str) or not rid:
        return 0.0
    return 1.0 if rid in targets else 0.0


def compute_retrieval_score(record: Record, query: RetrievalQuery) -> RetrievalScore:
    """Compute a deterministic weighted sum of numeric components."""
    rid = str(record.get('record_id') or '')

    measurement = _measurement_target_match(record, query)

    objective = measure_objective_relevance(record, query.get('objective_id'))

    recurrence = measure_recurrence(record)

    qv = query.get('conceptual_vector')
    rv = record.get('conceptual_vector')
    conceptual = measure_similarity(rv, qv) if (isinstance(rv, list) and isinstance(qv, list)) else 0.0

    constraint = measure_constraint_satisfaction(record, query)
    reference_label = measure_reference_label_support(record, query)
    categorized_context = measure_categorized_context_support(record, query)
    scene_summary = measure_scene_summary_support(
        record,
        query,
        measurement=measurement,
        objective=objective,
        conceptual=conceptual,
        constraint=constraint,
    )

    # Deterministic weights (sum to 1.0).
    w = {
        'measurement': 0.25,
        'objective': 0.25,
        'recurrence': 0.15,
        'conceptual': 0.25,
        'constraint': 0.10,
    }
    score = (
        w['measurement'] * measurement
        + w['objective'] * objective
        + w['recurrence'] * recurrence
        + w['conceptual'] * conceptual
        + w['constraint'] * constraint
    )
    if reference_label > 0.0:
        score = _clamp01(float(score) + (0.10 * float(reference_label)))
    if categorized_context > 0.0:
        score = _clamp01(float(score) + (0.10 * float(categorized_context)))
    if scene_summary > 0.0:
        score = _clamp01(float(score) + (0.10 * float(scene_summary)))

    components = {
        'measurement': float(measurement),
        'objective': float(objective),
        'recurrence': float(recurrence),
        'conceptual': float(conceptual),
        'constraint': float(constraint),
    }
    if reference_label > 0.0:
        components['reference_label'] = float(reference_label)
    if categorized_context > 0.0:
        components['categorized_context'] = float(categorized_context)
    if scene_summary > 0.0:
        components['scene_summary'] = float(scene_summary)

    return {
        'record_id': rid,
        'score': float(score),
        'components': components,
    }


def compute_retrieval_component_score(
    components: dict[str, Any],
    weights: Optional[dict[str, float]] = None,
) -> float:
    if not isinstance(components, dict) or not components:
        return 0.0

    if not isinstance(weights, dict):
        values = []
        for value in components.values():
            try:
                values.append(float(value))
            except Exception:
                continue
        return _clamp01((sum(values) / float(len(values))) if values else 0.0)

    comp_score = 0.0
    total = 0.0
    for key, value in components.items():
        try:
            component_value = float(value)
        except Exception:
            continue

        raw_weight = weights.get(str(key))
        if raw_weight is None:
            raw_weight = RETRIEVAL_COMPONENT_POLICY_DEFAULT_WEIGHTS.get(str(key))
        try:
            weight_value = float(raw_weight)
        except Exception:
            continue
        if weight_value == 0.0:
            continue

        comp_score += (weight_value * component_value)
        total += abs(weight_value)

    if total <= 0.0:
        return 0.0
    return _clamp01(float(comp_score) / float(total))


def rank_records(scores: list[RetrievalScore]) -> list[RetrievalScore]:
    """Sort by score desc, then record_id asc (deterministic tie-break)."""
    return sorted(scores, key=lambda s: (-float(s.get('score') or 0.0), str(s.get('record_id') or '')))


def retrieve(store: list[Record], query: RetrievalQuery) -> list[Record]:
    """Compute scores for all records, rank, and return top N."""
    max_results = query.get('max_results')
    try:
        limit = int(max_results) if max_results is not None else 10
    except Exception:
        limit = 10
    if limit <= 0:
        limit = 10

    # Backward compatible default: keep existing retrieval scoring logic stable.
    scored: list[tuple[RetrievalScore, Record]] = []
    for r in store or []:
        if not isinstance(r, dict):
            continue
        rs = compute_retrieval_score(r, query)
        scored.append((rs, r))
    ranked = rank_records([s for s, _ in scored])
    # Build lookup for stable selection.
    by_id: dict[str, Record] = {str(r.get('record_id') or ''): r for _, r in scored if isinstance(r, dict)}
    out: list[Record] = []
    for s in ranked:
        rid = s.get('record_id')
        if isinstance(rid, str) and rid in by_id:
            out.append(by_id[rid])
        if len(out) >= limit:
            break
    return out


def retrieve_with_scores(*, store: list[Record], query: RetrievalQuery, weights: Optional[dict[str, float]] = None) -> list[RetrievalScore]:
    """Return scored rows (Think Deeper mode)."""
    max_results = query.get('max_results')
    try:
        limit = int(max_results) if max_results is not None else 10
    except Exception:
        limit = 10
    if limit <= 0:
        limit = 10

    rows = rank_records_td(store=store, query=query, weights=weights, n_samples=32)
    return rows[:limit]


def _record_from_semantic_json(path: str) -> Optional[Record]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            rec = json.load(f)
    except Exception:
        return None
    if not isinstance(rec, dict):
        return None
    rid = rec.get('id')
    if not isinstance(rid, str) or not rid:
        return None
    rs = rec.get('relational_state') if isinstance(rec.get('relational_state'), dict) else {}
    cm = (rs or {}).get('conceptual_measurement') if isinstance(rs, dict) else None
    rep = rec.get('repetition_profile') if isinstance(rec.get('repetition_profile'), dict) else None

    # Recurrence: prefer stability_score, else normalized occurrence_count.
    stability = 0.0
    if isinstance(rep, dict):
        try:
            stability = float(rep.get('stability_score') or 0.0)
        except Exception:
            stability = 0.0
    if stability <= 0.0:
        try:
            occ = int(rec.get('occurrence_count') or 0)
        except Exception:
            occ = 0
        stability = _clamp01(float(occ) / 5.0)

    # Objective links map.
    links_map: dict[str, float] = {}
    links = (rs or {}).get('objective_links') if isinstance(rs, dict) else None
    if isinstance(links, list):
        for l in links:
            if not isinstance(l, dict):
                continue
            oid = l.get('objective_id')
            rel = l.get('relevance')
            if isinstance(oid, str) and oid:
                try:
                    links_map[oid] = _clamp01(float(rel) if rel is not None else 0.0)
                except Exception:
                    continue

    # Conceptual vector: deterministic numeric projection of token_counts when present.
    vec: list[float] = []
    if isinstance(cm, dict):
        tc = cm.get('token_counts')
        if isinstance(tc, dict) and tc:
            # Deterministic order by token, values normalized by max.
            items = [(str(k), int(v)) for k, v in tc.items() if isinstance(k, str)]
            items.sort(key=lambda t: t[0])
            mx = max((v for _, v in items), default=0)
            if mx > 0:
                vec = [float(v) / float(mx) for _, v in items[:32]]

    scene_summary_profile = _scene_summary_profile_from_value(rec)
    reference_label_profile = _reference_label_profile_from_value(rec)

    out: Record = {
        'record_id': rid,
        'value': rec,
        'context_id': str(rec.get('category') or 'semantic'),
        'recurrence': float(_clamp01(stability)),
        'objective_links': links_map,
        'conceptual_vector': vec,
        'constraints': (rs.get('constraints') if isinstance(rs, dict) else {}) if isinstance(rs, dict) else {},
    }
    if scene_summary_profile:
        out['scene_summary_profile'] = scene_summary_profile
    if reference_label_profile:
        out['reference_label_profile'] = reference_label_profile
    return out


def load_semantic_store(*, limit: int = 200) -> list[Record]:
    """Load semantic records from LongTermStore into an in-memory store list."""
    base = resolve_path('semantic')
    if not os.path.isdir(base):
        return []
    out: list[Record] = []
    for fn in sorted(os.listdir(base)):
        if not fn.endswith('.json'):
            continue
        path = safe_join(base, fn)
        r = _record_from_semantic_json(path)
        if r is not None:
            out.append(r)
        if limit and len(out) >= int(limit):
            break
    return out


# Backward-compatible wrappers for earlier scaffold usage.
def score_record_for_objectives(*, record: dict[str, Any], objectives: Optional[list[dict[str, Any]]] = None) -> float:
    _ = objectives
    # Convert a repo record dict to a Retrieval Record and return objective relevance proxy.
    rid = str(record.get('id') or '')
    rs = record.get('relational_state') if isinstance(record.get('relational_state'), dict) else {}
    links = (rs or {}).get('objective_links') if isinstance(rs, dict) else None
    if isinstance(links, list) and links:
        return 0.7
    return 0.2


def retrieve_candidates(*, records: list[dict[str, Any]], objectives: Optional[list[dict[str, Any]]] = None, limit: int = 10) -> list[dict[str, Any]]:
    """Compatibility: rank incoming record dicts deterministically."""
    _ = objectives
    # Minimal deterministic ordering by presence of objective_links, then id.
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        scored.append((float(score_record_for_objectives(record=r, objectives=objectives)), r))
    scored.sort(key=lambda t: (-t[0], str((t[1] or {}).get('id') or '')))
    out = [r for _, r in scored]
    return out[: int(limit)] if limit else out
