# temp_12.md — Tasks + Project Assessment (AI_Algorithms)

Date: 2026-01-25

## Log

- Completed (2026-01-27): added the Copilot app AI guide to the public mirror and ensured regeneration preserves it.
  - Created: `COPILOT.md` (root) as a copy of `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_AI_Guide.md`.
  - Updated: `scripts/create_public_mirror.py` now copies `COPILOT.md` into the mirror (when present).
  - Regenerated: `public_mirror/` (profile `core_thinking`, preserving `.git/`), confirming `public_mirror/COPILOT.md` is present.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): investigate duplicate public mirror locations; determine whether it is an error and report findings.

- Completed (2026-01-26): performed git commit operations for the current workspace changes (code + tests + docs).
  - Commits:
    - `db490fb` ("Add adaptive sampling, rollback-storm policy, and observability")
    - `4970016` ("Docs: document adversarial sweep runner")
    - `2a26c98` ("Docs: add adversarial sweep command to learn page")
    - `aeddcf4` ("Docs: document optional adversarial sweep")
  - Left untracked (not committed): `Backups/` and `adversarial_run_index.json` (generated/local artifacts)

- Completed (2026-01-26): pushed local `main` to `origin/main`.
  - Remote: (redacted)
  - Tip: repo still has local untracked artifacts (`Backups/`, `adversarial_run_index.json`, `tools/`).

- Completed (2026-01-26): committed remaining untracked items and pushed.
  - Commit: `39b5f88` ("Add sweep tools and run docs")
  - Note: `adversarial_run_index.json` paths were normalized to repo-relative to avoid machine-specific absolute paths.

- New task (2026-01-27): public mirror hygiene + completeness for Copilot app review.
  - Remove: owner-specific git remote strings from committed docs (public mirror is intended to be shareable without owner identifiers).
  - Add: missing safe files to `public_mirror` (core_thinking profile) so README/roadmap links resolve (CLI, scripts, key docs, sweep verifier).
  - Verification: regenerate mirror + exports; run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): public mirror hygiene + completeness for Copilot app review.
  - Updated: `temp_12.md` redacts the owner-specific git remote string.
  - Updated: `scripts/create_public_mirror.py` core_thinking profile now includes key docs (`docs/*`), CLI/scripts, sweep verifier, and AI_Brain docs so public reviewers can follow README/roadmap links.
  - Regenerated: `public_mirror/` (note: if `public_mirror/` is already a git repo on Windows, use `--preserve-git` to avoid `.git` file-lock errors).
  - Regenerated: Copilot app exports via `scripts/export_copilot_app_attachments.py`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-27): published updated public mirror contents.
  - In `public_mirror/`: committed and pushed mirror updates to the public repo (core_thinking completeness + doc hygiene).

- Completed (2026-01-27): mirror sanity + broken-link fix.
  - Found: `public_mirror/README.md` referenced `adversarial_run_results_v1.md` which was missing from the mirror.
  - Updated: `scripts/create_public_mirror.py` core_thinking allowlist includes `adversarial_run_results_v1.md`.
  - Regenerated and published: pushed the mirror update so the README link resolves.

- New task (2026-01-27): main repo hygiene — don’t track generated public mirror artifacts.
  - Update: `.gitignore` to ignore `public_mirror/` and Copilot exports.
  - Update: remove `public_mirror/` from main repo git index (keep files on disk; mirror is published separately).
  - Restore: any accidental deletions (workflow/templates) before the next commit.

- Completed (2026-01-27): main repo hygiene — don’t track generated public mirror artifacts.
  - Updated: `.gitignore` now ignores `public_mirror/` and only ignores `Copilot_app_Attachments_txt_files_of_py_modules/exports/` (so Copilot procedure docs can be committed).
  - Updated: removed `public_mirror/` from the main repo git index (mirror remains on disk and is published separately).
  - Restored: `.github/workflows/canary_checks.yml` and `docs/TRIAGE_TICKET_TEMPLATE.md` to avoid accidental deletions.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): document the “two repos” public mirror workflow.
  - Add: a short guide explaining main repo vs `public_mirror/` repo responsibilities and the `--preserve-git` regeneration workflow.
  - Update: mirror-generated docs (`public_mirror/README_MIRROR.md`, `public_mirror/PUBLISHING.md`) to mention `--preserve-git` and clarify that the mirror repo is published separately.
  - Update: Copilot app procedure doc to warn that `public_mirror/` is ignored in the main repo and must be updated via commits inside the mirror repo.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- In progress (2026-01-26): wire `orchestration_migration` error_resolution activity execution + add an eval gate that asserts an error_resolution activity appears when contradictions are decisive.

- New task (2026-01-26): add an owner reminder in `index.html` to update repo acquisition info later (e.g., insert public GitHub URL when available).

- Completed (2026-01-26): added owner reminder to the dashboard.
  - Updated: `index.html` Current Task card includes a reminder to update `learn.html#get-the-repo` (public GitHub URL + contact).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): add a `learn.html` section describing how a developer can obtain the project files (USB transfer, future public GitHub link placeholder, or request from the owner).

- Completed (2026-01-26): added repo acquisition guidance to `learn.html`.
  - Updated: `learn.html#get-the-repo` documents USB transfer, a future public GitHub link placeholder, and an owner contact email.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): update `learn.html` with a “what to read vs what to skip” guide (by developer experience level) and a copyable prompt to have an agent generate a tailored reading list from the repo.

- Completed (2026-01-26): added reading-tier guidance + tailored reading-plan prompt to `learn.html`.
  - Updated: `learn.html#reading` distinguishes recommended reads vs first-pass skips and includes a copyable prompt that adapts to experience level + goals.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): implement staging/rollout helper scripts (Copilot summary follow-up).
  - Add: `scripts/compare_adaptive_vs_fixed.py` helper to report sample reduction + decision agreement on deterministic scenarios.
  - Add: `scripts/sweep_adaptive_sampling_params.py` to run a small parameter grid and emit a CSV summary artifact.
  - Update: `scripts/metrics_dashboard.py` CLI to support `--reports-dir` and `--metrics-file` (backward compatible with `--path`).
  - Docs: update `TUNING_GUIDE.md` with the new helper commands.
  - Verification: run `py -3 run_eval.py` and record results.

- Completed (2026-01-26): staging/rollout helper scripts implementation.
  - Added: `scripts/compare_adaptive_vs_fixed.py` (deterministic scenario compare; supports `--use-config`, `--csv`, `--json`).
  - Added: `scripts/sweep_adaptive_sampling_params.py` (bounded grid sweep; writes CSV; forces deterministic comparisons; uses importlib to load compare helper reliably).
  - Updated: `scripts/metrics_dashboard.py` (supports `--reports-dir` and `--metrics-file`; keeps `--path` precedence).
  - Docs: `TUNING_GUIDE.md` updated with compare/sweep/dashboard commands.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): documented GitHub Actions cost/scaling notes (optional).
  - Updated: `TUNING_GUIDE.md` clarifies that scheduled sweeps are optional (run locally or on-demand) to avoid unexpected CI minutes/usage.

- Completed (2026-01-26): surfaced GitHub Actions cost/optional sweep note in `index.html`.
  - Updated: `index.html` now includes rollout-helper commands and an explicit note that scheduled CI sweeps are optional and may increase GitHub Actions usage.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): documented an optional manual GitHub Actions sweep workflow in `index.html` (description only).
  - Updated: `index.html` “Rollout Helpers (Optional)” now includes a note describing a `workflow_dispatch`-only sweep workflow that uploads `sweep_results.csv` as an artifact.
  - Constraint honored: no workflow files added.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): added rollout report template doc.
  - Added: `ROLLOUT_REPORT_TEMPLATE.md`.
  - Updated: `index.html` links the template in Quick Links.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): added an offline-friendly HTML dashboard page for metrics/adversarial reports.
  - Added: `dashboard.html` (file-picker loading for file://; Plotly charts; escalation + scenario tables).
  - Added: `dashboard_readme.txt` (usage instructions).
  - Updated: `index.html` links `dashboard.html` in Quick Links.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): add a repo-native adversarial sweep runner.
  - Add: `scripts/adversarial_sweep.py` to sweep scenario parameters (S1–S6) under a fixed budget; write per-run `adversarial_report_*.json` + `sweep_results.csv`.
  - Update: `module_adversarial_test.run_scenario` to accept optional parameter overrides and custom report filenames (defaults unchanged).
  - Update: add a copy/paste command entry in `index.html`.
  - Verification: run “AI Brain: eval” and log completion.

- Completed (2026-01-26): repo-native adversarial sweep runner added.
  - Added: `scripts/adversarial_sweep.py` (bounded sweep driver; emits `TemporaryQueue/adversarial_sweep/sweep_results.csv` + per-run reports).
  - Updated: `module_adversarial_test.py` report writing hardened with `safe_join`, and `run_scenario(...)` supports `params` + `report_name` for sweep runs.
  - Updated: `index.html` Rollout Helpers includes an adversarial sweep copy/paste command.
  - Smoke-run: verified the sweep runner writes output; fixed a docstring Windows-path escape `SyntaxWarning`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): document the new adversarial sweep runner in `TUNING_GUIDE.md` (what it’s for, when to run it, and where outputs go); re-run eval.

- Completed (2026-01-26): documented adversarial sweep runner.
  - Updated: `TUNING_GUIDE.md` now includes the `scripts/adversarial_sweep.py` command, what it’s for, and output locations.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): add a short pointer to the adversarial sweep runner in `learn.html` (new dev discoverability) and `README.md` (adversarial section), linking to `TUNING_GUIDE.md`; re-run eval.

- Completed (2026-01-26): adversarial sweep runner pointers added.
  - Updated: `learn.html` Commands section includes an optional `scripts/adversarial_sweep.py` entry and points to `TUNING_GUIDE.md`.
  - Updated: `README.md` Adversarial harness section references the sweep command and links to `TUNING_GUIDE.md`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): add the remaining sweep artifacts from the Copilot plan.
  - Add: `tools/adversarial_sweep_native.py` wrapper CLI (reuses `scripts/adversarial_sweep.py`).
  - Add: `tools/sweep_defaults.json` small default grid.
  - Add: `tools/sweep_to_html.py` CSV→HTML converter (no deps).
  - Add: `docs/SWEEP_RUN.md` usage + how to view via `dashboard.html`.
  - Verification: run “AI Brain: eval” and log completion.

- Completed (2026-01-26): added sweep artifacts from the Copilot plan.
  - Added: `tools/adversarial_sweep_native.py` (wrapper), `tools/sweep_defaults.json`, `tools/sweep_to_html.py`, `docs/SWEEP_RUN.md`.
  - Smoke-run: verified wrapper + CSV→HTML helper execute and write outputs.
  - Verification: ran VS Code task “AI Brain: eval” (PASS).

- New task (2026-01-26): standardize adversarial sweep per-run report filenames to `adversarial_report_{scenario}_{cell_id}_r{repeat}.json`, and update sweep docs; re-run eval.

- Completed (2026-01-26): standardized adversarial sweep report filenames.
  - Updated: `scripts/adversarial_sweep.py` now writes per-run reports as `adversarial_report_{scenario}_{cell_id}_r{repeat}.json`.
  - Updated: `docs/SWEEP_RUN.md` documents the canonical filename pattern.
  - Smoke-run: verified output filenames under `TemporaryQueue/adversarial_sweep_namecheck/reports/`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): create an attachable MD assessment report (project + onboarding) and upgrade `learn.html` with an “Agent Mode / LLM collaboration” section.
  - Include: paste-ready prompts (like the user’s last message), R&D investigation options, smart-vs-poor thinking rubric, module activity logic, math/3D/media considerations, and a hardware/resource checklist.
  - Add: a developer-info “request template” (what info the AI should ask for) and a copyable message template.
  - Verification: run “AI Brain: eval” after doc edits and log completion.

- Completed (2026-01-26): created attachable assessment report + upgraded `learn.html` for agent/LLM collaboration.
  - Added: `AGENT_MODE_ASSESSMENT_REPORT.md` (attachable assessment method + architecture review + paste-ready prompt).
  - Updated: `learn.html#agent-mode` (prompt templates, R&D variants, developer info request template, scaling/math/modality notes).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): add a CI “escalation gate” that fails if rollback-storm escalations occur unexpectedly (using metrics flushed to JSON), wire into `.github/workflows/ci.yml`, update docs, and re-run eval.

- Completed (2026-01-26): CI rollback-storm escalation gate added and verified.
  - Updated: `module_error_resolution.py` increments `resolution_rollback_storm_escalations_total` when the rollback-storm policy escalates to `needs_review`.
  - Added: `scripts/check_rollback_storm_escalation_gate.py` (reads `TemporaryQueue/metrics.json`, enforces `max_escalations` with config/env overrides).
  - Updated: `config.json` adds `error_resolution.rollback_storm_policy.ci_gate` defaults; `.github/workflows/ci.yml` runs the gate (forced enabled); `TUNING_GUIDE.md` documents usage/knobs.
  - Verification: ran `py -3 run_eval.py` (PASS; `determinism_suite: PASS`) and `py -3 scripts/check_rollback_storm_escalation_gate.py --use-config` (PASS).

- New task (2026-01-26): integrate a minimal “resolution executor” behavior into `module_integration.run_cycle` by persisting updated rollback-capable resolution tasks back into in-memory state and (best-effort) storage; keep behavior unchanged otherwise; re-run eval.

- Completed (2026-01-26): persisted rollback-capable resolution task updates in integration.
  - Updated: `module_integration.run_cycle` now writes the executed `resolution_task` back into `td_tasks_by_target` and the activity `metadata.resolution_task` (when present), and best-effort calls `storage.update_task` if supported.
  - Verification: ran VS Code task “AI Brain: eval” (PASS).

- New task (2026-01-26): add a one-click copy “assessment prompt” template to `index.html` so new developers can quickly ask VS Code Agent Mode or other LLMs to explain how the AI Brain thinks.

- Completed (2026-01-26): added a one-click copy “assessment prompt” to `index.html`.
  - Updated: `index.html#copilot_app` now includes a paste-ready prompt template with a Copy button.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): orchestration-migration error-resolution gate now passes.
  - Updated: `module_integration.py` broadened the trigger for injecting `want_error_resolution` to include `contradiction_signal` / `recommended_actions` (not just `decisive_recommendation`).
  - Verification: ran `py -3 run_eval.py` (PASS; `logic_orchestration_migration_error_resolution: PASS`; exit code 0).

- New task (2026-01-26): add bounded debug fields to `orchestration_migration` trace (whether error-resolution want was injected + summarized want/activity types) to make future eval failures diagnosable; re-run eval.

- Completed (2026-01-26): bounded debug fields added to `orchestration_migration` trace.
  - Updated: `module_integration.py` now records `debug.injected_error_resolution`, `debug.want_types`, and `debug.pending_activity_types` inside `relational_state.decision_trace.activity_cycle_trace`.
  - Verification: ran `py -3 run_eval.py` (PASS; exit code 0).

- New task (2026-01-26): document `orchestration_migration` tuning knobs (including an optional flag to include/omit `activity_cycle_trace.debug` fields) in `TUNING_GUIDE.md`; re-run eval.

- Completed (2026-01-26): documented `orchestration_migration` tuning knobs.
  - Updated: `TUNING_GUIDE.md` adds an “Orchestration migration trace” section with `enable`, `max_steps`, `trace_cap`, and `include_debug`.
  - Updated: `module_integration.py` respects `orchestration_migration.include_debug` (omit trace debug fields when false).
  - Updated: `config.json` now includes `orchestration_migration.include_debug`.
  - Verification: ran `py -3 run_eval.py` (PASS; exit code 0).

- New task (2026-01-26): continue the incremental project assessment; write the next assessment report (`temp_28.md`) covering remaining orchestration unification phases (from observability → advisory outputs → decision influence), risks, and proposed eval gates.

- Completed (2026-01-26): incremental assessment continuation report written.
  - Added: `temp_28.md` (what’s complete vs unfinished; next incremental phases A/B/C; suggested eval gates).

- New task (2026-01-26): implement Phase A advisory outputs from `orchestration_migration` activity cycle (additive only) and add eval gates for shape + determinism; re-run eval.

- Completed (2026-01-26): Phase A advisory outputs + eval gates.
  - Updated: `module_integration.py` now persists additive advisory outputs (`next_steps_from_cycle`, `cycle_outcomes`) derived from the activity cycle; also adds per-trace `advisory` payload (bounded, deterministic).
  - Updated: `config.json` adds `orchestration_migration.include_advisory` (default true).
  - Updated: `TUNING_GUIDE.md` documents `include_advisory` and the new advisory fields.
  - Updated: `run_eval.py` adds `logic_orchestration_migration_advisory_shape` and `logic_orchestration_migration_advisory_deterministic` gates.
  - Verification: ran `py -3 run_eval.py` (PASS; exit code 0).

