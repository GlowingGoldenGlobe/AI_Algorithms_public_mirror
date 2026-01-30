import argparse
import json
import os
import sys
import subprocess
import contextlib
import io
import zipfile
from datetime import datetime, timezone

from module_determinism import evaluate_determinism_suite, print_determinism
from module_measure import print_weights
from module_integration import RelationalMeasurement
from module_tools import build_semantic_index, _load_config

BASE = os.path.dirname(os.path.abspath(__file__))


def _write_config(cfg: dict):
    path = os.path.join(BASE, 'config.json')
    os.makedirs(BASE, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    # Ensure subsequent reads in this process see the updated config
    try:
        from module_tools import _clear_config_cache
        _clear_config_cache()
    except Exception:
        pass

def cmd_init(args):
    from module_integration import initialize_ai_brain
    res = initialize_ai_brain()
    print(json.dumps(res, indent=2))

def cmd_cycle(args):
    if getattr(args, 'quiet', False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            labels = RelationalMeasurement(args.id, args.content, args.category)
    else:
        labels = RelationalMeasurement(args.id, args.content, args.category)
    print(json.dumps({"id": args.id, "labels": labels}, indent=2))

def cmd_eval(args):
    exe = sys.executable
    if getattr(args, 'quiet', False):
        proc = subprocess.run([exe, os.path.join(BASE, 'run_eval.py')], capture_output=True, text=True)
        # Emit minimal summary only
        print(json.dumps({"ok": proc.returncode == 0}, indent=2))
        sys.exit(proc.returncode)
    else:
        proc = subprocess.run([exe, os.path.join(BASE, 'run_eval.py')], capture_output=False)
        sys.exit(proc.returncode)

def cmd_stress(args):
    # Auto-reexec into workspace venv if launched with a different interpreter (e.g., py -3)
    try:
        expected = os.path.join(BASE, 'Scripts', 'python.exe')
        if os.path.exists(expected) and os.path.normcase(sys.executable) != os.path.normcase(expected):
            cmd = [expected, os.path.join(BASE, 'cli.py'), 'stress', '--id', args.id, '--content', args.content]
            if getattr(args, 'quiet', False):
                cmd.append('--quiet')
            r = subprocess.run(cmd)
            sys.exit(r.returncode)
    except Exception:
        pass
    try:
        from collector_stress_test import stress_test
        res = stress_test(args.id, args.content, quiet=getattr(args, 'quiet', False))
        # Enrich with interpreter diagnostics for troubleshooting
        try:
            res['interpreter'] = sys.executable
            # Heuristic: workspace venv on Windows is BASE\\Scripts\\python.exe
            venv_py = os.path.join(BASE, 'Scripts', 'python.exe')
            res['in_workspace_venv'] = (os.path.normcase(sys.executable) == os.path.normcase(venv_py))
        except Exception:
            pass
        print(json.dumps(res, indent=2))
    except Exception as e:
        err = {
            'ok': False,
            'error': str(e),
            'id': getattr(args, 'id', None),
        }
        print(json.dumps(err, indent=2))
        sys.exit(1)

def cmd_baseline(args):
    exe = sys.executable
    proc = subprocess.run([exe, os.path.join(BASE, 'scripts', 'stress_baseline.py')], capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
    sys.exit(proc.returncode)

def cmd_det(args):
    if getattr(args, 'quiet', False):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rep = evaluate_determinism_suite()
    else:
        rep = evaluate_determinism_suite()
    print(json.dumps(rep, indent=2))
    if not rep.get('overall_passed'):
        sys.exit(1)

def cmd_weights(args):
    print_weights()

def cmd_determinism(args):
    print_determinism()


def cmd_adversarial(args):
    try:
        from module_adversarial_test import run_scenario
    except Exception as e:
        print(json.dumps({'ok': False, 'error': f'Cannot import module_adversarial_test: {e}'}, indent=2))
        sys.exit(1)

    scenario = str(getattr(args, 'scenario', '') or '')
    if not scenario:
        print(json.dumps({'ok': False, 'error': 'Missing --scenario'}, indent=2))
        sys.exit(2)

    # Determinism default: follow config unless caller overrides.
    deterministic_mode = None
    if getattr(args, 'deterministic', False):
        deterministic_mode = True
    if getattr(args, 'non_deterministic', False):
        deterministic_mode = False
    if deterministic_mode is None:
        try:
            cfg = _load_config() or {}
            det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}
            deterministic_mode = bool(det.get('deterministic_mode'))
        except Exception:
            deterministic_mode = True

    rep = run_scenario(
        scenario,
        deterministic_mode=bool(deterministic_mode),
        global_seed=getattr(args, 'seed', None),
        write_report=(not bool(getattr(args, 'no_write', False))),
        report_dir=getattr(args, 'report_dir', None),
    )
    out = {'ok': ('error' not in rep), 'report': rep}
    print(json.dumps(out, indent=2))
    if 'error' in rep:
        sys.exit(1)


def cmd_det_set(args):
    cfg = _load_config() or {}
    det = cfg.setdefault('determinism', {})
    before = {'deterministic_mode': bool(det.get('deterministic_mode')), 'fixed_timestamp': det.get('fixed_timestamp')}
    if getattr(args, 'on', False):
        det['deterministic_mode'] = True
    if getattr(args, 'off', False):
        det['deterministic_mode'] = False
    if getattr(args, 'fixed_timestamp', None):
        det['fixed_timestamp'] = args.fixed_timestamp
    after = {'deterministic_mode': bool(det.get('deterministic_mode')), 'fixed_timestamp': det.get('fixed_timestamp')}
    out = {'dry_run': bool(getattr(args, 'dry_run', False)), 'before': before, 'after': after}
    print(json.dumps(out, indent=2))
    if not getattr(args, 'dry_run', False):
        _write_config(cfg)


def cmd_policy_list(args):
    presets = {
        'conservative': { 'sel_min_ben_syn': 0.5, 'composite_activate': 0.6 },
        'balanced':     { 'sel_min_ben_syn': 0.4, 'composite_activate': 0.55 },
        'aggressive':   { 'sel_min_ben_syn': 0.3, 'composite_activate': 0.5 }
    }
    print(json.dumps(presets, indent=2))


def cmd_policy_apply(args):
    name = args.name
    dry = bool(getattr(args, 'dry_run', False))
    presets = {
        'conservative': { 'sel_min_ben_syn': 0.5, 'composite_activate': 0.6 },
        'balanced':     { 'sel_min_ben_syn': 0.4, 'composite_activate': 0.55 },
        'aggressive':   { 'sel_min_ben_syn': 0.3, 'composite_activate': 0.5 }
    }
    if name not in presets:
        print(json.dumps({'ok': False, 'error': 'Unknown preset', 'name': name}, indent=2))
        sys.exit(2)
    chosen = presets[name]
    cfg_path = os.path.join(BASE, 'config.json')
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    pol = cfg.setdefault('policy', {}).setdefault('activation', {})
    pol.update(chosen)
    out = {'ok': True, 'preset': name, 'activation': pol, 'dry_run': dry}
    print(json.dumps(out, indent=2))
    if not dry:
        tmp = cfg_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, cfg_path)
        try:
            from module_tools import _clear_config_cache
            _clear_config_cache()
        except Exception:
            pass


def _find_det_reports():
    root = os.path.join(BASE, 'ActiveSpace')
    out = []
    try:
        for name in os.listdir(root):
            if name.startswith('determinism_report_') and name.endswith('.json'):
                p = os.path.join(root, name)
                out.append((p, os.path.getmtime(p)))
        out.sort(key=lambda t: t[1], reverse=True)
    except Exception:
        return []
    return [p for p, _ in out]


def cmd_det_report(args):
    # Resolve report path
    rep_path = None
    if getattr(args, 'latest', False):
        files = _find_det_reports()
        if files:
            rep_path = files[0]
    if not rep_path:
        rep_id = getattr(args, 'id', 'det_suite')
        rep_path = os.path.join(BASE, 'ActiveSpace', f'determinism_report_{rep_id}.json')
    # Read
    try:
        with open(rep_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': f'Cannot read report: {e}', 'path': rep_path}, indent=2))
        sys.exit(1)
    # Raw or summarized
    if getattr(args, 'raw', False):
        print(json.dumps(report, indent=2))
    else:
        checks = {c.get('check'): bool(c.get('passed')) for c in (report.get('checks') or [])}
        summary = {
            'deterministic_mode': bool(report.get('deterministic_mode')),
            'fixed_timestamp': report.get('fixed_timestamp'),
            'overall_passed': bool(report.get('overall_passed')),
            'checks': checks,
            'path': rep_path
        }
        print(json.dumps(summary, indent=2))
    if getattr(args, 'strict', False) and not report.get('overall_passed'):
        sys.exit(2)


def cmd_policy_show(args):
    cfg = _load_config() or {}
    pol = (cfg.get('policy') or {}).get('activation', {})
    out = {
        'policy.activation': {
            'sel_min_ben_syn': pol.get('sel_min_ben_syn', 0.4),
            'composite_activate': pol.get('composite_activate', 0.55)
        }
    }
    print(json.dumps(out, indent=2))


def cmd_policy_set(args):
    cfg = _load_config() or {}
    policy = cfg.setdefault('policy', {})
    activation = policy.setdefault('activation', {})
    before = {
        'sel_min_ben_syn': activation.get('sel_min_ben_syn', 0.4),
        'composite_activate': activation.get('composite_activate', 0.55)
    }
    updated = False
    if args.sel_min_ben_syn is not None:
        activation['sel_min_ben_syn'] = float(args.sel_min_ben_syn)
        updated = True
    if args.composite_activate is not None:
        activation['composite_activate'] = float(args.composite_activate)
        updated = True
    after = {
        'sel_min_ben_syn': activation.get('sel_min_ben_syn'),
        'composite_activate': activation.get('composite_activate')
    }
    out = {'dry_run': bool(args.dry_run), 'before': before, 'after': after, 'updated': updated}
    print(json.dumps(out, indent=2))
    if updated and not args.dry_run:
        _write_config(cfg)


def cmd_diagnose(args):
    info = {}
    try:
        info['cwd'] = os.getcwd()
        info['base'] = BASE
        info['interpreter'] = sys.executable
        info['sys_version'] = sys.version
        info['virtual_env'] = os.environ.get('VIRTUAL_ENV')
        venv_py = os.path.join(BASE, 'Scripts', 'python.exe')
        info['expected_venv_python'] = venv_py
        info['in_workspace_venv'] = (os.path.normcase(sys.executable) == os.path.normcase(venv_py))
        # Config snapshot
        cfg = _load_config() or {}
        info['determinism'] = (cfg.get('determinism') or {})
        info['policy_activation'] = ((cfg.get('policy') or {}).get('activation') or {})
        # Path checks
        paths = {
            'ActiveSpace': os.path.join(BASE, 'ActiveSpace'),
            'LTS.ActiveSpace': os.path.join(BASE, 'LongTermStore', 'ActiveSpace'),
            'LTS.Semantic': os.path.join(BASE, 'LongTermStore', 'Semantic')
        }
        info['paths'] = {k: {'path': v, 'exists': os.path.isdir(v)} for k, v in paths.items()}
        # Write test (non-destructive): create and remove a temp file in ActiveSpace
        touch_dir = paths['ActiveSpace']
        os.makedirs(touch_dir, exist_ok=True)
        probe = os.path.join(touch_dir, 'diagnose_touch.tmp')
        try:
            with open(probe, 'w', encoding='utf-8') as f:
                f.write('ok')
            info['write_test'] = {'path': probe, 'ok': True}
        except Exception as we:
            info['write_test'] = {'path': probe, 'ok': False, 'error': str(we)}
        finally:
            try:
                if os.path.exists(probe):
                    os.remove(probe)
            except Exception:
                pass
    except Exception as e:
        info = {'ok': False, 'error': str(e)}
    print(json.dumps(info, indent=2))


def _load_cycle_policy_inputs(cycle: dict):
    data_id = cycle.get('data_id')
    rel_labels = cycle.get('relation_labels') or []
    conflicts = cycle.get('arbiter', {}).get('conflicts') or []
    dec = cycle.get('decisive_recommendation')
    # Defaults
    selection_score = 0.0
    similarity = float(((cycle.get('signals') or {}).get('similarity')) or 0.0)
    usefulness = (cycle.get('signals') or {}).get('usefulness') or 'unknown'
    beneficial_and_synthesis = (('beneficial' in rel_labels) and ('synthesis_value' in rel_labels))
    objective_alignment = 'unknown'
    contradiction = bool(dec == 'contradiction_resolve' or any((c or {}).get('severity', 0) > 0.5 for c in conflicts) or ('detrimental' in rel_labels))
    # Try to enrich from semantic record decision_signals if present
    try:
        sem_path = os.path.join(BASE, 'LongTermStore', 'Semantic', f'{data_id}.json')
        with open(sem_path, 'r', encoding='utf-8') as f:
            rec = json.load(f)
        ds_list = rec.get('decision_signals') or []
        if ds_list:
            last = ds_list[-1]
            selection_score = float(last.get('selection_score') or selection_score)
            objective_alignment = last.get('objective_alignment', objective_alignment)
            beneficial_and_synthesis = bool(last.get('beneficial_and_synthesis', beneficial_and_synthesis))
            contradiction = bool(last.get('contradiction', contradiction))
            usefulness = last.get('usefulness', usefulness)
            similarity = float(last.get('similarity', similarity))
    except Exception:
        pass
    return {
        'selection_score': selection_score,
        'similarity': similarity,
        'usefulness': usefulness,
        'beneficial_and_synthesis': beneficial_and_synthesis,
        'objective_alignment': objective_alignment,
        'contradiction': contradiction
    }


def _policy_decision(inputs: dict, sel_min_ben_syn: float, comp_activate: float):
    usefulness = inputs.get('usefulness')
    contradiction = bool(inputs.get('contradiction'))
    maturity = 'unknown'  # not available from cycles; conservative default
    sel_score = float(inputs.get('selection_score', 0.0))
    sim = float(inputs.get('similarity', 0.0))
    obj_align = str(inputs.get('objective_alignment', 'unknown')).lower()
    ben_syn = bool(inputs.get('beneficial_and_synthesis', False))
    if contradiction:
        return 'HoldingSpace'
    comp = (0.5 * sel_score) + (0.4 * sim) + (0.1 if usefulness == 'useful_now' else 0.0)
    if ben_syn and (sel_score >= sel_min_ben_syn or obj_align == 'aligned'):
        return 'ActiveSpace'
    if (usefulness == 'useful_now' and maturity in ('stable','strong')) or comp >= comp_activate:
        return 'ActiveSpace'
    if usefulness in ('useful_later','not_useful'):
        return 'HoldingSpace'
    return 'HoldingSpace'


def cmd_policy_eval(args):
    # Load current thresholds as defaults
    cfg = _load_config() or {}
    pol = (cfg.get('policy') or {}).get('activation', {})
    sel_min = float(args.sel_min_ben_syn if args.sel_min_ben_syn is not None else pol.get('sel_min_ben_syn', 0.4))
    comp_act = float(args.composite_activate if args.composite_activate is not None else pol.get('composite_activate', 0.55))

    # Load recent cycles
    apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    try:
        with open(apath, 'r', encoding='utf-8') as f:
            act = json.load(f)
        cycles = (act.get('cycles') or [])[-int(max(0, args.recent)):] if args.recent else (act.get('cycles') or [])
    except Exception:
        cycles = []
    evaluated = 0
    would_activate = 0
    items = []
    for c in cycles:
        inputs = _load_cycle_policy_inputs(c)
        tgt = _policy_decision(inputs, sel_min, comp_act)
        evaluated += 1
        if tgt == 'ActiveSpace':
            would_activate += 1
        if args.detail:
            items.append({'data_id': c.get('data_id'), 'target': tgt, 'selection_score': inputs['selection_score'], 'similarity': inputs['similarity']})
    out = {
        'evaluated': evaluated,
        'would_activate': would_activate,
        'activation_rate': (float(would_activate) / evaluated) if evaluated else 0.0,
        'thresholds': {'sel_min_ben_syn': sel_min, 'composite_activate': comp_act}
    }
    if args.detail:
        out['items'] = items
    print(json.dumps(out, indent=2))


def _frange(start: float, end: float, step: float):
    vals = []
    x = start
    # Ensure numerical stability
    while x <= end + 1e-12:
        vals.append(round(x, 6))
        x += step
    return vals


def _parse_range(spec: str, default_center: float, radius: float, step: float):
    if spec:
        try:
            parts = [float(p) for p in spec.split(':')]
            if len(parts) == 3:
                a, b, c = parts
                if c <= 0:
                    c = step
                a = max(0.0, min(1.0, a))
                b = max(0.0, min(1.0, b))
                if a > b:
                    a, b = b, a
                return _frange(a, b, c)
        except Exception:
            pass
    a = max(0.0, default_center - radius)
    b = min(1.0, default_center + radius)
    return _frange(a, b, step)


def cmd_policy_tune(args):
    cfg = _load_config() or {}
    pol = (cfg.get('policy') or {}).get('activation', {})
    sel_center = float(pol.get('sel_min_ben_syn', 0.4))
    comp_center = float(pol.get('composite_activate', 0.55))

    # Build candidate ranges
    sel_vals = _parse_range(getattr(args, 'sel_range', None), sel_center, 0.15, 0.05)
    comp_vals = _parse_range(getattr(args, 'comp_range', None), comp_center, 0.15, 0.02)

    # Load cycles window
    apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    try:
        with open(apath, 'r', encoding='utf-8') as f:
            act = json.load(f)
        cycles = (act.get('cycles') or [])
        if args.recent and args.recent > 0:
            cycles = cycles[-int(args.recent):]
    except Exception:
        cycles = []

    target = float(args.target_rate)
    max_pairs = int(getattr(args, 'max_pairs', 500))
    pairs = []
    for sv in sel_vals:
        for cv in comp_vals:
            pairs.append((sv, cv))
    if len(pairs) > max_pairs:
        pairs = pairs[:max_pairs]

    best = None
    evaluated = 0
    for (sv, cv) in pairs:
        evaluated += 1
        evald = 0
        actv = 0
        for c in cycles:
            inputs = _load_cycle_policy_inputs(c)
            tgt = _policy_decision(inputs, sv, cv)
            evald += 1
            if tgt == 'ActiveSpace':
                actv += 1
        rate = (float(actv) / evald) if evald else 0.0
        diff = abs(rate - target)
        cand = {'sel_min_ben_syn': sv, 'composite_activate': cv, 'rate': rate, 'diff': diff}
        if (best is None) or (cand['diff'] < best['diff']) or (cand['diff'] == best['diff'] and cand['rate'] > best['rate']):
            best = cand

    out = {
        'target_rate': target,
        'evaluated_pairs': evaluated,
        'recent_cycles': len(cycles),
        'current': {'sel_min_ben_syn': sel_center, 'composite_activate': comp_center},
        'recommendation': best
    }
    print(json.dumps(out, indent=2))
    if best and getattr(args, 'apply', False):
        cfg.setdefault('policy', {}).setdefault('activation', {})
        cfg['policy']['activation']['sel_min_ben_syn'] = best['sel_min_ben_syn']
        cfg['policy']['activation']['composite_activate'] = best['composite_activate']
        _write_config(cfg)


def _delete_files(files):
    deleted = 0
    for p in files:
        try:
            os.remove(p)
            deleted += 1
        except Exception:
            continue
    return deleted


def _get_files_sorted(dir_path, prefix=None, suffix=None):
    items = []
    try:
        for name in os.listdir(dir_path):
            if prefix and not name.startswith(prefix):
                continue
            if suffix and not name.endswith(suffix):
                continue
            p = os.path.join(dir_path, name)
            if os.path.isfile(p):
                items.append((p, os.path.getmtime(p)))
        items.sort(key=lambda t: t[1], reverse=True)
    except Exception:
        return []
    return [p for p, _ in items]


def cmd_gc(args):
    # Parameters
    keep_collectors = max(0, getattr(args, 'collectors', 50))
    temp_days = max(0, getattr(args, 'temp_days', 7))
    trim_cycles = max(0, getattr(args, 'cycles', 200))
    dry_run = getattr(args, 'dry_run', True)

    now = datetime.now(timezone.utc).timestamp()
    changes = {
        'dry_run': bool(dry_run),
        'collector_files_deleted': 0,
        'temporary_files_deleted': 0,
        'activity_cycles_trimmed': 0,
        'kept_collectors': keep_collectors,
        'temp_days': temp_days,
        'cycles_cap': trim_cycles
    }

    # Prune collector files in LongTermStore/ActiveSpace
    lts_as = os.path.join(BASE, 'LongTermStore', 'ActiveSpace')
    collectors = _get_files_sorted(lts_as, prefix='collector_', suffix='.json')
    to_delete = collectors[keep_collectors:]
    if not dry_run:
        changes['collector_files_deleted'] = _delete_files(to_delete)
    else:
        changes['collector_files_deleted'] = len(to_delete)

    # Clean TemporaryQueue files older than temp_days
    tmp_dir = os.path.join(BASE, 'TemporaryQueue')
    tmp_deleted = 0
    try:
        if os.path.isdir(tmp_dir):
            for name in os.listdir(tmp_dir):
                p = os.path.join(tmp_dir, name)
                try:
                    if not os.path.isfile(p):
                        continue
                    age_days = (now - os.path.getmtime(p)) / 86400.0
                    if age_days > temp_days:
                        if not dry_run:
                            os.remove(p)
                        tmp_deleted += 1
                except Exception:
                    continue
    except Exception:
        pass
    changes['temporary_files_deleted'] = tmp_deleted

    # Trim activity cycles to cap
    act_path = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    try:
        if os.path.isfile(act_path):
            with open(act_path, 'r', encoding='utf-8') as f:
                act = json.load(f)
            cycles = act.get('cycles') or []
            if len(cycles) > trim_cycles:
                trimmed = len(cycles) - trim_cycles
                changes['activity_cycles_trimmed'] = trimmed
                act['cycles'] = cycles[-trim_cycles:]
                if not dry_run:
                    with open(act_path, 'w', encoding='utf-8') as f:
                        json.dump(act, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print(json.dumps(changes, indent=2))

def _read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _summarize_resources(limit=10):
    root = os.path.join(BASE, 'LongTermStore', 'ActiveSpace')
    if not os.path.isdir(root):
        return {}
    files = [os.path.join(root, f) for f in os.listdir(root) if f.startswith('collector_') and f.endswith('.json')]
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    files = files[:limit]
    total_cpu = 0
    max_mem = 0
    items = 0
    per_module = {}
    for p in files:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                arr = json.load(f)
            for it in arr:
                if not isinstance(it, dict):
                    continue
                rh = (it or {}).get('resource_hints') or {}
                total_cpu += int(rh.get('cpu_time_ms', 0))
                max_mem = max(max_mem, int(rh.get('mem_est_kb', 0)))
                items += 1
                m = (it or {}).get('module') or 'unknown'
                pm = per_module.setdefault(m, {'count': 0, 'total_cpu_time_ms': 0, 'max_mem_kb': 0})
                pm['count'] += 1
                pm['total_cpu_time_ms'] += int(rh.get('cpu_time_ms', 0))
                pm['max_mem_kb'] = max(pm['max_mem_kb'], int(rh.get('mem_est_kb', 0)))
        except Exception:
            continue
    for m, pm in per_module.items():
        c = max(1, pm['count'])
        pm['avg_cpu_time_ms'] = int(pm['total_cpu_time_ms'] / c)
    return {
        'files_scanned': len(files),
        'items': items,
        'cpu_time_ms_total': total_cpu,
        'max_mem_kb': max_mem,
        'per_module': per_module
    }


def _recent_cycles(n=5):
    apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    out = []
    try:
        with open(apath, 'r', encoding='utf-8') as f:
            act = json.load(f)
        cycles = act.get('cycles') or []
        for c in cycles[-n:]:
            out.append({
                'data_id': c.get('data_id'),
                'labels': c.get('relation_labels'),
                'decisive': c.get('decisive_recommendation'),
                'rationale': ((c.get('arbiter') or {}).get('rationale'))
            })
    except Exception:
        pass
    return out


def _determinism_summary():
    files = _find_det_reports()
    if not files:
        return {'available': False}
    try:
        p = files[0]
        with open(p, 'r', encoding='utf-8') as f:
            report = json.load(f)
        checks = {c.get('check'): bool(c.get('passed')) for c in (report.get('checks') or [])}
        return {
            'available': True,
            'deterministic_mode': bool(report.get('deterministic_mode')),
            'overall_passed': bool(report.get('overall_passed')),
            'checks': checks,
            'path': p
        }
    except Exception:
        return {'available': False}

def _list_recent_files(dir_path, prefix=None, suffix=None, limit=50):
    try:
        entries = []
        for name in os.listdir(dir_path):
            if prefix and not name.startswith(prefix):
                continue
            if suffix and not name.endswith(suffix):
                continue
            p = os.path.join(dir_path, name)
            if os.path.isfile(p):
                entries.append((p, os.path.getmtime(p)))
        entries.sort(key=lambda t: t[1], reverse=True)
        return [p for p, _ in entries[:max(0, limit)]]
    except Exception:
        return []


def cmd_snapshot(args):
    out_path = args.out or os.path.join(BASE, f"AI_Brain_Snapshot_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zip")
    include_collectors = max(0, getattr(args, 'collectors', 10))
    include_sem = max(0, getattr(args, 'semantic', 50))

    files = []
    # Always include config
    cfg = os.path.join(BASE, 'config.json')
    if os.path.isfile(cfg):
        files.append((cfg, 'config.json'))
    # ActiveSpace
    act = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    if os.path.isfile(act):
        files.append((act, os.path.join('ActiveSpace', 'activity.json')))
    # LongTermStore ActiveSpace collectors (recent)
    lts_as = os.path.join(BASE, 'LongTermStore', 'ActiveSpace')
    for p in _list_recent_files(lts_as, prefix='collector_', suffix='.json', limit=include_collectors):
        rel = os.path.relpath(p, BASE)
        files.append((p, rel))
    # LongTermStore Semantic (recent)
    lts_sem = os.path.join(BASE, 'LongTermStore', 'Semantic')
    for p in _list_recent_files(lts_sem, suffix='.json', limit=include_sem):
        rel = os.path.relpath(p, BASE)
        files.append((p, rel))

    # Create zip
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arc in files:
            try:
                zf.write(src, arcname=arc)
            except Exception:
                # Skip unreadable files
                continue
    print(json.dumps({
        'ok': True,
        'archive': out_path,
        'files_included': len(files)
    }, indent=2))


def cmd_status(args):
    cfg = _load_config() or {}
    det = cfg.get('determinism', {})
    idx = build_semantic_index()
    apath = os.path.join(BASE, 'ActiveSpace', 'activity.json')
    cycles = 0
    try:
        with open(apath, 'r', encoding='utf-8') as f:
            act = json.load(f)
        cycles = len(act.get('cycles', []))
    except Exception:
        cycles = 0
    out = {
        'deterministic_mode': bool(det.get('deterministic_mode')),
        'fixed_timestamp': det.get('fixed_timestamp'),
        'index_ids': len((idx.get('id_to_tokens') or {})),
        'activity_cycles': cycles
    }

    # Optional: append a status snapshot to a JSONL file for time-series tracking.
    if bool(getattr(args, 'log', False)):
        try:
            from module_storage import ROOT as _ROOT, resolve_path
            from module_tools import safe_join

            sem_dir = resolve_path('semantic')
            proc_dir = resolve_path('procedural')
            obj_dir = os.path.join(str(_ROOT), 'LongTermStore', 'Objectives')
            lts_as_dir = os.path.join(str(_ROOT), 'LongTermStore', 'ActiveSpace')

            def _count_json_files(d: str) -> int:
                try:
                    return int(len([n for n in os.listdir(d) if str(n).lower().endswith('.json')]))
                except Exception:
                    return 0

            snapshot = {
                'schema_version': '1.0',
                # Wall clock time for time-series; keep deterministic timestamp alongside when enabled.
                'ts_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'deterministic_mode': bool(det.get('deterministic_mode')),
                'fixed_timestamp': det.get('fixed_timestamp'),
                'qty': {
                    'index_ids': int(out.get('index_ids') or 0),
                    'activity_cycles': int(out.get('activity_cycles') or 0),
                    'semantic_records': _count_json_files(sem_dir),
                    'objectives': _count_json_files(obj_dir),
                    'procedural_records': _count_json_files(proc_dir),
                    'collector_outputs': _count_json_files(lts_as_dir),
                },
            }

            rel = str(getattr(args, 'log_path', '') or '').strip()
            if not rel:
                rel = 'TemporaryQueue/status_history.jsonl'
            log_path = safe_join(str(_ROOT), rel)
            os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n")
            out['status_log'] = {'ok': True, 'path': os.path.relpath(log_path, str(_ROOT))}
        except Exception:
            out['status_log'] = {'ok': False}
    if getattr(args, 'resources', False):
        out['resources'] = _summarize_resources(limit=getattr(args, 'collectors', 10))
    if getattr(args, 'recent', 0) and args.recent > 0:
        out['recent_cycles'] = _recent_cycles(n=args.recent)
    if getattr(args, 'det', False):
        out['determinism'] = _determinism_summary()
    if getattr(args, 'policy_rate', False):
        cfg2 = _load_config() or {}
        pol = (cfg2.get('policy') or {}).get('activation', {})
        sel_min = float(getattr(args, 'sel_min_ben_syn', None) if args.sel_min_ben_syn is not None else pol.get('sel_min_ben_syn', 0.4))
        comp_act = float(getattr(args, 'composite_activate', None) if args.composite_activate is not None else pol.get('composite_activate', 0.55))
        # Load cycles (respect existing --recent window)
        try:
            with open(apath, 'r', encoding='utf-8') as f:
                act = json.load(f)
            cycles_list = (act.get('cycles') or [])
            if getattr(args, 'recent', 0):
                cycles_list = cycles_list[-int(max(0, args.recent)):]
        except Exception:
            cycles_list = []
        evaluated = 0
        would_activate = 0
        for c in cycles_list:
            inputs = _load_cycle_policy_inputs(c)
            tgt = _policy_decision(inputs, sel_min, comp_act)
            evaluated += 1
            if tgt == 'ActiveSpace':
                would_activate += 1
        out['policy_eval'] = {
            'evaluated': evaluated,
            'would_activate': would_activate,
            'activation_rate': (float(would_activate) / evaluated) if evaluated else 0.0,
            'thresholds': {'sel_min_ben_syn': sel_min, 'composite_activate': comp_act}
        }
    print(json.dumps(out, indent=2))


def cmd_hw(args):
    """Capture a hardware/system snapshot.

    Intended for monitoring AI Brain activities and correlating runs with resource usage.
    """
    cfg = _load_config() or {}
    det = cfg.get('determinism', {}) if isinstance(cfg, dict) else {}

    from module_hardware_metrics import get_hardware_info

    hw = get_hardware_info(fast=bool(getattr(args, 'fast', False)))
    out = {
        'schema_version': '1.0',
        'ts_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'deterministic_mode': bool(det.get('deterministic_mode')),
        'fixed_timestamp': det.get('fixed_timestamp'),
        'hardware': hw,
    }

    # Optional: automation gate for agent-mode runners.
    if bool(getattr(args, 'gate', False)):
        gate_cfg = (cfg.get('hardware_gate') or {}) if isinstance(cfg, dict) else {}
        def _pick(name: str, default_val):
            v = getattr(args, name, None)
            if v is not None:
                return v
            try:
                return gate_cfg.get(name, default_val)
            except Exception:
                return default_val

        cpu_max = _pick('cpu_max', 95.0)
        mem_max = _pick('mem_max', 95.0)
        disk_max = _pick('disk_max', 97.0)
        require_ok = bool(_pick('require_ok', False))

        info = (hw.get('info') or {}) if isinstance(hw, dict) else {}
        cpu = info.get('cpu_percent')
        mem = info.get('memory_percent')
        disk = info.get('disk_percent')

        reasons = []
        gate_ok = True

        if isinstance(hw, dict) and not bool(hw.get('ok', False)):
            if require_ok:
                gate_ok = False
                reasons.append('hardware_snapshot_unavailable')
            else:
                reasons.append('hardware_snapshot_unavailable_soft')

        def _check(val, max_val, label):
            nonlocal gate_ok
            if val is None:
                return
            try:
                v = float(val)
                m = float(max_val) if max_val is not None else None
                if m is not None and v > m:
                    gate_ok = False
                    reasons.append(f"{label}_over_max:{v:.1f}>{m:.1f}")
            except Exception:
                # Ignore parse issues; keep gate best-effort.
                return

        _check(cpu, cpu_max, 'cpu')
        _check(mem, mem_max, 'mem')
        _check(disk, disk_max, 'disk')

        out['gate'] = {
            'ok': bool(gate_ok),
            'reasons': reasons,
            'thresholds': {
                'cpu_max': cpu_max,
                'mem_max': mem_max,
                'disk_max': disk_max,
                'require_ok': bool(require_ok),
            },
        }

    if bool(getattr(args, 'log', False)):
        try:
            from module_storage import ROOT as _ROOT
            from module_tools import safe_join

            rel = str(getattr(args, 'log_path', '') or '').strip()
            if not rel:
                rel = 'TemporaryQueue/hardware_history.jsonl'
            log_path = safe_join(str(_ROOT), rel)
            os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")
            out['hardware_log'] = {'ok': True, 'path': os.path.relpath(log_path, str(_ROOT))}
        except Exception:
            out['hardware_log'] = {'ok': False}

    print(json.dumps(out, indent=2))
    if bool(getattr(args, 'gate', False)) and bool(getattr(args, 'strict', False)):
        try:
            if not bool((out.get('gate') or {}).get('ok', True)):
                sys.exit(2)
        except SystemExit:
            raise
        except Exception:
            pass


def cmd_index(args):
    """Rebuild and summarize the semantic index."""
    idx = build_semantic_index()
    out = {
        'ok': True,
        'index_ids': len((idx.get('id_to_tokens') or {})),
        'last_build_ts': idx.get('last_build_ts'),
    }
    if getattr(args, 'show_ids', False):
        out['ids'] = sorted((idx.get('id_to_tokens') or {}).keys())
    print(json.dumps(out, indent=2))


def cmd_backup(args):
    from module_backup import backup_repo_to_archive, resolve_archive_root
    archive_root = resolve_archive_root(getattr(args, 'archive_root', None))
    if not archive_root:
        print(json.dumps({
            'ok': False,
            'error': 'archive_root is required (pass --archive-root or set AI_ALGORITHMS_ARCHIVE_ROOT)',
        }, indent=2))
        sys.exit(2)
    try:
        rep = backup_repo_to_archive(
            repo_root=BASE,
            archive_root=archive_root,
            project_dir_name=getattr(args, 'project_name', 'AI_Algorithms'),
            mode=getattr(args, 'mode', 'committed'),
            dry_run=bool(getattr(args, 'dry_run', False)),
        )
        print(json.dumps(rep, indent=2))
        if not rep.get('ok', False):
            # Distinct exit codes make scripting easier.
            # 3: copy failure (partial staging); 4: finalize/rename failure
            if rep.get('finalize_error'):
                sys.exit(4)
            if int(rep.get('error_count') or 0) > 0:
                sys.exit(3)
            sys.exit(1)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}, indent=2))
        sys.exit(1)

