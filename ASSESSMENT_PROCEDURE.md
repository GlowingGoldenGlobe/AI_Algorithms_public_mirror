# Assessment Procedure (AI_Algorithms)

This repo already has an *implicit* assessment practice:

- `orchestration/project_modifications_tasks/tasks_042026_1.md` acts as the running orchestrator-owned assessment + task log for the current April corrective work (`tasks_032026_1.md`, `temp_Feb2026_1.md`, and `temp_12.md` are historical archives).
- `run_eval.py` (and the VS Code task “AI Brain: eval”) acts as the acceptance/health gate.
- `.github/copilot-instructions.md` and `AGENT.md` define the “log tasks first, then implement, then re-run eval” workflow.

This document makes that practice explicit so any VS Code agent (or human) can run periodic assessments consistently.

Operator-facing status note:

- When the user asks whether the AI Brain is running or active, use the six-section operator-facing status template in the `Required results template for “Is the AI Brain running?”` section below.
- Treat that template as mandatory for AI Brain status answers, not as optional wording guidance.

---

## Where to report assessments

- **Primary place:** append to `orchestration/project_modifications_tasks/tasks_042026_1.md` (`tasks_032026_1.md`, `temp_Feb2026_1.md`, and `temp_12.md` are historical archives).
  - Add a dated section:
    - “Assessment (YYYY-MM-DD)”
    - findings (what’s good / what’s risky)
    - recommended tasks (next actions)
  - If tasks are actionable, convert them into checklist items in `orchestration/project_modifications_tasks/tasks_042026_1.md`.

- **Navigation aid:** use the workspace map at [TemporaryQueue/filesystem_map.txt](TemporaryQueue/filesystem_map.txt) when scanning artifacts; regenerate with `./.venv/Scripts/python.exe tools/fs_map.py --max-depth 4 --out TemporaryQueue/filesystem_map.txt` if stale.

- **Optional (for long-form reports):** create a new `ASSESSMENT_YYYYMMDD.md` when the assessment is big.
  - Still add a short summary + links back into `orchestration/project_modifications_tasks/tasks_042026_1.md`.

- **Blender/orchestration corrective note:** keep April 2026 acceptance criteria intact. For current Blender work, do not treat the task as rebuilding support from scratch; treat the existing routed Blender -> measurement -> AI Brain commit path as the starting point, then preserve this order: trace the carrier chain, fix `running` semantics, prove one integrated routed path, and only then require repeatability before widening quantity.

---

## Assessment cadence (suggested)

- **Quick check:** after any meaningful code change (especially logic, determinism, storage, or policy).
- **Routine check:** daily/weekly depending on how actively you’re iterating.

### Recurring cadence for a perpetually running AI Brain

Use this schedule when the orchestrator or dashboard suite is meant to stay up across multiple operator sessions. Keep the cadence focused on the existing repo surfaces rather than inventing new probes.

| When | Run / review | Evidence to capture | Escalate when |
| --- | --- | --- | --- |
| Before start, resume, scale-up, or config change | `AI Brain: preflight (hardware limits)` or `AI Brain: preflight report (hardware limits JSON)`; `AI Brain: orchestrator status`; `AI Brain: dashboard suite (status)` or `AI Brain: ops status report (write JSON)` | Latest `TemporaryQueue/hardware_preflight.json` if written, `TemporaryQueue/ops_status.json` if written, and current `ActiveSpace/orchestrator_state.json` | Any hardware violation, `ok=false`, stale dashboard status, missing orchestrator status, or a new crash trace blocks start or resume until remediated |
| Every 15 minutes during a live run | `AI Brain: orchestrator status`; metrics snapshot via `AI Brain: metrics table`, `AI Brain: compare metrics (flush)`, or dashboard fetch; optional dashboard ping if the suite is serving | Timestamped note of orchestrator state, metrics source used, and whether dashboard/watchers were healthy | Pause and investigate if orchestrator state is missing, backlog or error counters jump materially, dashboard status goes red, or storage pressure moves toward hardware caps |
| Every 60 minutes during a live run | `AI Brain: canary checks` or `AI Brain: canary checks (safe: pause orch → canary → resume)`; refresh `TemporaryQueue/ops_status.json`; spot-check one recent semantic record and its activity mirror | Canary artifact directory under `TemporaryQueue/canary_checks/`, refreshed `TemporaryQueue/ops_status.json`, one sampled semantic record path, and the matching activity id | Pause immediately if canaries fail, sampled records show broken reason or toggle evidence, or ops status reports watcher/dashboard drift |
| At the start of each operator shift or at least daily | `AI Brain: eval (safe: pause orch → eval → resume)` or `python run_eval.py` with the orchestrator paused first; review `TemporaryQueue/metrics.json`, `TemporaryQueue/activity_scaling_latest.json`, recent orchestrator log tail, and `TemporaryQueue/eval_runs/safe_runs/safe_eval_latest.json` when the safe wrapper is used | Eval result summary, metrics snapshot path, activity scaling snapshot timestamp, safe-wrapper summary path when applicable, and any notable log lines from `TemporaryQueue/orchestrator/orchestrator.log` | Keep the orchestrator paused until resolved if eval fails, determinism regresses, the safe wrapper does not restore the prior paused state, or metrics show unexplained drift versus the last known good baseline |
| At least weekly, or sooner when reference growth, comparison-pressure, activity-capacity pressure, or tier-family backlog suggests the current family may be under-sized | Run one explicit scale-up review and, only if the gates stay green, one bounded scale-up attempt using the documented tier workflow; refresh hardware preflight, ops status, metrics, activity scaling, and any relevant 3D counters first | `TemporaryQueue/hardware_preflight.json`, `TemporaryQueue/ops_status.json`, `TemporaryQueue/metrics.json`, `TemporaryQueue/activity_scaling_latest.json`, metrics-table output if refreshed, and a task-log note stating why scale-up was attempted or deferred | Defer or roll back if preflight is not green, ops health is stale or red, determinism or eval is regressing, the candidate tier cannot stay read-only in `shadow` or `standby`, or the review cannot name one bounded knob group with a rollback path |
| After any incident, pause, resume, or rollback | Re-run preflight, orchestrator status, ops status, and either canaries or eval depending on severity before resuming unattended runtime | Before/after state snapshots, incident timestamp, rollback action taken, and the first green verification result | Escalate to deeper investigation if the same fault reappears after resume, if evidence is incomplete, or if rollback does not restore a green status |

### Minimum evidence bundle for recurring assessments

Capture these files or summaries for each recurring assessment window:

1. `ActiveSpace/orchestrator_state.json` or the output of `AI Brain: orchestrator status`.
2. `TemporaryQueue/hardware_preflight.json` when preflight is part of the window.

### Local-first retained-storage failover procedure

Use this procedure when you want external storage to remain optional until the desktop machine's local AI Brain storage reaches a reasonable limit.