- New task (2026-01-26): Phase B “soft influence” (bounded) for orchestration migration.
  - Add a feature flag to let one advisory signal (e.g., `verifier_ok_rate`) apply a small capped delta to policy inputs / decision signals (no authority flip).
  - Add eval gates: deterministic stability + no unexpected space flips on a small scenario set.

- Completed (2026-01-26): Phase B eval gates (soft influence).
  - Added: `run_eval.py` gates `logic_orchestration_migration_soft_influence_deterministic` and `logic_orchestration_migration_soft_influence_bounded_no_flip`.
  - Verification: ran `py -3 run_eval.py` (PASS; both new gates PASS; `determinism_suite: PASS`).

- Completed (2026-01-26): enrich Phase B soft-influence audit payload.
  - Updated: `module_integration.py` now includes `target_space_base`, `target_space_adjusted`, and `target_space_final` in `decision_signals.soft_influence`.
  - Updated: `run_eval.py` now asserts `target_space_final == target_space_base` for the no-flip gate.
  - Verification: ran `py -3 run_eval.py` (PASS; `logic_orchestration_migration_soft_influence_bounded_no_flip: PASS`; `determinism_suite: PASS`).

- New task (2026-01-26): run external storage backup module on request.
- Completed (2026-01-26): external storage backup completed.
  - Command: `py -3 cli.py backup --archive-root "E:\\Archive_AI_Algorithms"`
  - Output: `E:\\Archive_AI_Algorithms\\Archive_6` (220 files, manifest written).

- New task (2026-01-26): assess docs to compare the project’s smart relational measurement system against LLMs and summarize adherence to stated differences.
- Completed (2026-01-26): reviewed README/DESIGN_GOALS/assessment report and prepared a grounded comparison against LLMs with adherence notes.

- New task (2026-01-27): update AI_Brain README/ARCHITECTURE to reflect LLM comparison and adherence notes; run eval and log results.
- Completed (2026-01-27): updated AI_Brain README/ARCHITECTURE with positioning vs LLMs and adherence notes.
  - Updated: `AI_Brain/README.md`, `AI_Brain/ARCHITECTURE.md`.
  - Verification: ran VS Code task “AI Brain: eval” (completed; collector outputs saved; exit code 0).

- New task (2026-01-27): update learn.html and index.html to describe the project’s measurement-first, non-LLM smartness and rational loop; run eval and log results.
- Completed (2026-01-27): updated website pages with non-LLM positioning and rational/measurement-first summary.
  - Updated: `learn.html`, `index.html`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): add a Copilot App “uniqueness vs LLMs” page in exports and update AGENT guide(s) to align; run eval and log results.
- Completed (2026-01-27): added Copilot App uniqueness page and updated AGENT guides with non‑LLM positioning guidance.
  - Added: `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_Uniqueness_Guide.md`.
  - Updated: `AGENT.md`, `Copilot_app_Attachments_txt_files_of_py_modules/exports/AGENT.md`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): rename the Copilot app guide page and rewrite as an AI guide with normalized format, incorporating project/architecture/AI_Brain guidance; run eval and log results.
- Completed (2026-01-27): renamed and rewrote the Copilot app AI guide with normalized format and project/architecture guidance.
  - Renamed: `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_Uniqueness_Guide.md` → `CopilotApp_AI_Guide.md`.
  - Updated: `CopilotApp_AI_Guide.md`, `AGENT.md`, `Copilot_app_Attachments_txt_files_of_py_modules/exports/AGENT.md`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): incorporate external Agent Mode assessment upgrades (from `AGENT_MODE_ASSESSMENT_REPORT.md`).
  - A) Canonical cycle artifact: persist one schema-validated per-cycle summary tying inputs → retrieval → reasoning artifacts → decision → verification → scheduling, with provenance pointers.
  - B) Objective-centric measurement metrics: add measurable counters like “objective influenced retrieval/selection/scheduling” and document how to inspect them.
  - C) Beginner inspection path: add a 5-minute walkthrough (run → open 2 files → interpret ~10 fields), aligned with `learn.html`/`TEMP_TRAIL_INDEX.md`.

- Completed (2026-01-26): canonical cycle artifact schema (Phase C groundwork).
  - Updated: `module_integration.py` now persists `relational_state.decision_trace.cycle_artifact` (and bounded `cycle_artifacts`) tying inputs → plan → activities → decision → verification → scheduling.
  - Updated: `config.json` adds `orchestration_migration.include_cycle_artifact` (default true); `TUNING_GUIDE.md` documents it.
  - Updated: `run_eval.py` adds gates `logic_orchestration_migration_cycle_artifact_shape` and `logic_orchestration_migration_cycle_artifact_deterministic`.
  - Verification: ran `py -3 run_eval.py` (PASS; both new gates PASS; `determinism_suite: PASS`).

- Completed (2026-01-26): objective-centric influence metrics.
  - Updated: `module_integration.py` now persists additive `relational_state.decision_trace.objective_influence_metrics` when enabled.
  - Updated: `config.json` adds `orchestration_migration.objective_influence_metrics` defaults; `TUNING_GUIDE.md` documents usage.
  - Updated: `run_eval.py` adds gates `logic_objective_influence_metrics_shape` and `logic_objective_influence_metrics_deterministic`.
  - Verification: ran `py -3 run_eval.py` (PASS; both new gates PASS; `determinism_suite: PASS`).

- New task (2026-01-26): add a beginner 5-minute walkthrough (run -> open 2 files -> interpret key fields) to `learn.html`, aligned with `TEMP_TRAIL_INDEX.md` and `AGENT_MODE_ASSESSMENT_REPORT.md`; re-run eval.

- Completed (2026-01-26): beginner 5-minute walkthrough added.
  - Updated: `learn.html#walkthrough` now documents a practical run → inspect path using two deterministic eval artifacts (`LongTermStore/Semantic/eval_orch_cycle_art_001.json` and `LongTermStore/Semantic/eval_obj_infl_001.json`).
  - Updated: `TEMP_TRAIL_INDEX.md` now points to `learn.html#walkthrough` for the quick inspection path.
  - Verification: ran VS Code task “AI Brain: eval” (PASS; see `run_eval.out`, `determinism_suite: PASS`).

- New task (2026-01-26): quantify “thinking activities” per cycle by activity_type (measure/retrieve/synthesize/error_resolution) and category (semantic/procedural) using existing eval artifacts and/or a small helper script; document the baseline numbers.

- Completed (2026-01-26): baseline “thinking activity quantity” helper.
  - Added: `scripts/activity_counts_report.py` to summarize per-cycle activity counts (completed + pending) from stored record artifacts.
  - Updated: `learn.html#walkthrough` includes a copyable command to run the helper.
  - Baseline example: `eval_orch_cycle_art_001` reports completed `{measure:1, error_resolution:1}` and pending `{retrieve:1}` with `max_steps=2`.
  - Verification: ran `py -3 scripts/activity_counts_report.py --category semantic --id eval_orch_cycle_art_001` and VS Code task “AI Brain: eval” (PASS).

- New task (2026-01-26): (optional) add an aggregated per-record-category activity summary.
  - Purpose: hardware-aware tuning and workload budgeting (e.g., “how many retrieve/measure steps are we doing per semantic vs procedural record class?”).
  - Default: off / scripts-only (do not run in the core cycle unless explicitly enabled).
  - Integration idea: emit summary via `module_metrics` on-demand (e.g., during eval/stress, or a manual CLI command), not during normal runtime.
  - Optional knob shape (if integrated): `activity_reporting.enabled` + `activity_reporting.mode` + `activity_reporting.sample_limit` + `activity_reporting.io_budget`.

- Completed (2026-01-26): documented activity-quantity reporting helper.
  - Updated: `TUNING_GUIDE.md` adds an “Optional: thinking activity quantity reporting” section and clarifies that per-record-category aggregation should remain optional/off by default.
  - Verification: ran VS Code task “AI Brain: eval” (PASS).

- New task (2026-01-27): add operational canary monitoring artifacts (one-command cycle checks + triage template + optional manual workflow), wire into docs/dashboard, and re-run eval.

- Completed (2026-01-27): added triage ticket template for canary failures.
  - Added: `docs/TRIAGE_TICKET_TEMPLATE.md`.
  - Note: created before logging due to an interrupted summary request; logging now to preserve repo workflow discipline.

- Completed (2026-01-27): added canary monitoring runner + on-demand CI workflow + wired docs/dashboard.
  - Added: `scripts/canary_cycle_checks.py` (one-command per-cycle canary checks; writes `TemporaryQueue/canary_checks/<run_id>/summary.txt` + step outputs).
  - Added: `.github/workflows/canary_checks.yml` (manual `workflow_dispatch` only; uploads canary artifacts).
  - Updated: `index.html` staging window now links triage template + includes a copyable canary command.
  - Updated: `docs/PRODUCTION_ROLLOUT.md` includes the one-command canary runner and links to the triage template.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): remove optional “canary cycle” tooling and wiring.
  - Reason: keep repo minimal; avoid optional ops tooling unless actively used for assessment.
  - Plan: delete `scripts/canary_cycle_checks.py`, `.github/workflows/canary_checks.yml`, and `docs/TRIAGE_TICKET_TEMPLATE.md`; remove related links/commands in `index.html` and `docs/PRODUCTION_ROLLOUT.md`; re-run eval.

- New task (2026-01-27): create an assessment-oriented roadmap for Copilot app / LLM progression.
  - Add: `roadmap_table_2.md` with a clean, accurate task sequence that references current repo files.
  - Constraints: no optional ops tooling; focus on assessment continuity (what to attach/read/run per milestone).

- Completed (2026-01-27): removed optional “canary cycle” tooling and wiring.
  - Deleted: `.github/workflows/canary_checks.yml`, `docs/TRIAGE_TICKET_TEMPLATE.md`, `scripts/canary_cycle_checks.py`.
  - Updated: `index.html` and `docs/PRODUCTION_ROLLOUT.md` to remove references.

- Completed (2026-01-27): added assessment-oriented roadmap.
  - Added: `roadmap_table_2.md` (Copilot/LLM-friendly milestones + what to attach/run).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): improve `public_mirror/` assessment continuity.
  - Ensure the mirror includes `roadmap_table_2.md` and a change log pointer (prefer `temp_12.md`) so Copilot app can assess progression.
  - Update `scripts/create_public_mirror.py` to optionally preserve `public_mirror/.git/` during regeneration.

- New task (2026-01-27): add Copilot app guidance doc into `public_mirror/`.
  - Source: `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_AI_Guide.md`.
  - Add: `public_mirror/COPILOT.md` (same content) and include it in mirror generation for continuity.

- Completed (2026-01-26): refreshed activity-quantity reporting docs.
  - Updated: `TUNING_GUIDE.md` now includes an explicit aggregate (`--aggregate`) command example; reiterated scripts-only + opt-in behavior.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): design a hardware-aware scaling plan for activity quantity.
  - Add config knobs for per-cycle activity budgets (max_steps, per-type caps, resource_budget cpu/io/mem).
  - Add metrics: counts per activity_type, average cost, and wall-clock per cycle.
  - Add eval/stress gates: bounded runtime, deterministic output stability, and no unbounded queue growth.

- New task (2026-01-26): update `TUNING_GUIDE.md` so CI gate examples match current behavior (`--use-config` + env forced enabled), and add a brief note about when adaptive sampling is exercised; re-run eval.

- Completed (2026-01-26): `TUNING_GUIDE.md` CI gate + adaptive sampling notes refreshed.
  - Updated: `TUNING_GUIDE.md` clarifies that adaptive sampling is exercised only when rollback resolution is enabled, and adds config-driven CI gate invocation (`--use-config`) alongside the CLI-override example.
  - Verification: ran VS Code task “AI Brain: eval” (PASS; includes `determinism_suite: PASS`).

- New task (2026-01-26): add a new-developer “how the AI Brain thinks” learning path and a temp-trail index.
  - Add: `TEMP_TRAIL_INDEX.md` (what the temp files are + recommended reading order).
  - Update: `index.html` and `learn.html` to link it and highlight the core thinking loop + the key modules to read.
  - Verification: run “AI Brain: eval” after doc edits and log results.

- Completed (2026-01-26): added a new-developer “how the AI Brain thinks” learning path.
  - Added: `TEMP_TRAIL_INDEX.md` (temp trail map + reading order + key code entrypoints).
  - Updated: `index.html` now links the index and includes a “How the AI Brain thinks” card.
  - Updated: `learn.html` now includes a “How the AI Brain thinks” section and links to `TEMP_TRAIL_INDEX.md` + `temp_12.md`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): improve `learn.html` onboarding with a paste-ready “start + assess” prompt for VS Code Agent Mode or other LLMs, and document how to inspect metrics/artifacts after running the AI Brain.

- Completed (2026-01-26): improved onboarding “start + assess” guidance in `learn.html`.
  - Added: `learn.html#start-brain` section covering baseline run commands, where artifacts live, optional metrics flush/dashboard, and a paste-ready assessment prompt template for VS Code Agent Mode or other LLMs.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): update `learn.html` to explicitly document how to use VS Code Agent Mode and the desktop Copilot app workflow (public mirror + attachment fallback), with links to the relevant procedure docs; re-run eval.

- Completed (2026-01-26): documented VS Code Agent Mode + desktop Copilot app workflow in `learn.html`.
  - Added: a new “Copilot workflows” section with links to the mirror/attachment procedure docs and copyable commands (`scripts/create_public_mirror.py`, `scripts/export_copilot_app_attachments.py`).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- Completed (2026-01-26): upgraded `orchestration_migration` activity handlers to use real retrieval/reasoning modules, strengthened eval gate, and fixed eval config patching via in-process config cache; ran `AI Brain: eval` (PASS).

- Completed (2026-01-26): implemented `orchestration_migration` (default-off observability-only activity cycle trace in `RelationalMeasurement`), added config defaults, and added eval gates; ran `AI Brain: eval` (PASS).

- New task (2026-01-26): fix `scripts/*.py` helpers to reliably import repo modules when executed as `python scripts/...` (ensure repo root is on `sys.path`); re-run gate scripts and eval.

- Completed (2026-01-26): script import-path reliability fixes.
  - Updated: `scripts/check_adaptive_sampling_gate.py`, `scripts/metrics_dashboard.py`, `scripts/check_adaptive_vs_fixed_agreement.py` now prepend the repo root to `sys.path` when run as `python scripts/...`.
  - Verified: `py -3 scripts/check_adaptive_vs_fixed_agreement.py --use-config` passes; `py -3 -c "from module_metrics import flush_metrics; print(flush_metrics())"` writes `TemporaryQueue/metrics.json`; `py -3 scripts/check_adaptive_sampling_gate.py --use-config` reports no data (expected when adaptive not used).
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- New task (2026-01-26): add a lightweight CI regression gate to compare adaptive vs fixed sampling decisions on a small deterministic scenario set; wire into CI, document knobs, and re-run eval.

- Completed (2026-01-26): adaptive vs fixed agreement regression gate.
  - Added: `scripts/check_adaptive_vs_fixed_agreement.py` (deterministic in-memory scenarios; compares task status between adaptive and fixed sampling).
  - Updated: `config.json` adds `verifier.adaptive_sampling.regression_gate` defaults.
  - Updated: `.github/workflows/ci.yml` runs the new gate (forced enabled via `AI_BRAIN_AGREEMENT_GATE_ENABLED=1`).
  - Docs: updated `TUNING_GUIDE.md` with usage + knobs.
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- New task (2026-01-26): update `.github/workflows/ci.yml` to run the adaptive sampling gate with `--use-config` so tolerances are driven by `config.json` (while keeping the gate enforced).

- Completed (2026-01-26): CI now runs adaptive sampling gate via config.
  - Updated: `.github/workflows/ci.yml` runs `scripts/check_adaptive_sampling_gate.py --use-config` and forces the gate enabled via `AI_BRAIN_ADAPTIVE_GATE_ENABLED=1`.
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- New task (2026-01-26): make the adaptive sampling CI gate configurable via `config.json` and environment variables (without changing current defaults/CLI flags), and add optional machine-readable JSON output to the metrics dashboard; update docs and re-run eval.

