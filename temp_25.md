# temp_25.md — Systematic Workflow/Module Audit (AI_Algorithms)

Composed: 2026-01-26

## Purpose
This report is a systematic, code-grounded audit of the current AI Brain workflow versus the intended project workflow (Store/Repeat/Measure/Want/Select/Toggle/Schedule/Integrate) and an assessment of “total thinking ability” maturity.

Scope note: this focuses on the semantic pipeline in the repo root modules. The separate `AI_Brain/` 3D subsystem is treated as an optional measurement adapter input/output.

## Executive Summary (Current State)
- The repo now has two “centers of gravity” for the cognitive loop:
  - `module_integration.RelationalMeasurement(...)` (file-based semantic cycle, produces `cycle_record`, persists decision_trace, runs collector, triggers toggle/schedule).
  - `module_integration.run_cycle(...)` (stateful activity-queue loop, integrates rollback-capable error resolution + verifier pre/postconditions).
- Determinism has been treated as a first-class invariant for most of the loop (provenance, verifier, want/retrieval, error-resolution), but there are notable pockets of non-deterministic timestamps (notably `module_objectives.*` and backup filenames in `module_storage._backup_existing`).
- “Thinking ability” is strongest in: measurement-first scoring, deterministic provenance, rollback-capable error resolution, and objective-driven retrieval primitives.
- “Thinking ability” is weakest in: selection (legacy keyword/length heuristics), objective lifecycle management (non-deterministic timestamps + limited semantics), and the lack of a single unified orchestration path (two loops with partially overlapping responsibilities).

## Workflow Truth (What Actually Runs)
### A) `RelationalMeasurement(...)` loop (semantic file pipeline)
Primary behaviors observed in `module_integration.RelationalMeasurement(...)`:
- Store: persists semantic record via `module_storage.store_and_get_path(...)` and/or direct JSON write.
- Indexing: relies on `module_tools.build_semantic_index(...)` (called from storage on store/update).
- Measure: computes signals (`similarity`, `usefulness`, `synthesis`, objective relation) and calls `module_measure.measure_information(...)` for a structured measurement report.
- Reasoning/trace: persists reasoning outputs into `record.relational_state.decision_trace` (constraints, contradictions, proposed_actions) and logs `decision_signals`.
- Want/Awareness:
  - If gated want migration is enabled: generates a structured want plan (`awareness_plan_from_record(...)`) and persists it into decision_trace.
  - Else: falls back to stub `module_awareness.awareness_plan(...)`.
- Arbiter: resolves conflicts and chooses `accepted_actions`/`rejected_actions`, then delegates movement decision to `module_toggle.decide_toggle(...)`.
- Schedule: flags review via `module_scheduler.flag_record(...)`.
- Integrate/log: persists a `cycle_record` into both `ActiveSpace/activity.json` and `LongTermStore/ActiveSpace/activity.json`.
- Collector: runs `module_collector.collect_results(...)` for sandboxed module execution and stores outputs to the record.

### B) `run_cycle(...)` loop (activity-queue pipeline)
Primary behaviors observed in `module_integration.run_cycle(...)`:
- Builds/updates a relational world state from `measure_mod.measure_world(...)` and adapter functions.
- Iterates records, measures each record (`measure_mod.measure_record`), detects errors (`error_mod.detect_error`) and creates rollback-capable resolution tasks when feature-flagged.
- Enqueues `error_resolution` activities with embedded resolution-task payloads and executes activities via an `activity_modules` mapping.
- Uses `module_want.compute_awareness_plan(...)` to produce an awareness plan given objectives, measurement gaps, errors, and synthesis opportunities.
- Integrates verifier thresholds and supports adaptive statistical validation in error-resolution.

## Component-by-Component Assessment (Workflow Fit + Maturity)
Legend: **Strong** = mostly aligned with measurement-first + determinism; **Mixed** = good core but gaps; **Weak** = present but not aligned or not used.

### Orchestration
- `module_integration.RelationalMeasurement`: **Strong** for end-to-end semantic loop; **Mixed** due to duplicated activity persistence and mixed storage paths.
- `module_integration.run_cycle`: **Strong** for activity modeling + rollback-capable error resolution + verifier integration; **Mixed** because it doesn’t fully leverage objective vectors/conceptual measurement for retrieval and selection.

### Storage / Memory
- `module_storage`: **Strong** for atomic writes, schema validation, safe paths (`sanitize_id`, `safe_join`), repetition profile, incremental index update, provenance log persistence.
- Risks / gaps:
  - `_backup_existing(...)` uses wall-clock time for backup filenames (nondeterministic side effect).
  - Some records are written/updated outside `module_storage` (direct JSON writes in integration code paths), increasing the risk of schema drift.

### Measurement
- `module_measure`: **Strong** for structured measurement report, configurable weights, decisive recommendation, and additive uncertainties.
- Gaps:
  - The base signals still include heuristic components (token similarity + usefulness stubs), but they are deterministic and progressively replaceable.

### Reasoning / Explanation
- `module_reasoning`: **Strong** (Think-Deeper artifacts exist per `temp_12.md` log) and supports deterministic distribution summaries and constraint checks.
- `decision_trace` persistence: **Strong** pattern in `RelationalMeasurement` (constraints/contradictions/proposed_actions/want_plan) but not yet fully unified across both orchestration loops.

