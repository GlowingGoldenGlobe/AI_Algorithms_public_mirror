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
