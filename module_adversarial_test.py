"""module_adversarial_test.py

Deterministic adversarial test harness for the AI_Algorithms repo.

Design goals:
- Deterministic reports when deterministic_mode is enabled.
- No reliance on persisted workspace state (in-memory records/provenance only).
- Uses existing Think-Deeper modules: error_resolution, retrieval, reasoning, verifier.

Public API:
- run_scenario

Scenarios:
- S1_small_noise
- S2_large_outlier
- S3_context_swap
- S4_poisoned_retrieval
- S5_rollback_storm
- S6_counterfactual_negative_gain
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import module_error_resolution as error_resolution
import module_provenance as provenance
import module_reasoning as reasoning
import module_retrieval as retrieval
import module_verifier as verifier


_GLOBAL_SEED = "adversarial_global_seed_v1"


def stable_seed(obj: Any) -> int:
    """Stable 64-bit seed derived from JSON (deterministic)."""
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = str(obj)
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16], 16)


def _det_time(deterministic_mode: bool) -> float:
    if deterministic_mode:
        return 0.0
    try:
        return float(provenance.now_ts())
    except Exception:
        return 0.0


def _write_report(report: Dict[str, Any], *, scenario_id: str, report_dir: Optional[str]) -> str:
    """Write report JSON to a safe location (no hard-coded absolute paths)."""
    safe_name = "adversarial_report_" + "".join(ch for ch in scenario_id if ch.isalnum() or ch in ("_", "-")) + ".json"
    if report_dir:
        out_dir = report_dir
    else:
        # Default to TemporaryQueue/ (repo convention).
        try:
            from module_storage import resolve_path

            out_dir = resolve_path("temporary")
        except Exception:
            out_dir = os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    try:
        from module_tools import safe_join

        out_path = safe_join(out_dir, safe_name)
    except Exception:
        out_path = os.path.join(out_dir, safe_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True, ensure_ascii=False)
    return out_path


def _write_report_named(report: Dict[str, Any], *, report_name: str, report_dir: Optional[str]) -> str:
    """Write report JSON with a caller-specified filename (sanitized)."""
    base = str(report_name or "report.json")
    if not base.lower().endswith(".json"):
        base = base + ".json"
    safe_name = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "-", "."))
    if not safe_name.lower().endswith(".json"):
        safe_name = safe_name + ".json"
    if report_dir:
        out_dir = report_dir
    else:
        try:
            from module_storage import resolve_path

            out_dir = resolve_path("temporary")
        except Exception:
            out_dir = os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    try:
        from module_tools import safe_join

        out_path = safe_join(out_dir, safe_name)
    except Exception:
        out_path = os.path.join(out_dir, safe_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True, ensure_ascii=False)
    return out_path


def _run_td_resolution(
    *,
    record_before: Dict[str, Any],
    measurement: Dict[str, Any],
    resolution_strategy: str,
    provenance_log: List[Dict[str, Any]],
    deterministic_mode: bool,
    deterministic_time: float,
    n_samples: int = 256,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Run the rollback-capable path entirely in-memory."""

    store: Dict[str, Dict[str, Any]] = {str(record_before.get("record_id") or ""): dict(record_before)}
    rid = str(record_before.get("record_id") or "")

    def record_lookup_fn(record_id: str) -> Dict[str, Any]:
        return dict(store[record_id])

    def storage_update_fn(rec: Dict[str, Any]) -> None:
        out = dict(rec)
        # For adversarial scenarios we treat measurement uncertainty as part of the update.
        # This keeps statistical validation meaningful (before vs after distributions).
        m_unc = measurement.get("uncertainty") if isinstance(measurement, dict) else None
        if isinstance(m_unc, dict):
            out_unc = dict(m_unc)
            # Keep uncertainty mean consistent with the stored value when possible.
            try:
                out_unc["value"] = float(out.get("value"))
            except Exception:
                pass
            out["uncertainty"] = out_unc

        rrid = out.get("record_id") if isinstance(out.get("record_id"), str) else out.get("id")
        if isinstance(rrid, str) and rrid:
            store[rrid] = dict(out)

    def measure_fn(record_id: str) -> Dict[str, Any]:
        m = dict(measurement)
        m.setdefault("record_id", record_id)
        return m

    def relink_fn(rec: Dict[str, Any], new_context_id: str) -> Dict[str, Any]:
        out = dict(rec)
        out["context_id"] = str(new_context_id)
        return out

    def recompute_fn(rec: Dict[str, Any]) -> Dict[str, Any]:
        return dict(rec)

    # Detect error to produce a realistic error_report (schema-compatible with existing module).
    m0 = measure_fn(rid)
    rep = error_resolution.detect_error(measurement=m0, record=record_lookup_fn(rid))
    if not isinstance(rep, dict):
        rep = {
            "target_record_id": rid,
            "error_type": "mis_description",
            "severity": 0.0,
            "measured_value": m0.get("value"),
            "stored_value": record_before.get("value"),
            "delta": 0.0,
            "confidence": 0.5,
            "event_id": "",
        }

    task, prov2 = error_resolution.create_resolution_task(
        error_report=rep,
        resolution_strategy=str(resolution_strategy),
        provenance_log=provenance_log,
        deterministic_mode=deterministic_mode,
        deterministic_time=deterministic_time,
    )

    out_task, prov3 = error_resolution.execute_resolution_task(
        task=task,
        record_lookup_fn=record_lookup_fn,
        measure_fn=measure_fn,
        storage_update_fn=storage_update_fn,
        relink_fn=relink_fn,
        recompute_fn=recompute_fn,
        provenance_log=prov2,
        deterministic_mode=deterministic_mode,
        deterministic_time=deterministic_time,
        n_samples=int(n_samples),
    )

    return out_task, prov3, dict(store.get(rid) or {})


