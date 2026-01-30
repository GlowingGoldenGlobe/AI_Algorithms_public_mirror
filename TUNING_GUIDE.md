# Tuning Guide (AI_Algorithms)

This repo supports tuning **policy activation thresholds** and related knobs to control when an item moves into `ActiveSpace` (activation) versus staying in `HoldingSpace` (hold) or being quarantined.

If you’re just getting started, the short version is:

1. Prefer `--dry-run` first.
2. Change a small amount at a time.
3. Re-run eval after any tuning change.

---

## What you can tune

### 1) Activation thresholds (primary)

In `config.json`, under `policy.activation`:

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

- `sel_min_ben_syn`
  - Minimum selection score required when the system has strong “beneficial + synthesis_value” signals (or objective alignment qualifies).
  - Raising this makes activation stricter (fewer items become active).
  - Lowering this makes activation easier (more items become active).

- `composite_activate`
  - Composite cutoff used when alignment is weaker and the system is relying more on a combined score.
  - Raising this reduces activations; lowering increases activations.

Important invariant:
- **Contradiction always quarantines** (overrides activation).

### 2) Similarity method (secondary)

In `config.json`, under `similarity`:

```json
{
  "similarity": {
    "method": "jaccard",
    "max_docs": 200,
    "max_terms": 2048
  }
}
```

- `method`
  - `jaccard` (default): deterministic token overlap; fast; low risk.
  - `tfidf` (optional): cosine similarity over bounded TF‑IDF vectors; still bounded for determinism.

- `max_docs`, `max_terms` (TF‑IDF only)
  - Caps to keep runtime predictable and to reduce instability.

### 3) Error-resolution statistical validation (runtime/robustness)

If you have rollback-capable error resolution enabled (`feature_flags.use_rollback_resolution: true`), you can tune how statistical validation is computed.

Note: `verifier.adaptive_sampling.enabled` only affects the rollback-capable validation path (it won’t change behavior if rollback resolution is disabled).

Preferred config location (new): `config.json > verifier.adaptive_sampling`.

In `config.json`, under `verifier.adaptive_sampling`:

```json
{
  "verifier": {
    "adaptive_sampling": {
      "enabled": false,
      "n_min": 32,
      "n0": 64,
      "n_max": 256,
      "multiplier": 2,
      "early_stop_margin": 0.01
    }
  }
}
```

- `enabled`
  - When `true`, validation uses deterministic adaptive Monte Carlo sampling.
- `n0`, `n_max`, `multiplier`
  - The sampler starts at `n0` (must be >= `n_min`) and grows by `multiplier` up to `n_max`.
- `early_stop_margin`
  - Early-stop when p-value is clearly outside the band $[\alpha - m, \alpha + m]$.

Legacy compatibility: some older setups may use `config.json > error_resolution.adaptive_sampling` (still supported).

Metrics note: error-resolution sampling counters are kept in-process. To persist them to JSON for debugging/CI, run:

```powershell
py -3 -c "from module_metrics import flush_metrics; print(flush_metrics())"
```

This writes `TemporaryQueue/metrics.json` by default.

Dashboard: to print a quick summary (avg samples, early-stop rate), run:

```powershell
py -3 scripts\metrics_dashboard.py
```

Runbook-style flags are also supported (backward compatible with `--path`):

```powershell
py -3 scripts\metrics_dashboard.py --reports-dir TemporaryQueue --metrics-file metrics.json
```

For a machine-readable summary (for scripting/log capture), run:

```powershell
py -3 scripts\metrics_dashboard.py --json
```

Compare helper (staging): to compare adaptive vs fixed decisions + sample usage on a small deterministic scenario set:

```powershell
py -3 scripts\compare_adaptive_vs_fixed.py --use-config --deterministic
```

Optional outputs:

```powershell
py -3 scripts\compare_adaptive_vs_fixed.py --use-config --deterministic --json
py -3 scripts\compare_adaptive_vs_fixed.py --use-config --deterministic --csv TemporaryQueue\compare_rows.csv
```

Sweep helper (nightly/staging): run a small parameter grid over adaptive knobs and write a CSV summary:

```powershell
py -3 scripts\sweep_adaptive_sampling_params.py --out TemporaryQueue\sweep_results.csv
```

Keep the grid small for CI budgets (use `--max-combos` and/or tight lists for `--n-max`, `--n0`, etc.).

GitHub Actions note: running this sweep in CI (especially on a schedule or with a matrix) can increase GitHub Actions usage (minutes/artifacts), depending on your GitHub plan. Recommended default is to run sweeps locally or via on-demand CI (`workflow_dispatch`) and only add a nightly schedule if you explicitly want that ongoing cost/usage.

Adversarial sweep runner (staging/debugging): run a bounded sweep across adversarial scenarios (S1–S6) to see how policy behavior changes as you vary scenario parameters.

This is **optional** and is not required for normal operation or `run_eval.py`. It’s most useful after you change verifier/error-resolution logic and want to sanity-check the “shape” of responses under controlled stress.

Default run (deterministic, budget-capped):

