# module_current_activity.py
import datetime
import json
import os

_current_activity = {}

# Persist activity to top-level ActiveSpace in the current workspace
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ActiveSpace")

def set_activity(activity_id, description):
    # honor deterministic timestamp if configured
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, 'config.json'), 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        det = cfg.get('determinism', {})
        ts = det.get('fixed_timestamp') if det.get('deterministic_mode') else datetime.datetime.now().isoformat()
    except Exception:
        ts = datetime.datetime.now().isoformat()
    _current_activity[activity_id] = {
        "description": description,
        "timestamp": ts
    }

def get_activity():
    return _current_activity

def persist_activity():
    """
    Write the current activity log to ActiveSpace\activity.json.
    """
    os.makedirs(ROOT, exist_ok=True)
    path = os.path.join(ROOT, "activity.json")
    # Read existing log to append runs rather than overwrite
    existing = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as rf:
                existing = json.load(rf)
        except Exception:
            existing = {}
    # Merge current activity entries
    # ensure cycles array and last_cycle_ts for relational_measure
    # merge basic entries
    existing.update(_current_activity)
    try:
        rel = existing.get('relational_measure', {})
        desc = rel.get('description')
        if isinstance(desc, str):
            try:
                payload = json.loads(desc)
            except Exception:
                payload = {}
        elif isinstance(desc, dict):
            payload = desc
        else:
            payload = {}
        cycle_ts = payload.get('cycle_ts')
        cycles = existing.get('cycles') or []
        if payload:
            cycles.append(payload)
        existing['cycles'] = cycles[-200:]
        if cycle_ts:
            existing['last_cycle_ts'] = cycle_ts
    except Exception:
        pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    return f"Activity log persisted to {path}"

def log_collector_run(run_summary: dict):
    """Append a collector_runs entry to ActiveSpace/activity.json."""
    os.makedirs(ROOT, exist_ok=True)
    path = os.path.join(ROOT, "activity.json")
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as rf:
                data = json.load(rf)
        except Exception:
            data = {}
    runs = data.get("collector_runs", [])
    # honor deterministic timestamp if configured
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, 'config.json'), 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        det = cfg.get('determinism', {})
        ts = det.get('fixed_timestamp') if det.get('deterministic_mode') else datetime.datetime.now().isoformat()
    except Exception:
        ts = datetime.datetime.now().isoformat()
    runs.append({"timestamp": ts, **run_summary})
    data["collector_runs"] = runs
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path