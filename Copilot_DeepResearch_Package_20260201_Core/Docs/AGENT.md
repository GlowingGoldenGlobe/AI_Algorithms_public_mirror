# AGENT.md — Persistent Agent Instructions (AI_Algorithms)

This file is a persistent guide for any coding agent working in this repository.

## Primary Operating Rules

1. **Don’t ask for permission for small/medium improvements.**
   - If an improvement is helpful and low-risk, add it to `temp_12.md` as a task and perform it.

2. **Always log work in `temp_12.md`.**
   - When you discover a helpful task, add it to the task list.
   - After implementing, record what changed, why, and how it was verified.

2b. **Optional: use a dedicated task-list file for complex work.**
   - Keep `temp_12.md` as the primary audit log (required), but for multi-step work you may also create a focused task list file like `Copilot_Tasks_2.md` (or `Copilot_Tasks_<N>.md`).
   - Use the task list file to keep the plan readable (goals, steps, acceptance criteria). In `temp_12.md`, log a short pointer to the task list and the final outcomes.
   - This is useful when a change spans multiple areas (e.g., dashboard + scripts + config) and you want a clean checklist without bloating the main log.

3. **Backups / diffs for substantial changes.**
   - If a change is substantial (multi-file refactor, behavior change, or large edits):
     - Create a backup copy of the file(s) being changed (e.g., `filename.bak_YYYYMMDDTHHMMSSZ`).
     - Or record a clear “diff summary” in `temp_12.md` (what functions/files changed and why).

4. **Prefer deterministic + testable changes.**
   - Keep logic deterministic when possible; avoid nondeterministic timestamps unless gated by determinism settings.
   - After changes, run the existing eval task and record results.

## When to use the desktop Copilot app (external)

This repo is typically worked on in **VS Code Agent Mode** (local read/write + tasks). The standalone **Microsoft Copilot desktop app** is a separate tool that is useful for review and research.

Use **VS Code Agent Mode (local)** for:
- Implementing changes (code + docs) and keeping diffs small.
- Running verification (`AI Brain: eval`, `pytest -q`, sanity checks).
- Debugging failures with direct stack traces and repro.

Ask the user to use the **Copilot app (external)** when you need:
- Long-form architecture review, alternative design exploration, or “fresh eyes” critique.
- Broader research-style synthesis that doesn’t require executing code.
- A mirror-based assessment against the public repo URL (so the reviewer can browse/search without pasting files).

When you do ask for Copilot help, be explicit about what you want back:
- Exact file paths + quoted snippets for any issues.
- A ranked list of recommended changes with rationale and risk.
- Clear PASS/FAIL checks (e.g., `pytest -q`, `python run_eval.py`, determinism repro steps).

Reference docs for the workflow:
- `Copilot_app_Attachments_txt_files_of_py_modules/CopilotApp_Mirror_Bootstrap.md` (paste-ready new chat message)
- `Copilot_app_Attachments_txt_files_of_py_modules/CopilotApp_Procedure_PublicMirror_and_Attachments.md` (how to mirror/attach)
- `docs/PUBLIC_MIRROR_WORKFLOW.md` (two-repo mirror publishing)

## Project Conventions

- Root system (“language-context pipeline”) lives at workspace root (`module_*.py`, `cli.py`, etc.).
- 3D measurement core is in `AI_Brain/` and should remain cleanly layered.
- Storage must use safe path resolution (`sanitize_id`, `safe_join`, `resolve_path`) instead of absolute paths.

## Category Positioning (LLM vs. AI Brain)

- This repo is **not** an LLM. It is a deterministic, measurement‑first cognitive loop with file‑backed memory and auditable artifacts.
- When describing “smartness,” ground it in: explicit measurements, objective alignment, determinism, and traceable decision outputs.
- Avoid comparing with market LLMs by capability claims. Instead compare **method** (measurement‑first vs. probabilistic text inference) and **artifacts** (auditable traces vs. opaque outputs).
- Cite authoritative sources in this repo: `DESIGN_GOALS.md`, `README.md`, and `temp_12.md`.
- If preparing content for external AI reviewers, use the normalized response format in `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_AI_Guide.md`.

## Verification

- Prefer running the VS Code task “AI Brain: eval”.
- If a change affects determinism, also run the determinism suite or ensure it still passes in eval.

## Assessment / Reporting

- Follow the runbook in `ASSESSMENT_PROCEDURE.md`.
- Write assessments and next-task recommendations into `temp_12.md` (primary log).

Practical example:
- If you need to generate metrics for visualization without overwriting run outputs, you can flush comparison metrics to `TemporaryQueue/metrics_compare.json` and point the dashboard at it (server mode). Track the steps in a `Copilot_Tasks_*.md` file, and record the final verification (e.g., “AI Brain: eval PASS”) in `temp_12.md`.