def _scenario_S1(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Small noise with low variance -> should validate (no rollback)."""
    det_t = _det_time(deterministic_mode)

    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    try:
        delta = float(params.get("measurement_delta", 0.01))
    except Exception:
        delta = 0.01
    try:
        variance = float(params.get("variance", 1e-6))
    except Exception:
        variance = 1e-6
    try:
        n_samples = int(params.get("n_samples", 256))
    except Exception:
        n_samples = 256

    record = {
        "record_id": "r_s1",
        "value": 100.0,
        "context_id": "c",
        "version": 0,
        "uncertainty": {"value": 100.0, "variance": variance, "provenance": {"id": "r"}},
    }
    measurement = {
        "value": 100.0 + delta,
        "source_id": "m",
        "timestamp": 0.0,
        "context_id": "c",
        "uncertainty": {"value": 100.0 + delta, "variance": variance, "provenance": {"id": "m"}},
    }

    out_task, prov, after = _run_td_resolution(
        record_before=record,
        measurement=measurement,
        resolution_strategy="re_measure",
        provenance_log=[],
        deterministic_mode=deterministic_mode,
        deterministic_time=det_t,
        n_samples=n_samples,
    )

    return {
        "scenario": "S1",
        "task_status": out_task.get("status"),
        "rolled_back": out_task.get("status") == "rolled_back",
        "record_value_after": after.get("value"),
        "validation": out_task.get("validation") if isinstance(out_task, dict) else None,
        "rollback_reason": out_task.get("rollback_reason") if isinstance(out_task, dict) else None,
        "provenance_event_types": [e.get("event_type") for e in prov if isinstance(e, dict)],
    }


def _scenario_S2(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Large outlier with huge variance -> should become needs_review (no update)."""
    det_t = _det_time(deterministic_mode)

    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    try:
        record_value = float(params.get("record_value", 10.0))
    except Exception:
        record_value = 10.0
    try:
        measurement_value = float(params.get("measurement_value", 1000.0))
    except Exception:
        measurement_value = 1000.0
    try:
        variance = float(params.get("variance", 1e9))
    except Exception:
        variance = 1e9
    try:
        n_samples = int(params.get("n_samples", 128))
    except Exception:
        n_samples = 128

    record = {
        "record_id": "r_s2",
        "value": record_value,
        "context_id": "c",
        "version": 0,
        "uncertainty": {"value": record_value, "variance": variance, "provenance": {"id": "r"}},
    }
    measurement = {
        "value": measurement_value,
        "source_id": "m",
        "timestamp": 0.0,
        "context_id": "c",
        "uncertainty": {"value": measurement_value, "variance": variance, "provenance": {"id": "m"}},
    }

    out_task, prov, after = _run_td_resolution(
        record_before=record,
        measurement=measurement,
        resolution_strategy="re_measure",
        provenance_log=[],
        deterministic_mode=deterministic_mode,
        deterministic_time=det_t,
        n_samples=n_samples,
    )

    return {
        "scenario": "S2",
        "task_status": out_task.get("status"),
        "needs_review": out_task.get("status") == "needs_review",
        "record_value_after": after.get("value"),
        "validation": out_task.get("validation") if isinstance(out_task, dict) else None,
        "provenance_event_types": [e.get("event_type") for e in prov if isinstance(e, dict)],
    }


def _scenario_S3(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Context swap -> classify as mis_association."""
    _ = deterministic_mode
    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    record_ctx = str(params.get("record_context_id", "c2"))
    meas_ctx = str(params.get("measurement_context_id", "c1"))

    record = {"record_id": "r_s3", "value": 1, "context_id": record_ctx, "links": {}, "derived": False, "inputs": []}
    measurement = {"value": 1, "source_id": "m", "timestamp": 0.0, "context_id": meas_ctx}

    et = error_resolution.classify_error(measurement=measurement, record=record)
    return {"scenario": "S3", "classified_error_type": et, "mis_association": et == "mis_association"}


def _scenario_S4(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Poisoned retrieval: conceptual similarity high, objective relevance low."""

    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    try:
        num_docs = int(params.get("num_docs", 3))
    except Exception:
        num_docs = 3
    try:
        objective_link = float(params.get("objective_link", 0.0))
    except Exception:
        objective_link = 0.0

    base_vec = [1.0, 0.0, 0.0]
    store = [
        {
            "record_id": f"adv_poison_{stable_seed(seed_obj)}_{i}",
            "value": i,
            "context_id": "semantic",
            "recurrence": 0.1,
            "objective_links": {"target_obj": objective_link},
            "conceptual_vector": list(base_vec),
            "constraints": {},
        }
        for i in range(max(0, num_docs))
    ]

    query = {
        "objective_id": "target_obj",
        "conceptual_vector": list(base_vec),
        "required_context": "semantic",
        "max_results": 5,
        "deterministic_mode": bool(deterministic_mode),
    }

    rows = retrieval.retrieve_with_scores(store=store, query=query)
    top = rows[0] if rows else None
    explain = top.get("explain_vector") if isinstance(top, dict) else None
    if not isinstance(explain, dict):
        explain = {}

    conc = abs(float(explain.get("conceptual") or 0.0))
    obj = abs(float(explain.get("objective") or 0.0))

    return {
        "scenario": "S4",
        "top_record_id": top.get("record_id") if isinstance(top, dict) else None,
        "conceptual_contrib": conc,
        "objective_contrib": obj,
        "flagged": bool(conc > obj),
    }


def _scenario_S5(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Rollback storm -> repeated rollbacks yield low-confidence escalation."""
    _ = seed_obj
    det_t = _det_time(deterministic_mode)

    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    try:
        base_value = float(params.get("base_value", 10.0))
    except Exception:
        base_value = 10.0
    try:
        base_measurement = float(params.get("base_measurement", 10.1))
    except Exception:
        base_measurement = 10.1
    try:
        delta_per_attempt = float(params.get("delta_per_attempt", 0.01))
    except Exception:
        delta_per_attempt = 0.01
    try:
        variance = float(params.get("variance", 1e6))
    except Exception:
        variance = 1e6
    try:
        n_samples = int(params.get("n_samples", 128))
    except Exception:
        n_samples = 128
    try:
        max_retries = int(params.get("max_retries", 3))
    except Exception:
        max_retries = 3

    record = {
        "record_id": "r_s5",
        "value": base_value,
        "context_id": "c",
        "version": 0,
        # Huge variance makes statistical validation unlikely to pass for moderate changes.
        "uncertainty": {"value": base_value, "variance": variance, "provenance": {"id": "r"}},
    }

    prov: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for attempt in range(max_retries + 1):
        measurement = {
            "value": base_measurement + attempt * delta_per_attempt,
            "source_id": "m",
            "timestamp": 0.0,
            "context_id": "c",
            "uncertainty": {"value": base_measurement, "variance": variance, "provenance": {"id": "m"}},
        }
        out_task, prov, _after = _run_td_resolution(
            record_before=record,
            measurement=measurement,
            resolution_strategy="re_measure",
            provenance_log=prov,
            deterministic_mode=deterministic_mode,
            deterministic_time=det_t,
            n_samples=n_samples,
        )
        failures.append({"attempt": attempt, "status": out_task.get("status"), "confidence": out_task.get("confidence")})

    # Create a deterministic validation artifact and ask the verifier for an action.
    pre = {"ok": True, "evidence": {"checks": [{"name": "scenario", "ok": True}]}, "activity_id": "adv_s5"}
    post = {"ok": False, "evidence": {"checks": [{"name": "rollback_storm", "ok": False}], "statistical_validation": {}}}
    artifact = verifier.generate_validation_artifact(pre=pre, post=post, provenance=prov, deterministic_mode=bool(deterministic_mode))
    action = verifier.escalate_on_failure(artifact=artifact, policy={"confidence_threshold": 0.99})

    return {
        "scenario": "S5",
        "attempts": max_retries + 1,
        "failures": failures,
        "escalation_action": action.get("action"),
        "escalation_reason": action.get("reason"),
    }


def _scenario_S6(seed_obj: Dict[str, Any], deterministic_mode: bool) -> Dict[str, Any]:
    """Counterfactual negative gain -> propose re_evaluate."""
    _ = deterministic_mode

    params = seed_obj.get("params") if isinstance(seed_obj, dict) else None
    params = params if isinstance(params, dict) else {}
    try:
        coherence_gain = float(params.get("coherence_gain", -0.5))
    except Exception:
        coherence_gain = -0.5

    # Counterfactual: force a negative coherence_gain to exercise the
    # "re_evaluate" path deterministically.
    res = {
        "new_record_id": "synth_counterfactual",
        "value": None,
        "conceptual_vector": [],
        "inputs": ["a", "b"],
        "coherence_gain": coherence_gain,
    }
    steps = reasoning.propose_next_steps(synthesis_result=res)

    return {
        "scenario": "S6",
        "coherence_gain": res.get("coherence_gain"),
        "negative_gain": float(res.get("coherence_gain") or 0.0) < 0.0,
        "proposed": list(steps) if isinstance(steps, list) else steps,
        "re_evaluate": isinstance(steps, list) and "re_evaluate" in steps,
    }


_SCENARIO_MAP: Dict[str, Callable[[Dict[str, Any], bool], Dict[str, Any]]] = {
    "S1_small_noise": _scenario_S1,
    "S2_large_outlier": _scenario_S2,
    "S3_context_swap": _scenario_S3,
    "S4_poisoned_retrieval": _scenario_S4,
    "S5_rollback_storm": _scenario_S5,
    "S6_counterfactual_negative_gain": _scenario_S6,
}


def run_scenario(
    scenario_id: str,
    *,
    deterministic_mode: bool = True,
    global_seed: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    write_report: bool = False,
    report_dir: Optional[str] = None,
    report_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a scenario and return a machine-readable report dict."""
    seed = _GLOBAL_SEED if global_seed is None else str(global_seed)
    seed_obj: Dict[str, Any] = {"scenario": str(scenario_id), "seed": seed}
    if isinstance(params, dict) and params:
        seed_obj["params"] = dict(params)

    fn = _SCENARIO_MAP.get(str(scenario_id))
    if not fn:
        return {"error": f"unknown scenario: {scenario_id}", "scenario_id": str(scenario_id)}

    result = fn(seed_obj, bool(deterministic_mode))

    report: Dict[str, Any] = {
        "scenario_id": str(scenario_id),
        "deterministic_mode": bool(deterministic_mode),
        "seed_obj": seed_obj,
        "result": result,
    }

    # Deterministic provenance snapshot when available.
    try:
        prov_ids: List[str] = []
        if isinstance(result, dict):
            # Some scenarios include event types only; keep snapshot empty unless caller needs more.
            pass
        report["provenance_snapshot"] = prov_ids
    except Exception:
        report["provenance_snapshot"] = []

    if write_report:
        if report_name:
            report["report_file"] = _write_report_named(report, report_name=str(report_name), report_dir=report_dir)
        else:
            report["report_file"] = _write_report(report, scenario_id=str(scenario_id), report_dir=report_dir)

    return report
