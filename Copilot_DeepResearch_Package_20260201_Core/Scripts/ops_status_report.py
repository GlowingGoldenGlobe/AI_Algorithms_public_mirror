"""scripts/ops_status_report.py

Write a single operational status JSON file under TemporaryQueue/ops_status.json.

Includes:
- Dashboard server health (/api/ping, port open) and best-effort PID for the port listener
- Live metrics watcher freshness (ai_brain_metrics_live.json age + stop-file)
- Orchestrator paused state (from project_orchestrator.py status)

This is intended for quick diagnostics and for the dashboard UI to display.

Usage:
  .venv/Scripts/python.exe scripts/ops_status_report.py
  .venv/Scripts/python.exe scripts/ops_status_report.py --json

"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _resolve_temporary(repo_root: str) -> str:
    try:
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from module_storage import resolve_path  # type: ignore

        p = str(resolve_path("temporary"))
        if p:
            return p
    except Exception:
        pass
    return os.path.join(repo_root, "TemporaryQueue")


def _atomic_write_json(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True, indent=2)
    os.replace(tmp, path)


def _is_port_open(host: str, port: int, timeout_sec: float) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(float(timeout_sec))
            return s.connect_ex((str(host), int(port))) == 0
    except Exception:
        return False


def _ping(host: str, port: int, timeout_sec: float) -> dict[str, Any]:
    url = f"http://{host}:{int(port)}/api/ping"
    try:
        with urlopen(url, timeout=float(timeout_sec)) as r:
            status = int(getattr(r, "status", 200))
            body = r.read(1024).decode("utf-8", errors="replace")
            return {"ok": status == 200, "status": status, "url": url, "body": body}
    except URLError as e:
        return {"ok": False, "status": None, "url": url, "error": f"URLError: {e}"}
    except Exception as e:
        return {"ok": False, "status": None, "url": url, "error": f"{type(e).__name__}: {e}"}


def _file_stat(path: str) -> dict[str, Any]:
    out: dict[str, Any] = {"path": path, "exists": False}
    if not path or not os.path.isfile(path):
        return out
    out["exists"] = True
    try:
        out["bytes"] = int(os.path.getsize(path))
    except Exception:
        out["bytes"] = None
    try:
        out["mtime"] = float(os.path.getmtime(path))
    except Exception:
        out["mtime"] = None
    return out


def _try_find_listening_pid_windows(port: int) -> int | None:
    try:
        p = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        text = (p.stdout or "") + "\n" + (p.stderr or "")
    except Exception:
        return None

    pid = None
    port_str = f":{int(port)}"
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if "LISTENING" not in s.upper():
            continue
        if port_str not in s:
            continue
        parts = re.split(r"\s+", s)
        if len(parts) < 5:
            continue
        cand = parts[-1]
        if cand.isdigit():
            pid = int(cand)
            break

    return pid


def _try_tasklist_image_name_windows(pid: int) -> str | None:
    try:
        p = subprocess.run(
            ["tasklist", "/fi", f"PID eq {int(pid)}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (p.stdout or "")
    except Exception:
        return None

    # Parse the first data line under the header.
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 3:
        return None
    data = lines[2]
    # Image Name is the first column; split on 2+ spaces.
    parts = re.split(r"\s{2,}", data.strip())
    if not parts:
        return None
    return parts[0] or None


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def _try_read_json_file(path: str) -> dict[str, Any] | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _orchestrator_status(repo_root: str) -> dict[str, Any]:
    py = os.path.join(repo_root, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(py):
        py = sys.executable

    cmd = [
        py,
        os.path.join(repo_root, "project_orchestrator.py"),
        "--config",
        os.path.join(repo_root, "orchestrator_config.json"),
        "status",
    ]

    try:
        p = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=10)
        parsed = _extract_json_object(p.stdout or "")
        paused = None
        if isinstance(parsed, dict):
            if "paused" in parsed:
                paused = parsed.get("paused")
            elif isinstance(parsed.get("state"), dict):
                paused = parsed["state"].get("paused")
        return {
            "ok": p.returncode == 0 and isinstance(parsed, dict),
            "returncode": int(p.returncode),
            "paused": paused,
            "status": parsed,
            "stderr_tail": (p.stderr or "")[-2000:],
            "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "cmd": cmd}


def main() -> int:
    ap = argparse.ArgumentParser(description="Write an operational status JSON file.")
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--timeout-sec", type=float, default=1.5)
    ap.add_argument("--max-live-age-sec", type=float, default=180.0)
    ap.add_argument("--out", default=None, help="Output path (default: TemporaryQueue/ops_status.json)")
    ap.add_argument("--json", action="store_true", help="Also print the JSON payload")
    args = ap.parse_args()

    repo_root = _repo_root()
    temp_dir = _resolve_temporary(repo_root)

    out_path = str(args.out) if args.out else os.path.join(temp_dir, "ops_status.json")

    live_path = os.path.join(temp_dir, "ai_brain_metrics_live.json")
    stop_path = os.path.join(temp_dir, "ai_brain_metrics.stop")
    hw_path = os.path.join(temp_dir, "hardware_preflight.json")

    port_open = _is_port_open(str(args.bind), int(args.port), float(args.timeout_sec))
    ping = _ping(str(args.bind), int(args.port), float(args.timeout_sec)) if port_open else {"ok": False}

    pid = _try_find_listening_pid_windows(int(args.port)) if os.name == "nt" else None
    image = _try_tasklist_image_name_windows(int(pid)) if (os.name == "nt" and pid) else None

    live = _file_stat(live_path)
    stop_file = _file_stat(stop_path)
    hw_file = _file_stat(hw_path)

    hw_summary = None
    if bool(hw_file.get("exists")):
        rep = _try_read_json_file(hw_path)
        if isinstance(rep, dict):
            try:
                hw_summary = {
                    "ts": rep.get("ts"),
                    "ok": rep.get("ok"),
                    "enforce": rep.get("enforce"),
                    "violations": len(rep.get("violations") or []),
                    "disk_free_percent": (rep.get("disk") or {}).get("free_percent"),
                }
            except Exception:
                hw_summary = None

    live_age = None
    if live.get("exists") and live.get("mtime") is not None:
        try:
            live_age = float(time.time()) - float(live["mtime"])
        except Exception:
            live_age = None

    watcher_ok = bool(live.get("exists")) and (live_age is not None) and (live_age <= float(args.max_live_age_sec))
    if bool(stop_file.get("exists")):
        watcher_ok = False

    orch = _orchestrator_status(repo_root)

    payload: dict[str, Any] = {
        "ts": _utc_now_iso(),
        "server": {
            "bind": str(args.bind),
            "port": int(args.port),
            "port_open": bool(port_open),
            "ping": ping,
            "pid": pid,
            "image": image,
        },
        "hardware_preflight": {
            "file": hw_file,
            "summary": hw_summary,
        },
        "watcher": {
            "temp_dir": temp_dir,
            "live": live,
            "live_age_sec": live_age,
            "stop_file": stop_file,
            "ok": bool(watcher_ok),
        },
        "orchestrator": {
            "ok": bool(orch.get("ok")),
            "paused": orch.get("paused"),
        },
    }

    # Overall ops health is primarily about monitoring being up.
    payload["ok"] = bool(payload["server"]["ping"].get("ok")) and bool(payload["watcher"]["ok"])

    _atomic_write_json(out_path, payload)

    if bool(args.json):
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(f"wrote {out_path}")
        print(
            "server: port_open={} ping_ok={} pid={} image={}".format(
                payload["server"]["port_open"],
                payload["server"]["ping"].get("ok", False),
                payload["server"]["pid"],
                payload["server"]["image"],
            )
        )
        print(
            "watcher: ok={} live_age_sec={} stop_file_exists={}".format(
                payload["watcher"]["ok"],
                None if payload["watcher"]["live_age_sec"] is None else round(float(payload["watcher"]["live_age_sec"]), 3),
                payload["watcher"]["stop_file"].get("exists"),
            )
        )
        print(f"orchestrator: paused={payload['orchestrator']['paused']}")
        print(f"ops: ok={payload['ok']}")

    return 0 if bool(payload["ok"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
