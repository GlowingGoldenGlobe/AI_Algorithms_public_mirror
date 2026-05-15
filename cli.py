import argparse
import html
import json
import math
import os
import sys
import subprocess
import contextlib
import io
import zipfile
import hashlib
import shutil
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from module_determinism import evaluate_determinism_suite, print_determinism
from module_measure import print_weights, summarize_measurement_adequacy
from module_integration import RelationalMeasurement
from module_integration import (
    build_ai_brain_durable_contract_alignment_summary,
    build_mirrored_parameter_review_summary,
    build_multi_location_comprehension_review_summary,
    build_retained_memory_capability_measurement_summary,
)
from module_metrics import (
    build_graph_metric_inputs,
    build_composed_graph_metrics,
    build_learning_readiness_verdict,
    build_retained_storage_pressure_metrics,
)
from module_storage import build_ai_brain_durable_memory_contract_snapshot
from module_relational_adapter import summarize_record_categorized_context
from module_retrieval import (
    build_categorized_context_profile,
    summarize_reference_use,
    summarize_categorized_context_join_quality,
)
from module_composition_contracts import (
    build_dry_run_composition_response,
    compute_composition_request_id,
    validate_composition_request,
)
from module_tools import build_semantic_index, _load_config, canonical_json_bytes, safe_join, sanitize_id

BASE = os.path.dirname(os.path.abspath(__file__))
VISUAL_PIPELINE_REVIEW_MARKER = 'ai_brain_visual_pipeline.teacher_review_sample_bundle.v1'
TEACHER_REVIEW_ADAPTER_PURPOSE = 'teacher_curated_visual_pipeline_interest_translation'
INBOUND_INTEREST_REVIEW_MARKER = 'ai_algorithms.review_only_inbound_interest_evidence_adapter.v1'
ACCEPTED_REVIEW_DESTINATIONS = ('same_tier_later', 'bounded_scale_up_review')

DEFAULT_BLENDER_COMPOSITION_CONFIG = {
    'enabled': False,
    'transport': {
        'mode': 'json_over_tcp',
        'host': '127.0.0.1',
        'port': 9101,
    },
    'launcher': {
        'blender_executable': '',
        'controller_entrypoint': 'scripts/blender_composition_receiver.py',
        'clean_profile': True,
        'startup_timeout_sec': 30,
    },
    'artifacts': {
        'artifact_root': 'TemporaryQueue/blender_composition',
        'request_subdir': 'requests',
        'response_subdir': 'responses',
        'export_subdir': 'exports',
    },
    'defaults': {
        'action': 'export_scene',
        'scene_id': 'scene_demo',
        'recipe_id': 'recipe_demo',
        'recipe_version': '0.1.0',
        'export_format': 'ply',
        'units': 'meters',
    },
}


