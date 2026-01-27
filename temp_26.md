# temp_26.md — Continued Systematic Assessment (AI_Algorithms)

Composed: 2026-01-26

## Purpose
Continue and deepen the systematic assessment started in `temp_25.md`, focusing on:
- The activity-queue “thinking engine” (`module_activity_manager`) versus the single-record cycle (`RelationalMeasurement`).
- Determinism holes (remaining nondeterministic timestamps).
- Where “total thinking ability” is currently bottlenecked by unused stronger modules.

## Key Finding: The Repo Has a Stronger Planner Than It Uses
The repo contains a credible deterministic multi-activity loop (`module_activity_manager` + `module_verifier` + rollback-capable `module_error_resolution` in `run_cycle`), but the most commonly exercised path (`RelationalMeasurement`) still drives action selection primarily via legacy heuristics + a policy composite.

Net: your strongest “thinking” machinery exists, but isn’t the default steering wheel.

## Module Deep Dive (Additional to temp_25)

### `module_activity_manager.py` — Deterministic Activity Queue (Strong)
What it does well:
- Deterministic activity IDs (`_make_activity_id`) and stable ordering when `queue['deterministic_mode']` is set.
- Converts wants into concrete activities (`translate_wants_to_activities`) with numeric priorities.
- Enforces resource budgets deterministically (`can_allocate_resources`, `allocate_resources`, `release_resources`).
- Has a clear interface contract: injected execution functions rather than global coupling.

What’s missing / limiting:
- This queue engine isn’t yet the default orchestrator for the file-based semantic loop; `RelationalMeasurement` still directly chooses actions and schedules flags.

High leverage integration step:
- Treat `RelationalMeasurement` as “single-record ingest + measurements + want-plan emission”, and immediately hand the generated plan into `module_activity_manager` for next steps.

### `module_uncertainty.py` — Deterministic Uncertainty Primitives (Strong)
What it does well:
- Uses config-backed fixed timestamp when deterministic mode is enabled.
- Provides prefix-stable sampling (`sample_distribution_prefix`) which is essential for adaptive Monte Carlo validation.

Remaining caution:
- In nondeterministic mode, `now_ts()` uses wall clock. That’s correct, but it means any persisted `provenance.ts` fields will vary across runs if emitted during nondeterministic mode.

### `module_error_resolution.py` — Rollback-Capable Correction + Statistical Validation (Strong)
What it does well:
- Treats correction as a measurement + delta + validation problem.
- Uses uncertainty-aware confidence when uncertainty payloads are present.
- Has Think-Deeper add-ons (stable hash, deterministic timestamps when requested).

Operational note:
- Your `run_cycle` loop is the best current “self-correction executor” because it can create rollback-capable tasks and validate them.

### `module_scheduler.py` — Deterministic Scheduling (Mixed)
Strengths:
- Deterministic timestamp control exists for scheduled event times.

Gaps:
- When parsing fixed timestamps, if parsing fails it falls back to `datetime.now()` (a reasonable fallback), but this creates an implicit nondeterminism failure mode.

### `module_toggle.py` — Deterministic Policy Movement (Strong)
Strengths:
- Uses deterministic timestamps for justifications.
- Policy consumes selection score + similarity + usefulness; supports configurable thresholds.

Strategic issue:
- Policy is only as good as the inputs. If selection remains heuristic, policy is bounded by that heuristic.

### `module_ai_brain_bridge.py` — Optional 3D Measurement Adapter (Strong, but isolated)
Strengths:
- Clean adapter pattern, returns JSON-friendly measurement dict.
- Avoids hard-coded paths; reads spatial paths from record fields.

Gap:
- This measurement is not yet consistently fed into the relational_state/decision_trace as a first-class measurement signal.

## Determinism Holes (Evidence-Based)
Even with deterministic mode enabled globally, there are still a few pockets that can introduce nondeterministic artifacts:
- `module_storage._backup_existing(...)` uses wall-clock time for backup filenames.
- `module_integration` still has a couple direct `datetime.now().isoformat()` writes (e.g., procedure match timestamps) that bypass fixed timestamp.
- `module_scheduler._deterministic_now()` falls back to `datetime.now()` on parse failure.

These don’t necessarily break eval today, but they are the next sources of “same input, different output” drift.

## “Total Thinking Ability” Bottleneck Update
Compared to `temp_25.md`, the clearest bottleneck isn’t missing modules — it’s orchestration priority:
- You have Want → Activities → Verifier → Rollback-capable correction… but the primary ingest loop still jumps to a decision without consistently routing through that pipeline.

Put simply:
- The system can plan and self-correct, but it doesn’t always choose to.

## Recommended Next Steps (Actionable)
1. Orchestration unification: define a single canonical loop.
   - Option A (recommended): `RelationalMeasurement` emits plan + persists trace, then hands off to activity queue execution.
   - Option B: make `run_cycle` the main driver and treat file-based `RelationalMeasurement` as an ingest helper.

2. Determinism cleanup pass (targeted):
   - Replace remaining `datetime.now()` writes in integration with deterministic timestamp helper.
   - Decide whether backup filenames should be deterministic under deterministic_mode.

3. Policy inputs upgrade:
   - Expand policy inputs to include retrieval score components and want EVoI outputs (not just heuristic selection score).

## Status
This report (`temp_26.md`) continues the assessment beyond `temp_25.md` and identifies orchestration priority as the main limiter on “total thinking ability.”
