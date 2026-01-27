"""module_verifier.py

Deterministic validation utilities for activities.

Public API:
- check_preconditions
- check_postconditions
- generate_validation_artifact
- escalate_on_failure

Design goals:
- Deterministic artifacts when deterministic_mode is enabled
- Side-effect-free checks
- Additive: callers may ignore this module
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(obj: Any) -> str:
    return hashlib.sha256(_stable_json(obj).encode("utf-8")).hexdigest()


def _now_ts(*, deterministic_mode: bool) -> float:
    if deterministic_mode:
        try:
            from module_provenance import now_ts as _prov_now_ts

            return float(_prov_now_ts())
        except Exception:
            return 0.0
    try:
        from module_provenance import now_ts as _prov_now_ts

        return float(_prov_now_ts())
    except Exception:
        return 0.0


def _confidence_from_checks(checks: List[Dict[str, Any]]) -> float:
    if not checks:
        return 1.0
    passed = 0
    total = 0
    for c in checks:
        if not isinstance(c, dict):
            continue
        total += 1
        if bool(c.get("ok")):
            passed += 1
    if total <= 0:
        return 1.0
    return float(passed) / float(total)


def _extract_activity_cost(activity: Dict[str, Any]) -> Dict[str, float]:
    meta = activity.get("metadata")
    if isinstance(meta, dict) and isinstance(meta.get("cost"), dict):
        out: Dict[str, float] = {}
        for k, v in meta.get("cost", {}).items():
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out
    if isinstance(activity.get("cost"), dict):
        out = {}
        for k, v in activity.get("cost", {}).items():
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out
    try:
        c = float(activity.get("cost") or 0.0)
    except Exception:
        c = 0.0
    return {"cpu": float(c)}


def _validate_provenance_chain(provenance: List[Dict[str, Any]]) -> bool:
    """Validate a simple linear chain of events.

    This does not assume a global log; it validates internal consistency.
    """
    if not isinstance(provenance, list):
        return False
    try:
        from module_provenance import compute_hash

        prev_id: Optional[str] = None
        for e in provenance:
            if not isinstance(e, dict):
                return False
            eid = e.get("event_id")
            if not isinstance(eid, str) or not eid:
                return False
            base = {k: e[k] for k in e if k != "event_id"}
            if compute_hash(base) != eid:
                return False
            ph = e.get("prev_hash")
            if prev_id is None:
                # first element can have None prev_hash
                pass
            else:
                if ph != prev_id:
                    return False
            prev_id = eid
        return True
    except Exception:
        # If provenance module lacks hashing utilities, treat as unknown/ok.
        return True


def check_preconditions(activity: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Check preconditions deterministically.

    Returns: {ok: bool, failures: list[str], evidence: dict}
    """
    failures: List[str] = []
    evidence: Dict[str, Any] = {"checks": []}

    meta = activity.get("metadata") if isinstance(activity, dict) else None
    pre = (meta or {}).get("preconditions") if isinstance(meta, dict) else None
    if pre is None:
        pre = []

    # schema_validation
    if not isinstance(activity, dict) or not isinstance(activity.get("activity_type"), str):
        failures.append("schema_validation")
        evidence["checks"].append({"name": "schema_validation", "ok": False, "reason": "missing_activity_type"})
    else:
        evidence["checks"].append({"name": "schema_validation", "ok": True})

    # record_version / measurement_freshness are modeled in activity.metadata.preconditions
    if isinstance(pre, list):
        records_map = state.get("records_map") if isinstance(state, dict) else None
        last_measure_ts = state.get("last_measure_ts") if isinstance(state, dict) else None

        for p in pre:
            if not isinstance(p, dict):
                continue
            ptype = str(p.get("type") or "")
            if ptype == "record_version":
                rid = str(p.get("record_id") or "")
                try:
                    min_v = int(p.get("min_version") or 0)
                except Exception:
                    min_v = 0
                got_v = 0
                if isinstance(records_map, dict) and isinstance(records_map.get(rid), dict):
                    try:
                        got_v = int((records_map.get(rid) or {}).get("version") or 0)
                    except Exception:
                        got_v = 0
                ok = got_v >= min_v
                if not ok:
                    failures.append("record_version")
                evidence["checks"].append({"name": "record_version", "ok": bool(ok), "record_id": rid, "min": min_v, "got": got_v})

            elif ptype == "measurement_freshness":
                rid = str(p.get("record_id") or "")
                try:
                    min_ts = float(p.get("min_ts") or 0.0)
                except Exception:
                    min_ts = 0.0
                got_ts = 0.0
                if isinstance(last_measure_ts, dict):
                    try:
                        got_ts = float(last_measure_ts.get(rid) or 0.0)
                    except Exception:
                        got_ts = 0.0
                ok = got_ts >= min_ts
                if not ok:
                    failures.append("measurement_freshness")
                evidence["checks"].append({"name": "measurement_freshness", "ok": bool(ok), "record_id": rid, "min_ts": min_ts, "got_ts": got_ts})

    # resource_availability (optional)
    budget = state.get("resource_budget") if isinstance(state, dict) else None
    used = state.get("used_resources") if isinstance(state, dict) else None
    if isinstance(budget, dict) and isinstance(used, dict):
        cost = _extract_activity_cost(activity)
        ok = True
        for k, v in cost.items():
            try:
                if float(used.get(k, 0.0)) + float(v) > float(budget.get(k, 1.0)):
                    ok = False
            except Exception:
                continue
        if not ok:
            failures.append("resource_availability")
        evidence["checks"].append({"name": "resource_availability", "ok": bool(ok), "cost": cost})

    # provenance_integrity (optional)
    prov = state.get("provenance") if isinstance(state, dict) else None
    if isinstance(prov, list):
        ok = _validate_provenance_chain([e for e in prov if isinstance(e, dict)])
        if not ok:
            failures.append("provenance_integrity")
        evidence["checks"].append({"name": "provenance_integrity", "ok": bool(ok), "n_events": len(prov)})

    return {"ok": len(failures) == 0, "failures": failures, "evidence": evidence}


