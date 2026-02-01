# Assessment Procedure (AI_Algorithms)

This repo already has an *implicit* assessment practice:

- `temp_12.md` acts as the running assessment + task log.
- `run_eval.py` (and the VS Code task “AI Brain: eval”) acts as the acceptance/health gate.
- `.github/copilot-instructions.md` and `AGENT.md` define the “log tasks first, then implement, then re-run eval” workflow.

This document makes that practice explicit so any VS Code agent (or human) can run periodic assessments consistently.

---

## Where to report assessments

- **Primary place:** append to `temp_12.md`.
  - Add a dated section:
    - “Assessment (YYYY-MM-DD)”
    - findings (what’s good / what’s risky)
    - recommended tasks (next actions)
  - If tasks are actionable, convert them into checklist items in `temp_12.md`.

- **Optional (for long-form reports):** create a new `ASSESSMENT_YYYYMMDD.md` when the assessment is big.
  - Still add a short summary + links back into `temp_12.md`.

---

## Assessment cadence (suggested)

- **Quick check:** after any meaningful code change (especially logic, determinism, storage, or policy).
- **Routine check:** daily/weekly depending on how actively you’re iterating.

---

## Minimum assessment checklist

### 1) Confirm the system “runs”

- Status:

```powershell
py -3 cli.py status
```

Optional (recommended): include recent cycles + policy activation snapshot:

```powershell
py -3 cli.py status --det --policy-rate --recent 3
```

If the automation orchestrator daemon is running, you can also confirm it is healthy via:
- `ActiveSpace/orchestrator_state.json`
- `ActiveSpace/orchestrator.lock.info.json`
- `TemporaryQueue/orchestrator/orchestrator.log`

- One demo cycle (pick a unique id):

```powershell
py -3 cli.py cycle --id assess_demo_001 --content "keyword good synthesis" --category semantic
```

### 2) Run the evaluation harness (acceptance gate)

```powershell
py -3 run_eval.py
```

(or VS Code task: “AI Brain: eval”)

If eval fails, the assessment output should stop here and capture:
- which eval(s) failed
- what recent change likely caused it
- proposed fix task(s)

**Single-writer note (orchestrator):** if the `project_orchestrator.py` daemon is running, avoid running eval concurrently.
Pause it before eval, then resume afterwards:

```powershell
./.venv/Scripts/python.exe project_orchestrator.py --config orchestrator_config.json pause
py -3 run_eval.py
./.venv/Scripts/python.exe project_orchestrator.py --config orchestrator_config.json resume
```

### 2b) Confirm metrics were flushed (run metrics)

`run_eval.py` flushes metrics at the end of the run. Confirm the file exists and summarize it:

```powershell
py -3 scripts/metrics_dashboard.py --path TemporaryQueue/metrics.json
```

Interpretation:
- `TemporaryQueue/metrics.json` is the **run** metrics file (live counters from normal runs).
- `TemporaryQueue/metrics_compare.json` is the **compare** metrics file (used by the adaptive-vs-fixed comparison helper).

### 3) Spot-check run artifacts (ground truth)

Check these artifacts for internal consistency:

- Activity log(s):
  - `ActiveSpace/activity.json`
  - `LongTermStore/ActiveSpace/activity.json`

- The semantic record for your demo id:
  - `LongTermStore/Semantic/<id>.json`

Focus on:
- do `signals` agree with `collector_outputs`?
- are timestamps consistent with determinism settings?
- did `toggle_justifications` get written?
- does `reason_chain` exist?
- are `matched_procedures` present when expected?

---

## Optional: dashboard-based assessment (recommended)

The repo includes a local dashboard that can auto-load the recommended files (metrics + adversarial reports) when served over HTTP.

### Start the dashboard server

Preferred: VS Code task **AI Brain: dashboard (bg)**.

CLI alternative:

```powershell
./.venv/Scripts/python.exe scripts/run_dashboard_server.py --port 8000 --bind 127.0.0.1
```

Then open:

- `http://127.0.0.1:8000/dashboard.html?autofetch=1&metrics=compare`

### Load recommended defaults

Use the dashboard button **Generate Compare Metrics + Load Defaults**.

Notes:
- This button calls a local endpoint (`POST /api/compare_flush`) on the dashboard server to generate `TemporaryQueue/metrics_compare.json`.
- It then loads defaults (metrics + `TemporaryQueue/adversarial_report_*.json`) and renders charts/tables.
- If you want **run** metrics instead of **compare**, change “Server mode metrics source” to “Run metrics (TemporaryQueue/metrics.json)” and click “Try Fetch Defaults (server mode)”.

Quick sanity checks to report in the assessment:
- What metrics file was loaded (run vs compare)?
- Are scenario tables populated (S1–S6 adversarial reports loaded)?
- Do escalation rows appear (S5/S2 typically) and are they explained?

Troubleshooting:
- If the Simple Browser shows a blank/white page, the server is likely not running. Confirm:
  - `http://127.0.0.1:8000/api/ping` returns `{ "ok": true, ... }`

---

## What “good performance” looks like (for this repo)

Given the eval harness and current architecture, “good” means:

- Eval suite passes (especially determinism suite).
- Cycle records are schema-valid and include `reason_chain` and decision signals.
- Policy/toggle results are explainable via `toggle_justifications`.
- The same content does not produce contradictory signals between modules.

---

## How to produce the task list after assessment

1. Add tasks to `temp_12.md` **before** implementing.
2. Prefer small, surgical changes.
3. After implementing, record:
   - what changed (files/symbols)
   - why
   - verification (eval output)

---

## Optional: deeper assessment

If you want the agent to do a deeper read, add a task to `temp_12.md` to:
- sample N recent cycles and compute summary stats
- review objective alignment + contradiction handling rates
- identify “signal mismatches” and propose refactors
