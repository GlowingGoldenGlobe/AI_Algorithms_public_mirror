# module_collector.py
import subprocess
import json
import os
import sys
import time
import uuid
from datetime import datetime
import time as _time
try:
    import psutil
except Exception:
    psutil = None

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(_BASE_DIR, "LongTermStore", "ActiveSpace")

CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")


def _det_ts() -> str:
    """Return deterministic fixed timestamp if enabled; else None."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        det = cfg.get('determinism', {})
        if det.get('deterministic_mode') and det.get('fixed_timestamp'):
            return str(det.get('fixed_timestamp'))
    except Exception:
        pass
    return None

def load_collector_config():
    """
    Load collector configuration from config.json.
    Falls back to defaults if section or file is missing.
    """
    defaults = {
        "max_terminals": 8,
        "timeout_seconds": 15,
        "modules_allowlist": [
            "module_measure",
            "module_awareness",
            "ai_brain_measure",
            "search_internet",
            "module_scheduler",
            "module_select",
            "module_storage",
            "module_toggle"
        ],
        "merge_outputs": True,
        "de_dupe": True,
        "history_cap": 50,
        "merge_strategy": "append",
        "dry_run": False,
        "module_timeouts": {},
        "enable_resource_metrics": True,
        "activity_summary_level": "detailed",
        "strategy_overrides": {}
    }

    if not os.path.exists(CONFIG_PATH):
        return defaults

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        collector_cfg = config.get("collector", {})
        return {**defaults, **collector_cfg}
    except Exception:
        return defaults

def _format_output(module, status, output, summary=None, details=None):
    """
    Standardize collector outputs into a consistent schema.
    """
    # determinism support
    fixed_ts = None
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        det = cfg.get('determinism', {})
        if det.get('deterministic_mode'):
            fixed_ts = det.get('fixed_timestamp')
    except Exception:
        fixed_ts = None
    # Ensure details is an object to satisfy schema
    def _as_obj(val):
        if isinstance(val, dict):
            return val
        try:
            # Attempt to parse JSON strings
            if isinstance(val, str):
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            pass
        return {"text": str(val)[:2000]}

    rec = {
        "module": module,
        "status": status,  # "completed", "error", "stderr", etc.
        "timestamp": fixed_ts or datetime.now().isoformat(),
        "summary": summary if summary else str(output)[:80],  # short preview
        "details": _as_obj(details if details is not None else output)  # object per schema
    }
    # ensure schema_version
    rec["schema_version"] = "1.0"
    return rec

def run_module_function(module_name, data_id, content="demo content"):
    """
    Spawn a subprocess to run a real module function.
    Each subprocess executes Python with inline code that imports the module and calls a function.
    """
    code = f"""
