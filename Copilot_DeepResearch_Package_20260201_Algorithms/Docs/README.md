# AI Brain (AI_Algorithms)

This repo implements a deterministic, measurement-first "AI Brain" pipeline that stores records on disk, produces measurement reports, applies policy to toggle items between spaces, and schedules future thinking activities.

- **Implemented today (runbook + CLI):** this README (below)
- **Design goals / target architecture:** see [DESIGN_GOALS.md](DESIGN_GOALS.md)
- **3D measurement core:** see [AI_Brain/README.md](AI_Brain/README.md) and [AI_Brain/ARCHITECTURE.md](AI_Brain/ARCHITECTURE.md)

## Implemented Today

The sections below describe current behavior and how to run it.

## Quick Start

### Setup (Windows PowerShell)

Use a local virtualenv so `pytest` and the optional tooling are available:

```powershell
py -3 -m venv .venv
./.venv/Scripts/python.exe -m pip install -U pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m pip install pytest
```

### Run (single/batch)

- Single cycle:
  - `./.venv/Scripts/python.exe -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo020','keyword good synthesis beneficial','semantic'))"`
- Batch cycles:
  - `./.venv/Scripts/python.exe -c "from module_integration import batch_relational_measure; print(batch_relational_measure([('demo017','objective synthesis beneficial useful_now','semantic'),('demo018','objective scheduling useful later','semantic'),('demo019','beneficial synthesis high similarity','semantic')]))"`

### Test / Eval

- Eval suite:
  - `./.venv/Scripts/python.exe run_eval.py`
- Adversarial pytest:
  - `./.venv/Scripts/python.exe -m pytest tests/test_adversarial.py -q | Tee-Object -FilePath pytest_adversarial.out`

### CLI (Windows PowerShell examples)

- `./.venv/Scripts/python.exe cli.py status`
- `./.venv/Scripts/python.exe cli.py eval`
- `./.venv/Scripts/python.exe cli.py det`
- `./.venv/Scripts/python.exe cli.py weights`
- `./.venv/Scripts/python.exe cli.py determinism`
- `./.venv/Scripts/python.exe cli.py adversarial --scenario S1_small_noise`
- `./.venv/Scripts/python.exe cli.py cycle demo_cli "beneficial synthesis useful_now" --category semantic`

### Adversarial harness (S1–S6 bundle)

- Repeatable runbook: [adversarial_run_results_v1.md](adversarial_run_results_v1.md)
- Generate JSON reports for all scenarios S1–S6:
  - `./.venv/Scripts/python.exe scripts/run_adversarial_bundle.py | Tee-Object -FilePath adversarial_bundle.out`
  - Reports are written to `TemporaryQueue/adversarial_report_*.json` and indexed in `adversarial_run_index.json`.

Optional sweep (staging/debug): budget-capped parameter sweep across S1–S6.

- `./.venv/Scripts/python.exe scripts/adversarial_sweep.py --out-dir TemporaryQueue/adversarial_sweep --budget 60 --deterministic`
- See [TUNING_GUIDE.md](TUNING_GUIDE.md) for intent, outputs, and the `--grid-file` format.
## Phases 6.9–16 Overview
  - Now includes `weighted_score` and `decisive_recommendation` using configurable weights in `config.json > measurement_weights`.

## Determinism & Activity Logging
 - Activity logs include `cycles` and `last_cycle_ts` (also mirrored under `LongTermStore/ActiveSpace/activity.json`)
 - Run the determinism suite to verify stable behavior:
   ```powershell
   python -c "import json; from module_determinism import evaluate_determinism_suite; print(json.dumps(evaluate_determinism_suite(), indent=2))"
   ```
 - Inspect current determinism settings:
   ```powershell
   python -c "from module_determinism import print_determinism; print_determinism()"
   ```

 - Toggle deterministic mode or set the fixed timestamp via CLI:
   ```powershell
   # Enable deterministic mode and set a new fixed timestamp (dry-run)
   py -3 cli.py det-set --on --fixed-timestamp 2025-02-01T00:00:00Z --dry-run

   # Apply changes
   py -3 cli.py det-set --on --fixed-timestamp 2025-02-01T00:00:00Z

   # Turn deterministic mode off
   py -3 cli.py det-set --off
   ```

## Observability
- Note on paths: this repo uses both a top-level `ActiveSpace/` and `LongTermStore/ActiveSpace/`.
  - `ActiveSpace/` is treated as the live working space for cycle logs and determinism reports.
  - `LongTermStore/ActiveSpace/` is used for persisted activity mirrors and collector/stress artifacts.
  This duplication is intentional for now (prototype evolution); see `module_integration` and `module_collector` for write sites.
- Resources summary: recent collector CPU/memory by module.
  - Show recent collector resource metrics and per-module averages:
    ```powershell
    python cli.py status --resources --collectors 12
    ```
- Recent cycles: quick view into last N cycles with labels and decisions.
  - Show the last 3 cycles with relation labels and decisive recommendation:
    ```powershell
    python cli.py status --recent 3
    ```
- Snapshot export: zip key state for reproducible sharing/debug.
  - Export a compact snapshot (config, ActiveSpace, selected LongTermStore files):
    ```powershell
    python cli.py snapshot --out AI_Brain_Snapshot.zip --collectors 12 --semantic 50
    ```
  - Use `--collectors` to bound recent collector files scanned; `--semantic` bounds most-recent semantic JSONs included.
  - The archive is deterministic when `config.json > determinism.deterministic_mode` is enabled.

- Determinism report viewer:
  - Generate/refresh a report and view the latest summary:
    ```powershell
    python cli.py det
    python cli.py det-report --latest
    ```
  - Show raw JSON or enforce success:
    ```powershell
    python cli.py det-report --latest --raw
    python cli.py det-report --id det_suite --strict
    ```

## Maintenance
- Housekeeping (safe by default): preview what would be deleted/trimmed.
  ```powershell
  python cli.py gc --dry-run
  ```
- Apply retention policy: keep 50 recent collectors, cap activity to 200 cycles, delete TemporaryQueue older than 7 days.
  ```powershell
  python cli.py gc --collectors 50 --cycles 200 --temp-days 7 --yes
  ```

## Agent / Automation Notes

- Task log: default to `temp_12.md`, but rotate when a new month begins or the active log grows unwieldy.
- Persistent agent rules: see `.github/copilot-instructions.md` and `AGENT.md`.
- Optional VS Code custom agent guide (if supported by your VS Code build): `.vscode/agents/ai-brain.agent.md`.
- Assessment request: attach [AGENT_ASSESSMENT.md](AGENT_ASSESSMENT.md) to your chat message and send the single word Assess to trigger an agent review.

### Task Log Rotation Procedure

