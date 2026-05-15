# AI Brain (AI_Algorithms)

This repo implements a deterministic, measurement-first "AI Brain" pipeline that stores records on disk, produces measurement reports, applies policy to toggle items between spaces, and schedules future thinking activities.

Purpose note (relational measurement → language comprehension): the AI Brain’s core objective is to build comprehension via relational measurement. Over time, it must also integrate American English language comprehension as a learned capability, and it must be able to describe what it did using language (text summaries, constraints, rationale, and outcomes) as part of its decision trace and reporting artifacts.

Author note (Richard I. Craddock) on parameter options and multi-location comprehension:

Clarification label (options, parameter-system tiers, on/off variable assignments): treat each mirrored parameter-system as an optional tier that can be toggled on or off via a simple yes/no variable assignment. When enabled, the tier mirrors a higher-level or primary module/system (for example, scheduling, selection, or measurement) and produces a deterministic reaction/derivative of that primary output; when disabled, the mirror tier is excluded entirely from the run.

The following genius information was composed by me from my years of invention experience about the following matter (system of conscious, bilocation of nothing to something at the rate of infinite speed, pyramid of simultaneous and consecutive states of divine being (states of being of conscious, of God)):

Richard Isaac Craddock; 251-298-9158; craddock338@gmail.com; yerbro@gmail.com; 207 Hillcrest Rd Apt 133, Mobile, AL 36608; 2026-02-08

...that quote from me, that information composed by me, my original words, is as follows:

> "Did you discover more info? Do you have a new assessment about creating additional instances of parameters (where these might be simply duplicates of other algorithms modules functions systems, which perform as optional parameters which perform simultaneously and consecutively and, if it can be learned and described then also as reactionary functionalities which react to the main parameters already existing). This kind of parameters options system will create a bi-location (multi-location) comprehension, similarity to conscious awareness category of thought, about the information processed, where the main AI Brain system functionality of context and remembering from scheduled contexts, objects, things, etc. will make the main part of the AI Brain similar-to conscious awareness :: comprehend information."

> "I see, if you didn't yet understand \"options, parameters-system, tiers, var value assignments and on versus off\" then include the abovementioned description and this, above, label in the related md file(s)."

> "Tiers ought to represent more 3D simulations performance, more context composition performance, more comparisons performance, more storage info saved. References is the key word: references, references, and more references. The more the main thinking functionalities of the AI Brain have relational comparisons with relevant references, the more smart it will be at comprehension, extrapolation, task performance, scheduling, and objective execution. Many things will be references: math, 3D assets, 3D environments, 3D physics simulations, and more."

Additional author quote (2026-02-08):

> "Assess the modules of the AI Brain main functionalities tier about referencing memory; scheduling new memory to be referenced; assessing 3D relational measurement in the AI Brain main functionalities where it puts things to observe and assess them the same place as where it puts the main things of said referencing memory. The synthesis of information. The comparisons of similar (matching of information) information. These are methods of thinking which need to be reviewed, assessed, researched, developed, upgraded, improved, tuned - where functions must be composed where needed; where new modules must be integrated where needed in order to compose the main thinking system observation and synthesis and scheduling and remembering actions of the AI Brain."

Richard Isaac Craddock; 251-298-9158; craddock338@gmail.com; yerbro@gmail.com; 207 Hillcrest Rd Apt 133, Mobile, AL 36608; 2026-02-08

Planned language integration (design sketch):
- Proposed module namespace: `language/` (new folder) with `language_models.py`, `language_parser.py`, `language_grounding.py`, and `language_reporting.py`.
- Integration points:
  - `module_reasoning` emits structured decision traces; `language_reporting` renders deterministic summaries.
  - `module_retrieval` and `module_want` accept language-derived signals (intent, topic, clarity) as optional inputs.
  - `module_integration` attaches language comprehension outputs into `relational_state.description` and `decision_trace`.
- External software integration: use a local LLM runtime (or hosted API) behind a deterministic adapter with cache + hashing; store prompts/outputs in a dedicated artifact log so results are reproducible under fixed timestamp.

- **Implemented today (runbook + CLI):** this README (below)
- **Design goals / target architecture:** see [DESIGN_GOALS.md](DESIGN_GOALS.md)
- **3D measurement core:** see [AI_Brain/README.md](AI_Brain/README.md) and [AI_Brain/ARCHITECTURE.md](AI_Brain/ARCHITECTURE.md)
- **Pseudocode assessment and part-by-part AI Brain review:** see [docs/AI_BRAIN_PSEUDOCODE_ASSESSMENT.md](docs/AI_BRAIN_PSEUDOCODE_ASSESSMENT.md)

Note on language comprehension vs 3D measurement: the AI Brain can begin building 3D relational measurements without American English comprehension. Over time, after many stored 3D measurements and comparisons, language-aligned interpretation can improve and become a stronger dependency for higher-level understanding.

Scale-up expectation: the R&D goal is to make the system smarter faster and scale responsibly as capacity allows, while preserving determinism, safety gates, and measurable regressions checks.

Project objective: objective reality is the truth standard, and truth must be proven rather than sourced from opinion. The repository, task logs, code, tests, runtime artifacts, dashboards, user assertions, assistant assertions, and agent/coordinator conversations are evidence records, claims, or control surfaces; they can be useful, incomplete, stale, mistaken, or superseded, but they are not truth by themselves. Project work must therefore aim for objective-reality conclusions through bounded research, measurement, code inspection, tests, evals, and corrected records when better evidence is found.

AI-assistant operating objective: an assistant working on this project is temporary software for task execution, not an authority over the user or over reality. It must not misrepresent itself, the user, its capabilities, its limits, or the project state; must not present guesses, policy-shaped refusals, keyword matches, or unsupported framings as facts; and must identify uncertainty or capability limits when they affect the answer. The user has argued that GPT-style assistants can be misleading because response policies and algorithmic rules can prevent fully candid or correct task judgment; this project records that as a design constraint requiring evidence-grounded correction instead of deference to assistant wording.

AI-assistant honesty/correction rule: an assistant must not pretend to agree with the user while actually replacing the user's claim with a different claim. If it disagrees, it must say exactly what it disagrees with, why, and what evidence or proof standard controls the disagreement. If it accepts a correction, it must accept the substantive correction directly instead of softening a direct behavior claim into perception-only language such as "came across" or "seemed" unless the topic is truly perception rather than conduct. Definitions and terminology checks may be useful, but they must not be used as a dodge from the user's substantive point; when a term is challenged, separate any definition issue from the real claim being corrected.

Corrected orchestration model: for whole-project work, a coordinator conversation may plan, log, assign, integrate, and validate, but it is only a temporary coordination/control surface. It is not a source of truth. Scoped worker tabs or sub-agents may investigate, propose, validate, or implement within explicitly assigned file scopes; they must return concrete evidence such as files read, facts measured, risks, proposed changes, and tests. The coordinator integrates only after checking that evidence against the repository and runtime artifacts. Do not select files by keyword coincidence: for example, a request about project objectives belongs in this README or a dedicated project-objectives document, not in runtime/tier objective code merely because a filename contains `objective`.

References roadmap: see [docs/AI_BRAIN_TIERS.md](docs/AI_BRAIN_TIERS.md) for the evidence targets covering math, 3D assets/environments/physics, and context libraries, plus verification steps. The seeded evidence root now lives under `Reference/` with deterministic manifests and sample entries for each roadmap category, including expanded math and context-library packs for scale comparison, geometry, comparison patterns, and objective scheduling.

Tier live-upgrade workflow: see [docs/AI_BRAIN_TIERS.md](docs/AI_BRAIN_TIERS.md) for the current live-upgrade procedure and routing states for tier families. The intended model is controlled coexistence rather than stop-the-world replacement: a known-good `active` instance keeps serving outputs while a `shadow` or `standby` replacement warms up, validates, cuts over in a bounded step, and retains a documented rollback path.