def main():
    p = argparse.ArgumentParser(description='AI Brain CLI')
    p.add_argument('--quiet', action='store_true', help='Global quiet mode for supported commands')
    sub = p.add_subparsers(dest='cmd', required=True)

    sp = sub.add_parser('init', help='Initialize seeds and list objectives')
    sp.set_defaults(func=cmd_init)

    sc = sub.add_parser('cycle', help='Run a relational measurement cycle')
    sc.add_argument('--id', required=True)
    sc.add_argument('--content', required=True)
    sc.add_argument('--category', default='semantic')
    sc.add_argument('--quiet', action='store_true', help='Suppress non-essential prints')
    sc.set_defaults(func=cmd_cycle)

    se = sub.add_parser('eval', help='Run evaluation suite')
    se.add_argument('--quiet', action='store_true', help='Suppress test output; print summary JSON only')
    se.set_defaults(func=cmd_eval)

    ss = sub.add_parser('stress', help='Run collector stress test')
    ss.add_argument('--id', default='stress001')
    ss.add_argument('--content', default='keyword good synthesis')
    ss.add_argument('--quiet', action='store_true', help='Suppress non-essential prints')
    ss.set_defaults(func=cmd_stress)

    sb = sub.add_parser('baseline', help='Generate stress baseline JSON')
    sb.set_defaults(func=cmd_baseline)

    st = sub.add_parser('status', help='Show determinism, index size, and activity cycles')
    st.add_argument('--resources', action='store_true', help='Include recent collector resource summary')
    st.add_argument('--collectors', type=int, default=10, help='How many collector files to scan')
    st.add_argument('--recent', type=int, default=0, help='Show last N cycle summaries')
    st.add_argument('--det', action='store_true', help='Include latest determinism summary')
    st.add_argument('--log', action='store_true', help='Append a status snapshot to TemporaryQueue/status_history.jsonl')
    st.add_argument('--log-path', default='TemporaryQueue/status_history.jsonl', help='Workspace-relative JSONL path for status snapshots')
    st.add_argument('--policy-rate', action='store_true', help='Include activation-rate snapshot based on thresholds')
    st.add_argument('--sel-min-ben-syn', type=float, dest='sel_min_ben_syn', help='Override selection score threshold for beneficial+synthesis')
    st.add_argument('--composite-activate', type=float, dest='composite_activate', help='Override composite score threshold to activate')
    st.set_defaults(func=cmd_status)

    shw = sub.add_parser('hw', help='Capture a hardware/system snapshot (CPU/mem/disk)')
    shw.add_argument('--fast', action='store_true', help='Faster sampling (may be less stable)')
    shw.add_argument('--log', action='store_true', help='Append snapshot to TemporaryQueue/hardware_history.jsonl')
    shw.add_argument('--log-path', default='TemporaryQueue/hardware_history.jsonl', help='Workspace-relative JSONL path for hardware snapshots')
    shw.add_argument('--gate', action='store_true', help='Evaluate CPU/mem/disk usage against thresholds (automation)')
    shw.add_argument('--strict', action='store_true', help='With --gate: exit non-zero if thresholds exceeded')
    shw.add_argument('--cpu-max', type=float, dest='cpu_max', default=None, help='With --gate: max allowed CPU percent')
    shw.add_argument('--mem-max', type=float, dest='mem_max', default=None, help='With --gate: max allowed memory percent')
    shw.add_argument('--disk-max', type=float, dest='disk_max', default=None, help='With --gate: max allowed disk percent')
    shw.add_argument('--require-ok', action='store_true', help='With --gate: fail gate if snapshot cannot be obtained')
    shw.set_defaults(func=cmd_hw)

    si = sub.add_parser('index', help='Rebuild and summarize semantic index')
    si.add_argument('--show-ids', action='store_true', help='Include sorted ids in output')
    si.set_defaults(func=cmd_index)

    ssnap = sub.add_parser('snapshot', help='Export a compact snapshot zip (config, ActiveSpace, recent LongTermStore)')
    ssnap.add_argument('--out', default=None, help='Output zip file path')
    ssnap.add_argument('--collectors', type=int, default=12, help='Recent collector files from LongTermStore/ActiveSpace')
    ssnap.add_argument('--semantic', type=int, default=50, help='Recent semantic JSON files to include')
    ssnap.set_defaults(func=cmd_snapshot)

    sbu = sub.add_parser('backup', help='Backup repo to external archive (Git-only files)')
    sbu.add_argument('--archive-root', default=None, help='Archive root dir (or set AI_ALGORITHMS_ARCHIVE_ROOT)')
    sbu.add_argument('--project-name', default='AI_Algorithms', help='Project directory name inside Archive_N')
    sbu.add_argument('--mode', choices=['committed', 'tracked'], default='committed', help='committed=HEAD only; tracked=all tracked files')
    sbu.add_argument('--dry-run', action='store_true', help='Preview without copying')
    sbu.set_defaults(func=cmd_backup)

    sd = sub.add_parser('det', help='Run determinism suite')
    sd.add_argument('--quiet', action='store_true', help='Suppress intermediate prints from cycles')
    sd.set_defaults(func=cmd_det)

    sw = sub.add_parser('weights', help='Print measurement weights')
    sw.set_defaults(func=cmd_weights)

    sdm = sub.add_parser('determinism', help='Print determinism settings')
    sdm.set_defaults(func=cmd_determinism)

    sds = sub.add_parser('det-set', help='Toggle deterministic mode and/or set fixed timestamp')
    g = sds.add_mutually_exclusive_group()
    g.add_argument('--on', action='store_true', help='Enable deterministic mode')
    g.add_argument('--off', action='store_true', help='Disable deterministic mode')
    sds.add_argument('--fixed-timestamp', help='Set fixed timestamp, e.g. 2025-01-01T00:00:00Z')
    sds.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    sds.set_defaults(func=cmd_det_set)

    

    sdr = sub.add_parser('det-report', help='Show determinism report (latest or by id)')
    sdr.add_argument('--latest', action='store_true', help='Use the most recent determinism report in ActiveSpace')
    sdr.add_argument('--id', default='det_suite', help='Determinism report id (defaults to det_suite)')
    sdr.add_argument('--raw', action='store_true', help='Print raw report JSON')
    sdr.add_argument('--strict', action='store_true', help='Exit non-zero if overall_passed is false')
    sdr.set_defaults(func=cmd_det_report)

    sgc = sub.add_parser('gc', help='Housekeeping: prune old collectors, trim activity cycles, clean TemporaryQueue')
    sgc.add_argument('--collectors', type=int, default=50, help='Keep most-recent N collector files (default 50)')
    sgc.add_argument('--temp-days', type=int, default=7, help='Delete TemporaryQueue files older than N days (default 7)')
    sgc.add_argument('--cycles', type=int, default=200, help='Cap for activity cycles (default 200)')
    sgc.add_argument('--dry-run', action='store_true', help='Preview changes without deleting (default)')
    sgc.add_argument('--yes', dest='dry_run', action='store_false', help='Apply deletions and trims')
    sgc.set_defaults(func=cmd_gc, dry_run=True)

    spolicy = sub.add_parser('policy', help='View or update activation policy thresholds')
    sp_sub = spolicy.add_subparsers(dest='policy_cmd', required=True)
    sp_show = sp_sub.add_parser('show', help='Show current policy activation thresholds')
    sp_show.set_defaults(func=cmd_policy_show)
    sp_set = sp_sub.add_parser('set', help='Update policy activation thresholds')
    sp_set.add_argument('--sel-min-ben-syn', type=float, dest='sel_min_ben_syn', help='Min selection score for beneficial+synthesis fast-path (default 0.4)')
    sp_set.add_argument('--composite-activate', type=float, dest='composite_activate', help='Composite score threshold to activate (default 0.55)')
    sp_set.add_argument('--dry-run', action='store_true', help='Preview configuration changes without writing')
    sp_set.set_defaults(func=cmd_policy_set, dry_run=False)
    sp_eval = sp_sub.add_parser('eval', help='Evaluate activation rate over recent cycles under thresholds')
    sp_eval.add_argument('--recent', type=int, default=50, help='Number of recent cycles to evaluate')
    sp_eval.add_argument('--sel-min-ben-syn', type=float, dest='sel_min_ben_syn', help='Candidate min selection score for beneficial+synthesis')
    sp_eval.add_argument('--composite-activate', type=float, dest='composite_activate', help='Candidate composite score threshold')
    sp_eval.add_argument('--detail', action='store_true', help='Include per-item decisions')
    sp_eval.set_defaults(func=cmd_policy_eval)
    sp_tune = sp_sub.add_parser('tune', help='Search thresholds to target an activation rate')
    sp_tune.add_argument('--target-rate', type=float, required=True, help='Desired activation rate (0..1)')
    sp_tune.add_argument('--recent', type=int, default=50, help='Number of recent cycles to consider')
    sp_tune.add_argument('--sel-range', dest='sel_range', help='Range spec a:b:c for sel_min_ben_syn (defaults around current)')
    sp_tune.add_argument('--comp-range', dest='comp_range', help='Range spec x:y:z for composite_activate (defaults around current)')
    sp_tune.add_argument('--max-pairs', type=int, default=500, help='Cap number of threshold pairs to evaluate')
    sp_tune.add_argument('--apply', action='store_true', help='Write recommended thresholds to config.json')
    sp_tune.set_defaults(func=cmd_policy_tune)
    sp_list = sp_sub.add_parser('list-presets', help='List built-in activation presets')
    sp_list.set_defaults(func=cmd_policy_list)
    sp_apply = sp_sub.add_parser('apply', help='Apply a built-in activation preset to config.json')
    sp_apply.add_argument('--name', required=True, choices=['conservative','balanced','aggressive'])
    sp_apply.add_argument('--dry-run', action='store_true')
    sp_apply.set_defaults(func=cmd_policy_apply)

    

    # Diagnose environment and interpreter
    sdiag = sub.add_parser('diagnose', help='Print environment and interpreter diagnostics')
    sdiag.set_defaults(func=cmd_diagnose)

    sadv = sub.add_parser('adversarial', help='Run deterministic adversarial scenario and emit JSON report')
    sadv.add_argument('--scenario', required=True, help='Scenario id (e.g., S1_small_noise)')
    sadv.add_argument('--seed', default=None, help='Optional global seed string override')
    sadv.add_argument('--no-write', dest='no_write', action='store_true', help='Do not write report JSON to disk')
    sadv.add_argument('--report-dir', dest='report_dir', default=None, help='Directory to write report JSON (default TemporaryQueue)')
    gdet = sadv.add_mutually_exclusive_group()
    gdet.add_argument('--deterministic', action='store_true', help='Force deterministic_mode=True for the scenario run')
    gdet.add_argument('--non-deterministic', dest='non_deterministic', action='store_true', help='Force deterministic_mode=False for the scenario run')
    sadv.set_defaults(func=cmd_adversarial)

    

    args = p.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