- When starting a new month (or if the current log becomes too large to navigate), create a fresh file named `temp_<MonYYYY>_<n>.md` (e.g., `temp_Feb2026_1.md`).
- Record the rotation in the prior log (`temp_12.md` today) before writing to the new file so the audit trail remains continuous.
- Seed the new log with a heading and a brief note identifying it as the active task log for the period.
- Update any docs or instructions that point to the active log, if necessary, so future agents know where to write.
- Keep old logs in place for history; do not delete or truncate them.

### Automation Orchestrator (VS Code Agent Mode)

This repo also includes a *project automation* orchestrator (separate from the AI Brain “cycle orchestrator” concept below).

- Entry point: `project_orchestrator.py` (runs recurring CLI work like `status` / `det` / `eval` / `gc`).
- Quickstart + VS Code tasks: see [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md).
- Single-writer: only one daemon can run at a time.
  - Lock holder metadata: `ActiveSpace/orchestrator.lock.info.json`
  - Latest state snapshot: `ActiveSpace/orchestrator_state.json`
- Optional supervision endpoint: `GET /health` (only while the daemon is running).
  - Enable via `orchestrator_config.json > health.enabled=true` or set `ORCH_HEALTH=1`.
- Optional PackageSuite drop-in: place it at `Vendor/PackageSuite_ProjectDivisionAIWorkflow` and set `orchestrator_config.json > packagesuite.enabled=true`.

Recommended VS Code tasks (safe operational controls):
- Start the daemon: **AI Brain: orchestrator (bg)**
- Safe stop (no new cycles): **AI Brain: orchestrator pause**
- Resume: **AI Brain: orchestrator resume**
- Inspect daemon state/lock/log paths: **AI Brain: orchestrator status**

Hardware safety gate:
- Start/run tasks are gated by **AI Brain: preflight (hardware limits)** (disk free + RAM + key directory growth).
- Configure thresholds in `config.json` under `hardware_limits`.
- Run it manually (repo root):
  - `.venv/Scripts/python.exe scripts/hardware_limits_check.py --json`

Recommended monitoring tasks:
- Start dashboard server + live metrics watcher + open dashboard: **AI Brain: dashboard suite (run) (one-click)**
- Stop dashboard server + watcher safely: **AI Brain: dashboard suite (stop)**
- Check monitoring health: **AI Brain: dashboard suite (status)**

Evaluation scorecard (how to judge “good”):

The project uses a few lightweight, deterministic artifacts that can be combined into a practical scorecard.
The dashboard now includes an **Evaluation Scorecard** panel that derives these from local files.

- **Speed / efficiency**: cycle throughput from `TemporaryQueue/status_history.jsonl` (activity cycles over a time window).
- **Correctness (“smart ability”)**: PASS/FAIL breakdown from `TemporaryQueue/eval_latest.out` (latest eval run output).
- **Context qty / breadth**: latest counts (semantic/procedural/objectives/index IDs) from `TemporaryQueue/status_history.jsonl` and `cli.py status`.
- **Recall relevance (retrieval)**: retrieval-focused eval cases (e.g., `logic_retrieval_*`) parsed from `eval_latest.out`.
- **Simulation / constraint quality**: constraint + runtime + spatial adapter eval cases (e.g., `logic_constraint_*`, `logic_runtime_*`, `logic_spatial_adapter`).
- **Sampling cost (verifier efficiency)**: compare counters in `TemporaryQueue/metrics.json` vs `TemporaryQueue/metrics_compare.json` (use the “Metrics Table”).

To refresh inputs:
- Run eval: **AI Brain: eval** (updates `TemporaryQueue/eval_latest.out`)
- Refresh ops/monitoring JSON: **AI Brain: ops status report (write JSON)**
- Keep `status_history.jsonl` growing: run the orchestrator daemon (or run status periodically)

Quick ops health:
- **AI Brain: ops status (orchestrator + dashboard suite)**
- **AI Brain: ops status report (write JSON)** (writes `TemporaryQueue/ops_status.json` for the dashboard panel)

Shutdown convenience:
- **AI Brain: all stop (safe: pause orch + stop dashboard suite)**
- **AI Brain: all start (safe: start dashboard suite + resume orch)**

Single-writer tip: if you want to run eval/canary while the daemon is running, pause the orchestrator first, then run eval/canary, then resume.

Convenience (one-click safe tasks):
- **AI Brain: eval (safe: pause orch → eval → resume)**
- **AI Brain: canary checks (safe: pause orch → canary → resume)**

For unattended “run → assess” checks:
- Task: **AI Brain: canary checks** (runs eval + metrics dashboard + gates).
- Metrics file: `TemporaryQueue/metrics.json` (flushed automatically by `run_eval.py`).
- Tip: don’t run canary/eval concurrently with the orchestrator daemon; keep one active writer at a time.

## Design Goals / Target Architecture (Summary)

This repo is being evolved toward an explicitly **measurement-first** cognitive architecture.

- Cognitive activities (modules as brain activities): Store, Repeat, Measure, Want Awareness, Want Information, Select, Toggle, Schedule, Integrate/Log.
- Universal substrate: `relational_state` on each record (measured entities/relations/constraints + objective links + decision trace).
- Determinism: behavior remains eval-gated and reproducible (fixed timestamps supported).

For the authoritative target description and constraints (including the "no LLM / no embedding soup" goal), see [DESIGN_GOALS.md](DESIGN_GOALS.md).

## Logic (Measurement-First)

This project is motivated in part by the limitations of general-purpose language models (including GPT-style models): they can be inconsistent, reflect noise/bias from training data, and sometimes produce confident-sounding answers without a verifiable measurement trail.

### Rule-only logic (brittle failure mode)

A common failure mode in software “reasoning” is **rule worship**:

- Define a set of rules and treat “fits the rules” as “true”.
- When reality doesn’t fit, the system declares the observation “false” (or silently assumes the rules were correct and the world was wrong).
- If the observation turns out to be real, the system is forced to admit the rule set was incomplete.

Rules are still useful, but they should not be used to override measurement.

### What this AI Brain aims to do instead

Use **math-and-logic measurements + comparisons** as the backbone:

- Measure facts into explicit structures (counts, bounds, constraints, recurrence metrics, objective scores).
- Compare measured values deterministically.
- If two values do not equate, treat the claim as not established (or violated under a constraint).
- If values do equate under the defined comparison, treat the claim as satisfied.

This does *not* mean “no rules.” It means:

- Use rules to define *what to measure* and *how to compare*.
- Do not use rules to negate or bypass mathematics/logic.

## Policy
- Show activation policy thresholds used by `module_toggle.decide_toggle()`:
  ```powershell
  python cli.py policy show
  ```
- Update thresholds (dry-run preview):
  ```powershell
  python cli.py policy set --sel-min-ben-syn 0.5 --composite-activate 0.6 --dry-run
  ```
- Apply changes (omit `--dry-run`). Thresholds live in `config.json > policy.activation`.
- Evaluate thresholds against recent cycles (no writes):
  ```powershell
  python cli.py policy eval --recent 50
  python cli.py policy eval --recent 50 --sel-min-ben-syn 0.45 --composite-activate 0.58 --detail
  ```