1. Keep the configured mode at `storage_failover.mode = "local"` during normal operation.
2. Run `python scripts\storage_failover_assess.py --json` as the assessment step; this writes `TemporaryQueue/storage_failover_status.json`.
3. Treat the switch as warranted only when one or more of these configured limits are crossed:
   - local AI Brain storage total (`TemporaryQueue` + `ActiveSpace` + local `LongTermStore`) reaches **150 GiB**
   - local free disk falls to **15%** or lower
   - local free bytes falls to **100 GiB** or lower
4. If the assessment recommends `external` and the `E:` device is available, apply the switch with `python scripts\storage_failover_assess.py --apply --json`.
5. The applied switch moves only the managed retained-storage categories (`holding`, `semantic`, `procedural`, `event`) to `E:\AI_Brain_LiveStorage`; it does **not** turn backup archives into live state and it does **not** move `TemporaryQueue` or `ActiveSpace` off the desktop.
6. Capture the resulting `TemporaryQueue/storage_failover_status.json`, refreshed hardware preflight, and current runtime-effectiveness snapshot in the operator log whenever the mode changes.
3. `TemporaryQueue/ops_status.json` when dashboard or watcher health is relevant.
4. `TemporaryQueue/metrics.json` or `TemporaryQueue/metrics_compare.json`, with a note describing which one was reviewed.
5. `TemporaryQueue/activity_scaling_latest.json` for daily or shift-level drift review.
6. `TemporaryQueue/orchestrator/orchestrator.log` tail, plus `TemporaryQueue/orchestrator/crash_last.txt` if present.
7. One representative semantic record and matching activity id for hourly or incident spot-checks.

### Pause, rollback, and deeper-investigation rules

Pause the orchestrator before further action when any of the following happens:

1. Hardware preflight reports `ok=false` or any enforced limit violation.
2. Canary checks fail or an hourly semantic-record spot-check shows missing or inconsistent `reason_chain`, `collector_outputs`, or `toggle_justifications`.
3. `run_eval.py` fails, especially on determinism, orchestration, or persistence cases.
4. `TemporaryQueue/ops_status.json` reports `ok=false`, dashboard health goes red, or watcher freshness is stale.
5. `TemporaryQueue/orchestrator/crash_last.txt` appears or the orchestrator status shows a new crash/error loop.

Rollback or revert the last operational change before resuming unattended runtime when any of these are true:

1. The issue started after a config, policy, cadence, or deployment change and the prior known-good state is available.
2. Pause alone does not restore green preflight or ops status.
3. The same failure recurs after one guarded resume attempt.

Escalate to deeper investigation rather than immediate resume when:

1. The evidence bundle is incomplete or contradictory.
2. Metrics drift persists without an obvious config or workload explanation.
3. The problem crosses task ownership boundaries, such as sleeping-tier rehearsal behavior reserved for Task `48`.
4. You can only keep the system green by disabling core checks instead of fixing the cause.

### Scale-up review: reasons why or why not

Use this decision frame whenever the operator or orchestrator performs the weekly scale-up review window.

Benefit-first comparison rule:

1. judge a proposed increase in computation, references, categorized context, or tier quantity by the benefit it is expected to produce,
2. compare that expected benefit against the current state and against lower-cost alternatives,
3. and confirm the added quantity is actually usable by the current pipeline rather than only available in theory.

Here, usable means the repo can retrieve, compare, summarize, and review the added quantity well enough to improve results.

Extrapolation-capacity assessment rule:

1. ask how much of the needed interest-formation work the current top tier can already extrapolate across cleanly,
2. include not only direct relational measurement and current comparison, but also the follow-on interest work needed to create or expand storage, create or expand contexts, create or expand references, support 3D simulations, and coordinate tier-module activity around those results,
3. treat the current top tier as already responsible for many core functions unless evidence shows otherwise,
4. and open create-tier review only when that broader extrapolation workload is materially larger than what current top-tier upgrades can coordinate without degrading comparison, comprehension, or review quality.

Reasons to attempt a bounded scale-up:

1. The expected relational-measurement benefit is specific and observable, such as better distinction between related and unrelated contexts, stronger comparison quality, or stronger synthesis quality.
2. More comparison surfaces, reference-similarity labeling, 3D assets, 3D environments, or other comparison-ready references are expected to improve that observable result.
3. More activity or processing capacity is expected to help useful work complete well enough to improve results without changing Tier 1 semantics.
4. A candidate mirror tier, standby instance, or additional bounded parameter-system tier is ready to validate in `shadow` or `standby` while preserving read-only behavior and deterministic outputs.
5. Hardware preflight, ops health, metrics, canaries, and eval are all green enough to support a bounded observation window.
6. The review can name one exact change to test, the expected benefit, and the rollback steps if the benefit does not materialize.
7. The bounded objective now needs materially more references, materially more retained storage, or materially more simultaneous compute activity than the current family can coordinate while keeping the added quantity retrievable, comparable, and reviewable.
8. The bounded objective needs more extrapolation across interest-formation work than the current top tier can currently sustain, including measurement follow-through into storage creation, context creation, reference creation, simulation support, or module-family coordination.

Interpretation note: the repo's scale-up discussion is not about imitating transformer parameter counts directly. Here, "parameters" means bounded parameter-system choices, tier flags, mirrored instances, reference surfaces, and subsystem capacity increases that still obey the measurement-first and determinism-safe design.

Reasons not to scale up yet:

1. Hardware preflight is red, close to enforced limits, or storage pressure is high enough that added outputs would be hard to trust.
2. `TemporaryQueue/ops_status.json` is unhealthy or stale, the dashboard or watcher is drifting, or the orchestrator status is incomplete.
3. Eval, canary checks, or determinism already show regressions, so added scale would hide root-cause work rather than improve the system.
4. The candidate tier cannot remain read-only during `shadow` or `standby`, or the routing states and evidence boundaries are still ambiguous.
5. The review cannot state one exact change, the expected improvement, and the rollback steps, so the attempt would be too broad to judge cleanly.
6. The proposed scale-up is likely to worsen related-versus-unrelated discrimination, flood storage with low-value material, or otherwise reduce result quality.
7. The current need is better data quality, schema repair, or reference curation rather than more scale.
8. The current top tier or an existing group can still be upgraded to meet the bounded objective without adding a new family.
9. The proposal has no explicit upper bound on tier quantity or compute spread and is effectively asking for unbounded activity instead of one bounded family change.
10. The real gap is not family quantity but unfinished top-tier extrapolation quality over existing interest work, so the smarter action is to strengthen current measurement, storage, context, reference, or comprehension surfaces first.

Utilization questions for the review:

