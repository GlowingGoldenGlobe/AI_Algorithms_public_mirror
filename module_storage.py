import os
import json
from datetime import datetime, timezone
from typing import Any, Dict
from module_tools import validate_record, validate_relational_state, sanitize_id, safe_join, _load_config

# Resolve workspace root dynamically from this file's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = BASE_DIR


def _ensure_relational_state(record: Dict[str, Any]) -> None:
    """Ensure a canonical, empty relational_state exists on the record.

    This is Stage-1 safe: it adds structure but does not change decisions.
    """
    rs = record.get("relational_state")
    if not isinstance(rs, dict):
        rs = {}
        record["relational_state"] = rs
    rs.setdefault("entities", [])
    rs.setdefault("relations", [])
    rs.setdefault("constraints", [])
    rs.setdefault("objective_links", [])
    rs.setdefault("spatial_measurement", None)
    rs.setdefault("decision_trace", {})
    rs.setdefault("focus_snapshot", None)


def _now_ts() -> str:
    """Return a timestamp string.

    - If deterministic mode is enabled, returns the configured fixed timestamp.
    - Otherwise, returns a UTC Zulu timestamp.
    """
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def resolve_path(category: str) -> str:
    """Map category to subdirectory under ROOT."""
    mapping = {
        "temporary": "TemporaryQueue",
        "active": "ActiveSpace",
        "event": os.path.join("LongTermStore", "Events"),
        "semantic": os.path.join("LongTermStore", "Semantic"),
        "procedural": os.path.join("LongTermStore", "Procedural"),
    }
    return os.path.join(ROOT, mapping.get(category, "LongTermStore"))

def _atomic_write_json(target_path: str, data: Dict[str, Any], *, metrics_category: str | None = None) -> None:
    tmp_path = target_path + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Lightweight storage-event metrics (best-effort).
    try:
        from module_metrics import add_counter, incr_counter

        size_bytes = int(os.path.getsize(tmp_path))
        incr_counter("storage_write_count_total", 1.0)
        add_counter("storage_write_bytes_total", float(size_bytes))
        if metrics_category:
            key = str(metrics_category).strip().lower()
            if key:
                incr_counter(f"storage_write_count_{key}", 1.0)
                add_counter(f"storage_write_bytes_{key}", float(size_bytes))
    except Exception:
        pass
    os.replace(tmp_path, target_path)

