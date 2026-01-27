# Adversarial harness run plan and results template (v1)

## Latest local run (2026-01-26)

- Branch: `main`
- Commit: `d93e387`
- Determinism config: `config.json > determinism.deterministic_mode = true`
- Artifacts:
  - `pytest_adversarial.out`
  - `run_eval.out`
  - `determinism_check.out`
  - `adversarial_run_index.json`
  - Reports: `TemporaryQueue/adversarial_report_*.json` (S1–S6)

---

## Purpose
Run the adversarial harness (scenarios S1–S6) in deterministic mode, collect reports and eval outputs, and produce a concise diagnostics bundle for follow‑up work.

---

## Quick run checklist for VS Code agent or local terminal

1. Switch to intended branch and confirm latest commit hash.
2. Ensure config: set `determinism.deterministic_mode` to `true` in `config.json`.
3. Install dependencies:
   - Windows PowerShell (recommended here):
     - `py -3 -m venv .venv`
     - `./.venv/Scripts/python.exe -m pip install -U pip`
     - `./.venv/Scripts/python.exe -m pip install -r requirements.txt`
     - `./.venv/Scripts/python.exe -m pip install pytest`
4. Run adversarial tests:
   - `./.venv/Scripts/python.exe -m pytest tests/test_adversarial.py -q | Tee-Object -FilePath pytest_adversarial.out`
5. Run eval suite:
   - `./.venv/Scripts/python.exe run_eval.py 2>&1 | Tee-Object -FilePath run_eval.out`
6. Run deterministic reproducibility check:
   - `./.venv/Scripts/python.exe -c "from module_adversarial_test import run_scenario; r1=run_scenario('S1_small_noise', deterministic_mode=True); r2=run_scenario('S1_small_noise', deterministic_mode=True); print('provenance_equal:', r1.get('provenance_snapshot')==r2.get('provenance_snapshot'))" | Tee-Object -FilePath determinism_check.out`
7. Generate reports for all scenarios (S1–S6):
   - `./.venv/Scripts/python.exe scripts/run_adversarial_bundle.py | Tee-Object -FilePath adversarial_bundle.out`

---

## Expected acceptance criteria

- All adversarial tests run; tests either pass or failing tests are reported with tracebacks.
- Determinism check prints `provenance_equal: True`.
- Eval gates `logic_adversarial_report_shape`, `logic_adversarial_deterministic_repro`, and `logic_adversarial_escalation_policy` pass (or failing gates are listed).
- Reports for each scenario exist and include `scenario_id`, `seed_obj`, `provenance_snapshot`, `result`, and `report_file`.

---

## Report JSON schema (what each `adversarial_report_{scenario}.json` should contain)

```json
{
  "scenario_id": "S1_small_noise",
  "deterministic_mode": true,
  "seed_obj": {"scenario":"S1_small_noise","seed":"adversarial_global_seed_v1"},
  "start_ts": 0.0,
  "result": {},
  "end_ts": 0.0,
  "provenance_snapshot": ["event_id_1","event_id_2"],
  "report_file": "adversarial_report_S1_small_noise.json"
}
```

Required fields: `scenario_id`, `deterministic_mode`, `seed_obj`, `result`, `provenance_snapshot`, `report_file`.

---

## What to include in a follow-up message after running

- One-line project state: branch name and commit hash.
- Attach or paste:
  - `pytest_adversarial.out`
  - `run_eval.out` (or last 200 lines)
  - `TemporaryQueue/adversarial_report_S1_small_noise.json` (and any other scenario reports)
  - `temp_12.md` excerpt if needed
- Determinism check result: the printed `provenance_equal` boolean.
- If tests failed: the failing traceback and the file/line for the first failure.

---

## Troubleshooting quick fixes

- Missing module/symbol: share the `ImportError`/`AttributeError` and the file that raised it.
- Slow tests due to MC sampling: reduce sample size in `module_error_resolution.py` or run a single scenario first.
- Provenance log too large: provide a short excerpt of the last 200 events and the path to the full log.