- Completed (2026-01-26): CI gate config/env support + dashboard JSON output.
  - Updated: `scripts/check_adaptive_sampling_gate.py` supports `--use-config` + `--config`, and (when enabled) reads `verifier.adaptive_sampling.ci_gate` and/or env vars (`AI_BRAIN_ADAPTIVE_GATE_*`), while preserving CLI flags and existing defaults.
  - Updated: `scripts/metrics_dashboard.py` supports `--json` output.
  - Docs: updated `TUNING_GUIDE.md` with the optional config/env knobs and JSON output usage.
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- Completed (2026-01-26): orchestration unification assessment and eval-gated migration plan written as `temp_27.md`.

- Completed (2026-01-26): continued systematic assessment report written.
  - Added: `temp_26.md` (deeper module review: activity manager, uncertainty, error resolution, scheduler/toggle, AI_Brain bridge; determinism holes; orchestration bottlenecks).
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- Completed (2026-01-26): objective determinism + selection migration (opt-in).
  - Updated: `module_objectives.py` now uses deterministic timestamps when enabled.
  - Updated: `config.json` adds `selection_migration` (default disabled).
  - Updated: `module_integration.RelationalMeasurement(...)` can (opt-in) blend conceptual-measure objective alignment into selection ranking.
  - Updated: `run_eval.py` adds `logic_objectives_deterministic_timestamps` gate.
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- In progress (2026-01-26): drafting systematic workflow/component audit report as `temp_25.md`.

- New task (2026-01-26): systematically assess each AI Brain component/module vs the project workflow and “total thinking ability”; write report as `temp_25.md`.

- Completed (2026-01-26): systematic workflow/component audit report written.
  - Added: `temp_25.md` (module-by-module workflow mapping + thinking ability rubric + gaps + prioritized tasks).
  - Verification: ran VS Code task “AI Brain: eval” (completed; output shows collector runs saved + deterministic timestamps).

- New task (2026-01-26): scan `temp_[n].md` progression and compose next `temp_[n].md` (temp_24.md) with upgrade assessment, gaps, and prioritized follow-ups.

- Completed (2026-01-26): temp trail assessment report written.
  - Added: `temp_24.md` (progress assessment + gaps + prioritized tasks + recomposition suggestions).
  - Verification: ran VS Code task “AI Brain: eval” (no errors reported).

- New task (2026-01-26): upgrade `module_reasoning.py` to Think-Deeper (distributional reasoning + counterfactuals + justification artifacts) without breaking existing APIs.
  - Constraints: deterministic by default; side-effect-free; additive outputs only; avoid absolute paths.
  - Validation: add logic-suite eval gates for distribution/counterfactual shape + determinism; run “AI Brain: eval” and record results.

- Completed (2026-01-26): Think-Deeper upgrades for `module_reasoning.py`.
  - Updated: `module_reasoning.synthesize(...)` now includes additive artifacts: `why` (distribution + coherence + stability) and `counterfactuals` (leave-one-out deltas).
  - Added tests: `tests/test_reasoning_think_deeper.py` (requires pytest).
  - Added eval gates: `logic_reasoning_think_deeper_artifacts`, `logic_reasoning_think_deeper_deterministic_repro`.
  - Eval: PASS (filtered)
    - `logic_reasoning_synthesis_engine: PASS`
    - `logic_reasoning_think_deeper_artifacts: PASS`
    - `logic_reasoning_think_deeper_deterministic_repro: PASS`

- New task (2026-01-27): perform git commit operations per user request (review status, stage, commit, and report).

- Completed (2026-01-27): performed git commit operations.
  - Commit: `214005b` ("Update docs, mirror, and canary workflow").
    - `determinism_suite: PASS`

- New task (2026-01-26): implement operational follow-ups for adaptive sampling.
  - A) Add a lightweight dashboard script to summarize `TemporaryQueue/metrics.json` (avg samples, early-stop rate).
  - B) Add a CI gate script + wire into `.github/workflows/ci.yml` to fail if metrics exceed tolerances.
  - C) Implement a rollback-storm policy (cap retries / escalate) with config knobs.
  - Validation: run “AI Brain: eval” and keep determinism PASS.

- Completed (2026-01-26): operational follow-ups for adaptive sampling.
  - Added dashboard: `scripts/metrics_dashboard.py` (reads `TemporaryQueue/metrics.json`).
  - Added CI gate: `scripts/check_adaptive_sampling_gate.py` and wired it into `.github/workflows/ci.yml` (also uploads metrics artifact).
  - Added rollback-storm policy: `config.json > error_resolution.rollback_storm_policy` and enforcement in `module_error_resolution.execute_resolution_task` (escalates to `needs_review` after N rollbacks per target).
  - Added tests: `tests/test_rollback_storm_policy.py`.
  - Docs: updated `TUNING_GUIDE.md` with dashboard/gate commands and rollback-storm config.
  - Eval: PASS (includes `determinism_suite: PASS`).
  - Note: `py -3 -m pytest` currently fails with “No module named pytest”; pytest is not listed in root `requirements.txt`.

- New task (2026-01-26): run adversarial harness scenarios S1–S6 in deterministic mode and collect diagnostic artifacts.
  - Outputs: `pytest_adversarial.out`, `run_eval.out`, determinism reproduction output, and `adversarial_report_*.json` reports.
  - Acceptance: determinism repro true; adversarial eval gates pass; reports exist for S1–S6.

- Completed (2026-01-26): adversarial harness run (S1–S6) + artifacts collected.
  - Project state: branch `main`, commit `d93e387`.
  - Config: `config.json > determinism.deterministic_mode` is `true`.
  - Pytest (adversarial): PASS (`7 passed in 0.05s`). Output: `pytest_adversarial.out`.
  - Eval suite: PASS. Output: `run_eval.out`.
    - Confirmed gates: `logic_adversarial_report_shape: PASS`, `logic_adversarial_deterministic_repro: PASS`, `logic_adversarial_escalation_policy: PASS`.
  - Determinism repro: `provenance_equal: True` (see `determinism_check.out`).
  - Reports written to `TemporaryQueue/`:
    - `TemporaryQueue/adversarial_report_S1_small_noise.json`
    - `TemporaryQueue/adversarial_report_S2_large_outlier.json`
    - `TemporaryQueue/adversarial_report_S3_context_swap.json`
    - `TemporaryQueue/adversarial_report_S4_poisoned_retrieval.json`
    - `TemporaryQueue/adversarial_report_S5_rollback_storm.json`
    - `TemporaryQueue/adversarial_report_S6_counterfactual_negative_gain.json`
  - Bundle index: `adversarial_run_index.json` and stdout capture `adversarial_bundle.out`.

- Completed (2026-01-26): saved the Copilot-app adversarial run template as `adversarial_run_results_v1.md` for future repeatable runs.

- Completed (2026-01-26): upgraded README/docs for clearer setup + testing instructions.
  - Goals: add `.venv` setup (Windows), clarify pytest vs eval usage, document adversarial harness bundle artifacts.
  - Also remove hard-coded absolute paths from docs (esp. `AI_Brain/README.md`).

- Completed (2026-01-26): added a provenance excerpt extractor script for compact diagnostic bundles.
  - Inputs: an adversarial report JSON (includes `provenance_snapshot`) and global `LongTermStore/Provenance/provenance_log.json`.
  - Output: a small JSON bundle (events + related ids) suitable to attach to Copilot app/chat.
  - Script: `scripts/extract_provenance_bundle.py`
  - Sample bundle: `TemporaryQueue/adversarial_report_S1_small_noise_prov_bundle.json`

- Connector note (2026-01-26): Desktop Copilot “connector” isn’t something I can attach to directly from this VS Code agent session, but the agent already has local workspace capabilities (file read/write + task execution) without any tokens pasted into chat.
  - Repo packaging: no `pyproject.toml` present; uses `requirements.txt` + direct `py -3 ...` commands.
  - Confirmed `config.json` includes determinism + feature_flags.
  - Ran `py -3 cli.py status`: determinism_suite PASS; deterministic_mode true; fixed_timestamp 2025-01-01T00:00:00Z.
  - Ran `py -3 run_eval.py` (filtered): key suites PASS (integration/verifier/want/activity_manager/retrieval/adversarial + determinism_suite).

- New task (2026-01-26): implement `module_adversarial_test.py` (deterministic adversarial harness) + `tests/test_adversarial.py` + eval gates.
  - Goals: deterministic scenarios S1–S6 targeting error resolution, retrieval, reasoning, and verifier escalation.
  - Constraints: avoid assuming `integration.modules` globals; prefer in-memory stores; avoid hard-coded paths (use `sanitize_id`/`safe_join`/`resolve_path`).
  - Validation: add logic-suite gates for report shape + deterministic reproduction + escalation policy; run “AI Brain: eval” and record results.

- Completed (2026-01-26): adversarial harness + tests + eval gates.
  - Added: `module_adversarial_test.py` (S1–S6, deterministic, in-memory).
  - Added: `tests/test_adversarial.py`.
  - Added eval gates: `logic_adversarial_report_shape`, `logic_adversarial_deterministic_repro`, `logic_adversarial_escalation_policy`.
  - Eval: PASS (including `determinism_suite: PASS`).

- New task (2026-01-26): add CLI command to run adversarial scenarios and optionally write JSON reports to `TemporaryQueue/`.
  - Command: `python cli.py adversarial --scenario S1_small_noise`.
  - Options: `--seed`, `--no-write`, `--report-dir`, `--deterministic/--non-deterministic`.
  - Validation: re-run “AI Brain: eval” and record results.

- Completed (2026-01-26): `cli.py adversarial` command.
  - Updated: `cli.py` (new `adversarial` subcommand).
  - Updated: `README.md` (Quick Start includes the new command).
  - Eval: PASS (including `determinism_suite: PASS`).

- New task (2026-01-26): fix statistical p-value handling when p==0.0 (avoid `x or 1.0` bugs).
  - Affects: `module_error_resolution.execute_resolution_task` and verifier threshold checks.
  - Validation: re-run “AI Brain: eval” and ensure adversarial S1 validates (no false rollback).

- Completed (2026-01-26): p-value bugfix for p==0.0.
  - Updated: `module_error_resolution.py` (do not treat `p==0.0` as missing).
  - Updated: `module_verifier.py` (threshold checks respect `p==0.0`).
  - Verified: `python cli.py adversarial --scenario S1_small_noise --no-write` now returns `task_status: validated`.
  - Eval: PASS (including `logic_adversarial_*: PASS` and `determinism_suite: PASS`).

- New task (2026-01-26): add adaptive Monte Carlo sampling for statistical validation in error resolution.
  - Goal: reduce runtime by early-stopping on clearly significant/non-significant cases while preserving determinism.
  - Constraints: backward compatible defaults; deterministic sampling; preserve existing validation dict keys.
  - Validation: add unit tests for adaptive early-stop behavior and run “AI Brain: eval”.

- Completed (2026-01-26): adaptive Monte Carlo sampling (opt-in) for error resolution validation.
  - Updated: `module_uncertainty.sample_distribution_prefix()` (prefix-stable deterministic sampling for adaptive routines).
  - Updated: `module_error_resolution.validate_records_statistically_adaptive()` and wired it into `execute_resolution_task(..., adaptive_sampling=True, ...)`.
  - Updated: `tests/test_error_resolution.py` to cover adaptive early-stop on clear validation and clear non-significance.
  - Mirror kept in sync: `public_mirror/module_uncertainty.py`, `public_mirror/module_error_resolution.py`.
  - Validation: ran “AI Brain: eval” (no failures observed) and confirmed `cli.py status` shows `determinism_suite: PASS`.

- New task (2026-01-26): wire adaptive sampling into runtime via `config.json`.
  - Goal: allow enabling adaptive MC sampling without changing call sites.
  - Scope: add config keys + thread them into `module_integration.run_cycle()` rollback error-resolution path.
  - Validation: run “AI Brain: eval” and confirm determinism remains PASS.

- Completed (2026-01-26): config-driven adaptive sampling wiring.
  - Updated: `config.json` adds `error_resolution.adaptive_sampling` (default disabled).
  - Updated: `module_integration.run_cycle()` reads the config and passes `adaptive_sampling`, `adaptive_n_min`, `adaptive_multiplier` into the rollback `execute_resolution_task(...)` call.
  - Also threads verifier thresholds into that call (`alpha` from `verifier.p_threshold`, `min_effect_size` from `verifier.min_effect_size`).
  - Validation: ran “AI Brain: eval” (no failures observed in task output) and re-checked `py -3 cli.py status`.

- New task (2026-01-26): update `TUNING_GUIDE.md` to document error-resolution adaptive sampling knobs.
  - Include: `error_resolution.adaptive_sampling` and how it interacts with `verifier.p_threshold` / `verifier.min_effect_size`.

- Completed (2026-01-26): documented adaptive error-resolution sampling knobs in `TUNING_GUIDE.md`.
  - Added: section “Error-resolution statistical validation (runtime/robustness)” with `config.json` snippets and parameter meanings.

- New task (2026-01-26): extend adaptive sampling knobs + add lightweight metrics.
  - Add support for: `n0`, `n_max`, growth `multiplier`, and `early_stop_margin` (Copilot suggestion).
  - Config: support `verifier.adaptive_sampling` while preserving `error_resolution.adaptive_sampling` for compatibility.
  - Add minimal in-process counters (`module_metrics.py`) and instrument `execute_resolution_task`.
  - Validation: run “AI Brain: eval” and keep determinism PASS.

- Completed (2026-01-26): extended adaptive sampling knobs + lightweight metrics.
  - Updated: `module_error_resolution.validate_records_statistically_adaptive()` now supports `n0`, `n_max`, growth multiplier, and `early_stop_margin` (adds `early_stopped` + `stop_reason` metadata).
  - Updated: `module_integration.run_cycle()` now prefers `config.json > verifier.adaptive_sampling` (falls back to `error_resolution.adaptive_sampling`) and threads those knobs into `execute_resolution_task(...)`.
  - Added: `module_metrics.py` (in-memory counters) and instrumented `execute_resolution_task` to increment adaptive/fixed sampling counters.
  - Added test: `tests/test_integration_adaptive_sampling_config.py` (ensures config-driven adaptive args are passed without call-site changes).
  - Updated docs: `TUNING_GUIDE.md` now documents `verifier.adaptive_sampling` and notes legacy compatibility.
  - Mirror kept in sync: `public_mirror/module_error_resolution.py`, `public_mirror/module_metrics.py`.
  - Validation: ran “AI Brain: eval”; checked `py -3 cli.py status`.

- New task (2026-01-26): persist metrics counters to JSON under TemporaryQueue.
  - Implement `module_metrics.flush_metrics(...)` using `resolve_path`/`safe_join` (no absolute paths).
  - Mirror in sync: `public_mirror/module_metrics.py`.
  - Validation: run “AI Brain: eval”.

- Completed (2026-01-26): metrics persistence to JSON.
  - Updated: `module_metrics.flush_metrics(...)` writes deterministic JSON to `TemporaryQueue/metrics.json` by default.
  - Mirror kept in sync: `public_mirror/module_metrics.py`.
  - Docs: `TUNING_GUIDE.md` includes a one-liner command to flush metrics.
  - Validation: ran “AI Brain: eval” after the change.

- New task (2026-01-26): perform git commit(s) for the recent simple upgrades (core module enhancements, new docs/static pages, backup module, verifier/uncertainty/provenance utilities, tests, and eval gates).

- Completed (2026-01-26): created commit `d93e387` ("feat: determinism-driven upgrades"); ran eval and saw `determinism_suite: PASS`.

- New task (2026-01-26): perform git commit(s) for public mirror artifacts + adversarial harness.
  - Scope: stage/commit the intended source/docs changes (incl. `public_mirror/`, adversarial harness, tests, eval gates, and related core module updates).
  - Exclusions: do not commit local export/attachment folders (e.g. `Copilot_app_Attachments_txt_files_of_py_modules/`) or local run artifacts like `*.out`.
  - Validation: run “AI Brain: eval” and record results.

- Completed (2026-01-26): created commit `97435b1` ("feat: adversarial harness + public mirror").
  - Eval: PASS (filtered)
    - `logic_reasoning_synthesis_engine: PASS`
    - `logic_reasoning_think_deeper_artifacts: PASS`
    - `logic_reasoning_think_deeper_deterministic_repro: PASS`
    - `logic_adversarial_report_shape: PASS`
    - `logic_adversarial_deterministic_repro: PASS`
    - `logic_adversarial_escalation_policy: PASS`
    - `determinism_suite: PASS`

- New task (2026-01-26): auto-close the sticky mini-nav menu after clicking a link (small screens) for smoother navigation.