1. If the proposal adds references, can retrieval find them, rank them, compare them, and expose their contribution in reviewable summaries?
2. If the proposal adds computation, does the extra work improve comparison, comprehension, or answer quality rather than only adding latency or noise?
3. If the proposal adds tier quantity, does the new tier perform a distinct useful role whose benefit exceeds the best no-new-tier alternative?
4. If those utilization questions cannot be answered clearly, defer the change even if the raw quantity increase sounds promising.

### Short-window quantity and extrapolation-quality procedure

Use this procedure when the question is no longer only whether the Blender path can run, but whether the current tier-part-integrated pipeline is producing enough committed simulations over capability-relevant periods and whether those simulations are producing the expected extrapolations.

Task-list authority for this procedure:

- **Primary live authority:** `orchestration\project_modifications_tasks\tasks_042026_1.md`
- **3D ladder / execution-order reference:** `orchestration\project_modifications_tasks\task_plan_3d_composition_upgrade_032026_1.md`

Apply the following rules before recommending any throughput, scheduler, carrier, or tier-growth change:

1. Keep **quantity** and **quality** as separate assessment axes.
   - Quantity asks whether committed simulation/object throughput is improving across periods that matter to the current runtime.
   - Quality asks whether the intended or project-specified extrapolations are actually appearing in committed Blender -> measurement -> AI Brain results.

2. Keep **bounded packet proof** separate from **short-window throughput proof**.
   - Earlier tens / hundreds / thousands work proved bounded packet size and integrated commit truth.
   - It did **not** by itself prove sustained 10-second or minute-scale rate, replacement truth, or the need for more tiers.

3. Freeze first-pass mapping closure from current repo truth.
   - Use `TemporaryQueue\scheduler_composition_routing_latest.json`, `TemporaryQueue\composition_workflow_chart_latest.json`, and `module_scheduler.py` as the main mapping sources.
   - Use existing `group_id` values as the first-pass `tier_group`.
   - Do **not** pretend `tier_part` is already canonical if the repo does not emit it directly; in the first pass derive it conservatively from `workflow_part` or `mapped_slice` evidence.

4. Define truthful **wall-clock** observability before trusting short windows.
   - Do not infer 10-second throughput from deterministic timestamps alone.
   - Keep deterministic/replay-friendly time fields separate from real wall-clock throughput fields.
   - Do not claim 10-second observability if the underlying producer cadence is still only 60 seconds.

5. Choose capability-relevant periods explicitly.
   - For the current short-window effort, assess at least `10s` primary buckets, `1m` rollups, `5m` rollups, and existing `30m` continuity windows.
   - Only treat a period as authoritative when the underlying event source and cadence can actually support it.

6. Select authoritative raw sources and join keys before counting throughput.
   - Choose the raw source set first: routing evidence, receiver/runtime evidence, measurement or bridge evidence, slot-lifecycle evidence, scene/request artifacts, and AI Brain commit evidence.
   - Cross-link by request / scene / commit identity before turning those events into throughput or replacement-rate numbers.

7. Derive **replacement rate** from committed handoff truth, not from pool speed alone.
   - Benchmark turnover or slot release by itself is not enough.
   - Count replacement only when a finished object has actually reached committed handoff conditions and the next object can honestly reuse that execution slot.
   - Exclude `duplicate_replay`, `draining`, and `no_spatial_asset_path` from throughput and replacement tallies.
   - For an intentional rerun of the same bounded proof packet, pass a distinct `--run-id` to `scripts\composition_runtime_pilot.py` and `scripts\scheduler_composition_router.py` so they write into a fresh run-scoped runtime root; leave `--run-id` unset when you want deterministic replay detection to stay in force.

8. Assess **quantity** against current capabilities and know-how.
   - Increase committed throughput only as far as is reasonable for the current machine, routing truth, runtime tuple, and current implementation maturity.
   - Treat operator/runtime know-how and observability fidelity as part of the real limit, not only raw Blender capacity.
   - If the limiter is event truth, routing closure, asset coverage, replacement handoff, or observability fidelity, fix that limiter before recommending wider quantity.

9. Assess **quality of extrapolations** explicitly.
   - Define or restate what extrapolations are expected for the bounded objective under review.
   - Compare those expectations against actual committed Blender, scene, measurement, and AI Brain outputs.
   - For the current first-pass repo-local quality spec, require at least **(a)** subject-mesh parity between stored request `asset_template_ids` and committed `*.scene_manifest.json` subject-mesh entries, and **(b)** non-failing `*.validation_summary.json` status for the same bounded packet.
   - If actual extrapolations are missing, weak, or misaligned, treat that as an algorithm/integration task first rather than compensating only by increasing quantity.
   - For the current first-pass **measurement** pass, use committed requests from `TemporaryQueue\blender_composition\receiver_state.json` with `replacement_crosslink.crosslink_status = committed_handoff_completed`, then compare for that same request id: expected subject-mesh count, committed manifest subject-mesh count, validation-summary status, and AI Brain commit status.
   - Keep the measurement request-scoped and bounded; do not promote it into a richer semantic score until the repo emits stronger evidence than request / manifest / validation / commit-chain truth.

10. Keep reporting and operator visibility aligned with the assessment.
    - Propagate short-window quantity rows, exclusion/provenance state, and fallback or partial-data truth into runtime/workflow reporting surfaces.
    - Keep a fused read-only quantity/quality gate in those reporting surfaces so operators can see whether current short-window throughput evidence and committed extrapolation-quality evidence are both strong enough to inform later tuning or tier-growth review.
    - Define retention/downsampling rules for the new observability histories so the short-window layer remains usable over time.
    - Treat `10s` / `1m` / `5m` rows as latest-window evidence unless a history surface explicitly retains them; do not imply long-run continuity from the latest payload alone.
    - Treat `ActiveSpace\Observability\runtime_effectiveness_history.jsonl` as the continuity source for `30m` cadence and safe-throughput history, `ActiveSpace\Observability\scheduler_composition_routing_history.jsonl` as the continuity source for carrier-rate policy, and workflow chart/pie histories as operator-facing continuity for fused summaries.

11. Keep the final recommendation evidence-gated.
    - Only tune scheduler/routing/tier-part rates after short-window observability is truthful and validated.
    - Only recommend more tiers or wider carrier growth when named existing carriers show measured short-window insufficiency **and** extrapolation quality remains acceptable within the hardware envelope.

### Procedure: bounded quantity experiment ladder

Use this procedure when the question is not "can one proof packet commit?" but "how much Blender-backed simulation quantity can the current routed path sustain truthfully?"

1. Capture the preflight baseline first.
   - Refresh the current baseline before each packet:
     - `.venv\Scripts\python.exe scripts\hardware_limits_check.py --json`
     - `.venv\Scripts\python.exe scripts\ops_status_report.py --json`
     - `.venv\Scripts\python.exe scripts\runtime_effectiveness_report.py`
     - `.venv\Scripts\python.exe scripts\composition_workflow_chart_report.py`
   - Record whether the runtime is truly running or only waiting; control-plane liveness alone does **not** count as quantity generation.

