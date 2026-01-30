"""module_hardware_metrics.py

Lightweight hardware/system snapshot helpers.

Goals:
- Dependency-light: uses psutil when available.
- Repo-local: can optionally import the vendored portable package under
  portable_packages/ai_brain_hardware_metrics without requiring pip install.
- Determinism-friendly: callers can include determinism fields alongside the
  wall-clock capture time.

Public API:
- get_hardware_info()

This module intentionally does not run background threads.
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import sys
from typing import Any, Dict, Optional


def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _try_import_portable_monitor() -> Optional[object]:
    """Return a callable that produces a monitor, or None."""
    repo_root = _repo_root()
    src_dir = os.path.join(repo_root, "portable_packages", "ai_brain_hardware_metrics", "src")
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    try:
        from ai_brain_hardware_metrics import create_ai_brain_monitor  # type: ignore

        return create_ai_brain_monitor
    except Exception:
        return None


def _disk_usage_target() -> str:
    # Prefer the drive containing the repo.
    repo = _repo_root()
    if platform.system() == "Windows":
        drive = os.path.splitdrive(repo)[0]
        if drive:
            return drive + os.sep
        return os.path.abspath(os.sep)
    return os.sep


def _windows_memory_info() -> Optional[Dict[str, Any]]:
    """Return Windows memory stats using GlobalMemoryStatusEx.

    Returns dict with total/available/percent or None if unavailable.
    """
    if platform.system() != "Windows":
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_uint32),
            ("dwMemoryLoad", ctypes.c_uint32),
            ("ullTotalPhys", ctypes.c_uint64),
            ("ullAvailPhys", ctypes.c_uint64),
            ("ullTotalPageFile", ctypes.c_uint64),
            ("ullAvailPageFile", ctypes.c_uint64),
            ("ullTotalVirtual", ctypes.c_uint64),
            ("ullAvailVirtual", ctypes.c_uint64),
            ("ullAvailExtendedVirtual", ctypes.c_uint64),
        ]

    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        if not ok:
            return None
        total = int(stat.ullTotalPhys)
        avail = int(stat.ullAvailPhys)
        used = max(0, total - avail)
        pct = float((used / total) * 100.0) if total else None
        return {
            "memory_total": total,
            "memory_available": avail,
            "memory_percent": pct,
        }
    except Exception:
        return None


def _disk_info(target: str) -> Optional[Dict[str, Any]]:
    try:
        usage = shutil.disk_usage(target)
        total = int(usage.total)
        free = int(usage.free)
        used = max(0, total - free)
        pct = float((used / total) * 100.0) if total else None
        return {
            "disk_total": total,
            "disk_free": free,
            "disk_percent": pct,
        }
    except Exception:
        return None


def get_hardware_info(*, fast: bool = False) -> Dict[str, Any]:
    """Get a single-point-in-time system snapshot.

    Returns a dict that always includes:
    - ok: bool
    - platform: str

    When ok is True, includes cpu/memory/disk fields.
    """
    create_monitor = _try_import_portable_monitor()
    if create_monitor is not None:
        try:
            monitor = create_monitor()
            info = monitor.get_hardware_info() if not fast else monitor.get_system_summary()

            # Supplement portable monitor output with native fallbacks when fields are missing.
            if isinstance(info, dict):
                if info.get("memory_percent") is None or info.get("memory_total") is None:
                    mi = _windows_memory_info()
                    if mi:
                        info.setdefault("memory_total", mi.get("memory_total"))
                        info.setdefault("memory_available", mi.get("memory_available"))
                        info["memory_percent"] = info.get("memory_percent") if info.get("memory_percent") is not None else mi.get("memory_percent")
                if info.get("disk_percent") is None or info.get("disk_total") is None:
                    di = _disk_info(_disk_usage_target())
                    if di:
                        info.setdefault("disk_total", di.get("disk_total"))
                        info.setdefault("disk_free", di.get("disk_free"))
                        info["disk_percent"] = info.get("disk_percent") if info.get("disk_percent") is not None else di.get("disk_percent")

            return {
                "ok": True,
                "platform": str(platform.system()),
                "info": info,
            }
        except Exception as e:
            return {
                "ok": False,
                "platform": str(platform.system()),
                "error": f"portable_monitor_failed: {e}",
            }

    try:
        import psutil  # type: ignore

        cpu_percent = float(psutil.cpu_percent(interval=0.0 if fast else 0.2))
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(_disk_usage_target())
        return {
            "ok": True,
            "platform": str(platform.system()),
            "info": {
                "cpu_percent": cpu_percent,
                "cpu_count": int(psutil.cpu_count() or 0),
                "memory_total": int(mem.total),
                "memory_available": int(mem.available),
                "memory_percent": float(mem.percent),
                "disk_total": int(disk.total),
                "disk_free": int(disk.free),
                "disk_percent": float(disk.percent),
            },
        }
    except Exception as e:
        # Best-effort fallback (Windows) to still support automation gating.
        info: Dict[str, Any] = {}
        mi = _windows_memory_info()
        if mi:
            info.update(mi)
        di = _disk_info(_disk_usage_target())
        if di:
            info.update(di)
        return {
            "ok": bool(info),
            "platform": str(platform.system()),
            "info": info,
            "error": f"psutil_unavailable_or_failed: {e}",
        }