def _write_config(cfg: dict):
    path = os.path.join(BASE, 'config.json')
    os.makedirs(BASE, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    try:
        from module_tools import _clear_config_cache
        _clear_config_cache()
    except Exception:
        pass


def _deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _get_blender_composition_config(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    source_cfg = cfg if isinstance(cfg, dict) else (_load_config() or {})
    block = source_cfg.get('blender_composition') if isinstance(source_cfg, dict) else {}
    if not isinstance(block, dict):
        block = {}
    return _deep_merge_dicts(DEFAULT_BLENDER_COMPOSITION_CONFIG, block)


def _get_cli_timestamp(cfg: Optional[Dict[str, Any]] = None) -> str:
    source_cfg = cfg if isinstance(cfg, dict) else (_load_config() or {})
    det = source_cfg.get('determinism') if isinstance(source_cfg, dict) else {}
    if isinstance(det, dict) and bool(det.get('deterministic_mode')):
        fixed = det.get('fixed_timestamp')
        if isinstance(fixed, str) and fixed:
            return fixed
        return '1970-01-01T00:00:00Z'
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _resolve_cli_output_path(path_value: Optional[str]) -> Optional[str]:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    normalized = path_value.strip().replace('/', os.sep)
    if os.path.isabs(normalized):
        return normalized
    return safe_join(BASE, normalized)


def _default_action_args(action: str, scene_id: str, export_format: str, artifact_root: str) -> Dict[str, Any]:
    export_relpath = f'{artifact_root}/exports/{scene_id}.{export_format}'
    if action == 'load_environment':
        return {
            'scene_id': scene_id,
            'environment_id': 'environment_default',
            'reset_scene': True,
        }
    if action == 'add_light':
        return {
            'scene_id': scene_id,
            'light_id': 'key_light',
            'light_type': 'SUN',
            'intensity': 1.0,
        }
    if action == 'set_camera':
        return {
            'scene_id': scene_id,
            'camera_id': 'camera_main',
            'position': [3.0, -3.0, 2.0],
            'target': [0.0, 0.0, 0.0],
            'lens_mm': 50,
        }
    if action == 'apply_material':
        return {
            'scene_id': scene_id,
            'object_id': 'subject_001',
            'material_id': 'material_default',
        }
    if action == 'validate_scene':
        return {
            'scene_id': scene_id,
            'checks': [
                'object_count_matches_manifest',
                'camera_present',
                'light_present',
                'bounds_finite',
            ],
        }
    return {
        'scene_id': scene_id,
        'export': {
            'format': export_format,
            'path': export_relpath,
        },
    }


def _default_expected_outputs(action: str, scene_id: str, export_format: str, artifact_root: str) -> List[Dict[str, Any]]:
    base_outputs = {
        'load_environment': [
            {'kind': 'scene_state', 'path': f'{artifact_root}/responses/{scene_id}_load_environment.json'},
        ],
        'add_light': [
            {'kind': 'scene_state', 'path': f'{artifact_root}/responses/{scene_id}_add_light.json'},
        ],
        'set_camera': [
            {'kind': 'scene_state', 'path': f'{artifact_root}/responses/{scene_id}_set_camera.json'},
        ],
        'apply_material': [
            {'kind': 'scene_state', 'path': f'{artifact_root}/responses/{scene_id}_apply_material.json'},
        ],
        'validate_scene': [
            {'kind': 'validation_summary', 'path': f'{artifact_root}/responses/{scene_id}_validation_summary.json'},
        ],
        'export_scene': [
            {'kind': 'export_asset', 'path': f'{artifact_root}/exports/{scene_id}.{export_format}'},
            {'kind': 'scene_manifest', 'path': f'{artifact_root}/responses/{scene_id}_scene_manifest.json'},
            {'kind': 'validation_summary', 'path': f'{artifact_root}/responses/{scene_id}_validation_summary.json'},
        ],
    }
    return list(base_outputs.get(action, base_outputs['export_scene']))


def _build_compose_request_payload(
    cfg: Dict[str, Any],
    action: str,
    scene_id: str,
    recipe_id: str,
    recipe_version: str,
    export_format: str,
    artifact_root: str,
    task_plan_id: str,
) -> Dict[str, Any]:
    comp_cfg = _get_blender_composition_config(cfg)
    transport = comp_cfg.get('transport') if isinstance(comp_cfg.get('transport'), dict) else {}
    launcher = comp_cfg.get('launcher') if isinstance(comp_cfg.get('launcher'), dict) else {}
    timestamp = _get_cli_timestamp(cfg)

    request = {
        'version': '1.0',
        'kind': 'blender_composition_request',
        'created_at': timestamp,
        'task_plan_id': task_plan_id,
        'determinism': {
            'deterministic_mode': bool((cfg.get('determinism') or {}).get('deterministic_mode')),
            'fixed_timestamp': (cfg.get('determinism') or {}).get('fixed_timestamp'),
            '3d_seed': (cfg.get('determinism') or {}).get('3d_seed'),
        },
        'transport': {
            'mode': str(transport.get('mode') or 'json_over_tcp'),
            'host': str(transport.get('host') or '127.0.0.1'),
            'port': int(transport.get('port') or 9101),
        },
        'launcher': {
            'dry_run': not bool(comp_cfg.get('enabled')),
            'blender_executable': str(launcher.get('blender_executable') or ''),
            'controller_entrypoint': str(launcher.get('controller_entrypoint') or 'scripts/blender_composition_receiver.py'),
            'clean_profile': bool(launcher.get('clean_profile', True)),
        },
        'request': {
            'scene_id': scene_id,
            'recipe_id': recipe_id,
            'recipe_version': recipe_version,
            'action': action,
            'action_args': _default_action_args(action, scene_id, export_format, artifact_root),
            'expected_outputs': _default_expected_outputs(action, scene_id, export_format, artifact_root),
        },
    }
    request['request_id'] = compute_composition_request_id(request)
    validate_composition_request(request)
    return request


def cmd_compose_request(args):
    cfg = _load_config() or {}
    comp_cfg = _get_blender_composition_config(cfg)
    defaults = comp_cfg.get('defaults') if isinstance(comp_cfg.get('defaults'), dict) else {}
    artifacts = comp_cfg.get('artifacts') if isinstance(comp_cfg.get('artifacts'), dict) else {}

    action = str(getattr(args, 'action', None) or defaults.get('action') or 'export_scene')
    scene_id = sanitize_id(str(getattr(args, 'scene_id', None) or defaults.get('scene_id') or 'scene_demo'))
    recipe_id = sanitize_id(str(getattr(args, 'recipe_id', None) or defaults.get('recipe_id') or 'recipe_demo'))
    recipe_version = str(getattr(args, 'recipe_version', None) or defaults.get('recipe_version') or '0.1.0')
    export_format = str(getattr(args, 'export_format', None) or defaults.get('export_format') or 'ply').lower()
    artifact_root = str(artifacts.get('artifact_root') or 'TemporaryQueue/blender_composition').rstrip('/\\')
    request = _build_compose_request_payload(
        cfg,
        action,
        scene_id,
        recipe_id,
        recipe_version,
        export_format,
        artifact_root,
        task_plan_id='07',
    )

    out_path = _resolve_cli_output_path(getattr(args, 'out', None))
    if out_path:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as handle:
            json.dump(request, handle, ensure_ascii=False, indent=2)

    print(json.dumps(request, ensure_ascii=False, indent=2))


def cmd_compose_response(args):
    cfg = _load_config() or {}
    request_path = _resolve_cli_output_path(getattr(args, 'request', None))
    if request_path:
        with open(request_path, 'r', encoding='utf-8') as handle:
            starter_request = json.load(handle)
    else:
        comp_cfg = _get_blender_composition_config(cfg)
        defaults = comp_cfg.get('defaults') if isinstance(comp_cfg.get('defaults'), dict) else {}
        artifacts = comp_cfg.get('artifacts') if isinstance(comp_cfg.get('artifacts'), dict) else {}
        action = str(getattr(args, 'action', None) or defaults.get('action') or 'export_scene')
        scene_id = sanitize_id(str(getattr(args, 'scene_id', None) or defaults.get('scene_id') or 'scene_demo'))
        recipe_id = sanitize_id(str(getattr(args, 'recipe_id', None) or defaults.get('recipe_id') or 'recipe_demo'))
        recipe_version = str(getattr(args, 'recipe_version', None) or defaults.get('recipe_version') or '0.1.0')
        export_format = str(getattr(args, 'export_format', None) or defaults.get('export_format') or 'ply').lower()
        artifact_root = str(artifacts.get('artifact_root') or 'TemporaryQueue/blender_composition').rstrip('/\\')
        starter_request = _build_compose_request_payload(
            cfg,
            action,
            scene_id,
            recipe_id,
            recipe_version,
            export_format,
            artifact_root,
            task_plan_id='07',
        )

    response = build_dry_run_composition_response(
        starter_request,
        status=str(getattr(args, 'status', None) or 'completed'),
        error_code=getattr(args, 'error_code', None),
        error_message=getattr(args, 'error_message', None),
    )

    out_path = _resolve_cli_output_path(getattr(args, 'out', None))
    if out_path:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as handle:
            json.dump(response, handle, ensure_ascii=False, indent=2)

    print(json.dumps(response, ensure_ascii=False, indent=2))


def cmd_compose_receiver_smoke(args):
    from module_composition_contracts import build_receiver_boundary_smoke_result

    cfg = _load_config() or {}
    request_path = _resolve_cli_output_path(getattr(args, 'request', None))
    if request_path:
        with open(request_path, 'r', encoding='utf-8') as handle:
            starter_request = json.load(handle)
    else:
        comp_cfg = _get_blender_composition_config(cfg)
        defaults = comp_cfg.get('defaults') if isinstance(comp_cfg.get('defaults'), dict) else {}
        artifacts = comp_cfg.get('artifacts') if isinstance(comp_cfg.get('artifacts'), dict) else {}
        action = str(getattr(args, 'action', None) or defaults.get('action') or 'export_scene')
        scene_id = sanitize_id(str(getattr(args, 'scene_id', None) or defaults.get('scene_id') or 'scene_demo'))
        recipe_id = sanitize_id(str(getattr(args, 'recipe_id', None) or defaults.get('recipe_id') or 'recipe_demo'))
        recipe_version = str(getattr(args, 'recipe_version', None) or defaults.get('recipe_version') or '0.1.0')
        export_format = str(getattr(args, 'export_format', None) or defaults.get('export_format') or 'ply').lower()
        artifact_root = str(artifacts.get('artifact_root') or 'TemporaryQueue/blender_composition').rstrip('/\\')
        starter_request = _build_compose_request_payload(
            cfg,
            action,
            scene_id,
            recipe_id,
            recipe_version,
            export_format,
            artifact_root,
            task_plan_id='09',
        )

    known_request_ids = [str(value) for value in (getattr(args, 'known_request_id', None) or []) if isinstance(value, str)]
    if bool(getattr(args, 'duplicate_replay', False)):
        known_request_ids.append(str(starter_request['request_id']))

    result = build_receiver_boundary_smoke_result(
        starter_request,
        receiver_status=str(getattr(args, 'receiver_status', None) or 'accepted'),
        runtime_status=getattr(args, 'runtime_status', None),
        known_request_ids=known_request_ids,
        output_root=_resolve_cli_output_path(getattr(args, 'out_dir', None)),
    )

    print(json.dumps({
        'ok': True,
        'request_id': result['request_id'],
        'receiver_decision': result['receiver_decision'],
        'duplicate_replay': result['duplicate_replay'],
        'first_acceptance': result['first_acceptance'],
        'receiver_status': result['status_boundary']['receiver_status'],
        'runtime_status': result['status_boundary']['runtime_status'],
        'runtime_phase_present': result['status_boundary']['runtime_phase_present'],
        'runtime_request_schema_version': result['runtime_request']['schema_version'],
        'receiver_response': result['receiver_response'],
        'runtime_response': result['runtime_response'],
    }, ensure_ascii=False, indent=2))


def cmd_compose_runtime_artifacts(args):
    from module_composition_contracts import (
        build_runtime_recipe_sidecar,
        build_runtime_scene_manifest,
        build_runtime_validation_summary,
        build_runtime_composition_request_artifact,
        write_runtime_artifact_bundle,
    )

    cfg = _load_config() or {}
    request_path = _resolve_cli_output_path(getattr(args, 'request', None))
    if request_path:
        with open(request_path, 'r', encoding='utf-8') as handle:
            starter_request = json.load(handle)
    else:
        comp_cfg = _get_blender_composition_config(cfg)
        defaults = comp_cfg.get('defaults') if isinstance(comp_cfg.get('defaults'), dict) else {}
        artifacts = comp_cfg.get('artifacts') if isinstance(comp_cfg.get('artifacts'), dict) else {}
        action = str(getattr(args, 'action', None) or defaults.get('action') or 'export_scene')
        scene_id = sanitize_id(str(getattr(args, 'scene_id', None) or defaults.get('scene_id') or 'scene_demo'))
        recipe_id = sanitize_id(str(getattr(args, 'recipe_id', None) or defaults.get('recipe_id') or 'recipe_demo'))
        recipe_version = str(getattr(args, 'recipe_version', None) or defaults.get('recipe_version') or '0.1.0')
        export_format = str(getattr(args, 'export_format', None) or defaults.get('export_format') or 'ply').lower()
        artifact_root = str(artifacts.get('artifact_root') or 'TemporaryQueue/blender_composition').rstrip('/\\')
        starter_request = _build_compose_request_payload(
            cfg,
            action,
            scene_id,
            recipe_id,
            recipe_version,
            export_format,
            artifact_root,
            task_plan_id='08',
        )

    out_dir = _resolve_cli_output_path(getattr(args, 'out_dir', None))
    runtime_request = build_runtime_composition_request_artifact(
        starter_request,
        output_root=out_dir,
    )
    recipe_sidecar = build_runtime_recipe_sidecar(runtime_request)
    scene_manifest = build_runtime_scene_manifest(runtime_request, recipe_sidecar)
    validation_summary = build_runtime_validation_summary(runtime_request, recipe_sidecar, scene_manifest)
    bundle = write_runtime_artifact_bundle(
        starter_request,
        output_root=out_dir,
        emit_claimed=bool(getattr(args, 'emit_claimed', False)),
        emit_running=bool(getattr(args, 'emit_running', False)),
        emit_validated=bool(getattr(args, 'emit_validated', False)),
        emit_measure_handoff_event=bool(getattr(args, 'emit_measure_handoff_event', False)),
        emit_response=bool(getattr(args, 'emit_response', False)),
        response_status=str(getattr(args, 'response_status', None) or 'completed'),
        emit_measurement_handoff=bool(getattr(args, 'emit_measurement_handoff', False)),
        complete_measurement_handoff=bool(getattr(args, 'complete_measurement_handoff', False)),
        emit_released=bool(getattr(args, 'emit_released', False)),
        emit_failed=bool(getattr(args, 'emit_failed', False)),
        failure_error_code=getattr(args, 'failure_error_code', None),
        failure_error_message=getattr(args, 'failure_error_message', None),
        recipe_sidecar=recipe_sidecar,
        scene_manifest=scene_manifest,
        validation_summary=validation_summary,
    )
    print(json.dumps({
        'ok': True,
        'request_id': bundle['request']['request_id'],
        'request_path': bundle['paths']['request'],
        'recipe_sidecar_path': bundle['paths']['recipe_sidecar'],
        'scene_manifest_path': bundle['paths']['scene_manifest'],
        'validation_summary_path': bundle['paths']['validation_summary'],
        'response_path': bundle['paths']['response'] if bundle.get('response') is not None else None,
        'measurement_path': bundle['paths']['measurement'] if bundle.get('measurement_handoff') is not None else None,
        'lineage_path': bundle['paths']['lineage'] if bundle.get('lineage') is not None else None,
        'ledger_path': bundle['paths']['ledger'],
        'events': [event['event_type'] for event in bundle['events']],
    }, ensure_ascii=False, indent=2))

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


def _count_files_recursive(dir_path):
    count = 0
    try:
        for _dirpath, _dirnames, filenames in os.walk(dir_path):
            count += len(filenames)
    except Exception:
        return count
    return count


def _get_stage7_run_dirs_sorted(stage7_root):
    rows = []
    try:
        names = os.listdir(stage7_root)
    except Exception:
        return []
    for name in names:
        if not isinstance(name, str) or not name.startswith('orch_blender_cycle_'):
            continue
        path = safe_join(stage7_root, name)
        if not os.path.isdir(path):
            continue
        try:
            rows.append((path, os.path.getmtime(path), name))
        except Exception:
            rows.append((path, 0.0, name))
    rows.sort(key=lambda item: (item[1], item[2]), reverse=True)
    return [path for path, _mtime, _name in rows]


def _prune_stage7_run_dirs(stage7_root, keep_runs, dry_run=True):
    keep = max(0, int(keep_runs))
    run_dirs = _get_stage7_run_dirs_sorted(stage7_root)
    to_delete = run_dirs[keep:]
    files_deleted = sum(_count_files_recursive(path) for path in to_delete)
    folders_deleted = 0
    if not dry_run:
        for path in to_delete:
            try:
                shutil.rmtree(path)
                folders_deleted += 1
            except Exception:
                continue
    else:
        folders_deleted = len(to_delete)
    return {
        'stage7_run_folders_deleted': folders_deleted,
        'stage7_run_files_deleted': files_deleted,
        'stage7_run_folder_count': len(run_dirs),
        'kept_stage7_runs': keep,
    }


def cmd_gc(args):
    # Parameters
    keep_collectors = max(0, getattr(args, 'collectors', 50))
    temp_days = max(0, getattr(args, 'temp_days', 7))
    trim_cycles = max(0, getattr(args, 'cycles', 200))
    keep_stage7_runs = max(0, getattr(args, 'stage7_runs', 3))
    dry_run = getattr(args, 'dry_run', True)

    now = datetime.now(timezone.utc).timestamp()
    changes = {
        'dry_run': bool(dry_run),
        'collector_files_deleted': 0,
        'temporary_files_deleted': 0,
        'stage7_run_folders_deleted': 0,
        'stage7_run_files_deleted': 0,
        'stage7_run_folder_count': 0,
        'activity_cycles_trimmed': 0,
        'kept_collectors': keep_collectors,
        'kept_stage7_runs': keep_stage7_runs,
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
            for dirpath, _dirnames, filenames in os.walk(tmp_dir):
                for name in filenames:
                    p = os.path.join(dirpath, name)
                    try:
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

    # Prune same-day stage-7 run directories by retention count. These folders can
    # exceed the TemporaryQueue file cap before age-based temp cleanup triggers.
    try:
        stage7_root = safe_join(tmp_dir, 'stage7_scheduler_composition_routing')
        changes.update(_prune_stage7_run_dirs(stage7_root, keep_stage7_runs, dry_run=dry_run))
    except Exception:
        pass

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


def _summarize_graph_metrics(relational_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"available": False, "metrics": {}}
    try:
        inputs = build_graph_metric_inputs(relational_state)
        composed = build_composed_graph_metrics(relational_state, metrics_payload=inputs)
    except Exception:
        return summary

    if not bool(composed.get("available")):
        return summary

    metrics = composed.get("metrics") if isinstance(composed.get("metrics"), dict) else {}
    trimmed: Dict[str, Any] = {
        "node_count": metrics.get("node_count"),
        "edge_count": metrics.get("edge_count"),
        "density": metrics.get("density"),
        "dominant_relation_type": metrics.get("dominant_relation_type"),
        "top_nodes_by_total_degree": metrics.get("top_nodes_by_total_degree"),
    }
    summary["available"] = True
    summary["metrics"] = {k: v for k, v in trimmed.items() if v is not None}
    summary["metrics_hash"] = composed.get("metrics_hash")
    if isinstance(inputs, dict) and inputs.get("available"):
        metrics_inputs = inputs.get("metrics") if isinstance(inputs.get("metrics"), dict) else {}
        snapshot_hash = metrics_inputs.get("snapshot_hash")
        if snapshot_hash:
            summary["snapshot_hash"] = snapshot_hash
    return summary


def _collect_spatial_overview(base_dir: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    base = base_dir or BASE
    semantic_dir = os.path.join(base, "LongTermStore", "Semantic")
    if not os.path.isdir(semantic_dir):
        return {"records": [], "total_records": 0}

    files = _list_recent_files(semantic_dir, suffix=".json", limit=limit)
    overview: List[Dict[str, Any]] = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except Exception:
            continue

        record_id = record.get("id") if isinstance(record.get("id"), str) else None
        if not record_id:
            record_id = os.path.splitext(os.path.basename(path))[0]

        rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
        spatial_measurement = rel_state.get("spatial_measurement") if isinstance(rel_state.get("spatial_measurement"), dict) else {}
        artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
        spatial_artifacts = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
        latest_snapshot = spatial_artifacts.get("latest") if isinstance(spatial_artifacts.get("latest"), dict) else {}

        measurement_hash = spatial_artifacts.get("measurement_hash") if isinstance(spatial_artifacts.get("measurement_hash"), str) else None
        if not measurement_hash and spatial_measurement:
            try:
                measurement_hash = hashlib.sha256(canonical_json_bytes(spatial_measurement)).hexdigest()
            except Exception:
                measurement_hash = None

        meta = spatial_measurement.get("meta") if isinstance(spatial_measurement.get("meta"), dict) else {}
        measurement_timestamp = None
        if isinstance(latest_snapshot.get("timestamp"), str):
            measurement_timestamp = latest_snapshot.get("timestamp")
        elif isinstance(meta.get("timestamp"), str):
            measurement_timestamp = meta.get("timestamp")

        graph_summary = _summarize_graph_metrics(rel_state)

        overview.append(
            {
                "record_id": record_id,
                "cycle_id": record.get("cycle_id") or (record.get("cycle_artifact") or {}).get("cycle_id"),
                "snapshot_relative_path": latest_snapshot.get("relative_path"),
                "snapshot_hash": latest_snapshot.get("hash"),
                "measurement_hash": measurement_hash,
                "measurement_timestamp": measurement_timestamp,
                "cache_hit": bool(spatial_measurement.get("cache_hit")) if isinstance(spatial_measurement.get("cache_hit"), bool) else False,
                "graph_metrics": graph_summary,
            }
        )

    return {"records": overview, "total_records": len(overview)}


def _collect_spatial_telemetry(base_dir: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    base = base_dir or BASE
    telemetry_path = os.path.join(
        base,
        "LongTermStore",
        "Telemetry",
        "SpatialMeasurements",
        "events.jsonl",
    )
    if not os.path.exists(telemetry_path):
        return {"events": [], "total_events": 0, "status_counts": {}, "limit": limit}

    recent_lines: deque[str] = deque(maxlen=max(1, limit))
    total_events = 0
    try:
        with open(telemetry_path, "r", encoding="utf-8") as handle:
            for line in handle:
                total_events += 1
                stripped = line.strip()
                if stripped:
                    recent_lines.append(stripped)
    except Exception:
        return {"events": [], "total_events": total_events, "status_counts": {}, "limit": limit}

    events: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for raw in recent_lines:
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        status = payload.get("status") if isinstance(payload.get("status"), str) else None
        if status:
            status_counts[status] += 1
        events.append(
            {
                "sequence_index": payload.get("sequence_index"),
                "status": status,
                "reason": payload.get("reason") or payload.get("reason_detail"),
                "latency_band": payload.get("latency_band"),
                "cache_hit": payload.get("cache_hit"),
                "measurement_hash": payload.get("measurement_hash"),
                "snapshot_hash": payload.get("snapshot_hash"),
                "timestamp_fixed": payload.get("timestamp_fixed"),
            }
        )

    events.sort(key=lambda item: (item.get("sequence_index") or 0), reverse=True)
    return {
        "events": events,
        "total_events": total_events,
        "status_counts": dict(status_counts),
        "limit": limit,
    }


def _summarize_measurement_adequacy(
    *,
    spatial_overview: Optional[Dict[str, Any]] = None,
    spatial_telemetry: Optional[Dict[str, Any]] = None,
    measurement_recorded: Optional[bool] = None,
    snapshot_present: Optional[bool] = None,
    measurement_hash_present: Optional[bool] = None,
    bridge_present: Optional[bool] = None,
    telemetry_completed_present: Optional[bool] = None,
) -> Dict[str, Any]:
    return summarize_measurement_adequacy(
        spatial_overview=spatial_overview,
        spatial_telemetry=spatial_telemetry,
        measurement_recorded=measurement_recorded,
        snapshot_present=snapshot_present,
        measurement_hash_present=measurement_hash_present,
        bridge_present=bridge_present,
        telemetry_completed_present=telemetry_completed_present,
    )


def _default_categorized_context_summary() -> Dict[str, Any]:
    return {
        "record_id": None,
        "reference_record_id": None,
        "labels": [],
        "aliases": [],
        "comparison_axes": [],
        "relation_families": [],
        "bridge_sources": [],
        "scene_summary_present": False,
        "support_level": "missing",
        "reference_profile_present": False,
        "reference_labels": [],
        "reference_aliases": [],
        "reference_comparison_axes": [],
        "reference_use_score": 0.0,
        "reference_use_breakdown": {
            "label_match_count": 0,
            "alias_match_count": 0,
            "comparison_axis_match_count": 0,
        },
        "join_status": "missing",
        "join_quality": "missing",
        "persistence_status": "missing",
        "follow_through_status": "missing",
        "matched_reference_labels": [],
        "matched_reference_aliases": [],
        "matched_reference_comparison_axes": [],
        "matched_reference_category_count": 0,
        "matched_reference_term_count": 0,
        "gap_reasons": [],
    }


def _build_reference_profile_for_assessment(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    profile = build_categorized_context_profile(record)
    labels = [str(item) for item in (profile.get("labels") or []) if isinstance(item, str)]
    aliases = [str(item) for item in (profile.get("aliases") or []) if isinstance(item, str)]
    comparison_axes = [str(item) for item in (profile.get("comparison_axes") or []) if isinstance(item, str)]
    if not (labels or aliases or comparison_axes):
        return {}
    return {
        "labels": labels,
        "aliases": aliases,
        "comparison_axes": comparison_axes,
    }


def _summarize_categorized_context_bundle(
    record: Optional[Dict[str, Any]],
    *,
    reference_record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return _default_categorized_context_summary()

    rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
    semantic_summary = derived.get("categorized_context_summary") if isinstance(derived.get("categorized_context_summary"), dict) else None
    if not isinstance(semantic_summary, dict) or not semantic_summary:
        semantic_summary = summarize_record_categorized_context(record, rel_state)

    reference_profile = _build_reference_profile_for_assessment(reference_record)
    reference_labels = [str(item) for item in reference_profile.get("labels", []) if isinstance(item, str)]
    reference_aliases = [str(item) for item in reference_profile.get("aliases", []) if isinstance(item, str)]
    reference_axes = [str(item) for item in reference_profile.get("comparison_axes", []) if isinstance(item, str)]
    join_quality = summarize_categorized_context_join_quality(semantic_summary, reference_profile)
    semantic_level = str(semantic_summary.get("support_level") or "missing")
    reference_use_score = 0.0
    reference_use_breakdown = {
        "label_match_count": 0,
        "alias_match_count": 0,
        "comparison_axis_match_count": 0,
    }
    if bool(join_quality.get("reference_profile_present")):
        reference_use = summarize_reference_use(
            record,
            {
                "reference_labels": list(reference_labels) + list(reference_aliases),
                "comparison_axes": list(reference_axes),
            },
        )
        reference_use_breakdown = {
            "label_match_count": int((reference_use.get("reference_use_breakdown") or {}).get("label_match_count", 0) or 0),
            "alias_match_count": int((reference_use.get("reference_use_breakdown") or {}).get("alias_match_count", 0) or 0),
            "comparison_axis_match_count": int(
                (reference_use.get("reference_use_breakdown") or {}).get("comparison_axis_match_count", 0) or 0
            ),
        }
        reference_use_score = float(reference_use.get("reference_use_score", 0.0) or 0.0)

    return {
        "record_id": record.get("id") if isinstance(record.get("id"), str) else None,
        "reference_record_id": reference_record.get("id") if isinstance(reference_record, dict) and isinstance(reference_record.get("id"), str) else None,
        "labels": list(semantic_summary.get("labels") or []),
        "aliases": list(semantic_summary.get("aliases") or []),
        "comparison_axes": list(semantic_summary.get("comparison_axes") or []),
        "relation_families": list(semantic_summary.get("relation_families") or []),
        "bridge_sources": list(semantic_summary.get("bridge_sources") or []),
        "scene_summary_present": bool(semantic_summary.get("scene_summary_present")),
        "support_level": semantic_level,
        "reference_profile_present": bool(join_quality.get("reference_profile_present")),
        "reference_labels": reference_labels,
        "reference_aliases": reference_aliases,
        "reference_comparison_axes": reference_axes,
        "reference_use_score": reference_use_score,
        "reference_use_breakdown": reference_use_breakdown,
        "join_status": str(join_quality.get("join_status") or "missing"),
        "join_quality": str(join_quality.get("join_quality") or "missing"),
        "persistence_status": str(join_quality.get("persistence_status") or "missing"),
        "follow_through_status": str(join_quality.get("follow_through_status") or "missing"),
        "matched_reference_labels": list(join_quality.get("matched_reference_labels") or []),
        "matched_reference_aliases": list(join_quality.get("matched_reference_aliases") or []),
        "matched_reference_comparison_axes": list(join_quality.get("matched_reference_comparison_axes") or []),
        "matched_reference_category_count": int(join_quality.get("matched_reference_category_count") or 0),
        "matched_reference_term_count": int(join_quality.get("matched_reference_term_count") or 0),
        "gap_reasons": _normalize_string_list(join_quality.get("gap_reasons"), limit=8),
    }


def _build_categorized_context_inventory_entry(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {"reference_profile_present": False, "support_level": "missing", "join_status": "missing"}

    rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
    semantic_summary = derived.get("categorized_context_summary") if isinstance(derived.get("categorized_context_summary"), dict) else None
    if not isinstance(semantic_summary, dict) or not semantic_summary:
        semantic_summary = summarize_record_categorized_context(record, rel_state)

    reference_profile = _build_reference_profile_for_assessment(record)
    join_quality = summarize_categorized_context_join_quality(semantic_summary, reference_profile)
    return {
        "reference_profile_present": bool(join_quality.get("reference_profile_present")),
        "support_level": str(semantic_summary.get("support_level") or "missing"),
        "join_status": str(join_quality.get("join_status") or "missing"),
        "join_quality": str(join_quality.get("join_quality") or "missing"),
        "follow_through_status": str(join_quality.get("follow_through_status") or "missing"),
        "persistence_status": str(join_quality.get("persistence_status") or "missing"),
    }


def _load_semantic_record_by_id(base_dir: str, record_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not isinstance(record_id, str) or not record_id:
        return None
    semantic_dir = os.path.join(base_dir, "LongTermStore", "Semantic")
    if not os.path.isdir(semantic_dir):
        return None
    for root, _, files in os.walk(semantic_dir):
        for name in files:
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(root, name)
            record = _load_json_file(path)
            if isinstance(record, dict) and record.get("id") == record_id:
                return record
    return None


def _collect_categorized_context_assessment(base_dir: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    base = base_dir or BASE
    semantic_dir = os.path.join(base, "LongTermStore", "Semantic")
    if not os.path.isdir(semantic_dir):
        return _default_categorized_context_summary()

    rank = {"missing": 0, "weak": 1, "strong": 2}
    best = _default_categorized_context_summary()
    best_rank = rank["missing"]

    for path in _list_recent_files(semantic_dir, suffix=".json", limit=limit):
        record = _load_json_file(path)
        if not isinstance(record, dict):
            continue
        summary = _summarize_categorized_context_bundle(record)
        current_rank = rank.get(str(summary.get("support_level") or "missing"), 0)
        if current_rank > best_rank:
            best = summary
            best_rank = current_rank
        if current_rank >= rank["strong"]:
            break

    return best


def _default_comprehension_review_summary() -> Dict[str, Any]:
    return {
        "record_id": None,
        "present": False,
        "quality": "missing",
        "summary": "No persisted comprehension review summary was found.",
        "supporting_evidence": {
            "scene_validation_present": False,
            "graph_metrics_available": False,
            "total_checks": 0,
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "scene_ids": [],
            "validation_evidence": {
                "scene_validation_present": False,
                "total_checks": 0,
                "passed": 0,
                "warnings": 0,
                "failed": 0,
            },
            "measurement_evidence": {
                "level": "missing",
                "reason": "",
                "measurement_recorded": False,
            },
            "categorized_context_evidence": {
                "support_level": "missing",
                "join_status": "missing",
                "label_count": 0,
                "alias_count": 0,
                "comparison_axis_count": 0,
                "relation_family_count": 0,
                "bridge_source_count": 0,
            },
            "retention_evidence": {
                "record_id_present": False,
                "relational_state_present": False,
                "scene_validation_summary_present": False,
            },
        },
        "observed_levels": {
            "measurement_adequacy": "missing",
            "categorized_context": "missing",
            "validation_evidence": "missing",
        },
        "rationale": "No persisted scene-validation review summary was available for operator review.",
        "unresolved_gaps": ["Persist a scene-validation review summary before treating comprehension as reviewable."],
    }


def _extract_scene_validation_summary_for_assessment(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(record, dict):
        return None
    if isinstance(record.get("scene_validation_summary"), dict):
        return dict(record.get("scene_validation_summary") or {})
    decision_trace = record.get("decision_trace") if isinstance(record.get("decision_trace"), dict) else None
    if not isinstance(decision_trace, dict):
        relational_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else None
        if isinstance(relational_state, dict):
            decision_trace = relational_state.get("decision_trace") if isinstance(relational_state.get("decision_trace"), dict) else None
    if not isinstance(decision_trace, dict):
        return None
    summary = decision_trace.get("scene_validation")
    return dict(summary) if isinstance(summary, dict) else None


def _normalize_comprehension_review_summary(
    summary: Optional[Dict[str, Any]],
    *,
    record: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(summary, dict):
        summary = _default_comprehension_review_summary()
    out = dict(summary)
    level = str(out.get("quality") or out.get("level") or "missing")
    out["quality"] = level
    if "present" not in out:
        out["present"] = bool(out)
    if "record_id" not in out:
        out["record_id"] = record.get("id") if isinstance(record, dict) and isinstance(record.get("id"), str) else None
    if not isinstance(out.get("supporting_evidence"), dict):
        out["supporting_evidence"] = {}
    if not isinstance(out.get("observed_levels"), dict):
        out["observed_levels"] = dict(_default_comprehension_review_summary()["observed_levels"])
    if not isinstance(out.get("unresolved_gaps"), list):
        out["unresolved_gaps"] = []
    return out


def _summarize_comprehension_review(
    record: Optional[Dict[str, Any]],
    *,
    measurement_adequacy: Optional[Dict[str, Any]] = None,
    categorized_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return _default_comprehension_review_summary()

    rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
    persisted_summary = (
        derived.get("comprehension_review_summary")
        if isinstance(derived.get("comprehension_review_summary"), dict)
        else {}
    )
    if persisted_summary:
        return _normalize_comprehension_review_summary(persisted_summary, record=record)

    graph_metrics = _summarize_graph_metrics(rel_state)
    graph_metrics_available = bool(graph_metrics.get("available"))
    scene_validation = _extract_scene_validation_summary_for_assessment(record)
    measurement_summary = (
        measurement_adequacy
        if isinstance(measurement_adequacy, dict)
        else (
            derived.get("measurement_adequacy_summary")
            if isinstance(derived.get("measurement_adequacy_summary"), dict)
            else {}
        )
    )
    categorized_summary = (
        categorized_context
        if isinstance(categorized_context, dict)
        else _summarize_categorized_context_bundle(record)
    )
    record_id_present = bool(
        (isinstance(record.get("id"), str) and str(record.get("id")).strip())
        or (isinstance(record.get("record_id"), str) and str(record.get("record_id")).strip())
    )
    relational_state_present = bool(rel_state)
    measurement_level = str(measurement_summary.get("level") or "missing")
    categorized_level = str(categorized_summary.get("support_level") or categorized_summary.get("level") or "missing")
    validation_level = "missing"

    if not isinstance(scene_validation, dict):
        missing = _default_comprehension_review_summary()
        missing["record_id"] = record.get("id") if isinstance(record.get("id"), str) else None
        missing["supporting_evidence"]["measurement_evidence"] = {
            "level": measurement_level,
            "reason": str(measurement_summary.get("reason") or ""),
            "measurement_recorded": bool(measurement_summary.get("signals", {}).get("measurement_recorded"))
            if isinstance(measurement_summary.get("signals"), dict)
            else False,
        }
        missing["supporting_evidence"]["categorized_context_evidence"] = {
            "support_level": categorized_level,
            "join_status": str(categorized_summary.get("join_status") or "missing"),
            "label_count": len(categorized_summary.get("labels") or []),
            "alias_count": len(categorized_summary.get("aliases") or []),
            "comparison_axis_count": len(categorized_summary.get("comparison_axes") or []),
            "relation_family_count": len(categorized_summary.get("relation_families") or []),
            "bridge_source_count": len(categorized_summary.get("bridge_sources") or []),
        }
        missing["supporting_evidence"]["retention_evidence"] = {
            "record_id_present": record_id_present,
            "relational_state_present": relational_state_present,
            "scene_validation_summary_present": False,
        }
        missing["observed_levels"] = {
            "measurement_adequacy": measurement_level,
            "categorized_context": categorized_level,
            "validation_evidence": validation_level,
        }
        if graph_metrics_available:
            missing["quality"] = "weak"
            missing["summary"] = "Structural evidence is present, but no persisted scene-validation review summary was found."
            missing["supporting_evidence"]["graph_metrics_available"] = True
            missing["rationale"] = "Graph metrics indicate structured evidence exists, but comprehension review was not persisted."
            missing["unresolved_gaps"] = ["Persist a scene-validation review summary so operators can inspect comprehension quality directly."]
        return missing

    try:
        total_checks = int(scene_validation.get("total_checks") or 0)
    except Exception:
        total_checks = 0
    try:
        passed = int(scene_validation.get("passed") or 0)
    except Exception:
        passed = 0
    try:
        warnings = int(scene_validation.get("warnings") or 0)
    except Exception:
        warnings = 0
    try:
        failed = int(scene_validation.get("failed") or 0)
    except Exception:
        failed = 0
    scene_ids = [str(item) for item in (scene_validation.get("scene_ids") or []) if isinstance(item, str)]
    validation_level = "clear" if total_checks > 0 and failed == 0 and warnings == 0 else "issues_present"

    if total_checks > 0 and failed == 0 and warnings == 0:
        quality = "strong"
        summary = f"Comprehension review passed all {total_checks} persisted scene-validation checks."
        rationale = "The persisted review summary shows a clean validation pass with no warnings or failed checks."
        unresolved_gaps: List[str] = []
    else:
        quality = "weak"
        if total_checks <= 0:
            summary = "A comprehension review summary exists, but it does not report any completed checks."
            rationale = "Review metadata is present, but the check counts are incomplete for a stronger comprehension verdict."
            unresolved_gaps = ["Persist non-zero scene-validation check counts."]
        else:
            summary = f"Comprehension review remains partial: {passed} passed, {warnings} warning, {failed} failed."
            if failed > 0:
                rationale = "One or more persisted scene-validation checks failed, so comprehension remains reviewable but not strong."
            else:
                rationale = "Only warning-level review evidence is present, so comprehension remains reviewable but not fully strong."
            unresolved_gaps = []
            if warnings > 0:
                unresolved_gaps.append("Resolve warning-level scene-validation checks for a stronger comprehension verdict.")
            if failed > 0:
                unresolved_gaps.append("Resolve failed scene-validation checks for a stronger comprehension verdict.")

    return {
        "record_id": record.get("id") if isinstance(record.get("id"), str) else None,
        "present": True,
        "quality": quality,
        "summary": summary,
        "supporting_evidence": {
            "scene_validation_present": True,
            "graph_metrics_available": graph_metrics_available,
            "total_checks": total_checks,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "scene_ids": scene_ids,
            "validation_evidence": {
                "scene_validation_present": True,
                "total_checks": total_checks,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
            },
            "measurement_evidence": {
                "level": measurement_level,
                "reason": str(measurement_summary.get("reason") or ""),
                "measurement_recorded": bool(measurement_summary.get("signals", {}).get("measurement_recorded"))
                if isinstance(measurement_summary.get("signals"), dict)
                else False,
            },
            "categorized_context_evidence": {
                "support_level": categorized_level,
                "join_status": str(categorized_summary.get("join_status") or "missing"),
                "label_count": len(categorized_summary.get("labels") or []),
                "alias_count": len(categorized_summary.get("aliases") or []),
                "comparison_axis_count": len(categorized_summary.get("comparison_axes") or []),
                "relation_family_count": len(categorized_summary.get("relation_families") or []),
                "bridge_source_count": len(categorized_summary.get("bridge_sources") or []),
            },
            "retention_evidence": {
                "record_id_present": record_id_present,
                "relational_state_present": relational_state_present,
                "scene_validation_summary_present": True,
            },
        },
        "observed_levels": {
            "measurement_adequacy": measurement_level,
            "categorized_context": categorized_level,
            "validation_evidence": validation_level,
        },
        "rationale": rationale,
        "unresolved_gaps": unresolved_gaps,
    }


def _collect_comprehension_review_assessment(
    base_dir: Optional[str] = None,
    limit: int = 5,
    *,
    measurement_adequacy: Optional[Dict[str, Any]] = None,
    categorized_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = base_dir or BASE
    semantic_dir = os.path.join(base, "LongTermStore", "Semantic")
    if not os.path.isdir(semantic_dir):
        return _default_comprehension_review_summary()

    rank = {"missing": 0, "weak": 1, "strong": 2}
    best = _default_comprehension_review_summary()
    best_rank = rank["missing"]

    for path in _list_recent_files(semantic_dir, suffix=".json", limit=limit):
        record = _load_json_file(path)
        if not isinstance(record, dict):
            continue
        summary = _summarize_comprehension_review(
            record,
            measurement_adequacy=measurement_adequacy,
            categorized_context=categorized_context,
        )
        current_rank = rank.get(str(summary.get("quality") or "missing"), 0)
        if current_rank > best_rank:
            best = summary
            best_rank = current_rank
        if current_rank >= rank["strong"]:
            break

    return best


def _summarize_learning_readiness(
    *,
    measurement_adequacy: Optional[Dict[str, Any]] = None,
    categorized_context: Optional[Dict[str, Any]] = None,
    comprehension_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    measurement_summary = measurement_adequacy if isinstance(measurement_adequacy, dict) else {}
    categorized_summary = categorized_context if isinstance(categorized_context, dict) else {}
    comprehension_summary = comprehension_review if isinstance(comprehension_review, dict) else {}

    categorized_level = categorized_summary.get("level")
    if not isinstance(categorized_level, str) or not categorized_level:
        categorized_level = categorized_summary.get("support_level")

    comprehension_level = comprehension_summary.get("level")
    if not isinstance(comprehension_level, str) or not comprehension_level:
        comprehension_level = comprehension_summary.get("quality")

    return build_learning_readiness_verdict(
        measurement_adequacy={
            "level": measurement_summary.get("level"),
            "reason": measurement_summary.get("reason"),
        },
        categorized_context={
            "level": categorized_level,
            "counts": {
                "labels": len(categorized_summary.get("labels") or []),
                "aliases": len(categorized_summary.get("aliases") or []),
                "comparison_axes": len(categorized_summary.get("comparison_axes") or []),
                "relation_families": len(categorized_summary.get("relation_families") or []),
                "bridge_sources": len(categorized_summary.get("bridge_sources") or []),
            },
        },
        comprehension_review={
            "level": comprehension_level,
            "summary": comprehension_summary.get("summary"),
            "unresolved_gaps": comprehension_summary.get("unresolved_gaps"),
            "supporting_evidence": comprehension_summary.get("supporting_evidence"),
        },
    )


def _list_spatial_snapshot_files(base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    base = base_dir or BASE
    root = os.path.join(base, "LongTermStore", "SpatialSnapshots")
    if not os.path.isdir(root):
        return []

    entries: List[Dict[str, Any]] = []
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.lower().endswith(".json"):
                continue
            path = os.path.join(dirpath, filename)
            try:
                stat_result = os.stat(path)
            except OSError:
                continue
            entries.append(
                {
                    "path": path,
                    "relative_path": os.path.relpath(path, base).replace("\\", "/"),
                    "mtime": stat_result.st_mtime,
                }
            )

    entries.sort(key=lambda item: (-float(item.get("mtime") or 0.0), str(item.get("relative_path") or "")))
    return entries


def _count_visual_files(base_dir: Optional[str] = None) -> Dict[str, Any]:
    base = base_dir or BASE
    allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".svg"}
    count = 0
    examples: List[str] = []
    extensions: Counter[str] = Counter()
    roots = [
        os.path.join(base, "LongTermStore"),
        os.path.join(base, "TemporaryQueue", "blender_composition"),
        os.path.join(base, "AI_Brain"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in allowed_exts:
                    continue
                count += 1
                extensions[ext] += 1
                if len(examples) < 5:
                    full_path = os.path.join(dirpath, filename)
                    examples.append(os.path.relpath(full_path, base).replace("\\", "/"))
    return {
        "count": count,
        "extensions": dict(sorted(extensions.items())),
        "examples": examples,
    }


def _display_path(path: str, *, base_dir: Optional[str] = None) -> str:
    base = base_dir or BASE
    try:
        rel_path = os.path.relpath(path, base).replace("\\", "/")
        if not rel_path.startswith("../"):
            return rel_path
    except Exception:
        pass
    return path.replace("\\", "/")


def _snapshot_record_cycle_from_path(relative_path: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not isinstance(relative_path, str) or not relative_path:
        return None, None
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) >= 5 and parts[0] == "LongTermStore" and parts[1] == "SpatialSnapshots":
        return parts[2], parts[3]
    return None, None


def _truncate_text(value: Any, *, limit: int = 44) -> str:
    text = str(value) if value is not None else ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def _safe_vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    out: List[float] = []
    for item in value[:3]:
        if not isinstance(item, (int, float)) or isinstance(item, bool) or not math.isfinite(float(item)):
            return None
        out.append(float(item))
    return out


def _summarize_spatial_snapshot_payload(snapshot_payload: Dict[str, Any], *, relative_path: str) -> Dict[str, Any]:
    measurement = snapshot_payload.get("measurement") if isinstance(snapshot_payload.get("measurement"), dict) else {}
    bridge_payloads = [item for item in (snapshot_payload.get("bridge_normalized") or []) if isinstance(item, dict)]

    bridge_entity_count = 0
    bridge_relation_count = 0
    bridge_constraint_count = 0
    relation_labels: List[str] = []
    constraint_labels: List[str] = []
    entity_labels: List[str] = []
    for payload in bridge_payloads:
        entities = payload.get("entities") if isinstance(payload.get("entities"), list) else []
        relations = payload.get("relations") if isinstance(payload.get("relations"), list) else []
        constraints = payload.get("constraints") if isinstance(payload.get("constraints"), list) else []
        bridge_entity_count += sum(1 for row in entities if isinstance(row, dict))
        bridge_relation_count += sum(1 for row in relations if isinstance(row, dict))
        bridge_constraint_count += sum(1 for row in constraints if isinstance(row, dict))

        for row in entities:
            if not isinstance(row, dict):
                continue
            entity_id = row.get("id") if isinstance(row.get("id"), str) else row.get("type")
            if isinstance(entity_id, str) and entity_id and len(entity_labels) < 4:
                entity_labels.append(_truncate_text(entity_id, limit=30))
        for row in relations:
            if not isinstance(row, dict):
                continue
            label = row.get("pred") if isinstance(row.get("pred"), str) else row.get("relation")
            if isinstance(label, str) and label and len(relation_labels) < 5:
                relation_labels.append(_truncate_text(label, limit=28))
        for row in constraints:
            if not isinstance(row, dict):
                continue
            label = row.get("type") if isinstance(row.get("type"), str) else "constraint"
            status = row.get("status") if isinstance(row.get("status"), str) else None
            rendered = f"{label}:{status}" if status else label
            if len(constraint_labels) < 5:
                constraint_labels.append(_truncate_text(rendered, limit=32))

    record_id, cycle_id = _snapshot_record_cycle_from_path(relative_path)
    if isinstance(snapshot_payload.get("record_id"), str) and snapshot_payload.get("record_id"):
        record_id = snapshot_payload.get("record_id")
    if isinstance(snapshot_payload.get("cycle_id"), str) and snapshot_payload.get("cycle_id"):
        cycle_id = snapshot_payload.get("cycle_id")

    metrics = measurement.get("metrics") if isinstance(measurement.get("metrics"), dict) else {}
    bounds = measurement.get("bounds") if isinstance(measurement.get("bounds"), dict) else {}
    bounds_min = _safe_vector3(bounds.get("min"))
    bounds_max = _safe_vector3(bounds.get("max"))
    centroid = _safe_vector3(measurement.get("centroid"))
    dimensions = measurement.get("aabb_dimensions") if isinstance(measurement.get("aabb_dimensions"), dict) else {}
    point_count = metrics.get("point_count") if isinstance(metrics.get("point_count"), int) else measurement.get("count")
    volume = measurement.get("volume") if isinstance(measurement.get("volume"), (int, float)) else None
    shape = measurement.get("shape") if isinstance(measurement.get("shape"), str) else None
    units = measurement.get("units") if isinstance(measurement.get("units"), str) else None
    measurement_ok = measurement.get("ok") if isinstance(measurement.get("ok"), bool) else None

    return {
        "record_id": record_id or os.path.splitext(os.path.basename(relative_path))[0],
        "cycle_id": cycle_id,
        "relative_path": relative_path,
        "measurement_hash": snapshot_payload.get("measurement_hash") if isinstance(snapshot_payload.get("measurement_hash"), str) else None,
        "shape": shape,
        "units": units,
        "volume": float(volume) if isinstance(volume, (int, float)) and math.isfinite(float(volume)) else None,
        "point_count": int(point_count) if isinstance(point_count, int) else None,
        "measurement_ok": measurement_ok,
        "bounds_min": bounds_min,
        "bounds_max": bounds_max,
        "centroid": centroid,
        "dimensions": {
            key: float(value)
            for key, value in dimensions.items()
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        },
        "bridge_entity_count": bridge_entity_count,
        "bridge_relation_count": bridge_relation_count,
        "bridge_constraint_count": bridge_constraint_count,
        "relation_labels": relation_labels,
        "constraint_labels": constraint_labels,
        "entity_labels": entity_labels,
        "logical_structure_present": bool(bridge_entity_count or bridge_relation_count or bridge_constraint_count),
    }


def _render_projection_panel(
    *,
    title: str,
    min_vector: Optional[List[float]],
    max_vector: Optional[List[float]],
    centroid: Optional[List[float]],
    axis_x: int,
    axis_y: int,
    panel_x: int,
    panel_y: int,
    panel_width: int,
    panel_height: int,
) -> str:
    title_y = panel_y + 24
    body_y = panel_y + 42
    body_height = panel_height - 54
    parts = [
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_width}" height="{panel_height}" rx="18" fill="#fffdf7" stroke="#d7c9af" stroke-width="2"/>',
        f'<text x="{panel_x + 18}" y="{title_y}" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700" fill="#4f4637">{html.escape(title)}</text>',
    ]
    if not min_vector or not max_vector:
        parts.append(
            f'<text x="{panel_x + 18}" y="{body_y + 48}" font-family="Consolas, monospace" font-size="16" fill="#8b7d67">No measurement bounds available</text>'
        )
        return "".join(parts)

    min_x = float(min_vector[axis_x])
    max_x = float(max_vector[axis_x])
    min_y = float(min_vector[axis_y])
    max_y = float(max_vector[axis_y])
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    padding = 20.0
    scale = min((panel_width - 2 * padding) / span_x, (body_height - 2 * padding) / span_y)
    rect_width = max(2.0, span_x * scale)
    rect_height = max(2.0, span_y * scale)
    offset_x = panel_x + (panel_width - rect_width) / 2.0
    offset_y = body_y + (body_height - rect_height) / 2.0

    parts.extend(
        [
            f'<line x1="{panel_x + 14}" y1="{body_y + body_height / 2:.2f}" x2="{panel_x + panel_width - 14}" y2="{body_y + body_height / 2:.2f}" stroke="#efe3cd" stroke-width="1.5"/>',
            f'<line x1="{panel_x + panel_width / 2:.2f}" y1="{body_y + 14}" x2="{panel_x + panel_width / 2:.2f}" y2="{body_y + body_height - 14}" stroke="#efe3cd" stroke-width="1.5"/>',
            f'<rect x="{offset_x:.2f}" y="{offset_y:.2f}" width="{rect_width:.2f}" height="{rect_height:.2f}" rx="12" fill="#d7e8c9" stroke="#58714a" stroke-width="2.5"/>',
        ]
    )
    if centroid:
        centroid_x = offset_x + (float(centroid[axis_x]) - min_x) * scale
        centroid_y = offset_y + rect_height - (float(centroid[axis_y]) - min_y) * scale
        parts.append(f'<circle cx="{centroid_x:.2f}" cy="{centroid_y:.2f}" r="6" fill="#ba4a1b" stroke="#fff6eb" stroke-width="2"/>')
    return "".join(parts)


def _render_spatial_snapshot_svg(snapshot_payload: Dict[str, Any], summary: Dict[str, Any]) -> str:
    width = 980
    height = 720
    top_panel = _render_projection_panel(
        title="Top View (x / y)",
        min_vector=summary.get("bounds_min"),
        max_vector=summary.get("bounds_max"),
        centroid=summary.get("centroid"),
        axis_x=0,
        axis_y=1,
        panel_x=36,
        panel_y=120,
        panel_width=430,
        panel_height=250,
    )
    front_panel = _render_projection_panel(
        title="Front View (x / z)",
        min_vector=summary.get("bounds_min"),
        max_vector=summary.get("bounds_max"),
        centroid=summary.get("centroid"),
        axis_x=0,
        axis_y=2,
        panel_x=500,
        panel_y=120,
        panel_width=430,
        panel_height=250,
    )

    metric_lines = [
        f"Record: {_truncate_text(summary.get('record_id') or 'unknown', limit=48)}",
        f"Cycle: {_truncate_text(summary.get('cycle_id') or 'n/a', limit=48)}",
        f"Shape: {_truncate_text(summary.get('shape') or 'n/a', limit=48)}",
        f"Units: {_truncate_text(summary.get('units') or 'n/a', limit=48)}",
        f"Volume: {summary.get('volume') if summary.get('volume') is not None else 'n/a'}",
        f"Points: {summary.get('point_count') if summary.get('point_count') is not None else 'n/a'}",
        f"Measurement ok: {summary.get('measurement_ok') if summary.get('measurement_ok') is not None else 'n/a'}",
    ]

    dims = summary.get("dimensions") if isinstance(summary.get("dimensions"), dict) else {}
    if dims:
        dim_bits = []
        for axis in ("diagonal", "dx", "dy", "dz"):
            value = dims.get(axis)
            if isinstance(value, (int, float)):
                dim_bits.append(f"{axis}={round(float(value), 4)}")
        if dim_bits:
            metric_lines.append("AABB: " + ", ".join(dim_bits))

    logic_lines = [
        f"Entities: {summary.get('bridge_entity_count', 0)}",
        f"Relations: {summary.get('bridge_relation_count', 0)}",
        f"Constraints: {summary.get('bridge_constraint_count', 0)}",
    ]
    if summary.get("entity_labels"):
        logic_lines.append("Entity ids: " + ", ".join(summary["entity_labels"]))
    if summary.get("relation_labels"):
        logic_lines.append("Predicates: " + ", ".join(summary["relation_labels"]))
    if summary.get("constraint_labels"):
        logic_lines.append("Checks: " + ", ".join(summary["constraint_labels"]))

    def _render_text_block(lines: List[str], *, start_x: int, start_y: int, line_height: int = 26, color: str = "#413729") -> str:
        parts: List[str] = []
        for index, line in enumerate(lines):
            safe_line = html.escape(_truncate_text(line, limit=88))
            y = start_y + index * line_height
            parts.append(
                f'<text x="{start_x}" y="{y}" font-family="Consolas, monospace" font-size="16" fill="{color}">{safe_line}</text>'
            )
        return "".join(parts)

    subtitle = "logical structure present" if summary.get("logical_structure_present") else "measurement-only snapshot"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#f5efe1"/>'
        '<rect x="20" y="20" width="940" height="680" rx="28" fill="#fbf7ee" stroke="#ccb894" stroke-width="3"/>'
        f'<text x="38" y="62" font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="#342b22">Spatial Snapshot Preview</text>'
        f'<text x="40" y="92" font-family="Segoe UI, Arial, sans-serif" font-size="17" fill="#6d604d">{html.escape(_truncate_text(summary.get("relative_path") or "", limit=110))}</text>'
        f'<text x="720" y="62" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="700" fill="#7a6649">{html.escape(subtitle)}</text>'
        f'{top_panel}{front_panel}'
        '<rect x="36" y="396" width="430" height="270" rx="18" fill="#fffdf7" stroke="#d7c9af" stroke-width="2"/>'
        '<rect x="500" y="396" width="430" height="270" rx="18" fill="#fffdf7" stroke="#d7c9af" stroke-width="2"/>'
        '<text x="54" y="426" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700" fill="#4f4637">Measurement Summary</text>'
        '<text x="518" y="426" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700" fill="#4f4637">Relational Structure</text>'
        f'{_render_text_block(metric_lines, start_x=54, start_y=458)}'
        f'{_render_text_block(logic_lines, start_x=518, start_y=458)}'
        '</svg>'
    )


def _assess_preview_adequacy(*, total_snapshots: int, exported_count: int, structured_count: int) -> Dict[str, Any]:
    if total_snapshots <= 0:
        return {
            "adequate": False,
            "mode": "no_snapshots",
            "reason": "No persisted spatial snapshots were available to review.",
        }
    if exported_count >= total_snapshots:
        return {
            "adequate": True,
            "mode": "full_coverage",
            "reason": f"Rendered previews for all {total_snapshots} persisted spatial snapshots.",
        }
    if exported_count >= min(total_snapshots, 24) and structured_count > 0:
        return {
            "adequate": True,
            "mode": "spot_check",
            "reason": f"Rendered {exported_count} recent previews, which is enough for operator spot-checking even though total persisted snapshots is {total_snapshots}.",
        }
    return {
        "adequate": False,
        "mode": "insufficient_sample",
        "reason": f"Rendered only {exported_count} preview(s) from {total_snapshots} snapshots; increase --limit for a stronger manual review sample.",
    }


def _render_spatial_gallery_html(*, exported: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    cards: List[str] = []
    for item in exported:
        summary_obj = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        svg_relpath = html.escape(str(item.get("svg_relative_path") or ""))
        record_id = html.escape(str(summary_obj.get("record_id") or "unknown"))
        cycle_id = html.escape(str(summary_obj.get("cycle_id") or "n/a"))
        counts = f"E {summary_obj.get('bridge_entity_count', 0)} | R {summary_obj.get('bridge_relation_count', 0)} | C {summary_obj.get('bridge_constraint_count', 0)}"
        cards.append(
            "".join(
                [
                    '<article class="card">',
                    f'<img src="{svg_relpath}" alt="Spatial preview for {record_id}" loading="lazy" />',
                    '<div class="meta">',
                    f'<h2>{record_id}</h2>',
                    f'<p>cycle: {cycle_id}</p>',
                    f'<p>{html.escape(counts)}</p>',
                    f'<p>{html.escape(_truncate_text(summary_obj.get("shape") or "n/a", limit=40))}</p>',
                    '</div>',
                    '</article>',
                ]
            )
        )

    adequacy = summary.get("adequacy") if isinstance(summary.get("adequacy"), dict) else {}
    return "".join(
        [
            '<!doctype html><html lang="en"><head><meta charset="utf-8"/>',
            '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
            '<title>AI Brain Spatial Gallery</title>',
            '<style>',
            'body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f1eadb;color:#2f281f;}',
            '.wrap{max-width:1400px;margin:0 auto;padding:32px 24px 48px;}',
            '.hero{background:#fbf7ee;border:2px solid #ccb894;border-radius:24px;padding:24px 28px;box-shadow:0 18px 48px rgba(84,66,35,.08);}',
            '.hero h1{margin:0 0 10px;font-size:34px;}',
            '.hero p{margin:8px 0;font-size:16px;line-height:1.5;}',
            '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;margin-top:24px;}',
            '.card{background:#fffdf7;border:2px solid #d7c9af;border-radius:22px;overflow:hidden;box-shadow:0 14px 28px rgba(84,66,35,.08);}',
            '.card img{display:block;width:100%;height:260px;object-fit:cover;background:#f5efe1;}',
            '.meta{padding:16px 18px 20px;}',
            '.meta h2{margin:0 0 8px;font-size:20px;}',
            '.meta p{margin:5px 0;color:#625642;font-size:14px;}',
            '</style></head><body><div class="wrap">',
            '<section class="hero">',
            '<h1>AI Brain Spatial Preview Gallery</h1>',
            f'<p>Native image files already present in workspace: {summary.get("preexisting_visual_file_count", 0)}</p>',
            f'<p>Persisted spatial snapshots: {summary.get("total_snapshot_files", 0)}</p>',
            f'<p>Rendered previews in this export: {summary.get("exported_preview_count", 0)}</p>',
            f'<p>Snapshots with logical structure in this export: {summary.get("structured_preview_count", 0)}</p>',
            f'<p>Adequacy: {html.escape(str(adequacy.get("reason") or ""))}</p>',
            '</section>',
            '<section class="grid">',
            ''.join(cards),
            '</section></div></body></html>',
        ]
    )


def _export_spatial_gallery(
    *,
    base_dir: Optional[str] = None,
    limit: int = 24,
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    base = base_dir or BASE
    requested_limit = max(0, int(limit))
    resolved_out_dir = _resolve_cli_output_path(out_dir) if out_dir else safe_join(base, "TemporaryQueue", "spatial_gallery")
    os.makedirs(resolved_out_dir, exist_ok=True)
    svg_dir = safe_join(resolved_out_dir, "svg")
    os.makedirs(svg_dir, exist_ok=True)

    visual_inventory = _count_visual_files(base_dir=base)
    snapshot_files = _list_spatial_snapshot_files(base_dir=base)
    selected = snapshot_files[:requested_limit] if requested_limit else []

    exported: List[Dict[str, Any]] = []
    structured_preview_count = 0
    for index, entry in enumerate(selected, start=1):
        payload = _load_json_file(entry["path"])
        if not isinstance(payload, dict):
            continue
        summary = _summarize_spatial_snapshot_payload(payload, relative_path=str(entry.get("relative_path") or ""))
        if summary.get("logical_structure_present"):
            structured_preview_count += 1
        svg_name = f"{index:03d}_{sanitize_id(str(summary.get('record_id') or 'snapshot'))}.svg"
        svg_path = safe_join(svg_dir, svg_name)
        with open(svg_path, "w", encoding="utf-8") as handle:
            handle.write(_render_spatial_snapshot_svg(payload, summary))
        exported.append(
            {
                "snapshot_relative_path": entry.get("relative_path"),
                "svg_path": svg_path,
                "svg_relative_path": os.path.relpath(svg_path, resolved_out_dir).replace("\\", "/"),
                "summary": summary,
            }
        )

    adequacy = _assess_preview_adequacy(
        total_snapshots=len(snapshot_files),
        exported_count=len(exported),
        structured_count=structured_preview_count,
    )
    result = {
        "images_being_created": bool(visual_inventory.get("count")),
        "preexisting_visual_file_count": visual_inventory.get("count", 0),
        "preexisting_visual_file_extensions": visual_inventory.get("extensions", {}),
        "preexisting_visual_examples": visual_inventory.get("examples", []),
        "total_snapshot_files": len(snapshot_files),
        "requested_preview_limit": requested_limit,
        "exported_preview_count": len(exported),
        "structured_preview_count": structured_preview_count,
        "extrapolated_structure_present": structured_preview_count > 0,
        "adequacy": adequacy,
        "gallery_dir": _display_path(resolved_out_dir, base_dir=base),
        "gallery_index": _display_path(os.path.join(resolved_out_dir, "index.html"), base_dir=base),
        "report_path": _display_path(os.path.join(resolved_out_dir, "report.json"), base_dir=base),
        "preview_examples": [
            {
                "record_id": item["summary"].get("record_id"),
                "cycle_id": item["summary"].get("cycle_id"),
                "svg_path": _display_path(item["svg_path"], base_dir=base),
                "snapshot_relative_path": item.get("snapshot_relative_path"),
                "bridge_entity_count": item["summary"].get("bridge_entity_count", 0),
                "bridge_relation_count": item["summary"].get("bridge_relation_count", 0),
                "bridge_constraint_count": item["summary"].get("bridge_constraint_count", 0),
            }
            for item in exported[:5]
        ],
    }

    with open(os.path.join(resolved_out_dir, "index.html"), "w", encoding="utf-8") as handle:
        handle.write(_render_spatial_gallery_html(exported=exported, summary=result))
    with open(os.path.join(resolved_out_dir, "report.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)

    return result


def _extract_telemetry_request_id(payload: Dict[str, Any]) -> Optional[str]:
    direct = payload.get("request_id") if isinstance(payload.get("request_id"), str) else None
    if direct:
        return direct

    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    nested = extra.get("request_id") if isinstance(extra.get("request_id"), str) else None
    if nested:
        return nested

    validation = extra.get("validation") if isinstance(extra.get("validation"), dict) else {}
    validation_request_id = validation.get("request_id") if isinstance(validation.get("request_id"), str) else None
    if validation_request_id:
        return validation_request_id

    composition_request = extra.get("composition_request") if isinstance(extra.get("composition_request"), dict) else {}
    composition_request_id = composition_request.get("request_id") if isinstance(composition_request.get("request_id"), str) else None
    if composition_request_id:
        return composition_request_id

    return None


def _telemetry_event_order(payload: Dict[str, Any]) -> tuple[int, str]:
    sequence_index = payload.get("sequence_index")
    sequence_value = sequence_index if isinstance(sequence_index, int) else -1
    timestamp_fixed = payload.get("timestamp_fixed") if isinstance(payload.get("timestamp_fixed"), str) else ""
    return sequence_value, timestamp_fixed


def _summarize_telemetry_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "status": payload.get("status") if isinstance(payload.get("status"), str) else None,
        "timestamp_fixed": payload.get("timestamp_fixed") if isinstance(payload.get("timestamp_fixed"), str) else None,
        "sequence_index": payload.get("sequence_index") if isinstance(payload.get("sequence_index"), int) else None,
    }
    measurement_hash = payload.get("measurement_hash") if isinstance(payload.get("measurement_hash"), str) else None
    request_id = _extract_telemetry_request_id(payload)
    if measurement_hash:
        summary["measurement_hash"] = measurement_hash
    if request_id:
        summary["request_id"] = request_id
    return summary


def _collect_spatial_telemetry_rollup(
    base_dir: Optional[str] = None,
    tracked_measurement_hashes: Optional[List[str]] = None,
    tracked_request_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    base = base_dir or BASE
    telemetry_path = os.path.join(
        base,
        "LongTermStore",
        "Telemetry",
        "SpatialMeasurements",
        "events.jsonl",
    )
    measurement_hashes = {value for value in (tracked_measurement_hashes or []) if isinstance(value, str) and value}
    request_ids = {value for value in (tracked_request_ids or []) if isinstance(value, str) and value}
    if not os.path.exists(telemetry_path):
        return {
            "total_events": 0,
            "completed_event_count": 0,
            "last_completed_event": None,
            "latest_status_by_measurement_hash": {},
            "latest_status_by_request_id": {},
        }

    total_events = 0
    completed_event_count = 0
    last_completed_payload: Optional[Dict[str, Any]] = None
    latest_by_measurement_hash: Dict[str, Dict[str, Any]] = {}
    latest_by_request_id: Dict[str, Dict[str, Any]] = {}

    try:
        with open(telemetry_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                total_events += 1
                try:
                    payload = json.loads(stripped)
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue

                status = payload.get("status") if isinstance(payload.get("status"), str) else None
                measurement_hash = payload.get("measurement_hash") if isinstance(payload.get("measurement_hash"), str) else None
                request_id = _extract_telemetry_request_id(payload)

                if status == "completed":
                    completed_event_count += 1
                    if last_completed_payload is None or _telemetry_event_order(payload) >= _telemetry_event_order(last_completed_payload):
                        last_completed_payload = payload

                if measurement_hash in measurement_hashes:
                    current = latest_by_measurement_hash.get(measurement_hash)
                    if current is None or _telemetry_event_order(payload) >= _telemetry_event_order(current):
                        latest_by_measurement_hash[measurement_hash] = payload

                if request_id in request_ids:
                    current = latest_by_request_id.get(request_id)
                    if current is None or _telemetry_event_order(payload) >= _telemetry_event_order(current):
                        latest_by_request_id[request_id] = payload
    except Exception:
        return {
            "total_events": total_events,
            "completed_event_count": completed_event_count,
            "last_completed_event": None,
            "latest_status_by_measurement_hash": {},
            "latest_status_by_request_id": {},
        }

    return {
        "total_events": total_events,
        "completed_event_count": completed_event_count,
        "last_completed_event": _summarize_telemetry_event(last_completed_payload) if last_completed_payload else None,
        "latest_status_by_measurement_hash": {
            key: _summarize_telemetry_event(value)
            for key, value in sorted(latest_by_measurement_hash.items())
        },
        "latest_status_by_request_id": {
            key: _summarize_telemetry_event(value)
            for key, value in sorted(latest_by_request_id.items())
        },
    }


def _load_json_file(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _normalize_string_list(values: Any, *, limit: Optional[int] = None) -> List[str]:
    if not isinstance(values, list):
        return []
    normalized: List[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in normalized:
            continue
        normalized.append(text)
        if limit is not None and len(normalized) >= limit:
            break
    return normalized


def _normalize_objective_links(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized: Dict[str, float] = {}
    for key in sorted(value.keys()):
        if not isinstance(key, str) or not key:
            continue
        raw = value.get(key)
        if not isinstance(raw, (int, float)):
            continue
        normalized[key] = round(float(raw), 6)
    return normalized


def _build_inbound_categorized_context_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    provided = record.get('categorized_context_summary') if isinstance(record.get('categorized_context_summary'), dict) else {}
    labels = _normalize_string_list(provided.get('labels') or record.get('labels'), limit=8)
    aliases = _normalize_string_list(provided.get('aliases') or record.get('aliases'), limit=8)
    comparison_axes = _normalize_string_list(provided.get('comparison_axes') or record.get('comparison_axes'), limit=8)
    relation_families = _normalize_string_list(provided.get('relation_families') or record.get('relation_families'), limit=8)
    bridge_sources = _normalize_string_list(provided.get('bridge_sources'), limit=8)
    support_level = str(provided.get('support_level') or ('strong' if labels and comparison_axes else 'weak' if (labels or comparison_axes) else 'missing'))
    reference_profile = {
        'labels': _normalize_string_list(provided.get('reference_labels') or labels, limit=8),
        'aliases': _normalize_string_list(provided.get('reference_aliases') or aliases, limit=8),
        'comparison_axes': _normalize_string_list(provided.get('reference_comparison_axes') or comparison_axes, limit=8),
    }
    join_quality = summarize_categorized_context_join_quality(
        {
            'labels': labels,
            'aliases': aliases,
            'comparison_axes': comparison_axes,
            'support_level': support_level,
        },
        reference_profile,
    )
    join_status = str(provided.get('join_status') or join_quality.get('join_status') or ('reference_backed_semantic_weak' if record.get('missing_reference_categories') else 'aligned'))
    return {
        'record_id': None,
        'reference_record_id': None,
        'labels': labels,
        'aliases': aliases,
        'comparison_axes': comparison_axes,
        'relation_families': relation_families,
        'bridge_sources': bridge_sources,
        'scene_summary_present': bool(provided.get('scene_summary_present') or str(record.get('context_id') or '') == '3d_reference'),
        'support_level': support_level,
        'reference_profile_present': bool(join_quality.get('reference_profile_present')),
        'reference_labels': list(reference_profile['labels']),
        'reference_aliases': list(reference_profile['aliases']),
        'reference_comparison_axes': list(reference_profile['comparison_axes']),
        'join_status': join_status,
        'join_quality': str(provided.get('join_quality') or join_quality.get('join_quality') or 'missing'),
        'persistence_status': str(provided.get('persistence_status') or join_quality.get('persistence_status') or 'missing'),
        'follow_through_status': str(provided.get('follow_through_status') or join_quality.get('follow_through_status') or 'missing'),
        'matched_reference_labels': _normalize_string_list(provided.get('matched_reference_labels') or join_quality.get('matched_reference_labels'), limit=8),
        'matched_reference_aliases': _normalize_string_list(provided.get('matched_reference_aliases') or join_quality.get('matched_reference_aliases'), limit=8),
        'matched_reference_comparison_axes': _normalize_string_list(provided.get('matched_reference_comparison_axes') or join_quality.get('matched_reference_comparison_axes'), limit=8),
        'matched_reference_category_count': int(provided.get('matched_reference_category_count') or join_quality.get('matched_reference_category_count') or 0),
        'matched_reference_term_count': int(provided.get('matched_reference_term_count') or join_quality.get('matched_reference_term_count') or 0),
        'gap_reasons': _normalize_string_list(provided.get('gap_reasons') or join_quality.get('gap_reasons'), limit=8),
    }


def _default_inbound_interest_review_output_path() -> str:
    return os.path.join(BASE, 'TemporaryQueue', 'inbound_interest_review', 'visual_pipeline_teacher_review_import.json')


def cmd_import_teacher_review(args):
    input_path = _resolve_cli_output_path(getattr(args, 'input', None))
    if not input_path:
        print(json.dumps({'ok': False, 'error': 'input_path_required'}, indent=2))
        raise SystemExit(1)

    payload = _load_json_file(input_path)
    if not isinstance(payload, dict):
        print(json.dumps({'ok': False, 'error': 'input_payload_invalid', 'input_path': input_path}, indent=2))
        raise SystemExit(1)

    adapter_purpose = str(payload.get('adapter_purpose') or '')
    bundle_marker = str(payload.get('source_bundle_marker') or '')
    if adapter_purpose != TEACHER_REVIEW_ADAPTER_PURPOSE or bundle_marker != VISUAL_PIPELINE_REVIEW_MARKER:
        print(
            json.dumps(
                {
                    'ok': False,
                    'error': 'unsupported_teacher_review_adapter',
                    'input_path': input_path,
                    'adapter_purpose': adapter_purpose,
                    'source_bundle_marker': bundle_marker,
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    records = payload.get('records') if isinstance(payload.get('records'), list) else []
    normalized_records: List[Dict[str, Any]] = []
    skipped_records: List[Dict[str, Any]] = []
    destination_counts: Dict[str, int] = {}

    for index, item in enumerate(records):
        if not isinstance(item, dict):
            skipped_records.append({'index': index, 'reason': 'record_not_object'})
            continue

        interest_label = str(item.get('interest_label') or '').strip()
        sample_id = str(item.get('teacher_review_sample_id') or '').strip()
        artifact_id = str(item.get('source_artifact_id') or '').strip()
        if not interest_label or not sample_id:
            skipped_records.append(
                {
                    'index': index,
                    'reason': 'missing_interest_label_or_sample_id',
                    'source_artifact_id': artifact_id or None,
                }
            )
            continue

        recommended_destinations = [
            value
            for value in _normalize_string_list(item.get('recommended_review_destinations'), limit=8)
            if value in ACCEPTED_REVIEW_DESTINATIONS
        ]
        for destination in recommended_destinations:
            destination_counts[destination] = destination_counts.get(destination, 0) + 1

        normalized = {
            'teacher_review_sample_id': sample_id,
            'source_artifact_id': artifact_id or None,
            'interest_label': interest_label,
            'priority': str(item.get('priority') or 'low'),
            'learning_stage': str(item.get('learning_stage') or 'foundational'),
            'objective_family_tags': _normalize_string_list(item.get('objective_family_tags'), limit=12),
            'context_id': str(item.get('context_id') or 'semantic'),
            'labels': _normalize_string_list(item.get('labels'), limit=8),
            'aliases': _normalize_string_list(item.get('aliases'), limit=8),
            'comparison_axes': _normalize_string_list(item.get('comparison_axes'), limit=8),
            'relation_families': _normalize_string_list(item.get('relation_families'), limit=8),
            'categorized_context_summary': _build_inbound_categorized_context_summary(item),
            'objective_links': _normalize_objective_links(item.get('objective_links')),
            'missing_reference_categories': _normalize_string_list(item.get('missing_reference_categories'), limit=8),
            'why_not': _normalize_string_list(item.get('why_not'), limit=12),
            'prerequisites': _normalize_string_list(item.get('prerequisites'), limit=8),
            'next_stage_interests': _normalize_string_list(item.get('next_stage_interests'), limit=8),
            'recommended_review_destinations': recommended_destinations,
            'routing_authority': 'descriptive_only',
            'runtime_authority_granted': False,
        }
        normalized_records.append(normalized)

    result = {
        'ok': True,
        'kind': 'review_only_inbound_interest_evidence_adapter',
        'marker': INBOUND_INTEREST_REVIEW_MARKER,
        'created_at': _get_cli_timestamp(),
        'source': {
            'input_path': input_path,
            'adapter_purpose': adapter_purpose,
            'source_bundle_marker': bundle_marker,
            'source_file': str(payload.get('source_file') or ''),
        },
        'consumer_boundary': {
            'routing_authority': 'descriptive_only',
            'runtime_authority_granted': False,
            'accepted_review_destinations': list(ACCEPTED_REVIEW_DESTINATIONS),
        },
        'record_count': len(normalized_records),
        'skipped_record_count': len(skipped_records),
        'destination_counts': destination_counts,
        'records': normalized_records,
        'skipped_records': skipped_records,
    }

    out_path = _resolve_cli_output_path(getattr(args, 'out', None)) or _default_inbound_interest_review_output_path()
    if not getattr(args, 'no_write', False):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        result['output_path'] = out_path

    if getattr(args, 'raw', False):
        print(json.dumps(result, indent=2))
        return

    print(
        json.dumps(
            {
                'ok': True,
                'marker': result['marker'],
                'input_path': input_path,
                'output_path': result.get('output_path'),
                'record_count': result['record_count'],
                'skipped_record_count': result['skipped_record_count'],
                'accepted_review_destinations': list(ACCEPTED_REVIEW_DESTINATIONS),
                'destination_counts': destination_counts,
                'interest_labels': [record['interest_label'] for record in normalized_records],
            },
            indent=2,
        )
    )


def _extract_composition_request_id_from_assessment_artifacts(
    artifacts: Dict[str, Any],
    bridge_outputs: List[Dict[str, Any]],
    derived: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if isinstance(derived, dict):
        derived_request_id = derived.get("composition_request_id")
        if isinstance(derived_request_id, str) and derived_request_id:
            return derived_request_id

    snapshot_request_id = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
    request_id_from_snapshot = snapshot_request_id.get("request_id") if isinstance(snapshot_request_id.get("request_id"), str) else None
    if request_id_from_snapshot:
        return request_id_from_snapshot

    composition_request = artifacts.get("composition_request") if isinstance(artifacts.get("composition_request"), dict) else {}
    composition_response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else {}
    composition_validation_summary = artifacts.get("composition_validation_summary") if isinstance(artifacts.get("composition_validation_summary"), dict) else {}
    validation_summary = artifacts.get("validation_summary") if isinstance(artifacts.get("validation_summary"), dict) else {}
    for request_id in (
        composition_request.get("request_id"),
        composition_response.get("request_id"),
        composition_validation_summary.get("request_id"),
        validation_summary.get("request_id"),
    ):
        if isinstance(request_id, str) and request_id:
            return request_id

    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        request_id = payload.get("request_id")
        if isinstance(request_id, str) and request_id:
            return request_id
    return None


def _extract_bridge_output_source_for_assessment(bridge_outputs: List[Dict[str, Any]]) -> Optional[str]:
    for payload in bridge_outputs:
        if not isinstance(payload, dict):
            continue
        source = payload.get("source")
        if isinstance(source, str) and source:
            return source
    return None


def _extract_request_id_from_snapshot_payload(payload: Dict[str, Any]) -> Optional[str]:
    for candidate in (
        payload.get("request_id"),
        payload.get("composition_request_id"),
    ):
        if isinstance(candidate, str) and candidate:
            return candidate

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    metadata_request_id = metadata.get("request_id") if isinstance(metadata.get("request_id"), str) else None
    if metadata_request_id:
        return metadata_request_id

    validation = payload.get("validation") if isinstance(payload.get("validation"), dict) else {}
    validation_request_id = validation.get("request_id") if isinstance(validation.get("request_id"), str) else None
    if validation_request_id:
        return validation_request_id

    composition_request = payload.get("composition_request") if isinstance(payload.get("composition_request"), dict) else {}
    composition_request_id = composition_request.get("request_id") if isinstance(composition_request.get("request_id"), str) else None
    if composition_request_id:
        return composition_request_id

    return None


def _load_snapshot_request_id_for_assessment(base_dir: str, snapshot_relpath: Optional[str]) -> Optional[str]:
    if not isinstance(snapshot_relpath, str) or not snapshot_relpath:
        return None
    snapshot_abspath = os.path.join(base_dir, snapshot_relpath.replace("/", os.sep))
    if not os.path.isfile(snapshot_abspath):
        return None
    payload = _load_json_file(snapshot_abspath)
    if not isinstance(payload, dict):
        return None
    return _extract_request_id_from_snapshot_payload(payload)


def _update_request_provenance_index(
    provenance_index: Dict[str, Dict[str, Any]],
    *,
    request_id: Optional[str],
    composition_record_id: Optional[str] = None,
    bridge_output_source: Optional[str] = None,
) -> None:
    if not isinstance(request_id, str) or not request_id:
        return

    existing = provenance_index.get(request_id, {})
    existing_has_source = isinstance(existing.get("bridge_output_source"), str) and bool(existing.get("bridge_output_source"))
    candidate_has_source = isinstance(bridge_output_source, str) and bool(bridge_output_source)
    if existing_has_source and not candidate_has_source:
        return

    merged = dict(existing)
    if isinstance(composition_record_id, str) and composition_record_id:
        merged["composition_record_id"] = composition_record_id
    if candidate_has_source:
        merged["bridge_output_source"] = bridge_output_source
    provenance_index[request_id] = merged


def _build_request_provenance_index(base_dir: str) -> Dict[str, Dict[str, Any]]:
    provenance_index: Dict[str, Dict[str, Any]] = {}
    semantic_dir = os.path.join(base_dir, "LongTermStore", "Semantic")
    semantic_files: List[str] = []
    if os.path.isdir(semantic_dir):
        for root, _, files in os.walk(semantic_dir):
            for name in files:
                if name.lower().endswith(".json"):
                    semantic_files.append(os.path.join(root, name))
    for path in sorted(semantic_files):
        record = _load_json_file(path)
        if not isinstance(record, dict):
            continue
        record_id = record.get("id") if isinstance(record.get("id"), str) else os.path.splitext(os.path.basename(path))[0]
        rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
        artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}
        bridge_outputs = rel_state.get("bridge_outputs") if isinstance(rel_state.get("bridge_outputs"), list) else []
        derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
        request_id = _extract_composition_request_id_from_assessment_artifacts(artifacts, bridge_outputs, derived)
        bridge_output_source = _extract_bridge_output_source_for_assessment(bridge_outputs)
        _update_request_provenance_index(
            provenance_index,
            request_id=request_id,
            composition_record_id=str(record_id),
            bridge_output_source=bridge_output_source,
        )

    runtime_dir = os.path.join(base_dir, "TemporaryQueue", "orchestrator", "composition_requests")
    if os.path.isdir(runtime_dir):
        lineage_files = sorted(
            os.path.join(runtime_dir, name)
            for name in os.listdir(runtime_dir)
            if name.endswith(".lineage.json")
        )
        for path in lineage_files:
            lineage_obj = _load_json_file(path)
            if not isinstance(lineage_obj, dict):
                continue
            request_id = lineage_obj.get("request_id") if isinstance(lineage_obj.get("request_id"), str) else None
            semantic_record = lineage_obj.get("semantic_record") if isinstance(lineage_obj.get("semantic_record"), dict) else {}
            semantic_record_id = semantic_record.get("semantic_record_id") if isinstance(semantic_record.get("semantic_record_id"), str) else None
            bridge_output_source = None
            attachment = lineage_obj.get("scene_summary_attachment") if isinstance(lineage_obj.get("scene_summary_attachment"), dict) else {}
            if isinstance(attachment.get("bridge_source"), str) and attachment.get("bridge_source"):
                bridge_output_source = attachment.get("bridge_source")
            _update_request_provenance_index(
                provenance_index,
                request_id=request_id,
                composition_record_id=semantic_record_id,
                bridge_output_source=bridge_output_source,
            )

    ledger_path = os.path.join(base_dir, "TemporaryQueue", "orchestrator", "composition_lock_events.jsonl")
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        payload = json.loads(stripped)
                    except Exception:
                        continue
                    if not isinstance(payload, dict) or payload.get("event_type") != "lineage_materialized":
                        continue
                    request_id = payload.get("request_id") if isinstance(payload.get("request_id"), str) else None
                    materialization = payload.get("lineage_materialization") if isinstance(payload.get("lineage_materialization"), dict) else {}
                    composition_record_id = materialization.get("semantic_record_id") if isinstance(materialization.get("semantic_record_id"), str) else None
                    _update_request_provenance_index(
                        provenance_index,
                        request_id=request_id,
                        composition_record_id=composition_record_id,
                        bridge_output_source="3d_scene_summary",
                    )
        except Exception:
            pass

    return provenance_index


def _collect_joined_provenance_chain(
    *,
    base_dir: str,
    record_id: str,
    rel_state: Dict[str, Any],
    artifacts: Dict[str, Any],
    request_provenance_index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    spatial_measurement = rel_state.get("spatial_measurement") if isinstance(rel_state.get("spatial_measurement"), dict) else None
    if not isinstance(spatial_measurement, dict) or not spatial_measurement:
        return None

    bridge_outputs = rel_state.get("bridge_outputs") if isinstance(rel_state.get("bridge_outputs"), list) else []
    derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
    local_request_id = _extract_composition_request_id_from_assessment_artifacts(artifacts, bridge_outputs, derived)
    request_id = local_request_id
    bridge_output_source = _extract_bridge_output_source_for_assessment(bridge_outputs)

    spatial_artifacts = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
    latest_snapshot = spatial_artifacts.get("latest") if isinstance(spatial_artifacts.get("latest"), dict) else {}
    snapshot_relpath = latest_snapshot.get("relative_path") if isinstance(latest_snapshot.get("relative_path"), str) else None
    if snapshot_relpath:
        snapshot_abspath = os.path.join(base_dir, snapshot_relpath.replace("/", os.sep))
        if not os.path.isfile(snapshot_abspath):
            snapshot_relpath = None
    if request_id is None:
        request_id = _load_snapshot_request_id_for_assessment(base_dir, snapshot_relpath)

    measurement_hash = None
    for candidate in (
        spatial_artifacts.get("measurement_hash"),
        derived.get("spatial_measurement_hash"),
    ):
        if isinstance(candidate, str) and candidate:
            measurement_hash = candidate
            break
    if measurement_hash is None:
        try:
            measurement_hash = hashlib.sha256(canonical_json_bytes(spatial_measurement)).hexdigest()
        except Exception:
            measurement_hash = None

    composition_record_id = request_id
    if isinstance(request_id, str) and request_id and isinstance(request_provenance_index, dict):
        provenance = request_provenance_index.get(request_id, {})
        if not isinstance(bridge_output_source, str) or not bridge_output_source:
            candidate_source = provenance.get("bridge_output_source") if isinstance(provenance.get("bridge_output_source"), str) else None
            if candidate_source:
                bridge_output_source = candidate_source
                candidate_record_id = provenance.get("composition_record_id") if isinstance(provenance.get("composition_record_id"), str) else None
                if candidate_record_id:
                    composition_record_id = candidate_record_id

    if not (isinstance(request_id, str) and request_id and isinstance(snapshot_relpath, str) and snapshot_relpath and isinstance(measurement_hash, str) and measurement_hash and isinstance(bridge_output_source, str) and bridge_output_source):
        return None

    return {
        "join_key_type": "request_id",
        "join_key": request_id,
        "composition_record_id": composition_record_id,
        "measurement_record_id": record_id,
        "snapshot_path": snapshot_relpath.replace("\\", "/"),
        "measurement_hash": measurement_hash,
        "bridge_output_source": bridge_output_source,
    }


def _summarize_runtime_lineage_integration(
    *,
    joined_provenance: Optional[Dict[str, Any]],
    measurement_recorded: bool,
    measurement_hash_present: bool,
    spatial_snapshot_present: bool,
    composition_artifact_present: bool,
    composition_bridge_output_present: bool,
) -> Dict[str, Any]:
    join_present = isinstance(joined_provenance, dict)
    if join_present:
        status = "complete"
    elif any(
        (
            measurement_recorded,
            measurement_hash_present,
            spatial_snapshot_present,
            composition_artifact_present,
            composition_bridge_output_present,
        )
    ):
        status = "partial"
    else:
        status = "missing"

    summary: Dict[str, Any] = {
        "status": status,
        "join_chain_present": join_present,
        "measurement_recorded": bool(measurement_recorded),
        "measurement_hash_present": bool(measurement_hash_present),
        "spatial_snapshot_present": bool(spatial_snapshot_present),
        "composition_artifact_present": bool(composition_artifact_present),
        "bridge_output_present": bool(composition_bridge_output_present),
    }
    if join_present:
        join_key_type = joined_provenance.get("join_key_type")
        join_key = joined_provenance.get("join_key")
        if isinstance(join_key_type, str) and join_key_type:
            summary["join_key_type"] = join_key_type
        if isinstance(join_key, str) and join_key:
            summary["join_key"] = join_key
    return summary


def _summarize_decision_trace(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "present": False,
            "scene_validation_present": False,
            "reason_chain_count": 0,
            "decision_signals_count": 0,
        }

    rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
    decision_trace = rel_state.get("decision_trace") if isinstance(rel_state.get("decision_trace"), dict) else {}
    scene_validation = (
        decision_trace.get("scene_validation")
        if isinstance(decision_trace.get("scene_validation"), dict)
        else {}
    )
    reason_chain = record.get("reason_chain") if isinstance(record.get("reason_chain"), list) else []
    decision_signals = record.get("decision_signals") if isinstance(record.get("decision_signals"), list) else []
    latest_signal = decision_signals[-1] if decision_signals and isinstance(decision_signals[-1], dict) else {}

    summary: Dict[str, Any] = {
        "present": bool(decision_trace or reason_chain or decision_signals),
        "scene_validation_present": bool(scene_validation.get("present")),
        "reason_chain_count": len(reason_chain),
        "decision_signals_count": len(decision_signals),
    }
    for key in ("total_checks", "passed", "failed", "warnings"):
        value = scene_validation.get(key)
        if isinstance(value, int):
            summary[f"scene_validation_{key}"] = value
    if isinstance(scene_validation.get("has_hard_failure"), bool):
        summary["scene_validation_has_hard_failure"] = scene_validation.get("has_hard_failure")
    if isinstance(latest_signal.get("selection_score"), (int, float)):
        summary["latest_selection_score"] = float(latest_signal.get("selection_score"))
    if isinstance(latest_signal.get("objective_alignment"), str):
        summary["latest_objective_alignment"] = latest_signal.get("objective_alignment")
    return summary


def _summarize_memory_consolidation_review_signal(
    *,
    retained_storage_pressure: Dict[str, Any],
    categorized_context: Dict[str, Any],
    categorized_context_inventory: Dict[str, Any],
) -> Dict[str, Any]:
    pressure_metrics = retained_storage_pressure.get("metrics") if isinstance(retained_storage_pressure, dict) else {}
    inventory = categorized_context_inventory if isinstance(categorized_context_inventory, dict) else {}
    support_counts = inventory.get("support_level_counts") if isinstance(inventory.get("support_level_counts"), dict) else {}
    join_counts = inventory.get("join_status_counts") if isinstance(inventory.get("join_status_counts"), dict) else {}

    retained_file_count = int(pressure_metrics.get("retained_file_count", 0) or 0)
    reference_profile_present_count = int(inventory.get("reference_profile_present_count", 0) or 0)
    strong_support_record_count = int(support_counts.get("strong", 0) or 0)
    aligned_join_record_count = int(join_counts.get("aligned", 0) or 0)
    primary_reference_use_score = float(categorized_context.get("reference_use_score", 0.0) or 0.0)

    thresholds = {
        "min_retained_file_count": 10,
        "min_reference_profile_present_count": 2,
        "min_strong_support_record_count": 2,
        "min_primary_reference_use_score": 0.75,
    }
    reconsider_later = (
        retained_file_count >= thresholds["min_retained_file_count"]
        and reference_profile_present_count >= thresholds["min_reference_profile_present_count"]
        and strong_support_record_count >= thresholds["min_strong_support_record_count"]
        and primary_reference_use_score >= thresholds["min_primary_reference_use_score"]
    )
    threshold_gaps = {
        "retained_file_count": max(thresholds["min_retained_file_count"] - retained_file_count, 0),
        "reference_profile_present_count": max(thresholds["min_reference_profile_present_count"] - reference_profile_present_count, 0),
        "strong_support_record_count": max(thresholds["min_strong_support_record_count"] - strong_support_record_count, 0),
        "primary_reference_use_score": round(max(thresholds["min_primary_reference_use_score"] - primary_reference_use_score, 0.0), 6),
    }
    return {
        "status": "later_review_candidate" if reconsider_later else "defer",
        "reconsider_later": reconsider_later,
        "current_window_only": True,
        "evidence": {
            "retained_file_count": retained_file_count,
            "reference_profile_present_count": reference_profile_present_count,
            "strong_support_record_count": strong_support_record_count,
            "aligned_join_record_count": aligned_join_record_count,
            "primary_reference_use_score": primary_reference_use_score,
        },
        "thresholds": thresholds,
        "threshold_gaps": threshold_gaps,
    }


def _summarize_categorized_context_follow_through(
    *,
    categorized_context: Dict[str, Any],
    categorized_context_inventory: Dict[str, Any],
) -> Dict[str, Any]:
    summary = categorized_context if isinstance(categorized_context, dict) else {}
    inventory = categorized_context_inventory if isinstance(categorized_context_inventory, dict) else {}
    join_quality_counts = inventory.get("join_quality_counts") if isinstance(inventory.get("join_quality_counts"), dict) else {}
    follow_through_counts = inventory.get("follow_through_status_counts") if isinstance(inventory.get("follow_through_status_counts"), dict) else {}
    persistence_counts = inventory.get("persistence_status_counts") if isinstance(inventory.get("persistence_status_counts"), dict) else {}

    return {
        "status": str(summary.get("follow_through_status") or "missing"),
        "join_status": str(summary.get("join_status") or "missing"),
        "join_quality": str(summary.get("join_quality") or "missing"),
        "persistence_status": str(summary.get("persistence_status") or "missing"),
        "matched_reference_category_count": int(summary.get("matched_reference_category_count") or 0),
        "matched_reference_term_count": int(summary.get("matched_reference_term_count") or 0),
        "gap_reasons": _normalize_string_list(summary.get("gap_reasons"), limit=8),
        "inventory": {
            "join_quality_counts": dict(join_quality_counts),
            "follow_through_status_counts": dict(follow_through_counts),
            "persistence_status_counts": dict(persistence_counts),
        },
    }


def _summarize_reason_chain(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {
            "present": False,
            "count": 0,
            "latest_inference_rule": None,
            "latest_conclusion": None,
            "latest_action": None,
        }

    reason_chain = record.get("reason_chain") if isinstance(record.get("reason_chain"), list) else []
    latest = reason_chain[-1] if reason_chain and isinstance(reason_chain[-1], dict) else {}
    return {
        "present": bool(reason_chain),
        "count": len(reason_chain),
        "latest_inference_rule": latest.get("inference_rule") if isinstance(latest.get("inference_rule"), str) else None,
        "latest_conclusion": latest.get("conclusion") if isinstance(latest.get("conclusion"), str) else None,
        "latest_action": latest.get("action") if isinstance(latest.get("action"), str) else None,
    }


def _collect_measurement_memory_assessment(base_dir: Optional[str] = None, limit: int = 250) -> Dict[str, Any]:
    base = base_dir or BASE
    semantic_dir = os.path.join(base, "LongTermStore", "Semantic")
    assessment_cfg = _load_json_file(os.path.join(base, "config.json"))
    if not isinstance(assessment_cfg, dict):
        assessment_cfg = {}
    telemetry = _collect_spatial_telemetry(base_dir=base, limit=10)
    request_provenance_index = _build_request_provenance_index(base)
    tracked_measurement_hashes: set[str] = set()
    tracked_request_ids: set[str] = set()
    primary_context_record: Optional[Dict[str, Any]] = None
    primary_measurement_record: Optional[Dict[str, Any]] = None

    result: Dict[str, Any] = {
        "measurement_recorded": False,
        "measurement_memory_persisted": False,
        "measurement_hash_present": False,
        "spatial_snapshot_present": False,
        "telemetry_present": False,
        "telemetry_completed_present": False,
        "composition_artifact_present": False,
        "composition_bridge_output_present": False,
        "ai_brain_demo_last_measurement_present": False,
        "ai_brain_demo_spatial_memory_file_present": False,
        "ai_brain_demo_object_memory_store_durable": False,
        "ai_brain_durable_memory_contract": {
            "status": "missing",
            "brain_state_present": False,
            "spatial_memory_present": False,
            "spatial_memory_measurement_count": 0,
            "contract_paths": {
                "brain_state": "AI_Brain/brain_state.json",
                "spatial_memory": "AI_Brain/memory/spatial_memory.json",
            },
            "alignment": {
                "status": "missing",
                "durable_contract_explicit": False,
                "validated_measurement_present": False,
                "validated_measurement_preserved": False,
                "measurement_hash_matches_semantic_record": False,
                "request_id_matches_semantic_record": False,
                "record_id_matches_semantic_record": False,
                "brain_state_measurement_hash_present": False,
                "spatial_memory_measurement_hash_present": False,
                "validation_summary_present": False,
                "validation_passed": False,
                "bridge_output_present": False,
                "snapshot_present": False,
                "summary": "durable spatial-memory contract is not present",
            },
        },
        "retained_storage_pressure": {
            "available": False,
            "metrics": {},
            "reason": "not_collected",
        },
        "semantic_records_scanned": 0,
        "telemetry_rollup": {
            "total_events": 0,
            "completed_event_count": 0,
            "last_completed_event": None,
            "latest_status_by_measurement_hash": {},
            "latest_status_by_request_id": {},
        },
        "joined_provenance": None,
        "runtime_lineage_integration_summary": {
            "status": "missing",
            "join_chain_present": False,
            "measurement_recorded": False,
            "measurement_hash_present": False,
            "spatial_snapshot_present": False,
            "composition_artifact_present": False,
            "bridge_output_present": False,
        },
        "categorized_context_inventory": {
            "scanned_records": 0,
            "reference_profile_present_count": 0,
            "support_level_counts": {},
            "join_status_counts": {},
            "join_quality_counts": {},
            "follow_through_status_counts": {},
            "persistence_status_counts": {},
        },
        "categorized_context_follow_through": {
            "status": "missing",
            "join_status": "missing",
            "join_quality": "missing",
            "persistence_status": "missing",
            "matched_reference_category_count": 0,
            "matched_reference_term_count": 0,
            "gap_reasons": [],
            "inventory": {
                "join_quality_counts": {},
                "follow_through_status_counts": {},
                "persistence_status_counts": {},
            },
        },
        "decision_trace_summary": {
            "present": False,
            "scene_validation_present": False,
            "reason_chain_count": 0,
            "decision_signals_count": 0,
        },
        "memory_consolidation_review_signal": {
            "status": "defer",
            "reconsider_later": False,
            "current_window_only": True,
            "evidence": {
                "retained_file_count": 0,
                "reference_profile_present_count": 0,
                "strong_support_record_count": 0,
                "aligned_join_record_count": 0,
                "primary_reference_use_score": 0.0,
            },
            "thresholds": {
                "min_retained_file_count": 10,
                "min_reference_profile_present_count": 2,
                "min_strong_support_record_count": 2,
                "min_primary_reference_use_score": 0.75,
            },
            "threshold_gaps": {
                "retained_file_count": 10,
                "reference_profile_present_count": 2,
                "strong_support_record_count": 2,
                "primary_reference_use_score": 0.75,
            },
        },
        "workflow_provenance_summary": None,
        "workflow_interpretation_summary": None,
        "mapped_utilization_summary": None,
        "observability_retention_summary": None,
        "runtime_inventory_summary": None,
        "extrapolation_runtime_inventory_summary": None,
        "reason_chain_summary": {
            "present": False,
            "count": 0,
            "latest_inference_rule": None,
            "latest_conclusion": None,
            "latest_action": None,
        },
        "selection_migration_sandbox": None,
        "examples": {
            "measurement_record_ids": [],
            "snapshot_record_ids": [],
            "composition_record_ids": [],
            "bridge_record_ids": [],
        },
        "notes": [],
        "retained_memory_capability_measurement_summary": {
            "status": "missing",
            "reference_use_summary": {
                "status": "missing",
                "reference_profile_present": False,
                "retrieval_component_present": False,
                "reference_use_score": 0.0,
                "reference_use_breakdown": {
                    "label_match_count": 0,
                    "alias_match_count": 0,
                    "comparison_axis_match_count": 0,
                },
                "matched_reference_category_count": 0,
                "matched_reference_term_count": 0,
                "summary": "reference-use evidence is not explicit in retained categorized context",
            },
            "categorized_context_benefit_summary": {
                "status": "missing",
                "support_level": "missing",
                "join_status": "missing",
                "join_quality": "missing",
                "follow_through_status": "missing",
                "retrieval_signal_present": False,
                "retrieval_ready": False,
                "telemetry_retained": False,
                "relation_family_count": 0,
                "bridge_source_count": 0,
                "summary": "categorized-context benefit is not available in the current retained window",
            },
            "retained_storage_pressure_summary": {
                "status": "unavailable",
                "available": False,
                "retained_file_count": 0,
                "retained_total_bytes": 0,
                "candidate_partition_count": 0,
                "candidate_partition_roots": [],
                "storage_density_bytes_per_file": 0.0,
                "largest_root_by_bytes": {},
                "metrics_hash": "",
                "inputs_hash": "",
                "summary": "retained-storage pressure metrics are unavailable",
            },
            "summary": "retained-memory capability measurement is unavailable",
            "measurement_hash": "",
        },
        "ai_brain_durable_contract_alignment_summary": {
            "status": "missing",
            "durable_memory_contract_status": "missing",
            "categorized_context_follow_through_status": "missing",
            "persistence_status": "missing",
            "retained_memory_capability_status": "missing",
            "spatial_memory_measurement_count": 0,
            "gap_reasons": [],
        },
    }

    measurement_record_ids: List[str] = []
    snapshot_record_ids: List[str] = []
    composition_record_ids: List[str] = []
    bridge_record_ids: List[str] = []

    if os.path.isdir(semantic_dir):
        files = _list_recent_files(semantic_dir, suffix=".json", limit=limit)
        result["semantic_records_scanned"] = len(files)
        for path in files:
            record = _load_json_file(path)
            if not isinstance(record, dict):
                continue
            if primary_context_record is None:
                primary_context_record = record
            inventory_entry = _build_categorized_context_inventory_entry(record)
            result["categorized_context_inventory"]["scanned_records"] += 1
            if inventory_entry["reference_profile_present"]:
                result["categorized_context_inventory"]["reference_profile_present_count"] += 1
            support_level = str(inventory_entry["support_level"])
            join_status = str(inventory_entry["join_status"])
            join_quality = str(inventory_entry.get("join_quality") or "missing")
            follow_through_status = str(inventory_entry.get("follow_through_status") or "missing")
            persistence_status = str(inventory_entry.get("persistence_status") or "missing")
            support_counts = result["categorized_context_inventory"]["support_level_counts"]
            join_counts = result["categorized_context_inventory"]["join_status_counts"]
            join_quality_counts = result["categorized_context_inventory"]["join_quality_counts"]
            follow_through_counts = result["categorized_context_inventory"]["follow_through_status_counts"]
            persistence_counts = result["categorized_context_inventory"]["persistence_status_counts"]
            support_counts[support_level] = int(support_counts.get(support_level, 0)) + 1
            join_counts[join_status] = int(join_counts.get(join_status, 0)) + 1
            join_quality_counts[join_quality] = int(join_quality_counts.get(join_quality, 0)) + 1
            follow_through_counts[follow_through_status] = int(follow_through_counts.get(follow_through_status, 0)) + 1
            persistence_counts[persistence_status] = int(persistence_counts.get(persistence_status, 0)) + 1

            record_id = record.get("id") if isinstance(record.get("id"), str) else os.path.splitext(os.path.basename(path))[0]
            rel_state = record.get("relational_state") if isinstance(record.get("relational_state"), dict) else {}
            artifacts = record.get("artifacts") if isinstance(record.get("artifacts"), dict) else {}

            spatial_measurement = rel_state.get("spatial_measurement") if isinstance(rel_state.get("spatial_measurement"), dict) else None
            if isinstance(spatial_measurement, dict) and spatial_measurement:
                result["measurement_recorded"] = True
                result["measurement_memory_persisted"] = True
                if primary_measurement_record is None:
                    primary_measurement_record = record
                if len(measurement_record_ids) < 5:
                    measurement_record_ids.append(str(record_id))

            derived = rel_state.get("derived") if isinstance(rel_state.get("derived"), dict) else {}
            spatial_artifacts = artifacts.get("spatial_snapshots") if isinstance(artifacts.get("spatial_snapshots"), dict) else {}
            latest_snapshot = spatial_artifacts.get("latest") if isinstance(spatial_artifacts.get("latest"), dict) else {}

            if isinstance(spatial_artifacts.get("measurement_hash"), str) and spatial_artifacts.get("measurement_hash"):
                result["measurement_hash_present"] = True
                tracked_measurement_hashes.add(spatial_artifacts.get("measurement_hash"))
            if isinstance(derived.get("spatial_measurement_hash"), str) and derived.get("spatial_measurement_hash"):
                result["measurement_hash_present"] = True
                tracked_measurement_hashes.add(derived.get("spatial_measurement_hash"))
            if not result["measurement_hash_present"] and isinstance(spatial_measurement, dict) and spatial_measurement:
                try:
                    tracked_measurement_hashes.add(hashlib.sha256(canonical_json_bytes(spatial_measurement)).hexdigest())
                except Exception:
                    pass

            snapshot_relpath = latest_snapshot.get("relative_path") if isinstance(latest_snapshot.get("relative_path"), str) else None
            if snapshot_relpath:
                snapshot_abspath = os.path.join(base, snapshot_relpath.replace("/", os.sep))
                if os.path.isfile(snapshot_abspath):
                    result["spatial_snapshot_present"] = True
                    if len(snapshot_record_ids) < 5:
                        snapshot_record_ids.append(str(record_id))

            bridge_outputs = rel_state.get("bridge_outputs") if isinstance(rel_state.get("bridge_outputs"), list) else []
            if any(isinstance(payload, dict) and payload.get("source") == "3d_scene_summary" for payload in bridge_outputs):
                result["composition_bridge_output_present"] = True
                if len(bridge_record_ids) < 5:
                    bridge_record_ids.append(str(record_id))

            composition_keys = (
                "composition_request",
                "composition_response",
                "composition_scene_summary",
                "composition_validation_summary",
                "composition_recipe",
                "scene_manifest",
                "validation_summary",
                "recipe_sidecar",
            )
            if any(isinstance(artifacts.get(key), dict) for key in composition_keys):
                result["composition_artifact_present"] = True
                if len(composition_record_ids) < 5:
                    composition_record_ids.append(str(record_id))

            composition_request = artifacts.get("composition_request") if isinstance(artifacts.get("composition_request"), dict) else {}
            composition_response = artifacts.get("composition_response") if isinstance(artifacts.get("composition_response"), dict) else {}
            composition_validation_summary = artifacts.get("composition_validation_summary") if isinstance(artifacts.get("composition_validation_summary"), dict) else {}
            validation_summary = artifacts.get("validation_summary") if isinstance(artifacts.get("validation_summary"), dict) else {}
            for request_id in (
                composition_request.get("request_id"),
                composition_response.get("request_id"),
                composition_validation_summary.get("request_id"),
                validation_summary.get("request_id"),
            ):
                if isinstance(request_id, str) and request_id:
                    tracked_request_ids.add(request_id)

            if result.get("joined_provenance") is None:
                joined = _collect_joined_provenance_chain(
                    base_dir=base,
                    record_id=str(record_id),
                    rel_state=rel_state,
                    artifacts=artifacts,
                    request_provenance_index=request_provenance_index,
                )
                if isinstance(joined, dict):
                    result["joined_provenance"] = joined

    telemetry_rollup = _collect_spatial_telemetry_rollup(
        base_dir=base,
        tracked_measurement_hashes=sorted(tracked_measurement_hashes),
        tracked_request_ids=sorted(tracked_request_ids),
    )
    result["telemetry_present"] = bool(telemetry_rollup.get("total_events"))
    result["telemetry_completed_present"] = bool(telemetry_rollup.get("completed_event_count"))
    result["telemetry_rollup"] = telemetry_rollup

    ai_brain_dir = os.path.join(base, "AI_Brain")
    brain_state = _load_json_file(os.path.join(ai_brain_dir, "brain_state.json")) if os.path.isdir(ai_brain_dir) else None
    if isinstance(brain_state, dict) and isinstance(brain_state.get("last_measurement"), dict) and brain_state.get("last_measurement"):
        result["ai_brain_demo_last_measurement_present"] = True

    spatial_memory_path = os.path.join(ai_brain_dir, "memory", "spatial_memory.json")
    spatial_memory_payload = _load_json_file(spatial_memory_path)
    if isinstance(spatial_memory_payload, dict):
        result["ai_brain_demo_spatial_memory_file_present"] = True
        measurements = spatial_memory_payload.get("measurements")
        if isinstance(measurements, list) and measurements:
            result["measurement_memory_persisted"] = True
    result["retained_storage_pressure"] = build_retained_storage_pressure_metrics(root_path=base)
    runtime_effectiveness_payload = _load_json_file(
        os.path.join(base, "TemporaryQueue", "runtime_effectiveness_latest.json")
    )
    workflow_chart_payload = _load_json_file(os.path.join(base, "TemporaryQueue", "composition_workflow_chart_latest.json"))
    if isinstance(workflow_chart_payload, dict) and isinstance(workflow_chart_payload.get("workflow_provenance_summary"), dict):
        result["workflow_provenance_summary"] = workflow_chart_payload.get("workflow_provenance_summary")
    if isinstance(workflow_chart_payload, dict) and isinstance(workflow_chart_payload.get("workflow_interpretation_summary"), dict):
        result["workflow_interpretation_summary"] = workflow_chart_payload.get("workflow_interpretation_summary")
    if isinstance(workflow_chart_payload, dict) and isinstance(workflow_chart_payload.get("mapped_utilization_summary"), dict):
        result["mapped_utilization_summary"] = workflow_chart_payload.get("mapped_utilization_summary")
    if isinstance(workflow_chart_payload, dict) and isinstance(workflow_chart_payload.get("observability_retention_summary"), dict):
        result["observability_retention_summary"] = workflow_chart_payload.get("observability_retention_summary")
    if isinstance(runtime_effectiveness_payload, dict) and isinstance(runtime_effectiveness_payload.get("runtime_inventory"), dict):
        result["runtime_inventory_summary"] = runtime_effectiveness_payload.get("runtime_inventory")
    if isinstance(runtime_effectiveness_payload, dict) and isinstance(
        runtime_effectiveness_payload.get("extrapolation_runtime_inventory"), dict
    ):
        result["extrapolation_runtime_inventory_summary"] = runtime_effectiveness_payload.get(
            "extrapolation_runtime_inventory"
        )
    result["runtime_lineage_integration_summary"] = _summarize_runtime_lineage_integration(
        joined_provenance=result["joined_provenance"] if isinstance(result.get("joined_provenance"), dict) else None,
        measurement_recorded=bool(result["measurement_recorded"]),
        measurement_hash_present=bool(result["measurement_hash_present"]),
        spatial_snapshot_present=bool(result["spatial_snapshot_present"]),
        composition_artifact_present=bool(result["composition_artifact_present"]),
        composition_bridge_output_present=bool(result["composition_bridge_output_present"]),
    )

    result["examples"] = {
        "measurement_record_ids": measurement_record_ids,
        "snapshot_record_ids": snapshot_record_ids,
        "composition_record_ids": composition_record_ids,
        "bridge_record_ids": bridge_record_ids,
    }

    result["measurement_adequacy"] = _summarize_measurement_adequacy(
        measurement_recorded=result["measurement_recorded"],
        snapshot_present=result["spatial_snapshot_present"],
        measurement_hash_present=result["measurement_hash_present"],
        bridge_present=result["composition_bridge_output_present"],
        telemetry_completed_present=result["telemetry_completed_present"],
        spatial_telemetry=telemetry,
    )

    categorized_record = primary_measurement_record or primary_context_record
    reference_record = None
    joined_provenance = result.get("joined_provenance") if isinstance(result.get("joined_provenance"), dict) else {}
    composition_record_id = joined_provenance.get("composition_record_id") if isinstance(joined_provenance.get("composition_record_id"), str) else None
    categorized_record_id = categorized_record.get("id") if isinstance(categorized_record, dict) and isinstance(categorized_record.get("id"), str) else None
    if composition_record_id and composition_record_id != categorized_record_id:
        reference_record = _load_semantic_record_by_id(base, composition_record_id)
    result["categorized_context"] = _summarize_categorized_context_bundle(
        categorized_record,
        reference_record=reference_record,
    )
    result["categorized_context_follow_through"] = _summarize_categorized_context_follow_through(
        categorized_context=result["categorized_context"],
        categorized_context_inventory=result["categorized_context_inventory"],
    )
    result["ai_brain_durable_memory_contract"] = build_ai_brain_durable_memory_contract_snapshot(
        root_path=base,
        measurement_record=categorized_record,
        joined_provenance=result["joined_provenance"] if isinstance(result.get("joined_provenance"), dict) else None,
    )
    result["retained_memory_capability_measurement_summary"] = build_retained_memory_capability_measurement_summary(
        categorized_summary=result["categorized_context"],
        retained_storage_pressure=result["retained_storage_pressure"],
        retained_memory_follow_through_summary={
            "categorized_context_follow_through_summary": result["categorized_context_follow_through"],
            "retrieval_readiness_summary": {
                "retrieval_ready": bool(
                    result["categorized_context"].get("reference_profile_present")
                    or str(result["categorized_context"].get("support_level") or "missing") != "missing"
                )
            },
            "telemetry_retention_summary": {
                "telemetry_retained": bool(
                    result["telemetry_present"]
                    or result["telemetry_completed_present"]
                    or result["measurement_hash_present"]
                    or result["spatial_snapshot_present"]
                ),
            },
        },
    )
    result["ai_brain_durable_contract_alignment_summary"] = build_ai_brain_durable_contract_alignment_summary(
        durable_memory_contract_summary={
            "status": str(result["ai_brain_durable_memory_contract"].get("status") or "missing"),
            "spatial_memory_measurement_count": int(
                result["ai_brain_durable_memory_contract"].get("spatial_memory_measurement_count") or 0
            ),
        },
        categorized_context_follow_through_summary=result["categorized_context_follow_through"],
        retained_memory_capability_summary=result["retained_memory_capability_measurement_summary"],
    )
    if isinstance(categorized_record, dict):
        decision_signals = categorized_record.get("decision_signals")
        if isinstance(decision_signals, list):
            for entry in reversed(decision_signals):
                if not isinstance(entry, dict):
                    continue
                sandbox = entry.get("selection_migration_sandbox")
                if isinstance(sandbox, dict):
                    result["selection_migration_sandbox"] = dict(sandbox)
                    break
    result["comprehension_review"] = _summarize_comprehension_review(
        categorized_record,
        measurement_adequacy=result["measurement_adequacy"],
        categorized_context=result["categorized_context"],
    )
    result["learning_readiness"] = _summarize_learning_readiness(
        measurement_adequacy=result["measurement_adequacy"],
        categorized_context=result["categorized_context"],
        comprehension_review=result["comprehension_review"],
    )
    supporting_evidence = (
        result["comprehension_review"].get("supporting_evidence")
        if isinstance(result["comprehension_review"], dict)
        and isinstance(result["comprehension_review"].get("supporting_evidence"), dict)
        else None
    )
    if isinstance(supporting_evidence, dict):
        supporting_evidence["retained_memory_capability_measurement_summary"] = dict(
            result["retained_memory_capability_measurement_summary"]
        )
    learning_evidence = (
        result["learning_readiness"].get("evidence")
        if isinstance(result["learning_readiness"], dict)
        and isinstance(result["learning_readiness"].get("evidence"), dict)
        else None
    )
    if isinstance(learning_evidence, dict):
        learning_evidence["retained_memory_capability_measurement_summary"] = dict(
            result["retained_memory_capability_measurement_summary"]
        )
    result["mirrored_parameter_review"] = build_mirrored_parameter_review_summary(
        categorized_record,
        cfg=assessment_cfg,
    )
    result["multi_location_comprehension_review"] = build_multi_location_comprehension_review_summary(
        categorized_record,
        cfg=assessment_cfg,
        mirrored_parameter_review_summary=result["mirrored_parameter_review"],
    )
    result["decision_trace_summary"] = _summarize_decision_trace(categorized_record)
    result["memory_consolidation_review_signal"] = _summarize_memory_consolidation_review_signal(
        retained_storage_pressure=result["retained_storage_pressure"],
        categorized_context=result["categorized_context"],
        categorized_context_inventory=result["categorized_context_inventory"],
    )
    result["reason_chain_summary"] = _summarize_reason_chain(categorized_record)
    notes: List[str] = []
    if not result["measurement_recorded"]:
        notes.append("No semantic record with relational_state.spatial_measurement was found in the scanned window.")
    sample_completed_present = bool((telemetry.get("status_counts") or {}).get("completed"))
    if result["telemetry_present"] and not result["telemetry_completed_present"]:
        notes.append("Spatial telemetry exists, but no completed measurement event was found in the full telemetry ledger.")
    elif result["telemetry_completed_present"] and not sample_completed_present:
        last_completed_event = result["telemetry_rollup"].get("last_completed_event") if isinstance(result.get("telemetry_rollup"), dict) else None
        last_completed_timestamp = None
        if isinstance(last_completed_event, dict) and isinstance(last_completed_event.get("timestamp_fixed"), str):
            last_completed_timestamp = last_completed_event.get("timestamp_fixed")
        completed_count = result["telemetry_rollup"].get("completed_event_count") if isinstance(result.get("telemetry_rollup"), dict) else None
        if isinstance(completed_count, int) and completed_count > 0:
            if last_completed_timestamp:
                notes.append(
                    f"Recent telemetry sampling missed completed events, but the full telemetry ledger found {completed_count} completed event(s); the last completed event was at {last_completed_timestamp}."
                )
            else:
                notes.append(
                    f"Recent telemetry sampling missed completed events, but the full telemetry ledger found {completed_count} completed event(s)."
                )
    if not result["spatial_snapshot_present"]:
        notes.append("No persisted spatial snapshot file was linked from the scanned semantic records.")
    if not result["composition_artifact_present"]:
        notes.append("No persisted composition sidecar artifact was found in the scanned semantic records.")
    if not result["composition_bridge_output_present"]:
        notes.append("No persisted 3d_scene_summary bridge output was found in the scanned semantic records.")
    if result["composition_artifact_present"] and result["measurement_recorded"] and result.get("joined_provenance") is None:
        notes.append("Composition and measurement evidence exist, but no joined provenance chain could be recovered from the scanned records or historical runtime evidence.")
    if result["ai_brain_demo_last_measurement_present"] and not result["ai_brain_demo_spatial_memory_file_present"]:
        notes.append("The legacy AI_Brain demo stores last_measurement in brain_state.json, but no durable spatial_memory.json file is present.")
    if result["ai_brain_durable_memory_contract"]["status"] == "complete":
        notes.append(
            f"AI_Brain durable-memory contract is complete: brain_state.json and spatial_memory.json are both present"
            f" (spatial measurements={result['ai_brain_durable_memory_contract']['spatial_memory_measurement_count']})."
        )
    if (
        isinstance(result["ai_brain_durable_memory_contract"].get("alignment"), dict)
        and result["ai_brain_durable_memory_contract"]["alignment"].get("validated_measurement_present")
        and not result["ai_brain_durable_memory_contract"]["alignment"].get("validated_measurement_preserved")
    ):
        notes.append("Validated semantic measurements are present, but durable AI_Brain preservation is not yet fully explicit across both contract files.")
    notes.append("AI_Brain object_memory_store remains in-process only; durable legacy evidence comes from brain_state.json and optional spatial_memory.json.")
    result["notes"] = notes
    return result


def cmd_measurement_memory_assess(args):
    report = _collect_measurement_memory_assessment(
        base_dir=BASE,
        limit=int(max(1, getattr(args, "limit", 250))),
    )
    print(json.dumps(report, indent=2))


def cmd_spatial_gallery(args):
    report = _export_spatial_gallery(
        base_dir=BASE,
        limit=int(max(0, getattr(args, "limit", 24))),
        out_dir=getattr(args, "out_dir", None),
    )
    print(json.dumps(report, indent=2))


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

    spatial_overview = _collect_spatial_overview(limit=5)
    if spatial_overview.get('total_records'):
        out['spatial_overview'] = spatial_overview

    spatial_telemetry = _collect_spatial_telemetry(limit=10)
    if spatial_telemetry.get('events'):
        out['spatial_telemetry'] = spatial_telemetry
    out['measurement_adequacy'] = _summarize_measurement_adequacy(
        spatial_overview=spatial_overview,
        spatial_telemetry=spatial_telemetry,
    )
    out['categorized_context'] = _collect_categorized_context_assessment(base_dir=BASE, limit=5)
    out['comprehension_review'] = _collect_comprehension_review_assessment(
        base_dir=BASE,
        limit=5,
        measurement_adequacy=out['measurement_adequacy'],
        categorized_context=out['categorized_context'],
    )
    out['learning_readiness'] = _summarize_learning_readiness(
        measurement_adequacy=out['measurement_adequacy'],
        categorized_context=out['categorized_context'],
        comprehension_review=out['comprehension_review'],
    )
    print(json.dumps(out, indent=2))


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
    from module_project_backup import backup_project_to_archive
    archive_root = resolve_archive_root(getattr(args, 'archive_root', None))
    if not archive_root:
        print(json.dumps({
            'ok': False,
            'error': 'archive_root is required (pass --archive-root or set AI_ALGORITHMS_ARCHIVE_ROOT)',
        }, indent=2))
        sys.exit(2)
    try:
        mode = getattr(args, 'mode', 'full')
        if mode == 'full':
            rep = backup_project_to_archive(
                repo_root=BASE,
                archive_root=archive_root,
                project_dir_name=getattr(args, 'project_name', 'AI_Algorithms'),
                dry_run=bool(getattr(args, 'dry_run', False)),
            )
        else:
            rep = backup_repo_to_archive(
                repo_root=BASE,
                archive_root=archive_root,
                project_dir_name=getattr(args, 'project_name', 'AI_Algorithms'),
                mode=mode,
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


def cmd_3d_cache_status(args):
    try:
        from module_ai_brain_bridge import (  # type: ignore
            get_3d_metrics,
            get_cache_stats,
            clear_3d_cache,
            get_3d_limits,
        )
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': f'module_ai_brain_bridge import failed: {exc}'}, indent=2))
        sys.exit(1)

    try:
        from module_relational_adapter import (  # type: ignore
            get_3d_cycle_counters_snapshot,
            reset_3d_cycle_counters,
        )
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': f'module_relational_adapter import failed: {exc}'}, indent=2))
        sys.exit(1)

    result = {
        'ok': True,
        'metrics': get_3d_metrics(),
        'cache': get_cache_stats(),
        'cycle_counters': get_3d_cycle_counters_snapshot(),
        'limits': get_3d_limits(),
        'reset_performed': False,
    }

    if getattr(args, 'reset', False):
        clear_3d_cache()
        reset_3d_cycle_counters()
        result['reset_performed'] = True

    print(json.dumps(result, indent=2))

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
    st.add_argument('--policy-rate', action='store_true', help='Include activation-rate snapshot based on thresholds')
    st.add_argument('--sel-min-ben-syn', type=float, dest='sel_min_ben_syn', help='Override selection score threshold for beneficial+synthesis')
    st.add_argument('--composite-activate', type=float, dest='composite_activate', help='Override composite score threshold to activate')
    st.set_defaults(func=cmd_status)

    scache = sub.add_parser('3d-cache-status', help='Show 3D cache snapshot and optionally reset counters')
    scache.add_argument('--reset', action='store_true', help='Clear cache and cycle counters after reporting')
    scache.set_defaults(func=cmd_3d_cache_status)

    smma = sub.add_parser('measurement-memory-assess', help='Assess whether composition artifacts, measurements, and measurement memory evidence are currently persisted')
    smma.add_argument('--limit', type=int, default=250, help='Maximum number of recent semantic records to scan')
    smma.set_defaults(func=cmd_measurement_memory_assess)

    sireview = sub.add_parser('import-teacher-review', help='Validate and normalize the Teacher-authored Visual Pipeline review adapter into a bounded review-only inbound evidence artifact')
    sireview.add_argument('--input', required=True, help='Path to visual_pipeline_teacher_interest_adapter.json or equivalent Teacher-authored adapter JSON')
    sireview.add_argument('--out', default=None, help='Optional output path for the normalized inbound review artifact')
    sireview.add_argument('--no-write', action='store_true', help='Validate and print the normalized summary without writing an artifact file')
    sireview.add_argument('--raw', action='store_true', help='Print the full normalized inbound review artifact JSON')
    sireview.set_defaults(func=cmd_import_teacher_review)

    sgallery = sub.add_parser('spatial-gallery', help='Render deterministic SVG previews and an HTML gallery for persisted spatial snapshots')
    sgallery.add_argument('--limit', type=int, default=24, help='Maximum number of recent spatial snapshots to render')
    sgallery.add_argument('--out-dir', default='TemporaryQueue/spatial_gallery', help='Output directory for preview SVGs, gallery HTML, and the report JSON')
    sgallery.set_defaults(func=cmd_spatial_gallery)

    scompose = sub.add_parser('compose-request', help='Emit a deterministic Blender composition request stub without requiring bpy')
    scompose.add_argument('--action', choices=['load_environment', 'add_light', 'set_camera', 'apply_material', 'validate_scene', 'export_scene'], default=None, help='Action name for the sample request')
    scompose.add_argument('--scene-id', default=None, help='Scene identifier for the sample request')
    scompose.add_argument('--recipe-id', default=None, help='Recipe identifier for the sample request')
    scompose.add_argument('--recipe-version', default=None, help='Recipe version for the sample request')
    scompose.add_argument('--export-format', choices=['ply', 'obj'], default=None, help='Export format for export_scene requests')
    scompose.add_argument('--out', default=None, help='Optional path to write the emitted request JSON')
    scompose.set_defaults(func=cmd_compose_request)

    scompose_response = sub.add_parser('compose-response', help='Emit a deterministic dry-run Blender composition response without requiring bpy')
    scompose_response.add_argument('--request', default=None, help='Optional path to an existing compose-request JSON payload')
    scompose_response.add_argument('--status', choices=['accepted', 'completed', 'rejected', 'error'], default='completed', help='Response status to emit')
    scompose_response.add_argument('--error-code', choices=['invalid_request', 'invalid_action', 'missing_artifact', 'validation_failed', 'launch_failed', 'internal_error'], default=None, help='Optional error code for rejected/error responses')
    scompose_response.add_argument('--error-message', default=None, help='Optional error message for rejected/error responses')
    scompose_response.add_argument('--action', choices=['load_environment', 'add_light', 'set_camera', 'apply_material', 'validate_scene', 'export_scene'], default=None, help='Action name when generating a starter request in memory')
    scompose_response.add_argument('--scene-id', default=None, help='Scene identifier when generating a starter request in memory')
    scompose_response.add_argument('--recipe-id', default=None, help='Recipe identifier when generating a starter request in memory')
    scompose_response.add_argument('--recipe-version', default=None, help='Recipe version when generating a starter request in memory')
    scompose_response.add_argument('--export-format', choices=['ply', 'obj'], default=None, help='Export format for generated export_scene starter requests')
    scompose_response.add_argument('--out', default=None, help='Optional path to write the emitted response JSON')
    scompose_response.set_defaults(func=cmd_compose_response)

    scompose_receiver = sub.add_parser('compose-receiver-smoke', help='Exercise receiver-boundary duplicate-request and status-phase behavior without requiring bpy or opening a live listener')
    scompose_receiver.add_argument('--request', default=None, help='Optional path to an existing compose-request JSON payload')
    scompose_receiver.add_argument('--action', choices=['load_environment', 'add_light', 'set_camera', 'apply_material', 'validate_scene', 'export_scene'], default=None, help='Action name when generating a starter request in memory')
    scompose_receiver.add_argument('--scene-id', default=None, help='Scene identifier when generating a starter request in memory')
    scompose_receiver.add_argument('--recipe-id', default=None, help='Recipe identifier when generating a starter request in memory')
    scompose_receiver.add_argument('--recipe-version', default=None, help='Recipe version when generating a starter request in memory')
    scompose_receiver.add_argument('--export-format', choices=['ply', 'obj'], default=None, help='Export format for generated export_scene starter requests')
    scompose_receiver.add_argument('--receiver-status', choices=['accepted', 'rejected'], default='accepted', help='Immediate receiver-boundary status to simulate')
    scompose_receiver.add_argument('--runtime-status', choices=['completed', 'error'], default=None, help='Optional later runtime-phase status to simulate after acceptance')
    scompose_receiver.add_argument('--duplicate-replay', action='store_true', help='Treat the current request_id as already seen to simulate idempotent duplicate replay')
    scompose_receiver.add_argument('--known-request-id', action='append', default=None, help='Additional known request_id values used to detect duplicate replay')
    scompose_receiver.add_argument('--out-dir', default=None, help='Optional output root used only for normalized runtime-request path derivation')
    scompose_receiver.set_defaults(func=cmd_compose_receiver_smoke)

    scompose_runtime = sub.add_parser('compose-runtime-artifacts', help='Emit runtime request and lock-event artifacts from a starter composition request without requiring bpy')
    scompose_runtime.add_argument('--request', default=None, help='Optional path to an existing compose-request JSON payload')
    scompose_runtime.add_argument('--action', choices=['load_environment', 'add_light', 'set_camera', 'apply_material', 'validate_scene', 'export_scene'], default=None, help='Action name when generating a starter request in memory')
    scompose_runtime.add_argument('--scene-id', default=None, help='Scene identifier when generating a starter request in memory')
    scompose_runtime.add_argument('--recipe-id', default=None, help='Recipe identifier when generating a starter request in memory')
    scompose_runtime.add_argument('--recipe-version', default=None, help='Recipe version when generating a starter request in memory')
    scompose_runtime.add_argument('--export-format', choices=['ply', 'obj'], default=None, help='Export format for generated export_scene starter requests')
    scompose_runtime.add_argument('--out-dir', default=None, help='Optional output directory for runtime artifacts (defaults under TemporaryQueue/orchestrator)')
    scompose_runtime.add_argument('--emit-claimed', action='store_true', help='Also emit a claimed event after the queued event')
    scompose_runtime.add_argument('--emit-running', action='store_true', help='Also emit a deterministic running event after the claimed event to model active dry-run processing before validation or handoff')
    scompose_runtime.add_argument('--emit-validated', action='store_true', help='Also emit a deterministic validated event after the claimed event to model a pre-measurement success checkpoint')
    scompose_runtime.add_argument('--emit-measure-handoff-event', action='store_true', help='Also emit a deterministic measure_handoff event after validation when a measurement placeholder is being handed to the bridge')
    scompose_runtime.add_argument('--emit-response', action='store_true', help='Also emit a deterministic dry-run response artifact at the declared response path')
    scompose_runtime.add_argument('--response-status', choices=['accepted', 'completed', 'rejected', 'error'], default='completed', help='Status to use when emitting the optional dry-run response artifact')
    scompose_runtime.add_argument('--emit-measurement-handoff', action='store_true', help='Also emit a deterministic measurement-handoff placeholder at the declared measurement record path')
    scompose_runtime.add_argument('--complete-measurement-handoff', action='store_true', help='When emitting the measurement placeholder, mark it as completed_measurement with deterministic completion metadata')
    scompose_runtime.add_argument('--emit-released', action='store_true', help='Also emit a deterministic released event at the end of the dry-run lock lifecycle')
    scompose_runtime.add_argument('--emit-failed', action='store_true', help='Also emit a deterministic failed event and error response for a terminal dry-run failure path')
    scompose_runtime.add_argument('--failure-error-code', choices=['invalid_request', 'invalid_action', 'missing_artifact', 'validation_failed', 'launch_failed', 'internal_error'], default=None, help='Optional error code to use for deterministic terminal failure paths')
    scompose_runtime.add_argument('--failure-error-message', default=None, help='Optional error message to use for deterministic terminal failure paths')
    scompose_runtime.set_defaults(func=cmd_compose_runtime_artifacts)

    si = sub.add_parser('index', help='Rebuild and summarize semantic index')
    si.add_argument('--show-ids', action='store_true', help='Include sorted ids in output')
    si.set_defaults(func=cmd_index)

    ssnap = sub.add_parser('snapshot', help='Export a compact snapshot zip (config, ActiveSpace, recent LongTermStore)')
    ssnap.add_argument('--out', default=None, help='Output zip file path')
    ssnap.add_argument('--collectors', type=int, default=12, help='Recent collector files from LongTermStore/ActiveSpace')
    ssnap.add_argument('--semantic', type=int, default=50, help='Recent semantic JSON files to include')
    ssnap.set_defaults(func=cmd_snapshot)

    sbu = sub.add_parser('backup', help='Backup project to external archive')
    sbu.add_argument('--archive-root', default=None, help='Archive root dir (or set AI_ALGORITHMS_ARCHIVE_ROOT)')
    sbu.add_argument('--project-name', default='AI_Algorithms', help='Project directory name inside Archive_N')
    sbu.add_argument('--mode', choices=['full', 'committed', 'tracked'], default='full', help='full=project tree minus excluded env/build/cache dirs; committed=HEAD only; tracked=all tracked files')
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
    sgc.add_argument('--stage7-runs', type=int, default=3, help='Keep latest N stage-7 orch_blender_cycle_* run folders (default 3)')
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