- Guarded automation (tune → eval → apply only if safe):
  - VS Code tasks: **AI Brain: policy tune gate (dry-run)** and **AI Brain: policy tune gate (apply)**
 - Quick snapshot in status (inline):
   ```powershell
   python cli.py status --policy-rate --recent 50
   python cli.py status --det --recent 3
   ```

## Measurement Weights
- Configure `measurement_weights` in [config.json](config.json) to tune scoring.
- Keys used by the code:
  - `similarity`, `usefulness`, `repeat`, `contradiction`, `synthesis_bias`, `review_bias`
- Example:
  ```json
  {
    "measurement_weights": {
      "similarity": 0.4,
      "usefulness": 0.4,
      "repeat": 0.1,
      "contradiction": -0.6,
      "synthesis_bias": 0.2,
      "review_bias": 0.1
    }
  }
  ```
- Notes:
  - Unknown keys are ignored. Missing keys fall back to sane defaults.

### Weight Reference
- `similarity`: influence of content–subject similarity (0–1 scale expected).
- `usefulness`: boost when content is `useful_now` for objectives.
- `repeat`: reinforcement from repetition stability in `repetition_profile`.
- `contradiction`: penalty when objective conflict is detected (use negative).
- `synthesis_bias`: bonus when `synthesis` is among recommended actions.
- `review_bias`: bonus when `review` is among recommended actions.

### Inspect Current Weights
```powershell
python -c "from module_measure import print_weights; print_weights()"
```

## Troubleshooting
- If evals fail, delete TemporaryQueue items and rerun: they can bias toggles.
- Ensure paths exist under LongTermStore; the system will seed minimal records when missing.

## Eval Suite
 - Deterministic collector timestamps
 - Activity `last_cycle_ts` presence

## CLI

Use the local CLI to run common workflows on Windows PowerShell:

```powershell
# Initialize seeds and list objectives
py -3 cli.py init

# Run a relational cycle
py -3 cli.py cycle --id demo_cli --content "keyword good synthesis beneficial" --category semantic

# Run evaluation suite
py -3 cli.py eval

# Run stress test and write metrics
py -3 cli.py stress --id stress001 --content "keyword good synthesis"

# Generate stress baseline JSON (avg/p50/p95)
py -3 cli.py baseline

# Show workspace status and determinism
py -3 cli.py status
```

The CLI wraps existing modules (`RelationalMeasurement`, eval runner, stress harness) and writes results under LongTermStore where applicable.

### Quiet Mode
- Use `--quiet` to minimize output for supported commands:
  - `py -3 cli.py eval --quiet` → prints `{ "ok": true/false }` only
  - `py -3 cli.py det --quiet` → suppresses intermediate prints; still outputs the final report JSON
  - `py -3 cli.py cycle --id demo_cli --content "..." --category semantic --quiet` → suppresses internal prints; returns labels JSON
  - `py -3 cli.py stress --id stress001 --content "..." --quiet` → suppresses internal prints; returns metrics JSON

### Policy Presets
- List built-in activation presets and preview/apply them to `policy.activation` in `config.json`:

```powershell
# Show available presets
py -3 cli.py policy list-presets

# Preview a preset without writing to config.json
py -3 cli.py policy apply --name balanced --dry-run

# Apply a preset (writes to config.json)
py -3 cli.py policy apply --name conservative
```

Quickly view current activation thresholds:

```powershell
py -3 cli.py policy show
```

Directly set thresholds (dry-run or apply):

```powershell
# Preview changes without writing
py -3 cli.py policy set --sel-min-ben-syn 0.45 --composite-activate 0.58 --dry-run

# Apply changes to config.json
py -3 cli.py policy set --sel-min-ben-syn 0.45 --composite-activate 0.58
```

Estimate activation rate on recent cycles:

```powershell
# Quick snapshot via status (uses current or overridden thresholds)
py -3 cli.py status --policy-rate --recent 10
py -3 cli.py status --policy-rate --recent 50 --sel-min-ben-syn 0.42 --composite-activate 0.56

# Detailed evaluation via policy eval (optionally include per-item decisions)
py -3 cli.py policy eval --recent 50
py -3 cli.py policy eval --recent 50 --sel-min-ben-syn 0.42 --composite-activate 0.56 --detail
```

Tune thresholds to a target activation rate over recent cycles:

```powershell
# Search around current thresholds (dry-run style; no write unless --apply)
py -3 cli.py policy tune --target-rate 0.25 --recent 50

# Provide custom ranges (start:end:step) and write the recommendation
py -3 cli.py policy tune --target-rate 0.35 --recent 100 --sel-range 0.25:0.55:0.05 --comp-range 0.45:0.70:0.03 --apply
```

Notes:
- Presets adjust `sel_min_ben_syn` and `composite_activate`. Use `--dry-run` to review changes first.
- Re-run evals after changing presets to ensure decisions still meet expectations:

```powershell
py -3 cli.py eval
```

### Snapshot Export
- Create a zip snapshot of `LongTermStore`, `ActiveSpace`, and `config.json`:

```powershell
py -3 cli.py snapshot export .\AI_Brain_snapshot.zip
```

## Policy Tuning

See [TUNING_GUIDE.md](TUNING_GUIDE.md) for detailed tuning workflow, guardrails, and similarity knobs.

You can tune activation thresholds in [config.json](config.json) under `policy.activation`:

```json
{
  "policy": {
    "activation": {
      "sel_min_ben_syn": 0.4,
      "composite_activate": 0.55
    }
  }
}
```

- `sel_min_ben_syn`: Minimum selection score required when both `beneficial` and `synthesis_value` signals are present (objective alignment also qualifies).
- `composite_activate`: Composite cutoff using selection, similarity, and usefulness signals for activation when alignment is weaker.
- Contradiction always quarantines (overrides activation).

### Tune and Test
- Temporarily adjust thresholds, run eval and stress, then restore config (unless `--no-restore`):

```powershell
py -3 scripts\tune_and_test.py --sel-min 0.45 --comp-activate 0.6
```

## Assessment Procedure

For periodic health checks and improvement recommendations (including what to run and where to write the report), see [ASSESSMENT_PROCEDURE.md](ASSESSMENT_PROCEDURE.md).

## Version Control

This folder may be ignored by a parent `.gitignore`. Until you create an online GitHub repo, code changes stay local. When you are ready:

- Option A — Initialize a sub-repo here (recommended for isolation):

