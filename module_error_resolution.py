"""module_error_resolution.py

Deterministic error-solving engine.

This module performs error detection, classification, correction, and validation
using measurement + comparison + delta.

No time sources are consulted here; timestamps are treated as provided inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics

from typing import Any, Callable, Literal, Optional, TypedDict


ErrorType = Literal[
    "mis_measurement",
    "mis_description",
    "mis_association",
    "mis_inference",
]


class Measurement(TypedDict):
    value: Any
    source_id: str
    timestamp: float
    context_id: str
    # Optional JSON-friendly uncertainty payload: {value, variance, provenance}
    uncertainty: dict[str, Any]


class StoredRecord(TypedDict, total=False):
    record_id: str
    value: Any
    context_id: str
    links: dict[str, Any]
    derived: bool
    inputs: list[str]
    # Optional JSON-friendly uncertainty payload: {value, variance, provenance}
    uncertainty: dict[str, Any]


class ErrorReport(TypedDict, total=False):
    error_type: ErrorType
    measured_value: Any
    stored_value: Any
    delta: float
    severity: float
    target_record_id: str
    confidence: float
    uncertainty_measured: dict[str, Any]
    uncertainty_stored: dict[str, Any]


def _uncertainty_dict_to_parts(u: Any) -> Optional[tuple[float, float, dict[str, Any]]]:
    if not isinstance(u, dict):
        return None
    try:
        variance = float(u.get('variance'))
    except Exception:
        return None
    if variance < 0.0:
        variance = 0.0
    prov = u.get('provenance')
    provenance = dict(prov) if isinstance(prov, dict) else {}
    val = u.get('value')
    try:
        value = float(val)
    except Exception:
        value = 0.0
    return (value, float(variance), provenance)


def _confidence_from_uncertainties(*, delta: float, m_unc: Any, r_unc: Any) -> Optional[float]:
    """Compute confidence if both uncertainties are present and parseable."""
    mp = _uncertainty_dict_to_parts(m_unc)
    rp = _uncertainty_dict_to_parts(r_unc)
    if mp is None or rp is None:
        return None
    try:
        from module_uncertainty import Uncertainty, confidence_from_delta

        u_m = Uncertainty(float(mp[0]), float(mp[1]), dict(mp[2]))
        u_r = Uncertainty(float(rp[0]), float(rp[1]), dict(rp[2]))
        return float(confidence_from_delta(float(delta), u_m, u_r))
    except Exception:
        return None


class ErrorResolutionTask(TypedDict):
    activity: Literal["error_resolution"]
    target_record_id: str
    error_type: ErrorType
    priority: float
    error_report: ErrorReport


def classify_error(*, measurement: Measurement, record: StoredRecord) -> ErrorType:
    """Classify error based on what differs.

    - Context mismatch -> mis_association
    - Derived record -> mis_inference
    - Missing measurement value -> mis_measurement
    - Otherwise -> mis_description
    """
    if measurement.get("context_id") != record.get("context_id"):
        return "mis_association"

    if bool(record.get("derived")):
        return "mis_inference"

    if measurement.get("value") is None:
        return "mis_measurement"

    return "mis_description"


def _compute_delta(*, measured_value: Any, stored_value: Any) -> float:
    """Compute a deterministic delta.

    - For numeric scalars: |M - D|
    - For other types: 1.0 when not equal
    """
    if measured_value == stored_value:
        return 0.0
    if isinstance(measured_value, (int, float)) and not isinstance(measured_value, bool) and isinstance(
        stored_value, (int, float)
    ) and not isinstance(stored_value, bool):
        return float(abs(float(measured_value) - float(stored_value)))
    return 1.0


def detect_error(*, measurement: Measurement, record: StoredRecord) -> Optional[ErrorReport]:
    """Detect mismatch via equivalence check and delta."""
    m = measurement.get("value")
    d = record.get("value")

    if m == d:
        return None

    delta = _compute_delta(measured_value=m, stored_value=d)
    et = classify_error(measurement=measurement, record=record)

    # Optional: uncertainty-aware confidence in [0,1].
    # If uncertainty is missing, we keep confidence neutral (0.5).
    m_unc = measurement.get('uncertainty')
    r_unc = record.get('uncertainty')
    conf = _confidence_from_uncertainties(delta=float(delta), m_unc=m_unc, r_unc=r_unc)
    confidence = float(conf) if conf is not None else 0.5

    return {
        "error_type": et,
        "measured_value": m,
        "stored_value": d,
        "delta": float(delta),
        "severity": float(delta),
        "target_record_id": str(record.get("record_id") or ""),
        "confidence": confidence,
        "uncertainty_measured": dict(m_unc) if isinstance(m_unc, dict) else {},
        "uncertainty_stored": dict(r_unc) if isinstance(r_unc, dict) else {},
    }


def create_error_resolution_task(*, error_report: ErrorReport) -> ErrorResolutionTask:
    return {
        "activity": "error_resolution",
        "target_record_id": error_report["target_record_id"],
        "error_type": error_report["error_type"],
        "priority": float(error_report["severity"]),
        "error_report": error_report,
    }


def execute_error_resolution_task(
    *,
    task: ErrorResolutionTask,
    measurement_fn: Callable[[str], Measurement],
    update_record_fn: Callable[[str, Any], StoredRecord],
    relink_fn: Callable[[str], StoredRecord],
    recompute_fn: Callable[[str], StoredRecord],
) -> StoredRecord:
    """Execute correction deterministically by delegating to the appropriate function."""
    error_type = task["error_type"]
    report = task["error_report"]
    target_id = report["target_record_id"]

    if error_type == "mis_measurement":
        new_measurement = measurement_fn(target_id)
        return update_record_fn(target_id, new_measurement["value"])

    if error_type == "mis_description":
        return update_record_fn(target_id, report["measured_value"])

    if error_type == "mis_association":
        return relink_fn(target_id)

    if error_type == "mis_inference":
        return recompute_fn(target_id)

    raise ValueError("Unknown error type")


def validate_correction(*, measurement: Measurement, record: StoredRecord) -> bool:
    """Re-measure -> re-compare -> confirm equivalence."""
    return measurement.get("value") == record.get("value")


def re_measure(*, measurement_fn: Callable[[str], Measurement], record_id: str) -> Measurement:
    return measurement_fn(record_id)


def update_record_value(*, record: StoredRecord, new_value: Any) -> StoredRecord:
    record["value"] = new_value
    return record


def relink_record(*, record: StoredRecord, new_context_id: str) -> StoredRecord:
    record["context_id"] = new_context_id
    return record


# -----------------------------
# Think-Deeper add-ons (additive)
# -----------------------------


def now_ts(*, deterministic_mode: bool = False, deterministic_time: Optional[float] = None) -> float:
    """Timestamp seconds.

    - deterministic_mode=True: return deterministic_time if provided else 0.0
    - otherwise: use module_provenance.now_ts() (wall-clock, deterministic-aware)
    """
    if deterministic_mode:
        return float(deterministic_time if deterministic_time is not None else 0.0)
    try:
        from module_provenance import now_ts as _prov_now_ts

        return float(_prov_now_ts())
    except Exception:
        return 0.0


def stable_hash(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _last_event_id(provenance_log: list[dict[str, Any]]) -> Optional[str]:
    if not provenance_log:
        return None
    last = provenance_log[-1]
    if not isinstance(last, dict):
        return None
    eid = last.get("event_id")
    return str(eid) if isinstance(eid, str) and eid else None


class RollbackPlan(TypedDict):
    snapshot: StoredRecord
    timestamp: float


class ResolutionTask(TypedDict, total=False):
    task_id: str
    activity: Literal["error_resolution"]
    target_record_id: str
    error_type: ErrorType
    resolution_strategy: str
    priority: float
    created_ts: float
    status: str
    error_report: ErrorReport
    error_event_id: str
    rollback_plan: RollbackPlan
    rollback_reason: dict[str, Any]
    validation: dict[str, Any]
    creation_event_id: str
    executed_event_id: str


def create_rollback_plan(
    *,
    record_snapshot: StoredRecord,
    deterministic_mode: bool = False,
    deterministic_time: Optional[float] = None,
) -> RollbackPlan:
    return {
        "snapshot": dict(record_snapshot),
        "timestamp": now_ts(deterministic_mode=deterministic_mode, deterministic_time=deterministic_time),
    }


def log_error_report(
    *,
    error_report: ErrorReport,
    provenance_log: list[dict[str, Any]],
    deterministic_mode: bool = False,
    deterministic_time: Optional[float] = None,
) -> tuple[ErrorReport, list[dict[str, Any]]]:
    """Append a deterministic provenance event for an error report."""
    try:
        from module_provenance import append_event, create_event

        rid = str(error_report.get("target_record_id") or "")
        ev = create_event(
            "error_report",
            {"target_ids": [rid] if rid else [], "error_report": dict(error_report)},
            prev_hash=_last_event_id(provenance_log),
            timestamp=now_ts(deterministic_mode=deterministic_mode, deterministic_time=deterministic_time),
        )
        out_log = append_event(provenance_log, ev)
        out_rep = dict(error_report)
        out_rep["event_id"] = ev.get("event_id")
        return out_rep, out_log
    except Exception:
        return dict(error_report), list(provenance_log or [])


def create_resolution_task(
    *,
    error_report: ErrorReport,
    resolution_strategy: str,
    priority: Optional[float] = None,
    metadata: Optional[dict[str, Any]] = None,
    provenance_log: Optional[list[dict[str, Any]]] = None,
    deterministic_mode: bool = False,
    deterministic_time: Optional[float] = None,
) -> tuple[ResolutionTask, list[dict[str, Any]]]:
    """Create a rollback-capable resolution task and log its creation."""
    prov = list(provenance_log or [])
    rid = str(error_report.get("target_record_id") or "")
    task_id = stable_hash({"rid": rid, "strategy": str(resolution_strategy), "er": error_report.get("event_id") or stable_hash(error_report)})
    task: ResolutionTask = {
        "task_id": task_id,
        "activity": "error_resolution",
        "target_record_id": rid,
        "error_type": error_report.get("error_type") or "mis_description",
        "resolution_strategy": str(resolution_strategy),
        "priority": float(priority if priority is not None else float(error_report.get("severity") or 0.0)),
        "created_ts": now_ts(deterministic_mode=deterministic_mode, deterministic_time=deterministic_time),
        "status": "pending",
        "error_report": dict(error_report),
        "error_event_id": str(error_report.get("event_id") or ""),
    }
    if isinstance(metadata, dict):
        task["metadata"] = dict(metadata)

    try:
        from module_provenance import append_event, create_event

        ev = create_event(
            "resolution_task_created",
            {"target_ids": [rid] if rid else [], "task": dict(task)},
            prev_hash=_last_event_id(prov),
            timestamp=now_ts(deterministic_mode=deterministic_mode, deterministic_time=deterministic_time),
        )
        prov = append_event(prov, ev)
        task["creation_event_id"] = str(ev.get("event_id") or "")
    except Exception:
        pass
    return task, prov


def paired_t_test(*, before_samples: list[float], after_samples: list[float]) -> dict[str, Any]:
    """Paired t-test with deterministic normal-approx p-value.

    Returns keys: t, p, n, mean_diff, sd
    """
    n = min(len(before_samples), len(after_samples))
    if n <= 0:
        return {"t": 0.0, "p": 1.0, "n": 0, "mean_diff": 0.0, "sd": 0.0}

    diffs = [float(after_samples[i]) - float(before_samples[i]) for i in range(n)]
    mean_diff = float(statistics.mean(diffs)) if diffs else 0.0
    sd = float(statistics.stdev(diffs)) if n > 1 else 0.0
    if not math.isfinite(sd) or sd <= 0.0:
        return {"t": 0.0, "p": 1.0, "n": int(n), "mean_diff": mean_diff, "sd": 0.0}
    t_stat = float(mean_diff / (sd / math.sqrt(float(n))))
    # two-sided p via standard-normal approximation
    p = 2.0 * (1.0 - (0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2.0)))))
    if p < 0.0:
        p = 0.0
    if p > 1.0:
        p = 1.0
    return {"t": t_stat, "p": float(p), "n": int(n), "mean_diff": mean_diff, "sd": sd}


def _record_uncertainty_as_uncertainty(record: dict[str, Any]) -> "Uncertainty":
    from module_uncertainty import Uncertainty

    u = record.get("uncertainty")
    parts = _uncertainty_dict_to_parts(u)
    if parts is not None:
        return Uncertainty(float(parts[0]), float(parts[1]), dict(parts[2]))
    v = record.get("value")
    try:
        value = float(v)
    except Exception:
        value = 0.0
    return Uncertainty(value, 0.0, {"note": "no_uncertainty"})


def validate_records_statistically(
    *,
    record_before: StoredRecord,
    record_after: StoredRecord,
    n_samples: int = 256,
) -> dict[str, Any]:
    """Deterministic Monte Carlo paired validation using stored uncertainties when available."""
    from module_uncertainty import sample_distribution

    u_before = _record_uncertainty_as_uncertainty(dict(record_before))
    u_after = _record_uncertainty_as_uncertainty(dict(record_after))
    before_samples = sample_distribution(u_before, int(n_samples))
    after_samples = sample_distribution(u_after, int(n_samples))
    return paired_t_test(before_samples=before_samples, after_samples=after_samples)


def validate_records_statistically_adaptive(
    *,
    record_before: StoredRecord,
    record_after: StoredRecord,
    n_min: int = 32,
    n0: Optional[int] = None,
    n_max: int = 256,
    alpha: float = 0.05,
    growth_multiplier: float = 2.0,
    decision_multiplier: float = 10.0,
    early_stop_margin: Optional[float] = None,
) -> dict[str, Any]:
    """Adaptive deterministic Monte Carlo paired validation.

    Uses prefix-stable sampling so that results at n=k are deterministic
    prefixes of results at larger n.

    Early-stops only when p is far from the decision boundary.
    Returns the same core keys as `paired_t_test` (t, p, n, mean_diff, sd)
    and adds metadata keys.
    """
    from module_uncertainty import sample_distribution_prefix

    n_min_i = int(n_min)
    if n_min_i < 2:
        n_min_i = 2

    if n0 is None:
        n0_i = int(n_min_i)
    else:
        n0_i = int(n0)
        if n0_i < int(n_min_i):
            n0_i = int(n_min_i)

    n1 = int(n_max)
    if n1 < n0_i:
        n1 = n0_i
    if n1 < n0:
        n1 = n0

    u_before = _record_uncertainty_as_uncertainty(dict(record_before))
    u_after = _record_uncertainty_as_uncertainty(dict(record_after))

    n = n0_i
    last_stats: dict[str, Any] = {"t": 0.0, "p": 1.0, "n": 0, "mean_diff": 0.0, "sd": 0.0}
    early_stopped = False
    stop_reason = ""
    while True:
        before_samples = sample_distribution_prefix(u_before, int(n))
        after_samples = sample_distribution_prefix(u_after, int(n))
        stats = paired_t_test(before_samples=before_samples, after_samples=after_samples)
        last_stats = dict(stats)

        try:
            p = float(stats.get("p", 1.0))
        except Exception:
            p = 1.0

        # Conservative early-stop: only stop when clearly far from alpha.
        if n >= n1:
            stop_reason = "reached_n_max"
            break

        m = early_stop_margin
        if m is not None:
            try:
                m = float(m)
            except Exception:
                m = None

        if (m is not None) and (m >= 0.0):
            lo = float(alpha) - float(m)
            hi = float(alpha) + float(m)
            if lo < 0.0:
                lo = 0.0
            if hi > 1.0:
                hi = 1.0
            if (p < lo) or (p > hi):
                early_stopped = True
                stop_reason = "p_margin"
                break
        else:
            mult = float(decision_multiplier) if float(decision_multiplier) > 1.0 else 10.0
            if (p < (float(alpha) / mult)) or (p > (float(alpha) * mult)):
                early_stopped = True
                stop_reason = "p_multiplier"
                break
            break

        gm = float(growth_multiplier)
        if gm < 1.1:
            gm = 2.0
        n = min(n1, int(max(int(n) + 1, int(round(float(n) * gm)))))
        if n <= int(last_stats.get("n") or 0):
            stop_reason = "no_progress"
            break

    last_stats["adaptive"] = True
    last_stats["n_min"] = int(n_min_i)
    last_stats["n0"] = int(n0_i)
    last_stats["n_max"] = int(n1)
    last_stats["growth_multiplier"] = float(growth_multiplier)
    last_stats["decision_multiplier"] = float(decision_multiplier)
    if early_stop_margin is not None:
        try:
            last_stats["early_stop_margin"] = float(early_stop_margin)
        except Exception:
            pass
    last_stats["alpha"] = float(alpha)
    last_stats["early_stopped"] = bool(early_stopped)
    if stop_reason:
        last_stats["stop_reason"] = str(stop_reason)
    return last_stats


def execute_resolution_task(
    *,
    task: ResolutionTask,
    record_lookup_fn: Callable[[str], StoredRecord],
    measure_fn: Callable[[str], Measurement],
    storage_update_fn: Callable[[StoredRecord], None],
    relink_fn: Callable[[StoredRecord, str], StoredRecord],
    recompute_fn: Callable[[StoredRecord], StoredRecord],
    provenance_log: list[dict[str, Any]],
    deterministic_mode: bool = False,
    deterministic_time: Optional[float] = None,
    n_samples: int = 256,
    alpha: float = 0.05,
    min_effect_size: float = 1e-6,
    adaptive_sampling: bool = False,
    adaptive_n_min: int = 32,
    adaptive_n0: Optional[int] = None,
    adaptive_n_max: Optional[int] = None,
    adaptive_growth_multiplier: float = 2.0,
    adaptive_early_stop_margin: Optional[float] = None,
    adaptive_multiplier: float = 10.0,
    rollback_storm_max_rollbacks: int = 3,
    rollback_storm_enabled: bool = False,
) -> tuple[ResolutionTask, list[dict[str, Any]]]:
    """Execute a rollback-capable correction with statistical validation.

    This is additive; the legacy execute_error_resolution_task remains unchanged.
    """
    prov = list(provenance_log or [])
    rid = str(task.get("target_record_id") or "")
    record_before = record_lookup_fn(rid)
    rollback = create_rollback_plan(record_snapshot=record_before, deterministic_mode=deterministic_mode, deterministic_time=deterministic_time)
    task["rollback_plan"] = rollback
    task["status"] = "running"

    strat = str(task.get("resolution_strategy") or "")
    # Execute strategy.
    if strat == "re_measure":
        m = measure_fn(rid)
        cur = record_lookup_fn(rid)
        delta = _compute_delta(measured_value=m.get("value"), stored_value=cur.get("value"))
        conf = _confidence_from_uncertainties(delta=float(delta), m_unc=m.get("uncertainty"), r_unc=cur.get("uncertainty"))
        confidence = float(conf) if conf is not None else 0.5
        if confidence > 0.75:
            updated = dict(cur)
            updated["value"] = m.get("value")
            if isinstance(updated.get("version"), int):
                updated["version"] = int(updated.get("version") or 0) + 1
            storage_update_fn(updated)
        else:
            task["status"] = "needs_review"
    elif strat == "update_description":
        er = task.get("error_report") if isinstance(task.get("error_report"), dict) else {}
        updated = dict(record_lookup_fn(rid))
        updated["value"] = er.get("measured_value")
        if isinstance(updated.get("version"), int):
            updated["version"] = int(updated.get("version") or 0) + 1
        storage_update_fn(updated)
    elif strat == "relink":
        meta = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
        new_context_id = str(meta.get("new_context_id") or "")
        if not new_context_id:
            task["status"] = "failed"
        else:
            updated = relink_fn(dict(record_lookup_fn(rid)), new_context_id)
            if isinstance(updated.get("version"), int):
                updated["version"] = int(updated.get("version") or 0) + 1
            storage_update_fn(updated)
    elif strat == "recompute":
        updated = recompute_fn(dict(record_lookup_fn(rid)))
        if isinstance(updated.get("version"), int):
            updated["version"] = int(updated.get("version") or 0) + 1
        storage_update_fn(updated)
    else:
        task["status"] = "failed"

    # If execution failed or needs review, we still log an execution event deterministically.
    record_after = record_lookup_fn(rid)
    if bool(adaptive_sampling):
        validation = validate_records_statistically_adaptive(
            record_before=rollback["snapshot"],
            record_after=record_after,
            n_min=int(adaptive_n_min),
            n0=adaptive_n0,
            n_max=int(adaptive_n_max) if adaptive_n_max is not None else int(n_samples),
            alpha=float(alpha),
            growth_multiplier=float(adaptive_growth_multiplier),
            decision_multiplier=float(adaptive_multiplier),
            early_stop_margin=adaptive_early_stop_margin,
        )
    else:
        validation = validate_records_statistically(record_before=rollback["snapshot"], record_after=record_after, n_samples=int(n_samples))
    task["validation"] = dict(validation)

    # Lightweight metrics (best-effort; no hard dependency).
    try:
        from module_metrics import add_counter, incr_counter

        n_used = int((validation or {}).get("n") or 0)
        if bool(adaptive_sampling):
            incr_counter("resolution_adaptive_used_total", 1)
            add_counter("resolution_adaptive_samples_total", float(n_used))
            if bool((validation or {}).get("early_stopped")):
                incr_counter("resolution_adaptive_early_stop_total", 1)
        else:
            add_counter("resolution_fixed_samples_total", float(n_used))
    except Exception:
        pass

    if task.get("status") == "running":
        try:
            p = float(validation.get("p", 1.0))
        except Exception:
            p = 1.0
        try:
            md = float(validation.get("mean_diff", 0.0))
        except Exception:
            md = 0.0
        if (p < float(alpha)) and (abs(md) > float(min_effect_size)):
            task["status"] = "validated"
        else:
            storage_update_fn(dict(rollback["snapshot"]))
            task["status"] = "rolled_back"
            task["rollback_reason"] = {"p": p, "mean_diff": md}

            # Rollback-storm policy: after repeated rollbacks for the same target,
            # escalate to needs_review instead of continually retrying.
            try:
                if bool(rollback_storm_enabled):
                    rid2 = str(task.get("target_record_id") or "")
                    max_rb = int(rollback_storm_max_rollbacks)
                    if max_rb < 1:
                        max_rb = 1

                    consecutive = 0
                    # scan provenance from newest to oldest
                    for ev in reversed(prov):
                        if not isinstance(ev, dict):
                            continue
                        if ev.get("event_type") != "resolution_executed":
                            continue
                        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
                        tprev = payload.get("task") if isinstance(payload.get("task"), dict) else {}
                        if str(tprev.get("target_record_id") or "") != rid2:
                            continue
                        status_prev = str(tprev.get("status") or "")
                        if status_prev == "rolled_back":
                            consecutive += 1
                            continue
                        # break on first non-rollback status for this target
                        break

                    # include current rollback attempt
                    consecutive += 1
                    task["rollback_storm"] = {
                        "enabled": True,
                        "max_rollbacks": int(max_rb),
                        "consecutive_rollbacks": int(consecutive),
                    }
                    if consecutive >= int(max_rb):
                        task["status"] = "needs_review"
                        task["rollback_storm"]["escalated"] = True

                        # Metrics: track escalations (best-effort; no hard dependency).
                        try:
                            from module_metrics import incr_counter

                            incr_counter("resolution_rollback_storm_escalations_total", 1)
                        except Exception:
                            pass
            except Exception:
                pass

    try:
        from module_provenance import append_event, create_event

        ev = create_event(
            "resolution_executed",
            {
                "target_ids": [rid] if rid else [],
                "task": dict(task),
                "validation": dict(validation),
            },
            prev_hash=_last_event_id(prov),
            timestamp=now_ts(deterministic_mode=deterministic_mode, deterministic_time=deterministic_time),
        )
        prov = append_event(prov, ev)
        task["executed_event_id"] = str(ev.get("event_id") or "")
    except Exception:
        pass

    return task, prov


def recompute_inference(*, record: StoredRecord, compute_fn: Callable[[list[str]], Any]) -> StoredRecord:
    new_value = compute_fn(list(record.get("inputs") or []))
    record["value"] = new_value
    return record
