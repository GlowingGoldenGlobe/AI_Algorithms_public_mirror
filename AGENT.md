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

5. **When corrected by the user, capture the correction as procedure.**
   - If the user points out something you “should have already done,” treat it as a missing checklist item.
   - First: comply immediately (don’t argue; don’t over-explain).
   - Then (only if it’s smart and applicable): write a short note in `temp_12.md` describing the correction as a reusable rule.
   - Finally (only if it genuinely generalizes beyond the current task): update this file (`AGENT.md`) with a brief, future-proof guideline.
   - Goal: reduce repeated omissions by turning feedback into a deterministic process step.

6. **If options aren’t prioritized, start from the top.**
   - When offering multiple options and no explicit “importance” ordering is provided, treat the list order as the default priority.
   - Default action: proceed with the first/top option.

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

## Metric Definitions (Agent Memory)

- Synapse (analogy only): metaphor for a discrete thought-connection event (conceptual, not a software module).
- Neural algorithm activity: code execution that performs thinking-like operations (scoring/selecting/retrieving/integrating).
- 3D measurement activity: computations tied to relational measurement (constructing relational state, measuring entities/relations, producing measurement reports).

## Category Positioning (LLM vs. AI Brain)

- This repo is **not** an LLM. It is a deterministic, measurement‑first cognitive loop with file‑backed memory and auditable artifacts.
- When describing “smartness,” ground it in: explicit measurements, objective alignment, determinism, and traceable decision outputs.
- Avoid comparing with market LLMs by capability claims. Instead compare **method** (measurement‑first vs. probabilistic text inference) and **artifacts** (auditable traces vs. opaque outputs).
- Cite authoritative sources in this repo: `DESIGN_GOALS.md`, `README.md`, and `temp_12.md`.
- If preparing content for external AI reviewers, use the normalized response format in `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_AI_Guide.md`.

## Verification

- Prefer running the VS Code task “AI Brain: eval”.
- If a change affects determinism, also run the determinism suite or ensure it still passes in eval.

## “Start AI Brain” (Agent Mode convention)

When the user says **Start** (e.g., “Start”, “Start Project”, “Run workflow”, “Start AI Brain”), treat it as a request to run the repo’s start/init event.

- Preferred agent action: run the VS Code task “AI Brain: init” (runs `cli.py init` via the repo venv).
- Fallback (no tasks available): run `python cli.py init` (calls `module_integration.initialize_ai_brain()` and ensures workspace state/objectives are present).
- If the user wants *continuous operation*, follow up by starting a loop (e.g., orchestrator daemon) — do not assume this from “Start” alone.
- Avoid concurrent writers: don’t run eval/canary while the orchestrator daemon is running.

## Assessment / Reporting

- Follow the runbook in `ASSESSMENT_PROCEDURE.md`.
- Write assessments and next-task recommendations into `temp_12.md` (primary log).
