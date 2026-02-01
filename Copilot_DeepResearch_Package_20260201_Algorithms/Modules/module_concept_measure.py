"""module_concept_measure.py

Conceptual measurement engine.

Purpose:
Deterministically measure non-3D information (text, concepts, descriptions)
into explicit numeric/structural metrics that can be attached to
`relational_state` and used by reasoning, scheduling, and objectives.

Design constraints:
- Deterministic (never uses system clock).
- No embeddings.
- No external calls.

Integration note:
This module is safe to call directly. Runtime integration is gated elsewhere
via config switches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, sqrt
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _tokenize(content: str, *, max_tokens: int = 4096) -> List[str]:
    """Deterministic tokenizer.

    - lowercase
    - split on non-alnum
    - bounded by max_tokens
    """
    if not isinstance(content, str):
        content = str(content)

    tokens: List[str] = []
    current: List[str] = []
    for ch in content:
        if ch.isalnum():
            current.append(ch.lower())
        else:
            if current:
                tokens.append("".join(current))
                current = []
                if max_tokens and len(tokens) >= int(max_tokens):
                    break
    if current and (not max_tokens or len(tokens) < int(max_tokens)):
        tokens.append("".join(current))
    return tokens


def _top_k_token_counts(tokens: List[str], *, top_k: int = 128) -> Dict[str, int]:
    """Return deterministic token counts, capped to top-K.

    To prevent LongTermStore bloat, we store only the top-K tokens by count,
    tie-broken lexicographically.
    """
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    items = list(counts.items())
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    if top_k and len(items) > int(top_k):
        items = items[: int(top_k)]
    return {k: int(v) for k, v in items}


def _parse_ts(ts: str) -> Optional[datetime]:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        s = ts.strip()
        # tolerate Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _deterministic_now_ts(record: Dict[str, Any], now_ts: Optional[str] = None) -> Optional[datetime]:
    """Return a deterministic 'now' time.

    Priority:
    1) explicit now_ts argument
    2) config determinism.fixed_timestamp (if available)
    3) derive from record timestamps (max timestamp)

    Never uses system clock.
    """
    if isinstance(now_ts, str) and now_ts:
        return _parse_ts(now_ts)

    # Attempt to read deterministic fixed timestamp from config via module_tools.
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode") and det.get("fixed_timestamp"):
            return _parse_ts(str(det.get("fixed_timestamp")))
    except Exception:
        pass

    ts = record.get("timestamps")
    if isinstance(ts, list) and ts:
        parsed = [p for p in (_parse_ts(str(x)) for x in ts) if p is not None]
        if parsed:
            return max(parsed)
    return None


def _compute_recurrence_metrics(record: Dict[str, Any], *, now_ts: Optional[str] = None) -> Dict[str, Any]:
    """Compute deterministic recurrence metrics.

    - occurrence_count: from record
    - recency_score: exp(-age / half_life)
    - stability_score: 1 / (1 + cv(intervals)) when 3+ timestamps
      else uses repetition_profile.stability_score if present, else 0.5.
    """
    occ = record.get("occurrence_count")
    try:
        occ_i = int(occ) if occ is not None else 0
    except Exception:
        occ_i = 0

    dtnow = _deterministic_now_ts(record, now_ts=now_ts)
    ts = record.get("timestamps")
    parsed: List[datetime] = []
    if isinstance(ts, list):
        parsed = [p for p in (_parse_ts(str(x)) for x in ts) if p is not None]
    parsed.sort()

    # Recency
    recency = 0.0
    if dtnow is not None and parsed:
        age_s = max(0.0, (dtnow - parsed[-1]).total_seconds())
        half_life_s = 7.0 * 24.0 * 3600.0
        recency = float(exp(-age_s / half_life_s))
    elif parsed:
        # If we only have timestamps but no now reference, treat as fully recent.
        recency = 1.0
    else:
        recency = 0.0

    # Stability
    stability = None
    if len(parsed) >= 3:
        intervals = [(parsed[i] - parsed[i - 1]).total_seconds() for i in range(1, len(parsed))]
        mean = sum(intervals) / max(1, len(intervals))
        if mean <= 0:
            stability = 0.0
        else:
            var = sum((x - mean) ** 2 for x in intervals) / max(1, len(intervals))
            std = sqrt(var)
            cv = std / mean
            stability = float(1.0 / (1.0 + cv))
    if stability is None:
        rep = record.get("repetition_profile")
        if isinstance(rep, dict) and rep.get("stability_score") is not None:
            try:
                stability = float(rep.get("stability_score"))
            except Exception:
                stability = 0.5
        else:
            stability = 0.5

    # Clamp
    recency = max(0.0, min(1.0, recency))
    stability = max(0.0, min(1.0, float(stability)))
    return {
        "occurrence_count": occ_i,
        "recency_score": recency,
        "stability_score": stability,
    }


def _normalize_keywords(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for k in raw:
        if not isinstance(k, str):
            continue
        kk = k.strip().lower()
        if kk:
            out.append(kk)
    # stable unique
    return sorted(set(out))


def _objective_to_spec(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize objectives.

    Supports both:
    - existing repo objective records: {id, content, labels, ...}
    - richer spec form: {id, keywords, constraints, priority, ...}
    """
    objective_id = obj.get("id") if isinstance(obj.get("id"), str) else str(obj.get("id", ""))
    if not objective_id:
        objective_id = "objective"

    try:
        priority = float(obj.get("priority", 0.5))
    except Exception:
        priority = 0.5
    priority = max(0.0, min(1.0, priority))

    keywords = _normalize_keywords(obj.get("keywords"))
    if not keywords:
        # Derive from labels + content tokens (transitional, deterministic)
        labels = obj.get("labels")
        if isinstance(labels, list):
            for l in labels:
                if isinstance(l, str):
                    ll = l.strip().lower()
                    if ll and ll not in ("objective",):
                        keywords.append(ll)
        content = obj.get("content")
        if isinstance(content, str) and content:
            keywords.extend(_tokenize(content, max_tokens=64))
        keywords = sorted(set(k for k in keywords if k))

    constraints = obj.get("constraints")
    if not isinstance(constraints, dict):
        constraints = {}

    return {
        "objective_id": objective_id,
        "priority": priority,
        "keywords": keywords,
        "constraints": constraints,
    }