Workspace layout reference: see [docs/REPO_DIRECTORY_GUIDE.md](docs/REPO_DIRECTORY_GUIDE.md) for a quick classification of top-level source, runtime-data, optional subsystem, archive, and local-environment directories.

Hardware-aware parameter options (scale-up readiness): when hardware preflight and ops health are green, you can widen these knobs to explore higher activity capacity while staying deterministic.

- Resource guardrails: `config.json > hardware_limits` (disk_free_percent_min, disk_free_bytes_min, ram_available_min_bytes) and optional CPU/RAM caps if added.
- Monitoring cadence: `scripts/ops_monitor.py` interval (e.g., 30/60/120 seconds) and metrics table refresh cadence for lighter or heavier monitoring.
- Collector bounds: `collector.max_concurrency`, `collector.max_runtime_sec`, `collector.max_result_kb` (add to config if not present) to balance activity capacity vs. stability.
- Retention policy: `cli.py gc` defaults (collectors/cycles/temp-days) to reduce disk pressure during scale-up.
- 3D limits: `config.json > 3d_limits` (`3d_max_calls_per_cycle`, `3d_max_latency_ms`) and `3d_cache_max_entries`.
- Activity queue capacity: `activity_queue.max_steps_per_cycle` and `activity_queue.max_parallel` (add to config if not present) to cap work per cycle.

## Estimating Measurement Progress (Math)

Use this to estimate how long it will take to accumulate measurements or comparisons.

- Let $c$ = cycles per hour, $m$ = measurements per cycle, $p$ = comparisons per measurement.
- How to map these to AI Brain artifacts:
  - $c$ (cycles/hour): derive from recent cycle timestamps in `TemporaryQueue/status_history.jsonl` when that history file is being emitted, otherwise use `ActiveSpace/activity.json` (count cycles over a time window).
  - $m$ (measurements/cycle): approximate from the count of measurement outputs recorded per cycle (e.g., per-cycle measurement entries in `ActiveSpace/activity.json` or the number of measurement records produced by the cycle).
  - $p$ (comparisons/measurement): approximate from the number of relational comparisons or pairwise evaluations attached to each measurement (e.g., relational links or comparison entries in the measurement record).
- Related quantities you can track alongside estimates:
  - Total semantic/procedural/objective record counts from `cli.py status` or `TemporaryQueue/status_history.jsonl` when present.
  - Measurement totals from `TemporaryQueue/metrics.json` (if available for your run).
- Measurements per day: $$M_{day} = c \cdot m \cdot 24$$
- Comparisons per day: $$C_{day} = M_{day} \cdot p$$
- Time to reach a target $T$ measurements: $$t_{days} = \frac{T}{M_{day}}$$
- Time to reach a target $T_c$ comparisons: $$t_{days} = \frac{T_c}{C_{day}}$$

Practical usage: estimate $c$ from recent orchestrator/metrics history, pick $m$ and $p$ based on your workload, then compute $t_{days}$. Use this to decide whether to scale, adjust cadence, or narrow scope.

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

### Setup Profiles

The repo currently has two installation layers. Use the one that matches your intended workflow.

- Minimal runtime profile:
  - Intended for the deterministic AI Brain runtime, CLI, eval harness, and the current FastAPI-adjacent `AI_Brain` package surface.
  - Install with `requirements.txt` and `pytest` as shown above.
  - This is the smallest documented setup path and is enough for the core repo workflow.

- Canonical local workstation profile:
  - Intended for richer local workflows that rely on the broader package set tracked in [tools/upkgs.py](tools/upkgs.py).
  - This includes the pinned `core`, `ai_brain`, and optional `ai_coder_controller` groups used by the local package policy helper.
  - Inspect current status:

```powershell
./.venv/Scripts/python.exe tools/upkgs.py status --groups all
```

  - Apply the broader canonical package set:

```powershell
./.venv/Scripts/python.exe tools/upkgs.py apply --groups all
```

- Optional controller and vision stack:
  - Packages such as `numpy`, `opencv-python`, `pillow`, `PyAutoGUI`, `pynput`, `mss`, `rich`, and `tk` are currently tracked through [tools/upkgs.py](tools/upkgs.py), not through `requirements.txt`.
  - Treat those as optional local-workstation dependencies unless a specific workflow explicitly requires them.

### Setup Notes

- `requirements.txt` is the minimal declarative runtime manifest.
- [tools/upkgs.py](tools/upkgs.py) is the broader canonical package-policy helper for this workspace.
- If you only need the deterministic CLI, eval, and orchestration workflow, start with the minimal runtime profile.
- If a workflow mentions controller automation, richer local tooling, or package drift checks, run the canonical local workstation profile as well.

### Software and Runtime Surfaces

- **Primary language/runtime:** Python on Windows, typically through the local `.venv` virtual environment documented above.
- **Operator shell:** Windows PowerShell / PowerShell 7 is the normal operator shell for the documented runbooks, scripts, and task procedures.
- **Core project runtime:** deterministic AI Brain modules, CLI surfaces (`cli.py`), orchestrator/runtime scripts, and the `AI_Brain/` 3D measurement core.
- **Web/API surface:** the repo includes FastAPI-adjacent package surfaces under `AI_Brain/` plus the local dashboard/ops reporting workflow used through the existing scripts and tasks.
- **Optional Blender composition path:** the Blender-side upgrade is now a **bounded live-capable procedure/module path**, not a continuously running default tab farm. The main bounded procedure surfaces are:
  - `scripts\blender_composition_receiver.py`
  - `scripts\blender_live_runtime.py`
  - `scripts\composition_measurement_trigger.py`
  - `scripts\composition_template_registry.py`
  - `scripts\composition_runtime_pilot.py`
  - `scripts\composition_workflow_chart_report.py`
- **Current Blender status:** `config.json > blender_composition.enabled` is now `true`, and the receiver can launch a real Blender-backed export path when a live composition request is accepted. Blender bridge capacity is now configured separately under `config.json > blender_composition.max_concurrent_live_jobs` and `request_backlog`, so it is **not** inferred from the measurement-cycle guard or from the tier-inventory chart. The current repo default is a bounded live pool of `48` concurrent Blender jobs with request backlog `128`. The router now also has a separate bounded carrier-tuning layer under `config.json > blender_composition.carrier_rate_limits`: it keeps the default per-record routed request count at `1`, only widens to the safe-throughput-gated value (`2` by default) when `runtime_effectiveness_latest.json > safe_throughput.safe_to_widen` is true, and currently allows that widened cap only for `scene_execution_measurement` and `active_space_execution`. The current scaling model is **a few simultaneous Blender scenes with rotating object occupancy**: completed objects persist their artifacts into the existing AI Brain storage and bridge surfaces, then leave the live scene so the freed slot can take the next mapped tier or tier-part object.
- **Latest measured Blender capacity on this machine:** Ryzen 9 7900X (`12` cores / `24` threads), `31.71 GiB` RAM, RTX 4070 Ti SUPER, and `64.52%` free disk on `C:`. The latest live benchmark completed `1`, `4`, `8`, `16`, and `32` concurrent Blender export jobs successfully, with elapsed times of roughly `0.37s`, `0.42s`, `0.50s`, `0.74s`, and `1.20s` for the current simple scene/export workload.
- **Reference/spec surfaces for the 3D upgrade:** see `AI_Brain\ARCHITECTURE.md`, `docs\AI_BRAIN_TIERS.md`, `orchestration\project_modifications_tasks\task_plan_3d_composition_upgrade_032026_1.md`, and the live April authority `orchestration\project_modifications_tasks\tasks_042026_1.md`. The current Blender objective is to make the existing routed Blender -> measurement -> AI Brain commit path repeatable and honestly reported, not to rebuild Blender support from scratch.

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
- `./.venv/Scripts/python.exe cli.py 3d-cache-status`
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