- New task (2026-01-26): make sticky mini-nav bars collapsible on small screens (hamburger toggle; static/offline; no external dependencies).

- New task (2026-01-26): add a small sticky mini-nav to the dashboard and onboarding guide pages for faster in-page navigation while scrolling (static HTML, offline-friendly).

- New task (2026-01-26): make the onboarding/dashboard navigation more friendly (add a dedicated “Start here / New developer?” section on `index.html`, add a table-of-contents + anchor navigation + back-to-top/back-to-dashboard controls on `learn.html`).

- New task (2026-01-26): add a new-developer onboarding page (static `learn.html`) plus a clear dashboard button/link to open it in the same tab; keep wording generic and privacy-safe (no references to any external/hidden project context).

- New task (2026-01-26): add a git-aware external archive backup module that copies only files included in the Git repo (committed/tracked), avoiding unnecessary local artifacts (venv, caches, runtime stores). Also add a short backup procedure doc and link it from `index.html`.

- Created `temp_15.md` containing a paste-ready response section for the desktop Copilot app (describes what VS Code agent Copilot can do to support repo analysis/integration work).
- Updated `temp_15.md` to also include: (a) additional info requests needed from the repo, (b) research/prior-art checklist with candidate frameworks, (c) a general phased plan, and (d) a concrete task/deliverables list.
- Task added: replace the meta-level `temp_15.md` with an evidence-based assessment of this repo (package/dependency reality, integration synthesis, objectives/concentrations integration, and context/memory storage capabilities), with concrete recommendations grounded in code.
- Task added (user request): re-compose `temp_15.md` so “AI Brain” is treated as the primary system (LLMs optional tools), and so the message is suitable to send to the desktop Copilot app.
- Task added (user request): further improve `temp_15.md` so it matches what the Copilot app asked for (architecture + file/module pointers + tree snapshot + research/prior-art), and is adequate context for generating solutions.

- New workstream (2026-01-25): begin upgrading the repo to conform to the architecture described in `temp_18.md` and the transformation roadmap in `temp_19.md`.
  - Strategy: proceed in eval-gated, incremental steps to avoid breaking existing behavior.
  - Phase 1 focus: docs alignment (README split + DESIGN_GOALS.md + expand AI_Brain/ARCHITECTURE.md + normalize paths).
  - Phase 2+ focus: migrate away from keyword/Jaccard heuristics via opt-in config switches and new measurement modules, then flip defaults once eval coverage is expanded.

- Phase 1 (docs alignment): created backups and updated docs.
  - Backups: `README.md.bak_20260125T153731Z`, `AI_Brain/ARCHITECTURE.md.bak_20260125T153731Z`
  - Updated: `README.md` (added Implemented Today + Design Goals sections)
  - Added: `DESIGN_GOALS.md` (authoritative target-architecture constraints)
  - Updated: `AI_Brain/ARCHITECTURE.md` (expanded beyond stub; added root integration notes)

- Re-ran `py -3 run_eval.py` after Phase 1 doc changes: PASS.

- Phase 2 prep (scaffolding + migration switches; non-breaking):
  - Added stubs (not wired into runtime yet):
    - `module_concept_measure.py`
    - `module_want.py`
    - `module_activity_manager.py`
    - `module_retrieval.py`
  - Added directory: `ActivityQueue/` (empty queue scaffold)
  - Added config switches (defaults preserve existing behavior): `config.json > measurement_migration`

- Re-ran `AI Brain: eval` and `py -3 run_eval.py` after scaffolding + config switches: PASS.

- New implementation task (2026-01-25): implement a repo-compatible conceptual measurement engine.
  - Implement `module_concept_measure.measure_conceptual_content(record, objectives, now_ts=None)` and `attach_conceptual_measurement_to_relational_state(...)`.
  - Determinism: never use system clock; prefer caller-injected `now_ts`, else `config.json > determinism.fixed_timestamp`, else derive `now_ts` from record timestamps.
  - Objectives: support current objective records (id/content/labels) via normalization, while also supporting a richer objective spec (keywords/constraints/priority) when provided.
  - Storage: cap persisted `token_counts` deterministically (top-K tokens) to avoid bloating LongTermStore.
  - Integration: wire into `module_integration.RelationalMeasurement()` behind `config.json > measurement_migration.enable`.
  - Eval: add logic-suite gates for conceptual measurement counts/recurrence/objective scoring/relational_state attachment.

- Completed conceptual measurement implementation (non-breaking + gated):
  - Implemented: `module_concept_measure.measure_conceptual_content()` + `attach_conceptual_measurement_to_relational_state()`.
    - Determinism: never uses system clock; `now_ts` argument > fixed_timestamp > max(record timestamps).
    - Objectives: supports existing repo objective records via normalization; also supports richer (keywords/constraints/priority) specs.
    - Storage: caps persisted token_counts deterministically (top-K).
  - Gated runtime hook: `module_integration.RelationalMeasurement()` attaches `relational_state.conceptual_measurement` only when `config.json > measurement_migration.enable` is true.
  - Updated schema allowance: `schemas/relational_state.schema.json` now includes optional `conceptual_measurement`.
  - Updated shallow validator: `module_tools.validate_relational_state()` allows optional `conceptual_measurement`.
  - Added eval gates: `logic_concept_measure_*` in `run_eval.py`.

- Re-ran `AI Brain: eval` and `py -3 run_eval.py` after conceptual measurement work: PASS.

- README request (2026-01-25): add a section explaining the project's logic stance.
  - Intent: contrast brittle rule-only thinking vs measurement-first logic (explicit measurements + comparisons).
  - Note: keep wording professional in-repo (avoid derogatory/insult language), while preserving the underlying point about LLM limitations and why this project exists.

- Next implementation (2026-01-25): upgrade `module_want.py` from scaffold to deterministic Want Awareness/Want Information engine.
  - Inputs: record + relational_state (incl. conceptual_measurement / decision_trace) + objectives.
  - Outputs: typed `WantSignal` + `AwarenessPlan` with suggested activities (retrieve/measure/error_resolution/synthesize).
  - Integration: wire into `module_integration.RelationalMeasurement()` behind a new `config.json` gate (`want_migration.enable`, default false) and persist plan into cycle_record and decision_trace.
  - Add eval gates in `run_eval.py` for deterministic want outputs + structure.

- Ran eval after want changes: PASS (including `logic_want_basic_signals`, `logic_want_error_signal`, `logic_want_synthesis_signal`, and `determinism_suite`).

- Spec update (2026-01-25): refactor `module_want.py` to accept explicit measurable inputs (objectives, measurement_gaps, error_summaries, synthesis_opportunities) and expose core functions:
  - `compute_want_information`, `compute_want_error_resolution`, `compute_want_synthesis`, `aggregate_wants`, `compute_awareness_plan`.
  - Keep `awareness_plan_from_record` as a convenience adapter.
  - Update logic-suite evals to cover the new API (high delta → want_information; many severe errors → want_error_resolution; high coherence → want_synthesis; empty inputs → empty/weak plan).

- Ran eval after want API refactor: PASS (including `logic_want_empty_inputs` and `determinism_suite`).

- Next implementation (2026-01-25): upgrade `module_activity_manager.py` from scaffold to deterministic multi-activity engine:
  - Translate `AwarenessPlan.wants` -> Activities with numeric priority.
  - Deterministic queue ops: enqueue, sort, select, execute, complete.
  - Keep existing file-backed queue helpers for compatibility.
  - Add logic-suite eval for want->activity translation.

- New implementation (2026-01-26): wire uncertainty + provenance into measurement/error/want.
  - Task A: `module_error_resolution.detect_error` adds `confidence` when uncertainty data is present.
    - Accepts optional `measurement['uncertainty']` and `record['uncertainty']` (JSON-friendly dict form).
    - Computes confidence via `module_uncertainty.confidence_from_delta`.
    - Backward compatible: if uncertainty missing, keeps behavior and returns `confidence=0.5` (or omits).
  - Task B: `module_measure.measure_information` attaches an `uncertainties` map for numeric signals (structure-only; deterministic).
    - Must not break existing callers; new keys only.
  - Task C: `module_provenance.now_ts` / `module_uncertainty.now_ts` honor determinism settings.
    - Deterministic mode: fixed timestamp seconds (existing behavior).
    - Non-deterministic mode: allow wall clock seconds.
  - Task D: Upgrade `module_want.py` with an additive EVoI API.
    - Add `compute_expected_value_of_information(...)` (Monte Carlo using `sample_distribution`, deterministic seed).
    - Keep `compute_awareness_plan(...)` behavior unchanged unless explicitly called.
  - Task E: Eval gates.
    - Add `logic_want_evoi_positive` / `logic_want_evoi_negative`.
    - Add `logic_error_resolution_confidence_uncertainty`.
  - Run `AI Brain: eval` and log PASS/FAIL.

- Completed (2026-01-26): uncertainty/provenance wiring + EVoI.
  - Updated: `module_error_resolution.detect_error` now returns `confidence` when uncertainty payloads are provided (neutral 0.5 otherwise).
  - Updated: `module_measure.measure_information` now attaches an additive `uncertainties` map (JSON-friendly; deterministic in deterministic mode).
  - Updated: `module_want.compute_expected_value_of_information` (deterministic Monte Carlo via `sample_distribution`).
  - Updated: `module_uncertainty.now_ts` and `module_provenance.now_ts` honor determinism settings (fixed timestamp when enabled; wall clock otherwise).
  - Updated: `run_eval.py` added gates: `logic_want_evoi_positive`, `logic_want_evoi_negative`, `logic_error_resolution_confidence_uncertainty`.
  - Eval: PASS (including new gates + `determinism_suite: PASS`).

- Next implementation (2026-01-26): upgrade `module_want.py` to “Think Deeper”.
  - Add an explicit EVoI cost model helper (deterministic; caller-overridable).
  - Add “why vectors” for EVoI-driven wants (structured rationale: inputs, assumptions, sample stats).
  - Keep existing want signals API stable; add new helpers rather than changing old outputs.
  - Add unit tests under `tests/` for EVoI + why vector stability.
  - Add a logic-suite eval gate to ensure why-vector output is deterministic and well-formed.

- Completed (2026-01-26): `module_want.py` Think Deeper additions.
  - Added: `estimate_information_cost(...)` (deterministic cost model helper).
  - Added: `compute_evoi_with_why(...)` (EVoI + structured why vector; deterministic sampling).
  - Added: unit tests `tests/test_want_evoi.py`.
  - Added eval gate: `logic_want_evoi_why_vector`.
  - Eval: PASS (including `logic_want_evoi_why_vector` + `determinism_suite: PASS`).

- Next implementation (2026-01-26): expand `module_activity_manager.py` with preconditions, budgeter, verifier stubs (additive).
  - Preserve existing public functions used by evals: `translate_wants_to_activities`, `new_queue`, `enqueue_activities`, `prioritize_queue`, `select_next_activity`, `execute_activity`, `complete_activity`.
  - Add deterministic-mode queue metadata:
    - `queue.deterministic_mode`, `queue.resource_budget`, `queue.used_resources`.
  - Add precondition framework:
    - Support `record_version` using `state.records_map[record_id].version`.
    - Support `measurement_freshness` using `state.last_measure_ts[record_id]`.
    - Allow custom preconditions via injected `verifier_funcs` mapping.
  - Add resource budgeter:
    - Support scalar cost and multi-dim dict cost (e.g. `{cpu, io}`)
    - Ensure allocation is deterministic and released on completion.
  - Add verifier integration stubs:
    - `execute_activity_with_hooks(...)` returns an execution artifact with verifier result.
  - Tests:
    - `tests/test_activity_manager.py` covers deterministic enqueue+prioritize, precondition rejection, budget rejection.
  - Eval gates (logic-suite):
    - `logic_activity_manager_deterministic_queue`
    - `logic_activity_manager_budget_respect`
    - `logic_activity_manager_precondition_enforcement`
  - Run `AI Brain: eval` and log PASS/FAIL.

- Completed (2026-01-26): `module_activity_manager.py` deterministic queue + preconditions + budgeter + verifier hooks.
  - Updated: `new_queue()` now includes `deterministic_mode`, `resource_budget`, `used_resources` (defaults preserve prior behavior).
  - Updated: `enqueue_activities()` sorts incoming activities by `activity_id` when deterministic_mode is enabled.
  - Updated: `select_next_activity()` now supports optional precondition checks + budget checks (still compatible with old calls).
  - Added: resource helpers `can_allocate_resources`, `allocate_resources`, `release_resources` and `precondition_check()`.
  - Added: `execute_activity_with_hooks()` returns execution artifact + optional verifier result.
  - Added tests: `tests/test_activity_manager.py`.
  - Added eval gates: `logic_activity_manager_deterministic_queue`, `logic_activity_manager_budget_respect`, `logic_activity_manager_precondition_enforcement`.
  - Eval: PASS (including new gates + `determinism_suite: PASS`).

- Next implementation (2026-01-26): upgrade `module_retrieval.py` to Think Deeper standards.
  - Preserve existing `retrieve(store, query)` behavior and current eval gate `logic_retrieval_ranking`.
  - Add deterministic ranking engine `rank_records(...)` with:
    - score components (conceptual/objective/recurrence/constraint/uncertainty)
    - score distributions (deterministic sampling)
    - explainability vector
    - diversity constraint (deterministic clustering)
  - Add tests: `tests/test_retrieval.py`.
  - Add eval gates:
    - `logic_retrieval_score_components`
    - `logic_retrieval_deterministic_sampling`
    - `logic_retrieval_diversity`
    - `logic_retrieval_explainability`
  - Run `AI Brain: eval` and log PASS/FAIL.

- Completed (2026-01-26): `module_retrieval.py` Think Deeper retrieval upgrade.
  - Preserved existing `retrieve(store, query)` behavior and `logic_retrieval_ranking`.
  - Added: `rank_records_td(...)` + `retrieve_with_scores(...)` returning scored rows with:
    - `components` (conceptual/objective/recurrence/constraint/uncertainty)
    - `score_distribution` (deterministic sampling when uncertainty present)
    - `explain_vector` (contribution breakdown)
    - diversity via `diversity_k` using deterministic vector-hash clustering
  - Added tests: `tests/test_retrieval.py`.
  - Added eval gates: `logic_retrieval_score_components`, `logic_retrieval_deterministic_sampling`, `logic_retrieval_diversity`, `logic_retrieval_explainability`.
  - Eval: PASS (including new gates + `determinism_suite: PASS`).

- Ran eval after activity manager changes: PASS (including `logic_activity_manager_translate` and `determinism_suite`).

- Next implementation (2026-01-26): upgrade `module_retrieval.py` from scaffold to deterministic measurement-driven retrieval engine:
  - Typed structures: Record, RetrievalQuery, RetrievalScore.
  - Numeric components: measurement(target match), objective relevance, recurrence, conceptual similarity (cosine), constraint/context match.
  - Deterministic ranking: score desc then record_id asc.
  - Keep backward-compatible wrapper for existing scaffold functions.
  - Add logic-suite eval for retrieval ranking.

- Ran eval after retrieval changes: PASS (including `logic_retrieval_ranking` and `determinism_suite`).

- Added `module_error_resolution.py` (2026-01-26): deterministic error detection/classification/correction/validation based on measurement equivalence and delta.

- Ran eval after error resolution module + tests: PASS (including `logic_error_resolution_detect_equal`, `logic_error_resolution_detect_mismatch`, and `determinism_suite`).

- Next implementation (2026-01-26): extend `module_reasoning.py` with deterministic synthesis engine functions (coherence, combine values/vectors, synthesize, propose_next_steps) while preserving existing constraint/contradiction helpers relied on by eval.
- Next (2026-01-26): add a new logic-suite eval gate for the synthesis helpers (`logic_reasoning_synthesis_engine`) and re-run `AI Brain: eval`.

- Ran eval after adding `logic_reasoning_synthesis_engine`: PASS.

- Next (2026-01-26): add additional logic-suite gates for `module_reasoning.propose_next_steps` to cover positive/negative coherence_gain branches; re-run eval.

- Ran eval after adding `logic_reasoning_propose_next_steps_positive` / `logic_reasoning_propose_next_steps_negative`: PASS.

- New spec (2026-01-26): extend `module_relational_adapter.py` with deterministic structure-only 3D→Relational mapping API (`Raw3DObject`/`Raw3DRelation` → dict-based `RelationalState`), while preserving existing `attach_spatial_relational_state` integration.

- Ran eval after updating `module_relational_adapter.py` (new mapping API + compatibility preserved): PASS (including `logic_spatial_adapter` and `determinism_suite`).

