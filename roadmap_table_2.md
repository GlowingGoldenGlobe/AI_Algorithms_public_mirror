# Roadmap Table 2 — Assessment-Oriented Progression (Copilot/LLM friendly)

Purpose: keep a **truthful, minimal, reproducible** progression plan that an external reviewer (Copilot app, VS Code Agent Mode, or any LLM) can follow without being misled by stale “planned modules”.

This roadmap is not a “wishlist”; each milestone is designed to produce **attachable artifacts** and a clear **PASS/FAIL** checkpoint.

## Rules for assessment readiness

- Prefer **existing repo commands** over new tooling.
- If a milestone introduces a new artifact or script, add an eval gate or a small unit test and log it in `temp_12.md`.
- Never embed owner/private info in committed files; use `docs/SECRETS.md` for local-only details.

## Milestones (core AI_Algorithms / AI Brain pipeline)

| Milestone | Goal | Why it helps assessment | Run (Windows PowerShell, repo root) | Expected outputs | Attach to Copilot app (minimal) |
|---|---|---|---|---|---|
| M0 — Baseline snapshot | Ensure “what exists” is documented | Prevents reviewers from assuming missing modules/features | `py -3 run_eval.py` | Updated evaluation artifacts under `LongTermStore/` and/or `ActiveSpace/` depending on current harness behavior | `README.md`, `DESIGN_GOALS.md`, `temp_12.md`, `run_eval.py` |
| M1 — Determinism evidence | Show reproducible results in deterministic mode | Makes regressions diagnosable and claims verifiable | `py -3 cli.py det-set --on --fixed-timestamp 2025-02-01T00:00:00Z --dry-run` then apply if desired | Determinism reports and stable outputs (see `RESULTS_Determinism.md`) | `config.json`, latest determinism report JSON (path from `cli.py det-report --latest`) |
| M2 — Adversarial tests (unit) | Demonstrate the adversarial harness runs and asserts expected behavior | External reviewers can validate safety/robustness without reading everything | `py -3 -m pytest tests\test_adversarial.py -q` | Pytest PASS/FAIL output | `tests/test_adversarial.py` and (if failing) failing traceback |
| M3 — Adversarial bundle (reports) | Generate concrete JSON reports for scenarios S1–S6 | Gives attachable evidence artifacts for analysis | `py -3 scripts\run_adversarial_bundle.py` | `TemporaryQueue/adversarial_report_*.json` + `adversarial_run_index.json` | One or two representative reports (e.g., one PASS and one “needs_review”) + the index file |
| M4 — Metrics sanity | Demonstrate metrics are emitted and summarize cleanly | Reviewers can connect code paths → counters | `py -3 scripts\metrics_dashboard.py --reports-dir TemporaryQueue --metrics-file metrics.json` | `TemporaryQueue/metrics.json` summary output | `TemporaryQueue/metrics.json` (or a clipped excerpt) |
| M5 — Optional targeted sweep (debug/triage) | Run a budget-capped sweep only when needed | Produces structured CSV evidence when tuning | `py -3 scripts\adversarial_sweep.py --out-dir TemporaryQueue\adversarial_sweep --budget 60 --deterministic` then `py -3 tools\verify_sweep_outputs.py --sweep-dir TemporaryQueue\adversarial_sweep --json` | `TemporaryQueue/adversarial_sweep/sweep_results.csv` + `reports/` | `sweep_results.csv` + 1–2 example report JSONs |

## Milestones (AI_Brain 3D measurement track)

This is a separate track from the top-level AI_Algorithms pipeline.

| Milestone | Goal | Where | Done when |
|---|---|---|---|
| B0 — Confirm scope | Ensure reviewers understand the 3D subsystem boundaries | `AI_Brain/README.md`, `AI_Brain/ARCHITECTURE.md` | Docs clearly explain what is and is not integrated with the top-level cycle |
| B1 — Follow current AI_Brain next-tasks list | Execute the current prioritized 3D measurement tasks | `AI_Brain/NEXT_TASKS.md` | Each task is either implemented with tests or explicitly deferred with rationale |

## “New chat” starter bundle (recommended)

When starting a new Copilot app chat for continuity, attach or link these first:

- `temp_12.md` (authoritative change log + what passed)
- `roadmap_table_2.md` (this file)
- `README.md`
- `DESIGN_GOALS.md`
- `run_eval.py`
- `config.json`

Then, if the reviewer needs more code context, regenerate a public mirror:

- `py -3 scripts/create_public_mirror.py --profile core_thinking`
- `py -3 scripts/export_copilot_app_attachments.py`

## Notes

- If a prior snapshot file (e.g., `temp_23_v2.md`) claims modules that do not exist in this repo, treat it as *non-authoritative* and prefer `temp_12.md` + this roadmap.
