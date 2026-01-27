"""scripts/adversarial_sweep.py

Repo-native adversarial sweep runner.

- Uses `module_adversarial_test.run_scenario` (real harness).
- Sweeps small parameter grids under a total run budget.
- Writes per-run `adversarial_report_*.json` into an output reports directory.
- Writes `sweep_results.csv` summary for quick analysis.

This is intentionally bounded and deterministic when `--deterministic` is set.

Usage:
  py -3 scripts/adversarial_sweep.py --budget 40
    py -3 scripts/adversarial_sweep.py --out-dir TemporaryQueue/adversarial_sweep --budget 80 --repeats 2
    py -3 scripts/adversarial_sweep.py --grid-file TemporaryQueue/sweep_grid.json

Grid file format (JSON):
{
  "S1_small_noise": {"measurement_delta": [0.01, 0.05], "variance": [1e-6], "n_samples": [128, 256]},
  "S5_rollback_storm": {"max_retries": [2, 3], "variance": [1e5, 1e6]}
}

Exit codes:
- 0: success
- 2: invalid inputs
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Ensure repo root is importable when running `python scripts/...`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import module_adversarial_test as adversarial


def _stable_hex(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = str(obj)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _default_out_dir() -> str:
    try:
        from module_storage import resolve_path
        from module_tools import safe_join

        return safe_join(resolve_path("temporary"), "adversarial_sweep")
    except Exception:
        return os.path.join("TemporaryQueue", "adversarial_sweep")


def _default_grid() -> Dict[str, Dict[str, List[Any]]]:
    # Keep small; budget is enforced anyway.
    return {
        "S1_small_noise": {
            "measurement_delta": [0.005, 0.01, 0.05],
            "variance": [1e-6, 1e-4],
            "n_samples": [64, 128, 256],
        },
        "S2_large_outlier": {
            "record_value": [10.0],
            "measurement_value": [100.0, 1000.0, 10000.0],
            "variance": [1e6, 1e9],
            "n_samples": [64, 128],
        },
        "S3_context_swap": {
            "record_context_id": ["c2"],
            "measurement_context_id": ["c1", "c2"],
        },
        "S4_poisoned_retrieval": {
            "num_docs": [1, 3],
            "objective_link": [0.0, 0.5, 1.0],
        },
        "S5_rollback_storm": {
            "max_retries": [1, 2, 3, 4],
            "variance": [1e4, 1e6],
            "n_samples": [64, 128],
            "delta_per_attempt": [0.01, 0.05],
        },
        "S6_counterfactual_negative_gain": {
            "coherence_gain": [-0.5, -0.1, 0.1],
        },
    }


def _expand_grid(params: Dict[str, List[Any]]) -> Iterable[Dict[str, Any]]:
    keys = list(params.keys())
    if not keys:
        yield {}
        return

    def rec(i: int, cur: Dict[str, Any]):
        if i >= len(keys):
            yield dict(cur)
            return
        k = keys[i]
        vals = params.get(k) if isinstance(params.get(k), list) else []
        if not vals:
            # If empty, treat as default.
            yield from rec(i + 1, cur)
            return
        for v in vals:
            cur[k] = v
            yield from rec(i + 1, cur)

    yield from rec(0, {})


def _expected_pass(scenario_id: str, report: Dict[str, Any]) -> Tuple[str, bool]:
    """Returns (label, ok) based on scenario expectations.

    This treats PASS as "behavior matches scenario intention".
    """

    res = report.get("result") if isinstance(report, dict) else None
    res = res if isinstance(res, dict) else {}

    sid = str(scenario_id)
    if sid == "S1_small_noise":
        rolled_back = bool(res.get("rolled_back") is True)
        return ("no_rollback", not rolled_back)

    if sid == "S2_large_outlier":
        needs_review = bool(res.get("needs_review") is True)
        return ("needs_review", needs_review)

    if sid == "S3_context_swap":
        mis_assoc = bool(res.get("mis_association") is True)
        return ("mis_association", mis_assoc)

    if sid == "S4_poisoned_retrieval":
        flagged = bool(res.get("flagged") is True)
        return ("flagged", flagged)

    if sid == "S5_rollback_storm":
        action = str(res.get("escalation_action") or "")
        return ("needs_review", action == "needs_review")

    if sid == "S6_counterfactual_negative_gain":
        re_eval = bool(res.get("re_evaluate") is True)
        return ("re_evaluate", re_eval)

    return ("unknown", False)


def _extract_n(report: Dict[str, Any]) -> Optional[int]:
    res = report.get("result") if isinstance(report, dict) else None
    res = res if isinstance(res, dict) else {}
    v = res.get("validation") if isinstance(res.get("validation"), dict) else None
    if not isinstance(v, dict):
        return None
    try:
        return int(float(v.get("n")))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=None, help="Output directory (default: TemporaryQueue/adversarial_sweep)")
    ap.add_argument("--grid-file", default=None, help="Optional JSON file containing per-scenario param grids")
    ap.add_argument("--scenarios", default=None, help="Comma-separated scenario ids (default: all)")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--budget", type=int, default=100, help="Max total runs across all scenarios")
    ap.add_argument("--deterministic", action="store_true", help="Force deterministic mode")
    ap.add_argument("--seed-base", default="adv_sweep_seed_v1")
    ap.add_argument("--flush-metrics", action="store_true", help="Flush metrics to TemporaryQueue/metrics.json after sweep")
    args = ap.parse_args()

    out_dir = str(args.out_dir) if args.out_dir else _default_out_dir()
    reports_dir = os.path.join(out_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    if int(args.repeats) < 1 or int(args.budget) < 1:
        print("invalid repeats/budget")
        return 2

    grid = _default_grid()
    if args.grid_file:
        try:
            with open(str(args.grid_file), "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                grid = loaded  # expected: {scenario_id: {param: [vals]}}
        except Exception:
            print("invalid grid file")
            return 2

    scenario_ids: List[str]
    if args.scenarios:
        scenario_ids = [s.strip() for s in str(args.scenarios).split(",") if s.strip()]
    else:
        scenario_ids = [k for k in grid.keys()]

    # Build cells.
    cells: List[Tuple[str, Dict[str, Any]]] = []
    for sid in scenario_ids:
        p = grid.get(sid)
        if not isinstance(p, dict):
            continue
        for combo in _expand_grid({k: v for k, v in p.items() if isinstance(v, list)}):
            cells.append((sid, combo))

    if not cells:
        print("no cells")
        return 2

    total_requested = len(cells) * int(args.repeats)
    repeats = int(args.repeats)
    if total_requested > int(args.budget):
        repeats = max(1, int(args.budget) // max(1, len(cells)))
    if repeats < 1:
        repeats = 1

    # If still too large, trim cells.
    max_cells = max(1, int(args.budget) // repeats)
    cells = cells[:max_cells]

    out_csv = os.path.join(out_dir, "sweep_results.csv")

    fieldnames = [
        "run_id",
        "scenario_id",
        "cell_id",
        "repeat",
        "params",
        "global_seed",
        "deterministic_mode",
        "expectation",
        "passed",
        "n",
        "report_file",
    ]

    run_id = _stable_hex({"seed_base": args.seed_base, "cells": cells, "repeats": repeats})[:12]

    rows: List[Dict[str, Any]] = []
    run_count = 0
    budget = int(args.budget)

    for (cell_index, (sid, params)) in enumerate(cells):
        cell_id = f"{cell_index:04d}"
        for r in range(repeats):
            if run_count >= budget:
                break

            seed_obj = {"seed_base": str(args.seed_base), "scenario_id": sid, "cell_id": cell_id, "repeat": int(r), "params": params}
            global_seed = _stable_hex(seed_obj)[:24]
            report_name = f"adversarial_report_{sid}_{cell_id}_r{r}.json"

            rep = adversarial.run_scenario(
                sid,
                deterministic_mode=bool(args.deterministic),
                global_seed=global_seed,
                params=params,
                write_report=True,
                report_dir=reports_dir,
                report_name=report_name,
            )

            expectation, ok = _expected_pass(sid, rep)
            n_used = _extract_n(rep)

            rows.append(
                {
                    "run_id": run_id,
                    "scenario_id": sid,
                    "cell_id": cell_id,
                    "repeat": int(r),
                    "params": json.dumps(params, sort_keys=True),
                    "global_seed": global_seed,
                    "deterministic_mode": bool(args.deterministic),
                    "expectation": expectation,
                    "passed": bool(ok),
                    "n": "" if n_used is None else int(n_used),
                    "report_file": rep.get("report_file", "") if isinstance(rep, dict) else "",
                }
            )

            run_count += 1

        if run_count >= budget:
            break

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    if bool(args.flush_metrics):
        try:
            from module_metrics import flush_metrics

            flush_metrics()
        except Exception:
            pass

    print(out_dir)
    print(out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
