# AGENT_ASSESSMENT.md — AI Brain Assessment Guide

Use this guide when you want an agent to evaluate the current AI Brain run without pasting the full repository. Attach this file to the chat and issue the command **Assess**.

---

## 0. Expectations for the Agent

- Operate in VS Code Agent Mode with write access.
- Log every new task in `temp_12.md` before making changes.
- Prefer VS Code tasks over direct shell commands when available.
- After significant changes, run the eval harness and record results.

---

## 1. Minimum Context Attachments

Provide (or confirm availability of) the following assets so the agent can assess accurately:

| What | Location | Why it matters |
| --- | --- | --- |
| Task & assessment log | `temp_12.md` | Shows recent work, open risks, verification state. |
| Assessment runbook | `ASSESSMENT_PROCEDURE.md` | Defines detailed checklist; agent must stay aligned. |
| Eval harness | `run_eval.py` (VS Code task **AI Brain: eval**) | Canonical health gate; rerun after changes. |
| CLI control surface | `cli.py` | Provides status, cycle, pause/resume commands. |
| Orchestrator config | `orchestrator_config.json` and `orchestrator_config_assessment.json` | Needed if orchestration state looks off. |
| Ops dashboard script | `scripts/run_dashboard_server.py`, `dashboard.html` | Used to regenerate ops/metrics summaries. |
| Metrics helpers | `scripts/metrics_table.py`, `metrics_dashboard.py` | For interpreting `TemporaryQueue/metrics*.json`. |

When sharing runtime artifacts, include the latest copies of:

- `TemporaryQueue/metrics.json`
- `TemporaryQueue/metrics_compare.json` (if compare mode is relevant)
- `TemporaryQueue/ops_status.json`
- `TemporaryQueue/hardware_preflight.json` (if hardware limits recently changed)
- `TemporaryQueue/activity_scaling_latest.json`
- `ActiveSpace/orchestrator_state.json`
- `ActiveSpace/orchestrator.lock.info.json`
- Any new files under `ActiveSpace/Observability/` created by monitoring scripts

---

## 2. Key Directories to Inspect

| Directory | Contents worth checking |
| --- | --- |
| `ActiveSpace/` | Live orchestrator state, active activity log, lock info. |
| `LongTermStore/ActiveSpace/` | Historical activity mirror; confirms persistence health. |
| `LongTermStore/Semantic/` | Per-activity semantic records; inspect matching ids from recent cycles. |
| `TemporaryQueue/` | Metrics, ops status, adversarial reports, dashboard data. |
| `scripts/` | `activity_scaling_log.py`, `hardware_limits_check.py`, other assessment helpers. |
| `AI_Brain/` | Core measurement engine (only needed if anomalies point into 3D core). |

---

## 3. Assessment Workflow (Agent Checklist)

1. **Stabilize writers**
   - If `project_orchestrator.py` daemon is active, pause it (VS Code task **AI Brain: orchestrator pause**).
   - Confirm pause via **AI Brain: orchestrator status**.

2. **Capture system status**
   - Run `py -3 cli.py status --det --policy-rate --recent 3`.
   - Review `ActiveSpace/orchestrator_state.json` for paused flag, last cycle timestamp, and current policy set.

3. **Run health gate**
   - Execute VS Code task **AI Brain: eval** (`run_eval.py`).
   - If it fails, stop and report failure details + suspected causes.

4. **Inspect metrics**
   - Read `TemporaryQueue/metrics.json` (run metrics).
   - Use **AI Brain: metrics table** task or `py -3 scripts/metrics_table.py --json` for summaries.
   - For compare runs, trigger dashboard endpoint (`POST /api/metrics_table`) or use local task as needed.

5. **Check dashboard artifacts** (optional but recommended)
   - Run **AI Brain: ops status report (write JSON)** to refresh `TemporaryQueue/ops_status.json`.
   - If the dashboard suite is running, hit `http://127.0.0.1:8000/api/ping` and load `dashboard.html?autofetch=run`.
   - Use “Generate Ops Status + Fetch” or “Metrics Table” buttons to pull fresh data.

6. **Deep artifact spot-check**
   - Inspect the latest activity entry in `ActiveSpace/activity.json` and its mirror in `LongTermStore/ActiveSpace/activity.json`.
   - Locate the corresponding semantic record in `LongTermStore/Semantic/<activity_id>.json`.
   - Confirm `reason_chain`, `signals`, `collector_outputs`, and `toggle_justifications` align.

7. **Resume orchestrator (if paused)**
   - Run **AI Brain: orchestrator resume** once assessment reads are complete.

---

## 4. Reporting Format

Produce a concise assessment with:

1. **Findings**
   - Eval pass/fail result.
   - Highlights from metrics (notable deltas, regressions, anomalies).
   - Operational status (orchestrator paused?, dashboard healthy?).

2. **Risks / Gaps**
   - Any missing data, stalled processes, or integrity issues in artifacts.

3. **Recommended Tasks**
   - Each actionable item logged into `temp_12.md` per workflow rules.
   - Note required verification commands for each task (usually **AI Brain: eval**).

4. **Verification**
   - List commands/tasks you ran and their outcomes.

---

## 5. Additional Notes

- Determinism is enforced; avoid introducing nondeterministic behavior without toggles.
- Use `sanitize_id`, `safe_join`, and `resolve_path` for any file access.
- Keep changes minimal and auditable; large edits require backups or explicit diff summaries in `temp_12.md`.
- If external review is needed, point to the public mirror workflow (`docs/PUBLIC_MIRROR_WORKFLOW.md`).

Attach this guide plus the listed runtime artifacts, then ask the agent to **Assess** to trigger a focused evaluation.
