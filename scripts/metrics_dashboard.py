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
from typing import Any, Dict, Tuple


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

    def _extract_3d_metrics() -> Tuple[Dict[str, float], Dict[str, Any]]:
        snapshot: Dict[str, float] = {
            "3d_calls_total": float(metrics.get("3d_calls_total", 0.0)),
            "3d_failures_total": float(metrics.get("3d_failures_total", 0.0)),
            "3d_latency_ms_total": float(metrics.get("3d_latency_ms_total", 0.0)),
            "3d_cache_hits_total": float(metrics.get("3d_cache_hits_total", 0.0)),
            "3d_cache_misses_total": float(metrics.get("3d_cache_misses_total", 0.0)),
        }
        cache_stats: Dict[str, Any] = {"size": 0, "entries": []}
        try:
            from module_ai_brain_bridge import get_3d_metrics, get_cache_stats  # type: ignore

            bridge_metrics = get_3d_metrics()
            for key in snapshot:
                if key in bridge_metrics:
                    snapshot[key] = float(bridge_metrics[key])
            cache_stats = get_cache_stats()
        except Exception:
            pass
        size = cache_stats.get("size") if isinstance(cache_stats, dict) else None
        if isinstance(size, int):
            snapshot.setdefault("3d_cache_size", float(size))
        else:
            snapshot.setdefault("3d_cache_size", 0.0)
        snapshot.setdefault("3d_cache_hits_total", 0.0)
        snapshot.setdefault("3d_cache_misses_total", 0.0)
        return snapshot, cache_stats if isinstance(cache_stats, dict) else {"size": None, "entries": []}

    three_d_metrics, cache_snapshot = _extract_3d_metrics()

    def gf(key: str) -> float:
        try:
            return float(metrics.get(key, 0.0))
        except Exception:
            return 0.0

    adaptive_used = gf("resolution_adaptive_used_total")
    adaptive_samples = gf("resolution_adaptive_samples_total")
    adaptive_early = gf("resolution_adaptive_early_stop_total")
    fixed_samples_total = gf("resolution_fixed_samples_total")
    parameter_used_total = gf("parameter_events_used_total")
    parameter_available_total = gf("parameter_events_available_total")

    avg_adaptive_n = (adaptive_samples / adaptive_used) if adaptive_used > 0 else 0.0
    early_stop_rate = (adaptive_early / adaptive_used) if adaptive_used > 0 else 0.0
    param_util = (parameter_used_total / parameter_available_total) if parameter_available_total > 0 else 0.0

    if bool(args.json):
        out = {
            "path": path,
            "adaptive_used_total": int(adaptive_used),
            "adaptive_avg_n": round(avg_adaptive_n, 6),
            "adaptive_early_stop_rate": round(early_stop_rate, 6),
            "fixed_samples_total": int(fixed_samples_total),
            "parameter_events_used_total": int(parameter_used_total),
            "parameter_events_available_total": int(parameter_available_total),
            "parameter_events_utilization_rate": round(param_util, 6),
            "3d_calls_total": int(three_d_metrics.get("3d_calls_total", 0.0)),
            "3d_cache_hits_total": int(three_d_metrics.get("3d_cache_hits_total", 0.0)),
            "3d_cache_misses_total": int(three_d_metrics.get("3d_cache_misses_total", 0.0)),
            "3d_cache_size": int(three_d_metrics.get("3d_cache_size", 0.0)),
        }
        print(json.dumps(out, sort_keys=True))
    else:
        print("metrics_dashboard")
        print(f"- path: {path}")
        print(f"- adaptive_used_total: {int(adaptive_used)}")
        print(f"- adaptive_avg_n: {avg_adaptive_n:.2f}")
        print(f"- adaptive_early_stop_rate: {early_stop_rate:.3f}")
        print(f"- fixed_samples_total: {int(fixed_samples_total)}")
        print(f"- parameter_events_used_total: {int(parameter_used_total)}")
        print(f"- parameter_events_available_total: {int(parameter_available_total)}")
        print(f"- parameter_events_utilization_rate: {param_util:.3f}")
        print(f"- 3d_calls_total: {int(three_d_metrics.get('3d_calls_total', 0.0))}")
        print(f"- 3d_cache_hits_total: {int(three_d_metrics.get('3d_cache_hits_total', 0.0))}")
        print(f"- 3d_cache_misses_total: {int(three_d_metrics.get('3d_cache_misses_total', 0.0))}")
        cache_size_val = three_d_metrics.get("3d_cache_size", 0.0)
        print(f"- 3d_cache_size: {int(cache_size_val)}")
        if cache_snapshot.get("entries"):
            newest = cache_snapshot["entries"][-1]
            if isinstance(newest, dict):
                age = newest.get("age_seconds")
                path_info = newest.get("path")
                print(f"- 3d_cache_latest_entry: path={path_info} age={age}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