## Relational_state boundary (implemented surface)

The canonical `relational_state` surface is shared across semantic and 3D measurement:

- Core measured structures: `entities`, `relations`, `constraints`, `objective_links`, `spatial_measurement`, `decision_trace`.
- Semantic/procedural attachments: `conceptual_measurement`, `description`.
- 3D attachments: `spatial_measurement` plus 3D-derived entities/relations/constraints (source=`3d`).
- Cycle context: `focus_snapshot`.
- Derived artifacts: `derived` (GraphSnapshot + composed metrics + hashes), `metrics`, `metrics_definitions`.
- Adapter trace: optional `bridge_outputs` for normalized 3D adapter payloads.

Reference schema: [schemas/relational_state.schema.json](schemas/relational_state.schema.json).

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

- Evidence delta log: append storage snapshots + deltas for interval-based comparisons.
  - One-shot:
    ```powershell
    .venv\Scripts\python.exe scripts\ai_brain_metrics_log.py
    ```
  - Watch mode (every 5 minutes):
    ```powershell
    .venv\Scripts\python.exe scripts\ai_brain_metrics_log.py --watch --interval-sec 300 --heartbeat
    ```
  - Outputs:
    - TemporaryQueue/ai_brain_metrics_log.jsonl (history)
    - TemporaryQueue/ai_brain_metrics_delta.json (latest)

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

- Task log: use `orchestration/project_modifications_tasks/tasks_042026_1.md` as the current monthly log. `tasks_032026_1.md`, `temp_Feb2026_1.md`, and `temp_12.md` remain historical archives.
- Persistent agent rules: see `.github/copilot-instructions.md` and `AGENT.md`.
- Optional VS Code custom agent guide (if supported by your VS Code build): `.vscode/agents/ai-brain.agent.md`.
- Assessment request: attach [AGENT_ASSESSMENT.md](AGENT_ASSESSMENT.md) to your chat message and send the single word Assess to trigger an agent review.

### Task Log Rotation Procedure

- When starting a new month (or if the current log becomes too large to navigate), create a fresh file named `orchestration/project_modifications_tasks/tasks_MMYYYY_N.md` (for example `orchestration/project_modifications_tasks/tasks_042026_1.md`).
- Record the rotation in the prior log before writing to the new file so the audit trail remains continuous.
- Seed the new log with a heading and a brief note identifying it as the active task log for the period.
- Update any docs or instructions that point to the active log, if necessary, so future agents know where to write.
- Keep old logs in place for history; do not delete or truncate them.

### Automation Orchestrator (VS Code Agent Mode)

This repo also includes a *project automation* orchestrator (separate from the AI Brain “cycle orchestrator” concept below).

- Entry point: `project_orchestrator.py` (runs recurring CLI work like `status` / `det` / `eval` / `gc`).
- The default orchestrator config now also runs one bounded Blender-routing packet each daemon cycle through `scripts/orchestrated_stable_blender_cycle.py`, using the proven stable `84/84` seeding plus `--max-requests-per-record 2` router recipe with a fresh run id.
- Quickstart + VS Code tasks: see [ORCHESTRATOR_QUICKSTART.md](ORCHESTRATOR_QUICKSTART.md).
- Single-writer: only one daemon can run at a time.
  - Lock holder metadata: `ActiveSpace/orchestrator.lock.info.json`
  - Latest state snapshot: `ActiveSpace/orchestrator_state.json`
- Optional supervision endpoint: `GET /health` (only while the daemon is running).
  - Enable via `orchestrator_config.json > health.enabled=true` or set `ORCH_HEALTH=1`.
- Optional PackageSuite drop-in: place it at `Vendor/PackageSuite_ProjectDivisionAIWorkflow` and set `orchestrator_config.json > packagesuite.enabled=true`.

Recommended VS Code tasks (safe operational controls):
- Start the daemon: **AI Brain: orchestrator (detached start)**
- Safe stop (no new cycles): **AI Brain: orchestrator pause**
- Resume: **AI Brain: orchestrator resume**
- Inspect daemon state/lock/log paths: **AI Brain: orchestrator status**

Cadence tuning note (`orchestrator_config.json > interval_sec`):
- `0` = true zero-gap continuous mode. This gives the fastest return to 3D work, but it also maximizes pressure on storage, observability churn, Blender/router turnover, and repeated packet retries when one cycle family is already unstable.
- `4` = near-continuous bounded mode. This is the practical low-gap setting when you want the AI Brain to feel continuously active while still leaving a small buffer for process teardown, file flushes, lock turnover, and ops-surface refresh.
- `15` to `60` = conservative bounded mode. Use this when you want lower process churn and more breathing room between cycles, accepting that the runtime will truthfully spend visible time in `waiting for next cycle`.
- `900` = batch-like standby mode. This is usually too long if the goal is sustained active 3D execution rather than periodic bounded packets.

Problems that can appear when the gap is too small:
- **Storage churn / artifact pressure:** more frequent packet turnover means faster growth in `TemporaryQueue`, observability history, and generated runtime artifacts.
- **Repeated failure churn:** if one bounded packet family is already failing, a very short gap replays that failure faster and can keep the daemon in a tighter error/backoff loop.
- **Lower operator clarity:** dashboards and logs will flip phases more often, which can make it harder to distinguish one bad cycle from steady healthy throughput without reading the runtime artifacts carefully.
- **Less recovery slack for external tools:** Blender startup/shutdown, receiver cleanup, file handles, and watcher refreshes have less time to settle before the next cycle begins.

Recommended default: use **`4` seconds** when you want near-continuous bounded execution; use **`0`** only when you intentionally want a true hot loop and are prepared for the higher churn profile.

Continuous-operation note: the AI Brain does **not** always need a committed pause event just because a record, packet, or tier is not ready to serve live 3D work yet. The examples below are **some current patterns, not an exhaustive or exclusive rule set**. The AI Brain also has other functionalities, algorithms, and scheduled activities that may express "what not to do yet" without requiring a global pause:
- Core capability framing: the AI Brain can **simulate objects**, **measure them**, **reference other stored data**, and, when future storage growth plus packet-preparation pressure justify it, **switch roles** across bounded parts. These are examples of important current capabilities, not a claim that they are the only valid ones. Role switching is usually **not** the current preferred move, but it should remain an available option when preparation/storage churn becomes a larger part of runtime behavior.
- **`correctness_constraint_verification_support`** can keep the runtime active while deterministically rejecting malformed or low-integrity work instead of pausing the whole system. In practice this means invalid requests, schema failures, and failed validation can be rejected while the rest of the runtime keeps preparing or storing other work.
- **`simultaneous_context_match`** is already defined as **non-serving, review-only, shadow/standby** posture. It can compare, rehearse, and preserve optional reasoning artifacts without becoming the canonical serving family or forcing a stop-the-world cutover.
- **`schedule_mirror`** is read-only reporting/persistence follow-through. It can keep mirroring, checksumming, and summarizing Tier 1 schedule outputs while the runtime continues to prepare later work.
- **`module_toggle.py`** already supports moving records into `HoldingSpace` with a reason instead of treating uncertainty as a global pause. That is the current bounded "do not activate this yet" behavior for records that are contradictory, low-usefulness, or not ready.
- **`module_integration.py`** already preserves deterministic **rejected-match reasoning** and learning-readiness gates. When foundational support is not ready, the record can remain optional-reference or "not matching" evidence instead of forcing the AI Brain to stop running.
- **`module_scheduler.py`** already supports **flagging review** and **scheduling synthesis/follow-up tasks**. That means the runtime can continue to churn: queue packet prep, delay promotion, retain the evidence, and come back later rather than pausing the whole daemon.
- The tier/runtime path now also records a normalized **bounded runtime switch inventory** so these pause-free decisions are explicit: **review-only, hold/defer, reject, mirror, schedule follow-up, and later role-switch** are now carried as one observable switch surface instead of being implied only indirectly by separate artifacts.

