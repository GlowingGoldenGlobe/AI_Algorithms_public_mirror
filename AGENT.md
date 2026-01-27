# AGENT.md — Persistent Agent Instructions (AI_Algorithms)

This file is a persistent guide for any coding agent working in this repository.

## Primary Operating Rules

1. **Don’t ask for permission for small/medium improvements.**
   - If an improvement is helpful and low-risk, add it to `temp_12.md` as a task and perform it.

2. **Always log work in `temp_12.md`.**
   - When you discover a helpful task, add it to the task list.
   - After implementing, record what changed, why, and how it was verified.

3. **Backups / diffs for substantial changes.**
   - If a change is substantial (multi-file refactor, behavior change, or large edits):
     - Create a backup copy of the file(s) being changed (e.g., `filename.bak_YYYYMMDDTHHMMSSZ`).
     - Or record a clear “diff summary” in `temp_12.md` (what functions/files changed and why).

4. **Prefer deterministic + testable changes.**
   - Keep logic deterministic when possible; avoid nondeterministic timestamps unless gated by determinism settings.
   - After changes, run the existing eval task and record results.

## Project Conventions

- Root system (“language-context pipeline”) lives at workspace root (`module_*.py`, `cli.py`, etc.).
- 3D measurement core is in `AI_Brain/` and should remain cleanly layered.
- Storage must use safe path resolution (`sanitize_id`, `safe_join`, `resolve_path`) instead of absolute paths.

## Verification

- Prefer running the VS Code task “AI Brain: eval”.
- If a change affects determinism, also run the determinism suite or ensure it still passes in eval.

## Assessment / Reporting

- Follow the runbook in `ASSESSMENT_PROCEDURE.md`.
- Write assessments and next-task recommendations into `temp_12.md` (primary log).