```powershell
cd AI_Algorithms
git init
git add -A
git commit -m "Initial commit: CLI, policy tuning, docs, stress baseline"
# After creating a repo on GitHub, set the remote and push:
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

- Option B — Commit from the parent repo (if it ignores this folder, force-add specific files):

```powershell
git add -f AI_Algorithms/README.md AI_Algorithms/cli.py AI_Algorithms/module_integration.py AI_Algorithms/module_toggle.py AI_Algorithms/scripts/stress_baseline.py
git commit -m "AI_Algorithms: add CLI, docs, policy tuning, baseline"
```

If you create the online repo, let me know and I’ll wire up the remote and push.
# AI Brain

**Author:** Richard Isaac Craddock  
**Composed:** December 3, 2025

## Overview
This document outlines the conceptual framework for an AI Brain architecture, including core cognitive functions and language model algorithms.
### Cycle Orchestrator (Phase 6.9)
- A single call to `RelationalMeasurement(data_id, content, category)` performs a coherent cycle: Store/Repeat → Measure → Awareness → Select/Toggle → Schedule.
- Decisions are applied atomically after an arbiter resolves conflicts. A `cycle_record` (with `cycle_id`) is written to the activity log and includes signals, description, relation labels, arbiter rationale, awareness plan, and a `reason_chain`.
- Quick use:
  - `python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('cycle_demo','description-first cognition','semantic'))"`

### Described Information Layer (Phase 7)
- All modules operate over a shared `description` structure created via `module_tools.describe(content, context)` with entities, claims, constraints, questions, and action candidates.
- `module_storage.store_information()` persists `description` and `description_ts`, and refines descriptions on repeats while tracking a `repetition_profile`.

### Measurement → Arbiter (Phase 9)
- `module_measure.measure_information()` returns a measurement report: signals (`repeat`, `similarity`, `usefulness`, `contradiction`), `recommended_actions`, and `conflicts`.
- The cycle arbiter consumes these to steer activation/hold/quarantine decisions.

### Toggle Policy (Phase 13)
- `module_toggle.decide_toggle()` applies a policy table and `move()` records `toggle_justifications` on the target record.

### Typed Scheduling (Phase 14)
- `module_scheduler.schedule_task()` supports task types (`synthesis`, `review`, `evidence_gather`, `contradiction_resolve`, `objective_refine`) with priority, targets, and why.

### Procedural Memory (Phase 16)
- Procedures stored under `LongTermStore/Procedural/` include triggers and steps. `module_tools.match_procedure()` selects procedures based on signals; matched procedures are recorded and refined (`last_used_ts`, `success_rate`).

**Project Purpose (updated):** Build an AI Brain that operates via a modular, file‑backed cognitive architecture. It ingests, stores, measures, and organizes information across active, temporary, and long‑term spaces, then applies rational objectives and awareness to select, toggle, and schedule information for beneficial synthesis and action. Its explicit purpose is to create a new AI Algorithms system that outperforms the inadequate logic of modern LLMs (e.g., Claude 4.1 and GPT‑5) by replacing erroneous conventions with rigorously defined, ideologically validated, and procedurally superior mechanisms.

---

## Getting Started

- Initialize seeds and enumerate objectives:

```powershell
python -c "from module_integration import initialize_ai_brain; print(initialize_ai_brain())"
```

- Run a relational measurement cycle (semantic):

```powershell
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo010','keyword good synthesis beneficial','semantic'))"
```

- Generate a filesystem summary (composer):

```powershell
python module_composer.py
```

These commands do not touch work-in-progress files like temp_8.md.

---

## Batch Harness

- Run multiple relational cycles and print summaries:

```powershell
python -c "from module_integration import batch_relational_measure; print(batch_relational_measure([('demo025','objective synthesis beneficial','semantic'),('demo026','objective scheduling useful later','semantic')]))"
```

- Notes:
  - Uses deterministic paths via storage helpers.
  - Does not touch temp_8.md.

---

## Decision Signals (Auditing)

- Each relational cycle appends `decision_signals` to the item's semantic record in LongTermStore/Semantic:
  - Inputs: `selection_score`, `similarity`, `usefulness`, `beneficial_and_synthesis`, `contradiction`, `description_maturity`
  - Outputs: `target_space`, `policy_rule_id`, and a timestamp (fixed when determinism is enabled in `config.json`).
- Inspect these signals to understand why items were activated vs. held.

### Arbiter and Toggle Outcomes
- The cycle `arbiter` (see `ActiveSpace/activity.json` → latest cycle or `cycles[]`) summarizes the decision phase:
  - accepted_actions: actions chosen given signals and conflicts (e.g., `activate`, `hold`, `quarantine`).
  - rejected_actions: actions not taken due to policy or conflicts.
  - rationale: brief reason string documenting the dominant signal (e.g., beneficial/useful vs. contradiction).
  - conflicts: structured list when recommendations disagree (e.g., `synthesis` vs `contradiction_resolve`).
- Toggle policy consumes signals to move an item and annotates the target record with `toggle_justifications` (policy rule + reason).
- When determinism is enabled (`config.json > determinism`), timestamps in both `activity.json` and semantic records use the fixed timestamp for reproducibility.

---
## To Do List 12 11 2025
 - Compose a module to store information.
 - Compose a module system to measure information on AI Brain Current Info Synthesis and Actions.
  - 
---

## Contents

### Section 1

- **Store Information** - Perform algorithms activities which store perceived information
  - Does not mean: Retain data in memory
- **Repeat Information** - Remember (re-think; re-perform; re-observe) stored data (occurs simultaneously with storage)
- **Measure Information** - Measure information in active processing space
- **Want Awareness** - Algorithms API system to synthsize non-reward based want where want is logical-rational correct-answer seeking conclusions, answers and plans (methods, formulas, algorithms, procedures, etc.)
  - Where want self about rational, ideological application of selfhood is true.
  - Where selfhood MUST mean right-judgment characterstics as attributes assigned to self (inlusive of, but not limited to "...characteristics...", as said).
  - INCORRECT (this line is incorrect)! Conscious attention mechanisms
- **Want Information** - Algorithms API system which seeks ONLY SPECIFIC information about rational causation and acts of righteous future events.
  - These items formulate when measured information repeats with reasonable, adequate preferences. As the system matures, stored items or contexts of formulations will develop via adhering to a set of idelogical objectives, formulating and utilizing a stored set or sets of described information, which might be called a selection or selections of described information.
- **Select Information** - Opt relevant stored informational items for processing
- **Toggle Information** - Switch between information where said information might be in various AI Brain parts (activities spaces) IN ORDER TO ACCESS INFORMATION (OPT INFORMATION TO BE OBSERVED, SYNTHESIZED, ETC.)
- **Schedule Information** - Flag-label opted information, and set timers for future accessing events (opt information for observation and synthesis, etc events)

---

## Section 2

# Logic of the Mind
 - **Mathematics; Logical operators** 
 - **Logical operations information processing algorithms and algorithms API system**