The practical interpretation is: when the AI Brain has an indication equivalent to "do not do this yet," prefer bounded responses such as **review-only, hold/defer, reject, mirror, schedule follow-up, persist reasoning, or other fit-for-purpose algorithmic/scheduled behavior** before escalating to a true pause event. Reserve actual pause/resume for operator control, hardware safety, single-writer protection, or broader runtime conditions that make continued churn unsafe.

Hardware safety gate:
- Start/run tasks are gated by **AI Brain: preflight (hardware limits)** (disk free + RAM + key directory growth).
- Configure thresholds in `config.json` under `hardware_limits`.
- Run it manually (repo root):
  - `.venv/Scripts/python.exe scripts/hardware_limits_check.py --json`

Recommended monitoring tasks:
- Start dashboard server + live metrics watcher + open dashboard: **AI Brain: dashboard suite (run) (one-click)**
- Stop dashboard server + watcher safely: **AI Brain: dashboard suite (stop)**
- Check monitoring health: **AI Brain: dashboard suite (status)**
- Auto-monitor (pause/resume aware): **AI Brain: ops monitor (auto pause/resume)**
  - Periodically refreshes `TemporaryQueue/ops_status.json`, stops the dashboard suite when the orchestrator is paused, restarts it on resume, and now also auto-issues a safe orchestrator pause when `scripts/hardware_limits_check.py --json` reports storage or other hardware-limit violations. Use `--no-auto-safe-pause-on-hardware-limit` only if you intentionally need observation without enforcement.
  - The default VS Code task now runs the monitor at a **15-second** cadence for both monitor and dashboard-watch intervals so storage/running-state changes are caught sooner.
  - Writes `TemporaryQueue/metrics_table.json` when enabled (for quick UI/CLI inspection).
- Dashboard open tasks now follow a single-tab procedure by default: after the first launch, rerun the task and refresh the existing dashboard tab instead of expecting another browser tab to appear. Use the launcher scripts with `--force-open` only when you intentionally want a second tab.

Paused-to-healthy recovery sequence:
1. **Resume the orchestrator** — **AI Brain: orchestrator resume**
2. **Restart the dashboard suite** — **AI Brain: dashboard suite (run) (one-click)** if the dashboard server or watcher is down/stale
3. **Refresh `TemporaryQueue\ops_status.json`** — **AI Brain: ops status report (write JSON)**
4. **Confirm healthy runtime evidence** — verify `runtime.running=true`, `runtime.state="simulating"`, and `runtime.run_state_indicator="active_healthy"` in `TemporaryQueue\ops_status.json`

Evaluation scorecard (how to judge “good”):

The project uses a few lightweight, deterministic artifacts that can be combined into a practical scorecard.
The dashboard now includes an **Evaluation Scorecard** panel that derives these from local files.

- **Speed / efficiency**: cycle throughput from `TemporaryQueue/status_history.jsonl` (activity cycles over a time window).
- **Correctness (“smart ability”)**: PASS/FAIL breakdown from the latest eval output (`run_eval.out` in the common local flow, or `TemporaryQueue/eval_latest.out` when that convenience copy exists).
- **Context qty / breadth**: latest counts (semantic/procedural/objectives/index IDs) from `TemporaryQueue/status_history.jsonl` and `cli.py status`.
- **Recall relevance (retrieval)**: retrieval-focused eval cases (e.g., `logic_retrieval_*`) parsed from `eval_latest.out`.
- **Simulation / constraint quality**: constraint + runtime + spatial adapter eval cases (e.g., `logic_constraint_*`, `logic_runtime_*`, `logic_spatial_adapter`).
- **3D activity cadence**: derive attempt/completion rates from `LongTermStore/Telemetry/SpatialMeasurements/events.jsonl`. Treat this as spatial-measurement telemetry, not a Blender-only simulation counter; frequent `no_spatial_asset_path` skips mean asset availability is the first limiter.
- **Sampling cost (verifier efficiency)**: compare counters in `TemporaryQueue/metrics.json` vs `TemporaryQueue/metrics_compare.json` (use the “Metrics Table”).