def _evaluate_constraints_for_objective(
    *,
    record: Dict[str, Any],
    objective_spec: Dict[str, Any],
    tokens: List[str],
    recurrence: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Evaluate simple explicit constraints for one objective.

    Supported constraints (all optional):
    - min_occurrence (int)
    - max_length (int)   # token length
    - required_keywords (list[str])
    - forbidden_keywords (list[str])

    Returns stable-sorted flags by constraint_id.
    """
    constraints = objective_spec.get("constraints")
    if not isinstance(constraints, dict):
        constraints = {}

    objective_id = str(objective_spec.get("objective_id") or "objective")
    length = int(len(tokens))
    tokset = set(tokens)

    flags: List[Dict[str, Any]] = []

    def add_flag(constraint_id: str, status: str, reason: str):
        flags.append(
            {
                "objective_id": objective_id,
                "constraint_id": constraint_id,
                "status": status,
                "reason": reason,
            }
        )

    # min_occurrence
    if "min_occurrence" in constraints:
        try:
            min_occ = int(constraints.get("min_occurrence"))
            occ = int(recurrence.get("occurrence_count") or 0)
            if occ >= min_occ:
                add_flag("min_occurrence", "satisfied", f"occurrence_count {occ} >= {min_occ}")
            else:
                add_flag("min_occurrence", "violated", f"occurrence_count {occ} < {min_occ}")
        except Exception:
            add_flag("min_occurrence", "unknown", "invalid min_occurrence")

    # max_length
    if "max_length" in constraints:
        try:
            max_len = int(constraints.get("max_length"))
            if length <= max_len:
                add_flag("max_length", "satisfied", f"length {length} <= {max_len}")
            else:
                add_flag("max_length", "violated", f"length {length} > {max_len}")
        except Exception:
            add_flag("max_length", "unknown", "invalid max_length")

    # required_keywords
    if "required_keywords" in constraints:
        req = _normalize_keywords(constraints.get("required_keywords"))
        if not req:
            add_flag("required_keywords", "unknown", "no required keywords")
        else:
            missing = [k for k in req if k not in tokset]
            if not missing:
                add_flag("required_keywords", "satisfied", "all required keywords present")
            else:
                add_flag("required_keywords", "violated", f"missing: {', '.join(sorted(missing))}")

    # forbidden_keywords
    if "forbidden_keywords" in constraints:
        forb = _normalize_keywords(constraints.get("forbidden_keywords"))
        if not forb:
            add_flag("forbidden_keywords", "unknown", "no forbidden keywords")
        else:
            present = [k for k in forb if k in tokset]
            if not present:
                add_flag("forbidden_keywords", "satisfied", "no forbidden keywords present")
            else:
                add_flag("forbidden_keywords", "violated", f"present: {', '.join(sorted(present))}")

    flags.sort(key=lambda f: str(f.get("constraint_id", "")))
    return flags


def _constraint_score_from_flags(flags: List[Dict[str, Any]]) -> float:
    if not flags:
        return 1.0
    # Any violation -> 0.0. Unknown -> partial penalty.
    has_violation = any(f.get("status") == "violated" for f in flags)
    if has_violation:
        return 0.0
    has_unknown = any(f.get("status") == "unknown" for f in flags)
    return 0.7 if has_unknown else 1.0


def _score_objective(
    *,
    tokens: List[str],
    objective_spec: Dict[str, Any],
    recurrence: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Score a single objective deterministically."""
    objective_id = str(objective_spec.get("objective_id") or "objective")
    keywords = objective_spec.get("keywords")
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k).lower() for k in keywords if isinstance(k, str) and k.strip()]
    tokset = set(tokens)

    keyword_hits = 0
    for k in keywords:
        if k in tokset:
            keyword_hits += 1
    length = max(1, int(len(tokens)))
    keyword_density = float(keyword_hits) / float(length)

    flags = _evaluate_constraints_for_objective(
        record={},  # not used today
        objective_spec=objective_spec,
        tokens=tokens,
        recurrence=recurrence,
    )
    cscore = _constraint_score_from_flags(flags)

    try:
        priority = float(objective_spec.get("priority", 0.5))
    except Exception:
        priority = 0.5
    priority = max(0.0, min(1.0, priority))

    overall = priority * (0.6 * keyword_density + 0.4 * cscore)
    overall = max(0.0, min(1.0, float(overall)))

    return (
        {
            "objective_id": objective_id,
            "keyword_hits": int(keyword_hits),
            "keyword_density": float(round(keyword_density, 6)),
            "constraint_score": float(round(cscore, 6)),
            "overall_score": float(round(overall, 6)),
        },
        flags,
    )


