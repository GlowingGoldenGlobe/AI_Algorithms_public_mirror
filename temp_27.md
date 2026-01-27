# temp_27.md — Orchestration Unification Assessment (2026-01-26)

## Why this report exists
The repo currently has **two orchestration loops** with different “thinking power” profiles:

- **`RelationalMeasurement(...)`** (module_integration): the *actual* ingestion loop used by `cli.py` and most eval paths.
- **`run_cycle(...)`** (module_integration): a *stateful* cycle that already wires in the stronger planner/executor primitives (Want → Activity Queue → Verifier hooks → Rollback-capable error resolution), but is mostly exercised by logic tests and requires interfaces that do not exist in the current production modules.

This report recommends a canonical path and a migration plan that is deterministic, eval-gated, and minimally disruptive.

---

## Ground truth: what’s wired today
### 1) Canonical entrypoint in practice: `RelationalMeasurement`
Evidence:
- `cli.py` calls `RelationalMeasurement(...)`.
- `run_eval.py` heavily uses `RelationalMeasurement(...)` for end-to-end runs.

What `RelationalMeasurement` currently does well:
- Deterministic-safe ID handling (`sanitize_id`, `safe_join`, `resolve_path`).
- Storage + minimal record bootstrapping (`store_and_get_path`, record existence checks).
- Optional attachment of relational-state augmentations (spatial adapter; conceptual measurement gating).
- Selection + toggle + scheduling + “decision_signals” logging.

Key gap:
- It **does not** route through the best planner/executor core (`module_activity_manager.run_activity_cycle` with verifier/error-resolution hooks). It performs a direct, per-record heuristic decision flow.

### 2) The stronger loop exists: `run_cycle`
`run_cycle(...)` already builds:
- Error reports → optional rollback-capable resolution tasks (feature-flagged).
- Want-plan via `module_want.compute_awareness_plan(...)`.
- Activity execution via `module_activity_manager.run_activity_cycle(...)`, with verifier context wired.

But it is not production-ready because:
- It expects a **measurement module** that implements `measure_world(context_id)` and `measure_record(record_id)`.
  - There are **no** such functions in the current `module_*.py` set (search found none), so production cannot supply a real `measure_mod` without adding an adapter.
- It expects a **storage module** that can persist state (`load_state/save_state`) in a structured way.
  - Current `module_storage.py` provides provenance log I/O, but not the state persistence API `initialize_system(...)` is designed to optionally use.

Net: `run_cycle` is the “right architecture direction”, but is currently a **harness-grade loop** unless we add adapters.

---

## Recommendation: pick a canonical loop and why
### Canonical loop (public API): keep `RelationalMeasurement`
Reason:
- It’s the callsite reality (CLI + eval).
- It already enforces path safety and record existence and is designed around file-based storage.

### Canonical execution model (internal): migrate toward Want → Activity Queue → Verifier
Reason:
- `module_activity_manager.run_activity_cycle(...)` is the strongest “thinking engine” in the repo: it provides deterministic ordering, explicit preconditions, resource accounting, and post-verification artifact hooks.
- The repo’s best correctness machinery (rollback-capable error resolution, verifier policy) is already modeled in that style.

Therefore:
- **Do not** flip the repo to `run_cycle` directly.
- **Do** introduce an adapter-driven internal engine and then (optionally) have `RelationalMeasurement` call it.

---

## Migration Plan (eval-gated, deterministic-safe)

### Phase 0 — Documentation + invariants (no behavior change)
Deliverables:
- Document in `DESIGN_GOALS.md` or a new `RESULTS_Orchestration.md` which loop is canonical and what invariants must hold.

Invariants:
- Default behavior stays the same unless a feature flag is enabled.
- Deterministic mode must not introduce wall-clock timestamps.
- No unsafe paths; always go through `sanitize_id`, `safe_join`, `resolve_path`.

### Phase 1 — Build adapter interfaces (still no behavior change)
Add adapters that let the activity engine operate over the existing file-based record system:
- **Measure adapter**
  - Implements `measure_record(record_id)` by resolving a deterministic file path and calling the existing measurement primitive (`module_measure.measure_information(...)` or equivalent).
  - Implements `measure_world(context_id)` as a safe no-op initially (`([], [])`) unless the 3D world subsystem is active.
- **Storage adapter**
  - Implements minimal `load_state/save_state` backed by the existing on-disk store (or a dedicated JSON in `LongTermStore/SystemState/`).
  - Keeps it deterministic: stable filenames; atomic writes; deterministic timestamps.

This makes `run_cycle` no longer “test-only”.

### Phase 2 — Feature-flagged call path inside `RelationalMeasurement`
Add config:
- `orchestration_migration.enable_activity_cycle`: default `false`.
- `orchestration_migration.max_steps`: default `1`.

When enabled:
- After `RelationalMeasurement` stores the record and computes decision context, it:
  - Builds a Want-plan via `module_want.compute_awareness_plan(...)` using the record’s context (objectives, error summary if available, synthesis opportunities).
  - Runs `module_activity_manager.run_activity_cycle(...)` with module mappings:
    - `retrieve` → existing retrieval module (initially can target the record itself or a small in-memory subset).
    - `measure` → measure adapter.
    - `error_resolution` → existing error resolution module (feature-flagged).
    - `synthesize` → existing reasoning module.
  - Writes the resulting activity artifacts back into the record under `relational_state.decision_trace.activity_cycle` (bounded history).

No change to selection/toggle decisions initially (observability-only).

### Phase 3 — Gradual authority shift (score blending)
Once Phase 2 is stable:
- Use activity/verifier outcomes as **inputs** to selection/toggle scoring (e.g., penalize items with verifier hard failures; boost items with strong postconditions).
- Keep feature-flagged and bounded (max impact per cycle, stable reasons).

---

## Required eval gates (to prevent regressions)
Add logic-suite tests in `run_eval.py`:

1) `logic_orchestration_migration_observability`
- Enable `orchestration_migration.enable_activity_cycle` (test can patch config in-memory or via temp config file if supported).
- Run `RelationalMeasurement(...)`.
- Assert the record contains an activity-cycle trace artifact (and that it is JSON-serializable).

2) `logic_orchestration_migration_deterministic`
- Determinism on with fixed timestamp.
- Run the same input twice.
- Assert stable timestamps/IDs in the recorded activity artifacts.

3) `logic_run_cycle_adapters_smoke`
- Instantiate adapters and call `run_cycle(...)` end-to-end without stubs.
- Assert it returns a state dict with `activity_queue` present.

---

## Key risks and how to mitigate
- **Interface drift**: `run_cycle` expects methods that don’t exist.
  - Mitigation: adapters; keep adapter surface minimal.
- **Behavior creep**: activity cycle changes decisions unexpectedly.
  - Mitigation: Phase 2 is observability-only; decisions unchanged until explicit Phase 3.
- **Determinism holes**: new artifacts introduce wall-clock timestamps.
  - Mitigation: thread deterministic time into adapters and use existing determinism helpers.

---

## Bottom line
- **Public canonical loop stays `RelationalMeasurement`** (because that’s what’s actually executed).
- **Internal canonical thinking model should become Want → Activity Queue → Verifier**, introduced via adapters and feature flags.
- This yields the best of both worlds: minimal disruption + a clear path to “total thinking ability” improvements without breaking the CLI/eval workflow.