- New spec (2026-01-26): add deterministic full-cycle orchestrator API to `module_integration.py` (initialize_system/run_cycle + helpers) using injected modules and storage interface; preserve existing `RelationalMeasurement` behavior.

- Ran eval after adding orchestrator API + `logic_integration_cycle_smoke`: PASS (including `determinism_suite`).

- Next (2026-01-26): update `module_integration.run_cycle` to merge world 3D objects/relations into existing canonical list-based `relational_state` (no new top-level keys) while keeping deterministic ordering; add eval gate and re-run.

- Ran eval after list-based `relational_state` merge + `logic_integration_cycle_preserves_list_relational_state`: PASS (including `determinism_suite`).

- New spec (2026-01-26): implement `module_uncertainty.py` + `module_provenance.py` with deterministic primitives and add tests/eval gates; re-run `AI Brain: eval`.

- Implemented `module_uncertainty.py` and `module_provenance.py`, added logic-suite gates (`logic_uncertainty_*`, `logic_provenance_*`) and pytest-style tests under `tests/`; ran eval: PASS (including `determinism_suite`).

## Evidence (runs)

- Ran `AI Brain: eval` (py -3 run_eval.py): all cases PASS (collector schema, scheduler, arbiter decisiveness, toggle justifications, reason chain, procedure match/refine, deterministic collector timestamps, last_cycle_ts activity, determinism suite).

## External archive backup (Git-only) (2026-01-26)

- Added `module_backup.py` + `cli.py backup` to create `Archive_N` backups containing only Git-listed files.
  - Mode `committed` (default): `HEAD` files only (closest to what’s on remote after push).
  - Mode `tracked`: tracked working-tree files (may include uncommitted edits).
- Added `BACKUP_PROCEDURE.md` and linked it from `index.html`.

Verification:
- Ran the VS Code task “AI Brain: eval”: PASS (including `determinism_suite: PASS`).

Safety refinement (2026-01-26): external archive backups must never overwrite an existing `Archive_N` folder. Implementation should select a non-existent destination or fail fast.

Verification (after safety refinement):
- Ran the VS Code task “AI Brain: eval”: PASS (including `determinism_suite: PASS`).

Refinement (2026-01-26): implement a staging-folder backup flow (`Archive_N.__staging__*` then rename) so an `Archive_N` folder only appears after the copy fully succeeds.

Verification (after staging refinement):
- Ran the VS Code task “AI Brain: eval”: PASS (including `determinism_suite: PASS`).

Refinement (2026-01-26): improve `cli.py backup`/`module_backup.py` error reporting. On failure, return structured error details and write a manifest/log into the staging folder so the user can inspect what failed.

Verification (after error-reporting refinement):
- Ran the VS Code task “AI Brain: eval”: PASS (including `determinism_suite: PASS`).

Refinement (2026-01-26): make `cli.py backup` exit with distinct codes (missing config vs copy failure vs finalize failure) for easier scripting.

Verification (after exit-code refinement):
- Ran the VS Code task “AI Brain: eval”: PASS (including `determinism_suite: PASS`).

## Copilot App Info Request (2026-01-25)

- [ ] Compose a copy-ready response for Copilot app requesting repo-grounded architecture context.
  - Provide an attachment checklist (tree, architecture docs, objectives, procedural templates, eval harness).
- (Note) Created the draft response file before logging it here (workflow slip); logging now for completeness.
- Drafted copy-ready Copilot response + attachment checklist: `COPILOT_APP_ARCH_CONTEXT_REPLY.md`.
- Re-ran `AI Brain: eval` after adding `COPILOT_APP_ARCH_CONTEXT_REPLY.md`: PASS (all eval_* + logic_* + determinism_suite).
- Re-ran `AI Brain: eval` after rewriting `temp_15.md`: all cases PASS.
- Improved `temp_15.md` with a concrete repo map + module pointers + prior-art appendix for the Copilot app; re-verified eval PASS.
- Task completed: compose a concise follow-up message to the desktop Copilot app (plus recommended file attachments) to enable it to propose repo-backed solutions.
- Task added (Copilot app deliverable): add `schemas/relational_state.schema.json` (draft v1 canonical relational-state schema) as a new schema file, but do not enforce/require it yet.
- Completed: added `schemas/relational_state.schema.json` (not yet wired into validation). Ran eval: PASS.
- Task added (Copilot app deliverable): implement the 3D↔relational adapter (new `module_relational_adapter.py`) and wire it into `RelationalMeasurement()` in a guarded, non-breaking way.
- Completed: added `module_relational_adapter.py` and wired guarded call into `module_integration.RelationalMeasurement()`; eval PASS.
- Task added (Copilot app deliverable): implement deterministic focus/concentration state (`module_focus.py`), snapshot it into `relational_state`, add objective_links, and use it to bias scheduling/measurement in a minimal non-breaking way.
- Completed: added `module_focus.py`, integrated `focus_state` into `RelationalMeasurement()` and `measure_information()`, persisted `relational_state.focus_snapshot` + objective_links; eval PASS.
- Completed: Stage 1 storage change — `module_storage.store_information()` now initializes `relational_state` on semantic records (new + existing) without changing decisions; eval PASS.
- Task added (user request): add deterministic eval cases for relational_state schema validity, constraint satisfaction, contradiction/objective alignment, focus influence, 3D adapter integration, decision trace completeness, and deterministic repetition (integrate into `run_eval.py` as a new logic suite).
- Completed: added deterministic logic-suite evals in `run_eval.py` (logic_* cases), updated `schemas/relational_state.schema.json` to match actual stored fields (nullable `spatial_measurement`, required lists, optional `focus_snapshot`), added `module_reasoning.py` (constraint checks), and added a synthetic 3D asset `eval_cases/assets/cube_eval.ply`; ran eval: PASS (including all logic_* cases).
- Re-verified on 2026-01-25 (filtered output): `py -3 run_eval.py | Select-String -Pattern 'logic_|determinism_suite|decisive_arbiter|last_cycle_ts_activity|deterministic_collector_ts' | ForEach-Object { $_.Line }`
  - logic_relational_state_schema: PASS
  - logic_constraint_satisfaction: PASS
  - logic_contradiction_detection: PASS
  - logic_objective_alignment: PASS
  - logic_focus_state_influence: PASS
  - logic_spatial_adapter: PASS
  - logic_decision_trace: PASS
  - logic_deterministic_repetition: PASS
  - deterministic_collector_ts: PASS
  - last_cycle_ts_activity: PASS
  - decisive_arbiter: PASS
  - determinism_suite: PASS

- Implemented runtime `relational_state` validation (shallow structural contract) and wired it into `module_storage.store_information()` for semantic records; re-ran eval and confirmed all logic_* and determinism checks PASS.

- Added `spatial` constraint validation support in `module_reasoning.check_constraints()` and a new eval gate `logic_runtime_spatial_constraint_integration`.
  - Note: initial implementation had a syntax error causing `logic_constraint_satisfaction` to FAIL; fixed and re-verified all logic_* and determinism checks PASS.

- Re-ran `AI Brain: eval` after adding `VSCODE_AGENT_MODE_INSTRUCTION_BLOCK.md`: PASS (logic suite + determinism suite).

## Message tasks (as received)

"Can you read the README files, compose a list of folders and files in this project. Read relevant files to assess the project progress. The AI Brain of the project is not yet completed. In your opinion, assess the logic of the AI Brain about the workflow of the AI Brain, such that you can discover if the packages are logical enough for the AI Brain versus if you might compose modifications to the packages. Are there recomendations online for making the packages more logical about algorithms about language context and reasoning?"

## Task checklist

- [x] Read root README(s) and AI_Brain README(s)
- [x] Inventory project folders/files (top-level + AI_Brain)
- [x] Read relevant orchestration/decision modules to assess workflow and progress
- [x] Assess architecture/package boundaries and recommend refactors
- [ ] (Optional) Pull specific external references/links if you want them cited explicitly

## Next tasks (recommended)

- [ ] Tighten schema validation for `relational_state`.
  - Today `module_tools.validate_record()` only does shallow type checks and does not validate nested objects.
  - Option A (small): add a dedicated `validate_relational_state()` (type/required/allowed-keys) and call it from `module_storage.store_information()` for semantic records.
  - Option B (bigger): extend `validate_record()` with limited recursive validation for nested objects/arrays.

- [ ] Promote constraint/contradiction reasoning from eval-only into runtime decisions.
  - Write `module_reasoning.check_constraints()` results into `relational_state.decision_trace` and surface a hard-violation as `decision_signals.contradiction=True`.

## In progress (2026-01-25)

- [x] Implement runtime constraint propagation
  - Goal: if `relational_state.constraints` contains a supported hard violation (lt/gt/eq/neq), propagate that into:
    - `conflicts` (severity 1.0)
    - `decide_toggle(... contradiction=True ...)`
    - `relational_state.decision_trace.constraints_report`
    - `decision_signals.contradiction=True` with provenance
  - Verification: `AI Brain: eval` and a new `logic_runtime_constraint_integration` eval case.

## Evidence (runs)


  - Re-ran `AI Brain: eval` after adding new-developer onboarding page (`learn.html`) and linking it from `index.html`: PASS.

  - Re-ran `AI Brain: eval` after making onboarding/dashboard navigation more friendly (TOC/anchors + Start Here links): PASS.

  - Re-ran `AI Brain: eval` after adding sticky mini-nav bars to `index.html` and `learn.html`: PASS.

  - Re-ran `AI Brain: eval` after making sticky mini-nav bars collapsible on small screens (hamburger Menu): PASS.

  - Re-ran `AI Brain: eval` after adding auto-close behavior for the sticky nav menu on link click: PASS.

  - Updated `module_reasoning.check_constraints()` to support spatial volume ranges (e.g. `{\"volume\": {\"max\": 5.0}}`) and to treat missing/malformed evaluation data as soft violations.
  - Implemented `module_reasoning.detect_contradictions()` to detect relation conflicts (same subj+pred, different obj, confidence>=0.8).

  - New doc/dashboard task (2026-01-26): repurpose `index.html` into an offline “AI_Algorithms / AI Brain” project dashboard.
    - Purpose: quick links to key docs/results + copy/paste commands for `cli.py` workflows (status/eval/stress/policy/determinism/gc).
    - Constraints: static HTML only (no direct execution of Python from browser), keep it useful even when opened via `file://`.

  - Re-ran `AI Brain: eval` after dashboard update: PASS (logic suite + determinism suite).
  - Helper (2026-01-26): create a Windows Desktop shortcut (.lnk) pointing to `index.html` for quick access to the local dashboard.
  - Implemented `module_reasoning.propose_actions(rel_state, signals)` and integrated it into `module_integration.RelationalMeasurement()` (merges into `mrep`, promotes conflicts, persists to `relational_state.decision_trace`).

  - Dashboard enhancement (2026-01-26): expand `index.html` with (a) a comprehensive `RESULTS_*.md` index, (b) copy helpers for `code .` / opening files in VS Code, and (c) a “Current task” box linking to `roadmap_table.md` (Task 1 highlighted).
  - Added `logic_reasoning_example_full_pass` to the logic suite (mirrors Copilot example; expects decisive `contradiction_resolve`).
  - Re-ran `AI Brain: eval`: PASS.
- Task completed (2026-01-26): transcribed the roadmap table from screenshot into `roadmap_table.md`.
- [x] Align reasoning operator outputs with Copilot example formatting.
  - Updated `propose_actions()` to include overridden candidates (review/synthesis) and to emit all four example reasons in deterministic order.
  - Updated `detect_contradictions()` to return contradiction `relations` as small descriptors (pred/obj/confidence/source) and also keep indices for debugging.
  - Updated `check_constraints()` reason strings for volume range violations (e.g. “volume exceeds allowed maximum”).
  - Updated `RelationalMeasurement()` reason_chain to include a leading rule: `hard_violation OR contradiction → contradiction_resolve`.
  - Re-ran `AI Brain: eval`: PASS.

- [x] Add Copilot “golden reasoning trace” fixture + stricter eval assertions.
  - Saved golden trace JSON under `eval_cases/golden_traces/golden_trace_contradiction_resolve.json`.
  - Tightened `logic_reasoning_example_full_pass` to assert golden ordering/strings (recommended_actions + constraint reason + contradiction relation descriptors + reasons set).
  - Re-ran `AI Brain: eval`: PASS.

- [x] Add synthesis-path golden trace + eval gate.
  - Saved clean-path trace as `eval_cases/golden_traces/golden_trace_synthesis.json`.
  - Updated `module_reasoning.propose_actions()` clean-path behavior to emit `recommended_actions` `["synthesis","review"]` and reasons including: “high similarity and usefulness”, “objective alignment”, “no contradictions”, “no constraint violations”.
  - Added `logic_golden_trace_synthesis_pass` to `run_eval.py`.
  - Re-ran `AI Brain: eval`: PASS.

- [ ] Add one more eval gate: objective_links + focus snapshot persistence.
  - Ensure `relational_state.focus_snapshot` and `objective_links` exist and are stable when objectives are present.

- [ ] Repo hygiene: ensure binary artifacts are not tracked.
  - `.gitignore` now excludes `*.zip`; consider removing `AI_Brain_Snapshot.zip` from git history/index if it’s currently tracked.

- [x] Add a durable “VSCode Agent Mode Instruction Block” doc to the repo.
  - Created `VSCODE_AGENT_MODE_INSTRUCTION_BLOCK.md` containing the instruction block plus repo-specific annotations (implemented stages + what’s superseded).
  - Notes that minimal deterministic constraint reasoning + runtime propagation already exist and are eval-gated.

- [x] Align with Copilot deliverable-6 spec nits.
  - Updated `module_relational_adapter.attach_spatial_relational_state()` to always return `record_path`.
  - Updated Stage-1 relational_state init in `module_storage._ensure_relational_state()` to include `focus_snapshot` (default `None`).
  - Re-ran `AI Brain: eval`: PASS.

## Inventory (folders + files)

### Top-level (workspace root)

Folders:
- `.git/`, `.github/`, `.vscode/`
- `ActiveSpace/`, `HoldingSpace/`, `TemporaryQueue/`, `DiscardSpace/`
- `AI_Brain/` (separate sub-workspace for 3D measurement)
- `AI_Coder_Controller/`
- `LongTermStore/`, `memory/`, `schemas/`, `Scripts/`, `eval_cases/`, `Include/`, `Lib/`

Key files:
- Entry/runner: `main.py`, `bootstrap.py`, `cli.py`, `run_eval.py`
- Core modules: `module_integration.py`, `module_storage.py`, `module_tools.py`, `module_measure.py`, `module_select.py`, `module_toggle.py`, `module_scheduler.py`, `module_objectives.py`, `module_collector.py`, `module_awareness.py`, `module_determinism.py`
- Config: `config.json`
- Docs/results: `README.md`, `REPO_SETUP_LOG.md`, many `RESULTS_*.md`
- Scratch notes: `temp.md`, `temp_2.md` … `temp_11.md`

### AI_Brain (sub-workspace)

Folders:
- `measurement_engine/`, `memory/`, `perception/`, `reasoning/`, `learning/`, `interfaces/`, `simulation/`, `diagnostics/`, `logs/`

Key files:
- Boot: `brain_init.py`, `brain_config.yaml`, `brain_state.json`, `brain_clock.py`
- Routing: `brain_memory_router.py`
- Docs/specs: `README.md`, `ARCHITECTURE.md`, `MEASUREMENT_SPEC.md`, `LEARNING_SPEC.md`, `REASONING_SPEC.md`, `SPATIAL_MEMORY_SPEC.md`, `MEASUREMENT_SPEC.md`, `NEXT_TASKS.md`
- API: `interfaces/api_server` (FastAPI/uvicorn scaffold referenced in README)

## Progress assessment (what appears completed vs pending)

### Root system (text/semantic “AI Brain”)

Evidence from `README.md` + code reads suggests these are implemented to a “working prototype” level:
- CLI workflows: `cli.py cycle`, `eval`, `status`, `stress`, policy tuning, snapshot export
- Storage pipeline with atomic writes + backups + schema validation: `module_storage.py`
- Determinism support (fixed timestamps) and determinism reporting: `module_determinism.py` + CLI wrappers
- Measurement report with weighted scoring + decisive recommendation: `module_measure.measure_information()`
- Toggle policy driving movement between `TemporaryQueue/ActiveSpace/HoldingSpace`: `module_toggle.decide_toggle()`
- Orchestration loop for a cycle: `module_integration.RelationalMeasurement()`