import json
from datetime import datetime
import os
BASE = r"{_BASE_DIR}"
try:
    # determinism support inside subproc
    fixed_ts = None
    try:
        with open(r"{CONFIG_PATH}", 'r', encoding='utf-8') as cf:
            _cfg = json.load(cf)
        _det = _cfg.get('determinism', {{}})
        if _det.get('deterministic_mode'):
            fixed_ts = _det.get('fixed_timestamp')
    except Exception:
        fixed_ts = None
    if "{module_name}" == "module_measure":
        from module_measure import measure_information
        try:
            from module_objectives import get_objectives_by_label
            _objectives = get_objectives_by_label("measurement")
        except Exception:
            _objectives = None
        result = measure_information(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"), objectives=_objectives)
    elif "{module_name}" == "module_awareness":
        from module_awareness import validate_response
        result = validate_response("{data_id}")
    elif "{module_name}" == "ai_brain_measure":
        from module_ai_brain_bridge import measure_ai_brain_for_record
        result = measure_ai_brain_for_record(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"))
    elif "{module_name}" == "search_internet":
        from module_tools import search_internet
        result = search_internet("{content}")
    elif "{module_name}" == "module_scheduler":
        from module_scheduler import flag_record
        result = flag_record(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"), "collector-demo", 5)
    elif "{module_name}" == "module_scheduler.reschedule":
        from module_scheduler import reschedule_task
        result = reschedule_task(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"), 10)
    elif "{module_name}" == "module_scheduler.cancel":
        from module_scheduler import cancel_task
        result = cancel_task(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"), "task001")
    elif "{module_name}" == "module_scheduler.priority":
        from module_scheduler import set_priority
        result = set_priority(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"), "task001", "high")
    elif "{module_name}" == "module_select":
        from module_select import select_information
        result = select_information(os.path.join(BASE, "LongTermStore", "Semantic", "{data_id}.json"))
        # Ensure ranking output has reasons
        if isinstance(result, dict) and "ranking" in result:
            for item in result.get("ranking", []):
                item.setdefault("rationale", "auto")
    elif "{module_name}" == "module_storage":
        from module_storage import store_information
        enriched = {{"source": "collector", "tags": ["phase6"], "context": "{content}"}}
        result = store_information("{data_id}", enriched, "semantic")
    elif "{module_name}" == "module_toggle":
        from module_toggle import toggle_information
        result = toggle_information("{data_id}", "semantic")
    else:
        result = f"No-op for {{module_name}}"
    print(json.dumps({{"module":"{module_name}","status":"completed","timestamp":(fixed_ts or datetime.now().isoformat()),"summary":str(result)[:80],"details":result}}))
except Exception as e:
    print(json.dumps({{"module":"{module_name}","status":"error","timestamp":(fixed_ts or datetime.now().isoformat()),"summary":str(e)[:80],"details":str(e)}}))
"""
    return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def collect_results(plan, data_id, content="demo content", timeout_seconds=None):
    """
    Spawn terminals based on plan["terminals"], run assigned modules, and collect standardized outputs.
    """
    os.makedirs(ROOT, exist_ok=True)
    cfg = load_collector_config()
    max_terminals = cfg["max_terminals"]
    timeout_seconds = timeout_seconds or cfg["timeout_seconds"]
    allowlist = cfg["modules_allowlist"]
    merge_outputs = cfg["merge_outputs"]
    de_dupe = cfg.get("de_dupe", True)
    history_cap = cfg.get("history_cap", 50)
    merge_strategy = cfg.get("merge_strategy", "append")
    dry_run = cfg.get("dry_run", False)
    module_timeouts = cfg.get("module_timeouts", {})
    enable_resource_metrics = cfg.get("enable_resource_metrics", True)
    strategy_overrides = cfg.get("strategy_overrides", {})

    results = []
    processes = []
    per_module_start = []

    terminals = min(max_terminals, plan.get("terminals", 1))
    modules = [m for m in plan.get("modules", []) if m in allowlist]

    start_time = time.time()
    run_id = str(uuid.uuid4())

    for i in range(terminals):
        module_name = modules[i % len(modules)] if modules else "noop"
        # Apply per-module merge strategy override
        if module_name in strategy_overrides:
            merge_strategy = strategy_overrides.get(module_name, merge_strategy)
        if dry_run:
            # Simulate a completed output without executing
            simulated = _format_output(module_name, "completed", {"dry_run": True, "data_id": data_id}, summary=f"Dry-run for {module_name}")
            simulated["run_id"] = run_id
            simulated["duration_ms"] = 0
            results.append(simulated)
        else:
            proc = run_module_function(module_name, data_id, content)
            processes.append((proc, module_name))
            per_module_start.append({"module": module_name, "t": time.time()})

    for proc, module_name in processes:
        try:
            # Allow per-module override timeout
            tmo = module_timeouts.get(module_name, timeout_seconds)
            stdout, stderr = proc.communicate(timeout=tmo)
            if stdout:
                try:
                    item = json.loads(stdout.decode().strip())
                    # Coerce details to object per schema
                    if not isinstance(item.get("details"), dict):
                        item["details"] = {"text": str(item.get("details"))[:2000]}
                    item.setdefault("schema_version", "1.0")
                    # add per-module duration
                    start_rec = next((p for p in per_module_start if p["module"] == module_name), None)
                    if start_rec:
                        item["duration_ms"] = int((time.time() - start_rec["t"]) * 1000)
                        fixed_ts = _det_ts()
                        item["start_ts"] = fixed_ts or datetime.fromtimestamp(start_rec["t"]).isoformat()
                        item["end_ts"] = fixed_ts or datetime.now().isoformat()
                        # resource metrics
                        if enable_resource_metrics:
                            cpu_ms = int((_time.process_time() * 1000))
                            mem_kb = 0
                            if psutil:
                                try:
                                    p = psutil.Process(os.getpid())
                                    mem_kb = int(p.memory_info().rss / 1024)
                                except Exception:
                                    mem_kb = 0
                            item["resource_hints"] = {"cpu_time_ms": cpu_ms, "mem_est_kb": mem_kb}
                    item["run_id"] = run_id
                    # validate minimal collector output
                    try:
                        from module_tools import validate_record
                        if not validate_record(item, 'collector_output'):
                            item["status"] = "schema_error"
                    except Exception:
                        pass
                    results.append(item)
                except Exception:
                    results.append(_format_output("unknown", "parse_error", stdout.decode()))
            if stderr:
                results.append(_format_output("unknown", "stderr", stderr.decode()))
        except subprocess.TimeoutExpired:
            results.append(_format_output("unknown", "timeout", "Process exceeded timeout"))

    duration_ms = int((time.time() - start_time) * 1000)

    # Persist results to collector file
    path = os.path.join(ROOT, f"collector_{data_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Build collector summary
    modules_requested = len(modules)
    collector_summary = {
        "modules_launched": terminals,
        "modules_requested": modules_requested,
        "duration_ms": duration_ms,
        "status": "completed" if results else "no_results",
        "run_id": run_id,
        "dry_run": dry_run,
        "merge_strategy": merge_strategy
    }

    # Merge into Semantic record if exists and allowed
    semantic_path = os.path.join(_BASE_DIR, "LongTermStore", "Semantic", f"{data_id}.json")
    if merge_outputs and os.path.exists(semantic_path):
        with open(semantic_path, "r+", encoding="utf-8") as f:
            record = json.load(f)
            outputs = record.setdefault("collector_outputs", [])
            # Merge strategy
            new_outputs = results
            if de_dupe:
                seen = set()
                deduped = []
                for item in new_outputs:
                    key = (item.get("module"), item.get("timestamp"))
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(item)
                new_outputs = deduped

            if merge_strategy == "replace":
                outputs = new_outputs
            elif merge_strategy == "summarize":
                # keep summaries only
                outputs.extend({
                    "module": o.get("module"),
                    "status": o.get("status"),
                    "timestamp": o.get("timestamp"),
                    "summary": o.get("summary"),
                    "details": "summarized"
                } for o in new_outputs)
            else:  # append
                outputs.extend(new_outputs)

            # history cap
            if isinstance(outputs, list) and history_cap and len(outputs) > history_cap:
                outputs = outputs[-history_cap:]
            record["collector_outputs"] = outputs

            metrics = record.setdefault("collector_metrics", {})
            metrics.update({
                "modules_requested": modules_requested,
                "terminals_launched": terminals,
                "duration_ms": duration_ms,
            })
            metrics["collector_runs"] = metrics.get("collector_runs", 0) + 1
            metrics["collector_summary"] = collector_summary
            metrics["resource_hints"] = {"approx_cpu_ms": duration_ms, "modules": modules}
            # Aggregate per-module averages and recent trends
            try:
                per_module = {}
                for o in outputs:
                    if not isinstance(o, dict):
                        continue
                    m = o.get("module") or "unknown"
                    pm = per_module.setdefault(m, {"count": 0, "total_duration_ms": 0, "total_cpu_time_ms": 0, "max_mem_kb": 0})
                    pm["count"] += 1
                    d = o.get("duration_ms")
                    if isinstance(d, (int, float)):
                        pm["total_duration_ms"] += int(d)
                    rh = o.get("resource_hints") or {}
                    cpu = rh.get("cpu_time_ms")
                    if isinstance(cpu, (int, float)):
                        pm["total_cpu_time_ms"] += int(cpu)
                    mem = rh.get("mem_est_kb")
                    if isinstance(mem, (int, float)):
                        pm["max_mem_kb"] = max(pm["max_mem_kb"], int(mem))
                # finalize averages
                for m, pm in per_module.items():
                    c = max(1, pm.get("count", 1))
                    pm["avg_duration_ms"] = int(pm["total_duration_ms"] / c)
                    pm["avg_cpu_time_ms"] = int(pm["total_cpu_time_ms"] / c)
                metrics["per_module"] = per_module
                # recent trend over last N outputs
                N = min(10, len(outputs))
                recent = outputs[-N:] if N else []
                r_count = 0
                r_dur = 0
                r_cpu = 0
                r_mem = 0
                for o in recent:
                    if not isinstance(o, dict):
                        continue
                    d = o.get("duration_ms")
                    if isinstance(d, (int, float)):
                        r_dur += int(d)
                    rh = o.get("resource_hints") or {}
                    cpu = rh.get("cpu_time_ms")
                    if isinstance(cpu, (int, float)):
                        r_cpu += int(cpu)
                    mem = rh.get("mem_est_kb")
                    if isinstance(mem, (int, float)):
                        r_mem = max(r_mem, int(mem))
                    r_count += 1
                metrics["recent"] = {
                    "window": N,
                    "avg_duration_ms": (int(r_dur / r_count) if r_count else 0),
                    "avg_cpu_time_ms": (int(r_cpu / r_count) if r_count else 0),
                    "max_mem_kb": r_mem
                }
            except Exception:
                pass
            f.seek(0)
            # ensure schema_version on semantic record
            record.setdefault("schema_version", "1.0")
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.truncate()
    elif not merge_outputs:
        pass

    # Log to activity
    try:
        from module_current_activity import set_activity, persist_activity, log_collector_run
        set_activity(f"collector_{data_id}", {
            "modules": modules,
            "terminals": terminals,
            "duration_ms": duration_ms,
            "status": collector_summary["status"],
            "run_id": run_id,
            "dry_run": dry_run
        })
        persist_activity()
        log_collector_run({
            "run_id": run_id,
            "data_id": data_id,
            "modules": modules,
            "terminals": terminals,
            "duration_ms": duration_ms,
            "status": collector_summary["status"],
            "merge_strategy": merge_strategy,
            "dry_run": dry_run,
            "resource_hints": {"approx_cpu_ms": duration_ms}
        })
    except Exception:
        pass

    return f"Collector run complete. Results saved to {path}"