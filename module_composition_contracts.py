import hashlib
import json
import os
from copy import deepcopy
from typing import Any, Dict, List

from module_storage import resolve_path
from module_tools import canonical_json_bytes, safe_join


REQUEST_SCHEMA_VERSION = "1.0"
REQUEST_KIND = "blender_composition_request"
RESPONSE_KIND = "blender_composition_response"
REQUEST_ID_PREFIX = "bcomp_"

SUPPORTED_COMPOSITION_ACTIONS = (
    "load_environment",
    "add_light",
    "set_camera",
    "apply_material",
    "validate_scene",
    "export_scene",
)

SUPPORTED_TRANSPORT_MODES = (
    "json_over_tcp",
    "file_drop_queue",
)

SUPPORTED_EXPECTED_OUTPUT_KINDS = (
    "scene_state",
    "export_asset",
    "scene_manifest",
    "validation_summary",
)

SUPPORTED_RESPONSE_STATUSES = (
    "accepted",
    "completed",
    "rejected",
    "error",
)

SUPPORTED_RECEIVER_SMOKE_DECISIONS = (
    "accepted",
    "rejected",
    "duplicate_replay",
)

SUPPORTED_RECEIVER_BOUNDARY_STATUSES = (
    "accepted",
    "rejected",
)

SUPPORTED_RUNTIME_BOUNDARY_STATUSES = (
    "completed",
    "error",
)

SUPPORTED_RESPONSE_ERROR_CODES = (
    "invalid_request",
    "invalid_action",
    "missing_artifact",
    "validation_failed",
    "launch_failed",
    "internal_error",
)

_CHECK_STATUSES = ("pass", "warn", "fail")

_REQUEST_ACTION_REQUIRED_ARGS = {
    "load_environment": ("scene_id", "environment_id"),
    "add_light": ("scene_id", "light_id", "light_type"),
    "set_camera": ("scene_id", "camera_id"),
    "apply_material": ("scene_id", "object_id", "material_id"),
    "validate_scene": ("scene_id", "checks"),
    "export_scene": ("scene_id", "export"),
}

_LEGACY_REQUEST_ACTION_REQUIRED_ARGS = {
    "load_environment": ("environment_id",),
    "add_light": ("light_id", "type"),
    "set_camera": ("camera_id",),
    "apply_material": ("target_id", "material"),
    "validate_scene": ("expected_object_count",),
    "export_scene": ("scene_id", "output_name"),
}

_LEGACY_RESPONSE_STATUSES = ("ok", "error")
RUNTIME_REQUEST_SCHEMA_VERSION = "composition_request_v1"
RUNTIME_LOCK_EVENT_SCHEMA_VERSION = "composition_lock_event_v1"
RUNTIME_MEASUREMENT_HANDOFF_SCHEMA_VERSION = "composition_measurement_handoff_v1"
RUNTIME_LINEAGE_SCHEMA_VERSION = "composition_runtime_lineage_v1"
SUPPORTED_MEASUREMENT_HANDOFF_STATUSES = (
    "pending_measurement",
    "completed_measurement",
    "skipped_measurement",
)
SUPPORTED_RUNTIME_LINEAGE_STATUSES = (
    "pending_scene_summary_attachment",
    "materialized_scene_summary_attachment",
)
SUPPORTED_SEMANTIC_RECORD_TARGET_STATUSES = (
    "pending_materialization",
    "materialized",
)
SUPPORTED_RUNTIME_ARTIFACT_STATUSES = (
    "queued",
    "claimed",
    "running",
    "validated",
    "measure_handoff",
    "failed",
    "released",
    "lineage_materialized",
)

_STARTER_RUNTIME_FORBIDDEN_FIELDS = (
    "schema_version",
    "requester",
    "aps_context",
    "scene",
    "recipe",
    "actions",
    "expected_artifacts",
    "lock_scope",
    "health_gates",
    "handoff",
    "status",
)

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class CompositionSchemaError(Exception):
    """Raised when a composition fixture does not conform to the local contract."""


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _prefixed_stable_hash(payload: Dict[str, Any]) -> str:
    return "sha256:" + _stable_hash(payload)


def _payload_without_key(payload: Dict[str, Any], key: str) -> Dict[str, Any]:
    cloned = deepcopy(payload)
    cloned.pop(key, None)
    return cloned