Still incomplete / inconsistent (based on structure and some hard-coded behavior):
- Hard-coded absolute path usage still appears in `module_integration.ProcessIncomingData()` (and some fallbacks)
- “Objectives” and reasoning are mostly heuristic/rule-based; there’s scaffolding for evidence capture and LLM/search hooks, but it’s not a cohesive reasoning layer yet
- Two parallel architectures exist: root “text brain” vs `AI_Brain/` “3D brain”; integration between them is not defined

### AI_Brain sub-workspace (3D measurement core)

This appears intentionally minimal and cleanly layered:
- Runnable boot path (`brain_init.py`) that:
  - ticks a clock
  - loads or synthesizes a point cloud
  - runs measurement
  - routes measurement into memory
  - persists spatial memory
- Architecture and specs exist, but reasoning/learning are currently placeholders (explicitly stated)

## Workflow logic assessment

### Root workflow (RelationalMeasurement)

Current workflow is coherent as a pipeline:
1. Store item into LongTermStore (with repetition + description)
2. Ensure item is present in TemporaryQueue for decisions
3. Optionally collect results (collector plan)
4. Compute signals: similarity, familiarity, usefulness, synthesis potential, objective alignment, selection ranking
5. Compute measurement report with weighted arbiter and “decisive recommendation”
6. Apply policy in an arbiter step to choose accepted/rejected actions
7. Decide target space (Active vs Holding) via `module_toggle.decide_toggle()`
8. Move JSON between spaces and schedule synthesis when activated

Main structural concern: **responsibilities are mixed inside `RelationalMeasurement()`** (storage, queuing, collection, scoring, evidence capture, policy, movement, scheduling). It works, but it will become brittle as features grow.

### AI_Brain workflow (3D)

Current workflow is also coherent and cleaner:
- `brain_init.py` is effectively a small orchestrator with clear boundaries:
  - measurement engine (pure-ish computation)
  - memory routing
  - spatial memory persistence

Main concern here: reasoning/learning layers are currently “empty shells” (as expected), so the workflow is not a full “brain” yet—just a measurement core.

## Package / module structure recommendations

### High-value refactor for the root system

Goal: keep current behavior, but make the “brain workflow” legible and testable.

Recommended package layout (example):
- `brain/`
  - `ingest/` (cycle input + normalization)
  - `storage/` (LongTermStore IO, schemas, atomic writes)
  - `signals/` (similarity/usefulness/repeat/contradiction calculations)
  - `policy/` (toggle rules, thresholds, presets, tuning)
  - `scheduler/` (review/synthesis scheduling)
  - `collectors/` (search/web/LLM evidence capture)
  - `orchestrator/` (one “cycle” function that composes the above)
  - `cli/` (thin wrappers that call orchestrator)

Concrete improvements based on observed code:
- Remove/avoid hard-coded absolute paths in orchestration; always use `resolve_path()` and/or `safe_join()`
- Split `RelationalMeasurement()` into smaller pure functions so:
  - scoring is deterministic given inputs
  - IO side effects are isolated
  - policies are easy to test
- Formalize a small set of shared data contracts (e.g., `CycleInput`, `MeasurementReport`, `ToggleDecision`) and keep them stable

### Clarify the relationship between root “text brain” and AI_Brain “3D brain”

Right now you effectively have **two brains**:
- Root: language-context pipeline with storage, scoring, toggling
- AI_Brain: 3D measurement core with spatial memory

Recommendation:
- Decide whether `AI_Brain/` is:
  - (A) an independent project, OR
  - (B) a subsystem under one unified brain.

If (B), introduce a single “orchestrator” interface and let both subsystems implement the same pattern:
- `measure()` returns a report
- `route_to_memory()` persists
- `policy_decide()` chooses actions

## “Online recommendations” (general, commonly used patterns)

These are broadly recommended approaches (by software architecture + LLM/RAG engineering communities) that map well to your codebase:

Architecture patterns:
- Clean Architecture / Hexagonal Architecture: keep pure domain logic separate from IO (files, web, LLM)
- Event-driven pipeline (even if in-process): treat each step as emitting an event/report
- Data contracts first: strongly-typed request/response objects (Python: `pydantic` is common)

Algorithms for language context & reasoning (implementation-agnostic):
- Retrieval-Augmented Generation (RAG) style memory: store chunks + embeddings + metadata; retrieve by similarity and objective filters
- Hybrid retrieval: lexical (BM25) + semantic embeddings
- Reasoning loop patterns: “plan → act (tools) → observe → revise” (often called ReAct-style)
- Constraint-based arbitration: explicit conflict detection + resolution policies (you already started this with contradiction signals)

Common practical library choices (if/when you want them):
- Typed data contracts: `pydantic`
- Vector indexing: `faiss` or `chromadb` (or a simple on-disk cosine index for prototypes)
- Embeddings: `sentence-transformers` (local) or API-based embeddings
- Evaluation harness: regression-style eval cases + deterministic runs (you already have an eval harness + determinism modes)

## Suggested next reading targets (if continuing assessment)

- Root: `module_tools.py` (signals, search/LLM hooks, index build), `module_select.py`, `module_scheduler.py`
- AI_Brain: `interfaces/` FastAPI scaffold, `measurement_engine/` details, `memory/` store/map implementations

## Discovery notes (additional reads on 2026-01-25)

### Root system (language-context pipeline)

- `module_tools._load_config()` caches config in-process (`_CONFIG_CACHE`). If `cli.py` updates `config.json` during the same process, callers won’t see new values unless cache is cleared (this matters for determinism/policy tweaks if you ever run “cycle” in-process repeatedly).
- Core signal functions are currently mostly heuristics / placeholders:
  - `similarity()` always returns `0.85` (placeholder), so “high similarity” conditions will nearly always trigger.
  - `compare_against_objectives()` returns `aligned` only if an objective keyword appears in content; otherwise it returns `conflict` (this is important because it can make “contradiction” the default state).
  - `search_related()` is a simple keyword scan over JSON files in LongTermStore.
- `module_select.rank()` is a lightweight scorer (length + keyword hits + optional objective keyword boosts). Useful as scaffolding, but it is not yet a robust “selector” in the sense of retrieval + reranking.
- `module_scheduler.flag_record()` and deterministic scheduling:
  - `flag_record()` uses deterministic time when enabled (good), but `module_scheduler.py` also contains a hard-coded `ROOT = r"C:\Users\yerbr\AI_Algorithms"` (portability risk).
- Collector behavior (`module_collector.py`):
  - Spawns subprocesses with inline `python -c` code to call selected modules; merges standardized outputs into the semantic record under `collector_outputs`.
  - Writes raw collector arrays under `LongTermStore/ActiveSpace/collector_<id>.json` (note: this is different from the top-level `ActiveSpace/` folder, which can be confusing).
  - Has an allowlist (`modules_allowlist`) and optional resource metrics via `psutil`.
- Determinism suite (`module_determinism.py`) is well thought through for a prototype: it strips dynamic keys, checks collector timestamps/evidence timestamps, checks index stability, and persists a report into `ActiveSpace/determinism_report_<id>.json`.

### Important logic concern discovered

- `module_measure.measure_information()` currently calls:
  - `usefulness(content, ["measurement"], ...)` and
  - `compare_against_objectives(content, ["measurement"])`

  Because `compare_against_objectives()` defaults to `conflict` unless the literal string `measurement` appears in the content, this can make `contradiction_signal` true for most inputs.

  Practical effect: the measurement report can frequently recommend `contradiction_resolve` (and the arbiter in `RelationalMeasurement()` may “hold” more than intended).

  Likely fix direction: pass the real objective set (from `module_objectives`) into `measure_information()`, or change `compare_against_objectives()` to return something like `"unknown"` instead of `"conflict"` when no match is found.

### Eval harness expectations

- `run_eval.py` includes eval cases for: storage, tools path-safety, indexing, collector schema outputs, scheduler, integration, toggle, reason chains, procedure matching, decisive arbiter behavior, and a determinism suite.
- This indicates the “target brain” is intended to include: `reason_chain` population and `matched_procedures` updates during cycles (so reasoning/procedural memory aren’t just ideas—they are part of the acceptance criteria).

### AI_Brain (3D measurement core)

- `AI_Brain/measurement_engine/` uses numeric-prefixed modules and a safe dynamic loader in `__init__.py`.
- `3d_pointcloud_processor.py` supports ASCII `.ply` and `.obj` vertex-only input; `.glb/.gltf` are explicitly unsupported right now.
- `3d_measurement_core.py` computes centroid, bounds, AABB volume, AABB surface area, diagonal length, and a heuristic shape label (cube_like / elongated / rect_prism / flat).
- Memory layer is intentionally minimal:
  - `ObjectMemoryStore` just appends measurement/perception dicts.
  - `SpatialMemoryMap` persists points + measurement list to `memory/spatial_memory.json`.

## Next concrete actions (if you want me to proceed)

- Normalize “objective alignment vs contradiction” semantics so `conflict` isn’t the default.
- Remove hard-coded paths (`module_scheduler.ROOT`, `module_integration.ProcessIncomingData()` absolute file paths) in favor of `resolve_path()` + `safe_join()`.
- Decide whether top-level `ActiveSpace/` vs `LongTermStore/ActiveSpace/` should both exist; if yes, document purpose; if no, consolidate to one.

## Work performed (code changes applied on 2026-01-25)

- Objective/contradiction semantics:
  - Updated `module_tools.compare_against_objectives()` to return `aligned`, `conflict`, or `unknown` (instead of defaulting to `conflict`).
  - Added explicit “conflict marker” heuristics so inputs containing words like `conflict/contradict/contradiction` still produce `conflict`.
  - Updated `module_measure.measure_information()` to accept an `objectives` parameter and use it for `usefulness` + objective relation.
  - Updated `module_integration.RelationalMeasurement()` to pass the real `objectives` set into `measure_information()`.

- Portability / hard-coded paths:
  - Replaced hard-coded absolute LongTermStore paths in `module_integration.ProcessIncomingData()` and related fallbacks with `resolve_path(category)` + `sanitize_id()`.
  - Replaced `module_scheduler.ROOT = r"C:\Users\yerbr\AI_Algorithms"` with `ROOT = _BASE_DIR`.

- Config cache correctness:
  - Added `module_tools._clear_config_cache()` and invoked it after config writes in `cli.py` so the same process sees updated settings.

- Documentation:
  - Added a short note in the root README clarifying the purpose of `ActiveSpace/` vs `LongTermStore/ActiveSpace/`.

## Verification (eval)

- Ran `py -3 run_eval.py` via the VS Code task.
- First run result: `decisive_arbiter` failed (system activated when it should hold on contradiction).
- Fix applied: adjusted `compare_against_objectives()` so explicit conflict markers override alignment-by-keyword.
- Second run result: all eval cases passed, including `decisive_arbiter` and `determinism_suite`.

## Continuation notes (portability + cleanup sweep)

- Removed remaining hard-coded LongTermStore root in `test_self_information.py` by resolving it relative to the workspace.
- Updated `AI_Coder_Controller/src/main.py` to default its `root` to a path derived from `__file__` instead of a fixed absolute path.
- Updated `main.py`’s docstring example output paths to avoid stale `AI_Algorithms_2` references (comment-only).

## Next tasks (recommended)

- Reduce placeholder bias in core signals:
  - Replace `module_tools.similarity()` constant `0.85` with a real similarity implementation (done: token-Jaccard vs semantic index, with self-match exclusion).
  - Consider making `compare_against_objectives()` objective-aware (per-objective weights) rather than keyword-only.

- Clarify storage vs working spaces:
  - Decide whether to keep both `ActiveSpace/` and `LongTermStore/ActiveSpace/` long-term.
  - If keeping both: rename or document the persisted one as `LongTermStore/Telemetry/` or similar.

- Unify objective data flow:
  - Ensure `module_objectives` provides structured objectives (keywords/priority), and thread that same object through measurement → arbiter → scheduling.

## New tasks discovered (2026-01-25)

- Remove duplicate `cmd_policy_show()` definition in `cli.py` (currently defined twice; one silently overrides the other).

- Add a dedicated CLI command to rebuild/inspect the semantic index (useful now that similarity depends on it).

- Add a config-driven similarity method (keep default deterministic Jaccard; add optional TF-IDF cosine using the semantic index).

### Completed

- Removed the duplicate `cmd_policy_show()` definition in `cli.py` (kept the richer `policy.activation` output format).
- Re-ran eval suite; all cases PASS.

- Added `cli.py index` command to rebuild/inspect the semantic index.
- Re-ran eval suite after adding the command; all cases PASS.

- Added config-driven similarity method selection in `module_tools.similarity()`.
  - Default: `jaccard` (existing behavior)
  - Optional: `tfidf` (cosine similarity over TF-IDF, using semantic index tokens)
  - Config keys (optional):
    - `config.json > similarity.method`: `jaccard` or `tfidf`
    - `config.json > similarity.max_docs`: cap docs compared (default 200)
    - `config.json > similarity.max_terms`: cap terms vectorized (default 2048)
- Re-ran eval suite after adding similarity config; all cases PASS.

- Tighten determinism:
  - Standardize timestamps (`...Z`) everywhere in cycle records, collector outputs, and evidence.

## Similarity implementation update (2026-01-25)

- Implemented deterministic token-based similarity in `module_tools.similarity()`:
  - Jaccard similarity over token sets.
  - Compares content to (a) current_subject tokens and (b) LongTermStore semantic index tokens.
  - Adds `exclude_id` to avoid trivial self-matching after storage.
  - Auto-builds `LongTermStore/Index/semantic_index.json` if missing.

- Updated callers:
  - `module_integration.RelationalMeasurement()` passes `exclude_id=<data_id>`.
  - `module_measure.measure_information()` passes `exclude_id=<record id>`.

- Verification:
  - Re-ran eval suite after the similarity change; all cases PASS.

## Persistent agent instructions (2026-01-25)

Goal: enforce the recurring instruction: “log tasks in temp_12.md, perform them autonomously, and back up or diff-log substantial changes.”

Files added:
- `AGENT.md`: human-readable persistent guide for any agent working in this repo.
- `.github/copilot-instructions.md`: the most widely supported Copilot mechanism for persistent repo instructions.
- `.vscode/agents/ai-brain.agent.md`: optional guide file if your VS Code build supports agent guide loading from `.vscode/agents/`.

Notes:
- If VS Code’s “Custom Agents” guide-file loading is enabled in your build, `.vscode/agents/*.agent.md` should be picked up automatically.
- If not, Copilot still reliably reads `.github/copilot-instructions.md` for repo-scoped instructions.

## README note (2026-01-25)

- Added a short section to the root README pointing contributors/agents to `temp_12.md`, `.github/copilot-instructions.md`, and `AGENT.md`.

---

Notes:
- This file intentionally focuses on structure and workflow logic, not on changing code.
- If you want, the next step can be me proposing a concrete refactor plan (minimal diffs) that preserves CLI behavior.

## New tasks discovered (2026-01-25, continued)

High-impact, low-risk fixes to improve “workability” and safety:

- Path-safety hardening:
  - `module_integration.RelationalMeasurement()` writes `TemporaryQueue/<data_id>.json` using the raw `data_id` (unsanitized). This can fail on invalid IDs and is a path traversal risk.
  - `module_toggle.move()` composes `src_path`/`tgt_path` using raw `data_id` (unsanitized). Same risk; also breaks portability for IDs with invalid filename characters.

- Determinism polish:
  - `module_toggle.__ts()` always uses real wall-clock time. In deterministic mode, it should prefer `config.json > determinism.fixed_timestamp` to keep justification metadata reproducible.

Planned actions:
- Patch `module_integration.py` to use `sanitize_id()` for any filename derived from `data_id`.
- Patch `module_toggle.py` to use `sanitize_id()` + `safe_join()` for per-ID paths.
- Patch `module_toggle.__ts()` to honor determinism settings.
- Create `temp_13.md` task list (per user request).
- Re-run eval (`py -3 run_eval.py` via VS Code task) and record results here.

Status update (2026-01-25): executing the path-safety + determinism polish items now; will re-run eval and log results.

Completed (2026-01-25): path-safety hardening + eval

- `module_integration.py`:
  - Require `sanitize_id()` early and remove fallback to raw `data_id` for filesystem paths.
  - Use `safe_join()` for `resolve_path(category)` files and for `TemporaryQueue/<id>.json`.
- `module_toggle.py`:
  - Confirmed `move()` already uses `sanitize_id()` + `safe_join()`.
  - Confirmed `__ts()` already honors determinism (`deterministic_mode` + `fixed_timestamp`).