2. Use a fresh run scope for each deliberate packet.
   - Generate a distinct `run_id` per packet and pass it to:
     - `scripts\composition_runtime_pilot.py --run-id <run_id>`
     - `scripts\scheduler_composition_router.py --run-id <run_id>`
   - Keep the same `run_id` across the pilot and routed packet for one experiment window so the resulting artifacts stay cross-linkable.

3. Run the packet in bounded order.
   - Use this command sequence:
     - `.venv\Scripts\python.exe .\scripts\composition_runtime_pilot.py --limit <pilot_limit> --run-id <run_id>`
     - `.venv\Scripts\python.exe .\scripts\mapped_workload_seeding.py --limit-records <seed_limit> --per-slice-limit <slice_limit>`
     - `.venv\Scripts\python.exe .\scripts\scheduler_composition_router.py --limit <route_limit> --max-requests-per-record <per_record_limit> --run-id <run_id>`
     - `.venv\Scripts\python.exe .\scripts\composition_workflow_chart_report.py`
   - Start with a conservative packet and only widen one axis at a time.
   - Current proven stable recipe:
     - full breadth: `--limit-records 84 --per-slice-limit 28`
     - stable pressure: `--max-requests-per-record 2`
     - thousand-scale path: repeat fresh bounded cycles with new `run_id` values instead of raising per-record pressure further
     - do **not** treat `--max-requests-per-record 3` as the default next step; the stronger pressure probe regressed request yield relative to the stable `2` setting.

4. Widen by ladder, not by guesswork.
   - Keep the packet families explicit:
     - **tens**: prove repeated routed commits without replay collapse,
     - **hundreds**: prove widened routed request volume without breaking handoff/measurement truth,
     - **thousands**: only attempt if the lower packet stays truthful and hardware-safe, preferably through repeated bounded cycles at the proven stable pressure setting instead of a stronger per-record step.
   - Do not widen scenes, objects, routed requests, and per-record pressure all at once.
   - Current repo evidence for the ladder:
     - first stable pressure rung (`--max-requests-per-record 2`): `103` routed requests
     - first repeated-cycle batch (`qty_cycle_a_*`): `430` routed requests across 5 cycles
     - second repeated-cycle batch (`qty_cycle_b_*`): `585` routed requests across 7 cycles
     - combined stable cycle total: `1015` routed requests with `quantity_status=pass`, `quality_status=pass`, and `safe_to_widen=true`

5. Collect the same evidence after every packet.
   - At minimum record:
     - pilot selected count,
     - routed record count,
     - routed request count,
     - accepted receiver count,
     - completed trigger count,
     - completed AI Brain commit count,
     - replacement-rate truth,
     - hardware pressure / preflight state,
     - quantity/quality validation state.
   - The minimum artifact set is:
     - `TemporaryQueue\composition_runtime_pilot_latest.json`
     - `TemporaryQueue\scheduler_composition_routing_latest.json`
     - `TemporaryQueue\runtime_effectiveness_latest.json`
     - `TemporaryQueue\composition_workflow_chart_latest.json`

6. Interpret bounded proof honestly.
   - `runtime.running=false` with `state=waiting` after a packet is not itself a failure if the packet committed work.
   - The quantity problem remains open when the repo can only produce isolated bounded packets and still lacks authoritative `10s` / `1m` / `5m` quantity evidence for growth review.

7. Stop widening when the limiter changes category.
   - Stop and fix the implementation instead of pushing quantity higher when the blocker is:
     - missing authoritative short windows,
     - routing closure dropping back to no useful work,
     - replacement/commit crosslink truth degrading,
     - hardware preflight violations,
     - extrapolation quality slipping.

8. Validate after each meaningful packet.
   - Focused test minimum for quantity-packet changes:
     - `tests\test_composition_runtime_pilot.py`
     - `tests\test_scheduler_composition_router.py`
     - `tests\test_runtime_effectiveness_report.py`
     - `tests\test_composition_workflow_chart_report.py`
     - `tests\test_composition_workflow_pie_live.py`
   - Add any directly touched 3D/runtime contract tests when implementation changes extend beyond those surfaces.
   - Repo gates:
     - `.venv\Scripts\python.exe .\cli.py eval --quiet`
     - `.venv\Scripts\python.exe .\run_eval.py`
   - For repeated bounded cycle batches, run a clean standalone `.venv\Scripts\python.exe .\cli.py eval --quiet` after the batch even if the live gate stayed green during the individual cycles.

9. Promote a packet only when the evidence is cumulative.
   - A higher packet is only meaningful if the previous packet remains reproducible and the resulting short-window evidence becomes more authoritative, not merely noisier.
   - If the higher packet adds routed count but not authoritative quantity windows, treat that as an observability or integration task before claiming quantity growth.

When logging or expanding future work in `tasks_042026_1.md`, keep the queue separated into at least these packet families:

- wall-clock event contract / raw-source selection
- mapping closure (`tier_group` plus conservative `tier_part`)
- short-window throughput rollups
- replacement-rate truth
- reporting / provenance / retention
- extrapolation-quality specification and measurement
- algorithm/integration improvements
- quantity-and-quality validation before tuning or tier growth

### Create-tier option: why / why not now

Use this narrower gate when the discussion is not a general scale-up, but specifically whether to create or extend a tier family now.

Create-tier comparison rule:

1. state the exact benefit expected from the new tier,
2. compare that benefit against the current system without the new tier,
3. compare it again against documentation-only, workflow-only, or non-tier improvement options,
4. confirm whether mass reference demand, retained-storage demand, or simultaneous-compute demand is the real pressure behind the request,
5. assess whether current top-tier extrapolation is already sufficient for the full interest workload around the bounded objective,
6. and confirm the added tier will be usable by the current evidence, routing, and review surfaces.

If the request is specifically about very large future tier quantity, use [task_plan_mass_create_tier_event_scaling_032026_1.md](orchestration/vscode_orchestration_gpt5/project_modifications_tasks/task_plan_mass_create_tier_event_scaling_032026_1.md) as the required general-procedure planning surface before implementation. That plan defines the expected create-tier event contract, bounded family-factory model, lifecycle states, template-versus-instance reporting split, integrated test ladder, and retirement or garbage-collection rules so mass growth is judged as a bounded scaling contract rather than as static config multiplication.

For the first factory-backed create-tier trial, require one explicit quantity rule per needed group:

1. default to one created non-serving instance for a materially pressured group,
2. allow a second instance only for one explicit paired-purpose such as alternate comparison or standby rehearsal,
3. reject larger first-event quantities unless the event contract documents the stronger bounded need,
4. and keep groups with no current measurable pressure at quantity `0` until a later event reopens them.

