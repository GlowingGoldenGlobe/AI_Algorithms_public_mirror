"""scripts/compare_adaptive_vs_fixed.py

Helper: compare adaptive vs fixed Monte Carlo validation.

This is intended for staging/rollout verification:
- Reports decision agreement (task status) across deterministic scenarios.
- Reports sample reduction (avg n) for adaptive vs fixed.

It runs fully in-memory and is deterministic when `--deterministic` is set.

Exit codes:
- 0: success
- 2: invalid inputs

Usage:
  py -3 scripts/compare_adaptive_vs_fixed.py
  py -3 scripts/compare_adaptive_vs_fixed.py --use-config
  py -3 scripts/compare_adaptive_vs_fixed.py --csv TemporaryQueue/sweep_report_summary.csv

Notes:
- This script does NOT modify config.json.
- It does not require metrics.json; it computes n from validation artifacts.

Config (optional, when --use-config is set):
- verifier.adaptive_sampling (for adaptive parameters)
- verifier.p_threshold, verifier.min_effect_size

Env vars (optional, when --use-config is set):
- AI_BRAIN_COMPARE_DETERMINISTIC (0/1)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, Optional


# Ensure repo root is importable when running `python scripts/...`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import module_error_resolution as error_resolution


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _default_config_path() -> str:
    return os.path.join(os.getcwd(), "config.json")


def _load_config(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        return _load_json(path)
    except Exception:
        return {}


def _get_nested(d: Dict[str, Any], keys: list[str]) -> Optional[Any]:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _env_bool(name: str) -> Optional[bool]:
    v = os.environ.get(name)
    if v is None:
        return None
    vv = str(v).strip().lower()
    if vv in {"1", "true", "yes", "y", "on"}:
        return True
    if vv in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _scenario_inputs(scenario_id: str) -> Optional[Dict[str, Any]]:
    sid = str(scenario_id)
    if sid == "S1_small_noise":
        record = {
            "record_id": "r_s1",
            "value": 100.0,
            "context_id": "c",
            "version": 0,
            "uncertainty": {"value": 100.0, "variance": 1e-6, "provenance": {"id": "r"}},
        }
        measurement = {
            "value": 100.01,
            "source_id": "m",
            "timestamp": 0.0,
            "context_id": "c",
            "uncertainty": {"value": 100.01, "variance": 1e-6, "provenance": {"id": "m"}},
        }
        return {"record": record, "measurement": measurement, "strategy": "re_measure"}

    if sid == "S2_large_outlier":
        record = {
            "record_id": "r_s2",
            "value": 10.0,
            "context_id": "c",
            "version": 0,
            "uncertainty": {"value": 10.0, "variance": 1e9, "provenance": {"id": "r"}},
        }
        measurement = {
            "value": 1000.0,
            "source_id": "m",
            "timestamp": 0.0,
            "context_id": "c",
            "uncertainty": {"value": 1000.0, "variance": 1e9, "provenance": {"id": "m"}},
        }
        return {"record": record, "measurement": measurement, "strategy": "re_measure"}

    return None


def _run_resolution_once(
    *,
    record_before: Dict[str, Any],
    measurement: Dict[str, Any],
    resolution_strategy: str,
    deterministic_mode: bool,
    deterministic_time: float,
    n_samples: int,
    alpha: float,
    min_effect_size: float,
    adaptive_sampling: bool,
    adaptive_n_min: int,
    adaptive_n0: Optional[int],
    adaptive_n_max: int,
    adaptive_growth_multiplier: float,
    adaptive_multiplier: float,
    adaptive_early_stop_margin: Optional[float],
) -> Dict[str, Any]:
    store: Dict[str, Dict[str, Any]] = {str(record_before.get("record_id") or ""): dict(record_before)}
    rid = str(record_before.get("record_id") or "")

    def record_lookup_fn(record_id: str) -> Dict[str, Any]:
        return dict(store[record_id])

    def storage_update_fn(rec: Dict[str, Any]) -> None:
        out = dict(rec)
        # Keep uncertainty aligned with measurement during update.
        m_unc = measurement.get("uncertainty") if isinstance(measurement, dict) else None
        if isinstance(m_unc, dict):
            out_unc = dict(m_unc)
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

    task, prov = error_resolution.create_resolution_task(
        error_report=rep,
        resolution_strategy=str(resolution_strategy),
        provenance_log=[],
        deterministic_mode=deterministic_mode,
        deterministic_time=deterministic_time,
    )

    out_task, _ = error_resolution.execute_resolution_task(
        task=task,
        record_lookup_fn=record_lookup_fn,
        measure_fn=measure_fn,
        storage_update_fn=storage_update_fn,
        relink_fn=relink_fn,
        recompute_fn=recompute_fn,
        provenance_log=prov,
        deterministic_mode=deterministic_mode,
        deterministic_time=deterministic_time,
        n_samples=int(n_samples),
        alpha=float(alpha),
        min_effect_size=float(min_effect_size),
        adaptive_sampling=bool(adaptive_sampling),
        adaptive_n_min=int(adaptive_n_min),
        adaptive_n0=adaptive_n0,
        adaptive_n_max=int(adaptive_n_max),
        adaptive_growth_multiplier=float(adaptive_growth_multiplier),
        adaptive_multiplier=float(adaptive_multiplier),
        adaptive_early_stop_margin=adaptive_early_stop_margin,
    )

    status = str(out_task.get("status") or "") if isinstance(out_task, dict) else ""
    v = out_task.get("validation") if isinstance(out_task, dict) else None
    n_used = 0
    if isinstance(v, dict):
        try:
            n_used = int(float(v.get("n", 0)))
        except Exception:
            n_used = 0

    return {"status": status, "n_used": int(n_used), "validation": v}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--use-config", action="store_true")
    ap.add_argument("--config", default=None, help="Path to config.json (default: ./config.json)")
    ap.add_argument("--scenarios", default="S1_small_noise,S2_large_outlier")
    ap.add_argument("--n-samples", type=int, default=256)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--min-effect-size", type=float, default=1e-6)

    # Adaptive knobs (when not using config)
    ap.add_argument("--adaptive-n-min", type=int, default=32)
    ap.add_argument("--adaptive-n0", type=int, default=64)
    ap.add_argument("--adaptive-n-max", type=int, default=256)
    ap.add_argument("--adaptive-multiplier", type=float, default=10.0, help="Decision multiplier")
    ap.add_argument("--adaptive-growth-multiplier", type=float, default=2.0)
    ap.add_argument("--adaptive-early-stop-margin", type=float, default=0.01)

    ap.add_argument("--deterministic", action="store_true", help="Force deterministic execution")
    ap.add_argument("--csv", default=None, help="Write per-scenario comparison rows to CSV")
    ap.add_argument("--json", action="store_true", help="Print summary as JSON")
    args = ap.parse_args()

    deterministic_mode = bool(args.deterministic)
    deterministic_time = 0.0

    # Optional config-driven knobs.
    if bool(args.use_config):
        cfg_path = str(args.config) if args.config else _default_config_path()
        cfg = _load_config(cfg_path)

        det_cfg = _get_nested(cfg, ["determinism", "deterministic_mode"])
        if det_cfg is not None:
            deterministic_mode = bool(det_cfg)

        env_det = _env_bool("AI_BRAIN_COMPARE_DETERMINISTIC")
        if env_det is not None:
            deterministic_mode = bool(env_det)

        vcfg = cfg.get("verifier") if isinstance(cfg, dict) else None
        if isinstance(vcfg, dict):
            try:
                args.alpha = float(vcfg.get("p_threshold", args.alpha))
            except Exception:
                pass
            try:
                args.min_effect_size = float(vcfg.get("min_effect_size", args.min_effect_size))
            except Exception:
                pass

            adapt = vcfg.get("adaptive_sampling")
            if isinstance(adapt, dict):
                try:
                    args.adaptive_n_min = int(adapt.get("n_min", args.adaptive_n_min))
                except Exception:
                    pass
                try:
                    args.adaptive_n0 = int(adapt.get("n0", args.adaptive_n0))
                except Exception:
                    pass
                try:
                    args.adaptive_n_max = int(adapt.get("n_max", args.adaptive_n_max))
                except Exception:
                    pass
                try:
                    args.adaptive_growth_multiplier = float(adapt.get("multiplier", args.adaptive_growth_multiplier))
                except Exception:
                    pass
                try:
                    args.adaptive_early_stop_margin = float(adapt.get("early_stop_margin", args.adaptive_early_stop_margin))
                except Exception:
                    pass

    scenario_ids = [s.strip() for s in str(args.scenarios).split(",") if s.strip()]
    if not scenario_ids:
        print("no scenarios")
        return 2

    rows = []
    disagreements = 0
    total = 0
    n_fixed_total = 0
    n_adaptive_total = 0

    for sid in scenario_ids:
        inp = _scenario_inputs(sid)
        if not isinstance(inp, dict):
            continue

        fixed = _run_resolution_once(
            record_before=dict(inp["record"]),
            measurement=dict(inp["measurement"]),
            resolution_strategy=str(inp["strategy"]),
            deterministic_mode=deterministic_mode,
            deterministic_time=float(deterministic_time),
            n_samples=int(args.n_samples),
            alpha=float(args.alpha),
            min_effect_size=float(args.min_effect_size),
            adaptive_sampling=False,
            adaptive_n_min=int(args.adaptive_n_min),
            adaptive_n0=int(args.adaptive_n0),
            adaptive_n_max=int(args.adaptive_n_max),
            adaptive_growth_multiplier=float(args.adaptive_growth_multiplier),
            adaptive_multiplier=float(args.adaptive_multiplier),
            adaptive_early_stop_margin=float(args.adaptive_early_stop_margin),
        )

        adapt = _run_resolution_once(
            record_before=dict(inp["record"]),
            measurement=dict(inp["measurement"]),
            resolution_strategy=str(inp["strategy"]),
            deterministic_mode=deterministic_mode,
            deterministic_time=float(deterministic_time),
            n_samples=int(args.n_samples),
            alpha=float(args.alpha),
            min_effect_size=float(args.min_effect_size),
            adaptive_sampling=True,
            adaptive_n_min=int(args.adaptive_n_min),
            adaptive_n0=int(args.adaptive_n0),
            adaptive_n_max=int(args.adaptive_n_max),
            adaptive_growth_multiplier=float(args.adaptive_growth_multiplier),
            adaptive_multiplier=float(args.adaptive_multiplier),
            adaptive_early_stop_margin=float(args.adaptive_early_stop_margin),
        )

        fixed_status = str(fixed.get("status") or "")
        adapt_status = str(adapt.get("status") or "")
        disagree = int(fixed_status != adapt_status)

        total += 1
        disagreements += disagree
        n_fixed_total += int(fixed.get("n_used") or 0)
        n_adaptive_total += int(adapt.get("n_used") or 0)

        rows.append(
            {
                "scenario_id": str(sid),
                "fixed_status": fixed_status,
                "adaptive_status": adapt_status,
                "disagree": disagree,
                "fixed_n": int(fixed.get("n_used") or 0),
                "adaptive_n": int(adapt.get("n_used") or 0),
            }
        )

    if total <= 0:
        print("no supported scenarios selected")
        return 2

    disagreement_rate = float(disagreements) / float(total)
    avg_fixed_n = float(n_fixed_total) / float(total)
    avg_adaptive_n = float(n_adaptive_total) / float(total)
    reduction = (1.0 - (avg_adaptive_n / avg_fixed_n)) if avg_fixed_n > 0 else 0.0

    summary = {
        "cases": int(total),
        "disagreements": int(disagreements),
        "disagreement_rate": round(disagreement_rate, 6),
        "avg_fixed_n": round(avg_fixed_n, 6),
        "avg_adaptive_n": round(avg_adaptive_n, 6),
        "sample_reduction": round(reduction, 6),
        "deterministic_mode": bool(deterministic_mode),
        "adaptive": {
            "n_min": int(args.adaptive_n_min),
            "n0": int(args.adaptive_n0),
            "n_max": int(args.adaptive_n_max),
            "growth_multiplier": float(args.adaptive_growth_multiplier),
            "decision_multiplier": float(args.adaptive_multiplier),
            "early_stop_margin": float(args.adaptive_early_stop_margin),
        },
    }

    if args.csv:
        try:
            out_path = str(args.csv)
            out_dir = os.path.dirname(os.path.abspath(out_path))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["scenario_id", "fixed_status", "adaptive_status", "disagree", "fixed_n", "adaptive_n"])
                w.writeheader()
                for r in rows:
                    w.writerow(r)
        except Exception:
            pass

    if bool(args.json):
        print(json.dumps(summary, sort_keys=True))
    else:
        print("compare_adaptive_vs_fixed")
        print(f"- cases: {summary['cases']}")
        print(f"- disagreement_rate: {summary['disagreement_rate']:.3f}")
        print(f"- avg_fixed_n: {summary['avg_fixed_n']:.2f}")
        print(f"- avg_adaptive_n: {summary['avg_adaptive_n']:.2f}")
        print(f"- sample_reduction: {summary['sample_reduction']:.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
