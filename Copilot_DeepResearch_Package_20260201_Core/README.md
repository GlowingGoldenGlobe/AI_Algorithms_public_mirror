# Copilot Deep Research Package — Core System (2026-02-05)

This package captures the key artifacts required to analyze or upgrade the AI Brain’s core deterministic workflow.

## Contents

- temp_Feb2026_1.md — Current month task log for operational context.
- Docs/
  - README.md — Overview of the AI Brain measurement-first pipeline.
  - DESIGN_GOALS.md — Canonical design principles and category positioning.
  - AGENT.md — Persistent agent instructions (single-writer rules, logging expectations).
  - ASSESSMENT_PROCEDURE.md — Standard health/assessment runbook.
- Config/
  - config.json — System configuration (measurement weights, hardware limits, policies).
  - orchestrator_config.json — Automation orchestrator settings.
  - orchestrator_config_assessment.json — Assessment-focused orchestrator config.
- Modules/
  - module_integration.py — Cycle orchestrator linking storage, measurement, awareness, scheduling.
  - module_ai_brain_bridge.py — Bridge into the AI_Brain 3D measurement core.
  - module_relational_adapter.py — Adapter mapping 3D measurements into relational_state.
  - module_measure.py — Deterministic measurement signals feeding the arbiter.
- Scripts/
  - run_eval.py — Evaluation harness (acceptance gate).
  - hardware_limits_check.py — Hardware safety preflight.
  - ops_status_report.py — Operational status snapshot generator.
  - agent_run.sh — Deterministic test harness runner (telemetry-emitting pytest wrapper).
- Tests/
  - agent_integration_test.py — 3D bridge deterministic integration test using mock AI Brain.
  - mocks/mock_ai_brain.py — Reusable deterministic measurement engine mock.
- Telemetry/
  - metrics.json — Latest metrics snapshot (deterministic mode enabled).
  - ops_status.json — Latest ops report (dashboard/orchestrator health).
- .vscode/tasks.json — VS Code task wiring for deterministic agent runs.
- .github/PULL_REQUEST_TEMPLATE.md — Deterministic checklist used for PR reviews.
- Prompts/deep_research_prompt_core.md — Paste-ready prompt text for Microsoft Copilot Deep Research.

## Usage Notes

- Attach this directory (plus README) when requesting external analysis focused on the system’s core algorithms and operations.
- Emphasize determinism (fixed timestamp 2025-01-01T00:00:00Z) and the single-writer workflow (pause orchestrator before evals, resume afterward).
- Highlight path safety utilities (`sanitize_id`, `safe_join`, `resolve_path`) when asking for recommendations.

## Source

All files copied from the root workspace on 2026-02-05.