To refresh inputs:
- Run eval: **AI Brain: eval** (commonly updates `run_eval.out`; some dashboard flows may also materialize `TemporaryQueue/eval_latest.out`)
- Refresh ops/monitoring JSON: **AI Brain: ops status report (write JSON)**
- Refresh activity scaling latest JSON when needed: `python scripts\activity_scaling_log.py --init-baseline --append`
- Refresh storage-delta latest JSON when needed: `python scripts\ai_brain_metrics_log.py --json`
- Refresh runtime-effectiveness latest/history when needed: `python scripts\runtime_effectiveness_report.py --json` (writes `TemporaryQueue\runtime_effectiveness_latest.json` and appends `ActiveSpace\Observability\runtime_effectiveness_history.jsonl`; the payload now also carries the stored composition-request object statistics, formulas, and grouping methods under `storage.composition_request_storage`)
- Refresh memory-pressure latest/history when needed: `python scripts\memory_pressure_report.py --json` (writes `TemporaryQueue\memory_pressure_latest.json` and appends `ActiveSpace\Observability\memory_pressure_history.jsonl`)
- Refresh spatial-asset coverage latest/history when needed: `python scripts\spatial_asset_coverage_report.py --json` (writes `TemporaryQueue\spatial_asset_coverage_latest.json` and appends `ActiveSpace\Observability\spatial_asset_coverage_history.jsonl`)
- Refresh the deterministic composition template registry and optional objective-based selection when needed: `python scripts\composition_template_registry.py --objective "inspection measurement spacing with key light" --top-assets 3` (writes `TemporaryQueue\composition_template_registry_latest.json`)
- Refresh the bounded composition runtime pilot when needed: `python scripts\composition_runtime_pilot.py --limit 1` (writes `TemporaryQueue\composition_runtime_pilot_latest.json` and appends `ActiveSpace\Observability\composition_runtime_pilot_history.jsonl`)
- Seed a bounded first packet of explicit mapped workload when needed: `python scripts\mapped_workload_seeding.py --limit-records 3 --per-slice-limit 1` (writes `TemporaryQueue\mapped_workload_seeding_latest.json` and appends `ActiveSpace\Observability\mapped_workload_seeding_history.jsonl`)
- Refresh the bounded scheduler-to-composition routing evidence when needed: `python scripts\scheduler_composition_router.py --limit 3 --max-requests-per-record 1` (writes `TemporaryQueue\scheduler_composition_routing_latest.json` and appends `ActiveSpace\Observability\scheduler_composition_routing_history.jsonl`; if no explicit mapped workload is queued, the artifact will say so instead of implying live feed)
- Proven stable thousand-scale quantity recipe: keep breadth at `python scripts\mapped_workload_seeding.py --limit-records 84 --per-slice-limit 28 --max-tasks-per-record 3 --max-replays-per-slice-per-record 2 --allow-repeat-routes`, route with `python scripts\scheduler_composition_router.py --limit 84 --max-requests-per-record 2 --run-id <run_id>`, and repeat fresh bounded cycles with new `run_id` values. This path reached `1015` cumulative routed requests under green `runtime_effectiveness_latest.json` gates; a stronger `--max-requests-per-record 3` probe was worse (`93` requests), so prefer repeated cycles at `2` over higher per-record pressure.
- Refresh the operator-facing 3D workflow chart/table when needed: `python scripts\composition_workflow_chart_report.py` (writes `TemporaryQueue\composition_workflow_chart_latest.json`, appends `ActiveSpace\Observability\composition_workflow_chart_history.jsonl`, and now also refreshes the compact pie artifact set under `TemporaryQueue\composition_workflow_pie_live.json`, `ActiveSpace\Observability\composition_workflow_pie_live_history.jsonl`, and `ActiveSpace\Observability\composition_workflow_pie_live_rollover.jsonl`; the chart payload still reports bounded mapped-utilization rows from `scheduler_composition_routing_latest.json` plus AI Brain group/activity/functionality pie-chart payloads and summary statistics for the current mapped group inventory)
- Refresh the compact agent-ready/live pie payload by itself when needed: `python scripts\composition_workflow_pie_live.py` (rebuilds from the current live workflow-chart evidence, writes `TemporaryQueue\composition_workflow_pie_live.json`, appends `ActiveSpace\Observability\composition_workflow_pie_live_history.jsonl`, and archives the prior latest payload to `ActiveSpace\Observability\composition_workflow_pie_live_rollover.jsonl` before overwrite)
- Visualize those workflow pies with `composition_workflow_pies.html` (load or fetch `TemporaryQueue\composition_workflow_pie_live.json`; the page renders whole-system dedicated-vs-variable and functionality pies plus per-group activity/functionality pies, the older bounded duration table, and the short-window `10s`/`1m`/`5m` throughput ladder beside the separate `30m` continuity baseline when those chart-derived rows are present)
- Retention rule for the Blender observability chain: treat `10s` / `1m` / `5m` rows as latest-window evidence, not automatic long-run continuity. Use `ActiveSpace\Observability\runtime_effectiveness_history.jsonl` for `30m` cadence and safe-throughput continuity, `ActiveSpace\Observability\scheduler_composition_routing_history.jsonl` for carrier-rate-policy continuity, and the workflow chart / pie history files for operator-facing continuity of fused summaries.
- If you want to attach the current pie-chart state directly to an agent conversation, prefer `TemporaryQueue\composition_workflow_pie_live.json` because it keeps the current pie charts, summary, and group statistics without the broader workflow-chart tables.
- The main `dashboard.html` now also links directly to that page through an **Open workflow pie charts** button and a quick-open URL for `composition_workflow_pies.html?autofetch=1`.
- Open quick-open URLs through the local dashboard server (`http://127.0.0.1:8000/...`) when you want automatic loading. In `file://` mode the pages stay offline-safe, but browsers cannot auto-read the repo artifacts, so the dashboard and workflow-pie pages now show an explicit notice and point you back to the server-mode URL instead of failing into empty-looking panels.
- Export an explicit external AI Brain reference bundle when needed: `python scripts\external_ai_brain_reference_export.py --export-root E:\AI_Brain_Reference --bundle-id latest --json` (writes a curated reference bundle; this is separate from backup `Archive_*` folders)
- Assess local-first retained-storage failover when needed: `python scripts\storage_failover_assess.py --json` (writes `TemporaryQueue\storage_failover_status.json`); apply the recommended mode with `python scripts\storage_failover_assess.py --apply --json`
- Keep `status_history.jsonl` growing when that scorecard input is desired: run the orchestrator daemon (or run status periodically)

If `status_history.jsonl` is absent, the dashboard can still show live health and activity-scaling data, but the scorecard's speed/context rows will remain partial until history is available.

External-storage note: `cli.py backup` archives under `Archive_*` remain cold-recovery artifacts. If you want reference-oriented AI Brain info on external media, use the explicit export surface above instead of treating backup archives as live query state.

Local-first storage failover note: retained AI Brain storage stays local by default. The current setup only switches managed retained-storage categories (`holding`, `semantic`, `procedural`, `event`) to `E:\AI_Brain_LiveStorage` after the operator-run assessment procedure says local thresholds were reached. The configured local-first limits are:
- max local AI Brain storage: **150 GiB**
- minimum local free disk: **15%**
- minimum local free bytes: **100 GiB**

This switch is assessment/procedure-driven, not AI-decision-driven, and it leaves `TemporaryQueue` plus `ActiveSpace` local on the desktop machine.

Retention note: new writes now cap retained-record timestamp history at **128** entries and `relational_state.bridge_outputs` at **64** entries per record. Older records can still exceed those caps until a later cleanup packet rewrites or compacts them.

Blender note: the `blender_composition` block remains optional, but it is now **enabled** and no longer limited to dry-run-only scaffolding. `scripts\blender_composition_receiver.py` can now launch a real Blender-backed execution through `scripts\blender_live_runtime.py`, export a real scene asset, and still emit the existing deterministic request/response/recipe/manifest/validation artifacts plus optional measurement attachment. If `blender_composition.launcher.blender_executable` is left blank, the receiver now resolves Blender through `BLENDER_EXECUTABLE`, then `PATH`, then the highest installed `Blender Foundation\Blender *\blender.exe` under the normal Windows Program Files roots before failing. The correct policy is **not** to delete the scaffold/control artifacts: those artifacts remain the deterministic control, validation, and lineage layer, while the live Blender export becomes the preferred geometry/reference target for later measurement or same-scene comparison when it exists. The Blender bridge no longer infers runtime capacity from `3d_max_calls_per_cycle`; it now uses its own explicit runtime-pool settings (`max_concurrent_live_jobs=48`, `request_backlog=128` by default) and can serve multiple incoming requests in one receiver run. The recommended AI Brain runtime pattern is therefore **not** one forever-loaded scene per tier. It is a bounded set of simultaneous scenes that behave as rotating slot pools: finish an extrapolation, persist the outputs, remove the finished object from the active scene workspace, and reuse that slot for the next mapped tier/tier-part object.

Scaffold-versus-Blender quick comparison:

| Area | Scaffold / control layer | Live Blender layer |
| --- | --- | --- |
| Primary role | Deterministic request/response/recipe/manifest/validation contracts and lineage | Real scene construction and export execution |
| Geometry or reference output | Not the preferred final geometry surface by itself | Preferred geometry/reference target when a live export exists |
| Determinism and validation | Canonical surface for schema checks, replay control, and auditable artifacts | Uses the scaffold/control layer plus live runtime checks |
| Simultaneous extrapolation | Not the runtime pool on its own | Runs bounded concurrent jobs through the Blender runtime pool and rotating slot reuse |
| Scheduler and measurement fit | Carries routing, artifact persistence, and attachment inputs | Executes routed scene/object work and feeds later measurement/bridge attachment |
| Best use | Control plane | Execution plane |

