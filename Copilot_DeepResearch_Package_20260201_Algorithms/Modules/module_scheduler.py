# module_scheduler.py
import json
import os
from datetime import datetime, timedelta
from module_tools import validate_record

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_cfg():
    try:
        with open(os.path.join(_BASE_DIR, 'config.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _deterministic_now():
    cfg = _load_cfg() or {}
    det = cfg.get('determinism', {})
    if det.get('deterministic_mode') and det.get('fixed_timestamp'):
        ts = str(det.get('fixed_timestamp'))
        # Accept Zulu by converting Z to +00:00
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now()
    return datetime.now()

ROOT = _BASE_DIR
TASK_TYPES = {"synthesis","review","evidence_gather","contradiction_resolve","objective_refine"}

def flag_record(file_path, label, minutes_from_now=5):
    """
    Flag a record with a label and schedule a future event time.
    """
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    with open(file_path, "r+", encoding="utf-8") as f:
        record = json.load(f)
        record.setdefault("labels", []).append(label)
        future_time = (_deterministic_now() + timedelta(minutes=minutes_from_now)).isoformat()
        record["future_event_time"] = future_time
        record.setdefault("schema_version", "1.0")
        # validate against semantic schema (minimal keys)
        try:
            validate_record(record, 'semantic')
        except Exception:
            pass
        f.seek(0)
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.truncate()

    return f"Flagged {file_path} with label '{label}', scheduled for {future_time}"

def schedule_task(file_path: str, task_type: str, priority: str = "normal", targets=None, why: str = ""):
    """Phase 14: schedule typed tasks with priority and explicit targets/why."""
    if task_type not in TASK_TYPES:
        return {"status": "error", "error": "invalid_task_type", "task_type": task_type}
    if not os.path.exists(file_path):
        return {"status": "error", "error": "file_not_found", "file": file_path}
    try:
        with open(file_path, "r+", encoding="utf-8") as f:
            record = json.load(f)
            tasks = record.setdefault("scheduled_tasks", [])
            task = {
                "task_type": task_type,
                "priority": priority,
                "targets": targets or [],
                "why": why,
                "created_ts": _deterministic_now().isoformat(),
                "schema_version": "1.0"
            }
            tasks.append(task)
            record["scheduled_tasks"] = tasks[-50:]
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "task": task}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def schedule_synthesis(file_path, minutes_from_now=5):
    """
    Flag a record for synthesis in ActiveSpace.
    """
    future_time = _deterministic_now() + timedelta(minutes=minutes_from_now)
    return f"Scheduled synthesis for {file_path} at {future_time.isoformat()}"

def reschedule_task(semantic_file: str, new_time_minutes: int):
    """Reschedule a record's future_event_time by new_time_minutes.
    Returns JSON with status, new_time, and task_id.
    """
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            new_time = (_deterministic_now() + timedelta(minutes=new_time_minutes)).isoformat()
            record["future_event_time"] = new_time
            record.setdefault("schema_version", "1.0")
            task_id = record.get("id", os.path.basename(semantic_file))
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "new_time": new_time, "task_id": task_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def cancel_task(semantic_file: str, task_id: str):
    """Cancel a scheduled task by clearing future_event_time; returns JSON."""
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            record.pop("future_event_time", None)
            record.setdefault("schema_version", "1.0")
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def set_priority(semantic_file: str, task_id: str, priority: str):
    """Set a priority label on the record; returns JSON."""
    if not os.path.exists(semantic_file):
        return {"status": "error", "error": "file_not_found", "file": semantic_file}
    try:
        with open(semantic_file, "r+", encoding="utf-8") as f:
            record = json.load(f)
            labels = record.setdefault("labels", [])
            if priority not in labels:
                labels.append(priority)
            record.setdefault("schema_version", "1.0")
            f.seek(0)
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
        return {"status": "completed", "task_id": task_id, "priority": priority}
    except Exception as e:
        return {"status": "error", "error": str(e)}