def measure_conceptual_content(
    record: Dict[str, Any],
    objectives: List[Dict[str, Any]],
    *,
    now_ts: Optional[str] = None,
    max_tokens: int = 4096,
    top_k_tokens: int = 128,
) -> Dict[str, Any]:
    """Main entry point.

    Returns a JSON-serializable conceptual_measurement dict:
    {
      token_counts, length, unique_tokens,
      recurrence: {occurrence_count, recency_score, stability_score},
      objective_scores: [...],
      constraint_flags: [...]
    }
    """
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")

    content = record.get("content")
    if not isinstance(content, str):
        content = str(content or "")

    tokens = _tokenize(content, max_tokens=max_tokens)
    token_counts = _top_k_token_counts(tokens, top_k=top_k_tokens)

    recurrence = _compute_recurrence_metrics(record, now_ts=now_ts)

    objective_specs = []
    for o in objectives or []:
        if isinstance(o, dict):
            objective_specs.append(_objective_to_spec(o))

    objective_scores: List[Dict[str, Any]] = []
    constraint_flags: List[Dict[str, Any]] = []

    for spec in objective_specs:
        score_row, flags = _score_objective(tokens=tokens, objective_spec=spec, recurrence=recurrence)
        objective_scores.append(score_row)
        # Re-stamp objective_id for flags with the normalized id
        for f in flags:
            f["objective_id"] = score_row.get("objective_id")
        constraint_flags.extend(flags)

    # Stable ordering
    objective_scores.sort(key=lambda r: (-float(r.get("overall_score", 0.0)), str(r.get("objective_id", ""))))
    constraint_flags.sort(key=lambda r: (str(r.get("objective_id", "")), str(r.get("constraint_id", ""))))

    return {
        "token_counts": token_counts,
        "length": int(len(tokens)),
        "unique_tokens": int(len(set(tokens))),
        "recurrence": {
            "occurrence_count": int(recurrence.get("occurrence_count") or 0),
            "recency_score": float(round(float(recurrence.get("recency_score") or 0.0), 6)),
            "stability_score": float(round(float(recurrence.get("stability_score") or 0.0), 6)),
        },
        "objective_scores": objective_scores,
        "constraint_flags": constraint_flags,
    }


def attach_conceptual_measurement_to_relational_state(
    record: Dict[str, Any],
    conceptual_measurement: Dict[str, Any],
    *,
    derive_objective_links: bool = True,
    min_overall_for_link: float = 0.3,
) -> Dict[str, Any]:
    """Attach conceptual_measurement into record['relational_state'].

    - Ensures relational_state exists and has required list fields.
    - Writes relational_state['conceptual_measurement'].
    - Optionally derives objective_links entries from objective_scores.
    """
    if not isinstance(record, dict):
        raise TypeError("record must be a dict")
    if not isinstance(conceptual_measurement, dict):
        raise TypeError("conceptual_measurement must be a dict")

    rs = record.get("relational_state")
    if not isinstance(rs, dict):
        rs = {}
        record["relational_state"] = rs

    rs.setdefault("entities", [])
    rs.setdefault("relations", [])
    rs.setdefault("constraints", [])
    rs.setdefault("objective_links", [])
    rs.setdefault("spatial_measurement", None)
    rs.setdefault("decision_trace", {})

    rs["conceptual_measurement"] = conceptual_measurement

    if derive_objective_links:
        links = rs.get("objective_links")
        if not isinstance(links, list):
            links = []
            rs["objective_links"] = links
        existing = {l.get("objective_id") for l in links if isinstance(l, dict)}

        scores = conceptual_measurement.get("objective_scores")
        if isinstance(scores, list):
            for row in scores:
                if not isinstance(row, dict):
                    continue
                oid = row.get("objective_id")
                if not isinstance(oid, str) or not oid or oid in existing:
                    continue
                try:
                    overall = float(row.get("overall_score") or 0.0)
                except Exception:
                    overall = 0.0
                if overall < float(min_overall_for_link):
                    continue
                links.append(
                    {
                        "objective_id": oid,
                        "relevance": max(0.0, min(1.0, overall)),
                        "reason": "conceptual_measurement",
                        "evidence": [],
                    }
                )
                existing.add(oid)

    return record
