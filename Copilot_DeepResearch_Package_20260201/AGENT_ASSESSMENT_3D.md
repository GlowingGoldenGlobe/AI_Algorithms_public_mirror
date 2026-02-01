# AGENT_ASSESSMENT_3D.md — 3D Simulation Assessment Guide

Attach this guide when requesting a focused evaluation of the AI Brain's 3D simulation usage and its upgrade needs. After attaching, instruct the agent with the single word **Assess** (or a short variant such as "Assess 3D").

---

## 0. Expectations for the Agent

- Work in VS Code Agent Mode with write access.
- Log all discovered tasks in the active task log (see README "Task Log Rotation Procedure").
- Keep changes surgical; record verification steps after modifications.
- Run **AI Brain: eval** after any substantive code change.

---

## 1. Minimum Context Attachments

| Asset | Location / Task | Purpose |
| --- | --- | --- |
| Primary task log | `temp_Feb2026_1.md` (or current active log) | Shows recent work and constraints. |
| Persistent agent rules | `AGENT.md`, `.github/copilot-instructions.md` | Workflow expectations and safety constraints. |
| 3D core overview | `AI_Brain/README.md`, `AI_Brain/ARCHITECTURE.md` | Describes simulation engine, memory layout, and interfaces. |
| Integration glue | `module_relational_adapter.py`, `module_ai_brain_bridge.py`, `module_measure.py` | How relational measurements call into the 3D core. |
| Bridge config | `config.json` (`ai_brain_bridge`, `measurement_weights`, `determinism`) | Tunables impacting 3D usage. |
| Relational pipeline | `module_integration.py`, `module_concept_measure.py`, `module_measure.py` | End-to-end call graph from cycle intake to measured outputs. |
| Simulation tasks / scripts | `scripts/` (e.g., `activity_scaling_log.py`, `hardware_limits_check.py`, `ai_brain_metrics.py`) | Surface current performance metrics. |
| Current eval outputs | `TemporaryQueue/metrics.json`, `TemporaryQueue/metrics_compare.json`, `TemporaryQueue/ops_status.json` | Reveal how 3D components currently perform. |
| Recent activity samples | `ActiveSpace/activity.json`, `LongTermStore/Semantic/<id>.json` | Validate 3D data presence in measured artifacts. |

Optional but useful:

- `AI_Brain/memory/` contents (if non-empty) for simulation state snapshots.
- `AI_Brain/tests/` or benchmarking scripts (if present).
- Any recent design notes about 3D upgrades (`RESULTS_*`, `roadmap_table*.md`).

---

## 2. Key Questions to Answer

1. **Current Utilization**
   - Where does the 3D core participate in the relational measurement pipeline?
   - Which modules invoke 3D simulations and what data do they exchange?
   - Are there telemetry or metrics showing simulation frequency, cost, or bottlenecks?

2. **Data Completeness & Fidelity**
   - Do activity records include 3D-derived measurements, constraints, or reason chains?
   - Are semantic records enriched with 3D observables, and are they referenced in decisions/toggles?
   - Is there schema drift between 3D outputs and what consumers expect?

3. **Upgrade Needs**
   - What pain points exist (performance, coverage gaps, determinism risks)?
   - Which modules require refactors or new APIs to make 3D simulations more useful?
   - Are additional storage paths, policies, or metrics needed to close the loop?

4. **Determinism & Reproducibility**
   - Does the 3D core respect deterministic settings (fixed seeds, timestamp overrides)?
   - Are there any stochastic elements without toggles or reproducibility controls?

5. **Testing & Verification Gaps**
   - What automated tests cover 3D behavior (unit/integration/eval cases)?
   - Identify missing tests or monitoring needed for future upgrades.

---

## 3. Assessment Workflow (Agent Checklist)

1. **Stabilize Writers**
   - Pause the orchestrator if running (**AI Brain: orchestrator pause**), confirm via **AI Brain: orchestrator status**.

2. **Establish Current State**
   - Run `py -3 cli.py status --det --recent 3 --policy-rate` to capture current metrics and policy context.
   - Record relevant outputs in the task log.

3. **Map 3D Integration Points**
   - Read `module_relational_adapter.py` to trace calls into `AI_Brain.*` modules.
   - Inspect `module_ai_brain_bridge.py` (or similar bridge) for I/O expectations.
   - Document key functions, data structures, and assumptions.

4. **Inspect 3D Core**
   - Review `AI_Brain/README.md` and `AI_Brain/ARCHITECTURE.md` for component responsibilities.
   - Sample code in `AI_Brain/` (e.g., measurement engine, simulation harness) to understand current features.
   - Note any TODOs or warnings about missing features.

5. **Evaluate Artifacts**
   - Open recent semantic and activity logs to verify 3D-derived data presence.
   - Check for linkages between 3D outputs and relational measurements or toggle decisions.

6. **Run Relevant Scripts / Tests**
   - Execute `py -3 run_eval.py` (or **AI Brain: eval**) to ensure baseline health.
   - If 3D-specific scripts exist (e.g., `python AI_Brain/tests/run_3d_checks.py`), run them and capture results.
   - Consider targeted dry-runs of modules producing 3D data, ensuring determinism compliance.

7. **Identify Upgrade Requirements**
   - For each pain point, outline concrete improvements (e.g., expand measurement schema, add caching, improve integration API).
   - Estimate dependencies (new configs, storage migrations, additional metrics).

8. **Resume Orchestrator**
   - If paused, run **AI Brain: orchestrator resume** after assessment steps conclude.

---

## 4. Reporting Template

When responding to the "Assess" command, structure the assessment as follows:

1. **Findings**
   - Current 3D integration summary (modules, data flow, verification status).
   - Key strengths (what already works) and observed issues.

2. **Gaps / Risks**
   - Missing instrumentation, performance limits, determinism breaches, schema mismatches, or testing gaps.

3. **Recommended Upgrades**
   - Ranked list of actionable tasks (log each into the active task log).
   - For each: impacted files/modules, expected benefit, verification commands.

4. **Verification Performed**
   - Commands/tasks run and their outcomes (include eval status and any 3D-specific checks).

---

## 5. Additional Notes

- Maintain determinism: use seeded randomness and respect `config.json > determinism` settings.
- Path safety: use `sanitize_id`, `resolve_path`, and `safe_join` for file operations.
- Avoid modifying large swaths of the 3D core without backups or explicit diff summaries logged in the task file.
- If deeper research or third-party review is needed, reference `docs/PUBLIC_MIRROR_WORKFLOW.md` for mirror publication.

This guide keeps the assessment focused on 3D simulation health and outlines how to plan upgrades that make relational measurement more effective and reliable.