Preserved signed guidance reminder:

1. review the verbatim 2026-03-25 author guidance in [AGENT_ASSESSMENT.md](AGENT_ASSESSMENT.md) before deciding,
2. especially Section `1` on one bounded change with one explicit benefit model that may contain multiple linked benefits,
3. Section `2` on the future simultaneous sub-tier comprehension concept plus the narrower current precursor,
4. and Section `3` on multi-category computation pressure for create-tier decisions.

Explicit simultaneous sub-tier review question:

1. ask whether the proposed create-tier change is meant to support simultaneous matching between sub-tier-owned context, stored references, and current top-tier or Active Space activity,
2. if yes, state clearly whether the review is only about the narrower precursor already supportable by the current repo or about the fuller future simultaneous sub-tier comprehension design,
3. do not claim the fuller design as current capability unless the repo has explicit new family behavior, verification, and operator-visible evidence for it.

Choose a real create-tier option when all of the following are true:

1. The expected relational-measurement benefit is specific and observable.
2. The proposed tier change is concrete enough to implement and evaluate.
3. The tier change stays limited to what is needed for that expected benefit rather than broadening multiple structures at once.
4. Current top-tier or existing-group upgrades are no longer enough to meet the bounded objective cleanly.
5. Hardware preflight, ops health, and determinism gates are green enough to trust the added family.
6. The proposal has an explicit bounded maximum rather than implying unlimited family growth or infinite simultaneous compute.
7. The rollback steps are stated in advance.
8. The review can show that the missing capability is not merely a local weakness in current top-tier extrapolation quality, but a real family-level gap across the total needed interest work.

Architecture-update rule for real create-tier work:

1. if the new family changes the project structure, system composition, dedicated-computing modules, sub-tier grouping, or category-concentration layout, identify which architecture-facing docs must change before implementation is considered complete,
2. at minimum review the root [README.md](README.md) and [DESIGN_GOALS.md](DESIGN_GOALS.md),
3. and review [AI_Brain/README.md](AI_Brain/README.md) plus [AI_Brain/ARCHITECTURE.md](AI_Brain/ARCHITECTURE.md) whenever the bounded family affects the 3D measurement core, layered module responsibilities, or the way AI Brain subsystems are described.

Create-tier architecture-doc mapping guide:

1. update [README.md](README.md) when the change affects operator-facing structure, top-level workspace layout, family naming, or the summary of implemented behavior,
2. update [DESIGN_GOALS.md](DESIGN_GOALS.md) when the change affects target architecture, ownership boundaries, the intended intelligence loop, or the long-horizon shape of subsystems,
3. update [docs/AI_BRAIN_TIERS.md](docs/AI_BRAIN_TIERS.md) whenever the change adds or modifies a family descriptor, routing states, create-tier decision logic, or family-level verification expectations,
4. update [AGENT_ASSESSMENT.md](AGENT_ASSESSMENT.md) when the operator procedure, orchestration split, verification steps, or create-tier decision options change,
5. update [AI_Brain/README.md](AI_Brain/README.md) when the change affects the AI_Brain subsystem quick-start story, 3D core role, or user-facing description of AI_Brain capabilities,
6. update [AI_Brain/ARCHITECTURE.md](AI_Brain/ARCHITECTURE.md) when the change affects layered module responsibilities, the 3D measurement core, subsystem boundaries, or new dedicated-computing modules that attach to the AI_Brain architecture,
7. and update both the root architecture docs and the AI_Brain architecture docs when the new family crosses the root pipeline and the AI_Brain subsystem boundary.

Architecture-update record template for create-tier work:

1. candidate family or sub-tier name,
2. bounded purpose,
3. structural change type: new family, new instance, new dedicated module, changed subsystem boundary, category-concentration split, or another exact label,
4. docs updated,
5. docs intentionally unchanged,
6. reason each updated doc was touched,
7. and reason each unchanged doc did not need a change.

Choose the documentation/workflow-only option instead when any of the following are true:

1. The evidence is not yet clear enough to justify a real tier change.
2. The main gap is in the review method, operator procedure, or the before-versus-after evidence you need to capture to judge results.
3. More tier quantity would create more activity but not materially improve the next decision.
4. The current top tier already owns the needed function category, but its present extrapolation depth across storage, context, reference, or simulation follow-through is still incomplete and should be upgraded directly before a new family is proposed.

Documentation-first Tier 1 invariance review rule:

1. when a future guarded descriptor slice is being reviewed without runtime adoption, compare the descriptor in two states: present in documentation and absent or ignored,
2. require the same stated Tier 1 decisions, routing authority, scheduler expectations, and dashboard dependencies in both states,
3. fail the review if the descriptor becomes necessary to explain current live behavior,
4. use the latest safe eval summary only as background health evidence rather than as authority produced by the descriptor,
5. and keep the result as a wording-and-dependency audit until a later task explicitly opens a guarded runtime slice.

Here, `workflow` means the operator-facing run, review, and comparison steps used to judge the system, and `evidence capture` means the artifacts, metrics, and traces needed to compare results before and after a change.

If the documentation/workflow-only option is chosen, record that explicitly in the monthly log and upgrade the why/why-not guidance before scheduling any new tier implementation.

If a real create-tier option is chosen, also record which architecture-facing docs were reviewed or updated so the resulting family shape is represented in operator and architecture guidance rather than only in code or config.

### Capability-formation integration procedure

Use this procedure when a proposed AI Brain capability is not yet fully inherent in the current repo, but may become more materially understandable as measured context, storage, Active Space recurrence, and tier formation improve over time.

Quoted signed basis for this procedure:

> "matching/not_matching/not_queried; reasons; all of those must be, even if schema, comprehensible to the AI Brain via observation/computation/tiers activities/the algorithms system of simultaneous activities. So, If this is not inherint in the relational measurement future understanding it might only be absent due to the unfinished nature of the qty of computing events/tiers performing as a whole AI Brain system. This category of comprehension might become inherint by way of formation of the tiers over time, including formation of the storage and ACTIVE SPACE context available information. Therefore, the way in which the schema is implemented might be modifiable and upgradable for future scheduled notice tasks list(s) performance. How might you schedule and integrate this and similar new capabilities of the AI Brain about a procedure, also, which you might include in what already exists or otherwise compose and reference it in related files/docs. The learning and formation of the AI Brain over some period of time might be the way to consider how to make a procedure about new capabilities integration. Such that they might be form-able as the AI Brain upgrades/formulates/forms/performs."

Richard Isaac Craddock; 251-298-9158; craddock338@gmail.com; yerbro@gmail.com; 207 Hillcrest Rd Apt 133, Mobile, AL 36608; 2026-03-25

Typical examples include future schema states such as:

1. `matching`
2. `not_matching`
3. `not_queried`
4. explicit reasons or reason-comparison artifacts

Run the procedure in this order:

1. preserve the capability as signed guidance or an explicit future candidate rather than only chat memory,
2. define one provisional deterministic schema that the current AI Brain can already parse, observe, or compare,
3. record what is current, what is only a narrower precursor, and what still depends on later storage, Active Space, or tier formation,
4. schedule notice or recheck tasks instead of forcing immediate implementation when the schema is likely to improve as the system forms,
5. reopen the capability only through evidence windows that show better measurement adequacy, categorized-context support, comprehension review, reference depth, or tier-family maturity,
6. keep the first runtime form documentation-first or read-only when possible,
7. and only promote the capability toward stronger runtime authority after deterministic tests or repo-eval guards exist.

Required logging for this procedure:

1. the active monthly log entry,
2. one owning task plan,
3. the related AI_Brain future-task or learning/readiness surface,
4. and any family-candidate plan that owns the specific capability.

Review question for capability-formation candidates:

1. is the missing capability absent because the schema is wrong,
2. or because the current AI Brain has not yet formed enough measured context, stored context, Active Space recurrence, or tier activity to use the capability well?

If the answer is mostly the second case, treat the next step as schema refinement plus scheduled recheck, not as an immediate claim that the runtime already supports the fuller capability.

### External handoff review: evidence-only or acceptance-ready

Use this gate when another repo proposes new destination semantics, mirror-tier review terms, queue ownership, or long-horizon learning behavior for `AI_Algorithms`.

Start from the narrower default:

1. treat the inbound package as evidence-only,
2. record the receiving-side boundary,
3. and document which parts remain recommendations rather than local runtime authority.

Current receiving-side rule from the Visual Pipeline handoff:

1. `same_tier_later` may be accepted only as a review-only descriptive destination,
2. `bounded_scale_up_review` may be accepted only as a review trigger under the repo's existing bounded scale-up workflow,
3. `mirror_tier_review` stays deferred until one exact read-only family descriptor is documented,
4. `long_horizon_learning` stays deferred until long-horizon ownership is accepted explicitly,
5. and the safest future family candidate, if adoption is revisited later, is one read-only `interest_review_mirror` descriptor.

When that candidate is described, require the descriptor to state all of the following before implementation is considered:

1. purpose and config root,
2. exact evidence inputs,
3. exact review-only outputs,
4. invariants that keep Tier 1 authority unchanged,
5. allowed routing states limited to `shadow` or `standby` at first,
6. and a verification path that stays documentation-first, then focused tests, then eval.

Do not reopen real ownership or scale-up acceptance from an external handoff until all of the following are true:

1. repeated typed evidence appears across multiple review windows,
2. the queue shape shows a durable pattern rather than one isolated backlog,
3. one explicit bounded ownership or review decision can be named,
4. and receiving-side gates are green for hardware preflight, ops health, and eval.

If those conditions are not met, keep the handoff in documentation-first review state and request another evidence cycle or bounded reference-curation follow-through instead of accepting runtime ownership.

### Teacher-interest phase-1 receiving-side accept or defer procedure

Use this narrower procedure when the current question is no longer "what is the first phase-1 plan" but instead "what should the receiving side explicitly accept now, and what should it defer".

Run the decision in this order:

1. accept `training_interests_adapter.json` as the canonical future runtime-input boundary for later bounded receiver-pack work,
2. accept the current phase-1 active-now slice for planning and review only: `education_and_workforce_specialization_learning`, `store_and_service_operations`, `workplace_and_environment_families`, and `research_and_development_acceleration`,
3. accept `categorized_context_companion.json` only as a conditional join layer after canonical record selection,
4. accept `3d_relational_measurement_adapter.json` only when a real gap exists, such as fit ambiguity, clearance uncertainty, reachability uncertainty, route ambiguity, or viewpoint weakness,
5. defer the schedule-next teacher-interest records to later bounded packets,
6. defer Teacher ladder files, demo bundles, Four Quadrants planning material, and long-horizon objective families to review-only status,
7. defer runtime ingestion and ownership claims until the repo has the documented receiver-pack loader, origin marker, manifest-history root, companion join path, and conditional 3D gap router.

Interpretation:

1. this procedure accepts a bounded receiving-side planning contract,
2. it does not accept runtime adoption,
3. and it should be recorded as an accept-or-defer decision rather than as a family release or serving-state change.

Compact operator rule:

1. if the item stays inside the canonical phase-1 slice and does not widen authority, accept it for bounded planning,
2. if it requires conditional companion context or conditional 3D support, record the exact trigger before accepting that support,
3. otherwise defer the item to phase 2, implementation follow-through, or a later ownership review.

### Repeated external evidence recheck procedure

Use this procedure later when deciding whether an external handoff has matured enough to reopen a real receiving-side ownership review.

Purpose:

1. avoid reopening the handoff too early,
2. separate repeated cross-repo evidence from one-off examples,
3. and decide whether the next bounded step is still reference curation, one review-only adapter candidate, or one new receiving-side review.

Run this procedure only when there is new external evidence to assess.

#### Step 1: refresh the external evidence bundle

Re-read the latest external handoff package and companion docs. Prefer concrete evidence files over summary claims.

Minimum bundle to inspect:

1. the latest handoff package,
2. current interest-contract examples or sidecars,
3. current queue summaries,
4. current why-not decisions or destination recommendations,
5. and any new note that states the exact ownership question.

#### Step 2: test for recurrence rather than novelty

Do not reopen the review just because one more artifact exists.

Look for all of the following:

1. at least three real artifacts or sidecars that persist typed interest evidence,
2. recurrence across at least two separate review windows or operator sessions,
3. the same missing-reference categories or equivalent typed gaps repeating in the same few areas,
4. and a queue pattern that looks durable rather than like one isolated backlog.

If those conditions are not met, stop here and keep the handoff in deferred review state.

#### Step 3: decide what kind of pressure the evidence shows

Classify the repeated evidence as one of these:

1. reference-curation pressure,
2. review-surface or adapter pressure,
3. or a real ownership or routing-shape question.

Use the narrowest explanation that still fits the evidence.

If the repeated evidence is still explained mainly by missing or weak references, the next action should remain reference-curation follow-through rather than ownership adoption.

#### Step 4: confirm receiving-side health gates

Before reopening any real review, confirm `AI_Algorithms` is healthy enough for the decision.

Minimum gates:

1. hardware preflight is green,
2. ops status is green or otherwise current enough to trust,
3. repo eval is green,
4. and the proposed next step can be stated as one bounded decision.

If these gates are not met, do not reopen the handoff review yet.

#### Step 5: choose the smallest acceptable reopened slice

If the repeated evidence and receiving-side gates are both strong enough, choose only one bounded next step:

1. one review-only inbound evidence adapter contract,
2. one read-only `interest_review_mirror` rehearsal plan in `shadow` or `standby` only,
3. one refreshed ownership-boundary review,
4. or one refreshed deferred-review result if the evidence is still insufficient.