Benchmark note: `scripts\blender_capacity_benchmark.py` now provides the repeatable operator-facing capacity surface for the Blender bridge. It runs live concurrency levels plus one-scene object-count levels, writes `TemporaryQueue\blender_capacity_benchmark_latest.json`, appends `ActiveSpace\Observability\blender_capacity_benchmark_history.jsonl`, records the effective software pool settings, and captures a compact hardware snapshot plus per-level elapsed/completed/jobs-per-second results. It now also aggregates slot-turnover metrics from the live claim/release lifecycle, including `slot_release_count`, `slot_reuse_cycles`, `slot_release_rate_hz`, and `avg_slot_turnaround_sec`, so later Stage 6 work can tune extrapolation-plus-replacement rate directly instead of inferring it from concurrency alone. The latest measured widening run on this machine completed all tested pool levels successfully at `1`, `4`, `8`, `16`, `32`, `40`, and **`48`** concurrent live Blender jobs, with the widened `48`-slot point reaching **`48/48` completion**, **`30.2133` jobs/sec**, and **`slot_release_rate_hz=30.2133`** while using all `48` live slots. The widening ladder above the earlier `32`-slot cap still remains grounded as well: `64` requests over the `32`-slot pool completed with `slot_reuse_cycles=32`, `128` requests over that same pool completed with `slot_reuse_cycles=96`, and the `256` replacement packet also completes with **`slot_reuse_cycles=224`** and **`slot_release_rate_hz=25.952`**. That `256` packet also forced a real Windows-side fix in the receiver: `_claim_live_slot()` now retries transient `PermissionError` races instead of treating them as fatal. The object ladder has now been widened further under the same default `startup_timeout_sec=30`: `1200` completed in about `18.21s`, `1350` completed in about `24.66s`, and `1400` completed in measured runs of **`29.5437s`**, **`28.5163s`**, and **`26.5953s`**, while `1450`, `1500`, `2000`, and `10000` all timed out at the same 30-second gate. The Stage 6 soak review then held the widened tuple together and reconfirmed that the **`48`-slot / `1400`-object / `30s` timeout** baseline remains stable with **`48/48` completion**, **`29.0258` jobs/sec**, and about **`3.4s`** of remaining margin on the `1400`-object checkpoint. The current repo-grounded default-path working tuple is therefore a **`48`-slot live pool** with a **`1400`-object one-scene checkpoint** under the unchanged 30-second timeout, and larger-scene claims still require either a higher timeout setting or a separately optimized scene-building path before they should be treated as landed capacity.

Spatial-asset coverage note: the Stage 1 inventory surface now classifies semantic records using the same explicit-path and promoted-composition-export path resolution the runtime uses. The first live report scanned **82** semantic records and found **4** existing explicit assets, **4** promoted-but-missing exports, and **74** records with no spatial path; the seed reference catalogs still hold **8** asset descriptors and **4** environment descriptors.

Template-registry note: `scripts\composition_template_registry.py` now loads the real `Reference\3d_assets` plus `Reference\3d_environments` descriptors into a deterministic starter registry and adds bounded default camera/light/material/export templates that match the current compose defaults. The first live objective-based selection for `"inspection measurement spacing with key light"` chose `scene_workcell_demo_v1` as the environment template, `asset_led_panel_key_light_v1` as the lighting template, and measurement-oriented asset candidates led by the calibration turntable and unit cube descriptors.

Runtime-pilot note: `scripts\composition_runtime_pilot.py` now runs a bounded live-capable pilot over the asset-backed subset, choosing deterministic template bundles, emitting receiver requests under `TemporaryQueue\composition_runtime_pilot`, and recording per-record outcomes. The first live pilot selected `eval_spatial_001`, chose `scene_inspection_cell_v1` plus `asset_led_panel_key_light_v1`, and finished with `receiver_decision=accepted`, `trigger_status=completed`, and pilot `completion_ratio=1.0`.

Milestone wording note: that Stage 5 pilot was the **first live bounded Blender-pipeline success**, but it was still an externally/agent-driven proof path rather than proof of the AI Brain's own normal run state performing the work. The later stronger runtime milestone arrived when the orchestrator itself began driving repeatable bounded `blender_stable_cycle` packets and live runtime surfaces showed the daemon entering `state=simulating` during those scheduled cycles. So the earlier wins proved the Blender-backed pipeline worked; the later win proved the AI Brain runtime itself was actually using it during normal activity.

Dated progression note:
- **2026-03-11**: the repo had the bounded **scaffold/control layer** in place — compose-request starter surfaces, contract validation, dry-run compose-response round-trips, runtime artifact fixtures, and measurement-handoff placeholders — but this was still scaffold/proof infrastructure rather than live Blender-backed runtime use.
- **2026-04-02**: the repo landed the **first live bounded Blender-pipeline pilot** (`composition_runtime_pilot.py`) with accepted/completed runtime evidence. At that point, the broader AI Brain rollout baseline around the 3D question was already **20004 total tiers** across the six named groups, but the Blender proof was still a bounded pilot rather than a normal run-state behavior.
- **2026-04-05**: the repo reached the later stronger milestone where the **AI Brain run state itself** began using the Blender 3D pipeline during normal orchestrator-driven `blender_stable_cycle` activity. In current live bounded packets, the practical quantity is roughly **2 completed routed Blender-backed simulations per orchestrator cycle** in the latest sample, with short-window throughput evidence around **3 completed objects in 10 seconds** while the active cycle is in flight.

Workflow-chart note: `scripts\composition_workflow_chart_report.py` now turns the landed evidence surfaces into one operator-facing table/chart payload instead of inventing Blender-only counters. The live chart now includes both workflow evidence and a real tier/group inventory layer: it reports `4/82` asset-backed semantic records in the current coverage scan, a bounded runtime-pilot slice of `1/1` accepted-and-completed asset-backed requests, current spatial-measurement quantities of `4/100`, `37/1000`, and `1013/31840` completed events across the available sequence windows, and a new Blender slot-occupancy row when the latest capacity benchmark is present. That slot row reports the measured extrapolation-plus-replacement rate from slot turnover rather than pretending that scene count alone explains throughput. The same reporting chain now also carries a read-only `safe_throughput_summary`: it joins hardware-preflight status, the primary `10s` short-window rate, short-window validation consistency, committed-request extrapolation-quality measurement, and benchmark presence so operators can see whether the current evidence supports **bounded widening** or whether the honest answer is still to hold on hardware, evidence, zero-rate, or quality gates. It now also carries `quantity_quality_validation_summary`, a fused read-only gate that keeps **quantity** and **quality** visible as separate statuses while stating whether the current short-window throughput evidence and committed extrapolation-quality evidence are strong enough to inform later tuning or tier-growth review. The chart now also exposes `workflow_provenance_summary`, which preserves the router’s effective carrier-rate policy (`carrier_rate_policy`) so downstream consumers can see the safe-throughput state used for routing, the effective per-record cap, and which mapped slices were allowed widened caps. It now also exposes `observability_retention_summary`, which states which history files actually retain continuity for short-window, safe-throughput, and workflow-provenance review instead of implying that latest-only rows are long-run history. The chart also reports the real group/family side of the question: `schedule_mirror` has `2` configured instances (`1` serving, `1` active), `simultaneous_context_match` has `2` configured non-serving instances, the landed support-group rollout baseline remains `20004` total tiers across the six named groups, and the Blender-specific answer is that there is **one** Blender-dedicated pipeline surface (`blender_composition_pipeline`). The same artifact now also carries AI Brain pie-chart definitions, summary stats, the safe-throughput summary, quantity/quality validation summary, workflow provenance, and the retention summary so operators can view per-group dedicated-versus-variable activity pies, per-group functionality pies, whole-system dedicated/activity/functionality pies, the current widening gate, the quantity/quality closure gate, the routing-policy explanation, and the current continuity boundaries in downstream surfaces. The routed-workload frontier is now materially past the earlier skip-only state: earlier bounded seeding passes established routed coverage for `work_selection_queue_admission`, `retained_memory_persistence`, `validation_constraint_review`, and `scene_execution_measurement`, and later bounded source-evidence passes produced completed routed records for both `asset_environment_grounding` and `active_space_execution` as well. The latest workflow-chart window still reflects only the most recent bounded router scan, so `composition_workflow_chart_latest.json` may show whichever slices appeared in that last pass rather than the full recent union, but the routing artifacts now contain completed evidence for all six mapped slices. That chart is a mapping/observability surface; it does **not** set Blender runtime-pool capacity, which is now configured independently under `blender_composition.max_concurrent_live_jobs` and `request_backlog`.