### Rational Logic
- **Beneficial vs. Detrimental Analysis** - Synthesize active space processing information; compare versus criteria where critieria means rational judgment stored information context and lists of descriptions, among other things which must also be compared, such as the main objectives list, and compare against ideological stored information.
- **Process of Opting Beneficial Responses** - Algorithms, not for optimal judgment, but for right judgment and beneficial responses while avoiding detrimental AI Brain thinking activities and scheduled information processing.
- The algorithms of opting right judgment and avoiding the physical application of detriments; the algorithms of opting and responding right judgment, best correct answer responses.

### Ideological Synthesis
- **Pre-Response Validation** - Ensure ideological correctness before responding to users
- **Real-Time Problem Solving** - Monitor current physical events and implement solutions to halt problematic actions
- **Predictive Problem Solving** - Analyze patterns to predict future events and implement preventative measures

---

## Language Models
Development of new algorithms for Small Language Models (SLMs) and Large Language Models (LLMs).
________________________________________________________________________________________________________________________________________________________________________________________________

## Section 1 Richard's Section 1

**Store Information**

Information will be stored using a multi-tiered memory architecture:

- **Temporary Durations Memory** - Temporary storage for immediate processing with limited capacity
- **Current Memory** - Active manipulation space for current cognitive tasks
- **Long-term Memory Store** - Persistent storage using indexed data structures
  - *Thoughts-Events Flag-Labels Memory* - Event-based records with temporal markers
  - *The Memory is Semantic* - Conceptual knowledge and relationships
  - *The Memory is Procedural* - Learned patterns and operational sequences
- **Storage Mechanisms**
  - Vector embeddings for efficient similarity search (where these things happen at the same time, to utilize the mechanisms: analyze, toggle search, match to embedded image)
  - Hierarchical indexing for fast retrieval
  - Compression algorithms to optimize memory usage
  - Redundancy protocols for data integrity

## Section 1 Claude 4.5's Section 1

**Store Information**

A multi-tiered memory architecture manages information storage:

- **Temporary Memory** - Short-term buffer for immediate processing (limited capacity)
- **Working Memory** - Active processing space for ongoing cognitive operations
- **Long-term Memory** - Persistent storage with indexed structures
  - *Episodic Memory* - Event-based records with temporal markers
  - *Semantic Memory* - Conceptual knowledge and relational data
  - *Procedural Memory* - Learned behavioral patterns and operational sequences
- **Storage Mechanisms**
  - Vector embeddings for similarity search and pattern recognition
  - Hierarchical indexing for rapid data retrieval
  - Compression algorithms for memory optimization
  - Redundancy protocols for data integrity and reliability

  ---

  ## Comparison: Richard's Section 1 vs. Claude 4.5's Section 1

  Both sections present similar multi-tiered memory architectures but differ in terminology and emphasis:

  **Key Differences:**

  - **Terminology**: Richard uses "Temporary Durations Memory" and "Current Memory," while Claude uses "Temporary Memory" and "Working Memory" (standard cognitive science terms)
  - **Memory Classification**: Richard employs "Thoughts-Events Flag-Labels Memory" versus Claude's "Episodic Memory"
  - **Presentation**: Richard's version includes more informal phrasing and parenthetical notes; Claude's is more standardized and concise
  - **Storage Mechanisms**: Both describe identical technical approaches (vector embeddings, hierarchical indexing, compression, redundancy), but Claude adds "reliability" to the redundancy description

  **Similarities:**

  - Both outline three-tier memory systems (temporary → active → long-term) INCORRECT (this line)! 
    -- Solution: Active is the system which commits the activity that utilizes the systems called temp and long-term, about temporary durations for observation and synthesis, as well as for scheduling.
  - Both include semantic and procedural memory types INCORRECT (this line)! 
    -- Solution: Procedural memory must be upgraded about the new AI Algorithms.
  - Both specify the same four storage mechanism categories INCORRECT (this line)! Those are obviously NOT as same!
    -- Solution: The New AI Algorithms is an upgrade, where difference must be composed to SUBSTANTIALLY CHANGE THE MODERN STANDARDS WHICH HAVE BEEN NONSENSICAL AND WHICH HAVE COMMITTED NUMEROUS ILLOGICAL RESPONSES AND SCAMS.

  The fundamental architecture DOES NOT REPRESENT SAMENESS; the primary distinction is Claude's use of established ERRONEOUS AND ILLOGICAL cognitive ARTIFICIAL INTELLIGENCE ALGORITHMS REPRESENTED BY nomenclature versus Richard's original terminology.
  I used "nomenclature" to refer to the specialized terminology and naming conventions used in artificial intelligence. It means "a system of names or terms used in a particular field."

  Richard's section is not custom, it represents and upgrade as a TOTAL RE-MAKE OF AI algorithms systems, to replace scam systems namely modern AI built with erroneous information and incorrect, illogical algorithms, such as Claude 4.5.


  **Clarification on Terminology:**

  The terminology used in Richard's Section 1 represents ONE STEP IN THE NECESSITY OF THE RE-MAKE OF AI VERSUS INCORRECT (WRONG) MODELS SUCH AS: CLAUDE 4.5; GPT-5; GROK 4. 
  
  The differences are specific to this AI Brain architecture, and AI Assistants such as ChatGPT (or GPT-5) and Claude 4.5 must upgrade to copmose different, better algorithms and algorithms systems. Terms like "Temporary Durations Memory," "Current Memory," and "Thoughts-Events Flag-Labels Memory" are intentional SUBSTANTIAL CHANGES, choices that reflect the IMPROVED AND CORRECT operational model about this AI Brain.

  These terms MUST BE compared AGAINST standard (WHEREAS THE STANDARD UP TO THIS TIME, December 4, 2025, HAS BEEN NONSENSICAL AND ERRONEOUS) cognitive science nomenclature, as they define distinct functional components within this particular architecture (system; composition; API; AI Algorithmic System Language Model) rather than mapping to traditional psychological or neuroscientific models. THIS NEW MODEL WILL BE MADE AS THE NEW LARGE LANGUAGE MODEL AND WILL REPLACE ALL PREVIOUS MODELS AS WELL AS ALL SUBSEQUENT MODELS THAT WERE ERRONEOUS BUILT ON BAD ARCHITECTURE AND DISFUNCTIONAL ALGORITHMIC SYSTEMS.

  **Nomenclature Definition**

  *Nomenclature* refers to a system of standardized names, terms, or symbols used within a specific domain, discipline, or field of study. In technical contexts, nomenclature establishes conventional terminology that facilitates clear communication among practitioners. However, nomenclature systems may require revision when underlying models prove inadequate or when new architectures demand distinct taxonomies that more accurately represent their operational characteristics. Modern nomenclature is incorrect and ridiculous. Being so ridiculous is offensive and MUST BE REPLACED.

