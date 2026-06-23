from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _venv_python(root: Path) -> Path:
    return root / ".venv" / "Scripts" / "python.exe"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _pid_alive(pid: Optional[int]) -> bool:
    if not pid or int(pid) <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            return False
        if proc.returncode != 0:
            return False
        line = (proc.stdout or "").strip()
        if not line or line.startswith("INFO:"):
            return False
        # CSV format when /NH: "Image Name","PID","Session Name",...
        # Require that the listed process is a Python interpreter (prevents false-alive on pid reuse by unrelated processes).
        try:
            # strip surrounding quotes and split on "," (accounting for quoted fields)
            cleaned = line.strip().strip('"')
            parts = cleaned.split('","')
            image = (parts[0] if parts else "").strip().lower()
            if "python" not in image:
                return False
        except Exception:
            # If parse fails but we got a non-empty non-INFO line, fall back to accepting (defensive).
            pass
        return True
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _status_snapshot(root: Path, python_exe: str, config_path: Path) -> Dict[str, Any]:
    proc = subprocess.run(
        [
            python_exe,
            str(root / "project_orchestrator.py"),
            "--config",
            str(config_path),
            "status",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return {
            "ok": False,
            "returncode": int(proc.returncode),
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    try:
        data = json.loads((proc.stdout or "").strip() or "{}")
    except Exception:
        return {
            "ok": False,
            "returncode": 0,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    return data if isinstance(data, dict) else {}


def _status_runtime_details(status: Dict[str, Any]) -> Dict[str, Any]:
    lock_path = Path(str(status.get("lock_path") or "")) if status.get("lock_path") else None
    runtime_status_path = Path(str(status.get("runtime_status_path") or "")) if status.get("runtime_status_path") else None
    lock_info_path = Path(str(lock_path) + ".info.json") if lock_path else None
    lock_info = _read_json(lock_info_path) if lock_info_path and lock_info_path.exists() else {}
    pid = lock_info.get("pid")
    try:
        pid = int(pid) if pid is not None else None
    except Exception:
        pid = None
    return {
        "lock_path": str(lock_path) if lock_path else "",
        "lock_info_path": str(lock_info_path) if lock_info_path else "",
        "runtime_status_path": str(runtime_status_path) if runtime_status_path else "",
        "lock_info": lock_info,
        "pid": pid,
        "pid_alive": _pid_alive(pid),
        "runtime_status_exists": bool(runtime_status_path and runtime_status_path.exists()),
    }


def _detached_creationflags() -> int:
    if os.name != "nt":
        return 0
    new_console = int(getattr(subprocess, "CREATE_NEW_CONSOLE", 0) or 0)
    new_group = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) or 0)
    breakaway = int(getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0) or 0)
    return new_console | new_group | breakaway


def _popen_detached(argv: list[str], cwd: Path, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        env = os.environ.copy()
        env["AI_BRAIN_FORCE_TTY"] = "1"
        subprocess.Popen(
            argv,
            cwd=str(cwd),
            creationflags=_detached_creationflags(),
            close_fds=False,
            env=env,
        )
        return
    with log_path.open("ab") as log_file:
        subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdout=log_file,
            stderr=log_file,
            creationflags=_detached_creationflags(),
            close_fds=True,
        )


def _wait_for_orchestrator(root: Path, python_exe: str, config_path: Path, previous_pid: Optional[int], wait_sec: float) -> Dict[str, Any]:
    deadline = time.time() + max(0.25, float(wait_sec))
    last_status: Dict[str, Any] = {}
    while time.time() < deadline:
        status = _status_snapshot(root, python_exe, config_path)
        details = _status_runtime_details(status)
        last_status = {
            "status": status,
            "details": details,
        }
        current_pid = details.get("pid")
        if details.get("pid_alive") and current_pid and current_pid != previous_pid:
            return last_status
        time.sleep(0.2)
    return last_status


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Start the AI_Algorithms orchestrator in a detached way.")
    parser.add_argument("--config", default="orchestrator_config.json")
    parser.add_argument("--wait-sec", type=float, default=5.0)
    args = parser.parse_args(argv)

    root = _repo_root()
    venv_py = _venv_python(root)
    python_exe = str(venv_py if venv_py.exists() else Path(sys.executable))
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()

    status_before = _status_snapshot(root, python_exe, config_path)
    details_before = _status_runtime_details(status_before)
    if details_before.get("pid_alive"):
        print(
            json.dumps(
                {
                    "ok": True,
                    "already_running": True,
                    "pid": details_before.get("pid"),
                    "lock_path": details_before.get("lock_path"),
                    "runtime_status_path": details_before.get("runtime_status_path"),
                },
                indent=2,
            )
        )
        return 0

    log_name = f"{config_path.stem}_launcher.log" if config_path.stem != "orchestrator_config" else "orchestrator_launcher.log"
    log_path = root / "TemporaryQueue" / "orchestrator" / log_name
    _popen_detached(
        [
            python_exe,
            str(root / "project_orchestrator.py"),
            "--config",
            str(config_path),
            "run",
            "--daemon",
        ],
        cwd=root,
        log_path=log_path,
    )

    started = _wait_for_orchestrator(
        root,
        python_exe,
        config_path,
        details_before.get("pid"),
        float(args.wait_sec),
    )
    details_after = started.get("details") or {}
    if details_after.get("pid_alive"):
        print(
            json.dumps(
                {
                    "ok": True,
                    "already_running": False,
                    "pid": details_after.get("pid"),
                    "lock_path": details_after.get("lock_path"),
                    "runtime_status_path": details_after.get("runtime_status_path"),
                    "launcher_log": str(log_path),
                },
                indent=2,
            )
        )
        return 0

    print(
        json.dumps(
            {
                "ok": False,
                "error": "orchestrator did not become ready within wait window",
                "launcher_log": str(log_path),
                "status": started.get("status") or status_before,
                "details": details_after or details_before,
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