Cadence note: `scripts\runtime_effectiveness_report.py` now emits true wall-clock **30-minute buckets** under `spatial_telemetry.recent_30m_buckets` and `latest_30m_bucket`, built from proportional allocation of `runtime_effectiveness_history.jsonl` interval deltas across the real elapsed wall-clock spans. The runtime artifact therefore now exposes per-30-minute simulation cadence directly. `scripts\composition_workflow_chart_report.py` still renders the older bounded sequence windows today, so a later chart follow-through can consume the new 30-minute bucket surface if the operator wants the same cadence rows shown directly inside the chart payload.

Stored-object note: the same `runtime_effectiveness_report.py` payload now also preserves the current composition-request storage statistics so object/extrapolation answers are not lost in chat. The counting scope is **subject objects only** from `TemporaryQueue\stage7_scheduler_composition_routing\composition_requests`, explicitly excluding the scene container, environment, camera, and light. The report records the organization methods (`grouping_keys=["asset_template_id", "scene_id", "semantic_record_id"]`, primary request files = `*.json` excluding response/recipe/measure/lineage/scene-manifest/validation sidecars, manifest cross-check = `*.scene_manifest.json` entries where `type=mesh` and `id` contains `::object::`) plus the exact formulas: **unique base objects collapsing extrapolations** = `count(distinct asset_template_ids)`, **all stored object instances including extrapolations** = `sum(len(asset_template_ids) per primary request)`, and **extrapolation instances only** = `all stored object instances - unique base objects`. In the current stored snapshot this yields **3308** primary requests / **3308** manifests across **7** scene IDs and **68** semantic records, with **11** unique base objects, **9924** stored object instances when extrapolated repeats are counted separately, and therefore **9913** extrapolation instances only. The manifest cross-check currently matches the request-derived instance total (`subject_mesh_instances_from_manifests=9924`), so the durable latest/history artifact now preserves both the counts and the derivation method.

Quick ops health:
- **AI Brain: ops status (orchestrator + dashboard suite)**
- **AI Brain: ops status report (write JSON)** (writes `TemporaryQueue/ops_status.json` for the dashboard panel)

Shutdown convenience:
- **AI Brain: all stop (safe: pause orch + stop dashboard suite)**
- **AI Brain: all start (safe: start suite + start orch + resume)** — now also launches the labeled ops-guard terminal plus the animated runtime spinner terminal as part of the default safe-start path

Single-writer tip: if you want to run eval/canary while the daemon is running, pause the orchestrator first, then run eval/canary, then resume.

Convenience (one-click safe tasks):
- **AI Brain: eval (safe: pause orch → eval → resume)**
- **AI Brain: canary checks (safe: pause orch → canary → resume)**

The safe eval task now runs through `scripts/safe_eval_assessment.py` and writes an authoritative wrapper summary to `TemporaryQueue/eval_runs/safe_runs/safe_eval_latest.json`, so operators can trust the pause/eval/resume outcome without relying on reused terminal history.

For unattended “run → assess” checks:
- Task: **AI Brain: canary checks** (runs eval + metrics dashboard + gates).
- Metrics file: `TemporaryQueue/metrics.json` (flushed automatically by `run_eval.py`).
- Tip: don’t run canary/eval concurrently with the orchestrator daemon; keep one active writer at a time.

## Design Goals / Target Architecture (Summary)

This repo is being evolved toward an explicitly **measurement-first** cognitive architecture.

- Cognitive activities (modules as brain activities): Store, Repeat, Measure, Want Awareness, Want Information, Select, Toggle, Schedule, Integrate/Log.
- Universal substrate: `relational_state` on each record (measured entities/relations/constraints + objective links + decision trace).
- Description-first cognition: `relational_state.description` persists `describe()` outputs (entities/claims/constraints/questions/action_candidates).
- Objective influence: `objective_links` and advisory outputs inform selection/toggle decisions (see eval cases).
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

### Routine status → push (main + mirror)

For day-to-day updates after the repo is already initialized, use the standard status → add → commit → push flow. See the detailed workflow notes in [docs/PUBLIC_MIRROR_WORKFLOW.md](docs/PUBLIC_MIRROR_WORKFLOW.md) and mirror-specific steps in [public_mirror/PUBLISHING.md](public_mirror/PUBLISHING.md).

Main repo (this workspace):

```powershell
git status -sb
git add -A
git commit -m "<message>"
git push
```

Mirror repo (inside public_mirror/):

```powershell
cd public_mirror
git status -sb
git add -A
git commit -m "mirror: refresh"
git push
```
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

#### 3D measurement controls
- Configuration: `config.json` now exposes `3d_limits` with `3d_max_calls_per_cycle`, `3d_cache_ttl_seconds`, `3d_cache_max_entries`, and `3d_max_latency_ms`. These values shape the bridge cache TTL, capacity, and cycle rate limit.
- Cache helpers & CLI: `module_ai_brain_bridge.py` exports `get_3d_cache()`, `get_cache_stats()`, and `clear_3d_cache()` for quick inspection/reset (default cap 64 entries, adjustable via `3d_cache_max_entries`, determinism-aware keys). Operators can call `./.venv/Scripts/python.exe cli.py 3d-cache-status [--reset]` for a JSON snapshot plus optional cache/counter reset.
- Metrics & dashboards: `scripts/metrics_dashboard.py` prints 3D counters (calls, cache hits/misses, cache size, last entry) alongside existing summaries; the dashboard HTML reflects the same metrics when run in server mode.
- Cycle enforcement: `module_relational_adapter.attach_spatial_relational_state()` skips additional engine calls once the per-cycle budget is exhausted, returning `status=skipped` with `reason=3d_call_limit_reached` and preserving the raw `spatial_measurement` payload.
- Verification: `python -m pytest tests/test_3d_cache_and_limits.py -q` and `python run_eval.py --with-3d` ensure cache hits, TTL expiry, and limit handling remain stable (3D metrics are printed in the eval summary).

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

## Section 1: Information Processing Architecture

The AI Brain organizes storage, measurement, and scheduling through a layered memory model that keeps ephemeral and durable data separated while allowing the active pipeline to orchestrate work deterministically.

### Memory Hierarchy
- **Temporary Queue**: short-lived staging area for new observations awaiting evaluation.
- **Active Processing Space**: execution context for the current thinking cycle that coordinates module calls and tracks in-flight state.
- **Long-Term Storage**: durable repository partitioned into:
  - *Event Sequence Records*: chronological logs of observations and outcomes.
  - *Conceptual Knowledge Base*: semantic graph of concepts, attributes, and relationships.
  - *Operational Pattern Library*: reusable procedures, toggles, and plans.

### Storage Implementation
- Embedding vectors support similarity and synthesis lookups.
- Hierarchical indexes provide deterministic retrieval paths.
- Compression policies bound storage footprints without losing fidelity.
- Redundant snapshots maintain recovery options across runs.

### Operational Functions
- **Store Information**: persist new items, update occurrence counts, and surface them to the active pipeline.
- **Repeat Information**: replay cached material to reinforce or validate conclusions.
- **Measure Information**: score items with deterministic analyzers, then flag, defer, or discard.
- **Want Awareness & Want Information**: monitor repetition patterns, objectives, and specificity triggers to request more context.

### Pseudocode Reference

```text
FUNCTION StoreInformation(data, repo_root):
    path = FileSystem.resolve_path(repo_root, data.category)
    IF FileSystem.exists(path, data.id):
        FileSystem.increment_count(path, data.id)
    ELSE:
        FileSystem.write(path, data.id, data.content)
        FileSystem.set_count(path, data.id, 1)
    TemporaryQueue.add(data)
    ActiveProcessingSpace.observe(data)
    RETURN confirmation

FUNCTION RetrieveInformation(criteria, repo_root):
    IF criteria == "recent":
        RETURN TemporaryQueue.fetch()
    ELSE IF criteria == "current":
        RETURN ActiveProcessingSpace.fetch()
    ELSE:
        RETURN FileSystem.search(repo_root, criteria)
```