Verification:
- Re-ran eval suite; all cases PASS.

## Follow-up (2026-01-25): assess temp_13.md

- [x] Assess `temp_13.md` created by other agent sessions and reconcile its task list with what’s already implemented.

## Run request (2026-01-25): run the AI Brain

- Run the brain via CLI (`status` and a single `cycle`) and capture outputs.

Run results (2026-01-25):

- `py -3 cli.py status`:
  - `deterministic_mode: true`
  - `fixed_timestamp: 2025-01-01T00:00:00Z`
  - `index_ids: 41`
  - `activity_cycles: 200`

- `py -3 cli.py cycle --id run_demo_20260125 --content "keyword good synthesis" --category semantic`:
  - Moved `run_demo_20260125` to `ActiveSpace`
  - Scheduled synthesis for the semantic record
  - Labels: `match`, `related`, `useful`, `synthesis_value`, `beneficial`

## Next tasks proposed (2026-01-25): improve “brain performance”

Observations from the run artifacts:
- Determinism leak: cycle uses fixed `cycle_ts`, but `awareness_plan.timestamp` is wall-clock (not fixed).
- Signal mismatch: cycle-level `signals.usefulness` was `useful_now`, while `collector_outputs.module_measure.details.usefulness_signal` was `not_useful` for the same content.
- Timestamp consistency: some logs use `...Z`, others use naive `datetime.now().isoformat()`.
- Dual activity logs exist (`ActiveSpace/activity.json` and `LongTermStore/ActiveSpace/activity.json`), which can diverge.

Planned actions:
- Determinism tightening:
  - Make `module_awareness` timestamps deterministic-aware (use fixed timestamp when enabled).
- Measurement consistency:
  - Align the definition of “usefulness” across `module_tools.usefulness()` and `module_measure` so a single input doesn’t produce contradictory usefulness signals.
  - Add a small “signals provenance” section to the cycle record showing which module computed each signal.
- Timestamp formatting:
  - Normalize non-deterministic-mode timestamps to UTC `...Z` in `module_current_activity` (and any other writers encountered).
- Activity log consolidation:
  - Pick one canonical activity log location (or add a clear bridge that writes to both consistently) and document it.

## Tasks to perform next (2026-01-25)

- [x] Fix usefulness signal mismatch:
  - [x] Ensure cycle-level `signals.usefulness` and stored `collector_outputs.module_measure.details.usefulness_signal` are derived from the same source for the same record.
  - [x] Add `signals_provenance` to cycle records so it’s explicit which module computed each signal.
  - [x] Re-run eval and record results.

- [x] Add optional AI_Brain measurement integration:
  - [x] Add a bridge module that can run the `AI_Brain/` 3D measurement engine from the root pipeline (non-invasive; off by default).
  - [x] Wire it into the collector module list as `ai_brain_measure` (skips when no spatial asset is present).
  - [x] Re-run eval and record results.

Work performed (2026-01-25): usefulness consistency + AI_Brain bridge

- `module_integration.py`:
  - Canonicalized `usefulness` from the measurement report (`module_measure.usefulness_signal`) and synchronized the `useful` label.
  - Added `signals_provenance` to each cycle record.
- `module_collector.py`:
  - Made `module_measure` execution pass objectives explicitly (loads `get_objectives_by_label('measurement')`) to prevent divergence.
  - Added optional collector module `ai_brain_measure` to allowlist and dispatcher.
- `module_ai_brain_bridge.py`:
  - New bridge module to run `AI_Brain` 3D measurement_engine (`load_point_cloud` + `measure_point_cloud`) when a semantic record includes `spatial_asset_path` / `point_cloud_path`.

Verification:
- Re-ran eval suite; all cases PASS.

## New tasks discovered (2026-01-25): dependency hygiene

- [x] Add a top-level dependency file so the repo’s expected packages are explicit.
  - Added `requirements.txt` that includes `AI_Brain/requirements.txt` + `AI_Coder_Controller/requirements.txt` and `psutil`.
- [x] Install missing optional dependency `psutil` (enables resource metrics in `module_collector.py`).
- [x] Re-run eval and record results.
  - Eval: all cases PASS.

Work performed (2026-01-25): determinism leak + measurement default objectives

- `module_awareness.py`:
  - Added deterministic-aware `_now_ts()` and updated all awareness timestamps (including `awareness_plan.timestamp`) to use it.
  - Non-deterministic timestamps now emit UTC `...Z` format.
- `module_measure.py`:
  - When `objectives` is omitted, default to `get_objectives_by_label('measurement')` (fallback: `['measurement']`) to better match the integration path and reduce signal mismatches.

Verification:
- Re-ran eval suite; all cases PASS.

## New task discovered (2026-01-25): assessment procedure

- [x] Create a repeatable assessment procedure (runbook) that:
  - defines where to write assessments,
  - defines the “minimum checks” (status + eval + sample cycle review),
  - ends by composing a next-task list back into `temp_12.md`.
- [x] Link it from `README.md` and `AGENT.md` so VS Code agents can follow it.

## New task discovered (2026-01-25): tuning guide doc

- [x] Add a dedicated tuning guidelines doc (`TUNING_GUIDE.md`) and link it from the root README.

## Next task queued (2026-01-26): Think-Deeper error resolution

Planned actions:
- Upgrade `module_error_resolution.py` additively with:
  - rollback plans (snapshot + restore),
  - statistical validation artifacts (paired test + deterministic Monte Carlo),
  - uncertainty-aware confidence integration (reuse `module_uncertainty`),
  - provenance logging of error reports and resolution execution (`module_provenance`),
  - deterministic execution option (stable task ids + fixed timestamps when requested).
- Add unit tests in `tests/test_error_resolution.py`.
- Add eval gates in `run_eval.py`:
  - `logic_error_resolution_rollback_plan`
  - `logic_error_resolution_stat_validation`
  - `logic_error_resolution_deterministic_execution`

Work performed (2026-01-26): Think-Deeper error resolution

- `module_error_resolution.py`:
  - Added additive Think-Deeper APIs: rollback plans, provenance event helpers, deterministic timestamps/task ids, and statistical validation (paired t-test + deterministic Monte Carlo sampling via `module_uncertainty.sample_distribution`).
  - Kept legacy API intact (`detect_error`, `create_error_resolution_task`, `execute_error_resolution_task`).
- `tests/test_error_resolution.py`:
  - New unit tests for classification, rollback snapshot/restore, validated vs rolled-back outcomes, and deterministic artifacts.
- `run_eval.py`:
  - Added eval gates: `logic_error_resolution_rollback_plan`, `logic_error_resolution_stat_validation`, `logic_error_resolution_deterministic_execution`.

Verification:
- Eval: new error-resolution gates PASS
- `determinism_suite: PASS`

## Next task queued (2026-01-26): wire rollback resolution behind feature flag

Planned actions:
- Add `feature_flags.use_rollback_resolution` (default false) to `config.json`.
- Add provenance log persistence helpers in `module_storage.py` (`load_provenance_log`, `save_provenance_log`).
- Update `module_integration.run_cycle()` to:
  - when flag enabled: create rollback-capable resolution tasks, enqueue as `error_resolution` activities with `metadata.resolution_task`, execute via `execute_resolution_task`, and propagate/persist `provenance_log`.
  - when flag disabled: preserve current legacy behavior.
- Add eval gate `logic_integration_rollback_propagation`.

Work performed (2026-01-26): wired rollback resolution behind feature flag

- `config.json`:
  - Added `feature_flags.use_rollback_resolution` default `false`.
- `module_storage.py`:
  - Added `load_provenance_log()` / `save_provenance_log()` persisting to `LongTermStore/Provenance/provenance_log.json`.
- `module_integration.py`:
  - `run_cycle()` now supports feature-flagged rollback-capable resolution:
    - When enabled: creates `ResolutionTask`s via `create_resolution_task`, enqueues deterministic `error_resolution` activities with `metadata.resolution_task`, executes via `execute_resolution_task`, and propagates/persists `provenance_log`.
    - When disabled: preserves the legacy resolution behavior.
- `run_eval.py`:
  - Added `logic_integration_rollback_propagation`.

Verification:
- `logic_integration_rollback_propagation: PASS`
- `determinism_suite: PASS`

## Next task queued (2026-01-26): module_verifier.py + wiring

Planned actions:
- Add `module_verifier.py` implementing deterministic pre/postcondition checks, validation artifact generation, and escalation policy.
- Wire verifier into `module_activity_manager.run_activity_cycle` (pre-check before selection; post-check + artifact after execution).
- Wire verifier into `module_integration.run_cycle` by passing verifier into the activity execution mapping.
- Add config defaults in `config.json` under `verifier` (p_threshold, min_effect_size, confidence_threshold).
- Add unit tests `tests/test_verifier.py`.
- Add eval gates in `run_eval.py`: `logic_verifier_precondition_enforcement`, `logic_verifier_validation_artifact_shape`, `logic_verifier_deterministic_artifacts`.

Work performed (2026-01-26): module_verifier + wiring

- `module_verifier.py`:
  - Implemented deterministic `check_preconditions`, `check_postconditions`, `generate_validation_artifact`, `escalate_on_failure`.
- `module_activity_manager.py`:
  - Added verifier-aware selection (`select_next_activity(..., verifier_module=...)`).
  - `run_activity_cycle(..., state=...)` now attaches verification artifacts via `execute_activity_with_hooks` when a verifier module is provided.
- `module_integration.py`:
  - Passes verifier into the activity execution mapping (`__verifier__`) and provides verifier context (records_map, last_measure_ts, provenance, config thresholds).
  - Maintains compatibility with eval stubs by falling back if `run_activity_cycle` doesn’t accept the new kwarg.
- `config.json`:
  - Added `verifier` defaults: p_threshold, min_effect_size, confidence_threshold.
- `tests/test_verifier.py`:
  - Added deterministic unit tests for pre/post checks, artifact determinism, escalation.
- `run_eval.py`:
  - Added gates: `logic_verifier_precondition_enforcement`, `logic_verifier_validation_artifact_shape`, `logic_verifier_deterministic_artifacts`.

Verification:
- `logic_verifier_*`: PASS
- `determinism_suite: PASS`
  - Rationale: tuning exists in README, but a standalone guide can capture guardrails, workflow, and configuration knobs (policy thresholds + similarity settings) without bloating the main README.

## Work performed (2026-01-25, continued)

- Path-safety hardening:
  - Updated `module_integration.RelationalMeasurement()` to sanitize the per-ID `TemporaryQueue/<id>.json` filename and to write the sanitized `id` into the temp record.
  - Updated `module_integration.RelationalMeasurement()` to call `module_toggle.move()` with the sanitized `data_id_s` instead of the raw `data_id`.
  - Updated `module_toggle.move()` to enforce `sanitize_id()` and compose `src_path`/`tgt_path` using `safe_join()`.

- Determinism polish:
  - Updated `module_toggle.__ts()` to prefer `config.json > determinism.fixed_timestamp` when `deterministic_mode` is enabled.

## Verification (eval) — continued

- Ran the VS Code task “AI Brain: eval”.
- Result: all listed cases PASS, including `determinism_suite`.

## New tasks discovered (2026-01-25, determinism tightening)

- Deterministic timestamps in storage:
  - `module_storage.store_information()` currently writes `timestamps[]`, `description_ts`, and repetition profile times using wall-clock UTC.
  - In deterministic mode, these should use `determinism.fixed_timestamp` for full reproducibility.

- Deterministic timestamps in activity collector runs:
  - `module_current_activity.log_collector_run()` appends timestamps using wall-clock time.
  - In deterministic mode, these should use `determinism.fixed_timestamp`.

Planned actions:
- Patch `module_storage.py` to use a determinism-aware `_now_ts()` (prefer cached config via `_load_config()`).
- Patch `module_current_activity.py` to use deterministic timestamps in `log_collector_run()`.
- Re-run eval and record results.

## Work performed (2026-01-25, determinism tightening)

- Updated `module_storage.py`:
  - Added `_now_ts()` that returns `determinism.fixed_timestamp` when enabled, else a UTC Z timestamp.
  - Updated `store_information()` to use `_now_ts()` for new and existing record timestamps.

- Updated `module_current_activity.py`:
  - Updated `log_collector_run()` to honor `determinism.fixed_timestamp` when enabled.

## Verification (eval) — determinism tightening

- Re-ran the VS Code task “AI Brain: eval”.
- Result: all listed cases PASS.

## New tasks discovered (2026-01-25, collector timestamp tightening)

- `module_collector.collect_results()` attaches per-module `start_ts` and `end_ts` using wall-clock time.
  - This is fine for normal mode.
  - In deterministic mode, these should use `determinism.fixed_timestamp` for reproducible collector telemetry.

Planned actions:
- Patch `module_collector.py` to use a shared determinism-aware timestamp helper for `start_ts`/`end_ts`.
- Re-run eval and record results.

## Work performed (2026-01-25, collector timestamp tightening)

- Updated `module_collector.py`:
  - Added `_det_ts()` helper.
  - When determinism is enabled, `collect_results()` now sets per-module `start_ts` and `end_ts` to the fixed timestamp.
  - Normal mode behavior is unchanged (uses real timestamps).

## Verification (eval) — collector timestamp tightening

- Re-ran the VS Code task “AI Brain: eval”.
- Result: all listed cases PASS.

## User request (2026-01-26): git commit

- Create a git commit with message `activities`.
  - Steps: inspect `git status`, stage intended files, commit.

## User request (2026-01-26): single copy-paste message for new agent chats (public mirror)

Goal: Provide a single, copy-paste bootstrap message that a fresh VS Code Agent Mode chat can follow to clone/open the public mirror, run adversarial tests + eval gates, verify determinism, and return the specific artifacts.

Paste-ready message:

---

### Purpose

Provide a single, copy‑paste message new VSCode Agent Mode chats can use to understand and act on the temporary public mirror. It tells the agent which files are available, what to run, what to return, and the exact next task to continue work.

---

### Repo and mirror info

**Mirror URL**: `REPLACE_WITH_PUBLIC_REPO_URL`
**Branch**: `main` (or `REPLACE_WITH_BRANCH`)
**Mirror scope**: limited public mirror containing only the modules and tests needed for adversarial harness and evaluation (no secrets, no large logs).

---

### Files included in the mirror

| Filename | Purpose | Notes |
|---|---|---|
| `module_integration.py` | Integration cycle entry points | core `run_cycle` used by scenarios |
| `module_error_resolution.py` | Error detection and rollback logic | includes statistical validation |
| `module_verifier.py` | Pre/postcondition checks and artifact generator | deterministic hashing enabled |
| `module_activity_manager.py` | Activity queue and executor | deterministic queue behavior |
| `module_adversarial_test.py` | Adversarial harness and scenarios S1–S6 | runner `run_scenario(...)` |
| `tests/test_adversarial.py` | Unit tests for scenarios | uses minimal fixtures |
| `config.json` | Determinism and verifier thresholds | sanitized, no secrets |
| `requirements.txt` | Python dependencies | pinned minimal set |
| `tests/fixtures/sample_records.json` | Small dataset for scenarios | < 500 KB |

---

### What I expect the new Copilot/agent chat to do

1. **Clone or open** the public mirror at the provided URL and switch to the specified branch.
2. **Install dependencies** from `requirements.txt` in an isolated environment.
3. **Run the adversarial tests** and eval gates:
   - `pytest tests/test_adversarial.py -q`
   - `python run_eval.py` (if present in the mirror)
4. **Produce and attach** the following artifacts (small text files or excerpts):
   - `pytest` stdout (full run or failing portion)
   - `adversarial_report_S1_small_noise.json` (or the generated report for each scenario)
   - eval output excerpt (last ~200 lines of `run_eval.out`, or equivalent)
5. **Report**:
   - Which tests passed/failed and failing tracebacks.
   - Any failing eval gates and their names.
   - Determinism check: run one scenario twice with `deterministic_mode=True` and confirm identical `provenance_snapshot` arrays.
6. **If tests fail**, include the minimal failing context (stack trace, failing assertion, relevant file and line) and propose a one‑line remediation.

---

### Exact commands to run (PowerShell on Windows)

```powershell
git clone REPLACE_WITH_PUBLIC_REPO_URL mirror-temp
Set-Location mirror-temp
git checkout REPLACE_WITH_BRANCH

py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt

pytest tests/test_adversarial.py -q | Tee-Object -FilePath pytest_adversarial.out

if (Test-Path .\run_eval.py) {
  python .\run_eval.py 2>&1 | Tee-Object -FilePath run_eval.out
} else {
  'run_eval.py not present in mirror; skipping eval.' | Tee-Object -FilePath run_eval.out
}

# deterministic reproducibility check
python - <<'PY'
from module_adversarial_test import run_scenario
r1 = run_scenario("S1_small_noise", deterministic_mode=True)
r2 = run_scenario("S1_small_noise", deterministic_mode=True)
print("provenance_equal:", r1.get("provenance_snapshot") == r2.get("provenance_snapshot"))
PY
```

