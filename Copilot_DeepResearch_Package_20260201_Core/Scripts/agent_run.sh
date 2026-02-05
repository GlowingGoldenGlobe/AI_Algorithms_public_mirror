#!/usr/bin/env bash
# Deterministic agent test harness runner.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

: "${DETERMINISTIC_TIMESTAMP:=2025-01-01T00:00:00Z}"
export DETERMINISTIC_TIMESTAMP

TEST_TARGET="${1:-Tests/agent_integration_test.py}"

echo "Using DETERMINISTIC_TIMESTAMP=${DETERMINISTIC_TIMESTAMP}"
echo "Running pytest target: ${TEST_TARGET}"

echo "[placeholder] Ensure orchestrator is paused before running tests"

PYTEST_EXIT=0
"${PYTHON}" -m pytest -q "${TEST_TARGET}" || PYTEST_EXIT=$?

METRICS_DIR="${ROOT_DIR}/Telemetry"
mkdir -p "${METRICS_DIR}"

export PYTEST_EXIT_CODE="${PYTEST_EXIT}"

"${PYTHON}" - <<'PY'
import json
import os
from datetime import datetime, timezone

status = "passed" if int(os.environ.get("PYTEST_EXIT_CODE", "0")) == 0 else "failed"
metrics = {
    "timestamp": os.environ.get("DETERMINISTIC_TIMESTAMP"),
    "status": status,
    "pytest_exit_code": int(os.environ.get("PYTEST_EXIT_CODE", "0")),
    "runner": "Scripts/agent_run.sh",
    "generated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
}
with open(os.path.join("Telemetry", "metrics.json"), "w", encoding="utf-8") as handle:
    json.dump(metrics, handle, indent=2)
print("Wrote Telemetry/metrics.json :: status=", status)
PY

if [ "${PYTEST_EXIT}" -ne 0 ]; then
    echo "Pytest exited with status ${PYTEST_EXIT}" >&2
    exit "${PYTEST_EXIT}"
fi

echo "[placeholder] Resume orchestrator after tests"
