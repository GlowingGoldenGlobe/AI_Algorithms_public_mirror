"""module_activity_manager.py

Deterministic multi-activity thinking engine.

Core idea:
- Receive an AwarenessPlan (from module_want.py)
- Transform want signals into executable Activity objects
- Rank numerically by priority
- Execute deterministically by delegating to injected module functions

This module does not require external tools; callers inject execution functions.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable, Literal, Optional, TypedDict


ActivityType = Literal[
    "measure",
    "retrieve",
    "error_resolution",
    "synthesize",
]


class Activity(TypedDict):
    activity_id: str
    activity_type: ActivityType
    targets: list[str]
    priority: float
    metadata: dict[str, Any]


class ActivityPrecondition(TypedDict, total=False):
    type: str
    record_id: str
    min_version: int
    min_ts: float
    key: str
    value: Any


class ResourceBudget(TypedDict, total=False):
    cpu: float
    io: float
    mem: float


class ActivityQueue(TypedDict):
    pending: list[Activity]
    active: list[Activity]
    completed: list[Activity]
    deterministic_mode: bool
    resource_budget: dict[str, float]
    used_resources: dict[str, float]


class AwarenessPlan(TypedDict):
    plan_id: str
    wants: list[dict]
    suggested_activities: list[str]


def _queue_dir() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "ActivityQueue")


def new_queue() -> ActivityQueue:
    return {
        "pending": [],
        "active": [],
        "completed": [],
        "deterministic_mode": False,
        "resource_budget": {"cpu": 1.0, "io": 1.0},
        "used_resources": {"cpu": 0.0, "io": 0.0},
    }


def stable_hash(obj: dict[str, Any]) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def _make_activity_id(*, plan_id: str, activity_type: str, targets: list[str], salt: str = "") -> str:
    """Deterministic id derived from plan_id + type + targets."""
    base = f"{plan_id}|{activity_type}|{'|'.join(targets)}|{salt}"
    h = hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]
    return f"act_{h}"


def translate_wants_to_activities(*, awareness_plan: AwarenessPlan) -> list[Activity]:
    """Convert WantSignals into Activity objects.

    Mapping is a direct transformation:
    - want_information -> retrieve + measure
    - want_error_resolution -> error_resolution
    - want_synthesis -> synthesize

    Strength becomes numeric priority (clamped 0..1).
    """
    plan_id = str(awareness_plan.get('plan_id') or 'plan')
    wants = awareness_plan.get('wants') if isinstance(awareness_plan, dict) else None
    if not isinstance(wants, list):
        return []

    out: list[Activity] = []
    for i, w in enumerate(wants):
        if not isinstance(w, dict):
            continue
        wt = w.get('want_type')
        if wt not in ('want_information', 'want_error_resolution', 'want_synthesis'):
            continue
        targets = w.get('targets')
        if not isinstance(targets, list) or not targets or not all(isinstance(t, str) and t for t in targets):
            continue
        try:
            strength = float(w.get('strength') or 0.0)
        except Exception:
            strength = 0.0
        pr = _clamp01(strength)
        meta = {
            'source_plan_id': plan_id,
            'source_want_type': wt,
            'source_strength': float(pr),
            'source_index': int(i),
        }

        if wt == 'want_information':
            for act_type in ('retrieve', 'measure'):
                aid = _make_activity_id(plan_id=plan_id, activity_type=act_type, targets=targets, salt=str(i))
                out.append(
                    {
                        'activity_id': aid,
                        'activity_type': act_type,  # type: ignore[typeddict-item]
                        'targets': list(targets),
                        'priority': float(pr),
                        'metadata': dict(meta),
                    }
                )
        elif wt == 'want_error_resolution':
            aid = _make_activity_id(plan_id=plan_id, activity_type='error_resolution', targets=targets, salt=str(i))
            out.append(
                {
                    'activity_id': aid,
                    'activity_type': 'error_resolution',
                    'targets': list(targets),
                    'priority': float(pr),
                    'metadata': dict(meta),
                }
            )
        elif wt == 'want_synthesis':
            aid = _make_activity_id(plan_id=plan_id, activity_type='synthesize', targets=targets, salt=str(i))
            out.append(
                {
                    'activity_id': aid,
                    'activity_type': 'synthesize',
                    'targets': list(targets),
                    'priority': float(pr),
                    'metadata': dict(meta),
                }
            )
    return out


def enqueue_activities(*, queue: ActivityQueue, activities: list[Activity]) -> ActivityQueue:
    """Add new activities to queue.pending; de-dupe by activity_id."""
    pending = queue.get('pending') if isinstance(queue, dict) else None
    active = queue.get('active') if isinstance(queue, dict) else None
    completed = queue.get('completed') if isinstance(queue, dict) else None
    if not isinstance(pending, list) or not isinstance(active, list) or not isinstance(completed, list):
        queue = new_queue()
        pending = queue['pending']
        active = queue['active']
        completed = queue['completed']

    existing = set()
    for arr in (pending, active, completed):
        for a in arr:
            if isinstance(a, dict) and isinstance(a.get('activity_id'), str):
                existing.add(a['activity_id'])

    # Deterministic append ordering when deterministic_mode is enabled.
    det = bool(queue.get('deterministic_mode')) if isinstance(queue, dict) else False
    incoming = list(activities or [])
    if det:
        incoming.sort(key=lambda a: str((a or {}).get('activity_id') or ''))

    for a in incoming:
        if not isinstance(a, dict):
            continue
        aid = a.get('activity_id')
        if not isinstance(aid, str) or not aid or aid in existing:
            continue
        pending.append(a)
        existing.add(aid)
    return queue


def prioritize_queue(*, queue: ActivityQueue) -> ActivityQueue:
    """Sort queue.pending by priority desc, then activity_id asc."""
    pending = queue.get('pending') if isinstance(queue, dict) else None
    if not isinstance(pending, list):
        return queue
    pending.sort(key=lambda a: (-float((a or {}).get('priority') or 0.0), str((a or {}).get('activity_id') or '')))
    return queue


def _normalize_cost(cost: Any) -> dict[str, float]:
    if isinstance(cost, dict):
        out: dict[str, float] = {}
        for k, v in cost.items():
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out
    try:
        c = float(cost)
    except Exception:
        c = 0.0
    return {"cpu": float(c)}


def can_allocate_resources(*, queue: ActivityQueue, activity: Activity) -> bool:
    used = queue.get('used_resources') if isinstance(queue, dict) else None
    budget = queue.get('resource_budget') if isinstance(queue, dict) else None
    if not isinstance(used, dict) or not isinstance(budget, dict):
        return True
    cost = _normalize_cost((activity or {}).get('metadata', {}).get('cost', (activity or {}).get('cost', 0.0)))
    for k, v in cost.items():
        try:
            if float(used.get(k, 0.0)) + float(v) > float(budget.get(k, 1.0)):
                return False
        except Exception:
            continue
    return True


def allocate_resources(*, queue: ActivityQueue, activity: Activity) -> None:
    used = queue.get('used_resources') if isinstance(queue, dict) else None
    if not isinstance(used, dict):
        return
    cost = _normalize_cost((activity or {}).get('metadata', {}).get('cost', (activity or {}).get('cost', 0.0)))
    for k, v in cost.items():
        try:
            used[k] = float(used.get(k, 0.0)) + float(v)
        except Exception:
            continue


def release_resources(*, queue: ActivityQueue, activity: Activity) -> None:
    used = queue.get('used_resources') if isinstance(queue, dict) else None
    if not isinstance(used, dict):
        return
    cost = _normalize_cost((activity or {}).get('metadata', {}).get('cost', (activity or {}).get('cost', 0.0)))
    for k, v in cost.items():
        try:
            used[k] = max(0.0, float(used.get(k, 0.0)) - float(v))
        except Exception:
            continue


def precondition_check(
    *,
    activity: Activity,
    verifier_funcs: Optional[dict[str, Callable[[dict[str, Any], dict[str, Any]], tuple[bool, str]]]] = None,
    state: Optional[dict[str, Any]] = None,
) -> tuple[bool, list[str]]:
    """Evaluate preconditions, returning (ok, failure_reasons)."""
    failures: list[str] = []
    meta = activity.get('metadata') if isinstance(activity, dict) else None
    pre = (meta or {}).get('preconditions') if isinstance(meta, dict) else None
    if not isinstance(pre, list) or not pre:
        return (True, failures)

    st = state or {}
    vf = verifier_funcs or {}

    for p in pre:
        if not isinstance(p, dict):
            continue
        ptype = str(p.get('type') or '')
        if ptype == 'record_version':
            rid = str(p.get('record_id') or '')
            try:
                min_v = int(p.get('min_version') or 0)
            except Exception:
                min_v = 0
            recs = st.get('records_map') if isinstance(st, dict) else None
            rec = recs.get(rid) if isinstance(recs, dict) else None
            got_v = 0
            if isinstance(rec, dict):
                try:
                    got_v = int(rec.get('version') or 0)
                except Exception:
                    got_v = 0
            if got_v < min_v:
                failures.append(f"record_version<{min_v}")
        elif ptype == 'measurement_freshness':
            rid = str(p.get('record_id') or '')
            try:
                min_ts = float(p.get('min_ts') or 0.0)
            except Exception:
                min_ts = 0.0
            lmt = st.get('last_measure_ts') if isinstance(st, dict) else None
            got_ts = 0.0
            if isinstance(lmt, dict):
                try:
                    got_ts = float(lmt.get(rid) or 0.0)
                except Exception:
                    got_ts = 0.0
            if got_ts < min_ts:
                failures.append('measurement_not_fresh')
        else:
            fn = vf.get(ptype)
            if callable(fn):
                try:
                    ok, reason = fn(p, st)
                except Exception:
                    ok, reason = (False, 'verifier_exception')
                if not ok:
                    failures.append(str(reason) if reason else 'precondition_failed')
            else:
                # Unknown preconditions are treated as failures to be conservative.
                failures.append(f"unknown_precondition:{ptype}")

    return (len(failures) == 0, failures)


def select_next_activity(
    *,
    queue: ActivityQueue,
    verifier_funcs: Optional[dict[str, Callable[[dict[str, Any], dict[str, Any]], tuple[bool, str]]]] = None,
    state: Optional[dict[str, Any]] = None,
    verifier_module: Optional[Any] = None,
) -> Optional[Activity]:
    """Select and activate next activity.

    Backward compatible: if verifier_funcs/state are not provided, this behaves like the
    original pop-from-pending implementation.
    """
    pending = queue.get('pending') if isinstance(queue, dict) else None
    active = queue.get('active') if isinstance(queue, dict) else None
    if not isinstance(pending, list) or not isinstance(active, list) or not pending:
        return None

    # Ensure deterministic ordering before selection.
    try:
        prioritize_queue(queue=queue)
    except Exception:
        pass

    for idx, act in enumerate(list(pending)):
        if not isinstance(act, dict):
            continue

        # Optional verifier module pre-check (Think-Deeper).
        if verifier_module is not None and hasattr(verifier_module, 'check_preconditions'):
            try:
                pre = verifier_module.check_preconditions(act, state or {})
            except Exception:
                pre = {'ok': False, 'failures': ['verifier_exception'], 'evidence': {}}
            if not bool((pre or {}).get('ok')):
                meta = act.get('metadata')
                if not isinstance(meta, dict):
                    meta = {}
                    act['metadata'] = meta
                meta['verifier_pre'] = pre
                # Mirror failures into the existing failure list for visibility.
                pf = meta.get('precondition_failures')
                if not isinstance(pf, list):
                    pf = []
                    meta['precondition_failures'] = pf
                for r in (pre.get('failures') or []) if isinstance(pre, dict) else []:
                    if isinstance(r, str) and r and r not in pf:
                        pf.append(r)
                continue
        ok, failures = precondition_check(activity=act, verifier_funcs=verifier_funcs, state=state)
        if not ok:
            meta = act.get('metadata')
            if not isinstance(meta, dict):
                meta = {}
                act['metadata'] = meta
            pf = meta.get('precondition_failures')
            if not isinstance(pf, list):
                pf = []
                meta['precondition_failures'] = pf
            for r in failures:
                if isinstance(r, str) and r not in pf:
                    pf.append(r)
            continue
        if not can_allocate_resources(queue=queue, activity=act):
            meta = act.get('metadata')
            if not isinstance(meta, dict):
                meta = {}
                act['metadata'] = meta
            pf = meta.get('precondition_failures')
            if not isinstance(pf, list):
                pf = []
                meta['precondition_failures'] = pf
            if 'insufficient_resources' not in pf:
                pf.append('insufficient_resources')
            continue

        pending.pop(idx)
        active.append(act)
        return act  # type: ignore[return-value]
    return None


def execute_activity(*, activity: Activity, modules: dict[str, Callable[[Activity], Any]]) -> Any:
    """Execute by delegating based on activity_type.

    Expected modules mapping keys:
    - 'measure'
    - 'retrieve'
    - 'error_resolution'
    - 'synthesize'
    """
    at = activity.get('activity_type')
    fn = modules.get(str(at)) if isinstance(modules, dict) else None
    if not callable(fn):
        return {'ok': False, 'reason': 'missing_module', 'activity_type': at}
    return fn(activity)


def execute_activity_with_hooks(
    *,
    activity: Activity,
    modules: dict[str, Callable[[Activity], Any]],
    queue: Optional[ActivityQueue] = None,
    verifier: Optional[Callable[[Activity, dict[str, Any], dict[str, Any]], dict[str, Any]]] = None,
    state: Optional[dict[str, Any]] = None,
    now_ts: Optional[Callable[[], float]] = None,
) -> dict[str, Any]:
    """Execute an activity with optional resource accounting and verifier hooks."""
    ts_fn = now_ts
    if not callable(ts_fn):
        try:
            from module_uncertainty import now_ts as _now

            ts_fn = _now
        except Exception:
            ts_fn = lambda: 0.0

    if isinstance(queue, dict):
        try:
            allocate_resources(queue=queue, activity=activity)
        except Exception:
            pass

    start = float(ts_fn())
    result = execute_activity(activity=activity, modules=modules)
    end = float(ts_fn())

    artifact: dict[str, Any] = {
        'activity_id': str(activity.get('activity_id') or ''),
        'activity_type': str(activity.get('activity_type') or ''),
        'targets': list(activity.get('targets') or []),
        'start_ts': float(start),
        'end_ts': float(end),
        'result': result,
    }

    if callable(verifier):
        try:
            artifact['verification'] = verifier(activity, artifact, state or {})
        except Exception:
            artifact['verification'] = {'ok': False, 'reason': 'verifier_exception'}
    else:
        artifact['verification'] = {'ok': True, 'reason': 'no_verifier'}

    if isinstance(queue, dict):
        try:
            release_resources(queue=queue, activity=activity)
        except Exception:
            pass
    return artifact


def complete_activity(*, queue: ActivityQueue, activity: Activity, result: Any) -> ActivityQueue:
    """Move activity from active -> completed; attach result into metadata."""
    active = queue.get('active') if isinstance(queue, dict) else None
    completed = queue.get('completed') if isinstance(queue, dict) else None
    if not isinstance(active, list) or not isinstance(completed, list):
        return queue
    aid = activity.get('activity_id')
    for i, a in enumerate(list(active)):
        if isinstance(a, dict) and a.get('activity_id') == aid:
            active.pop(i)
            meta = a.get('metadata')
            if not isinstance(meta, dict):
                meta = {}
                a['metadata'] = meta
            meta['result'] = result
            completed.append(a)
            break
    return queue


def run_activity_cycle(
    *,
    awareness_plan: AwarenessPlan,
    queue: ActivityQueue,
    modules: dict[str, Callable[[Activity], Any]],
    max_steps: int = 1,
    state: Optional[dict[str, Any]] = None,
) -> ActivityQueue:
    """Run a deterministic activity cycle.

    Steps:
    1. Translate wants -> activities
    2. Enqueue
    3. Prioritize
    4. Select next
    5. Execute
    6. Complete
    """
    activities = translate_wants_to_activities(awareness_plan=awareness_plan)
    queue = enqueue_activities(queue=queue, activities=activities)
    queue = prioritize_queue(queue=queue)

    steps = int(max_steps) if max_steps is not None else 1
    if steps < 1:
        steps = 1
    # Optional verifier module passed via modules mapping (non-activity key).
    verifier_module = None
    if isinstance(modules, dict):
        verifier_module = modules.get('__verifier__') or modules.get('verifier')

    base_state = state or {}
    # Provide resource accounting context to verifier.
    if isinstance(queue, dict):
        try:
            base_state = dict(base_state)
            base_state.setdefault('resource_budget', queue.get('resource_budget'))
            base_state.setdefault('used_resources', queue.get('used_resources'))
        except Exception:
            pass

    for _ in range(steps):
        act = select_next_activity(queue=queue, state=base_state, verifier_module=verifier_module)
        if act is None:
            break

        if verifier_module is not None and hasattr(verifier_module, 'check_postconditions') and hasattr(verifier_module, 'generate_validation_artifact'):
            # Use the existing hook wrapper to attach verification artifacts deterministically.
            def _verifier_cb(a: Activity, artifact: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
                try:
                    pre = verifier_module.check_preconditions(a, st)
                except Exception:
                    pre = {'ok': False, 'failures': ['verifier_exception'], 'evidence': {}}
                try:
                    post = verifier_module.check_postconditions(a, artifact.get('result') if isinstance(artifact, dict) else {}, st)
                except Exception:
                    post = {'ok': False, 'failures': ['verifier_exception'], 'evidence': {}}

                det = bool(st.get('deterministic_mode')) if isinstance(st, dict) else False
                prov = st.get('provenance') if isinstance(st, dict) else None
                prov_list = [e for e in (prov or []) if isinstance(e, dict)] if isinstance(prov, list) else []
                try:
                    artifact_doc = verifier_module.generate_validation_artifact(pre, post, prov_list, det)
                except Exception:
                    artifact_doc = {'ok': False, 'reason': 'artifact_exception'}

                out = {'ok': bool(pre.get('ok')) and bool(post.get('ok')), 'pre': pre, 'post': post, 'artifact': artifact_doc}
                try:
                    policy = st.get('verifier_policy') if isinstance(st, dict) else None
                    if not out['ok'] and hasattr(verifier_module, 'escalate_on_failure'):
                        out['escalation'] = verifier_module.escalate_on_failure(artifact_doc, policy or {})
                except Exception:
                    pass
                return out

            exec_artifact = execute_activity_with_hooks(activity=act, modules=modules, queue=queue, verifier=_verifier_cb, state=base_state)
            res = exec_artifact
        else:
            res = execute_activity(activity=act, modules=modules)

        queue = complete_activity(queue=queue, activity=act, result=res)
        queue = prioritize_queue(queue=queue)
    return queue


def enqueue_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Write an activity file into ActivityQueue.

    - Deterministic naming is delegated to caller via activity_id.
    - No sorting/dispatch yet; this is a storage primitive.
    """
    qd = _queue_dir()
    os.makedirs(qd, exist_ok=True)

    aid = activity.get("activity_id")
    if not isinstance(aid, str) or not aid:
        return {"ok": False, "reason": "missing_activity_id"}

    path = os.path.join(qd, f"{aid}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(activity, f, ensure_ascii=False, indent=2)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "reason": "write_failed", "error": str(e)}


def list_activities(*, limit: int = 100) -> List[Dict[str, Any]]:
    qd = _queue_dir()
    if not os.path.isdir(qd):
        return []
    items = []
    for fn in sorted(os.listdir(qd)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(qd, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                items.append(json.load(f))
        except Exception:
            continue
        if limit and len(items) >= int(limit):
            break
    return items
