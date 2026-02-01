# module_objectives.py
import json
import os
from datetime import datetime, timezone

# Use workspace-relative Objectives folder
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LongTermStore", "Objectives")


def _now_ts() -> str:
    """Return a timestamp string.

    - If deterministic mode is enabled, returns the configured fixed timestamp.
    - Otherwise, returns a UTC Zulu timestamp.
    """
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def load_objectives():
    """
    Load all objectives stored as JSON files in the Objectives folder.
    Returns a list of objective records.
    """
    objectives = []
    if os.path.exists(ROOT):
        for file in os.listdir(ROOT):
            if file.endswith(".json"):
                with open(os.path.join(ROOT, file), "r", encoding="utf-8") as f:
                    objectives.append(json.load(f))
    return objectives

def add_objective(obj_id, content, labels=None):
    """
    Add a new objective record to the Objectives folder.
    """
    os.makedirs(ROOT, exist_ok=True)
    path = os.path.join(ROOT, f"{obj_id}.json")
    record = {
        "id": obj_id,
        "content": content,
        "occurrence_count": 1,
        "timestamps": [_now_ts()],
        "labels": labels if labels else ["objective"]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return f"Objective {obj_id} added."

def update_objective(obj_id, new_content=None, new_label=None):
    """
    Update an existing objective: increment occurrence_count, add timestamp,
    optionally update content or add a new label.
    """
    path = os.path.join(ROOT, f"{obj_id}.json")
    if not os.path.exists(path):
        return f"Objective {obj_id} not found."

    with open(path, "r+", encoding="utf-8") as f:
        record = json.load(f)
        record["occurrence_count"] += 1
        record.setdefault("timestamps", []).append(_now_ts())
        if new_content:
            record["content"] = new_content
        if new_label:
            record.setdefault("labels", []).append(new_label)
        f.seek(0)
        json.dump(record, f, indent=2)
        f.truncate()
    return f"Objective {obj_id} updated."

def get_objectives_by_label(label):
    """
    Retrieve objectives that contain a given label.
    """
    objectives = load_objectives()
    return [obj for obj in objectives if label in obj.get("labels", [])]

def get_objective_by_id(obj_id):
    """
    Retrieve a single objective by its ID.
    """
    path = os.path.join(ROOT, f"{obj_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None