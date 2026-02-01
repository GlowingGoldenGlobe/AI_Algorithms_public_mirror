# Deep Research Prompt — Core System (2026-02-01)

Use this prompt when asking Microsoft Copilot (Deep Research) for guidance on upgrading or repairing the AI Brain while preserving its core measurement-first design.

## Paste-Ready Prompt

You are Microsoft Copilot (Deep Research). Review the attached files from public_mirror/Copilot_DeepResearch_Package_20260201_Core:

- Docs/README.md, Docs/DESIGN_GOALS.md, Docs/AGENT.md, Docs/ASSESSMENT_PROCEDURE.md
- Config/config.json, Config/orchestrator_config.json, Config/orchestrator_config_assessment.json
- Modules/module_integration.py, Modules/module_ai_brain_bridge.py, Modules/module_relational_adapter.py, Modules/module_measure.py
- Scripts/run_eval.py, Scripts/hardware_limits_check.py, Scripts/ops_status_report.py
- Telemetry/metrics.json, Telemetry/ops_status.json
- temp_Feb2026_1.md (current task log)

Context: AI Brain is a deterministic, measurement-first pipeline. Determinism is enabled (fixed timestamp 2025-01-01T00:00:00Z). Workflows require pausing the orchestrator before running eval/canary tasks. Path safety helpers: sanitize_id, safe_join, resolve_path. Environment: Windows PowerShell.

Deliverables requested:
1. Ranked recommendations (top 5) for upgrading or repairing core system behavior while preserving relational measurement, objective reality logic, rational judgment, and objective seeking loops.
   - For each recommendation: affected files/modules, rationale, risk assessment (impact on determinism, complexity), verification plan (commands/tasks/tests, telemetry to inspect).
2. Suggestions for strengthening operational safety (hardware limits, single-writer enforcement) without breaking the unique deterministic workflow.
3. References or patterns relevant to measurement-first cognitive systems (no probabilistic LLM replacements).
4. PASS/FAIL checklist covering preconditions (pause orchestrator, determinism check), implementation steps, and required verification (eval suite, dashboards, documentation updates).

Tailor responses for a Windows PowerShell workflow and favor deterministic-friendly tooling.

## Notes

- Attach the folder contents plus this file when submitting the prompt.
- Mention any additional context from temp_Feb2026_1.md if important.