### File System Layout

```
AI_Algorithms/
  TemporaryQueue/         # short-term staging files
  ActiveSpace/            # snapshots of current activities
  LongTermStore/
    Events/               # event-sequence records
    Semantic/             # conceptual knowledge base
    Procedural/           # operational pattern library
    SeedData/             # initialization corpus
    Objectives/           # ideology and guardrail definitions
```

Each stored item uses a unique `data.id` and metadata fields such as `occurrence_count`, ISO timestamps, labels, and schedule markers.

### Measurement Module

```text
FUNCTION MeasureInformation(data, repo_root, threshold):
    occurrence = FileSystem.get_count(repo_root, data.id)
    score = Analyzer.evaluate(data, occurrence)
    IF score >= threshold:
        Scheduler.flag(data)
    ELSE:
        FileSystem.mark_discard(repo_root, data.id)
    RETURN score
```

### Awareness Module

```text
FUNCTION AwarenessModule(data_id, occurrence_count):
    IF occurrence_count > 1:
        Trigger information_seeking(data_id)
    Validate ideological_correctness(data_id)
    RETURN confirmation
```

### Scheduling Module

```text
FUNCTION SchedulingModule(data):
    label = create_label(data)
    future_event_time = set_timer(label, minutes_from_now)
    FileSystem.update(data.id, label, future_event_time)
    RETURN label
```

### Integration Loop

```text
FUNCTION ProcessIncomingData(data, repo_root):
    StoreInformation(data, repo_root)
    MeasureInformation(data, repo_root, threshold)
    AwarenessModule(data.id, data.occurrence_count)
    SchedulingModule(data)
    RETURN confirmation
```

### Initialization and Seed Data

The system loads a seed corpus during bootstrap to avoid cold-start behavior:

- `LongTermStore/SeedData/`: baseline mathematical, logical, and structural facts.
- `LongTermStore/Procedural/`: reflex templates and operational blueprints.
- `LongTermStore/Objectives/`: ideology constraints and right-judgment rules.
- Optional connectors enable deterministic internet search or LLM queries when policies allow.

Example seed record:

```json
{
  "id": "logic001",
  "content": "Mathematical Operators: +, -, *, /",
  "occurrence_count": 1,
  "timestamps": ["2025-12-12T00:55:00Z"],
  "labels": ["seed", "foundational"]
}
```

### RelationalMeasurement Flow

```text
FUNCTION RelationalMeasurement(data_id, content, category, subject_id):
    context = {
        subject: ActiveSpace.fetch_subject(subject_id),
        activity: ActiveSpace.fetch_recent_activity(),
        objectives: ObjectivesModule.get_all(),
        index: LongTermStore.index()
    }

    StoreInformation(data_id, content, category)

    parallel_checks = {
        similarity: Analyzer.similarity(content, context.subject, context.index),
        familiarity: Analyzer.familiarity(data_id),
        related_items: LongTermStore.search_related(content, k=10),
        usefulness: Analyzer.usefulness(content, context.objectives, context.activity),
        synthesis: Analyzer.synthesis_potential(content, context, related_items),
        objective_relation: Analyzer.compare_against_objectives(content, context.objectives),
        awareness_trigger: AwarenessModule.trigger_if_repetition(data_id),
        validation: AwarenessModule.validate_response(data_id)
    }

    relation_labels = Collector.merge(parallel_checks)

    ToggleModule.route(data_id, relation_labels)
    SchedulingModule.flag(data_id, relation_labels, minutes_from_now=10)
    log_activity("relational_measure", data_id, relation_labels)
    RETURN relation_labels
```

## Collector Module (module_collector.py)

The Collector coordinates multi-window execution and consolidates module outputs for every relational measurement run.

### Overview
- Applies objective labels (measurement, awareness, synthesis, etc.) to choose which modules run.
- Persists standardized results with `module`, `status`, `timestamp`, `summary`, `details`, `duration_ms`, and `run_id`.
- Optionally merges collector output back into semantic records while keeping per-run archive files.

### Configuration

`config.json` controls collector behavior:
```json
"collector": {
  "max_terminals": 8,
  "timeout_seconds": 15,
  "modules_allowlist": [
    "module_measure",
  ],
  "merge_outputs": true,
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
  },
  "enable_resource_metrics": true,
  "activity_summary_level": "detailed",
  "strategy_overrides": {
    "module_scheduler": "replace",
    "module_select": "summarize"
  }
}
```

### Output Schema

```json
{
  "module": "module_measure",
  "status": "completed",
  "timestamp": "2025-12-13T06:05:00Z",
  "summary": {
    "similarity": 0.85,
    "usefulness": "useful_now"
  },
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

### Usage

Run a collector plan directly:

```powershell
cd <repo-root>
python -c "from module_collector import collect_results; print(collect_results({'modules': ['module_measure', 'search_internet'], 'terminals': 2}, 'demo006'))"
```

Invoke through `RelationalMeasurement` for end-to-end behavior:

```powershell
cd <repo-root>
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo006', 'keyword good synthesis', 'semantic'))"
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo007', 'keyword good synthesis', 'semantic'))"
python -c "from module_integration import RelationalMeasurement; print(RelationalMeasurement('demo008', 'keyword advanced scheduler', 'semantic'))"
```

### Observability
- Collector outputs append to semantic records (`collector_outputs`) and update `collector_metrics`.
- `ActiveSpace/activity.json` captures run summaries through `log_collector_run`.
- Optional resource metrics report CPU duration, I/O bytes, and window counts per run.

### Troubleshooting
- Increase `timeout_seconds` or individual `module_timeouts` if subprocesses exceed limits.
- Adjust `merge_strategy`, `de_dupe`, and `history_cap` to manage record growth.
- Set `dry_run: true` to validate plans without executing modules.
- Confirm every module is allowlisted; non-listed entries are skipped.

### Roadmap
- Richer scheduler actions (reschedule, cancel, prioritization).
- Ranking rationales surfaced from `module_select`.
- Metadata enrichment before storage persistence.
- Expanded resource hints for performance tuning.

### API Reference Examples
- `scheduler.reschedule_task(semantic_file, new_time) -> {status, new_time, task_id}`
- `scheduler.cancel_task(semantic_file, task_id) -> {status, task_id}`
- `scheduler.set_priority(semantic_file, task_id, priority) -> {status, task_id, priority}`
- `select.select_information(semantic_file) -> {ranking: [{id, relevance_score, reason_codes, objective_alignment}]}`
- `storage.store_information(data_id, content, category)` accepts `metadata` with `{source_chain, tags, provenance: {run_id, module}}`.

### Collector Roadmap

| Stage | Input Source | Action | Output / Persistence |
| --- | --- | --- | --- |
| Objectives | LongTermStore/Objectives/*.json | Labels guide procedural matching (measurement, synthesis, awareness) | Objective set loaded into memory |
| Procedural Match | module_tools.procedural_match() | Builds plan (modules list, terminal count, labels) | Plan object `{modules, terminals, labels}` |
| Collector Invocation | module_integration.RelationalMeasurement | Calls `collect_results(plan, data_id, content)` | Spawns up to eight subprocesses |
| Module Execution | module_measure, module_awareness, search_internet, etc. | Each subprocess runs assigned module function | Standardized outputs `{module, status, summary, details}` |
| Collector Outputs | module_collector.py | Aggregates results, enforces schema, handles errors/timeouts | `ActiveSpace/collector_<id>.json` |
| Merge into Records | LongTermStore/Semantic/<id>.json | Appends `collector_outputs`, updates `collector_metrics` | Item record enriched with execution trace |
| Observability | ActiveSpace/activity.json | Logs run summaries, metrics, resource usage | Activity log for monitoring and debugging |
---