Do not jump directly from repeated evidence to live ownership or long-horizon runtime authority.

Adapter-contract rule:

1. prefer the review-only inbound interest evidence adapter before any family rehearsal when the main need is deterministic normalization of external evidence,
2. keep the adapter limited to evidence shaping, category rollups, and bounded review recommendations,
3. and exclude scheduler authority, queue ownership, long-horizon control, or automatic routing commands.

#### Step 6: log the outcome explicitly

Record one explicit result in the monthly task log:

1. reopened bounded receiving-side review,
2. deferred review with reasons,
3. or reference-curation follow-through requested.

When applicable, cite the exact external evidence that justified the decision.

For every scale-up review window, log one explicit outcome in the active monthly task log:

1. attempted bounded scale-up,
2. deferred scale-up with reasons, or
3. rolled back attempted scale-up with reasons.

---

## Hardware health report template

Use this template when the user requests hardware health, monitoring, or metrics.

**Hardware report (from TemporaryQueue/hardware_preflight.json, ts <timestamp>)**
- Tier [n] thru Tier [n]
- ok: <true|false>
- violations: <count>
- enforce: <true|false>
- disk_free_percent: <value>
- disk_free_bytes: <value>
- ram_available_bytes: <value or n/a>

**Latest storage delta (from TemporaryQueue/ai_brain_metrics_log.jsonl)**
- Window: <start ts> -> <end ts> (elapsed <seconds> sec ~= <minutes> min)
- Increase: <bytes> bytes, <files> files
- Rate math: <bytes> bytes / <minutes> min = <bytes/min> bytes/min; <files> files / <minutes> min = <files/min> files/min
- Per-hour estimate: <bytes/hour> bytes/hour; <files/hour> files/hour
- 4-hour window: increase since <start -> end> (~240 min): <qty> (or state insufficient window)

**Hardware monitoring options**
1. VS Code task: **AI Brain: preflight (hardware limits)** (console summary)
2. VS Code task: **AI Brain: preflight report (hardware limits JSON)** (writes TemporaryQueue/hardware_preflight.json)
3. VS Code task: **AI Brain: ops status report (write JSON)** (writes TemporaryQueue/ops_status.json)
4. Dashboard server: **/api/hardware_preflight** (generates JSON) + read TemporaryQueue/hardware_preflight.json

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

#### Required results template for “Is the AI Brain running?”

Use this exact result shape when answering the running/active question:

1. **Direct verdict** — state one of: `running`, `active but degraded`, `paused`, or `stopped`.
2. **Runtime evidence** — report these `TemporaryQueue/ops_status.json` fields:
   - `runtime.running`
   - `runtime.state`
   - `runtime.run_state_indicator`
   - `runtime.performance_state`
   - `runtime.activity_phase`
   - `runtime.activity_job`
   - `runtime.blender_process_running`
   - `runtime.simulation_signal_source`
3. **Control-plane evidence** — report:
   - dashboard `server.port_open`
   - dashboard `server.ping.ok`
   - watcher freshness / live age
   - `runtime_surfaces.running_count`
   - whether the orchestrator daemon is alive
4. **Tier module quantity results** — report active-versus-total quantities, not active-only counts. In user-facing wording, refer to **groups of tiers** and **tiers**, not families. Include these `tiers.runtime_module_counts` fields:
   - `configured_family_count`
   - `configured_instance_count`
   - `active_family_count`
   - `active_instance_count`
   - `standby_instance_count`
   - `created_instance_count`
   - `active_family_ids`
   - `active_instance_ids`
   - When totals are present, phrase the result literally as active out of configured total, for example `1 active tier out of 4 configured tiers`.
   - State explicitly that this section describes the **currently instrumented runtime-module surface**, not the full AI Brain tier population.
   - If the broader project tier baseline is relevant, report it separately instead of merging it into the runtime-module count. The current broader rollout baseline is `20004` total tiers across the named groups.
5. **Recent evidence window** — include the latest relevant timestamp from metrics or recent artifact writes.
6. **Gaps / caveats** — say explicitly when the control plane is alive but simulation evidence is absent, or when files are stale or missing.

Timestamp rule for operator-facing answers:
- Treat any ISO 8601 timestamp with a trailing `Z` as UTC.
- When the operator is reasoning in local wall-clock time, convert the cited UTC timestamp to local time before drawing before/after or elapsed-time conclusions.
- Label quoted times explicitly as `UTC` or `local time`; do not leave the timezone implicit.

Minimum rule: do not describe tier modules as running without citing the quantity fields above.

#### Procedure for “What percent of the AI Brain is running?”

Use this procedure when the user asks for a percentage rather than only a yes/no running verdict.

1. **State that the percentage is an estimate, not a literal whole-brain truth.**
   - The repo has direct evidence for runtime state, tier-family quantities, and surface health.
   - It does **not** have one authoritative field for “100% of the whole AI Brain.”

2. **Use tier module share as the primary percentage estimate.**
   - Read these fields from `TemporaryQueue/ops_status.json`:
     - `tiers.runtime_module_counts.active_instance_count`
     - `tiers.runtime_module_counts.configured_instance_count`
   - Compute:
     - `tier module running share = active_instance_count / configured_instance_count * 100`
   - This is the default answer when the user asks what percentage of the AI Brain is running.

3. **Also compute the tier family share as a secondary quantity.**
   - Read:
     - `tiers.runtime_module_counts.active_family_count`
     - `tiers.runtime_module_counts.configured_family_count`
   - Compute:
     - `tier family running share = active_family_count / configured_family_count * 100`

4. **Separate module-share estimates from true simulation evidence.**
   - Read:
     - `runtime.running`
     - `runtime.state`
     - `runtime.run_state_indicator`
     - `runtime.blender_process_running`
     - `runtime.simulation_signal_source`
   - Interpretation:
     - If `runtime.running=true` and `runtime.state="simulating"`, the AI Brain is truly running simulation work at that moment.
     - If tier share is non-zero but `runtime.running=false`, the system has active configured modules without current live simulation.

5. **Optionally report the control-plane surface share, but do not substitute it for whole-brain percentage.**
   - Read:
     - `runtime_surfaces.running_count`
     - `runtime_surfaces.surface_count`
   - Compute:
     - `control-plane surface share = running_count / surface_count * 100`
   - Use this only as supporting evidence for control-plane health.

6. **Verify the estimate before answering.**
   - Refresh `TemporaryQueue/ops_status.json` immediately before answering.
   - If process sampling and `ops_status.json` disagree at the same moment, refresh `ops_status.json` once more because bounded Blender work can cross short timing boundaries between checks.
   - Include the exact numerator and denominator in the answer, not only the rounded percentage.