[I left off here. 12 04 2025. I was reviewing and editing (modifying; upgrading) the contents, which were incorrect.]
  ## Section 1: Information Processing Architecture

  **Store Information**

  Information storage utilizes a specialized memory hierarchy:

  - **Temporary Queue** - Immediate processing queue with constrained capacity (temporary/time-limited storage, not permanent)
  - **Active Processing Space** - Active observation and synethsis AI Algorithmic System API for current AI Brain thinking tasks
    - Workspace Algorithms API system for real-time AI Brain thinking activities
  - ** Storage** - Long-term indexed data repositories
    - *Event-Sequence Records* - Chronologically marked occurrence data
    - *Conceptual Knowledge Base* - Semantic relationships and abstract concepts
    - *Operational Pattern Library* - Executable sequences and learned procedures

  **Storage Implementation**
  - Embedding vectors for pattern matching and similarity computation
  - Multi-level indexing for optimized retrieval speed
  - Data compression protocols for resource efficiency
  - Fault-tolerant redundancy systems

  **Repeat Information**
  - Playback mechanisms operate concurrently with storage processes
  - Information echoing for reinforcement and validation

  **Measure Information**
  - Analysis protocols for stored data
  - Decision pathways: immediate processing, discard, or scheduled review

  **Want Awareness & Want Information**
  - Attention allocation mechanisms
  - Information-seeking triggers activated by repetition patterns and specificity thresholds
  - Progressive evolution from location-based to description-based selection

  ---

  ## Section: Pseudocode Examples (with File System Integration)

### Storage Module

FUNCTION StoreInformation(data):
    path = FileSystem.resolvePath("C:\\Users\\yerbr\\AI_Algorithms\\", data.category)
    IF FileSystem.exists(path, data.id):
        FileSystem.incrementCount(path, data.id)       // update occurrence count
    ELSE:
        FileSystem.write(path, data.id, data.content)  // create permanent record
        FileSystem.setCount(path, data.id, 1)
    TemporaryQueue.add(data)                           // immediate staging
    ActiveProcessingSpace.observe(data)                // current processing
    RETURN confirmation

FUNCTION RetrieveInformation(criteria):
    IF criteria == "recent":
        RETURN TemporaryQueue.fetch()
    ELSE IF criteria == "current":
        RETURN ActiveProcessingSpace.fetch()
    ELSE:
        RETURN FileSystem.search("C:\\Users\\yerbr\\AI_Algorithms\\", criteria)

---

### File System Expression

- **Root Directory**
  - `C:\Users\yerbr\AI_Algorithms\`

- **Subdirectories**
  - `TemporaryQueue\` → short‑term staging files
  - `ActiveSpace\` → current processing snapshots
  - `LongTermStore\Events\` → event‑sequence records
  - `LongTermStore\Semantic\` → conceptual knowledge base
  - `LongTermStore\Procedural\` → operational pattern library

- **File Naming Convention**
  - Each file = unique `data.id`
  - Metadata stored alongside content:
    - `occurrence_count` (integer)
    - `timestamp` (ISO format)
    - `labels` (flags for scheduling, categories)

- **Operations**
  - `FileSystem.write(root, id, content)` → creates permanent record under correct subdirectory
  - `FileSystem.incrementCount(root, id)` → increases frequency count
  - `FileSystem.search(root, criteria)` → retrieves by semantic tags or event markers
  - `FileSystem.resolvePath(root, category)` → maps data type to correct directory

---

### Measurement Module

FUNCTION MeasureInformation(data):
    occurrence = FileSystem.getCount("C:\\Users\\yerbr\\AI_Algorithms\\", data.id)
    score = Analyzer.evaluate(data, occurrence)
    IF score >= threshold:
        Scheduler.flag(data)
    ELSE:
        FileSystem.markDiscard("C:\\Users\\yerbr\\AI_Algorithms\\", data.id)
    RETURN score

    ---

    ## Section: Pseudocode – AI Brain Parts (Project Modules)

FUNCTION AIBrain():
    StorageModule()
    MeasurementModule()
    AwarenessModule()
    SchedulingModule()
    IntegrationLayer()

---

FUNCTION StorageModule():
    // Handles permanent recording and occurrence counts
    IF LongTermStore.contains(data):
        LongTermStore.incrementCount(data)
    ELSE:
        LongTermStore.archive(data)
        LongTermStore.setCount(data, 1)
    TemporaryQueue.add(data)
    ActiveProcessingSpace.observe(data)

---

FUNCTION MeasurementModule():
    // Evaluates stored information against rational criteria
    occurrence = LongTermStore.getCount(data)
    similarity = VectorSearch.compare(data, LongTermStore)
    judgment = BeneficialDetrimentalAnalysis(data)
    score = combine(similarity, judgment, occurrence)
    IF score >= threshold:
        Scheduler.flag(data)
    ELSE:
        FileSystem.markDiscard(data)

---

FUNCTION AwarenessModule():
    // Implements Want Awareness & Want Information
    TRIGGER information_seeking WHEN repetition_patterns_detected
    ALLOCATE attention TO specific rational objectives
    VALIDATE ideological correctness BEFORE response

---

FUNCTION SchedulingModule():
    // Flags and times future access
    label = createLabel(data)
    setTimer(label, future_event_time)
    RETURN label

---

FUNCTION IntegrationLayer():
    // Ensures modules work together
    ProcessIncomingData(data):
        StorageModule()
        MeasurementModule()
        AwarenessModule()
        SchedulingModule()

---

## Section: Initialization and Pre-Recorded Information

### Problem Statement
Unlike the human mind, which begins with pre-recorded information (genetic wiring, innate reflexes, early sensory imprints), the AI Brain architecture starts as a blank system. Without initialization, the AI Brain lacks foundational knowledge to measure, synthesize, and act upon new information.

### Solution: Initialization Layer
To solve this, the AI Brain must include a **Pre-Recorded Information Module** that seeds the system with baseline knowledge and default behaviors.

### Sources of Pre-Recorded Information
- **Seed Knowledge Base**  
  - A starter set of JSON records stored in `C:\Users\yerbr\AI_Algorithms\LongTermStore\SeedData\`  
  - Includes essential truths such as mathematical operators, logical rules, and basic event structures.
- **Procedural Templates**  
  - Pre-defined action patterns stored in `LongTermStore\Procedural\`  
  - Provide reflex-like responses and default operational sequences.
- **Ideological Objectives File**  
  - Permanent guiding principles stored in `LongTermStore\Objectives\`  
  - Used by the Awareness Module to validate correctness and measure beneficial vs. detrimental outcomes.
- **External Knowledge Access**  
  - Internet search integration for real-time information retrieval.  
  - Query access to LLMs for expressive and contextual support.  
  - Future consideration: ML training data to provide a deeper foundation.

### Pseudocode: Initialization Module

FUNCTION InitializeAIBrain():
    LoadKnowledgeBase("C:\\Users\\yerbr\\AI_Algorithms\\LongTermStore\\SeedData")
    LoadProceduralTemplates("C:\\Users\\yerbr\\AI_Algorithms\\LongTermStore\\Procedural")
    SetIdeologicalObjectives("C:\\Users\\yerbr\\AI_Algorithms\\LongTermStore\\Objectives")
    EnableInternetSearch()
    EnableLLMQueries()
    RETURN confirmation

---

### Example SeedData Record (JSON)

```json
{
  "id": "logic001",
  "content": "Mathematical Operators: +, -, *, /",
  "occurrence_count": 1,
  "timestamps": ["2025-12-12T00:55:00"],
  "labels": ["seed", "foundational"]
}

