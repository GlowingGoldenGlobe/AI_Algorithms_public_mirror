# Copilot Deep Research Package — 2026-02-01

This folder bundles the files requested for the Microsoft Copilot deep research prompt.

## Contents

- temp_Feb2026_1.md — Active February 2026 task and assessment log.
- temp_deep_research_prompt.md — Context snapshot and outstanding questions for research.
- AGENT_ASSESSMENT.md — General assessment workflow for this repository.
- AGENT_ASSESSMENT_3D.md — 3D-focused assessment guide.
- module_ai_brain_bridge.py — Bridge invoking the AI_Brain measurement engine.
- module_relational_adapter.py — Adapter mapping 3D measurements into relational_state.
- module_integration.py — Cycle orchestrator entry point calling the adapter.
- AI_Brain/README.md — 3D measurement core overview.
- AI_Brain/ARCHITECTURE.md — Layered architecture of the 3D core.
- AI_Brain/NEXT_TASKS.md — Pending upgrades for the 3D subsystem.
- TemporaryQueue/metrics.json — Latest run metrics snapshot (deterministic mode).
- TemporaryQueue/ops_status.json — Recent ops status report (dashboard + orchestrator health).

## Usage Notes

- Attach these files (plus this README) when running the Copilot deep research prompt.
- Maintain single-writer workflow: pause orchestrator before evals and resume afterwards.
- Determinism is enabled with fixed timestamp 2025-01-01T00:00:00Z.
- Path safety helpers: `sanitize_id`, `safe_join`, `resolve_path`.

## Source

All files copied from the root workspace on 2026-02-01 to provide a mirror-safe package for external review.
