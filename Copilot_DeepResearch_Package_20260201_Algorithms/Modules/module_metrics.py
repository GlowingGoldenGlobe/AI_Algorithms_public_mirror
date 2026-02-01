"""module_metrics.py

Tiny, dependency-free metrics counters.

This module is intentionally small and deterministic. It keeps metrics in-memory
for lightweight observability during runs and tests.

Public API:
- incr_counter(name, amount=1)
- add_counter(name, amount)
- get_metrics()
- reset_metrics()
- flush_metrics(path=None, category='temporary', filename='metrics.json')
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_METRICS: dict[str, float] = {}


def incr_counter(name: str, amount: float = 1.0) -> None:
    try:
        key = str(name)
    except Exception:
        return
    try:
        inc = float(amount)
    except Exception:
        inc = 1.0
    _METRICS[key] = float(_METRICS.get(key, 0.0) + inc)


def add_counter(name: str, amount: float) -> None:
    incr_counter(name, amount)


def get_metrics() -> Dict[str, Any]:
    return dict(_METRICS)


def reset_metrics() -> None:
    _METRICS.clear()


def flush_metrics(
    *,
    path: Optional[str] = None,
    category: str = "temporary",
    filename: str = "metrics.json",
) -> str:
    """Persist current metrics to disk and return the absolute path.

    - Default target: TemporaryQueue/metrics.json (via module_storage.resolve_path).
    - If `path` is provided, it is treated as a workspace-relative path and is
      validated with `safe_join`.
    - Writes deterministically (sorted keys). Includes determinism info when available.
    """
    try:
        from module_storage import ROOT as _ROOT, resolve_path
        from module_tools import safe_join, _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        deterministic_mode = bool(det.get("deterministic_mode"))
        fixed_timestamp = det.get("fixed_timestamp") if deterministic_mode else None

        if path is not None:
            target_path = safe_join(str(_ROOT), str(path))
        else:
            out_dir = resolve_path(str(category))
            os.makedirs(out_dir, exist_ok=True)
            target_path = safe_join(out_dir, str(filename))

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        payload: Dict[str, Any] = {
            "schema_version": "1.0",
            "deterministic_mode": bool(deterministic_mode),
            "fixed_timestamp": str(fixed_timestamp) if fixed_timestamp else None,
            "metrics": get_metrics(),
        }
        # Atomic write.
        tmp_path = target_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, target_path)
        return str(target_path)
    except Exception:
        return ""