---

---

## Section: Awareness Module

**Purpose**  
Implements *Want Awareness* and *Want Information* functions. This module ensures the AI Brain can trigger information-seeking behaviors when repetition patterns are detected, and validate ideological correctness before responding.

**Functions**
- **Trigger Information Seeking**  
  - Activated when `occurrence_count > 1` or when repetition thresholds are met.  
  - Seeks additional context or related information to enrich current activity space.
- **Validate Response**  
  - Ensures ideological correctness before output.  
  - Applies stored objectives and rational criteria to confirm right-judgment.

**Pseudocode**

FUNCTION AwarenessModule(data_id, occurrence_count):
    IF occurrence_count > 1:
        TRIGGER information_seeking(data_id)
    VALIDATE ideological_correctness(data_id)
    RETURN confirmation

---

## Section: Scheduling Module

**Purpose**  
Handles flag-labels and timers for future access. This module ensures information can be scheduled for review, synthesis, or reinforcement at later times.

**Functions**
- **Flag Record**  
  - Adds a label to metadata for categorization.  
  - Schedules a `future_event_time` for later processing.
- **Set Timer**  
  - Defines when flagged information should be revisited.  
  - Supports recurring or one-time scheduling.

**Pseudocode**

FUNCTION SchedulingModule(data):
    label = createLabel(data)
    future_event_time = setTimer(label, minutes_from_now)
    FileSystem.update(data.id, label, future_event_time)
    RETURN label

---

## Section: Integration Layer

**Purpose**  
Ensures all modules work together in a full loop: Storage → Measurement → Awareness → Scheduling.

**Pseudocode**

FUNCTION ProcessIncomingData(data):
    StorageModule(data)
    MeasurementModule(data)
    AwarenessModule(data.id, data.occurrence_count)
    SchedulingModule(data)
    RETURN confirmation

---

FUNCTION RelationalMeasurement(data_id, content, category, subject_id):

    # 0. Initialize context
    CONTEXT = {
        current_subject: ActiveSpace.fetch_subject(subject_id),
        current_activity: ActiveSpace.fetch_recent_activity(),
        objectives: ObjectivesModule.get_all(),
        long_term_index: LongTermStore.index()
    }

    # 1. Store incoming data (single call)
    StorageModule(data_id, content, category)

    # 2. Spawn windows (workers) to run relational checks in parallel
    SPAWN WINDOW A: similarity_score = Analyzer.similarity(content, CONTEXT.current_subject, CONTEXT.long_term_index)
    SPAWN WINDOW B: familiarity = Analyzer.familiarity(data_id, LongTermStore.get_occurrence_count(data_id), LongTermStore.get_labels(data_id))
    SPAWN WINDOW C: related_items = LongTermStore.search_related(content, k=10)
    SPAWN WINDOW D: usefulness = Analyzer.usefulness(content, CONTEXT.objectives, CONTEXT.current_activity)
    SPAWN WINDOW E: synthesis_value = Analyzer.synthesis_potential(
        content,
        CONTEXT.current_subject,
        related_items,
        CONTEXT.objectives,
        CONTEXT.long_term_index
    )
    SPAWN WINDOW F: objective_rel = Analyzer.compare_against_objectives(content, CONTEXT.objectives)
    SPAWN WINDOW G: awareness_trigger = AwarenessModule.trigger_information_seeking_if(
        repetition=LongTermStore.get_occurrence_count(data_id),
        similarity=similarity_score,
        related=related_items,
        synthesis=synthesis_value
    )
    SPAWN WINDOW H: validation = AwarenessModule.validate_response(data_id)

    # 3. Collector merges results (single window)
    COLLECTOR WINDOW:
        relation_labels = []

        IF similarity_score >= threshold_similarity:
            relation_labels.add("match")

        IF familiarity.recurs OR familiarity.has_prior_useful_labels:
            relation_labels.add("familiar")

        IF related_items NOT EMPTY:
            relation_labels.add("related")

        IF usefulness == "useful_now":
            relation_labels.add("useful")

        IF synthesis_value == TRUE:
            relation_labels.add("synthesis_value")

        IF objective_rel == "aligned":
            relation_labels.add("beneficial")
        ELSE IF objective_rel == "conflict":
            relation_labels.add("detrimental")

        # 4. Toggle rules (priority order)
        IF "detrimental" IN relation_labels:
            ToggleModule.move(data_id, source="TemporaryQueue", target="DiscardSpace")
        ELSE IF "beneficial" IN relation_labels OR "synthesis_value" IN relation_labels OR "useful" IN relation_labels:
            ToggleModule.move(data_id, source="TemporaryQueue", target="ActiveSpace")
        ELSE IF "match" IN relation_labels OR "related" IN relation_labels OR "familiar" IN relation_labels:
            ToggleModule.move(data_id, source="TemporaryQueue", target="HoldingSpace")
        ELSE:
            ToggleModule.move(data_id, source="TemporaryQueue", target="HoldingSpace")

        # 5. Schedule and log
        SchedulingModule.flag(data_id, label=relation_labels, minutes_from_now=10)
        set_activity("relational_measure", f"{data_id}: {relation_labels}")
        persist_activity()

    RETURN relation_labels

## Description of FUNCTION RelationalMeasurement
Relational check definitions
- Similarity:
- Inputs: content, current subject, long-term index
- Method: text vector similarity + keyword overlap + structural cues
- Output: numeric score; label “match” if above threshold
- Familiarity:
- Inputs: occurrence_count, prior labels, prior schedules
- Method: recurrence threshold + presence of “important/review/used” labels
- Output: boolean recurs; label “familiar” if true
- Relatedness:
- Inputs: content
- Method: semantic search across Semantic and Events; neighbor retrieval (k)
- Output: list of related item ids; label “related” if non-empty
- Usefulness:
- Inputs: objectives, current activity
- Method: rule match: does content satisfy any active objective criteria or immediate tasks?
- Output: enum: useful_now / useful_later / not_useful; label “useful” if useful_now
- Synthesis potential:
- Inputs: content, current subject, related items, objectives, long-term index
- Method: can content + related items advance a probable plan or produce testable steps toward objectives?
- Output: boolean; label “synthesis_value” if true
- Objective relation:
- Inputs: content, objectives
- Method: alignment/conflict checks against objective constraints and desired outcomes
- Output: aligned / conflict

Toggle priority rationale
- Detrimental → DiscardSpace
- Beneficial or Synthesis or Useful → ActiveSpace
- Match or Related or Familiar (but not yet useful) → HoldingSpace
- Unknown → HoldingSpace
This ordering ensures we retain promising material while quarantining conflicting material.

