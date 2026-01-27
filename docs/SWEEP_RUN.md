# Sweep Runner (Adversarial + Tuning)

This repo includes an **optional**, **budget-capped**, **deterministic** sweep runner to explore behavior across the adversarial scenarios S1–S6.

Use it when:
- You changed verifier / error-resolution logic and want a quick sanity check.
- You changed tuning knobs and want to see how scenario outcomes shift.

It is **not required** for normal runs or for `run_eval.py`.

## Quick start

### Option A (recommended): use the real runner

```powershell
py -3 scripts\adversarial_sweep.py --out-dir TemporaryQueue\adversarial_sweep --budget 60 --deterministic
```

Outputs:
- `TemporaryQueue/adversarial_sweep/sweep_results.csv`
- `TemporaryQueue/adversarial_sweep/reports/adversarial_report_*.json`

Canonical per-run report filename pattern:

`adversarial_report_{scenario}_{cell_id}_r{repeat}.json`

### Option B: Copilot-plan wrapper path (`tools/...`)

This wrapper exists to match the original Copilot rollout plan; it delegates to `scripts/adversarial_sweep.py`.

```powershell
py -3 tools\adversarial_sweep_native.py --out-dir sweep_out --grid-file tools\sweep_defaults.json --repeats 1 --budget 20 --deterministic
```

## Custom grids

Grid file format (JSON):

```json
{
  "S1_small_noise": {"measurement_delta": [0.01, 0.05], "variance": [1e-6], "n_samples": [128, 256]},
  "S5_rollback_storm": {"max_retries": [2, 3], "variance": [10000.0, 1000000.0]}
}
```

Then run:

```powershell
py -3 scripts\adversarial_sweep.py --grid-file tools\sweep_defaults.json --budget 120 --deterministic
```

## Viewing results

### Dashboard (recommended)

Open `dashboard.html` and load:
- the generated `sweep_results.csv` via the file picker
- and/or the per-run `adversarial_report_*.json` files

Note: `dashboard.html` can also auto-try `TemporaryQueue/sweep_results.csv`, so if you want auto-load you can run the sweep with `--out-dir TemporaryQueue` (but that will write `reports/` directly under `TemporaryQueue`).

### CSV → HTML (no deps)

```powershell
py -3 tools\sweep_to_html.py --csv sweep_out\sweep_results.csv --out sweep_out\sweep_summary.html
```

## Verify outputs (optional)

To assert that `sweep_results.csv` references real report files, the per-run filenames match the canonical pattern, and (optionally) two runs are deterministic-equal ignoring `report_file`, use:

```powershell
py -3 tools\verify_sweep_outputs.py --sweep-dir TemporaryQueue\adversarial_sweep
py -3 tools\verify_sweep_outputs.py --sweep-dir out_a --compare-dir out_b
```

## Related docs

- See `index.html` → “Rollout Helpers (Optional)” for copy/paste commands.
- See `TUNING_GUIDE.md` for the tuning/sweep workflow.