```powershell
py -3 scripts\adversarial_sweep.py --out-dir TemporaryQueue\adversarial_sweep --budget 60 --deterministic
```

Outputs:
- CSV summary: `TemporaryQueue/adversarial_sweep/sweep_results.csv`
- Per-run JSON reports: `TemporaryQueue/adversarial_sweep/reports/adversarial_report_*.json`

Advanced: provide your own per-scenario parameter grid JSON:

```powershell
py -3 scripts\adversarial_sweep.py --grid-file TemporaryQueue\sweep_grid.json --budget 120 --deterministic
```

CI gate (cost): to fail CI if adaptive sampling is too expensive, run:

```powershell
py -3 scripts\check_adaptive_sampling_gate.py --max-avg-n 192 --min-used 1
```

In CI we prefer config-driven execution:

```powershell
py -3 scripts\check_adaptive_sampling_gate.py --use-config
```

Optional: you can also have the gate read tolerances from `config.json` and/or environment variables.

Config (optional) under `config.json > verifier.adaptive_sampling.ci_gate`:

```json
{
  "verifier": {
    "adaptive_sampling": {
      "ci_gate": {
        "enabled": true,
        "max_avg_n": 192,
        "min_used": 1,
        "max_fixed_samples_total": null
      }
    }
  }
}
```

Then run:

```powershell
py -3 scripts\check_adaptive_sampling_gate.py --use-config
```

Environment variables (override config when `--use-config` is set):
- `AI_BRAIN_ADAPTIVE_GATE_ENABLED`
- `AI_BRAIN_ADAPTIVE_GATE_MAX_AVG_N`
- `AI_BRAIN_ADAPTIVE_GATE_MIN_USED`
- `AI_BRAIN_ADAPTIVE_GATE_MAX_FIXED_SAMPLES_TOTAL`

Agreement regression gate: to ensure adaptive sampling decisions stay aligned with fixed sampling on a small deterministic scenario set:

```powershell
py -3 scripts\check_adaptive_vs_fixed_agreement.py --use-config
```

Config (optional) under `config.json > verifier.adaptive_sampling.regression_gate`:

```json
{
  "verifier": {
    "adaptive_sampling": {
      "regression_gate": {
        "enabled": true,
        "max_disagreement_rate": 0.0,
        "min_cases": 1
      }
    }
  }
}
```

Environment variables (override config when `--use-config` is set):
- `AI_BRAIN_AGREEMENT_GATE_ENABLED`
- `AI_BRAIN_AGREEMENT_GATE_MAX_DISAGREEMENT_RATE`
- `AI_BRAIN_AGREEMENT_GATE_MIN_CASES`

Escalation gate: to fail CI when rollback-storm escalation occurs (status promoted to `needs_review` due to repeated rollbacks):

```powershell
py -3 scripts\check_rollback_storm_escalation_gate.py --use-config
```

Config (optional) under `config.json > error_resolution.rollback_storm_policy.ci_gate`:

```json
{
  "error_resolution": {
    "rollback_storm_policy": {
      "ci_gate": {
        "enabled": true,
        "max_escalations": 0
      }
    }
  }
}
```

Environment variables (override config when `--use-config` is set):
- `AI_BRAIN_ESCALATION_GATE_ENABLED`
- `AI_BRAIN_ESCALATION_GATE_MAX_ESCALATIONS`

---

## Optional: “thinking activity” quantity reporting (hardware-aware)

This repo includes an optional helper to report how many “thinking activities” are executed per cycle, by activity type:
- `measure`
- `retrieve`
- `synthesize`
- `error_resolution`

This is primarily useful when you’re considering increasing activity quantity (for “smarter/faster” behavior) but need to stay within hardware limits.

Example (deterministic eval artifact):

```powershell
py -3 scripts\activity_counts_report.py --category semantic --id eval_orch_cycle_art_001
```

Aggregate (optional; scripts-only):

```powershell
py -3 scripts\\activity_counts_report.py --aggregate --categories semantic procedural --limit 50
```

Notes:
- This is **scripts-only** and does not change runtime behavior.
- Aggregation remains **optional/off by default** (you only get it when you pass `--aggregate`).
- Scheduled-task target-category inference is also optional (single-record mode flag) because it can add disk I/O.

Rollback-storm policy: to prevent repeated rollback loops (escalate to `needs_review` after N rollbacks for the same target), configure:

```json
{
  "error_resolution": {
    "rollback_storm_policy": {
      "enabled": false,
      "max_rollbacks": 3
    }
  }
}
```
- `n_min`
  - Minimum number of Monte Carlo samples to start with.
  - Larger values reduce the chance of “borderline” cases but increase runtime.
- `multiplier`
  - Controls how conservative early-stop is.
  - Example: with `multiplier=10.0` and `alpha=0.05`, early-stop can occur when `p < 0.005` or `p > 0.5`.

Related verifier knobs (decision thresholds) live in `config.json` under `verifier`:

---

## Orchestration migration trace

These knobs affect the optional Want → ActivityQueue cycle that runs inside `RelationalMeasurement(...)` when `config.json > orchestration_migration.enable` is true.

In `config.json`, under `orchestration_migration`:

```json
{
  "orchestration_migration": {
    "enable": true,
    "max_steps": 2,
    "trace_cap": 5,
    "include_debug": true,
    "include_advisory": true,
    "include_cycle_artifact": true
  }
}
```

- `include_cycle_artifact`
  - When `true`, persists a canonical, bounded per-cycle summary under `relational_state.decision_trace.cycle_artifact` (and a small history under `cycle_artifacts`).
  - This is intended as the “one place to look” artifact tying together: inputs → plan/wants → activities → decision → verification outcomes → scheduling intent.

- `objective_influence_metrics`
  - When enabled, persists additive metrics under `relational_state.decision_trace.objective_influence_metrics` indicating whether objectives plausibly influenced retrieval/selection/scheduling.
  - This does not change decisions; it’s an observability/analysis aid.

```json
{
  "verifier": {
    "p_threshold": 0.05,
    "min_effect_size": 1e-6
  }
}
```

- `p_threshold`
  - Significance cutoff used by rollback validation (`alpha`).
- `min_effect_size`
  - Minimum absolute mean-difference required to accept a change (guards against “statistically significant but tiny” changes).

---

### 4) Orchestration migration trace (debug/observability)

If you’re working on the Want → ActivityQueue migration, you can tune the bounded trace that is written to each record at:

- `relational_state.decision_trace.activity_cycle_trace`

Config lives in `config.json` under `orchestration_migration`:

```json
{
  "orchestration_migration": {
    "enable": false,
    "max_steps": 2,
    "trace_cap": 5,
    "include_debug": true,
    "include_advisory": true,
    "soft_influence": {
      "enabled": false,
      "scale": 0.1,
      "max_delta": 0.05,
      "prevent_space_flip": true
    }
  }
}
```

- `enable`
  - When `true`, `RelationalMeasurement(...)` runs a bounded Want → ActivityQueue cycle for **observability only** (it does not change toggle/activation decisions).
- `max_steps`
  - Max number of activity steps to execute per record (hard-capped internally).
- `trace_cap`
  - Max number of traces to retain per record (older traces drop off).
- `include_debug`
  - When `true`, each trace includes a small `debug` object (bounded) with:
    - whether an error-resolution want was injected,
    - summarized want types,
    - summarized pending activity types.
  - Set to `false` if you want smaller records (at the cost of harder debugging).

- `include_advisory`
  - When `true`, the cycle also persists additive “advisory outputs” derived from the completed activities:
    - Per-trace: `activity_cycle_trace[].advisory.next_steps` and `.summary`
    - Stable location: `relational_state.decision_trace.next_steps_from_cycle` and `cycle_outcomes`
  - Set to `false` if you only want the raw trace.

- `soft_influence`
  - Optional, bounded “Phase B” blend that uses the **previous cycle** advisory outcome (currently: `cycle_outcomes.verifier_ok_rate`) to compute a small delta to `selection_score`.
  - This is designed to be safe by default:
    - `prevent_space_flip: true` means the system will not allow the adjustment to change the chosen `target_space`.
  - Output is recorded in `decision_signals[].soft_influence` for auditability.
  - Knobs:
    - `scale`: maps $(verifier\_ok\_rate - 0.5)$ into a score delta.
    - `max_delta`: absolute cap on the delta.

---

## Recommended tuning workflow

### A) Snapshot first

Before tuning thresholds, snapshot the current state:

```powershell
py -3 cli.py snapshot export .\AI_Brain_snapshot.zip
```

### B) Use the built-in tuning assistant (dry-run)

This searches ranges and suggests thresholds to hit a target activation rate:

```powershell
py -3 cli.py policy tune --target-rate 0.25 --recent 50
```

- Start with a smaller `--recent` when iterating quickly.
- Use a larger `--recent` when you want stability.

### C) Apply with explicit ranges (when ready)

```powershell
py -3 cli.py policy tune --target-rate 0.35 --recent 100 --sel-range 0.25:0.55:0.05 --comp-range 0.45:0.70:0.03 --apply
```

### D) Validate via eval every time

```powershell
py -3 cli.py eval
```

If eval fails, revert `config.json` from your snapshot or roll back your last config edits.

### E) Use tune-and-test for quick loops

This temporarily modifies thresholds, runs eval and stress, then restores config (unless `--no-restore`):

```powershell
py -3 scripts\tune_and_test.py --sel-min 0.45 --comp-activate 0.6
```

---

## Guardrails and common pitfalls

- Don’t tune while changing core scoring logic: separate “algorithm changes” from “threshold changes”.
- Keep determinism in mind: if you’re using deterministic mode, prefer stable datasets and bounded settings.
- Avoid large jumps: big threshold changes can cause oscillation in activation behavior.
- If activations are too frequent:
  - Raise `sel_min_ben_syn` first, then raise `composite_activate`.
- If activations are too rare:
  - Lower `composite_activate` first, then lower `sel_min_ben_syn`.

---

## Where tuning is referenced

- The root README has a short overview in its “Policy Tuning” section.
- The CLI exposes `policy tune`, `policy set`, and `policy apply` helpers.