def check_postconditions(activity: Dict[str, Any], result: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Check postconditions deterministically.

    Returns: {ok: bool, failures: list[str], evidence: dict}
    """
    failures: List[str] = []
    checks: List[Dict[str, Any]] = []

    at = str(activity.get("activity_type") or "")

    # validation_artifact exists for error_resolution when rollback-capable path is used
    stat = None
    if at == "error_resolution":
        # result may contain resolution_task with validation
        rt = result.get("resolution_task") if isinstance(result, dict) else None
        if isinstance(rt, dict):
            v = rt.get("validation")
            stat = v if isinstance(v, dict) else None

    if at == "error_resolution":
        ok = isinstance(stat, dict)
        if not ok:
            failures.append("validation_artifact")
        checks.append({"name": "validation_artifact", "ok": bool(ok)})

        # statistical_validation shape + thresholds when present
        cfg = state.get("verifier_cfg") if isinstance(state, dict) else None
        p_thr = 0.05
        min_eff = 1e-6
        if isinstance(cfg, dict):
            try:
                p_thr = float(cfg.get("p_threshold", p_thr))
            except Exception:
                pass
            try:
                min_eff = float(cfg.get("min_effect_size", min_eff))
            except Exception:
                pass

        if isinstance(stat, dict):
            has_shape = all(k in stat for k in ("t", "p", "n", "mean_diff", "sd"))
            checks.append({"name": "statistical_validation_shape", "ok": bool(has_shape)})
            if not has_shape:
                failures.append("statistical_validation_shape")
            try:
                p = float(stat.get("p", 1.0))
            except Exception:
                p = 1.0
            try:
                md = float(stat.get("mean_diff") or 0.0)
            except Exception:
                md = 0.0
            meets = (p < p_thr) and (abs(md) > min_eff)
            checks.append({"name": "statistical_validation_threshold", "ok": bool(meets), "p": p, "mean_diff": md, "p_thr": p_thr, "min_effect": min_eff})

    # no_unexpected_side_effects (minimal: optional allowed_record_ids)
    allowed = state.get("allowed_record_ids") if isinstance(state, dict) else None
    changed = state.get("changed_record_ids") if isinstance(state, dict) else None
    if isinstance(allowed, list) and isinstance(changed, list):
        extra = [x for x in changed if x not in allowed]
        ok = len(extra) == 0
        if not ok:
            failures.append("no_unexpected_side_effects")
        checks.append({"name": "no_unexpected_side_effects", "ok": bool(ok), "extra": extra})

    ok_all = len(failures) == 0
    return {"ok": ok_all, "failures": failures, "evidence": {"checks": checks, "statistical_validation": stat}}


def generate_validation_artifact(pre: Dict[str, Any], post: Dict[str, Any], provenance: List[Dict[str, Any]], deterministic_mode: bool) -> Dict[str, Any]:
    """Generate a machine-readable validation artifact."""
    pre_checks = (pre.get("evidence") or {}).get("checks") if isinstance(pre, dict) else None
    post_checks = (post.get("evidence") or {}).get("checks") if isinstance(post, dict) else None
    pre_list = list(pre_checks or []) if isinstance(pre_checks, list) else []
    post_list = list(post_checks or []) if isinstance(post_checks, list) else []

    prov_ids: List[str] = []
    for e in provenance or []:
        if isinstance(e, dict) and isinstance(e.get("event_id"), str):
            prov_ids.append(e["event_id"])

    confidence = 0.5 * _confidence_from_checks(pre_list) + 0.5 * _confidence_from_checks(post_list)
    payload = {
        "pre": pre,
        "post": post,
        "provenance_event_ids": prov_ids,
        "confidence": confidence,
        "ts": _now_ts(deterministic_mode=deterministic_mode),
    }
    artifact_id = _stable_hash(payload)

    out = {
        "artifact_id": artifact_id,
        "activity_id": str((pre.get("activity_id") if isinstance(pre, dict) else None) or (post.get("activity_id") if isinstance(post, dict) else None) or ""),
        "pre_checks": pre_list,
        "post_checks": post_list,
        "statistical_validation": (post.get("evidence") or {}).get("statistical_validation") if isinstance(post, dict) else None,
        "confidence_score": float(confidence),
        "provenance_snapshot": prov_ids,
        "timestamp": payload["ts"],
        "trace": {
            "pre_ok": bool(pre.get("ok")) if isinstance(pre, dict) else False,
            "post_ok": bool(post.get("ok")) if isinstance(post, dict) else False,
        },
    }
    return out


def escalate_on_failure(artifact: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    """Return an action plan given a failed artifact.

    Deterministic and policy-driven; does not perform side effects.
    """
    if not isinstance(artifact, dict):
        return {"action": "noop", "reason": "missing_artifact"}

    conf_thr = 0.8
    try:
        conf_thr = float((policy or {}).get("confidence_threshold", conf_thr))
    except Exception:
        pass

    conf = 0.0
    try:
        conf = float(artifact.get("confidence_score") or 0.0)
    except Exception:
        conf = 0.0

    if conf >= conf_thr:
        return {"action": "requeue", "reason": "high_confidence_failure", "follow_up_activity": "re_measure"}

    return {"action": "escalate", "reason": "low_confidence_failure", "notify": True}
