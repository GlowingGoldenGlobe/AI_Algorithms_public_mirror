# temp_deep_research_prompt.md — External Research Prep

Date: 2026-02-01

## Context Snapshot

- Repo: AI_Algorithms (deterministic measurement-first AI Brain).
- Current focus: strengthening 3D simulation integration for relational measurement.
- Determinism: enabled (fixed timestamp 2025-01-01T00:00:00Z).
- Latest health check: `run_eval.py` PASS on 2026-02-01; orchestrator resumed after pause.
- Active logs/tasks: see temp_Feb2026_1.md (February task log).

## Recent Assessment Highlights

1. 3D bridge/adapter flow confirmed working for seeded record (`eval_spatial_001`).
2. Most semantic records still lack `spatial_measurement` payloads (coverage gap).
3. AI_Brain memory directory lacks persisted spatial snapshots.
4. No telemetry on bridge execution frequency or failure reasons.
5. Upgrade ideas pending: telemetry, spatial memory persistence, broader tests.

## Outstanding Questions for Deep Research

- Proven patterns for integrating deterministic 3D measurements into relational knowledge graphs.
- Architectural approaches to persist and query spatial memory efficiently in measurement-first systems.
- Best practices for telemetry around optional 3D measurement pipelines (how to capture skip/error reasons without impacting determinism).
- Testing strategies for mock 3D assets that keep evaluation deterministic and quick.
- Tooling/library recommendations (Blender pipelines, ASCII PLY/OBJ handling, lightweight point-cloud libs) that align with repo constraints (Windows-friendly, deterministic, local execution, no heavy GPU assumptions).

## Desired Deliverables from Copilot App

1. Ranked proposal list (most impactful first) covering:
   - Telemetry instrumentation.
   - Spatial memory persistence + retrieval architecture.
   - Expanded automated test coverage for 3D integration.
2. For each proposal: required files/modules to touch, risk assessment, verification steps.
3. Optional references (docs/tutorials) for Blender-to-point-cloud workflows compatible with deterministic pipelines.
4. PASS/FAIL checklist for incorporating upgrades (e.g., eval suite, determinism checks, new tests).

## Files to Reference in Prompt

- temp_Feb2026_1.md (active task log).
- AGENT_ASSESSMENT_3D.md (3D assessment workflow guide).
- AGENT_ASSESSMENT.md (general assessment guide).
- module_ai_brain_bridge.py, module_relational_adapter.py, module_integration.py.
- AI_Brain/ARCHITECTURE.md, AI_Brain/README.md, AI_Brain/NEXT_TASKS.md.
- TemporaryQueue/metrics.json, TemporaryQueue/ops_status.json (latest health).

## Notes for External Review

- Emphasize single-writer workflow (pause orchestrator before evals).
- Mention determinism requirements (fixed timestamp) and path safety APIs (`sanitize_id`, `safe_join`, `resolve_path`).
- Request responses tailored to Windows PowerShell environment.
- Ask for concrete next tasks ready to log into temp_Feb2026_1.md.

## Raw GitHub URLs for Attachments

- README.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/README.md
- AGENT_ASSESSMENT.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AGENT_ASSESSMENT.md
- AGENT_ASSESSMENT_3D.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AGENT_ASSESSMENT_3D.md
- module_ai_brain_bridge.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_ai_brain_bridge.py
- module_integration.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_integration.py
- module_relational_adapter.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/module_relational_adapter.py
- AI_Brain/ARCHITECTURE.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/ARCHITECTURE.md
- AI_Brain/README.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/README.md
- AI_Brain/NEXT_TASKS.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/AI_Brain/NEXT_TASKS.md
- Snapshots/metrics.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/Snapshots/metrics.json
- Snapshots/ops_status.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/Snapshots/ops_status.json
- temp_deep_research_prompt.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/temp_deep_research_prompt.md
- temp_Feb2026_1.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201/temp_Feb2026_1.md