---

### Exact commands to run (bash / macOS / Linux)

```bash
git clone REPLACE_WITH_PUBLIC_REPO_URL mirror-temp && cd mirror-temp
git checkout REPLACE_WITH_BRANCH

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt

pytest tests/test_adversarial.py -q | tee pytest_adversarial.out

if [ -f run_eval.py ]; then
  python run_eval.py 2>&1 | tee run_eval.out || true
else
  echo "run_eval.py not present in mirror; skipping eval." | tee run_eval.out
fi

# deterministic reproducibility check
python - <<'PY'
from module_adversarial_test import run_scenario
r1 = run_scenario("S1_small_noise", deterministic_mode=True)
r2 = run_scenario("S1_small_noise", deterministic_mode=True)
print("provenance_equal:", r1.get("provenance_snapshot") == r2.get("provenance_snapshot"))
PY
```

---

### Acceptance criteria for this run

- `pytest tests/test_adversarial.py` completes; all tests pass or failing tests are reported with tracebacks.
- `run_eval.py` completes when present; any failing eval gates are listed.
- Determinism check prints `provenance_equal: True`.
- The agent attaches `pytest_adversarial.out`, `run_eval.out`, and `adversarial_report_S1_small_noise.json` (plus other scenario reports if generated).

---

### Constraints and safety

- Do not attempt to access private repos or secrets. Work only with the public mirror.
- Do not attach large binary files; attach only small text excerpts or JSON reports.
- Keep Monte Carlo sample sizes moderate; if tests are slow, report timing and suggest adaptive sampling.

---

### Next task message for the new chat (paste this exactly)

**NextTask:** Run the adversarial harness for all scenarios in deterministic mode and attach the generated reports.

**Context to paste at start of chat:**
- Mirror URL: `REPLACE_WITH_PUBLIC_REPO_URL`
- Branch: `REPLACE_WITH_BRANCH`
- Files included: `module_adversarial_test.py`, `tests/test_adversarial.py`, `config.json`, `module_error_resolution.py`, `module_verifier.py`, `module_activity_manager.py`, `module_integration.py`, `tests/fixtures/sample_records.json`.

**Commands to run:**
- `pytest tests/test_adversarial.py -q`
- `python run_eval.py`
- Determinism check snippet (provided above).

**Deliverables to attach or paste:**
- `pytest` stdout (or failing excerpts)
- `adversarial_report_S1_small_noise.json` (and other scenario reports if generated)
- `run_eval.out` excerpt (last ~200 lines)

**Acceptance criteria:**
- All adversarial tests run; determinism check returns True; eval gates `logic_adversarial_report_shape`, `logic_adversarial_deterministic_repro`, and `logic_adversarial_escalation_policy` pass or failing gates are reported.

---

### If anything unexpected happens

- If a test fails: attach the failing traceback and name the failing test.
- If the mirror is missing a required module or function name differs: report the missing symbol and the file where it was expected.
- If runtime errors reference missing dependencies: attach `pip freeze` output and the error.

---

### Closing note

Paste this message into the new VSCode agent chat so the agent has a clear, actionable checklist and the exact next task to continue the project. Replace the placeholders before running.

## New task (2026-01-26): generate a temporary public mirror folder

User intent: create a minimal, safe-to-publish mirror containing only the adversarial harness + required modules/tests/fixtures, so the desktop Copilot app can access it via a public GitHub repo.

Planned actions:
- Create `scripts/create_public_mirror.py` to build `public_mirror/` deterministically.
- Mirror contents (expected minimal set):
  - Core modules: `module_adversarial_test.py`, `module_error_resolution.py`, `module_provenance.py`, `module_reasoning.py`, `module_retrieval.py`, `module_verifier.py`
  - Dependencies: `module_uncertainty.py`, `module_storage.py`, `module_tools.py`
  - Tests/fixtures: `tests/test_adversarial.py`, `tests/fixtures/sample_records.json`
  - Mirror-only helpers: minimal `run_eval.py`, `requirements.txt`, `README_MIRROR.md`, `.gitignore`
- Run mirror smoke check locally (`pytest -q` inside `public_mirror/`) and record results.

## Work performed (2026-01-26): public mirror generation

- Added generator script: `scripts/create_public_mirror.py`.
- Added fixture (for mirror completeness): `tests/fixtures/sample_records.json`.
- Fixed adversarial scenario S6 to deterministically exercise negative-gain path:
  - Updated: `module_adversarial_test.py` (S6 now uses a counterfactual `coherence_gain=-0.5` so `re_evaluate` is asserted reliably).
- Generated mirror output directory: `public_mirror/` (includes `mirror_manifest.json`, mirror-only `run_eval.py`, minimal `requirements.txt`, `.gitignore`, and `README_MIRROR.md`).

## Verification (2026-01-26): public mirror smoke

- Installed: `pytest` into the local venv for smoke testing.
- Mirror tests: `public_mirror/` `pytest -q` => **7 passed** (warnings only).
- Mirror eval: `public_mirror/run_eval.py` => all adversarial gates PASS.
- Root eval (filtered): `logic_adversarial_*: PASS`, `determinism_suite: PASS`.

Artifacts written at repo root:
- `pytest_public_mirror.out`
- `run_eval_public_mirror.out`

## New task (2026-01-26): Copilot app attachments folder + instructions

User intent: prepare a folder of small, attachable text files plus a paste-ready “new chat” message for the desktop Copilot app (not VS Code), referencing the generated public mirror.

Planned actions:
- Create folder `Copilot_app_Attachments_txt_files_of_py_modules/` at repo root.
- Rename and move `temp_23_v2.md` into that folder; update it to reference `public_mirror/README_MIRROR.md`.
- Add a dedicated procedure/instructions file for the desktop Copilot app: what to attach + what message to paste in a new Copilot app chat.
- Add a small section/link on `index.html` so the developer can quickly find the mirror/attachments workflow.

## Work performed (2026-01-26): Copilot app attachments folder + instructions

- Created folder: `Copilot_app_Attachments_txt_files_of_py_modules/`.
- Renamed/moved: `temp_23_v2.md` -> `Copilot_app_Attachments_txt_files_of_py_modules/CopilotApp_Mirror_Bootstrap.md` (updated to reference the mirror and provide a paste-ready Copilot app message).
- Added procedure doc: `Copilot_app_Attachments_txt_files_of_py_modules/CopilotApp_Procedure_PublicMirror_and_Attachments.md`.
- Added exporter script: `scripts/export_copilot_app_attachments.py`.
  - Output folder: `Copilot_app_Attachments_txt_files_of_py_modules/exports/` (includes .txt copies of .py modules plus mirror docs).
- Updated dashboard: `index.html` now includes a “Copilot App Mirror” section with links to the mirror docs and procedure.

- Completed (2026-01-26): objective lifecycle timestamps already honor determinism.
  - Verified: `module_objectives.py` uses a config-aware `_now_ts()` that returns `determinism.fixed_timestamp` when deterministic mode is enabled.
  - Note: a dedicated `run_eval.py` gate for this is optional (not required for current suite).

- New task (2026-01-26): implement Copilot “staging observation window” follow-ups (repo-side).
  - Add: `tools/verify_sweep_outputs.py` to assert sweep output integrity (CSV↔reports), filename pattern, and optional deterministic equality across two runs (ignoring `report_file`).
  - Add: top-level `metrics_dashboard.py` wrapper so the documented command `python metrics_dashboard.py ...` works (delegates to `scripts/metrics_dashboard.py`).
  - Verification: run VS Code task “AI Brain: eval” and record results.

- Completed (2026-01-26): Copilot “staging observation window” follow-ups.
  - Added: `tools/verify_sweep_outputs.py` (checks missing files + canonical filename pattern; supports `--compare-dir` determinism compare ignoring `report_file`).
  - Added: `metrics_dashboard.py` wrapper (delegates to `scripts/metrics_dashboard.py`).
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- Completed (2026-01-26): documented sweep output verification helper.
  - Updated: `docs/SWEEP_RUN.md` adds a short “Verify outputs (optional)” section for `tools/verify_sweep_outputs.py`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): add “Staging Observation Window” to `index.html`.
  - Add: copy/paste staging commands (pytest adversarial + eval + metrics dashboard + optional sweep verify).
  - Add: a button that opens a popup explaining what it is, how it relates to AI Brain integration, and how it uses/produces metrics data.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): added “Staging Observation Window” section + description popup.
  - Updated: `index.html` Rollout Helpers now includes staging commands and a “What is this?” popup describing AI Brain integration + metrics (`TemporaryQueue/metrics.json`).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): add production rollout/promotion docs (operationalizing staging confidence).
  - Add: `docs/PRODUCTION_ROLLOUT.md` describing gradual rollout plan, acceptance thresholds, and rollback/triage workflow.
  - Add: `docs/PROMOTION_PR_TEMPLATE.md` (paste-ready PR template) and `docs/RELEASE_NOTES.md` (release log).
  - Update: `tools/verify_sweep_outputs.py` to support a simple `--detcheck <dirA> <dirB>` alias for comparing two report directories (ignore `report_file`).
  - Update: `roadmap_table.md` with an “Ops / rollout” item for the promotion runbook.
  - Update: `index.html` to link to the new rollout docs.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): production rollout/promotion docs.
  - Added: `docs/PRODUCTION_ROLLOUT.md`, `docs/PROMOTION_PR_TEMPLATE.md`, `docs/RELEASE_NOTES.md`.
  - Updated: `tools/verify_sweep_outputs.py` adds `--detcheck DIR_A DIR_B` (compare report dirs; ignore `report_file`).
  - Updated: `roadmap_table.md` adds an Ops/rollout row; `index.html` links the new docs (Quick Links + staging popup).
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-26): close remaining determinism holes in backups + integration timestamps.
  - Update: `module_storage._backup_existing(...)` to use fixed timestamp in backup filenames when deterministic mode is enabled.
  - Update: replace any remaining direct `datetime.now()` writes in `module_integration.py` with deterministic timestamp helpers.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-26): closed determinism holes in backups + integration timestamps.
  - Updated: `module_storage.py` `_backup_existing(...)` now uses `determinism.fixed_timestamp` (when enabled) to name backups deterministically.
  - Updated: `module_integration.py` procedure-match persistence now uses fixed timestamp in deterministic mode.
  - Verification: ran VS Code task “AI Brain: eval” (completed; exit code 0).

- New task (2026-01-26): retrieval-backed selection migration (opt-in).
  - Update: `module_integration.py` selection_migration to optionally incorporate `module_retrieval` scoring components (still default-off).
  - Add: `run_eval.py` logic gate that enables the new flag via config-cache patch and asserts deterministic/stable `decision_signals.selection_score` across two runs.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-26): retrieval-backed selection migration (opt-in).
  - Updated: `module_integration.py` supports `selection_migration.use_retrieval_scores` and `retrieval_objective_alignment_threshold`.
  - Updated: `config.json` documents the new selection_migration flags (defaults unchanged/off).
  - Added: `run_eval.py` gate `logic_selection_migration_retrieval_score_deterministic`.
  - Verification: ran VS Code task “AI Brain: eval” (PASS; new gate PASS).

- New task (2026-01-27): expand public mirror + Copilot app exports (core_thinking profile).
  - Update: `scripts/create_public_mirror.py` to support `--profile core_thinking` (adds `module_*.py` and selected docs) while keeping default mirror behavior unchanged.
  - Update: `scripts/create_public_mirror.py` manifest to include mirror-only files (README/PUBLISHING/run_eval/requirements/.gitignore) for completeness.
  - Update: `scripts/export_copilot_app_attachments.py` to export files based on `public_mirror/mirror_manifest.json` (so exports automatically track mirror contents), with collision-safe attachment filenames.
  - Update: Copilot app docs to describe profiles + updated exports.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): expanded public mirror + Copilot app exports (core_thinking profile).
  - Updated: `scripts/create_public_mirror.py` adds `--profile` (`adversarial` default; `core_thinking` includes `module_*.py` + selected docs) and records the profile in `public_mirror/mirror_manifest.json`.
  - Updated: `public_mirror/mirror_manifest.json` now includes mirror-only files (README/PUBLISHING/run_eval/requirements/.gitignore) so downstream tooling can follow the manifest.

- New task (2026-01-27): hide owner-only information and add a secrets pattern.
  - Update: `index.html` to remove/avoid publishing owner contact details; replace with a generic pointer to an owner-only secrets workflow.
  - Add: `docs/SECRETS.md` describing safe handling (keep out of git, don’t host publicly) and a local-only `secrets.local.json` pattern.
  - Add: `secrets.example.json` and update `.gitignore` to ignore `secrets.local.json`.
  - Optional: add a local-only “Load secrets file” button in `index.html` (file picker) so owner details can be viewed without committing them.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): owner-only secrets workflow.
  - Updated: `.gitignore` ignores `secrets.local.json`.
  - Added: `docs/SECRETS.md` + `secrets.example.json`.
  - Updated: `index.html` removes the public “Owner reminder” and adds a local-only “Load Secrets” file picker + a short Secrets popup.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): restore the user reminder on the dashboard.
  - Update: `index.html` to keep a visible reminder but make it a safe setup checklist for secrets (no embedded owner contact info).
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): restored dashboard reminder (safe).
  - Updated: `index.html` “Current Task” now includes a removable reminder/checklist for setting up `secrets.local.json` and verifying the Load Secrets flow.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): operational canary monitoring artifacts (“Next”).
  - Add: `scripts/canary_cycle_checks.py` one-command runner that executes the per-cycle monitoring checks and writes timestamped artifacts under `TemporaryQueue/canary_checks/`.
  - Add: `docs/TRIAGE_TICKET_TEMPLATE.md` for rollback/escalation/disagreement events (required attachments checklist).
  - Add (optional): `.github/workflows/production_monitor_dispatch.yml` as manual-only `workflow_dispatch` (no schedule) to run the same checks and upload artifacts.
  - Update: `docs/PRODUCTION_ROLLOUT.md` + `index.html` to point to the new canary runner and triage template.
  - Verification: run VS Code task “AI Brain: eval” and log completion.
  - Updated: `scripts/export_copilot_app_attachments.py` exports based on the mirror manifest (no hardcoded file list) and remains deterministic.
  - Updated: `Copilot_app_Attachments_txt_files_of_py_modules/*` docs describe how to regenerate the mirror with profiles and export attachments.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): upgrade `index.html` Copilot App Mirror “How to use it”.
  - Update: expand the Copilot app mirror section with a short step-by-step (build mirror → export attachments → publish mirror) and copy/paste commands.
  - Update: mention `--profile core_thinking` and that exports follow `mirror_manifest.json`.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): upgraded `index.html` Copilot App Mirror “How to use it”.
  - Updated: `index.html` now includes a step-by-step mini-runbook plus copy buttons for building the mirror (small + core_thinking), exporting attachments, and opening the exports folder.
  - Updated: clarified mirror profiles and that attachment exports follow `public_mirror/mirror_manifest.json`.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): upgrade `index.html` paste-ready Copilot app prompt.
  - Update: improve the existing “Paste-ready assessment prompt” to be mirror/manifest-aware (profile-driven) and include concrete deliverables.
  - Add: a second paste-ready message template specifically for the desktop Copilot app (includes placeholders for repo URL + branch).
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): upgraded `index.html` paste-ready Copilot app prompt.
  - Updated: existing prompt now starts from `mirror_manifest.json` (profile-aware) and requests concrete deliverables tied to file/function names.
  - Added: a dedicated “Copilot app paste message (mirror URL)” template with placeholders for repo URL + branch.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

- New task (2026-01-27): improve dashboard “Copy” behavior for multi-line prompts.
  - Update: `index.html` `copyCmd(...)` should normalize multi-line text (trim leading/trailing blank lines and strip common indentation) so copied prompts don’t include HTML indentation spaces.
  - Verification: run VS Code task “AI Brain: eval” and log completion.

- Completed (2026-01-27): improved dashboard “Copy” behavior for multi-line prompts.
  - Updated: `index.html` copy now normalizes multi-line blocks so pasted prompts don’t include leading indentation from HTML formatting.
  - Verification: ran VS Code task “AI Brain: eval” (completed).

