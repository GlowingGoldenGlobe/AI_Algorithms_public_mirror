# temp_deep_research_prompt.md — 3D Integration Deep Research Brief

Date: 2026-02-06

## Context Summary

- Project: AI_Algorithms (“AI Brain”) — deterministic, measurement-first loop with file-backed memory and auditable artifacts.
- Research focus: deepen the 3D measurement bridge so spatial data flows deterministically through relational_state, telemetry, and downstream integrations.
- Determinism: enforced via fixed timestamp 2025-01-01T00:00:00Z; path safety helpers (`sanitize_id`, `safe_join`, `resolve_path`) required for storage.
- Active task log: temp_Feb2026_1.md (February 2026).
- Artifact bundle for this study: public_mirror/Copilot_DeepResearch_Package_20260201/.

## System Snapshot

- Latest verification: `.venv/Scripts/python.exe run_eval.py` PASS on 2026-02-06 with determinism_suite PASS after logging guidance refresh.
- Orchestrator tasks: pause before running evals; resume afterward (see AGENT_ASSESSMENT.md workflow steps).
- Health telemetry snapshots: Snapshots/metrics.json and Snapshots/ops_status.json captured immediately after the passing eval.

## Key Assessment Highlights

1. The 3D bridge and relational adapter successfully ingest seeded spatial payloads but coverage across semantic records is still sparse.
2. No persistent spatial snapshots exist under AI_Brain memory; replay tooling is limited to in-memory fixtures.
3. Telemetry for 3D operations only captures aggregate counters; skip/failure reasons are not yet recorded.
4. Determinism controls (seed, fixed timestamp) work, yet cache/limit enforcement is skeletal.
5. Upcoming tasks require coordination with graph/metric upgrades documented in the February log.

## Research Objectives for Copilot App

1. **Spatial Memory Persistence** — Recommend deterministic persistence formats and retrieval patterns for AI_Brain spatial snapshots (consider JSON vs. lightweight point-cloud formats) and how to thread them through module_relational_adapter + module_measure.
2. **Telemetry & Diagnostics** — Design telemetry hooks that log skip/failure reasons, latency bands, and cache outcomes without breaking determinism; include storage locations and schema proposals.
3. **Testing & Tooling** — Propose deterministic fixture generation strategies plus lightweight libraries or scripts (Windows-friendly) for validating 3D measurements end-to-end.
4. **Integration Sequencing** — Outline how new 3D artifacts should integrate with upcoming graph/metric validators so workstreams remain aligned.

## Desired Deliverables

1. Ranked proposal list (top 5) with:
	- Summary, impacted modules/files, rationale tied to measurement-first design.
	- Determinism risks and mitigation strategies.
	- Verification checklist (tasks, commands, new pytest cases, eval coverage).
2. References to deterministic spatial data handling or telemetry frameworks compatible with local Windows execution.
3. PASS/FAIL implementation checklist covering orchestrator pauses, config updates, code changes, and validation steps.
4. Optional suggestions for additional artifacts to publish in the mirror to aid future spatial research.

## Attachments to Provide with Prompt

**Section 1 — Core Repo Context**
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/COPILOT.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/raw_urls_index.md

**Section 2 — 3D Research Package**
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/README.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AGENT_ASSESSMENT.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AGENT_ASSESSMENT_3D.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_ai_brain_bridge.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_relational_adapter.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_integration.py
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/README.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/ARCHITECTURE.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/NEXT_TASKS.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/Snapshots/metrics.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/Snapshots/ops_status.json
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/temp_deep_research_prompt.md
- https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/temp_Feb2026_1.md

## Notes for External Reviewers

- Work within the single-writer protocol: pause orchestrator (`project_orchestrator.py --config orchestrator_config.json pause`) before running evals/tests and resume afterward.
- Keep determinism on; prefer explicit seeds and avoid nondeterministic libraries.
- Tailor instructions for Windows PowerShell commands and `.venv/Scripts/python.exe` invocations.
- When recommending new artifacts, specify mirror-ready paths plus any sanitization requirements.
