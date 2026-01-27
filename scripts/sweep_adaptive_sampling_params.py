"""scripts/sweep_adaptive_sampling_params.py

Nightly/staging helper: run a small grid over adaptive sampling parameters and record
agreement vs fixed + sample reduction.

This is intentionally deterministic and bounded.

Output:
- Writes a CSV (default: TemporaryQueue/sweep_results.csv)

Exit codes:
- 0: success
- 2: invalid inputs

Usage:
  py -3 scripts/sweep_adaptive_sampling_params.py
  py -3 scripts/sweep_adaptive_sampling_params.py --out TemporaryQueue/sweep_results.csv

You can keep the grid tiny to respect CI budgets.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys


# Ensure repo root is importable when running `python scripts/...`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _default_out_path() -> str:
    try:
        from module_storage import resolve_path
        from module_tools import safe_join

        return safe_join(resolve_path("temporary"), "sweep_results.csv")
    except Exception:
        return os.path.join("TemporaryQueue", "sweep_results.csv")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="Output CSV path (default: TemporaryQueue/sweep_results.csv)")
    ap.add_argument("--scenarios", default="S1_small_noise,S2_large_outlier")
    ap.add_argument("--n-samples", type=int, default=256)

    # Grid specs (comma-separated lists)
    ap.add_argument("--n-min", default="32")
    ap.add_argument("--n0", default="64")
    ap.add_argument("--n-max", default="256,512")
    ap.add_argument("--multiplier", default="2")
    ap.add_argument("--early-stop-margin", default="0.01")

    ap.add_argument("--max-combos", type=int, default=50, help="Hard cap on grid size")
    args = ap.parse_args()

    compare_path = os.path.join(_REPO_ROOT, "scripts", "compare_adaptive_vs_fixed.py")
    if not os.path.exists(compare_path):
        print("missing compare helper")
        return 2

    def parse_ints(s: str):
        out = []
        for part in str(s).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(int(part))
            except Exception:
                continue
        return out

    def parse_floats(s: str):
        out = []
        for part in str(s).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.append(float(part))
            except Exception:
                continue
        return out

    n_min_list = parse_ints(args.n_min)
    n0_list = parse_ints(args.n0)
    n_max_list = parse_ints(args.n_max)
    mult_list = parse_floats(args.multiplier)
    margin_list = parse_floats(args.early_stop_margin)

    if not (n_min_list and n0_list and n_max_list and mult_list and margin_list):
        print("invalid grid")
        return 2

    out_path = str(args.out) if args.out else _default_out_path()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    spec = importlib.util.spec_from_file_location("compare_adaptive_vs_fixed", compare_path)
    if spec is None or spec.loader is None:
        print("unable to load compare helper")
        return 2
    compare_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare_mod)

    # Build combos.
    combos = []
    for n_min in n_min_list:
        for n0 in n0_list:
            for n_max in n_max_list:
                for gm in mult_list:
                    for m in margin_list:
                        combos.append((n_min, n0, n_max, gm, m))
    if len(combos) > int(args.max_combos):
        combos = combos[: int(args.max_combos)]

    fieldnames = [
        "n_min",
        "n0",
        "n_max",
        "growth_multiplier",
        "early_stop_margin",
        "cases",
        "disagreement_rate",
        "avg_fixed_n",
        "avg_adaptive_n",
        "sample_reduction",
    ]

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for (n_min, n0, n_max, gm, margin) in combos:
            # Call compare module's main by faking argv.
            argv0 = sys.argv
            try:
                sys.argv = [
                    argv0[0],
                    "--scenarios",
                    str(args.scenarios),
                    "--n-samples",
                    str(int(args.n_samples)),
                    "--deterministic",
                    "--adaptive-n-min",
                    str(int(n_min)),
                    "--adaptive-n0",
                    str(int(n0)),
                    "--adaptive-n-max",
                    str(int(n_max)),
                    "--adaptive-growth-multiplier",
                    str(float(gm)),
                    "--adaptive-early-stop-margin",
                    str(float(margin)),
                    "--json",
                ]
                # compare_mod.main prints JSON; capture by temporarily redirecting stdout.
                import io
                import json
                from contextlib import redirect_stdout

                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = compare_mod.main()
                if rc != 0:
                    continue
                payload = json.loads(buf.getvalue().strip() or "{}")
                w.writerow(
                    {
                        "n_min": int(n_min),
                        "n0": int(n0),
                        "n_max": int(n_max),
                        "growth_multiplier": float(gm),
                        "early_stop_margin": float(margin),
                        "cases": int(payload.get("cases") or 0),
                        "disagreement_rate": float(payload.get("disagreement_rate") or 0.0),
                        "avg_fixed_n": float(payload.get("avg_fixed_n") or 0.0),
                        "avg_adaptive_n": float(payload.get("avg_adaptive_n") or 0.0),
                        "sample_reduction": float(payload.get("sample_reduction") or 0.0),
                    }
                )
            except Exception:
                continue
            finally:
                sys.argv = argv0

    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
