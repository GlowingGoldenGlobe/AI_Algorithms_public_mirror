"""Integrated top-tier AI Brain module for 3D software runtime control.

This module owns two connected responsibilities:
1. start required 3D simulation software (currently Blender)
2. monitor whether required software from a JSON registry is running

The external start daemon/orchestrator remains separate; it starts the AI Brain,
while this module owns Blender runtime intent and health within the AI Brain.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from module_storage import _atomic_write_json, _now_ts, resolve_path, safe_join, store_information
from module_tools import sanitize_id

__all__ = [
    "default_registry_path",
    "load_software_registry",
    "run_3d_simulation_software_cycle",
    "run_3d_simulation_software_daemon",
]

_REPO_ROOT = Path(__file__).resolve().parent


def default_registry_path() -> str:
    return str(_REPO_ROOT / "AI_Brain" / "software_runtime_registry.json")


def _status_latest_path() -> str:
    return safe_join(resolve_path("temporary"), "software_runtime_status_latest.json")


def _alert_latest_path() -> str:
    return safe_join(resolve_path("temporary"), "software_runtime_alert_latest.json")


def _status_history_path() -> str:
    return safe_join(resolve_path("active"), os.path.join("Observability", "software_runtime_status_history.jsonl"))


def _alert_history_path() -> str:
    return safe_join(resolve_path("active"), os.path.join("Observability", "software_runtime_alert_history.jsonl"))


def _sanitize_runtime_id(value: str, *, default: str) -> str:
    cleaned = str(sanitize_id(str(value or ""))).strip("_")
    return cleaned or default


def _append_jsonl(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def load_software_registry(registry_path: str | None = None) -> Dict[str, Any]:
    path = str(registry_path or default_registry_path())
    payload = _read_json(path)
    software = payload.get("software")
    if not isinstance(software, list):
        payload["software"] = []
    payload["registry_path"] = path
    payload.setdefault("version", "1.0")
    return payload


def _process_snapshot() -> List[Dict[str, Any]]:
    if os.name == "nt":
        proc = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        rows: List[Dict[str, Any]] = []
        reader = csv.reader(io.StringIO(proc.stdout or ""))
        for row in reader:
            if len(row) < 2:
                continue
            image_name = str(row[0] or "").strip()
            pid_raw = str(row[1] or "").strip()
            try:
                pid = int(pid_raw)
            except ValueError:
                pid = None
            rows.append({"name": image_name, "pid": pid})
        return rows
    proc = subprocess.run(
        ["ps", "-A", "-o", "pid=,comm="],
        capture_output=True,
        text=True,
        timeout=10,
    )
    rows = []
    for line in str(proc.stdout or "").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            pid = None
        rows.append({"name": parts[1], "pid": pid})
    return rows


def _matching_processes(process_names: List[str], snapshot: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lowered = {str(name).strip().lower() for name in process_names if isinstance(name, str) and name.strip()}
    matches: List[Dict[str, Any]] = []
    for row in snapshot:
        image_name = str(row.get("name") or "").strip().lower()
        if image_name in lowered:
            matches.append({"name": row.get("name"), "pid": row.get("pid")})
    return matches


def _resolve_blender_executable() -> str:
    from module_tools import _load_config

    cfg = _load_config() or {}
    blender_cfg = cfg.get("blender_composition", {}) if isinstance(cfg, dict) else {}
    launcher = blender_cfg.get("launcher", {}) if isinstance(blender_cfg, dict) else {}
    explicit = str(launcher.get("blender_executable") or "").strip()
    if explicit and os.path.isfile(explicit):
        return explicit
    from scripts.blender_composition_receiver import _resolve_blender_executable as _receiver_resolve_blender_executable

    return str(_receiver_resolve_blender_executable(explicit))


def _launch_command_for_entry(entry: Dict[str, Any]) -> List[str]:
    launcher = entry.get("launcher") if isinstance(entry.get("launcher"), dict) else {}
    mode = str(launcher.get("mode") or "command").strip().lower()
    arguments = [str(value) for value in (launcher.get("arguments") or []) if isinstance(value, str)]
    if mode == "blender_config":
        return [_resolve_blender_executable(), *arguments]
    executable = str(launcher.get("executable") or "").strip()
    if not executable:
        raise ValueError(f"software entry {entry.get('software_id')!r} is missing launcher executable")
    return [executable, *arguments]


def _launch_software(entry: Dict[str, Any]) -> Dict[str, Any]:
    command = _launch_command_for_entry(entry)
    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "DETACHED_PROCESS", 0)) | int(
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    proc = subprocess.Popen(
        command,
        cwd=str(_REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return {
        "ok": True,
        "pid": int(proc.pid),
        "command": command,
    }


def _poll_running(entry: Dict[str, Any], *, deadline: float) -> List[Dict[str, Any]]:
    process_names = [str(value) for value in (entry.get("process_names") or []) if isinstance(value, str)]
    while time.time() < deadline:
        matches = _matching_processes(process_names, _process_snapshot())
        if matches:
            return matches
        time.sleep(1.0)
    return []


def _status_row(
    entry: Dict[str, Any],
    *,
    matches: List[Dict[str, Any]],
    launch_result: Dict[str, Any] | None,
    alert_committed: bool,
) -> Dict[str, Any]:
    software_id = _sanitize_runtime_id(str(entry.get("software_id") or ""), default="software")
    return {
        "software_id": software_id,
        "display_name": str(entry.get("display_name") or software_id),
        "required": bool(entry.get("required")),
        "auto_start": bool(entry.get("auto_start")),
        "running": bool(matches),
        "process_names": [str(value) for value in (entry.get("process_names") or []) if isinstance(value, str)],
        "matched_processes": matches,
        "launch_result": launch_result or {"ok": False, "pid": None, "command": None},
        "alert_committed": bool(alert_committed),
        "ts": _now_ts(),
    }


def _should_commit_alert(software_id: str, running: bool, previous_status: Dict[str, Any]) -> bool:
    prior_rows = previous_status.get("software") if isinstance(previous_status.get("software"), list) else []
    prior_running = None
    for row in prior_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("software_id") or "") == software_id:
            prior_running = bool(row.get("running"))
            break
    if running:
        return False
    return prior_running is not False


def _commit_alert(entry: Dict[str, Any], status_row: Dict[str, Any]) -> Dict[str, Any]:
    software_id = str(status_row.get("software_id") or "software")
    payload = {
        "alert_kind": "required_software_not_running",
        "software_id": software_id,
        "display_name": status_row.get("display_name"),
        "required": bool(status_row.get("required")),
        "running": False,
        "matched_processes": [],
        "ts": _now_ts(),
    }
    _atomic_write_json(_alert_latest_path(), payload)
    _append_jsonl(_alert_history_path(), payload)
    store_information(f"software_runtime_alert_{software_id}", payload, "event")
    return payload


def run_3d_simulation_software_cycle(
    *,
    registry_path: str | None = None,
    auto_start: bool = True,
) -> Dict[str, Any]:
    registry = load_software_registry(registry_path)
    entries = registry.get("software") if isinstance(registry.get("software"), list) else []
    previous_status = _read_json(_status_latest_path())
    rows: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        process_names = [str(value) for value in (entry.get("process_names") or []) if isinstance(value, str)]
        matches = _matching_processes(process_names, _process_snapshot())
        launch_result = None
        if (
            bool(entry.get("required"))
            and bool(entry.get("auto_start"))
            and auto_start
            and not matches
        ):
            try:
                launch_result = _launch_software(entry)
                grace_sec = int(
                    (
                        entry.get("launcher")
                        if isinstance(entry.get("launcher"), dict)
                        else {}
                    ).get("startup_grace_sec")
                    or 15
                )
                matches = _poll_running(entry, deadline=time.time() + max(1, grace_sec))
            except Exception as exc:
                launch_result = {
                    "ok": False,
                    "pid": None,
                    "command": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        software_id = _sanitize_runtime_id(str(entry.get("software_id") or ""), default="software")
        commit_alert = bool(entry.get("required")) and _should_commit_alert(
            software_id,
            bool(matches),
            previous_status,
        )
        row = _status_row(
            entry,
            matches=matches,
            launch_result=launch_result,
            alert_committed=commit_alert,
        )
        rows.append(row)
        if commit_alert:
            alerts.append(_commit_alert(entry, row))

    payload = {
        "ok": True,
        "registry_path": str(registry.get("registry_path") or default_registry_path()),
        "software": rows,
        "alert_count": len(alerts),
        "ts": _now_ts(),
    }
    _atomic_write_json(_status_latest_path(), payload)
    _append_jsonl(_status_history_path(), payload)
    return payload


def run_3d_simulation_software_daemon(
    *,
    registry_path: str | None = None,
    interval_sec: float = 15.0,
    auto_start: bool = True,
    once: bool = False,
) -> Dict[str, Any]:
    interval = max(1.0, float(interval_sec))
    latest = run_3d_simulation_software_cycle(registry_path=registry_path, auto_start=auto_start)
    while not once:
        time.sleep(interval)
        latest = run_3d_simulation_software_cycle(registry_path=registry_path, auto_start=auto_start)
    return latest


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the integrated 3D simulation software module.")
    ap.add_argument("--registry-path", default=None)
    ap.add_argument("--interval-sec", type=float, default=15.0)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-auto-start", action="store_true")
    args = ap.parse_args(argv)

    payload = run_3d_simulation_software_daemon(
        registry_path=args.registry_path,
        interval_sec=float(args.interval_sec),
        auto_start=not bool(args.no_auto_start),
        once=bool(args.once),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
