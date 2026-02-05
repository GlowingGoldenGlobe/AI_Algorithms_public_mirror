# Deep Research Prompt for Copilot DeepResearch Package Core

**Goal:** Obtain authoritative guidance on deterministic measurement harnesses, 3D-to-relational mapping best practices, and integration test patterns for AI bridge modules.

**Context:** Repository: Copilot_DeepResearch_Package_20260201_Core. Target files: module_ai_brain_bridge.py, module_relational_adapter.py, module_measure.py. Tests must be deterministic using timestamp `2025-01-01T00:00:00Z`.

**Questions to answer:**
1. Recommended interface contract for an AI bridge module that accepts 3D measurements and an AI client, and returns a relational mapping suitable for downstream adapters.
2. Deterministic testing patterns for measurement pipelines that rely on time, randomness, or external services.
3. Minimal, robust schema for relational mapping output (required keys, types, and validation rules).
4. Common pitfalls when mocking AI brain clients and how to avoid brittle tests.
5. Example unit and integration test snippets (Python/pytest) that are CI-friendly and do not require external binaries.

**Deliverable format:** concise report (max 2 pages) with:
- 5–8 bullet recommendations
- 2 short code snippets (one mock, one test)
- A short checklist for converting a flaky test into a deterministic one

**Constraints:** Prefer authoritative sources (academic papers, engineering blogs from major AI infra teams, official pytest docs). Cite sources inline.

## Raw GitHub URLs for Attachments

- README.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/README.md
- .github/PULL_REQUEST_TEMPLATE.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/.github/PULL_REQUEST_TEMPLATE.md
- .vscode/tasks.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/.vscode/tasks.json
- Config/config.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/config.json
- Config/orchestrator_config.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/orchestrator_config.json
- Config/orchestrator_config_assessment.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Config/orchestrator_config_assessment.json
- Docs/AGENT.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/AGENT.md
- Docs/ASSESSMENT_PROCEDURE.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/ASSESSMENT_PROCEDURE.md
- Docs/DESIGN_GOALS.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/DESIGN_GOALS.md
- Docs/README.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Docs/README.md
- Modules/module_ai_brain_bridge.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_ai_brain_bridge.py
- Modules/module_integration.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_integration.py
- Modules/module_measure.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_measure.py
- Modules/module_relational_adapter.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Modules/module_relational_adapter.py
- Prompts/deep_research_prompt_core.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Prompts/deep_research_prompt_core.md
- Scripts/agent_run.sh — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/agent_run.sh
- Scripts/hardware_limits_check.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/hardware_limits_check.py
- Scripts/ops_status_report.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/ops_status_report.py
- Scripts/run_eval.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Scripts/run_eval.py
- Telemetry/metrics.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Telemetry/metrics.json
- Telemetry/ops_status.json — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Telemetry/ops_status.json
- Tests/agent_integration_test.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Tests/agent_integration_test.py
- Tests/mocks/mock_ai_brain.py — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/Tests/mocks/mock_ai_brain.py
- temp_Feb2026_1.md — https://raw.githubusercontent.com/GlowingGoldenGlobe/AI_Algorithms_public_mirror/refs/heads/main/Copilot_DeepResearch_Package_20260201_Core/temp_Feb2026_1.md
