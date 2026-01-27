# Production Rollout (Adaptive Sampling)

This doc turns the staging observation window confidence into a safe, operational rollout plan.

## Goal

Enable adaptive Monte Carlo sampling in production in a gradual, monitored way, with a short rollback window.

## What is being promoted

- Config change: enable adaptive sampling (see `config.json` under `verifier.adaptive_sampling`).
- No behavior changes beyond what was already validated in staging and eval gates.

## Rollout plan (gradual)

1. **Prepare a promotion PR**
   - Enable `verifier.adaptive_sampling.enabled` behind the intended production config.
   - Include rollback notes and monitoring commands.

2. **Small-slice rollout window** ("canary") (suggested: 24 hours)
   - Start with a small blast radius (single region / small traffic slice).
   - Run the monitoring checks each cycle.

3. **Expand**
   - If canary passes, expand to a larger slice (e.g., 50% for 48 hours) then full rollout.

4. **Rollback immediately on failures**
   - Revert the flag to restore baseline behavior.
   - Open a triage item with attached artifacts.

## Acceptance thresholds

- **Sample reduction**: ≥ 30% vs baseline
- **Decision disagreement**: ≤ 1% on fixed-seed regression
- **Escalations**: at or below baseline (default expectation: 0 unexpected rollback-storm escalations)
- **Determinism spot check**: repeated deterministic runs match (ignoring `report_file` path differences)

## Monitoring commands (repeat each cycle)

```powershell
py -3 -m pytest tests\test_adversarial.py -q | tee pytest_adversarial.out
py -3 run_eval.py 2>&1 | tee run_eval.out
python metrics_dashboard.py --reports-dir TemporaryQueue --metrics-file metrics.json | tee metrics_summary.out
py -3 scripts\check_rollback_storm_escalation_gate.py --use-config
```

If you ran an adversarial sweep during the window:

```powershell
py -3 tools\verify_sweep_outputs.py --sweep-dir TemporaryQueue\adversarial_sweep --json | tee verify_sweep.out
```

## Artifacts to retain for triage

- `TemporaryQueue/metrics.json`
- Keep `pytest_adversarial.out`, `run_eval.out`, `metrics_summary.out`
- If sweeps were run: `TemporaryQueue/adversarial_sweep/sweep_results.csv` and `TemporaryQueue/adversarial_sweep/reports/adversarial_report_*.json`

## Triage workflow (if a check fails)

1. **Rollback**: set adaptive sampling enabled → false, redeploy.
2. **Collect evidence**: keep the artifacts above.
3. **Diagnose**:
   - Compare fixed vs adaptive decisions with `scripts/compare_adaptive_vs_fixed.py`.
   - Run a targeted sweep with a small budget to map the failing region.
4. **Fix**: tune `adaptive_sampling.n_min` / rollback thresholds or adjust verifier behavior.

## Where metrics come from

- Metrics are emitted via `module_metrics.py` and flushed to `TemporaryQueue/metrics.json`.
- Example: rollback-storm escalation increments `resolution_rollback_storm_escalations_total` in `module_error_resolution.py`.
- `metrics_dashboard.py` summarizes those metrics for quick review.
