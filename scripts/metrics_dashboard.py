"""scripts/metrics_dashboard.py

Print a small dashboard from metrics JSON.

Defaults to reading TemporaryQueue/metrics.json (repo convention).

Usage:
  py -3 scripts/metrics_dashboard.py
  py -3 scripts/metrics_dashboard.py --path TemporaryQueue/metrics.json
    py -3 scripts/metrics_dashboard.py --reports-dir . --metrics-file metrics.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict


# Ensure repo root is importable when running `python scripts/...`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _default_metrics_path() -> str:
    try:
        from module_storage import resolve_path
        from module_tools import safe_join

        return safe_join(resolve_path("temporary"), "metrics.json")
    except Exception:
        # Fallback: best-effort relative path.
        return os.path.join("TemporaryQueue", "metrics.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=None, help="Path to metrics JSON (default: TemporaryQueue/metrics.json)")
    ap.add_argument(
        "--reports-dir",
        default=None,
        help="Directory containing metrics.json (optional; used with --metrics-file)",
    )
    ap.add_argument(
        "--metrics-file",
        default=None,
        help="Metrics filename or path (alias for --path when --reports-dir is not set)",
    )
    ap.add_argument("--json", action="store_true", help="Print dashboard summary as JSON")
    args = ap.parse_args()

    # Backward compatible path resolution:
    # - --path remains the canonical single-arg way.
    # - --metrics-file can be used as an alias.
    # - When --reports-dir is provided, join it with --metrics-file (or default metrics.json).
    if args.path:
        path = str(args.path)
    elif args.reports_dir:
        mf = str(args.metrics_file) if args.metrics_file else "metrics.json"
        path = os.path.join(str(args.reports_dir), mf)
    elif args.metrics_file:
        path = str(args.metrics_file)
    else:
        path = _default_metrics_path()
    if not os.path.exists(path):
        print(f"metrics file not found: {path}")
        return 2

    payload = _load_json(path)
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else payload

    def gf(key: str) -> float:
        try:
            return float(metrics.get(key, 0.0))
        except Exception:
            return 0.0

    adaptive_used = gf("resolution_adaptive_used_total")
    adaptive_samples = gf("resolution_adaptive_samples_total")
    adaptive_early = gf("resolution_adaptive_early_stop_total")
    fixed_samples_total = gf("resolution_fixed_samples_total")

    avg_adaptive_n = (adaptive_samples / adaptive_used) if adaptive_used > 0 else 0.0
    early_stop_rate = (adaptive_early / adaptive_used) if adaptive_used > 0 else 0.0

    if bool(args.json):
        out = {
            "path": path,
            "adaptive_used_total": int(adaptive_used),
            "adaptive_avg_n": round(avg_adaptive_n, 6),
            "adaptive_early_stop_rate": round(early_stop_rate, 6),
            "fixed_samples_total": int(fixed_samples_total),
        }
        print(json.dumps(out, sort_keys=True))
    else:
        print("metrics_dashboard")
        print(f"- path: {path}")
        print(f"- adaptive_used_total: {int(adaptive_used)}")
        print(f"- adaptive_avg_n: {avg_adaptive_n:.2f}")
        print(f"- adaptive_early_stop_rate: {early_stop_rate:.3f}")
        print(f"- fixed_samples_total: {int(fixed_samples_total)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