def _require_dict(obj: Any, label: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise TypeError(f"{label}: expected dict, got {type(obj).__name__}")
    return obj


def _require_str(obj: Dict[str, Any], key: str, label: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CompositionSchemaError(f"{label}: missing or invalid string field '{key}'")
    return value.strip()


def _require_bool(obj: Dict[str, Any], key: str, label: str) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a bool")
    return value


def _require_int(obj: Dict[str, Any], key: str, label: str) -> int:
    value = obj.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CompositionSchemaError(f"{label}: field '{key}' must be an int")
    return value


def _require_nonnegative_int(obj: Dict[str, Any], key: str, label: str) -> int:
    value = _require_int(obj, key, label)
    if value < 0:
        raise CompositionSchemaError(f"{label}: field '{key}' must be >= 0")
    return value


def _validate_optional_prefixed_sha256(value: Any, label: str, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CompositionSchemaError(f"{label}: field '{key}' must be a non-empty string when present")
    _validate_prefixed_sha256(value.strip(), label, key)
    return value.strip()


def _require_dict_field(obj: Dict[str, Any], key: str, label: str) -> Dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a dict")
    return value


def _require_list_field(obj: Dict[str, Any], key: str, label: str) -> List[Any]:
    value = obj.get(key)
    if not isinstance(value, list):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a list")
    return value


def _require_nonempty_string_list(value: Any, label: str) -> List[str]:
    if not isinstance(value, list) or not value:
        raise CompositionSchemaError(f"{label}: expected a non-empty list of strings")
    rows: List[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CompositionSchemaError(f"{label}[{idx}]: must be a non-empty string")
        rows.append(item.strip())
    return rows


def _validate_object_activity_controls(
    action_args: Dict[str, Any],
    *,
    label: str,
    required: bool,
) -> List[Dict[str, Any]]:
    controls = action_args.get("object_activity_controls")
    if controls is None:
        if required:
            raise CompositionSchemaError(f"{label}: missing action_args.object_activity_controls")
        return []
    if not isinstance(controls, list) or not controls:
        raise CompositionSchemaError(f"{label}: action_args.object_activity_controls must be a non-empty list")
    asset_template_ids = [
        str(item).strip()
        for item in (action_args.get("asset_template_ids") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    if asset_template_ids and len(controls) != len(asset_template_ids):
        raise CompositionSchemaError(
            f"{label}: action_args.object_activity_controls must match asset_template_ids length"
        )
    normalized_controls: List[Dict[str, Any]] = []
    for idx, item in enumerate(controls):
        if not isinstance(item, dict):
            raise CompositionSchemaError(f"{label}: action_args.object_activity_controls[{idx}] must be a dict")
        control = dict(item)
        _require_str(control, "object_id_hint", f"{label}.object_activity_controls[{idx}]")
        _require_str(control, "asset_template_id", f"{label}.object_activity_controls[{idx}]")
        _require_str(control, "semantic_record_id", f"{label}.object_activity_controls[{idx}]")
        _require_str(control, "mapped_slice", f"{label}.object_activity_controls[{idx}]")
        _require_str(control, "scheduled_task_id", f"{label}.object_activity_controls[{idx}]")
        _require_str(control, "scheduled_task_type", f"{label}.object_activity_controls[{idx}]")
        control["controlling_carrier_ids"] = _require_nonempty_string_list(
            control.get("controlling_carrier_ids"),
            f"{label}.object_activity_controls[{idx}].controlling_carrier_ids",
        )
        control["controlling_action_ids"] = _require_nonempty_string_list(
            control.get("controlling_action_ids"),
            f"{label}.object_activity_controls[{idx}].controlling_action_ids",
        )
        normalized_controls.append(control)
    return normalized_controls


def _validate_iso_utc(value: str, label: str, key: str) -> None:
    if "T" not in value or not value.endswith("Z"):
        raise CompositionSchemaError(f"{label}: field '{key}' must be an ISO 8601 UTC timestamp")


def _validate_sha256(value: str, label: str, key: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value.lower()):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a 64-character sha256 hex string")


def _validate_request_id_format(value: str, label: str) -> None:
    if not value.startswith(REQUEST_ID_PREFIX):
        raise CompositionSchemaError(f"{label}: request_id must start with '{REQUEST_ID_PREFIX}'")
    suffix = value[len(REQUEST_ID_PREFIX):]
    if len(suffix) != 12 or any(ch not in "0123456789abcdef" for ch in suffix.lower()):
        raise CompositionSchemaError(f"{label}: request_id must end with 12 lowercase hex characters")


def compute_composition_request_id(request_envelope: Dict[str, Any]) -> str:
    request = _require_dict(request_envelope, "composition_request")
    return f"{REQUEST_ID_PREFIX}{_stable_hash(_payload_without_key(request, 'request_id'))[:12]}"


def compute_recipe_hash(recipe_sidecar: Dict[str, Any]) -> str:
    _require_dict(recipe_sidecar, "recipe_sidecar")
    return _stable_hash(_payload_without_key(recipe_sidecar, "recipe_hash"))


def compute_scene_manifest_hash(scene_manifest: Dict[str, Any]) -> str:
    _require_dict(scene_manifest, "scene_manifest")
    return _stable_hash(_payload_without_key(scene_manifest, "scene_hash"))


def compute_validation_summary_hash(validation_summary: Dict[str, Any]) -> str:
    _require_dict(validation_summary, "validation_summary")
    return _stable_hash(_payload_without_key(validation_summary, "summary_hash"))


def _validate_request_action_args(action: str, action_args: Dict[str, Any]) -> None:
    for required_key in _REQUEST_ACTION_REQUIRED_ARGS[action]:
        if required_key not in action_args:
            raise CompositionSchemaError(
                f"composition_request.request: action '{action}' requires action_args.{required_key}"
            )

    if action == "validate_scene":
        checks = action_args.get("checks")
        if not isinstance(checks, list) or not checks:
            raise CompositionSchemaError(
                "composition_request.request: validate_scene requires a non-empty action_args.checks list"
            )
        for idx, check in enumerate(checks):
            if not isinstance(check, str) or not check.strip():
                raise CompositionSchemaError(
                    f"composition_request.request: checks[{idx}] must be a non-empty string"
                )

    if action == "export_scene":
        export_block = action_args.get("export")
        if not isinstance(export_block, dict):
            raise CompositionSchemaError(
                "composition_request.request: export_scene requires action_args.export dict"
            )
        _require_str(export_block, "format", "composition_request.request.action_args.export")
        _require_str(export_block, "path", "composition_request.request.action_args.export")
        _validate_object_activity_controls(
            action_args,
            label="composition_request.request",
            required=False,
        )


def validate_composition_request(obj: Any) -> Dict[str, Any]:
    envelope = _require_dict(obj, "composition_request")
    if "version" not in envelope:
        _require_str(envelope, "request_id", "composition_request")
        _require_str(envelope, "scene_id", "composition_request")
        action = _require_str(envelope, "action", "composition_request")
        if action not in SUPPORTED_COMPOSITION_ACTIONS:
            raise CompositionSchemaError(f"composition_request: unsupported action '{action}'")

        args = _require_dict_field(envelope, "args", "composition_request")
        determinism = _require_dict_field(envelope, "determinism", "composition_request")
        seed = determinism.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise CompositionSchemaError("composition_request: determinism.seed must be an int")
        fixed_timestamp = _require_str(determinism, "fixed_timestamp", "composition_request.determinism")
        _validate_iso_utc(fixed_timestamp, "composition_request.determinism", "fixed_timestamp")
        _require_str(determinism, "noise_mode", "composition_request.determinism")

        expected_artifacts = _require_list_field(envelope, "expected_artifacts", "composition_request")
        for idx, artifact in enumerate(expected_artifacts):
            if not isinstance(artifact, str) or not artifact.strip():
                raise CompositionSchemaError(
                    f"composition_request: expected_artifacts[{idx}] must be a non-empty string"
                )

        for required_key in _LEGACY_REQUEST_ACTION_REQUIRED_ARGS[action]:
            if required_key not in args:
                raise CompositionSchemaError(
                    f"composition_request: action '{action}' requires args.{required_key}"
                )

        metadata = envelope.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise CompositionSchemaError("composition_request: metadata must be a dict when present")

        envelope.setdefault("version", REQUEST_SCHEMA_VERSION)
        envelope.setdefault("kind", REQUEST_KIND)
        envelope.setdefault("created_at", fixed_timestamp)
        envelope.setdefault(
            "task_plan_id",
            str((metadata or {}).get("task_plan_id") or "legacy_fixture"),
        )
        envelope.setdefault(
            "request",
            {
                "scene_id": envelope.get("scene_id"),
                "recipe_id": args.get("recipe_id"),
                "recipe_version": args.get("recipe_version"),
                "action": action,
                "action_args": deepcopy(args),
                "expected_outputs": deepcopy(expected_artifacts),
            },
        )
        return envelope

    version = _require_str(envelope, "version", "composition_request")
    if version != REQUEST_SCHEMA_VERSION:
        raise CompositionSchemaError(
            f"composition_request: unsupported version '{version}'"
        )

    kind = _require_str(envelope, "kind", "composition_request")
    if kind != REQUEST_KIND:
        raise CompositionSchemaError(
            f"composition_request: field 'kind' must be '{REQUEST_KIND}'"
        )

    created_at = _require_str(envelope, "created_at", "composition_request")
    _validate_iso_utc(created_at, "composition_request", "created_at")
    _require_str(envelope, "task_plan_id", "composition_request")
    task_plan_id = str(envelope.get("task_plan_id") or "")

    determinism = _require_dict_field(envelope, "determinism", "composition_request")
    _require_bool(determinism, "deterministic_mode", "composition_request.determinism")
    fixed_timestamp = _require_str(determinism, "fixed_timestamp", "composition_request.determinism")
    _validate_iso_utc(fixed_timestamp, "composition_request.determinism", "fixed_timestamp")
    _require_int(determinism, "3d_seed", "composition_request.determinism")

    transport = _require_dict_field(envelope, "transport", "composition_request")
    mode = _require_str(transport, "mode", "composition_request.transport")
    if mode not in SUPPORTED_TRANSPORT_MODES:
        raise CompositionSchemaError(f"composition_request.transport: unsupported mode '{mode}'")
    _require_str(transport, "host", "composition_request.transport")
    _require_int(transport, "port", "composition_request.transport")

    launcher = _require_dict_field(envelope, "launcher", "composition_request")
    _require_bool(launcher, "dry_run", "composition_request.launcher")
    blender_executable = launcher.get("blender_executable")
    if blender_executable is not None and not isinstance(blender_executable, str):
        raise CompositionSchemaError(
            "composition_request.launcher: field 'blender_executable' must be a string"
        )
    _require_str(launcher, "controller_entrypoint", "composition_request.launcher")
    _require_bool(launcher, "clean_profile", "composition_request.launcher")

    request_body = _require_dict_field(envelope, "request", "composition_request")
    _require_str(request_body, "scene_id", "composition_request.request")
    _require_str(request_body, "recipe_id", "composition_request.request")
    _require_str(request_body, "recipe_version", "composition_request.request")
    action = _require_str(request_body, "action", "composition_request.request")
    if action not in SUPPORTED_COMPOSITION_ACTIONS:
        raise CompositionSchemaError(f"composition_request.request: unsupported action '{action}'")
    action_args = _require_dict_field(request_body, "action_args", "composition_request.request")
    _validate_request_action_args(action, action_args)
    if action == "export_scene" and task_plan_id in {"stage7_scheduler_composition_routing", "3d_runtime_pilot"}:
        _validate_object_activity_controls(
            action_args,
            label="composition_request.request",
            required=True,
        )

    expected_outputs = _require_list_field(request_body, "expected_outputs", "composition_request.request")
    if not expected_outputs:
        raise CompositionSchemaError("composition_request.request: expected_outputs must not be empty")
    for idx, artifact in enumerate(expected_outputs):
        if not isinstance(artifact, dict):
            raise CompositionSchemaError(
                f"composition_request.request: expected_outputs[{idx}] must be a dict"
            )
        kind_value = _require_str(artifact, "kind", f"composition_request.request.expected_outputs[{idx}]")
        if kind_value not in SUPPORTED_EXPECTED_OUTPUT_KINDS:
            raise CompositionSchemaError(
                f"composition_request.request.expected_outputs[{idx}]: unsupported kind '{kind_value}'"
            )
        _require_str(artifact, "path", f"composition_request.request.expected_outputs[{idx}]")

    request_id = _require_str(envelope, "request_id", "composition_request")
    _validate_request_id_format(request_id, "composition_request")
    expected_request_id = compute_composition_request_id(envelope)
    if request_id != expected_request_id:
        raise CompositionSchemaError("composition_request: request_id does not match canonical payload")

    return envelope


def validate_composition_response(obj: Any) -> Dict[str, Any]:
    response = _require_dict(obj, "composition_response")
    if "version" not in response:
        _require_str(response, "request_id", "composition_response")
        _require_str(response, "scene_id", "composition_response")
        action = _require_str(response, "action", "composition_response")
        if action not in SUPPORTED_COMPOSITION_ACTIONS:
            raise CompositionSchemaError(f"composition_response: unsupported action '{action}'")

        status = _require_str(response, "status", "composition_response")
        if status not in _LEGACY_RESPONSE_STATUSES:
            raise CompositionSchemaError(f"composition_response: unsupported status '{status}'")

        emitted_artifacts = _require_list_field(response, "emitted_artifacts", "composition_response")
        for idx, artifact in enumerate(emitted_artifacts):
            if not isinstance(artifact, dict):
                raise CompositionSchemaError(f"composition_response: emitted_artifacts[{idx}] must be a dict")
            _require_str(artifact, "kind", f"composition_response.emitted_artifacts[{idx}]")
            _require_str(artifact, "path", f"composition_response.emitted_artifacts[{idx}]")
            sha_value = _require_str(artifact, "sha256", f"composition_response.emitted_artifacts[{idx}]")
            _validate_sha256(sha_value, f"composition_response.emitted_artifacts[{idx}]", "sha256")

        validation_summary = response.get("validation_summary")
        if validation_summary is not None:
            if not isinstance(validation_summary, dict):
                raise CompositionSchemaError("composition_response: validation_summary must be a dict when present")
            summary_status = _require_str(validation_summary, "status", "composition_response.validation_summary")
            if summary_status not in _CHECK_STATUSES:
                raise CompositionSchemaError(
                    f"composition_response.validation_summary: unsupported status '{summary_status}'"
                )
            check_count = validation_summary.get("check_count")
            if not isinstance(check_count, int) or isinstance(check_count, bool):
                raise CompositionSchemaError(
                    "composition_response.validation_summary: check_count must be an int"
                )

        metadata = response.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise CompositionSchemaError("composition_response: metadata must be a dict when present")
        return response

    version = _require_str(response, "version", "composition_response")
    if version != REQUEST_SCHEMA_VERSION:
        raise CompositionSchemaError(f"composition_response: unsupported version '{version}'")

    kind = _require_str(response, "kind", "composition_response")
    if kind != RESPONSE_KIND:
        raise CompositionSchemaError(
            f"composition_response: field 'kind' must be '{RESPONSE_KIND}'"
        )

    request_id = _require_str(response, "request_id", "composition_response")
    _validate_request_id_format(request_id, "composition_response")

    status = _require_str(response, "status", "composition_response")
    if status not in SUPPORTED_RESPONSE_STATUSES:
        raise CompositionSchemaError(f"composition_response: unsupported status '{status}'")

    action = _require_str(response, "action", "composition_response")
    if action not in SUPPORTED_COMPOSITION_ACTIONS:
        raise CompositionSchemaError(f"composition_response: unsupported action '{action}'")

    artifacts = _require_list_field(response, "artifacts", "composition_response")
    for idx, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise CompositionSchemaError(f"composition_response: artifacts[{idx}] must be a dict")
        kind_value = _require_str(artifact, "kind", f"composition_response.artifacts[{idx}]")
        if kind_value not in SUPPORTED_EXPECTED_OUTPUT_KINDS:
            raise CompositionSchemaError(
                f"composition_response.artifacts[{idx}]: unsupported kind '{kind_value}'"
            )
        _require_str(artifact, "path", f"composition_response.artifacts[{idx}]")
        sha_value = artifact.get("sha256")
        if sha_value is not None:
            if not isinstance(sha_value, str) or not sha_value.strip():
                raise CompositionSchemaError(
                    f"composition_response.artifacts[{idx}]: field 'sha256' must be a non-empty string"
                )
            _validate_sha256(sha_value, f"composition_response.artifacts[{idx}]", "sha256")

    validation_summary = response.get("validation_summary")
    if validation_summary is not None:
        if not isinstance(validation_summary, dict):
            raise CompositionSchemaError("composition_response: validation_summary must be a dict when present")
        summary_status = _require_str(validation_summary, "status", "composition_response.validation_summary")
        if summary_status not in _CHECK_STATUSES:
            raise CompositionSchemaError(
                f"composition_response.validation_summary: unsupported status '{summary_status}'"
            )
        check_count = validation_summary.get("check_count")
        if check_count is not None and (not isinstance(check_count, int) or isinstance(check_count, bool)):
            raise CompositionSchemaError(
                "composition_response.validation_summary: check_count must be an int when present"
            )

    error_block = response.get("error")
    if status in ("rejected", "error"):
        if not isinstance(error_block, dict):
            raise CompositionSchemaError(
                "composition_response: error status requires an error dict"
            )
        code = _require_str(error_block, "code", "composition_response.error")
        if code not in SUPPORTED_RESPONSE_ERROR_CODES:
            raise CompositionSchemaError(
                f"composition_response.error: unsupported code '{code}'"
            )
        _require_str(error_block, "message", "composition_response.error")
        details = error_block.get("details")
        if details is not None and not isinstance(details, dict):
            raise CompositionSchemaError(
                "composition_response.error: details must be a dict when present"
            )
    elif error_block not in (None,):
        raise CompositionSchemaError(
            "composition_response: successful statuses must not include an error block"
        )

    telemetry = response.get("telemetry")
    if telemetry is not None and not isinstance(telemetry, dict):
        raise CompositionSchemaError("composition_response: telemetry must be a dict when present")

    return response


def _compose_response_artifacts(request_envelope: Dict[str, Any], status: str) -> List[Dict[str, Any]]:
    if status != "completed":
        return []

    request_body = request_envelope["request"]
    artifacts: List[Dict[str, Any]] = []
    for item in request_body.get("expected_outputs", []):
        artifact = {
            "kind": item["kind"],
            "path": item["path"],
        }
        artifact["sha256"] = _stable_hash(
            {
                "request_id": request_envelope["request_id"],
                "kind": artifact["kind"],
                "path": artifact["path"],
            }
        )
        artifacts.append(artifact)
    return artifacts


def build_dry_run_composition_response(
    starter_request: Any,
    status: str = "completed",
    error_code: str | None = None,
    error_message: str | None = None,
) -> Dict[str, Any]:
    request = deepcopy(validate_composition_request(starter_request))
    if status not in SUPPORTED_RESPONSE_STATUSES:
        raise CompositionSchemaError(f"compose_response: unsupported status '{status}'")

    request_body = request["request"]
    action = request_body["action"]
    deterministic = request.get("determinism") if isinstance(request.get("determinism"), dict) else {}
    artifacts = _compose_response_artifacts(request, status)

    response = {
        "version": REQUEST_SCHEMA_VERSION,
        "kind": RESPONSE_KIND,
        "request_id": request["request_id"],
        "status": status,
        "action": action,
        "artifacts": artifacts,
        "validation_summary": None,
        "error": None,
        "telemetry": {
            "elapsed_ms": (int(_stable_hash({"request_id": request["request_id"], "status": status})[:4], 16) % 25) + 1,
            "deterministic_mode": bool(deterministic.get("deterministic_mode")),
            "fixed_timestamp": str(deterministic.get("fixed_timestamp") or request["created_at"]),
        },
    }

    if status == "completed":
        checks = request_body.get("action_args", {}).get("checks")
        check_count = len(checks) if isinstance(checks, list) and checks else len(artifacts)
        response["validation_summary"] = {
            "status": "pass",
            "check_count": check_count,
        }
    elif status in ("error", "rejected"):
        resolved_code = error_code or ("invalid_request" if status == "error" else "validation_failed")
        resolved_message = error_message or (
            "dry-run compose-response rejected the starter request" if status == "rejected" else "dry-run compose-response simulated a receiver error"
        )
        response["error"] = {
            "code": resolved_code,
            "message": resolved_message,
            "details": {
                "request_id": request["request_id"],
                "action": action,
            },
        }

    validate_composition_response(response)
    return response


def build_receiver_boundary_smoke_result(
    starter_request: Any,
    *,
    receiver_status: str = "accepted",
    runtime_status: str | None = None,
    known_request_ids: List[str] | None = None,
    output_root: str | None = None,
) -> Dict[str, Any]:
    starter = deepcopy(_validate_starter_compose_request(starter_request))
    if receiver_status not in SUPPORTED_RECEIVER_BOUNDARY_STATUSES:
        raise CompositionSchemaError(
            f"receiver_boundary_smoke: unsupported receiver_status '{receiver_status}'"
        )
    if runtime_status is not None and runtime_status not in SUPPORTED_RUNTIME_BOUNDARY_STATUSES:
        raise CompositionSchemaError(
            f"receiver_boundary_smoke: unsupported runtime_status '{runtime_status}'"
        )
    if receiver_status == "rejected" and runtime_status is not None:
        raise CompositionSchemaError(
            "receiver_boundary_smoke: rejected receiver_status cannot also emit a runtime_status"
        )

    request_id = starter["request_id"]
    known_ids = {
        str(item).strip()
        for item in (known_request_ids or [])
        if isinstance(item, str) and item.strip()
    }
    duplicate_replay = request_id in known_ids
    decision = "duplicate_replay" if duplicate_replay else receiver_status

    runtime_request = build_runtime_composition_request_artifact(
        starter,
        output_root=output_root,
        requester={
            "kind": "receiver_smoke",
            "requested_by": "compose-receiver-smoke",
        },
    )
    receiver_response = build_dry_run_composition_response(starter, status=receiver_status)
    runtime_response = None
    if runtime_status is not None:
        runtime_response = build_dry_run_composition_response(starter, status=runtime_status)

    result = {
        "request_id": request_id,
        "receiver_decision": decision,
        "duplicate_replay": duplicate_replay,
        "first_acceptance": decision == "accepted",
        "normalized_request_boundary": {
            "starter_request_kind": starter["kind"],
            "runtime_request_schema_version": runtime_request["schema_version"],
            "request_id": request_id,
        },
        "receiver_response": receiver_response,
        "runtime_response": runtime_response,
        "status_boundary": {
            "receiver_status": receiver_response["status"],
            "runtime_status": None if runtime_response is None else runtime_response["status"],
            "runtime_phase_present": runtime_response is not None,
        },
        "runtime_request": runtime_request,
    }
    if decision not in SUPPORTED_RECEIVER_SMOKE_DECISIONS:
        raise CompositionSchemaError(
            f"receiver_boundary_smoke: unsupported receiver decision '{decision}'"
        )
    return result


def validate_recipe_sidecar(obj: Any) -> Dict[str, Any]:
    recipe = _require_dict(obj, "recipe_sidecar")
    _require_str(recipe, "recipe_id", "recipe_sidecar")
    _require_str(recipe, "recipe_version", "recipe_sidecar")
    ordered_refs = _require_list_field(recipe, "ordered_context_references", "recipe_sidecar")
    export_settings = _require_dict_field(recipe, "export_settings", "recipe_sidecar")
    steps = _require_list_field(recipe, "steps", "recipe_sidecar")
    recipe_hash = _require_str(recipe, "recipe_hash", "recipe_sidecar")

    for idx, ref in enumerate(ordered_refs):
        if not isinstance(ref, str) or not ref.strip():
            raise CompositionSchemaError(f"recipe_sidecar: ordered_context_references[{idx}] must be a string")

    _require_str(export_settings, "format", "recipe_sidecar.export_settings")

    if not steps:
        raise CompositionSchemaError("recipe_sidecar: steps must not be empty")
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            raise CompositionSchemaError(f"recipe_sidecar: steps[{idx}] must be a dict")
        action = _require_str(step, "action", f"recipe_sidecar.steps[{idx}]")
        if action not in SUPPORTED_COMPOSITION_ACTIONS:
            raise CompositionSchemaError(f"recipe_sidecar: unsupported step action '{action}'")
        _require_dict_field(step, "args", f"recipe_sidecar.steps[{idx}]")

    expected_hash = compute_recipe_hash(recipe)
    if recipe_hash != expected_hash:
        raise CompositionSchemaError("recipe_sidecar: recipe_hash does not match canonical payload")
    return recipe


def validate_scene_manifest(obj: Any) -> Dict[str, Any]:
    manifest = _require_dict(obj, "scene_manifest")
    _require_str(manifest, "scene_id", "scene_manifest")
    _require_str(manifest, "scene_name", "scene_manifest")
    _require_str(manifest, "recipe_id", "scene_manifest")
    _require_str(manifest, "recipe_version", "scene_manifest")
    _require_str(manifest, "recipe_hash", "scene_manifest")
    object_inventory = _require_list_field(manifest, "object_inventory", "scene_manifest")
    exports = _require_list_field(manifest, "exports", "scene_manifest")
    active_camera = _require_str(manifest, "active_camera", "scene_manifest")
    active_lights = _require_list_field(manifest, "active_lights", "scene_manifest")
    scene_hash = _require_str(manifest, "scene_hash", "scene_manifest")

    inventory_ids = set()
    light_ids = set()
    for idx, item in enumerate(object_inventory):
        if not isinstance(item, dict):
            raise CompositionSchemaError(f"scene_manifest: object_inventory[{idx}] must be a dict")
        item_id = _require_str(item, "id", f"scene_manifest.object_inventory[{idx}]")
        item_type = _require_str(item, "type", f"scene_manifest.object_inventory[{idx}]")
        inventory_ids.add(item_id)
        if item_type == "light":
            light_ids.add(item_id)

    for idx, export in enumerate(exports):
        if not isinstance(export, dict):
            raise CompositionSchemaError(f"scene_manifest: exports[{idx}] must be a dict")
        _require_str(export, "format", f"scene_manifest.exports[{idx}]")
        _require_str(export, "path", f"scene_manifest.exports[{idx}]")

    if active_camera not in inventory_ids:
        raise CompositionSchemaError("scene_manifest: active_camera must reference an inventory object")

    for idx, light_id in enumerate(active_lights):
        if not isinstance(light_id, str) or light_id not in light_ids:
            raise CompositionSchemaError(
                f"scene_manifest: active_lights[{idx}] must reference a light inventory object"
            )

    expected_hash = compute_scene_manifest_hash(manifest)
    if scene_hash != expected_hash:
        raise CompositionSchemaError("scene_manifest: scene_hash does not match canonical payload")
    return manifest


def validate_validation_summary(obj: Any) -> Dict[str, Any]:
    summary = _require_dict(obj, "validation_summary")
    _require_str(summary, "summary_id", "validation_summary")
    _require_str(summary, "request_id", "validation_summary")
    _require_str(summary, "scene_id", "validation_summary")
    _require_str(summary, "recipe_hash", "validation_summary")
    status = _require_str(summary, "status", "validation_summary")
    if status not in _CHECK_STATUSES:
        raise CompositionSchemaError(f"validation_summary: unsupported status '{status}'")

    checks = _require_list_field(summary, "checks", "validation_summary")
    warnings = _require_list_field(summary, "warnings", "validation_summary")
    summary_hash = _require_str(summary, "summary_hash", "validation_summary")

    if not checks:
        raise CompositionSchemaError("validation_summary: checks must not be empty")
    for idx, check in enumerate(checks):
        if not isinstance(check, dict):
            raise CompositionSchemaError(f"validation_summary: checks[{idx}] must be a dict")
        _require_str(check, "name", f"validation_summary.checks[{idx}]")
        check_status = _require_str(check, "status", f"validation_summary.checks[{idx}]")
        if check_status not in _CHECK_STATUSES:
            raise CompositionSchemaError(
                f"validation_summary: checks[{idx}] has unsupported status '{check_status}'"
            )

    for idx, warning in enumerate(warnings):
        if not isinstance(warning, str):
            raise CompositionSchemaError(f"validation_summary: warnings[{idx}] must be a string")

    expected_hash = compute_validation_summary_hash(summary)
    if summary_hash != expected_hash:
        raise CompositionSchemaError("validation_summary: summary_hash does not match canonical payload")
    return summary


def build_composition_fixture_bundle(
    request: Any,
    response: Any,
    recipe_sidecar: Any,
    scene_manifest: Any,
    validation_summary: Any,
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_composition_request(request))
    response_obj = deepcopy(validate_composition_response(response))
    recipe_obj = deepcopy(validate_recipe_sidecar(recipe_sidecar))
    manifest_obj = deepcopy(validate_scene_manifest(scene_manifest))
    summary_obj = deepcopy(validate_validation_summary(validation_summary))

    is_enveloped_request = isinstance(request_obj.get("request"), dict)
    request_body = request_obj["request"] if is_enveloped_request else request_obj
    response_artifacts = (
        response_obj.get("artifacts")
        if isinstance(response_obj.get("artifacts"), list)
        else response_obj.get("emitted_artifacts")
    )
    expected_outputs = (
        request_body.get("expected_outputs")
        if isinstance(request_body.get("expected_outputs"), list)
        else request_body.get("expected_artifacts")
    )
    request_scene_id = request_body.get("scene_id")
    request_action = request_body.get("action")
    request_recipe_id = request_body.get("recipe_id")
    request_recipe_version = request_body.get("recipe_version")
    if request_recipe_id is None and isinstance(request_body.get("args"), dict):
        request_recipe_id = request_body["args"].get("recipe_id")
    if request_recipe_version is None and isinstance(request_body.get("args"), dict):
        request_recipe_version = request_body["args"].get("recipe_version")

    if request_obj["request_id"] != response_obj["request_id"]:
        raise CompositionSchemaError("composition_bundle: request_id mismatch between request and response")
    if request_obj["request_id"] != summary_obj["request_id"]:
        raise CompositionSchemaError("composition_bundle: request_id mismatch between request and validation summary")
    if request_scene_id != manifest_obj["scene_id"] or request_scene_id != summary_obj["scene_id"]:
        raise CompositionSchemaError("composition_bundle: scene_id mismatch across bundle")
    if request_action != response_obj["action"]:
        raise CompositionSchemaError("composition_bundle: action mismatch between request and response")
    if request_recipe_id != recipe_obj["recipe_id"] or manifest_obj["recipe_id"] != recipe_obj["recipe_id"]:
        raise CompositionSchemaError("composition_bundle: recipe_id mismatch across bundle")
    if request_recipe_version != recipe_obj["recipe_version"] or manifest_obj["recipe_version"] != recipe_obj["recipe_version"]:
        raise CompositionSchemaError("composition_bundle: recipe_version mismatch across bundle")
    if response_obj["status"] not in ("accepted", "completed", "ok"):
        raise CompositionSchemaError("composition_bundle: response status must be accepted or completed")

    recipe_hash = recipe_obj["recipe_hash"]
    if manifest_obj["recipe_hash"] != recipe_hash or summary_obj["recipe_hash"] != recipe_hash:
        raise CompositionSchemaError("composition_bundle: recipe_hash mismatch across bundle")

    emitted_kinds = {
        artifact["kind"]
        for artifact in (response_artifacts or [])
        if isinstance(artifact, dict) and isinstance(artifact.get("kind"), str)
    }
    expected_kinds = {
        artifact["kind"] if isinstance(artifact, dict) else artifact
        for artifact in (expected_outputs or [])
        if (isinstance(artifact, dict) and isinstance(artifact.get("kind"), str))
        or isinstance(artifact, str)
    }
    if not expected_kinds.issubset(emitted_kinds):
        raise CompositionSchemaError("composition_bundle: response artifacts do not satisfy request expectations")

    response_summary = response_obj.get("validation_summary")
    if response_summary is not None:
        if response_summary.get("status") != summary_obj["status"]:
            raise CompositionSchemaError("composition_bundle: validation status mismatch between response and summary")
        check_count = response_summary.get("check_count")
        if check_count is not None and check_count != len(summary_obj["checks"]):
            raise CompositionSchemaError("composition_bundle: validation check count mismatch")

    bridge_ready = {
        "request_id": request_obj["request_id"],
        "scene_id": request_scene_id,
        "recipe_hash": recipe_hash,
        "entities": [
            {"id": item["id"], "type": item["type"]}
            for item in manifest_obj["object_inventory"]
        ],
        "constraints": [
            {
                "type": "scene_validation",
                "name": check["name"],
                "status": check["status"],
                "expected": check.get("expected"),
                "actual": check.get("actual"),
            }
            for check in summary_obj["checks"]
        ],
        "artifacts": {
            "expected": deepcopy(expected_outputs),
            "emitted": deepcopy(response_artifacts),
            "scene_hash": manifest_obj["scene_hash"],
            "summary_hash": summary_obj["summary_hash"],
        },
        "validation_status": summary_obj["status"],
        "response_status": response_obj["status"],
    }

    request_bundle_obj = deepcopy(request_obj)
    request_bundle_obj.setdefault("scene_id", request_scene_id)
    request_bundle_obj.setdefault("action", request_action)
    request_bundle_obj.setdefault("recipe_id", request_recipe_id)
    request_bundle_obj.setdefault("recipe_version", request_recipe_version)

    response_bundle_obj = deepcopy(response_obj)
    response_bundle_obj.setdefault("emitted_artifacts", deepcopy(response_artifacts))

    runtime_bundle = _build_runtime_artifact_bundle_payload(
        request_obj,
        emit_claimed=True,
        emit_validated=True,
        emit_response=True,
        response_artifact=response_obj,
        recipe_sidecar=recipe_obj,
        scene_manifest=manifest_obj,
        validation_summary=summary_obj,
        emit_measurement_handoff=True,
        emit_measure_handoff_event=True,
        emit_released=True,
    )

    bundle = {
        "request": request_bundle_obj,
        "response": response_bundle_obj,
        "recipe_sidecar": recipe_obj,
        "scene_manifest": manifest_obj,
        "validation_summary": summary_obj,
        "bridge_ready": bridge_ready,
        "runtime_artifacts": runtime_bundle,
    }
    bundle["bundle_hash"] = _stable_hash(
        {
            "request_id": request_obj["request_id"],
            "scene_id": request_scene_id,
            "bridge_ready": bridge_ready,
            "runtime_artifacts": runtime_bundle,
        }
    )
    return bundle


def _validate_prefixed_sha256(value: str, label: str, key: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a 'sha256:<hex>' string")
    _validate_sha256(value.split(":", 1)[1], label, key)


def _validate_string_list(value: Any, label: str, key: str) -> List[str]:
    if not isinstance(value, list):
        raise CompositionSchemaError(f"{label}: field '{key}' must be a list")
    normalized: List[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise CompositionSchemaError(f"{label}: field '{key}[{idx}]' must be a non-empty string")
        normalized.append(item.strip())
    return normalized


def _validate_output_descriptors(outputs: Any, label: str, key: str) -> List[Dict[str, Any]]:
    items = _require_list_field({key: outputs}, key, label)
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise CompositionSchemaError(f"{label}: field '{key}[{idx}]' must be a dict")
        _require_str(item, "kind", f"{label}.{key}[{idx}]")
        _require_str(item, "path", f"{label}.{key}[{idx}]")
    return items


def _validate_runtime_lock_scope(lock_scope: Any, label: str) -> Dict[str, Any]:
    scope = _require_dict(lock_scope, label)
    _require_str(scope, "scene_id", label)
    _validate_string_list(scope.get("reference_paths", []), label, "reference_paths")
    _validate_string_list(scope.get("artifact_paths", []), label, "artifact_paths")
    _require_bool(scope, "exclusive", label)
    return scope


def _validate_runtime_actor(actor: Any, label: str) -> Dict[str, Any]:
    actor_obj = _require_dict(actor, label)
    _require_str(actor_obj, "kind", label)
    _require_str(actor_obj, "id", label)
    return actor_obj


def _validate_claim_health_snapshot(health_snapshot: Any, label: str) -> Dict[str, Any]:
    snapshot = _require_dict(health_snapshot, label)
    _require_bool(snapshot, "paused", label)
    _require_bool(snapshot, "operations_health_ok", label)
    _require_bool(snapshot, "resource_budgets_ok", label)
    return {
        "paused": snapshot["paused"],
        "operations_health_ok": snapshot["operations_health_ok"],
        "resource_budgets_ok": snapshot["resource_budgets_ok"],
    }


def _enforce_claim_health_gates(runtime_request: Dict[str, Any], health_snapshot: Dict[str, Any]) -> None:
    health_gates = runtime_request["health_gates"]
    if health_gates.get("pause_required_false") and health_snapshot["paused"]:
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: claim rejected because the supplied health snapshot is paused"
        )
    if health_gates.get("operations_health_required") and not health_snapshot["operations_health_ok"]:
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: claim rejected because operations health is not ok"
        )
    if health_gates.get("resource_budgets_required") and not health_snapshot["resource_budgets_ok"]:
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: claim rejected because resource budgets are not ok"
        )


def _replay_claim_ledger(existing_events: List[Any], request_id: str) -> tuple[List[Dict[str, Any]], str, Dict[str, Dict[str, Any]]]:
    validated_events: List[Dict[str, Any]] = []
    current_status = "queued"
    active_claims_by_scene: Dict[str, Dict[str, Any]] = {}

    for idx, event in enumerate(existing_events):
        event_obj = deepcopy(validate_composition_lock_event(event))
        validated_events.append(event_obj)

        scene_id = event_obj["lock_scope"]["scene_id"]
        if event_obj["event_type"] == "claimed":
            active_claims_by_scene[scene_id] = {
                "request_id": event_obj["request_id"],
                "lock_token": event_obj["lock_token"],
                "event_id": event_obj["event_id"],
            }
        elif event_obj["event_type"] == "released":
            active_claims_by_scene.pop(scene_id, None)

        if event_obj.get("request_id") == request_id:
            current_status = event_obj["status_after"]

    return validated_events, current_status, active_claims_by_scene


def _validate_starter_compose_request(obj: Any) -> Dict[str, Any]:
    request = deepcopy(validate_composition_request(obj))
    _require_str(request, "created_at", "starter_compose_request")
    _validate_iso_utc(request["created_at"], "starter_compose_request", "created_at")
    return request


def normalize_starter_composition_request(
    starter_request: Any,
    output_root: str | None = None,
    task_plan_id: str | None = None,
    requester: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Map the starter request envelope into runtime request state.

    Preserved from the starter envelope: request_id, created_at, task_plan_id,
    request.scene_id, request.recipe_id, request.recipe_version,
    request.action, request.action_args, request.expected_outputs, and the
    determinism flags that drive deterministic runtime behavior.

    Introduced locally at the runtime boundary: requester metadata,
    aps_context, scene/output namespace, recipe/input hashes, runtime action
    list, expected_artifacts summary, lock_scope, health_gates, handoff, and
    queued status. Lock events, measurement handoff records, and lineage
    artifacts remain outside the minimal starter contract.
    """
    starter_candidate = _require_dict(starter_request, "starter_compose_request")
    for field_name in _STARTER_RUNTIME_FORBIDDEN_FIELDS:
        if field_name in starter_candidate:
            raise CompositionSchemaError(
                f"starter_compose_request: field '{field_name}' belongs to the runtime boundary"
            )
    starter = _validate_starter_compose_request(starter_candidate)

    output_root_abs = _resolve_runtime_output_root(output_root)
    request_id = starter["request_id"]
    request_body = starter["request"]
    scene_id = request_body["scene_id"]
    recipe_id = request_body["recipe_id"]
    recipe_version = request_body["recipe_version"]
    action = request_body["action"]
    action_args = deepcopy(request_body["action_args"])
    expected_outputs = deepcopy(request_body["expected_outputs"])
    output_paths = _runtime_output_paths(request_id, output_root_abs)

    request_hash = _stable_hash(starter)
    action_args_hash = _stable_hash(action_args)
    recipe_hash = "sha256:" + _stable_hash(
        {
            "recipe_id": recipe_id,
            "recipe_version": recipe_version,
            "action": action,
            "action_args": action_args,
        }
    )
    expected_kinds = [item["kind"] for item in expected_outputs]
    exported_assets = [item["path"] for item in expected_outputs if item.get("kind") == "export_asset"]

    requester_payload = requester or {
        "kind": "dry_run_cli",
        "requested_by": "compose-runtime-artifacts",
    }
    runtime_request = {
        "schema_version": RUNTIME_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "task_plan_id": str(task_plan_id or starter.get("task_plan_id") or "08"),
        "created_ts": starter["created_at"],
        "requester": requester_payload,
        "aps_context": {
            "ticket_id": f"aps_{scene_id}",
            "context_id": scene_id,
            "priority": "normal",
            "objective": f"{action} for {scene_id}",
            "reference_bundle_id": recipe_id,
            "approval_mode": "dry_run",
        },
        "scene": {
            "scene_id": scene_id,
            "environment_id": str(action_args.get("environment_id") or "environment_default"),
            "output_namespace": scene_id,
        },
        "recipe": {
            "recipe_id": recipe_id,
            "recipe_version": recipe_version,
            "recipe_hash": recipe_hash,
            "context_refs": [],
            "input_hashes": {
                "starter_request": request_hash,
                "action_args": action_args_hash,
            },
        },
        "actions": [
            {
                "ordinal": 1,
                "action": action,
                "args": action_args,
                "expects": expected_kinds,
            }
        ],
        "expected_artifacts": {
            "required_outputs": expected_outputs,
            "scene_manifest": "scene_manifest" in expected_kinds,
            "validation_summary": "validation_summary" in expected_kinds,
            "exported_assets": exported_assets,
            "measurement_handoff": True,
        },
        "determinism": {
            "deterministic_mode": bool(starter.get("determinism", {}).get("deterministic_mode")),
            "fixed_timestamp": str(starter.get("determinism", {}).get("fixed_timestamp") or starter["created_at"]),
            "hash_algorithm": "sha256",
            "retry_policy": "no_implicit_retry",
        },
        "lock_scope": {
            "scene_id": scene_id,
            "reference_paths": [],
            "artifact_paths": [
                output_paths["request_rel"],
                output_paths["recipe_rel"],
                output_paths["scene_manifest_rel"],
                output_paths["validation_summary_rel"],
            ],
            "exclusive": True,
        },
        "health_gates": {
            "operations_health_required": True,
            "resource_budgets_required": True,
            "pause_required_false": True,
        },
        "handoff": {
            "worker_kind": "blender_controller",
            "response_path": output_paths["response_rel"],
            "measurement_record_path": output_paths["measure_rel"],
            "bridge_mode": "asset_path_first",
        },
        "status": "queued",
    }
    validate_runtime_composition_request(runtime_request)
    return runtime_request


def _resolve_runtime_output_root(output_root: str | None) -> str:
    if isinstance(output_root, str) and output_root.strip():
        normalized = output_root.strip().replace("/", os.sep)
        if os.path.isabs(normalized):
            return normalized
        return safe_join(_REPO_ROOT, normalized)
    return safe_join(resolve_path("temporary"), "orchestrator")


def _display_repo_path(path_value: str) -> str:
    absolute = os.path.abspath(path_value)
    try:
        common = os.path.commonpath([_REPO_ROOT, absolute])
    except ValueError:
        common = None
    if common == _REPO_ROOT:
        return os.path.relpath(absolute, _REPO_ROOT).replace("\\", "/")
    return absolute.replace("\\", "/")


def _resolve_repo_or_abs_path(path_value: str) -> str:
    normalized = str(path_value).replace("/", os.sep)
    if os.path.isabs(normalized):
        return normalized
    return safe_join(_REPO_ROOT, normalized)


def _runtime_output_paths(request_id: str, output_root: str) -> Dict[str, str]:
    request_dir = safe_join(output_root, "composition_requests")
    request_path = safe_join(request_dir, f"{request_id}.json")
    response_path = safe_join(request_dir, f"{request_id}.response.json")
    recipe_path = safe_join(request_dir, f"{request_id}.recipe.json")
    scene_manifest_path = safe_join(request_dir, f"{request_id}.scene_manifest.json")
    validation_summary_path = safe_join(request_dir, f"{request_id}.validation_summary.json")
    measure_path = safe_join(request_dir, f"{request_id}.measure.json")
    lineage_path = safe_join(request_dir, f"{request_id}.lineage.json")
    semantic_record_path = safe_join(request_dir, f"{request_id}.semantic_record.json")
    ledger_path = safe_join(output_root, "composition_lock_events.jsonl")
    return {
        "request_abs": request_path,
        "request_rel": _display_repo_path(request_path),
        "response_abs": response_path,
        "response_rel": _display_repo_path(response_path),
        "recipe_abs": recipe_path,
        "recipe_rel": _display_repo_path(recipe_path),
        "scene_manifest_abs": scene_manifest_path,
        "scene_manifest_rel": _display_repo_path(scene_manifest_path),
        "validation_summary_abs": validation_summary_path,
        "validation_summary_rel": _display_repo_path(validation_summary_path),
        "measure_abs": measure_path,
        "measure_rel": _display_repo_path(measure_path),
        "lineage_abs": lineage_path,
        "lineage_rel": _display_repo_path(lineage_path),
        "semantic_abs": semantic_record_path,
        "semantic_rel": _display_repo_path(semantic_record_path),
        "ledger_abs": ledger_path,
        "ledger_rel": _display_repo_path(ledger_path),
    }


def validate_runtime_composition_request(obj: Any) -> Dict[str, Any]:
    request = _require_dict(obj, "runtime_composition_request")
    schema_version = _require_str(request, "schema_version", "runtime_composition_request")
    if schema_version != RUNTIME_REQUEST_SCHEMA_VERSION:
        raise CompositionSchemaError(
            f"runtime_composition_request: unsupported schema_version '{schema_version}'"
        )

    _require_str(request, "request_id", "runtime_composition_request")
    created_ts = _require_str(request, "created_ts", "runtime_composition_request")
    _validate_iso_utc(created_ts, "runtime_composition_request", "created_ts")

    task_plan_id = request.get("task_plan_id")
    if task_plan_id is not None and (not isinstance(task_plan_id, str) or not task_plan_id.strip()):
        raise CompositionSchemaError("runtime_composition_request: task_plan_id must be a non-empty string when present")

    requester = _require_dict_field(request, "requester", "runtime_composition_request")
    _require_str(requester, "kind", "runtime_composition_request.requester")
    _require_str(requester, "requested_by", "runtime_composition_request.requester")

    aps_context = _require_dict_field(request, "aps_context", "runtime_composition_request")
    _require_str(aps_context, "ticket_id", "runtime_composition_request.aps_context")
    _require_str(aps_context, "context_id", "runtime_composition_request.aps_context")
    _require_str(aps_context, "priority", "runtime_composition_request.aps_context")
    _require_str(aps_context, "objective", "runtime_composition_request.aps_context")
    _require_str(aps_context, "reference_bundle_id", "runtime_composition_request.aps_context")
    _require_str(aps_context, "approval_mode", "runtime_composition_request.aps_context")

    scene = _require_dict_field(request, "scene", "runtime_composition_request")
    scene_id = _require_str(scene, "scene_id", "runtime_composition_request.scene")
    _require_str(scene, "environment_id", "runtime_composition_request.scene")
    _require_str(scene, "output_namespace", "runtime_composition_request.scene")

    recipe = _require_dict_field(request, "recipe", "runtime_composition_request")
    _require_str(recipe, "recipe_id", "runtime_composition_request.recipe")
    _require_str(recipe, "recipe_version", "runtime_composition_request.recipe")
    recipe_hash = _require_str(recipe, "recipe_hash", "runtime_composition_request.recipe")
    _validate_prefixed_sha256(recipe_hash, "runtime_composition_request.recipe", "recipe_hash")
    _validate_string_list(recipe.get("context_refs", []), "runtime_composition_request.recipe", "context_refs")
    input_hashes = _require_dict_field(recipe, "input_hashes", "runtime_composition_request.recipe")
    for key, value in input_hashes.items():
        if not isinstance(key, str) or not key.strip():
            raise CompositionSchemaError("runtime_composition_request.recipe: input_hashes keys must be non-empty strings")
        if not isinstance(value, str):
            raise CompositionSchemaError("runtime_composition_request.recipe: input_hashes values must be strings")
        _validate_sha256(value, "runtime_composition_request.recipe.input_hashes", key)

    actions = _require_list_field(request, "actions", "runtime_composition_request")
    if not actions:
        raise CompositionSchemaError("runtime_composition_request: actions must not be empty")
    for idx, action_item in enumerate(actions):
        if not isinstance(action_item, dict):
            raise CompositionSchemaError(f"runtime_composition_request: actions[{idx}] must be a dict")
        ordinal = _require_int(action_item, "ordinal", f"runtime_composition_request.actions[{idx}]")
        if ordinal <= 0:
            raise CompositionSchemaError(f"runtime_composition_request.actions[{idx}]: ordinal must be >= 1")
        action_name = _require_str(action_item, "action", f"runtime_composition_request.actions[{idx}]")
        if action_name not in SUPPORTED_COMPOSITION_ACTIONS:
            raise CompositionSchemaError(
                f"runtime_composition_request.actions[{idx}]: unsupported action '{action_name}'"
            )
        _require_dict_field(action_item, "args", f"runtime_composition_request.actions[{idx}]")
        _validate_string_list(action_item.get("expects", []), f"runtime_composition_request.actions[{idx}]", "expects")

    expected_artifacts = _require_dict_field(request, "expected_artifacts", "runtime_composition_request")
    _validate_output_descriptors(
        expected_artifacts.get("required_outputs", []),
        "runtime_composition_request.expected_artifacts",
        "required_outputs",
    )
    _require_bool(expected_artifacts, "scene_manifest", "runtime_composition_request.expected_artifacts")
    _require_bool(expected_artifacts, "validation_summary", "runtime_composition_request.expected_artifacts")
    _validate_string_list(expected_artifacts.get("exported_assets", []), "runtime_composition_request.expected_artifacts", "exported_assets")
    _require_bool(expected_artifacts, "measurement_handoff", "runtime_composition_request.expected_artifacts")

    determinism = _require_dict_field(request, "determinism", "runtime_composition_request")
    _require_bool(determinism, "deterministic_mode", "runtime_composition_request.determinism")
    fixed_timestamp = _require_str(determinism, "fixed_timestamp", "runtime_composition_request.determinism")
    _validate_iso_utc(fixed_timestamp, "runtime_composition_request.determinism", "fixed_timestamp")
    _require_str(determinism, "hash_algorithm", "runtime_composition_request.determinism")
    _require_str(determinism, "retry_policy", "runtime_composition_request.determinism")

    lock_scope = _validate_runtime_lock_scope(request.get("lock_scope"), "runtime_composition_request.lock_scope")
    if lock_scope.get("scene_id") != scene_id:
        raise CompositionSchemaError("runtime_composition_request: lock_scope.scene_id must match scene.scene_id")

    health_gates = _require_dict_field(request, "health_gates", "runtime_composition_request")
    _require_bool(health_gates, "operations_health_required", "runtime_composition_request.health_gates")
    _require_bool(health_gates, "resource_budgets_required", "runtime_composition_request.health_gates")
    _require_bool(health_gates, "pause_required_false", "runtime_composition_request.health_gates")

    handoff = _require_dict_field(request, "handoff", "runtime_composition_request")
    _require_str(handoff, "worker_kind", "runtime_composition_request.handoff")
    _require_str(handoff, "response_path", "runtime_composition_request.handoff")
    _require_str(handoff, "measurement_record_path", "runtime_composition_request.handoff")
    _require_str(handoff, "bridge_mode", "runtime_composition_request.handoff")

    status = _require_str(request, "status", "runtime_composition_request")
    if status not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError(
            f"runtime_composition_request: unsupported status '{status}'"
        )
    return request


def validate_composition_lock_event(obj: Any) -> Dict[str, Any]:
    event = _require_dict(obj, "composition_lock_event")
    schema_version = _require_str(event, "schema_version", "composition_lock_event")
    if schema_version != RUNTIME_LOCK_EVENT_SCHEMA_VERSION:
        raise CompositionSchemaError(
            f"composition_lock_event: unsupported schema_version '{schema_version}'"
        )

    _require_str(event, "event_id", "composition_lock_event")
    ts = _require_str(event, "ts", "composition_lock_event")
    _validate_iso_utc(ts, "composition_lock_event", "ts")
    _require_str(event, "request_id", "composition_lock_event")

    task_plan_id = event.get("task_plan_id")
    if task_plan_id is not None and (not isinstance(task_plan_id, str) or not task_plan_id.strip()):
        raise CompositionSchemaError("composition_lock_event: task_plan_id must be a non-empty string when present")

    event_type = _require_str(event, "event_type", "composition_lock_event")
    if event_type not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError(
            f"composition_lock_event: unsupported event_type '{event_type}'"
        )

    _validate_runtime_actor(event.get("actor"), "composition_lock_event.actor")
    _validate_runtime_lock_scope(event.get("lock_scope"), "composition_lock_event.lock_scope")

    status_before = event.get("status_before")
    if status_before is not None and status_before not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError("composition_lock_event: status_before must be a valid status when present")

    status_after = _require_str(event, "status_after", "composition_lock_event")
    if status_after not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError(
            f"composition_lock_event: unsupported status_after '{status_after}'"
        )

    artifacts = event.get("artifacts")
    if artifacts is not None:
        if not isinstance(artifacts, dict):
            raise CompositionSchemaError("composition_lock_event: artifacts must be a dict when present")
        outputs = artifacts.get("outputs")
        if outputs is not None:
            _validate_output_descriptors(outputs, "composition_lock_event.artifacts", "outputs")
        for key in ("request_artifact", "response_path", "measurement_record_path"):
            value = artifacts.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise CompositionSchemaError(
                    f"composition_lock_event.artifacts: {key} must be a non-empty string when present"
                )

    if event_type == "claimed":
        _require_str(event, "lock_token", "composition_lock_event")
        health_snapshot = _require_dict_field(event, "health_snapshot", "composition_lock_event")
        _require_bool(health_snapshot, "paused", "composition_lock_event.health_snapshot")
        _require_bool(health_snapshot, "operations_health_ok", "composition_lock_event.health_snapshot")
        _require_bool(health_snapshot, "resource_budgets_ok", "composition_lock_event.health_snapshot")

    if event_type == "running":
        runtime_phase = _require_dict_field(event, "runtime_phase", "composition_lock_event")
        _require_str(runtime_phase, "step", "composition_lock_event.runtime_phase")
        _require_str(runtime_phase, "bridge_mode", "composition_lock_event.runtime_phase")
        _require_bool(runtime_phase, "deterministic_mode", "composition_lock_event.runtime_phase")

    if event_type == "failed":
        error = _require_dict_field(event, "error", "composition_lock_event")
        _require_str(error, "code", "composition_lock_event.error")
        _require_str(error, "message", "composition_lock_event.error")

    if event_type == "measure_handoff":
        handoff = _require_dict_field(event, "measure_handoff", "composition_lock_event")
        _require_str(handoff, "bridge_mode", "composition_lock_event.measure_handoff")
        _require_str(handoff, "measurement_record_path", "composition_lock_event.measure_handoff")
        placeholder_status = _require_str(
            handoff,
            "placeholder_status",
            "composition_lock_event.measure_handoff",
        )
        if placeholder_status not in SUPPORTED_MEASUREMENT_HANDOFF_STATUSES:
            raise CompositionSchemaError(
                f"composition_lock_event.measure_handoff: unsupported placeholder_status '{placeholder_status}'"
            )
        lineage_artifact_path = handoff.get("lineage_artifact_path")
        if lineage_artifact_path is not None and (not isinstance(lineage_artifact_path, str) or not lineage_artifact_path.strip()):
            raise CompositionSchemaError(
                "composition_lock_event.measure_handoff: lineage_artifact_path must be a non-empty string when present"
            )
        _validate_optional_prefixed_sha256(
            handoff.get("lineage_artifact_sha256"),
            "composition_lock_event.measure_handoff",
            "lineage_artifact_sha256",
        )

    if event_type == "lineage_materialized":
        materialization = _require_dict_field(event, "lineage_materialization", "composition_lock_event")
        _require_str(materialization, "lineage_artifact_path", "composition_lock_event.lineage_materialization")
        _validate_prefixed_sha256(
            _require_str(materialization, "lineage_artifact_sha256", "composition_lock_event.lineage_materialization"),
            "composition_lock_event.lineage_materialization",
            "lineage_artifact_sha256",
        )
        _require_str(materialization, "semantic_record_id", "composition_lock_event.lineage_materialization")
        _require_str(materialization, "semantic_record_path", "composition_lock_event.lineage_materialization")
        _validate_prefixed_sha256(
            _require_str(materialization, "semantic_record_sha256", "composition_lock_event.lineage_materialization"),
            "composition_lock_event.lineage_materialization",
            "semantic_record_sha256",
        )
        _validate_prefixed_sha256(
            _require_str(materialization, "relational_attachment_hash", "composition_lock_event.lineage_materialization"),
            "composition_lock_event.lineage_materialization",
            "relational_attachment_hash",
        )
        _require_nonnegative_int(materialization, "entity_count", "composition_lock_event.lineage_materialization")
        _require_nonnegative_int(materialization, "relation_count", "composition_lock_event.lineage_materialization")
        _require_nonnegative_int(materialization, "constraint_count", "composition_lock_event.lineage_materialization")

    if event_type == "released":
        _require_str(event, "release_reason", "composition_lock_event")

    return event


def validate_measurement_handoff_placeholder(obj: Any) -> Dict[str, Any]:
    handoff_obj = _require_dict(obj, "measurement_handoff_placeholder")
    schema_version = _require_str(handoff_obj, "schema_version", "measurement_handoff_placeholder")
    if schema_version != RUNTIME_MEASUREMENT_HANDOFF_SCHEMA_VERSION:
        raise CompositionSchemaError(
            f"measurement_handoff_placeholder: unsupported schema_version '{schema_version}'"
        )

    _require_str(handoff_obj, "request_id", "measurement_handoff_placeholder")
    _require_str(handoff_obj, "scene_id", "measurement_handoff_placeholder")
    created_ts = _require_str(handoff_obj, "created_ts", "measurement_handoff_placeholder")
    _validate_iso_utc(created_ts, "measurement_handoff_placeholder", "created_ts")
    _require_str(handoff_obj, "bridge_mode", "measurement_handoff_placeholder")
    status = _require_str(handoff_obj, "status", "measurement_handoff_placeholder")
    if status not in SUPPORTED_MEASUREMENT_HANDOFF_STATUSES:
        raise CompositionSchemaError(
            f"measurement_handoff_placeholder: unsupported status '{status}'"
        )

    artifacts = _require_dict_field(handoff_obj, "artifacts", "measurement_handoff_placeholder")
    expected_outputs = _validate_output_descriptors(
        artifacts.get("expected_outputs", []),
        "measurement_handoff_placeholder.artifacts",
        "expected_outputs",
    )
    exported_assets = _validate_string_list(
        artifacts.get("exported_assets", []),
        "measurement_handoff_placeholder.artifacts",
        "exported_assets",
    )

    metadata = _require_dict_field(handoff_obj, "metadata", "measurement_handoff_placeholder")
    _require_bool(metadata, "deterministic_mode", "measurement_handoff_placeholder.metadata")
    fixed_timestamp = _require_str(metadata, "fixed_timestamp", "measurement_handoff_placeholder.metadata")
    _validate_iso_utc(fixed_timestamp, "measurement_handoff_placeholder.metadata", "fixed_timestamp")
    _require_str(metadata, "response_path", "measurement_handoff_placeholder.metadata")
    if status == "completed_measurement":
        completed_ts = _require_str(metadata, "completed_ts", "measurement_handoff_placeholder.metadata")
        _validate_iso_utc(completed_ts, "measurement_handoff_placeholder.metadata", "completed_ts")
    if status == "skipped_measurement":
        _require_str(metadata, "skip_reason", "measurement_handoff_placeholder.metadata")
        _require_str(metadata, "error_code", "measurement_handoff_placeholder.metadata")

    if exported_assets and not any(item.get("kind") == "export_asset" for item in expected_outputs):
        raise CompositionSchemaError(
            "measurement_handoff_placeholder: exported_assets require an export_asset expected output"
        )
    return handoff_obj


def validate_runtime_lineage_artifact(obj: Any) -> Dict[str, Any]:
    lineage_obj = _require_dict(obj, "runtime_lineage_artifact")
    schema_version = _require_str(lineage_obj, "schema_version", "runtime_lineage_artifact")
    if schema_version != RUNTIME_LINEAGE_SCHEMA_VERSION:
        raise CompositionSchemaError(
            f"runtime_lineage_artifact: unsupported schema_version '{schema_version}'"
        )

    _require_str(lineage_obj, "request_id", "runtime_lineage_artifact")
    _require_str(lineage_obj, "scene_id", "runtime_lineage_artifact")
    created_ts = _require_str(lineage_obj, "created_ts", "runtime_lineage_artifact")
    _validate_iso_utc(created_ts, "runtime_lineage_artifact", "created_ts")
    status = _require_str(lineage_obj, "status", "runtime_lineage_artifact")
    if status not in SUPPORTED_RUNTIME_LINEAGE_STATUSES:
        raise CompositionSchemaError(
            f"runtime_lineage_artifact: unsupported status '{status}'"
        )

    task_plan_id = lineage_obj.get("task_plan_id")
    if task_plan_id is not None and (not isinstance(task_plan_id, str) or not task_plan_id.strip()):
        raise CompositionSchemaError(
            "runtime_lineage_artifact: task_plan_id must be a non-empty string when present"
        )

    runtime_artifacts = _require_dict_field(lineage_obj, "runtime_artifacts", "runtime_lineage_artifact")
    for key in ("request_artifact", "response_path", "measurement_record_path", "ledger_path", "lineage_artifact_path"):
        _require_str(runtime_artifacts, key, "runtime_lineage_artifact.runtime_artifacts")
    _validate_prefixed_sha256(
        _require_str(runtime_artifacts, "request_sha256", "runtime_lineage_artifact.runtime_artifacts"),
        "runtime_lineage_artifact.runtime_artifacts",
        "request_sha256",
    )
    _validate_optional_prefixed_sha256(
        runtime_artifacts.get("response_sha256"),
        "runtime_lineage_artifact.runtime_artifacts",
        "response_sha256",
    )
    _validate_prefixed_sha256(
        _require_str(runtime_artifacts, "measurement_record_sha256", "runtime_lineage_artifact.runtime_artifacts"),
        "runtime_lineage_artifact.runtime_artifacts",
        "measurement_record_sha256",
    )
    handoff_status = _require_str(
        runtime_artifacts,
        "measurement_handoff_status",
        "runtime_lineage_artifact.runtime_artifacts",
    )
    if handoff_status not in SUPPORTED_MEASUREMENT_HANDOFF_STATUSES:
        raise CompositionSchemaError(
            "runtime_lineage_artifact.runtime_artifacts: measurement_handoff_status must be a supported status"
        )
    measure_handoff_event_id = runtime_artifacts.get("measure_handoff_event_id")
    if measure_handoff_event_id is not None and (not isinstance(measure_handoff_event_id, str) or not measure_handoff_event_id.strip()):
        raise CompositionSchemaError(
            "runtime_lineage_artifact.runtime_artifacts: measure_handoff_event_id must be a non-empty string when present"
        )
    composition_artifacts = runtime_artifacts.get("composition_artifacts")
    if composition_artifacts is not None:
        if not isinstance(composition_artifacts, dict):
            raise CompositionSchemaError(
                "runtime_lineage_artifact.runtime_artifacts: composition_artifacts must be a dict when present"
            )
        for key in ("recipe_sidecar", "scene_manifest", "validation_summary"):
            item = composition_artifacts.get(key)
            if not isinstance(item, dict):
                raise CompositionSchemaError(
                    f"runtime_lineage_artifact.runtime_artifacts.composition_artifacts: {key} must be a dict"
                )
            _require_str(item, "path", f"runtime_lineage_artifact.runtime_artifacts.composition_artifacts.{key}")
            _validate_prefixed_sha256(
                _require_str(
                    item,
                    "sha256",
                    f"runtime_lineage_artifact.runtime_artifacts.composition_artifacts.{key}",
                ),
                f"runtime_lineage_artifact.runtime_artifacts.composition_artifacts.{key}",
                "sha256",
            )

    semantic_record = _require_dict_field(lineage_obj, "semantic_record", "runtime_lineage_artifact")
    _require_str(semantic_record, "semantic_record_id", "runtime_lineage_artifact.semantic_record")
    _require_str(semantic_record, "semantic_record_path", "runtime_lineage_artifact.semantic_record")
    _validate_prefixed_sha256(
        _require_str(semantic_record, "semantic_record_sha256", "runtime_lineage_artifact.semantic_record"),
        "runtime_lineage_artifact.semantic_record",
        "semantic_record_sha256",
    )
    materialization_status = _require_str(
        semantic_record,
        "materialization_status",
        "runtime_lineage_artifact.semantic_record",
    )
    if materialization_status not in SUPPORTED_SEMANTIC_RECORD_TARGET_STATUSES:
        raise CompositionSchemaError(
            "runtime_lineage_artifact.semantic_record: unsupported materialization_status"
        )

    attachment = _require_dict_field(lineage_obj, "scene_summary_attachment", "runtime_lineage_artifact")
    bridge_source = _require_str(attachment, "bridge_source", "runtime_lineage_artifact.scene_summary_attachment")
    if bridge_source != "3d_scene_summary":
        raise CompositionSchemaError(
            f"runtime_lineage_artifact.scene_summary_attachment: unsupported bridge_source '{bridge_source}'"
        )
    _validate_prefixed_sha256(
        _require_str(attachment, "bridge_payload_hash", "runtime_lineage_artifact.scene_summary_attachment"),
        "runtime_lineage_artifact.scene_summary_attachment",
        "bridge_payload_hash",
    )
    _validate_prefixed_sha256(
        _require_str(attachment, "relational_attachment_hash", "runtime_lineage_artifact.scene_summary_attachment"),
        "runtime_lineage_artifact.scene_summary_attachment",
        "relational_attachment_hash",
    )
    _require_nonnegative_int(attachment, "entity_count", "runtime_lineage_artifact.scene_summary_attachment")
    _require_nonnegative_int(attachment, "relation_count", "runtime_lineage_artifact.scene_summary_attachment")
    _require_nonnegative_int(attachment, "constraint_count", "runtime_lineage_artifact.scene_summary_attachment")
    attachment_status = _require_str(
        attachment,
        "attachment_status",
        "runtime_lineage_artifact.scene_summary_attachment",
    )
    if attachment_status not in SUPPORTED_RUNTIME_LINEAGE_STATUSES:
        raise CompositionSchemaError(
            "runtime_lineage_artifact.scene_summary_attachment: unsupported attachment_status"
        )
    _validate_string_list(
        attachment.get("expected_output_kinds", []),
        "runtime_lineage_artifact.scene_summary_attachment",
        "expected_output_kinds",
    )
    return lineage_obj


def build_measurement_handoff_placeholder(
    runtime_request: Any,
    response: Any | None = None,
    status: str = "pending_measurement",
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    response_obj = None if response is None else deepcopy(validate_composition_response(response))
    if status not in SUPPORTED_MEASUREMENT_HANDOFF_STATUSES:
        raise CompositionSchemaError(f"measurement_handoff_placeholder: unsupported status '{status}'")

    expected_outputs = deepcopy(request_obj["expected_artifacts"]["required_outputs"])
    exported_assets = [item["path"] for item in expected_outputs if item.get("kind") == "export_asset"]
    handoff = {
        "schema_version": RUNTIME_MEASUREMENT_HANDOFF_SCHEMA_VERSION,
        "request_id": request_obj["request_id"],
        "scene_id": request_obj["scene"]["scene_id"],
        "created_ts": request_obj["created_ts"],
        "bridge_mode": request_obj["handoff"]["bridge_mode"],
        "status": status,
        "artifacts": {
            "expected_outputs": expected_outputs,
            "exported_assets": exported_assets,
        },
        "metadata": {
            "deterministic_mode": bool(request_obj["determinism"]["deterministic_mode"]),
            "fixed_timestamp": request_obj["determinism"]["fixed_timestamp"],
            "response_path": request_obj["handoff"]["response_path"],
        },
    }
    if response_obj is not None:
        handoff["metadata"]["response_status"] = response_obj["status"]
        handoff["metadata"]["response_artifact_count"] = len(response_obj.get("artifacts") or [])
    if status == "completed_measurement":
        handoff["metadata"]["completed_ts"] = request_obj["determinism"]["fixed_timestamp"]
    if status == "skipped_measurement":
        if response_obj is None or response_obj.get("status") not in ("error", "rejected"):
            raise CompositionSchemaError(
                "measurement_handoff_placeholder: skipped_measurement requires an error or rejected response"
            )
        error_obj = response_obj.get("error") if isinstance(response_obj.get("error"), dict) else {}
        handoff["metadata"]["skip_reason"] = "terminal_failure"
        handoff["metadata"]["error_code"] = str(error_obj.get("code") or "internal_error")

    validate_measurement_handoff_placeholder(handoff)
    return handoff


def build_runtime_recipe_sidecar(runtime_request: Any) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    action_row = deepcopy(request_obj["actions"][0])
    export_info = action_row.get("args", {}).get("export") if isinstance(action_row.get("args"), dict) else {}
    recipe_obj = {
        "recipe_id": request_obj["recipe"]["recipe_id"],
        "recipe_version": request_obj["recipe"]["recipe_version"],
        "ordered_context_references": deepcopy(request_obj["recipe"].get("context_refs", [])),
        "export_settings": {
            "format": str((export_info or {}).get("format") or "ply"),
            "path": str((export_info or {}).get("path") or ""),
        },
        "steps": [
            {
                "action": action_row["action"],
                "args": deepcopy(action_row["args"]),
            }
        ],
    }
    recipe_obj["recipe_hash"] = compute_recipe_hash(recipe_obj)
    validate_recipe_sidecar(recipe_obj)
    return recipe_obj


def build_runtime_scene_manifest(runtime_request: Any, recipe_sidecar: Any) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    recipe_obj = deepcopy(validate_recipe_sidecar(recipe_sidecar))
    scene_id = request_obj["scene"]["scene_id"]
    camera_id = f"{scene_id}::camera::main"
    light_id = f"{scene_id}::light::key"
    scene_node_id = f"{scene_id}::scene"
    exports = [
        {
            "format": str(item.get("path", "").rsplit(".", 1)[-1] or "ply") if "." in str(item.get("path", "")) else "ply",
            "path": str(item["path"]),
        }
        for item in request_obj["expected_artifacts"]["required_outputs"]
        if item.get("kind") == "export_asset"
    ]
    manifest_obj = {
        "scene_id": scene_id,
        "scene_name": scene_id,
        "recipe_id": recipe_obj["recipe_id"],
        "recipe_version": recipe_obj["recipe_version"],
        "recipe_hash": recipe_obj["recipe_hash"],
        "object_inventory": [
            {"id": scene_node_id, "type": "scene"},
            {"id": camera_id, "type": "camera"},
            {"id": light_id, "type": "light"},
        ],
        "exports": exports,
        "active_camera": camera_id,
        "active_lights": [light_id],
    }
    manifest_obj["scene_hash"] = compute_scene_manifest_hash(manifest_obj)
    validate_scene_manifest(manifest_obj)
    return manifest_obj


def build_runtime_scene_manifest_from_inventory(
    runtime_request: Any,
    recipe_sidecar: Any,
    *,
    object_inventory: List[Dict[str, Any]],
    active_camera: str,
    active_lights: List[str],
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    recipe_obj = deepcopy(validate_recipe_sidecar(recipe_sidecar))
    actions = request_obj.get("actions") if isinstance(request_obj.get("actions"), list) else []
    first_action = actions[0] if actions and isinstance(actions[0], dict) else {}
    action_args = first_action.get("args") if isinstance(first_action.get("args"), dict) else {}
    object_controls = _validate_object_activity_controls(
        action_args,
        label="runtime_composition_request.request",
        required=False,
    )
    controls_by_hint = {
        str(item.get("object_id_hint") or ""): deepcopy(item)
        for item in object_controls
        if isinstance(item, dict) and str(item.get("object_id_hint") or "")
    }
    remaining_controls = [deepcopy(item) for item in object_controls]
    normalized_inventory = []
    for idx, item in enumerate(object_inventory):
        if not isinstance(item, dict):
            raise CompositionSchemaError(f"scene_manifest_inventory: object_inventory[{idx}] must be a dict")
        entry = {
            "id": _require_str(item, "id", f"scene_manifest_inventory.object_inventory[{idx}]"),
            "type": _require_str(item, "type", f"scene_manifest_inventory.object_inventory[{idx}]"),
        }
        if entry["type"] == "mesh" and "::object::" in entry["id"] and object_controls:
            hint = entry["id"].rsplit("::object::", 1)[-1]
            control_ref = controls_by_hint.get(hint)
            if control_ref is None and remaining_controls:
                control_ref = remaining_controls.pop(0)
            elif control_ref is not None:
                remaining_controls = [
                    row
                    for row in remaining_controls
                    if str(row.get("object_id_hint") or "") != hint
                ]
            if isinstance(control_ref, dict):
                entry["ai_brain_control"] = control_ref
        normalized_inventory.append(entry)
    manifest_obj = {
        "scene_id": request_obj["scene"]["scene_id"],
        "scene_name": request_obj["scene"]["scene_id"],
        "recipe_id": recipe_obj["recipe_id"],
        "recipe_version": recipe_obj["recipe_version"],
        "recipe_hash": recipe_obj["recipe_hash"],
        "object_inventory": normalized_inventory,
        "exports": [
            {
                "format": str(item.get("path", "").rsplit(".", 1)[-1] or "ply") if "." in str(item.get("path", "")) else "ply",
                "path": str(item["path"]),
            }
            for item in request_obj["expected_artifacts"]["required_outputs"]
            if item.get("kind") == "export_asset"
        ],
        "active_camera": str(active_camera),
        "active_lights": [str(value) for value in active_lights],
    }
    manifest_obj["scene_hash"] = compute_scene_manifest_hash(manifest_obj)
    validate_scene_manifest(manifest_obj)
    return manifest_obj


def build_runtime_validation_summary(
    runtime_request: Any,
    recipe_sidecar: Any,
    scene_manifest: Any,
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    recipe_obj = deepcopy(validate_recipe_sidecar(recipe_sidecar))
    manifest_obj = deepcopy(validate_scene_manifest(scene_manifest))
    checks = [
        {
            "name": "scene_manifest_ready",
            "status": "pass",
            "expected": manifest_obj["scene_id"],
            "actual": manifest_obj["scene_id"],
        },
        {
            "name": "recipe_hash_matches_request",
            "status": "pass",
            "expected": request_obj["recipe"]["recipe_hash"],
            "actual": recipe_obj["recipe_hash"],
        },
        {
            "name": "export_targets_declared",
            "status": "pass",
            "expected": len(manifest_obj["exports"]),
            "actual": len(manifest_obj["exports"]),
        },
    ]
    summary_obj = {
        "summary_id": "vsum_" + _stable_hash({"request_id": request_obj["request_id"], "scene_id": manifest_obj["scene_id"]})[:12],
        "request_id": request_obj["request_id"],
        "scene_id": manifest_obj["scene_id"],
        "recipe_hash": recipe_obj["recipe_hash"],
        "status": "pass",
        "checks": checks,
        "warnings": [],
    }
    summary_obj["summary_hash"] = compute_validation_summary_hash(summary_obj)
    validate_validation_summary(summary_obj)
    return summary_obj


def build_runtime_validation_summary_from_checks(
    runtime_request: Any,
    recipe_sidecar: Any,
    scene_manifest: Any,
    *,
    checks: List[Dict[str, Any]],
    warnings: List[str] | None = None,
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    recipe_obj = deepcopy(validate_recipe_sidecar(recipe_sidecar))
    manifest_obj = deepcopy(validate_scene_manifest(scene_manifest))
    normalized_checks = []
    for idx, check in enumerate(checks):
        if not isinstance(check, dict):
            raise CompositionSchemaError(f"validation_summary_checks: checks[{idx}] must be a dict")
        name = _require_str(check, "name", f"validation_summary_checks.checks[{idx}]")
        status = _require_str(check, "status", f"validation_summary_checks.checks[{idx}]")
        if status not in _CHECK_STATUSES:
            raise CompositionSchemaError(
                f"validation_summary_checks: checks[{idx}] has unsupported status '{status}'"
            )
        normalized_checks.append(
            {
                "name": name,
                "status": status,
                "expected": check.get("expected"),
                "actual": check.get("actual"),
            }
        )
    normalized_warnings = [str(item) for item in (warnings or [])]
    if any(check["status"] == "fail" for check in normalized_checks):
        summary_status = "fail"
    elif any(check["status"] == "warn" for check in normalized_checks) or normalized_warnings:
        summary_status = "warn"
    else:
        summary_status = "pass"
    summary_obj = {
        "summary_id": "vsum_" + _stable_hash({"request_id": request_obj["request_id"], "scene_id": manifest_obj["scene_id"]})[:12],
        "request_id": request_obj["request_id"],
        "scene_id": manifest_obj["scene_id"],
        "recipe_hash": recipe_obj["recipe_hash"],
        "status": summary_status,
        "checks": normalized_checks,
        "warnings": normalized_warnings,
    }
    summary_obj["summary_hash"] = compute_validation_summary_hash(summary_obj)
    validate_validation_summary(summary_obj)
    return summary_obj


def build_runtime_lineage_artifact(
    runtime_request: Any,
    measurement_handoff: Any,
    response: Any | None = None,
    measure_handoff_event: Any | None = None,
    output_root: str | None = None,
    composition_artifacts: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    handoff_obj = deepcopy(validate_measurement_handoff_placeholder(measurement_handoff))
    response_obj = None if response is None else deepcopy(validate_composition_response(response))
    event_obj = None if measure_handoff_event is None else deepcopy(validate_composition_lock_event(measure_handoff_event))

    output_root_abs = _resolve_runtime_output_root(output_root)
    output_paths = _runtime_output_paths(request_obj["request_id"], output_root_abs)
    composition_artifact_refs = None
    if composition_artifacts is not None:
        recipe_obj = deepcopy(validate_recipe_sidecar(composition_artifacts.get("recipe_sidecar")))
        manifest_obj = deepcopy(validate_scene_manifest(composition_artifacts.get("scene_manifest")))
        summary_obj = deepcopy(validate_validation_summary(composition_artifacts.get("validation_summary")))
        composition_artifact_refs = {
            "recipe_sidecar": {
                "path": output_paths["recipe_rel"],
                "sha256": _prefixed_stable_hash(recipe_obj),
            },
            "scene_manifest": {
                "path": output_paths["scene_manifest_rel"],
                "sha256": _prefixed_stable_hash(manifest_obj),
            },
            "validation_summary": {
                "path": output_paths["validation_summary_rel"],
                "sha256": _prefixed_stable_hash(summary_obj),
            },
        }
    expected_outputs = deepcopy(request_obj["expected_artifacts"]["required_outputs"])
    expected_output_kinds = [
        item.get("kind")
        for item in expected_outputs
        if isinstance(item, dict) and isinstance(item.get("kind"), str) and item.get("kind")
    ]
    semantic_record_id = "semrec_" + _stable_hash(
        {
            "request_id": request_obj["request_id"],
            "scene_id": request_obj["scene"]["scene_id"],
            "bridge_source": "3d_scene_summary",
        }
    )[:16]
    semantic_record_seed = {
        "semantic_record_id": semantic_record_id,
        "request_id": request_obj["request_id"],
        "scene_id": request_obj["scene"]["scene_id"],
        "semantic_record_path": output_paths["semantic_rel"],
        "bridge_source": "3d_scene_summary",
    }
    bridge_payload_seed = {
        "request_id": request_obj["request_id"],
        "scene_id": request_obj["scene"]["scene_id"],
        "recipe": deepcopy(request_obj["recipe"]),
        "expected_outputs": expected_outputs,
        "exported_assets": deepcopy(handoff_obj["artifacts"]["exported_assets"]),
        "measurement_record_path": request_obj["handoff"]["measurement_record_path"],
        "response_path": request_obj["handoff"]["response_path"],
        "bridge_mode": request_obj["handoff"]["bridge_mode"],
    }
    if composition_artifact_refs is not None:
        bridge_payload_seed["composition_artifacts"] = deepcopy(composition_artifact_refs)
    bridge_payload_hash = _prefixed_stable_hash(bridge_payload_seed)
    attachment_seed = {
        "request_id": request_obj["request_id"],
        "semantic_record_id": semantic_record_id,
        "bridge_source": "3d_scene_summary",
        "bridge_payload_hash": bridge_payload_hash,
        "entity_count": 0,
        "relation_count": 0,
        "constraint_count": 0,
        "attachment_status": "pending_scene_summary_attachment",
    }
    lineage_obj = {
        "schema_version": RUNTIME_LINEAGE_SCHEMA_VERSION,
        "request_id": request_obj["request_id"],
        "task_plan_id": request_obj.get("task_plan_id"),
        "scene_id": request_obj["scene"]["scene_id"],
        "created_ts": request_obj["created_ts"],
        "status": "pending_scene_summary_attachment",
        "runtime_artifacts": {
            "request_artifact": output_paths["request_rel"],
            "request_sha256": _prefixed_stable_hash(request_obj),
            "response_path": request_obj["handoff"]["response_path"],
            "response_sha256": _prefixed_stable_hash(response_obj) if response_obj is not None else None,
            "measurement_record_path": request_obj["handoff"]["measurement_record_path"],
            "measurement_record_sha256": _prefixed_stable_hash(handoff_obj),
            "measurement_handoff_status": handoff_obj["status"],
            "measure_handoff_event_id": None if event_obj is None else event_obj["event_id"],
            "ledger_path": output_paths["ledger_rel"],
            "lineage_artifact_path": output_paths["lineage_rel"],
        },
        "semantic_record": {
            "semantic_record_id": semantic_record_id,
            "semantic_record_path": output_paths["semantic_rel"],
            "semantic_record_sha256": _prefixed_stable_hash(semantic_record_seed),
            "materialization_status": "pending_materialization",
        },
        "scene_summary_attachment": {
            "bridge_source": "3d_scene_summary",
            "bridge_payload_hash": bridge_payload_hash,
            "relational_attachment_hash": _prefixed_stable_hash(attachment_seed),
            "entity_count": 0,
            "relation_count": 0,
            "constraint_count": 0,
            "attachment_status": "pending_scene_summary_attachment",
            "expected_output_kinds": expected_output_kinds,
        },
    }
    if composition_artifact_refs is not None:
        lineage_obj["runtime_artifacts"]["composition_artifacts"] = composition_artifact_refs
    validate_runtime_lineage_artifact(lineage_obj)
    return lineage_obj


def materialize_runtime_lineage_artifact(
    lineage_artifact: Any,
    semantic_record: Any,
    bridge_payload: Any,
    *,
    semantic_record_path: str,
) -> Dict[str, Any]:
    lineage_obj = deepcopy(validate_runtime_lineage_artifact(lineage_artifact))
    record_obj = _require_dict(semantic_record, "semantic_record")
    bridge_obj = _require_dict(bridge_payload, "scene_summary_bridge_payload")

    if bridge_obj.get("source") != "3d_scene_summary":
        raise CompositionSchemaError(
            "scene_summary_bridge_payload: source must be '3d_scene_summary'"
        )
    if not isinstance(semantic_record_path, str) or not semantic_record_path.strip():
        raise CompositionSchemaError(
            "semantic_record: semantic_record_path must be a non-empty string"
        )

    record_id = _require_str(record_obj, "id", "semantic_record")
    request_id = lineage_obj["request_id"]

    extras = bridge_obj.get("extras") if isinstance(bridge_obj.get("extras"), dict) else {}
    validation = extras.get("validation") if isinstance(extras.get("validation"), dict) else {}
    bridge_request_id = validation.get("request_id")
    if bridge_request_id is not None and str(bridge_request_id).strip() and str(bridge_request_id) != request_id:
        raise CompositionSchemaError(
            "scene_summary_bridge_payload: request_id does not match runtime lineage artifact"
        )

    semantic_record_rel = _display_repo_path(semantic_record_path)
    semantic_record_sha256 = _prefixed_stable_hash(record_obj)
    bridge_payload_hash = _prefixed_stable_hash(bridge_obj)

    entity_rows = bridge_obj.get("entities") if isinstance(bridge_obj.get("entities"), list) else []
    relation_rows = bridge_obj.get("relations") if isinstance(bridge_obj.get("relations"), list) else []
    constraint_rows = bridge_obj.get("constraints") if isinstance(bridge_obj.get("constraints"), list) else []

    attachment_seed = {
        "request_id": request_id,
        "semantic_record_id": record_id,
        "semantic_record_path": semantic_record_rel,
        "bridge_source": "3d_scene_summary",
        "bridge_payload_hash": bridge_payload_hash,
        "entities": deepcopy(entity_rows),
        "relations": deepcopy(relation_rows),
        "constraints": deepcopy(constraint_rows),
    }

    lineage_obj["status"] = "materialized_scene_summary_attachment"
    lineage_obj["semantic_record"] = {
        "semantic_record_id": record_id,
        "semantic_record_path": semantic_record_rel,
        "semantic_record_sha256": semantic_record_sha256,
        "materialization_status": "materialized",
    }
    lineage_obj["scene_summary_attachment"] = {
        "bridge_source": "3d_scene_summary",
        "bridge_payload_hash": bridge_payload_hash,
        "relational_attachment_hash": _prefixed_stable_hash(attachment_seed),
        "entity_count": len(entity_rows),
        "relation_count": len(relation_rows),
        "constraint_count": len(constraint_rows),
        "attachment_status": "materialized_scene_summary_attachment",
        "expected_output_kinds": deepcopy(
            lineage_obj.get("scene_summary_attachment", {}).get("expected_output_kinds", [])
        ),
    }

    validate_runtime_lineage_artifact(lineage_obj)
    return lineage_obj


def materialize_runtime_lineage_for_semantic_record(
    semantic_record_path: str,
    output_root: str | None = None,
) -> Dict[str, Any]:
    if not isinstance(semantic_record_path, str) or not semantic_record_path.strip():
        raise CompositionSchemaError(
            "materialize_runtime_lineage_for_semantic_record: semantic_record_path must be a non-empty string"
        )

    try:
        with open(semantic_record_path, "r", encoding="utf-8") as handle:
            record_obj = json.load(handle)
    except Exception:
        return {
            "record_path": semantic_record_path,
            "status": "error",
            "reason": "failed_to_load_semantic_record",
        }

    if not isinstance(record_obj, dict):
        return {
            "record_path": semantic_record_path,
            "status": "error",
            "reason": "semantic_record_not_object",
        }

    bridge_outputs = []
    relational_state = record_obj.get("relational_state")
    if isinstance(relational_state, dict) and isinstance(relational_state.get("bridge_outputs"), list):
        bridge_outputs = relational_state.get("bridge_outputs")

    bridge_payload = None
    request_id = None
    for payload in bridge_outputs:
        if not isinstance(payload, dict) or payload.get("source") != "3d_scene_summary":
            continue
        extras = payload.get("extras") if isinstance(payload.get("extras"), dict) else {}
        validation = extras.get("validation") if isinstance(extras.get("validation"), dict) else {}
        candidate_request_id = validation.get("request_id")
        if isinstance(candidate_request_id, str) and candidate_request_id.strip():
            bridge_payload = payload
            request_id = candidate_request_id.strip()
            break

    if bridge_payload is None or request_id is None:
        artifacts = record_obj.get("artifacts") if isinstance(record_obj.get("artifacts"), dict) else {}
        validation_summary = None
        if isinstance(artifacts.get("composition_validation_summary"), dict):
            validation_summary = artifacts.get("composition_validation_summary")
        elif isinstance(artifacts.get("validation_summary"), dict):
            validation_summary = artifacts.get("validation_summary")
        candidate_request_id = None if not isinstance(validation_summary, dict) else validation_summary.get("request_id")
        if bridge_payload is None:
            return {
                "record_path": semantic_record_path,
                "status": "skipped",
                "reason": "no_scene_summary_bridge_output",
            }
        if not isinstance(candidate_request_id, str) or not candidate_request_id.strip():
            return {
                "record_path": semantic_record_path,
                "status": "skipped",
                "reason": "no_runtime_request_id",
            }
        request_id = candidate_request_id.strip()

    output_root_abs = _resolve_runtime_output_root(output_root)
    output_paths = _runtime_output_paths(request_id, output_root_abs)
    if not os.path.exists(output_paths["lineage_abs"]):
        return {
            "record_path": semantic_record_path,
            "request_id": request_id,
            "status": "skipped",
            "reason": "lineage_artifact_missing",
            "lineage_path": output_paths["lineage_rel"],
        }

    try:
        with open(output_paths["lineage_abs"], "r", encoding="utf-8") as handle:
            lineage_obj = json.load(handle)
    except Exception:
        return {
            "record_path": semantic_record_path,
            "request_id": request_id,
            "status": "error",
            "reason": "failed_to_load_lineage_artifact",
            "lineage_path": output_paths["lineage_rel"],
        }

    ledger_events = []
    if os.path.exists(output_paths["ledger_abs"]):
        with open(output_paths["ledger_abs"], "r", encoding="utf-8") as handle:
            ledger_events = [json.loads(line) for line in handle if line.strip()]

    materialized = (
        lineage_obj
        if str(lineage_obj.get("status") or "") == "materialized_scene_summary_attachment"
        else materialize_runtime_lineage_artifact(
            lineage_obj,
            record_obj,
            bridge_payload,
            semantic_record_path=semantic_record_path,
        )
    )

    with open(output_paths["lineage_abs"], "w", encoding="utf-8") as handle:
        json.dump(materialized, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    lineage_sha256 = _prefixed_stable_hash(materialized)
    existing_materialization = next(
        (
            event
            for event in ledger_events
            if isinstance(event, dict)
            and event.get("event_type") == "lineage_materialized"
            and isinstance(event.get("lineage_materialization"), dict)
            and event["lineage_materialization"].get("lineage_artifact_sha256") == lineage_sha256
        ),
        None,
    )

    appended_event_id = None
    if existing_materialization is None:
        request_artifact_path = _resolve_repo_or_abs_path(materialized["runtime_artifacts"]["request_artifact"])
        with open(request_artifact_path, "r", encoding="utf-8") as handle:
            runtime_request = json.load(handle)

        current_status = None
        if ledger_events:
            last_event = ledger_events[-1]
            if isinstance(last_event, dict):
                current_status = last_event.get("status_after")

        materialization_event = build_composition_lock_event(
            runtime_request,
            "lineage_materialized",
            lineage_artifact_path=materialized["runtime_artifacts"]["lineage_artifact_path"],
            lineage_artifact_sha256=lineage_sha256,
            semantic_record_id=materialized["semantic_record"]["semantic_record_id"],
            semantic_record_path=materialized["semantic_record"]["semantic_record_path"],
            semantic_record_sha256=materialized["semantic_record"]["semantic_record_sha256"],
            relational_attachment_hash=materialized["scene_summary_attachment"]["relational_attachment_hash"],
            entity_count=materialized["scene_summary_attachment"]["entity_count"],
            relation_count=materialized["scene_summary_attachment"]["relation_count"],
            constraint_count=materialized["scene_summary_attachment"]["constraint_count"],
            status_before_override=current_status,
        )
        with open(output_paths["ledger_abs"], "a", encoding="utf-8") as handle:
            handle.write(json.dumps(materialization_event, ensure_ascii=False) + "\n")
        appended_event_id = materialization_event["event_id"]
    else:
        appended_event_id = existing_materialization.get("event_id")

    return {
        "record_path": semantic_record_path,
        "request_id": request_id,
        "status": "completed",
        "lineage_path": output_paths["lineage_rel"],
        "lineage_event_id": appended_event_id,
        "semantic_record_id": materialized["semantic_record"]["semantic_record_id"],
        "entity_count": materialized["scene_summary_attachment"]["entity_count"],
        "relation_count": materialized["scene_summary_attachment"]["relation_count"],
        "constraint_count": materialized["scene_summary_attachment"]["constraint_count"],
    }


def build_runtime_composition_request_artifact(
    starter_request: Any,
    output_root: str | None = None,
    task_plan_id: str | None = None,
    requester: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return normalize_starter_composition_request(
        starter_request,
        output_root=output_root,
        task_plan_id=task_plan_id,
        requester=requester,
    )


def build_composition_lock_event(
    runtime_request: Any,
    event_type: str,
    actor: Dict[str, Any] | None = None,
    health_snapshot: Dict[str, Any] | None = None,
    release_reason: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    measure_handoff_status: str | None = None,
    lineage_artifact_path: str | None = None,
    lineage_artifact_sha256: str | None = None,
    semantic_record_id: str | None = None,
    semantic_record_path: str | None = None,
    semantic_record_sha256: str | None = None,
    relational_attachment_hash: str | None = None,
    entity_count: int | None = None,
    relation_count: int | None = None,
    constraint_count: int | None = None,
    status_before_override: str | None = None,
) -> Dict[str, Any]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    if event_type not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError(f"composition_lock_event: unsupported event_type '{event_type}'")

    actor_payload = actor or {"kind": "dry_run_writer", "id": "module_composition_contracts"}
    status_before_map = {
        "queued": None,
        "claimed": "queued",
        "running": "claimed",
        "validated": "claimed",
        "measure_handoff": "validated",
        "failed": "claimed",
        "released": "validated",
        "lineage_materialized": "measure_handoff",
    }
    status_before = status_before_override if status_before_override is not None else status_before_map.get(event_type)
    if status_before is not None and status_before not in SUPPORTED_RUNTIME_ARTIFACT_STATUSES:
        raise CompositionSchemaError(
            f"composition_lock_event: unsupported status_before '{status_before}'"
        )
    event_id = "clev_" + _stable_hash(
        {
            "request_id": request_obj["request_id"],
            "event_type": event_type,
            "status_before": status_before,
        }
    )[:16]
    event = {
        "schema_version": RUNTIME_LOCK_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "ts": request_obj["created_ts"],
        "request_id": request_obj["request_id"],
        "task_plan_id": request_obj.get("task_plan_id"),
        "event_type": event_type,
        "actor": actor_payload,
        "lock_scope": deepcopy(request_obj["lock_scope"]),
        "status_before": status_before,
        "status_after": event_type,
        "artifacts": {
            "request_artifact": request_obj["lock_scope"]["artifact_paths"][0],
            "response_path": request_obj["handoff"]["response_path"],
            "measurement_record_path": request_obj["handoff"]["measurement_record_path"],
            "outputs": deepcopy(request_obj["expected_artifacts"]["required_outputs"]),
        },
    }
    if event_type == "claimed":
        event["lock_token"] = "clock_" + _stable_hash(
            {"request_id": request_obj["request_id"], "event_type": event_type}
        )[:12]
        event["health_snapshot"] = _validate_claim_health_snapshot(
            (
                {
                    "paused": False,
                    "operations_health_ok": True,
                    "resource_budgets_ok": True,
                }
                if health_snapshot is None
                else health_snapshot
            ),
            "composition_lock_event.health_snapshot",
        )
    if event_type == "running":
        event["runtime_phase"] = {
            "step": "dry_run_processing",
            "bridge_mode": request_obj["handoff"]["bridge_mode"],
            "deterministic_mode": bool(request_obj["determinism"]["deterministic_mode"]),
        }
    if event_type == "validated":
        expected_outputs = request_obj["expected_artifacts"]["required_outputs"]
        validation_targets = sum(
            1 for item in expected_outputs if item.get("kind") in ("scene_manifest", "validation_summary")
        )
        event["validation_summary"] = {
            "status": "pass",
            "check_count": max(1, validation_targets),
            "deterministic_mode": bool(request_obj["determinism"]["deterministic_mode"]),
        }
    if event_type == "measure_handoff":
        placeholder_status = str(measure_handoff_status or "pending_measurement")
        if placeholder_status not in SUPPORTED_MEASUREMENT_HANDOFF_STATUSES:
            raise CompositionSchemaError(
                f"composition_lock_event.measure_handoff: unsupported placeholder_status '{placeholder_status}'"
            )
        event["measure_handoff"] = {
            "bridge_mode": request_obj["handoff"]["bridge_mode"],
            "measurement_record_path": request_obj["handoff"]["measurement_record_path"],
            "placeholder_status": placeholder_status,
        }
        if lineage_artifact_path is not None:
            event["measure_handoff"]["lineage_artifact_path"] = str(lineage_artifact_path)
        if lineage_artifact_sha256 is not None:
            event["measure_handoff"]["lineage_artifact_sha256"] = str(lineage_artifact_sha256)
    if event_type == "lineage_materialized":
        if not all(
            value is not None
            for value in (
                lineage_artifact_path,
                lineage_artifact_sha256,
                semantic_record_id,
                semantic_record_path,
                semantic_record_sha256,
                relational_attachment_hash,
                entity_count,
                relation_count,
                constraint_count,
            )
        ):
            raise CompositionSchemaError(
                "composition_lock_event.lineage_materialized: materialization payload fields are required"
            )
        event["lineage_materialization"] = {
            "lineage_artifact_path": str(lineage_artifact_path),
            "lineage_artifact_sha256": str(lineage_artifact_sha256),
            "semantic_record_id": str(semantic_record_id),
            "semantic_record_path": str(semantic_record_path),
            "semantic_record_sha256": str(semantic_record_sha256),
            "relational_attachment_hash": str(relational_attachment_hash),
            "entity_count": int(entity_count),
            "relation_count": int(relation_count),
            "constraint_count": int(constraint_count),
        }
    if event_type == "failed":
        event["error"] = {
            "code": str(error_code or "launch_failed"),
            "message": str(error_message or "dry-run runtime artifact emission simulated a terminal failure"),
        }
    if event_type == "released":
        event["release_reason"] = str(release_reason or "dry_run_completed")
    validate_composition_lock_event(event)
    return event


def append_dry_run_claim_release_events(
    runtime_request: Any,
    health_snapshot: Any,
    existing_events: List[Any] | None = None,
    actor: Dict[str, Any] | None = None,
    release_reason: str | None = None,
) -> List[Dict[str, Any]]:
    request_obj = deepcopy(validate_runtime_composition_request(runtime_request))
    if request_obj.get("status") != "queued":
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: runtime request must be queued"
        )

    snapshot_obj = _validate_claim_health_snapshot(
        health_snapshot,
        "append_dry_run_claim_release_events.health_snapshot",
    )
    _enforce_claim_health_gates(request_obj, snapshot_obj)
    actor_payload = (
        {"kind": "dry_run_claim_helper", "id": "module_composition_contracts"}
        if actor is None
        else _validate_runtime_actor(actor, "append_dry_run_claim_release_events.actor")
    )

    validated_events, current_status, active_claims_by_scene = _replay_claim_ledger(
        existing_events or [],
        request_obj["request_id"],
    )

    if current_status != "queued":
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: last lifecycle status must be queued"
        )

    scene_id = request_obj["lock_scope"]["scene_id"]
    active_scene_claim = active_claims_by_scene.get(scene_id)
    if active_scene_claim is not None and active_scene_claim["request_id"] != request_obj["request_id"]:
        raise CompositionSchemaError(
            "append_dry_run_claim_release_events: claim rejected because the scene already has an unreleased claim"
        )

    claimed_event = build_composition_lock_event(
        request_obj,
        "claimed",
        actor=actor_payload,
        health_snapshot=snapshot_obj,
        status_before_override=current_status,
    )
    released_event = build_composition_lock_event(
        request_obj,
        "released",
        actor=actor_payload,
        release_reason=release_reason,
        status_before_override=claimed_event["status_after"],
    )
    return validated_events + [claimed_event, released_event]


def _build_runtime_artifact_bundle_payload(
    starter_request: Any,
    output_root: str | None = None,
    emit_claimed: bool = False,
    emit_running: bool = False,
    emit_validated: bool = False,
    emit_measure_handoff_event: bool = False,
    emit_response: bool = False,
    response_status: str = "completed",
    emit_measurement_handoff: bool = False,
    complete_measurement_handoff: bool = False,
    emit_released: bool = False,
    emit_failed: bool = False,
    failure_error_code: str | None = None,
    failure_error_message: str | None = None,
    response_artifact: Any | None = None,
    recipe_sidecar: Any | None = None,
    scene_manifest: Any | None = None,
    validation_summary: Any | None = None,
) -> Dict[str, Any]:
    output_root_abs = _resolve_runtime_output_root(output_root)
    starter_request_obj = deepcopy(_validate_starter_compose_request(starter_request))
    composition_artifacts = None
    provided_composition_artifacts = {
        "recipe_sidecar": recipe_sidecar,
        "scene_manifest": scene_manifest,
        "validation_summary": validation_summary,
    }
    provided_count = sum(value is not None for value in provided_composition_artifacts.values())
    if provided_count not in (0, 3):
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: recipe_sidecar, scene_manifest, and validation_summary must be provided together"
        )
    if provided_count == 3:
        composition_artifacts = {
            "recipe_sidecar": deepcopy(validate_recipe_sidecar(recipe_sidecar)),
            "scene_manifest": deepcopy(validate_scene_manifest(scene_manifest)),
            "validation_summary": deepcopy(validate_validation_summary(validation_summary)),
        }
    if emit_failed and complete_measurement_handoff:
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: complete_measurement_handoff is incompatible with emit_failed"
        )
    if emit_running and not emit_claimed:
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: emit_running requires emit_claimed"
        )
    if emit_measure_handoff_event and not emit_validated:
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: emit_measure_handoff_event requires emit_validated"
        )
    if emit_measure_handoff_event and not emit_measurement_handoff:
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: emit_measure_handoff_event requires emit_measurement_handoff"
        )
    if response_artifact is not None and not emit_response:
        raise CompositionSchemaError(
            "write_runtime_artifact_bundle: response_artifact requires emit_response"
        )

    runtime_request = build_runtime_composition_request_artifact(
        starter_request_obj,
        output_root=output_root_abs,
    )
    if composition_artifacts is None:
        composition_artifacts = {
            "recipe_sidecar": build_runtime_recipe_sidecar(runtime_request),
            "scene_manifest": None,
            "validation_summary": None,
        }
        composition_artifacts["scene_manifest"] = build_runtime_scene_manifest(
            runtime_request,
            composition_artifacts["recipe_sidecar"],
        )
        composition_artifacts["validation_summary"] = build_runtime_validation_summary(
            runtime_request,
            composition_artifacts["recipe_sidecar"],
            composition_artifacts["scene_manifest"],
        )
    output_paths = _runtime_output_paths(runtime_request["request_id"], output_root_abs)
    events = []

    current_status = None

    def _append_event(event_type: str, **kwargs: Any) -> None:
        nonlocal current_status
        events.append(
            build_composition_lock_event(
                runtime_request,
                event_type,
                status_before_override=current_status,
                **kwargs,
            )
        )
        current_status = event_type

    _append_event("queued")
    if emit_claimed:
        _append_event("claimed")
    if emit_running:
        _append_event("running")
    if emit_validated:
        _append_event("validated")

    response_obj = None
    failure_event_payload = None
    if emit_response:
        if response_artifact is not None:
            response_obj = deepcopy(validate_composition_response(response_artifact))
        else:
            response_obj = build_dry_run_composition_response(starter_request_obj, status=response_status)
    if emit_failed:
        if response_obj is None:
            response_obj = build_dry_run_composition_response(
                starter_request_obj,
                status="error",
                error_code=failure_error_code,
                error_message=failure_error_message,
            )
        elif response_obj.get("status") not in ("error", "rejected"):
            raise CompositionSchemaError(
                "write_runtime_artifact_bundle: emit_failed requires an error or rejected response artifact"
            )
        failure_event_payload = {
            "error_code": failure_error_code or ((response_obj.get("error") or {}).get("code") if isinstance(response_obj.get("error"), dict) else None),
            "error_message": failure_error_message or ((response_obj.get("error") or {}).get("message") if isinstance(response_obj.get("error"), dict) else None),
        }

    measurement_handoff_obj = None
    measurement_handoff_status = None
    lineage_obj = None
    if emit_measurement_handoff:
        measurement_handoff_status = (
            "skipped_measurement"
            if emit_failed
            else ("completed_measurement" if complete_measurement_handoff else "pending_measurement")
        )
        measurement_handoff_obj = build_measurement_handoff_placeholder(
            runtime_request,
            response=response_obj,
            status=measurement_handoff_status,
        )
        lineage_obj = build_runtime_lineage_artifact(
            runtime_request,
            measurement_handoff_obj,
            response=response_obj,
            output_root=output_root_abs,
            composition_artifacts=composition_artifacts,
        )
    if emit_measure_handoff_event:
        _append_event(
            "measure_handoff",
            measure_handoff_status=measurement_handoff_status,
            lineage_artifact_path=(None if lineage_obj is None else output_paths["lineage_rel"]),
            lineage_artifact_sha256=(None if lineage_obj is None else _prefixed_stable_hash(lineage_obj)),
        )
        if lineage_obj is not None:
            lineage_obj = build_runtime_lineage_artifact(
                runtime_request,
                measurement_handoff_obj,
                response=response_obj,
                measure_handoff_event=events[-1],
                output_root=output_root_abs,
                composition_artifacts=composition_artifacts,
            )
            events[-1]["measure_handoff"]["lineage_artifact_sha256"] = _prefixed_stable_hash(lineage_obj)
            validate_composition_lock_event(events[-1])
    if failure_event_payload is not None:
        _append_event(
            "failed",
            error_code=failure_event_payload["error_code"],
            error_message=failure_event_payload["error_message"],
        )
    if emit_released:
        _append_event(
            "released",
            release_reason=(
                "dry_run_failed"
                if emit_failed
                else (
                    "dry_run_measure_handoff"
                    if emit_measure_handoff_event and not complete_measurement_handoff
                    else (
                        "dry_run_completed"
                        if complete_measurement_handoff and emit_measure_handoff_event
                        else ("dry_run_validated_checkpoint" if emit_validated else "dry_run_completed")
                    )
                )
            ),
        )

    runtime_bundle = {
        "request": runtime_request,
        "composition_artifacts": composition_artifacts,
        "response": response_obj,
        "measurement_handoff": measurement_handoff_obj,
        "lineage": lineage_obj,
        "lock_events": events,
        "paths": {
            "request_abs": output_paths["request_abs"],
            "request_rel": output_paths["request_rel"],
            "response_abs": output_paths["response_abs"],
            "response_rel": output_paths["response_rel"],
            "recipe_abs": output_paths["recipe_abs"],
            "recipe_rel": output_paths["recipe_rel"],
            "scene_manifest_abs": output_paths["scene_manifest_abs"],
            "scene_manifest_rel": output_paths["scene_manifest_rel"],
            "validation_summary_abs": output_paths["validation_summary_abs"],
            "validation_summary_rel": output_paths["validation_summary_rel"],
            "measure_abs": output_paths["measure_abs"],
            "measure_rel": output_paths["measure_rel"],
            "lineage_abs": output_paths["lineage_abs"],
            "lineage_rel": output_paths["lineage_rel"],
            "ledger_abs": output_paths["ledger_abs"],
            "ledger_rel": output_paths["ledger_rel"],
            "request": output_paths["request_abs"],
            "response": output_paths["response_abs"],
            "recipe_sidecar": output_paths["recipe_abs"],
            "scene_manifest": output_paths["scene_manifest_abs"],
            "validation_summary": output_paths["validation_summary_abs"],
            "measurement": output_paths["measure_abs"],
            "lineage": output_paths["lineage_abs"],
            "ledger": output_paths["ledger_abs"],
        },
    }
    runtime_bundle["bundle_hash"] = _stable_hash(
        {
            "request": runtime_request,
            "composition_artifacts": composition_artifacts,
            "response": response_obj,
            "measurement_handoff": measurement_handoff_obj,
            "lineage": lineage_obj,
            "lock_events": events,
        }
    )
    return runtime_bundle


def write_runtime_artifact_bundle(
    starter_request: Any,
    output_root: str | None = None,
    emit_claimed: bool = False,
    emit_running: bool = False,
    emit_validated: bool = False,
    emit_measure_handoff_event: bool = False,
    emit_response: bool = False,
    response_status: str = "completed",
    emit_measurement_handoff: bool = False,
    complete_measurement_handoff: bool = False,
    emit_released: bool = False,
    emit_failed: bool = False,
    failure_error_code: str | None = None,
    failure_error_message: str | None = None,
    recipe_sidecar: Any | None = None,
    scene_manifest: Any | None = None,
    validation_summary: Any | None = None,
) -> Dict[str, Any]:
    runtime_bundle = _build_runtime_artifact_bundle_payload(
        starter_request,
        output_root=output_root,
        emit_claimed=emit_claimed,
        emit_running=emit_running,
        emit_validated=emit_validated,
        emit_measure_handoff_event=emit_measure_handoff_event,
        emit_response=emit_response,
        response_status=response_status,
        emit_measurement_handoff=emit_measurement_handoff,
        complete_measurement_handoff=complete_measurement_handoff,
        emit_released=emit_released,
        emit_failed=emit_failed,
        failure_error_code=failure_error_code,
        failure_error_message=failure_error_message,
        recipe_sidecar=recipe_sidecar,
        scene_manifest=scene_manifest,
        validation_summary=validation_summary,
    )

    runtime_request = runtime_bundle["request"]
    composition_artifacts = runtime_bundle["composition_artifacts"]
    events = runtime_bundle["lock_events"]
    response_obj = runtime_bundle["response"]
    measurement_handoff_obj = runtime_bundle["measurement_handoff"]
    lineage_obj = runtime_bundle["lineage"]
    output_paths = runtime_bundle["paths"]

    os.makedirs(os.path.dirname(output_paths["request_abs"]), exist_ok=True)
    os.makedirs(os.path.dirname(output_paths["ledger_abs"]), exist_ok=True)
    with open(output_paths["request_abs"], "w", encoding="utf-8") as handle:
        json.dump(runtime_request, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    if composition_artifacts is not None:
        with open(output_paths["recipe_abs"], "w", encoding="utf-8") as handle:
            json.dump(composition_artifacts["recipe_sidecar"], handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with open(output_paths["scene_manifest_abs"], "w", encoding="utf-8") as handle:
            json.dump(composition_artifacts["scene_manifest"], handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        with open(output_paths["validation_summary_abs"], "w", encoding="utf-8") as handle:
            json.dump(composition_artifacts["validation_summary"], handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    if response_obj is not None:
        with open(output_paths["response_abs"], "w", encoding="utf-8") as handle:
            json.dump(response_obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    if measurement_handoff_obj is not None:
        with open(output_paths["measure_abs"], "w", encoding="utf-8") as handle:
            json.dump(measurement_handoff_obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    if lineage_obj is not None:
        with open(output_paths["lineage_abs"], "w", encoding="utf-8") as handle:
            json.dump(lineage_obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    with open(output_paths["ledger_abs"], "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False))
            handle.write("\n")

    return {
        "request": runtime_request,
        "composition_artifacts": composition_artifacts,
        "events": events,
        "response": response_obj,
        "measurement_handoff": measurement_handoff_obj,
        "lineage": lineage_obj,
        "paths": {
            "request": output_paths["request_abs"],
            "response": output_paths["response_abs"],
            "recipe_sidecar": output_paths["recipe_abs"],
            "scene_manifest": output_paths["scene_manifest_abs"],
            "validation_summary": output_paths["validation_summary_abs"],
            "measurement": output_paths["measure_abs"],
            "lineage": output_paths["lineage_abs"],
            "ledger": output_paths["ledger_abs"],
        },
    }
