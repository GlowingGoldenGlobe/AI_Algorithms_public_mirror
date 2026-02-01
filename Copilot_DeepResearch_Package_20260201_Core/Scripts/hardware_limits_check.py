"""scripts/hardware_limits_check.py

Preflight hardware + storage limits check for the AI_Algorithms workspace.

Purpose
- Prevent starting/running the AI Brain when the machine is likely to fail due to
  resource constraints (disk nearly full, low available RAM, runaway directory
  growth).

This script is safe-by-design:
- No network access
- No mutation of core state
- Best-effort; missing dirs are not fatal

Config
- Reads config.json key: hardware_limits

Exit codes
- 0: OK (no violations)
- 3: Violations detected
- 2: Unexpected error

Usage
  .venv/Scripts/python.exe scripts/hardware_limits_check.py
  .venv/Scripts/python.exe scripts/hardware_limits_check.py --json

"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def _ensure_repo_root_on_syspath() -> str:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return repo_root


_REPO_ROOT = _ensure_repo_root_on_syspath()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_config() -> Dict[str, Any]:
    try:
        from module_tools import _load_config as _lc

        cfg = _lc() or {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _resolve_path(category: str, default_rel: str) -> str:
    try:
        from module_storage import resolve_path

        return str(resolve_path(category))
    except Exception:
        return os.path.join(_REPO_ROOT, default_rel)


def _safe_join(base: str, name: str) -> str:
    try:
        from module_tools import safe_join

        return str(safe_join(base, name))
    except Exception:
        return os.path.join(base, name)


def _try_psutil_available_ram_bytes() -> Optional[int]:
    try:
        import psutil  # type: ignore

        return int(getattr(psutil.virtual_memory(), "available"))
    except Exception:
        return None


def _disk_usage(path: str) -> Dict[str, Any]:
    total, used, free = shutil.disk_usage(path)
    free_pct = (float(free) / float(total) * 100.0) if total else 0.0
    return {"total": int(total), "used": int(used), "free": int(free), "free_percent": float(free_pct)}


def _dir_stats_fast(path: str, stop_after_bytes: Optional[int], stop_after_files: Optional[int]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"path": path, "exists": False, "files": 0, "bytes": 0, "truncated": False}
    if not path or not os.path.isdir(path):
        return out
    out["exists"] = True

    files = 0
    total_bytes = 0

    try:
        for root, _dirs, filenames in os.walk(path):
            for fn in filenames:
                files += 1
                fp = os.path.join(root, fn)
                try:
                    total_bytes += int(os.path.getsize(fp))
                except Exception:
                    pass

                if stop_after_files is not None and files > stop_after_files:
                    out["truncated"] = True
                    out["files"] = int(files)
                    out["bytes"] = int(total_bytes)
                    return out

                if stop_after_bytes is not None and total_bytes > stop_after_bytes:
                    out["truncated"] = True
                    out["files"] = int(files)
                    out["bytes"] = int(total_bytes)
                    return out
    except Exception:
        # Best-effort only.
        pass

    out["files"] = int(files)
    out["bytes"] = int(total_bytes)
    return out


def _defaults_for_total_disk(total_disk_bytes: int) -> Dict[str, Any]:
    # Prefer fractional limits so this adapts to different machines.
    # Absolute floors prevent absurdly tiny thresholds on small disks.
    gib = 1024**3
    mib = 1024**2

    def _cap_fraction(frac: float, cap_gib: float) -> Dict[str, Any]:
        return {"max_bytes_fraction_of_disk": float(frac), "max_bytes_cap": int(cap_gib * gib)}

    return {
        "enforce": True,
        "min_free_disk_percent": 5.0,
        "min_free_disk_bytes": int(2 * gib),
        "min_avail_ram_bytes": int(512 * mib),
        "dirs": {
            # High-churn scratch; keep it relatively small.
            "temporary": {"max_files": 50_000, **_cap_fraction(0.02, 5.0)},
            # ActiveSpace is the orchestrator + operational artifacts.
            "active": {"max_files": 200_000, **_cap_fraction(0.05, 10.0)},
            # LongTermStore total (inclusive).
            "holding": {"max_files": 1_000_000, **_cap_fraction(0.80, 200.0)},
            "semantic": {"max_files": 800_000, **_cap_fraction(0.60, 150.0)},
            "procedural": {"max_files": 400_000, **_cap_fraction(0.25, 50.0)},
            "event": {"max_files": 400_000, **_cap_fraction(0.10, 20.0)},
        },
    }


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dicts(out[k], v)
        else:
            out[k] = v
    return out


def _effective_dir_limits(dir_cfg: Dict[str, Any], disk_total: int) -> Dict[str, Any]:
    max_files = dir_cfg.get("max_files")
    max_files_i = int(max_files) if max_files is not None else None

    max_bytes_abs = dir_cfg.get("max_bytes")
    max_bytes_abs_i = int(max_bytes_abs) if max_bytes_abs is not None else None

    frac = dir_cfg.get("max_bytes_fraction_of_disk")
    max_bytes_frac_i: Optional[int] = None
    if frac is not None:
        try:
            frac_f = float(frac)
            if frac_f > 0:
                max_bytes_frac_i = int(disk_total * frac_f)
        except Exception:
            max_bytes_frac_i = None

    cap = dir_cfg.get("max_bytes_cap")
    cap_i = int(cap) if cap is not None else None

    # Combine: start with fraction, then apply cap, then apply explicit max_bytes by taking the minimum.
    max_bytes_eff = max_bytes_frac_i
    if max_bytes_eff is not None and cap_i is not None:
        max_bytes_eff = min(max_bytes_eff, cap_i)
    if max_bytes_eff is None:
        max_bytes_eff = cap_i
    if max_bytes_eff is None:
        max_bytes_eff = max_bytes_abs_i
    elif max_bytes_abs_i is not None:
        max_bytes_eff = min(max_bytes_eff, max_bytes_abs_i)

    return {
        "enabled": bool(dir_cfg.get("enabled", True)),
        "max_files": max_files_i,
        "max_bytes": int(max_bytes_eff) if max_bytes_eff is not None else None,
    }


def check_limits() -> Dict[str, Any]:
    cfg = _load_config()

    repo_root = _REPO_ROOT
    disk = _disk_usage(repo_root)

    defaults = _defaults_for_total_disk(int(disk.get("total") or 0))
    user_cfg = cfg.get("hardware_limits") if isinstance(cfg, dict) else None
    merged = _merge_dicts(defaults, user_cfg) if isinstance(user_cfg, dict) else defaults

    enforce = bool(merged.get("enforce", True))

    # Resolve directories using module_storage mapping.
    paths = {
        "temporary": _resolve_path("temporary", "TemporaryQueue"),
        "active": _resolve_path("active", "ActiveSpace"),
        "holding": _resolve_path("holding", "LongTermStore"),
        "semantic": _resolve_path("semantic", os.path.join("LongTermStore", "Semantic")),
        "procedural": _resolve_path("procedural", os.path.join("LongTermStore", "Procedural")),
        "event": _resolve_path("event", os.path.join("LongTermStore", "Events")),
    }

    # Global checks
    violations: list[Dict[str, Any]] = []

    min_free_pct = merged.get("min_free_disk_percent")
    min_free_bytes = merged.get("min_free_disk_bytes")

    try:
        if min_free_pct is not None and float(disk.get("free_percent") or 0.0) < float(min_free_pct):
            violations.append(
                {
                    "type": "disk_free_percent",
                    "limit": float(min_free_pct),
                    "actual": float(disk.get("free_percent") or 0.0),
                }
            )
    except Exception:
        pass

    try:
        if min_free_bytes is not None and int(disk.get("free") or 0) < int(min_free_bytes):
            violations.append(
                {
                    "type": "disk_free_bytes",
                    "limit": int(min_free_bytes),
                    "actual": int(disk.get("free") or 0),
                }
            )
    except Exception:
        pass

    ram_avail = _try_psutil_available_ram_bytes()
    min_ram = merged.get("min_avail_ram_bytes")
    if min_ram is not None and ram_avail is not None:
        try:
            if int(ram_avail) < int(min_ram):
                violations.append({"type": "ram_available_bytes", "limit": int(min_ram), "actual": int(ram_avail)})
        except Exception:
            pass

    # Directory checks
    dir_reports: Dict[str, Any] = {}
    dir_cfg = merged.get("dirs") if isinstance(merged.get("dirs"), dict) else {}

    for name, path in paths.items():
        cfg_entry = dir_cfg.get(name) if isinstance(dir_cfg, dict) else None
        cfg_entry = cfg_entry if isinstance(cfg_entry, dict) else {}
        eff = _effective_dir_limits(cfg_entry, int(disk.get("total") or 0))

        # Early-stop walk once we exceed limit to keep runtime bounded.
        stop_files = eff.get("max_files")
        stop_bytes = eff.get("max_bytes")

        stats = _dir_stats_fast(path, stop_after_bytes=stop_bytes, stop_after_files=stop_files)

        entry_violations = []
        if bool(eff.get("enabled", True)) and bool(stats.get("exists")):
            if eff.get("max_files") is not None and int(stats.get("files") or 0) > int(eff["max_files"]):
                entry_violations.append(
                    {
                        "type": "dir_max_files",
                        "dir": name,
                        "path": path,
                        "limit": int(eff["max_files"]),
                        "actual": int(stats.get("files") or 0),
                    }
                )
            if eff.get("max_bytes") is not None and int(stats.get("bytes") or 0) > int(eff["max_bytes"]):
                entry_violations.append(
                    {
                        "type": "dir_max_bytes",
                        "dir": name,
                        "path": path,
                        "limit": int(eff["max_bytes"]),
                        "actual": int(stats.get("bytes") or 0),
                    }
                )

        dir_reports[name] = {
            "path": path,
            "exists": bool(stats.get("exists")),
            "files": int(stats.get("files") or 0),
            "bytes": int(stats.get("bytes") or 0),
            "truncated": bool(stats.get("truncated")),
            "limits": eff,
            "violations": entry_violations,
        }

        violations.extend(entry_violations)

    ok = len(violations) == 0

    return {
        "ts": _utc_now_iso(),
        "repo_root": repo_root,
        "ok": bool(ok) if enforce else True,
        "enforce": bool(enforce),
        "disk": disk,
        "ram": {"available": ram_avail, "min_available": int(min_ram) if min_ram is not None else None},
        "dirs": dir_reports,
        "violations": violations,
        "notes": {
            "config_key": "hardware_limits",
            "paths_resolved_via": "module_storage.resolve_path when available",
            "dir_stats": "best-effort os.walk with early-stop at limits",
        },
    }


def _write_back_defaults_if_missing() -> Tuple[bool, Optional[str]]:
    """If hardware_limits missing, write defaults into config.json.

    Returns (changed, error).
    """

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cfg_path = os.path.join(os.path.dirname(base_dir), "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception as e:
        return False, f"cannot read config.json: {e}"

    if isinstance(cfg.get("hardware_limits"), dict):
        return False, None

    disk = _disk_usage(_REPO_ROOT)
    cfg["hardware_limits"] = _defaults_for_total_disk(int(disk.get("total") or 0))

    try:
        tmp = cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, cfg_path)
        try:
            from module_tools import _clear_config_cache

            _clear_config_cache()
        except Exception:
            pass
        return True, None
    except Exception as e:
        return False, f"cannot write config.json: {e}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Preflight hardware + storage limits check")
    ap.add_argument("--json", action="store_true", help="Print full JSON report to stdout")
    ap.add_argument(
        "--out",
        default=None,
        help="Optional path to write the full JSON report (written atomically)",
    )
    ap.add_argument(
        "--init-config-defaults",
        action="store_true",
        help="If config.json lacks hardware_limits, write defaults into it",
    )
    args = ap.parse_args(argv)

    if bool(args.init_config_defaults):
        changed, err = _write_back_defaults_if_missing()
        if err:
            print(json.dumps({"ok": False, "error": err}, indent=2))
            return 2
        if changed:
            print(json.dumps({"ok": True, "changed": True, "message": "wrote hardware_limits defaults"}, indent=2))

    rep = check_limits()

    if getattr(args, "out", None):
        out_path = os.path.abspath(str(args.out))
        try:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            tmp = out_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, out_path)
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"cannot write --out: {e}", "out": out_path}, indent=2))
            return 2

    if bool(args.json):
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        # Stable short output for tasks.
        v = rep.get("violations") or []
        disk = rep.get("disk") or {}
        free_pct = float(disk.get("free_percent") or 0.0)
        free_b = int(disk.get("free") or 0)
        print(
            json.dumps(
                {
                    "ok": bool(rep.get("ok")),
                    "enforce": bool(rep.get("enforce")),
                    "violations": int(len(v)),
                    "disk_free_percent": round(free_pct, 2),
                    "disk_free_bytes": free_b,
                },
                indent=2,
            )
        )

    return 0 if bool(rep.get("ok")) else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
