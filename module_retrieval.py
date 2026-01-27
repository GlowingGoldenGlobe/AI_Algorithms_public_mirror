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


class RetrievalQuery(TypedDict, total=False):
    target_ids: list[str]
    objective_id: Optional[str]
    conceptual_vector: Optional[list[float]]
    required_context: Optional[str]
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

    u = _get_uncertainty_penalty(record)
    return {
        'conceptual': float(s_c),
        'objective': float(s_o),
        'recurrence': float(s_r),
        'constraint': float(s_q),
        'uncertainty': float(u),
    }


def compute_score_td(*, components: dict[str, float], weights: Optional[dict[str, float]] = None) -> float:
    """Weighted score with uncertainty penalty."""
    w = weights or {
        'conceptual': 0.40,
        'objective': 0.30,
        'recurrence': 0.20,
        'constraint': 0.10,
        'uncertainty': 0.20,
    }
    return float(
        float(w.get('conceptual', 0.0)) * float(components.get('conceptual', 0.0))
        + float(w.get('objective', 0.0)) * float(components.get('objective', 0.0))
        + float(w.get('recurrence', 0.0)) * float(components.get('recurrence', 0.0))
        + float(w.get('constraint', 0.0)) * float(components.get('constraint', 0.0))
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
        'conceptual': 0.40,
        'objective': 0.30,
        'recurrence': 0.20,
        'constraint': 0.10,
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

    return {
        'record_id': rid,
        'score': float(score),
        'components': {
            'measurement': float(measurement),
            'objective': float(objective),
            'recurrence': float(recurrence),
            'conceptual': float(conceptual),
            'constraint': float(constraint),
        },
    }


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

    return {
        'record_id': rid,
        'value': rec,
        'context_id': str(rec.get('category') or 'semantic'),
        'recurrence': float(_clamp01(stability)),
        'objective_links': links_map,
        'conceptual_vector': vec,
        'constraints': (rs.get('constraints') if isinstance(rs, dict) else {}) if isinstance(rs, dict) else {},
    }


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