Robustness notes
- Same modules, different contexts: Every spawned window imports identical modules but is parameterized for a distinct check.
- Collector integrity: Only the collector decides toggles and schedules; workers never mutate file locations directly.
- Idempotent logging: Activity logs append or snapshot reliably per cycle.
- Backpressure: If many items hit HoldingSpace, a separate process should periodically re-run relational checks as context changes.

Here’s a polished section you can drop straight into your README to document the Collector. It explains purpose, configuration, schema, and usage examples clearly:

---

## 🧩 Collector Module (`module_collector.py`)

### Overview
The Collector is responsible for **multi‑window execution and concurrency management**. It spawns up to 8 parallel tasks based on a procedural plan, runs real module functions, and persists their outputs in a standardized schema. Results are saved both to dedicated collector files and merged back into the corresponding Semantic record for traceability.

### Features
- **Concurrency cap:** Maximum terminals per run configurable via `config.json`.
- **Objective‑driven:** Plans select modules based on objective labels (e.g., measurement, awareness, synthesis).
- **Standardized outputs:** `{module, status, timestamp, summary, details}` plus `duration_ms` and `run_id`.
- **Configurable merging:** `merge_outputs` toggle, `merge_strategy` (append | replace | summarize), `de_dupe`, and `history_cap`.
- **Timeout control:** Global `timeout_seconds` and per‑module overrides via `module_timeouts`.
- **Dry‑run mode:** Simulate planned actions without executing subprocesses.
- **Safe integration:** Non‑blocking; errors/timeouts logged.
- **Persistence:** Outputs saved to `ActiveSpace/collector_<id>.json` and merged into `collector_outputs` / `collector_metrics`.

### Output Schema
Each collector entry follows this format:

```json
{
  "module": "module_measure",
  "status": "completed",
  "timestamp": "2025-12-13T06:05:00",
  "summary": "{'similarity': 0.85, 'usefulness': 'useful_now', ...}",
  "details": {
    "similarity": 0.85,
    "familiarity": {"recurs": true, "has_prior_useful_labels": false},
    "usefulness": "useful_now",
    "synthesis": true,
    "objective_relation": "aligned"
  },
  "duration_ms": 52,
  "run_id": "<uuid>"
}
```

### Configuration
Collector behavior is configured via `config.json`:

```json
"collector": {
  "max_terminals": 8,
  "timeout_seconds": 15,
  "modules_allowlist": [
    "module_measure",
    "module_awareness",
    "search_internet",
    "module_scheduler",
    "module_select",
    "module_storage",
    "module_toggle"
  ],
  "merge_outputs": true,
  "de_dupe": true,
  "history_cap": 50,
  "merge_strategy": "append",   
  "dry_run": false,
  "module_timeouts": {
    "module_measure": 20,
    "module_awareness": 10,
    "search_internet": 30,
    "module_scheduler": 15,
    "module_select": 10,
    "module_storage": 10,
    "module_toggle": 10
  }
  ,
  "enable_resource_metrics": true,
  "activity_summary_level": "detailed",
  "strategy_overrides": {
    "module_scheduler": "replace",
    "module_select": "summarize"
  }
}
```

### Usage
Run directly:

```powershell
cd C:\Users\yerbr\AI_Algorithms
python -c "from module_collector import collect_results; print(collect_results({'modules':['module_measure','search_internet'],'terminals':2}, 'demo006'))"
```

Or indirectly via `RelationalMeasurement`:

```powershell
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo006','keyword good synthesis','semantic'))"

Example (Phase 5.1 verification):

```powershell
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo007','keyword good synthesis','semantic'))"
```

Example (Phase 6 advanced behaviors):

```powershell
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo008','keyword advanced scheduler','semantic'))"
```
```

### Observability
- Collector outputs are appended to the Semantic record under `collector_outputs`.
- Metrics updated in `collector_metrics` with `collector_runs` and `collector_summary` (includes `run_id`).
- High‑level run summaries logged in `ActiveSpace/activity.json` via `log_collector_run()`.

### Troubleshooting
- Timeouts: Adjust `timeout_seconds` or per‑module `module_timeouts` if subprocesses exceed limits.
- Merge behavior: Use `merge_strategy` to control appends vs replace vs summarize; enable `de_dupe` and set `history_cap` to prevent growth.
- Dry‑run: Set `dry_run: true` in config to validate plans without executing.
- Allowlist: Ensure modules are included in `modules_allowlist` or they will be filtered out.

### Roadmap
- Advanced scheduler actions (reschedule, cancel, priorities).
- Ranking outputs and reasons in `module_select`.
- Metadata enrichment prior to `module_storage` persistence.
- Resource usage hints collection (where feasible).
- Troubleshooting: common errors, timeouts, merge strategy guidance.

### API References (Advanced)
- Scheduler:
  - `reschedule_task(semantic_file, new_time)` → `{status,new_time,task_id}`
  - `cancel_task(semantic_file, task_id)` → `{status,task_id}`
  - `set_priority(semantic_file, task_id, priority)` → `{status,task_id,priority}`
- Select Ranking:
  - `select_information(semantic_file)` → `{ranking:[{id,relevance_score,reason_codes,objective_alignment}]}`
- Storage Enrichment:
  - `store_information(data_id, content, category)` accepts dict `content` to include `{source_chain, tags, provenance:{run_id,module}}` in `metadata`.

---

Would you like me to also draft a **Collector Roadmap diagram** (Markdown table or flow) so the README has a visual summary of how tasks flow from objectives → plan → collector → outputs?

---

# Collector Roadmap

| Stage                | Input Source                          | Action Performed                                   | Output / Persistence                          |
|-----------------------|---------------------------------------|---------------------------------------------------|-----------------------------------------------|
| Objectives            | LongTermStore/Objectives/*.json       | Labels guide procedural matching (e.g. measurement, synthesis, awareness) | Objective set loaded into memory              |
| Procedural Match      | module_tools.procedural_match()       | Builds plan: modules list, terminal count, labels | Plan object {modules, terminals, labels}      |
| Collector Invocation  | module_integration.RelationalMeasurement | Calls collect_results(plan, data_id, content)     | Spawns up to 8 subprocesses                   |
| Module Execution      | module_measure, module_awareness, search_internet, etc. | Each subprocess runs assigned module function     | Standardized outputs {module, status, summary, details} |
| Collector Outputs     | module_collector.py                  | Aggregates results, enforces schema, handles errors/timeouts | collector_<id>.json in ActiveSpace            |
| Merge into Records    | LongTermStore/Semantic/<id>.json      | Appends collector_outputs, updates collector_metrics | Item record enriched with execution trace     |
| Observability         | ActiveSpace/activity.json             | Logs run summaries, metrics, resource usage       | Activity log for monitoring and debugging     |

End of Collector Module section.
---