7. **Answer format for the percentage question.**
   - Direct percentage estimate from tier module share.
   - The exact fraction used.
   - Whether true live simulation is currently happening.
   - Any secondary percentage that helps interpretation (tier family share or control-plane surface share).

#### Procedure for “How many tiers ought to be active?”

Use this procedure when the question is not only how many tiers are active now, but whether that active quantity is sufficient for the current AI Brain objective.

1. **Separate the three quantities first.**
   - **Full AI Brain tier baseline** — the broader project quantity, such as the current `20004` total tiers across the named groups.
   - **Current runtime-module surface** — the narrower `tiers.runtime_module_counts` values exposed in `TemporaryQueue/ops_status.json`.
   - **Needed active quantity** — the operator assessment of how many tiers should be active now for the current workload, hardware state, and implementation maturity.
   - Do not collapse those three quantities into one claim.

2. **Start from current live runtime truth.**
   - Read `TemporaryQueue/ops_status.json`:
     - `runtime.running`
     - `runtime.state`
     - `runtime.run_state_indicator`
     - `tiers.runtime_module_counts.configured_instance_count`
     - `tiers.runtime_module_counts.active_instance_count`
     - `tiers.runtime_module_counts.standby_instance_count`
     - `tiers.runtime_module_counts.shadow_instance_count` when present
   - This defines what the currently instrumented runtime-module surface is actually doing now.

3. **Use workflow chart and pie artifacts as group-quantity evidence, not as raw load math.**
   - Review `TemporaryQueue/composition_workflow_chart_latest.json`:
     - `ai_brain_group_statistics`
     - `safe_throughput_summary`
     - `quantity_quality_validation_summary`
     - `workflow_provenance_summary`
     - `observability_retention_summary`
   - Review `TemporaryQueue/composition_workflow_pie_live.json` when present.
   - Important interpretation rule:
     - pie slices are curated activity/functionality catalogs, **not runtime load shares**,
     - while `quantity`, `active_quantity`, and `serving_quantity` are the relevant fields for active-versus-needed tier assessment.

4. **Check whether the current objective actually needs more simultaneous activity.**
   - Use the current objective, routed workload evidence, throughput evidence, and recent committed activity.
   - Ask whether the limitation is truly too little simultaneous tier activity, rather than data quality, routing closure, asset coverage, observability gaps, or hardware limits.
   - Do **not** say more tiers ought to be active merely because the full AI Brain tier baseline is large.

5. **Require the widening gates to be green before saying more tiers ought to be active now.**
   - More-active-tier claims are justified only when all of these stay materially green:
     - `TemporaryQueue/hardware_preflight.json` is green,
     - `TemporaryQueue/ops_status.json` is healthy and fresh,
     - `safe_throughput_summary` supports bounded widening rather than a hold,
     - `quantity_quality_validation_summary` says current quantity and quality evidence are strong enough to inform tuning or tier-growth review,
     - and the relevant group-of-tiers contract allows more than the current serving posture.
   - If one of those gates is red, the honest answer is that more tiers may be desirable later, but they do **not** presently ought to be active.

6. **Respect the current group-of-tiers contracts.**
   - Use `docs/AI_BRAIN_TIERS.md` to check whether a group is currently serving, standby, shadow, or review-only.
   - A non-serving or review-only group is not automatically underutilized; it may be in the correct current posture.
   - Example: `schedule_mirror` is the current serving group, while `simultaneous_context_match` remains non-serving and review-only.

7. **Choose one of these literal conclusions.**
   - **Current active quantity is appropriate** — when the present serving set matches the documented contracts and no green-gated workload evidence shows a need for more simultaneous activity now.
   - **More active tiers may be needed later** — when the architecture purpose suggests wider simultaneous activity, but the current gates, workload evidence, or contracts do not yet justify activating more tiers now.
   - **More active tiers are presently warranted** — only when workload evidence shows real under-capacity and the hardware, throughput, quality, and contract gates all support one bounded widening step now.

8. **State the reason in the same answer.**
   - Name:
     - the live active quantity now,
     - the broader baseline when relevant,
     - the exact gate or evidence used,
     - and whether the current limit is architecture intent, implementation maturity, hardware, throughput proof, or contract posture.

9. **If the required chart or pie artifact is missing, refresh it rather than guessing.**
   - Refresh with:
     - `python scripts\composition_workflow_chart_report.py`
     - `python scripts\composition_workflow_pie_live.py`
   - Then reread the latest artifact(s) before deciding how many tiers ought to be active.

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

If the assessment question is specifically about drawing/composition artifacts, measurement recording, and whether measurement math is stored as memory, run:

```powershell
py -3 cli.py measurement-memory-assess
```

Interpretation:
- `measurement_recorded=true` means at least one scanned semantic record contains `relational_state.spatial_measurement`.
- `measurement_memory_persisted=true` means the repo currently has durable measurement evidence in semantic records and/or legacy `AI_Brain` spatial memory files.
- `composition_artifact_present` and `composition_bridge_output_present` distinguish persisted composition sidecars from downstream bridge attachment evidence.

If the assessment question is specifically about whether persisted spatial measurements are visually interpretable enough for a human spot-check, run:

```powershell
py -3 cli.py spatial-gallery --limit 24
```

Or use the VS Code task `AI Brain: CLI spatial gallery`.

Expected artifacts:
- `TemporaryQueue/spatial_gallery/index.html` for the operator-facing gallery page.
- `TemporaryQueue/spatial_gallery/report.json` for the summary facts.
- `TemporaryQueue/spatial_gallery/svg/` for the deterministic preview images.

What to inspect:
- `exported_preview_count` versus `total_snapshot_files` to confirm you rendered a representative sample.
- `structured_preview_count` and `extrapolated_structure_present` to confirm the exported sample includes snapshots with bridge entities, relations, or constraints instead of measurement-only payloads.
- `adequacy.reason` to confirm the sample is strong enough for a manual review; if it reports `insufficient_sample`, rerun with a higher `--limit`.
- In the SVG cards, verify the measurement panel shows stable bounds, centroid, and shape data, and the relational panel shows plausible entity, relation, and constraint counts.

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

Operator note:
- Keep a single dashboard tab open and refresh it during repeated checks. The launcher helpers now default to that single-tab procedure and will not keep spawning duplicate dashboard tabs unless you explicitly use `--force-open`.

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

1. Add tasks to `orchestration/project_modifications_tasks/tasks_042026_1.md` **before** implementing.
2. Prefer small, surgical changes.
3. After implementing, record:
   - what changed (files/symbols)
   - why
   - verification (eval output)

---

## Optional: deeper assessment

If you want the agent to do a deeper read, add a task to `orchestration/project_modifications_tasks/tasks_042026_1.md` to:
- sample N recent cycles and compute summary stats
- review objective alignment + contradiction handling rates
- identify “signal mismatches” and propose refactors