### Retrieval
- `module_retrieval`: **Strong** as a deterministic, objective-driven retrieval engine (components + distribution + explain vectors + diversity hooks).
- Gap: `run_cycle` currently calls retrieval with a minimal query (targets + max_results) and does not supply objective_id, conceptual vectors, or constraints, so the “Think Deeper” scoring is underused.

### Selection
- `module_select`: **Weak** relative to project goals; it is still keyword/length scoring with small objective keyword boost.
- Recommendation: treat `module_select` as legacy/compat and move selection decisions to `module_retrieval.retrieve(..., return_scores=True)` (or add a thin selection adapter that delegates to retrieval scoring).

### Want / Awareness
- `module_want`: **Strong** deterministic primitives (EVoI, why vectors, typed wants), and `run_cycle` uses `compute_awareness_plan(...)`.
- `module_awareness`: **Mixed/Weak** (primarily stub logic; “ideological correctness” wording is placeholder and not aligned with repo’s measurement-first objective framing).

### Toggle / Policy
- `module_toggle`: **Strong** policy-based movement decisions with determinism support.
- Gap: policies currently depend on a mixture of legacy selection scores and measurement signals; a cleaner policy could consume retrieval score components + want EVoI outputs.

### Scheduler
- `module_scheduler`: **Strong** deterministic scheduling utilities.
- Gap: scheduler appears to be mostly record-flagging; deeper queue execution is more present in `run_cycle`’s activity queue.

### Error Resolution + Verification
- `module_error_resolution`: **Strong** rollback-capable task execution, statistical validation (fixed/adaptive), provenance logging.
- `module_verifier`: **Strong** deterministic pre/postcondition checks and validation artifacts; integrates with error-resolution.

### Collector (Sandboxed Module Execution)
- `module_collector`: **Mixed**
  - Good: allowlist, per-module timeouts, structured outputs with schema_version, deterministic timestamp support, optional resource hints.
  - Risks: subprocess execution via `python -c` increases drift risk (imports and call signatures must remain stable), and returned “details” coercion may hide shape errors.

### Determinism Controls
- `module_provenance` + config-driven fixed timestamp: **Strong**.
- Gaps:
  - `module_objectives` uses `datetime.now()` and writes objective timestamps nondeterministically.
  - `module_storage._backup_existing(...)` uses wall-clock time for backup names.

## “Total Thinking Ability” Maturity Rubric
A practical rubric for this repo’s architecture:
- **Perception / ingestion** (store+describe+index): Strong
- **Memory** (durable store + repetition profile + index): Strong
- **Measurement-first evaluation** (signals + weighted scoring + uncertainty): Strong
- **Goal/Objective alignment** (objective semantics + lifecycle + linking): Mixed
- **Planning / next-action generation** (want + awareness plan + activity queue): Strong in `run_cycle`, Mixed in `RelationalMeasurement` due to gating/stubs
- **Search / retrieval quality** (objective-driven ranking + explainability): Strong primitives, partially underused in orchestration
- **Selection / arbitration** (consistent decision policy + tie-break rules): Mixed (arbiter exists; selection inputs are partly legacy)
- **Self-correction** (error detection + rollback + statistical validation): Strong
- **Explainability / trace** (decision_trace + provenance): Strong core, but needs unification across loops

## Highest-Leverage Gaps (What’s Still Missing)
1. **Unify orchestration**: decide whether `RelationalMeasurement` or `run_cycle` is the canonical loop (or explicitly define one as “single-record cycle” and the other as “batch/queue cycle”), and standardize persistence/logging.
2. **Replace legacy selection**: move `module_select` out of the critical path; use retrieval score components and want EVoI as policy inputs.
3. **Objective lifecycle determinism**: make objective timestamps deterministic when determinism mode is on (and/or allow caller-injected timestamps).
4. **Exploit conceptual measurement**: when `relational_state.conceptual_measurement` exists, feed its vectors into retrieval queries.
5. **Reduce non-atomic / duplicated activity writes**: `ActiveSpace/activity.json` and `LongTermStore/ActiveSpace/activity.json` are both updated; standardize one location and use atomic writes consistently.

## Recommended Next Tasks (Eval-Gated)
Prioritized tasks to improve workflow alignment and “thinking ability”:
1. **Selection migration** (compat-preserving)
   - Add a retrieval-backed selection path (opt-in config) and keep `module_select` as fallback.
   - Add eval gate: selection decisions remain deterministic and stable under fixed timestamp.
2. **Objective determinism upgrade**
   - Update `module_objectives` to honor determinism fixed timestamp (like other modules do).
   - Add eval gate: objective add/update timestamps stable in deterministic mode.
3. **Orchestrator unification plan**
   - Document a single “truth” path and align `cycle_record`/`decision_trace` emission semantics.
   - Add eval gate: `decision_trace` contains required keys (constraints/contradictions/proposed_actions/want_plan) when modules are enabled.

## Notes / Non-Goals
- This report does not attempt to refactor code; it is an evidence-grounded audit.
- It does not attempt to change public CLI outputs.
