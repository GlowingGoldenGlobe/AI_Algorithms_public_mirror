# deep_research_prompt_core.md — Deterministic Harness Deep Research Brief

Date: 2026-02-06

## Context Summary

- Project: AI_Algorithms (“AI Brain”) — deterministic, measurement-first control loop with auditable files.
- Research focus: harden the deterministic harness (bridge, adapter, measurement, graph metrics, CI tasks) shipped in this core package.
- Determinism: repository fixes timestamps to 2025-01-01T00:00:00Z and relies on `sanitize_id`, `safe_join`, and `resolve_path` for path safety.
- Active task log: temp_Feb2026_1.md (February 2026) documents recent graph metric upgrades and mirror sync notes.
- Artifact bundle: public_mirror/Copilot_DeepResearch_Package_20260201_Core/ (self-contained for Copilot attachments).

## System Snapshot

- Latest verification: `.venv/Scripts/python.exe run_eval.py` on 2026-02-06 (major suites PASS; `determinism_suite` currently FAIL and needs investigation alongside new graph metric adapters).
- Harness tasks: `Scripts/agent_run.sh` seeds deterministic pytest runs; `.vscode/tasks.json` wires VS Code commands for eval + deterministic agent execution.
- Telemetry: `Telemetry/metrics.json` and `Telemetry/ops_status.json` captured immediately after the most recent eval run.

## Key Assessment Highlights

1. Deterministic graph snapshot + metric inputs now persist via `module_measure` with hash tracking, but composed metrics need review for determinism regressions.
2. Integration tests cover bridge caching, relational adapter extras, and graph snapshot consumers, yet end-to-end determinism coverage for composed metrics is thin.
3. PR template and VS Code tasks enforce deterministic workflows, though guidance for monthly task logs and mirror syncing should be revalidated for external reviewers.
4. Current telemetry captures counts and hashes but omits failure reason logging for determinism suite breakages.
5. Mirror artifacts are aligned with the root repo, but future upgrades (metric engine rollout, validator plan) depend on sequencing captured in specs.

## Research Objectives for Copilot App

1. **Determinism Suite Remediation** — Diagnose why `determinism_suite` fails post graph metric persistence and outline fixes that preserve new snapshot hashing.
2. **Graph Metric Composition Strategy** — Recommend deterministic composition patterns, storage schema, and verification commands for the new graph metric adapters.
3. **Harness Coverage Expansion** — Identify missing pytest scenarios or lightweight fixtures that would close gaps in deterministic end-to-end coverage (bridge → adapter → measure → metrics).
4. **Telemetry & Reporting Enhancements** — Propose telemetry additions for failure reasons, latency buckets, and hash drift monitoring without compromising deterministic runs.

## Desired Deliverables

1. Ranked action list (top 5) with:
	- Summary, impacted modules/files, and rationale anchored in the measurement-first design.
	- Determinism risks plus mitigation steps.
	- Verification checklist (pytest targets, eval flags, mirror sync commands).
2. References to deterministic state-tracking or metrics composition practices applicable to Windows-first workflows.
3. PASS/FAIL implementation checklist covering orchestrator pauses, config updates, code and test changes, telemetry validation, and mirror publishing.
4. Optional suggestions for additional mirror artifacts (e.g., fixtures, schematics) that would accelerate future deterministic harness research.

## Attachments to Provide with Prompt

**Section 1 — Package Overview & Workflow**
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/COPILOT.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/raw_urls_index.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/README.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/AGENT.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/ASSESSMENT_PROCEDURE.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/temp_Feb2026_1.md

**Section 2 — Deterministic Harness Sources**
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_ai_brain_bridge.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_relational_adapter.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_measure.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_integration.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/agent_run.sh
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/.vscode/tasks.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/.github/PULL_REQUEST_TEMPLATE.md

**Section 3 — Tests, Telemetry, and Config**
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Tests/agent_integration_test.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Tests/mocks/mock_ai_brain.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/run_eval.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/hardware_limits_check.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Telemetry/metrics.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Telemetry/ops_status.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/config.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/orchestrator_config.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/orchestrator_config_assessment.json

## Notes for External Reviewers

- Operate within the single-writer protocol: pause the orchestrator before running evals/tests and resume afterward (`project_orchestrator.py --config orchestrator_config.json pause|resume`).
- Keep determinism enabled; rely on `Scripts/agent_run.sh` or `.vscode/tasks.json` commands for consistent pytest execution.
- Target Windows PowerShell command formats (`.venv\Scripts\python.exe`) when supplying verification steps.
- When recommending new artifacts, specify mirror-ready paths plus sanitization considerations so they can be published without additional triage.