def _backup_existing(file_path: str) -> None:
    if not os.path.exists(file_path):
        return
    base = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(base, 'LongTermStore', 'Backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = None
    try:
        cfg = _load_config() or {}
        det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
        fixed = det.get('fixed_timestamp') if det.get('deterministic_mode') else None
        if fixed:
            dt = datetime.fromisoformat(str(fixed).replace('Z', '+00:00'))
            ts = dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    except Exception:
        ts = None
    if not ts:
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = os.path.basename(file_path)
    backup_name = f"{name}.{ts}.bak"
    backup_path = os.path.join(backup_dir, backup_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    except Exception:
        pass

def store_information(data_id: str, content, category: str):
    """Store information permanently, increment occurrence count if already exists.
    Includes schema_version, validation, atomic writes, and backups.
    """
    data_id = sanitize_id(data_id)
    path = resolve_path(category)
    os.makedirs(path, exist_ok=True)
    file_path = safe_join(path, f"{data_id}.json")

    schema_name = 'semantic' if category == 'semantic' else ('event' if category == 'event' else 'semantic')

    record = None
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                record = json.load(f)
        except Exception:
            # If an existing record is corrupted (partial write / invalid JSON),
            # preserve a backup and recreate a clean record.
            try:
                _backup_existing(file_path)
            except Exception:
                pass
            try:
                os.remove(file_path)
            except Exception:
                pass
            record = None

    if isinstance(record, dict):
        record["occurrence_count"] = int(record.get("occurrence_count", 0)) + 1
        # ensure category present for schema validation
        record.setdefault("category", category)
        now_ts = _now_ts()
        record.setdefault("timestamps", []).append(now_ts)
        # repetition profile basics
        rp = record.setdefault("repetition_profile", {})
        rp["first_seen_ts"] = rp.get("first_seen_ts") or now_ts
        rp["last_seen_ts"] = now_ts
        # simplistic stability: increase slightly on repeat
        rp["stability_score"] = min(1.0, float(rp.get("stability_score", 0.5)) + 0.05)
        # intervals summary (requires previous timestamp)
        prev_ts = record["timestamps"][max(0, len(record["timestamps"]) - 2)] if len(record["timestamps"]) >= 2 else now_ts
        try:
            from datetime import datetime as _dt
            dt_prev = _dt.fromisoformat(prev_ts.replace('Z',''))
            dt_now = _dt.fromisoformat(now_ts.replace('Z',''))
            interval_sec = int((dt_now - dt_prev).total_seconds())
            arr = rp.setdefault("intervals_sec", [])
            arr.append(interval_sec)
            if len(arr) > 20:
                arr[:] = arr[-20:]
            rp["intervals_summary"] = {
                "min": min(arr) if arr else 0,
                "avg": (sum(arr)/len(arr)) if arr else 0,
                "max": max(arr) if arr else 0
            }
        except Exception:
            pass
        # contradictions registry stub
        record.setdefault("contradictions", [])
        record.setdefault("schema_version", "1.0")

        if schema_name == 'semantic':
            _ensure_relational_state(record)
            if not validate_relational_state(record.get('relational_state')):
                return f"Validation failed for relational_state: {data_id}"
        # description upgrade (simple merge)
        try:
            from module_tools import describe
            desc = describe(content, context=None)
            prev = record.get("description", {})
            # merge claims (unique by tuple)
            prev_claims = {(c.get('subject'), c.get('predicate'), c.get('object')) for c in prev.get('claims', [])}
            new_claims = [c for c in desc.get('claims', []) if (c.get('subject'), c.get('predicate'), c.get('object')) not in prev_claims]
            prev.setdefault('claims', []).extend(new_claims)
            record["description"] = prev
            record["description_ts"] = now_ts
        except Exception:
            pass
        _backup_existing(file_path)
        if not validate_record(record, schema_name):
            return f"Validation failed for existing record: {data_id}"
        _atomic_write_json(file_path, record, metrics_category=category)
        # incremental index update for semantic records
        if category == 'semantic':
            try:
                from module_tools import build_semantic_index
                build_semantic_index()
            except Exception:
                pass
    else:
        record = {
            "id": data_id,
            "category": category,
            "content": content,
            "occurrence_count": 1,
            "timestamps": [_now_ts()],
            "labels": [],
            "schema_version": "1.0"
        }

        if schema_name == 'semantic':
            _ensure_relational_state(record)
            if not validate_relational_state(record.get('relational_state')):
                return f"Validation failed for relational_state: {data_id}"
        # initial description
        try:
            from module_tools import describe
            record["description"] = describe(content, context=None)
            record["description_ts"] = record["timestamps"][0]
        except Exception:
            pass
        if isinstance(content, dict):
            provenance = {
                "run_id": content.get("run_id"),
                "module": content.get("module")
            }
            record["metadata"] = {
                "source_chain": content.get("source_chain", []),
                "labels": content.get("tags", []),
                "provenance": provenance
            }
        else:
            # minimal provenance when content is primitive
            record["metadata"] = {
                "source_chain": [],
                "labels": [],
                "provenance": {"run_id": None, "module": None}
            }
        if not validate_record(record, schema_name):
            return f"Validation failed for new record: {data_id}"
        _atomic_write_json(file_path, record, metrics_category=category)
        if category == 'semantic':
            try:
                from module_tools import build_semantic_index
                build_semantic_index()
            except Exception:
                pass

    return f"Stored {data_id} in {path}"

def retrieve_information(criteria: str):
    """Retrieve information by criteria (recent, current, or search)."""
    # For simplicity, just demonstrate search in LongTermStore
    search_path = os.path.join(ROOT, "LongTermStore")
    results = []
    for root, _, files in os.walk(search_path):
        for file in files:
            if criteria.lower() in file.lower():
                results.append(os.path.join(root, file))
    return results


def store_and_get_path(data_id: str, content, category: str) -> Dict[str, Any]:
    """Wrapper that stores information and returns a structured status with path.

    Does not change store_information signature for existing callers.
    Returns: {status: 'ok'|'error', path: <file_path>, message: <text>}
    """
    try:
        msg = store_information(data_id, content, category)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = safe_join(resolve_path(category), f"{sanitize_id(data_id)}.json")
        status = 'ok' if isinstance(msg, str) and msg.startswith('Stored') else 'ok'
        return {"status": status, "path": path, "message": msg}
    except Exception as e:
        return {"status": "error", "path": None, "message": str(e)}


def _provenance_log_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prov_dir = safe_join(base_dir, os.path.join('LongTermStore', 'Provenance'))
    os.makedirs(prov_dir, exist_ok=True)
    return safe_join(prov_dir, 'provenance_log.json')


def load_provenance_log() -> list[dict[str, Any]]:
    """Load the global provenance log.

    Returns an empty list if missing or unreadable.
    """
    path = _provenance_log_path()
    try:
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return [e for e in data if isinstance(e, dict)]
    except Exception:
        pass
    return []


def save_provenance_log(log: list[dict[str, Any]]) -> None:
    """Persist the global provenance log with atomic write."""
    path = _provenance_log_path()
    tmp_path = path + '.tmp'
    data = [e for e in (log or []) if isinstance(e, dict)]
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)