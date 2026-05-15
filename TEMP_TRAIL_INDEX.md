# TEMP_TRAIL_INDEX.md — Project thinking + temp file progression

This repo contains a set of `temp_[n].md` files that act like a chronological “upgrade trail”: early architecture sketches, later assessments, and migration plans.

## What to read first (how the AI Brain thinks)

1) **Current system overview**
- `README.md`
- `DESIGN_GOALS.md`

2) **How it stays correct + repeatable (the discipline)**
- `RESULTS_EvalHarness.md` (what counts as PASS/FAIL)
- `RESULTS_Determinism.md` (reproducibility and fixed timestamps)
- `RESULTS_PathSafety.md` + `RESULTS_AtomicWrites.md` (safe persistence)

3) **The actual “thinking loop” in code**
- `module_integration.py` (cycle orchestration)
- `module_reasoning.py` (synthesis + artifacts)
- `module_retrieval.py` (what gets pulled in)
- `module_select.py` (what gets chosen)
- `module_scheduler.py` (what gets revisited)
- `module_verifier.py` + `module_error_resolution.py` (validation, rollbacks, escalation)

4) **The canonical working log (what changed and why)**
- `orchestration/vscode_orchestration_gpt5/project_modifications_tasks/tasks_032026_1.md` (active monthly task log; `temp_Feb2026_1.md` remains the February archive and `temp_12.md` remains a deeper legacy archive)

Tip: if you want a quick “run → open 2 files → interpret the cycle” path, start with the Beginner 5-minute walkthrough in `learn.html#walkthrough`.

## Temp progression map (high-signal)

### Early trail (foundation)
- `temp_2.md` — early loop and objectives-driven behavior concepts
- `temp_3.md` — missing pieces list (procedural matching, expansion, actions)
- `temp_5.md` — large phased plan (collector/concurrency, config, observability)
- `temp_6.md` — Phase A–F follow-up plan
- `temp_7.md` — safety/infra checklist (schemas, atomic writes, path safety, indexing)
- `temp_8.md` — description-first cognition target and cycle-record emphasis
- `temp_9.md` — policy tuning + determinism/CLI workflow notes

### Architecture synthesis / doctrine
- `temp_15.md` / `temp_16.md` — evidence-based gaps and next-core work
- `temp_18.md` — architecture doctrine (modules as “brain activities”)
- `temp_19.md` — concrete transformation task list

### Recent assessments (2026-01-26)
- `temp_24.md` — assessment of the full temp trail + gaps + prioritized follow-ups
- `temp_25.md` — systematic workflow/component audit (how the system thinks end-to-end)
- `temp_26.md` — deeper module review + determinism holes + orchestration bottlenecks
- `temp_27.md` — orchestration unification assessment and eval-gated migration plan
- `temp_28.md` — incremental assessment continuation (observability-only orchestration + next phases)

## Notes

- `RESULTS_*.md` files are the “stable history” of major upgrades; the `temp_*.md` files are the narrative trail.
