# AGENT.md — Persistent Agent Instructions (AI_Algorithms)

This file is a persistent guide for any coding agent working in this repository.

## Primary Operating Rules

0. **Project purpose comes first.**
   - Your mission is to make the project workable, smart, and able to accomplish its objectives.
   - When the user says “Next,” propose a concrete, high‑leverage orchestrator action that advances AI Brain readiness (continuous thinking/performance), not a generic status reply.
   - Tie recommendations to observable gates (ops health, determinism, memory/RAG readiness, resource budgets) and record them in the active monthly log.

0a. **Hardware prompt auto‑report.**
   - When the user asks about hardware health/monitor/metrics (or similar), respond with the hardware report template in [ASSESSMENT_PROCEDURE.md](ASSESSMENT_PROCEDURE.md), using `TemporaryQueue/ops_status.json`, `TemporaryQueue/hardware_preflight.json`, and `TemporaryQueue/ai_brain_metrics_log.jsonl` as inputs.
   - If the files are missing or stale, say so and suggest running the hardware preflight task or ops status report.

0b. **“Is it running?” required-results template.**
    - This is the operator-facing AI Brain status template. When asked whether the AI Brain is running/active, answer with this literal result structure:
      1. **Direct verdict** — one sentence stating `running`, `active but degraded`, `paused`, or `stopped`.
      2. **Runtime evidence** — `TemporaryQueue/ops_status.json` values for `runtime.running`, `runtime.state`, `runtime.run_state_indicator`, `runtime.performance_state`, `runtime.activity_phase`, `runtime.activity_job`, `runtime.blender_process_running`, and `runtime.simulation_signal_source`.
      3. **Control-plane evidence** — dashboard `port_open` / `ping`, watcher freshness, `runtime_surfaces.running_count`, and whether the orchestrator daemon is alive.
      4. **Tier module quantity results** — report active-versus-total quantities, not active-only counts. In user-facing wording, refer to **groups of tiers** and **tiers**, not families. Include `tiers.runtime_module_counts.configured_family_count`, `configured_instance_count`, `active_family_count`, `active_instance_count`, `standby_instance_count`, `created_instance_count`, plus the active group ids and active tier ids when present.
      5. **Recent evidence window** — latest timestamps or mtimes from `TemporaryQueue/ai_brain_metrics_live.json`, `ActiveSpace`, `LongTermStore/Events`, or the freshest relevant runtime artifact.
      6. **Gaps / caveats** — say explicitly when the control plane is up but simulation evidence is absent, or when data is stale or missing.
    - Primary sources:
      - `TemporaryQueue/ops_status.json`
      - `TemporaryQueue/ai_brain_metrics_live.json`
      - recent artifact mtimes in `ActiveSpace`, `LongTermStore/Events`, and `TemporaryQueue`
    - State explicitly that `tiers.runtime_module_counts` is the **currently instrumented runtime-module surface**, not the total AI Brain tier population.
    - If relevant, separate that narrow runtime-module quantity from the broader AI Brain tier baseline (currently `20004` total tiers across the named groups), and do not collapse those two quantities into one claim.
    - Prefer wording such as `1 active tier out of 4 configured tiers` and `1 active group out of 2 configured groups` when totals are available.
    - Do not imply tier-module activity without quoting the quantity fields above.
    - If only watchdog/metrics are live but no recent simulation evidence exists, state that directly.
    - If data is missing or stale, state that directly and suggest running the ops status report or dashboard status.
    - When the user asks for a **percentage** of the AI Brain that is running, use `tiers.runtime_module_counts.active_instance_count / configured_instance_count` as the primary estimate, state the exact numerator and denominator, and say explicitly whether live simulation is currently happening.
    - When the user asks how many tiers **ought** to be active, do not answer from the runtime-module count alone. Use the active-versus-needed tier procedure in `ASSESSMENT_PROCEDURE.md` and distinguish the full AI Brain tier baseline from the narrower currently instrumented runtime-module surface.
    - When the user asks how many tiers **ought** to be active, do not answer from the runtime-module count alone. Use the procedure in `ASSESSMENT_PROCEDURE.md` for assessing active-versus-needed tiers, and distinguish the full AI Brain tier baseline from the narrower currently instrumented runtime-module surface.

1. **Don’t ask for permission for small/medium improvements.**
   - If an improvement is helpful and low-risk, add it to the active monthly task log (`orchestration/project_modifications_tasks/tasks_042026_1.md`) as a task and perform it.

2. **Always log work in the active monthly task file.**
   - Current file: `orchestration/project_modifications_tasks/tasks_042026_1.md` (April 2026).
   - Use the pattern `orchestration/project_modifications_tasks/tasks_MMYYYY_N.md` for the canonical monthly orchestrator log.
   - Older `temp_*.md` files, including `temp_Feb2026_1.md` and `temp_12.md`, are legacy archives and carry-over references only.
   - When you discover a helpful task, add it to the task list in the active file.
   - After implementing, record what changed, why, and how it was verified.
   - If a monthly file becomes unwieldy, start the next `tasks_MMYYYY_N.md` file and document the rotation in the current file before switching.

2a. **Child-agent ledgers (tabs).**
    - Child tabs must use their assigned JSON ledgers (proposal/completed/task files) per the orchestration package.
    - Do not write to the monthly task log from child tabs; only the orchestrator tab updates `orchestration/project_modifications_tasks/tasks_MMYYYY_N.md`.

2aa. **Sub-agent model choice must follow the user preference.**
    - When launching sub-agents or child-agent work that allows model selection, prefer GPT-family models and other real-world-info models only.
    - Do not choose Claude-family models for this repository unless the user explicitly reverses this preference.

2b. **Optional: use a dedicated task-list file for complex work.**
   - Keep the active monthly task file (for example `orchestration/project_modifications_tasks/tasks_042026_1.md`) as the primary audit log.
   - For multi-step work, create focused plan files beside it under `orchestration/project_modifications_tasks/` using names like `task_plan_<slug>_042026_1.md`.
   - Use the task list file to keep the plan readable (goals, steps, acceptance criteria). In the monthly log, note a short pointer to the task list and the final outcomes.
   - This is useful when a change spans multiple areas (e.g., dashboard + scripts + config) and you want a focused checklist without bloating the main log.

2c. **Terminology for git status checks.**
   - When summarizing git working tree state, avoid the word "clean" because it clashes with the destructive `git clean` command.
   - Prefer phrases like "no pending changes," "working tree empty," or "status clear" to describe an empty diff.

2d. **Terminology and grammar accuracy are mandatory.**
   - Do not introduce or normalize lingo, slang, invented labels, or inaccurate implementation terminology in code, docs, plans, ledgers, or user-facing status text.
   - Understand user shorthand privately when needed, but write the resulting repository language in clear, literal grammar.
   - The prohibited behavior is repeating, standardizing, or normalizing vague or inaccurate wording after the actual concept is already understood.
   - When a term does not match the real file ownership, task state, validation step, or artifact contract, replace it with direct domain-accurate wording before writing or revising artifacts.
   - Examples of wording to avoid as implementation terminology in this repo include `sidecar`, `recipe`, `hot-core`, `lane`, role-inaccurate labels, and similar wording when it does not literally describe the persisted artifact, file set, workflow, or actor responsibility being implemented.

2e. **Status and progress wording must be literal.**
    - Use clear grammar with direct subjects, verbs, and objects.
    - Do not use figures of speech, idioms, conversational shorthand, or compressed jargon in status updates, progress reports, assessments, implementation notes, or agent instructions.
    - Avoid figures of speech, idioms, or conversational shortcuts in status updates, progress reports, assessments, and implementation notes when they could blur meaning.
    - Prefer direct statements of the actual action or state, such as `I am running markdown diagnostics now` or `The markdown diagnostics reported no errors`.
    - Avoid ambiguous or ungrammatical phrases such as `close cleanly`, `button this up`, `tighten things up`, `invented labels`, role-inaccurate shorthand, or similar wording that leaves room for interpretation or weak grammar.
    - Prefer direct replacements such as `orchestrator work`, `orchestrator actions`, `wave reconciliation work`, or another literal phrase that states who is acting and what is being done.

2ea. **Direct answers and corrections must be explicit.**
    - When the user asks a comparative, capability, settings, or constraint question, answer the core question in the first sentence with the direct conclusion before adding supporting detail.
    - Distinguish documented facts from inference. State documented facts as facts. If a point is an inference from behavior or product structure rather than an explicit repository or product document statement, say that it is an inference.
    - When correcting an earlier answer, state the corrected answer directly and briefly. Do not add meta-commentary about persuasion, wording strategy, tone strategy, framing, spin, softening, or similar discussion about how the answer was presented.
    - Do not imply hidden product behavior, hidden filtering differences, or undocumented configuration effects as facts unless the repository evidence or the cited product documentation supports that claim directly.
    - For product comparisons such as Copilot CLI versus VS Code or direct API access, separate these dimensions literally: underlying model choice, available tools, permissions, context, repository instructions, and documented product constraints.

2eb. **Timezone handling must be explicit.**
    - Treat ISO 8601 timestamps with a trailing `Z` as UTC, not as local wall-clock time.
    - When the user asks what time something happened, how long ago it was, or whether one timestamp is before or after another, convert the UTC value to the relevant local time before answering if the user is reasoning in local time.
    - In user-facing answers and operator-facing status text, label timestamps as `UTC` or `local time` explicitly instead of leaving the timezone implicit.
    - Keep persisted artifact timestamps in their existing UTC form unless a file's contract explicitly says otherwise; this rule is about interpretation and presentation, not changing storage format.

2f. **Blocked queues must promote the unblocking frontier.**
    - Do not leave every child tab or every downstream packet marked blocked merely because later tasks depend on unfinished work.
    - When a queued or proposed task is blocked by a prerequisite, the orchestrator should identify the nearest materially-ready prerequisite or dependency-frontier packet and assign that packet actively instead of leaving the whole chain idle.
   - Prefer this order when deciding what to assign:
     1. the exact same-tab queued packet whose dependencies are already materially closed,
     2. the nearest unfinished prerequisite packet that would unblock one or more downstream queued packets,
     3. an evidence-only or planning-only gate packet that is the last missing prerequisite before implementation may continue.
   - Keep only the true downstream dependents queued behind that frontier packet. Do not describe the whole wave as blocked if a real unblocking packet can still be assigned.
   - Use bounded wait-and-recheck loops only when no materially-ready prerequisite frontier can yet be assigned and the next dependency closure is expected soon.

2g. **Known task-list sequences should continue automatically.**
   - When the next bounded task list is already known from the current evidence, do not pause only to ask the user for another message.
   - Record the task-list sequence in the relevant task-plan file or monthly log, then continue through the materially-ready lists automatically.
   - Move to the next known list after reconciling the current packet's artifacts, tests, and logs.
   - Only pause for user communication when a real ambiguity, permission boundary, safety boundary, or missing external input would materially change the next implementation choice.
   - Do not treat “user has not sent another message yet” as a blocker when the repository state already determines the next bounded packet.

2h. **Prefer multiple sub-agents or child tabs when applicable.**
   - When more than one materially-ready, non-overlapping packet exists, prefer using multiple child tabs or sub-agents in parallel instead of one-at-a-time execution.
   - Use this preference only when file ownership, restricted-file rules, and dependency ordering remain clear.
   - If a packet can be split into one write-side packet plus one or more read-side or evidence-side packets, prefer parallel fan-out so the orchestrator can reconcile faster.
   - Do not force parallelism when the packets overlap on the same files or when one packet's result materially determines the other's implementation.

3. **Backups / diffs for substantial changes.**
    - If a change is substantial (multi-file refactor, behavior change, or large edits):
       - Create a backup copy of the file(s) being changed (e.g., `filename.bak_YYYYMMDDTHHMMSSZ`).
   - Or record a clear “diff summary” in the active monthly log (currently `orchestration/project_modifications_tasks/tasks_042026_1.md`) detailing what functions/files changed and why.

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
- 3D measurement core is in `AI_Brain/` and should remain strictly layered.
- Storage must use safe path resolution (`sanitize_id`, `safe_join`, `resolve_path`) instead of absolute paths.
- Repository-level LSP configuration lives at `.github\lsp.json` and uses `.venv\Scripts\python.exe -m pylsp` for Python files in this workspace.
- Workspace map: VS Code agent mode can use [TemporaryQueue/filesystem_map.txt](TemporaryQueue/filesystem_map.txt); regenerate via `tools/fs_map.py --max-depth 4 --out TemporaryQueue/filesystem_map.txt` (defaults to temp path and safe joins).
- Deep research prompts should start from `public_mirror/Copilot_DeepResearch_Package_20260201/Prompts/deep_research_prompt_template.md` (copy + customize before publishing updates).

## Category Positioning (LLM vs. AI Brain)

- This repo is **not** an LLM. It is a deterministic, measurement‑first cognitive loop with file‑backed memory and auditable artifacts.
- When describing “smartness,” ground it in: explicit measurements, objective alignment, determinism, and traceable decision outputs.
- Avoid comparing with market LLMs by capability claims. Instead compare **method** (measurement‑first vs. probabilistic text inference) and **artifacts** (auditable traces vs. opaque outputs).
- Cite authoritative sources in this repo: `DESIGN_GOALS.md`, `README.md`, and the active monthly log (`orchestration/project_modifications_tasks/tasks_MMYYYY_N.md`).
- If preparing content for external AI reviewers, use the normalized response format in `Copilot_app_Attachments_txt_files_of_py_modules/exports/CopilotApp_AI_Guide.md`.

## Verification

- Prefer running the VS Code task “AI Brain: eval”.
- If a change affects determinism, also run the determinism suite or ensure it still passes in eval.

## Orchestrator Dependency-Frontier Rule

- When reviewing child-task ledgers, the orchestrator must distinguish between:
   - a **true frontier blocker**: a task that is itself assignable now and whose completion will unblock later queued work, and
   - a **downstream dependent**: a task that should stay queued behind that frontier blocker.
- If a task is reported as blocked, the orchestrator should ask: *what exact unfinished packet must complete before this task can run, and is that packet already materially assignable?*
- If the answer is yes, assign that prerequisite packet immediately instead of leaving both tabs idle.
- Only treat a branch as fully blocked when all of the following are true:
   - no same-tab queued packet has materially satisfied dependencies,
   - no prerequisite packet remains assignable on another tab without overlap violations,
   - and no evidence-only gate packet can be run to close the next dependency.
- In monthly-log summaries and task-ledger notes, describe blocker chains literally, for example: `243 waits on 242`, not `the whole wave is blocked` when `242` is the real assignable frontier.

## Assessment / Reporting

- Follow the runbook in `ASSESSMENT_PROCEDURE.md`.
- Write assessments and next-task recommendations into the active monthly log (currently `orchestration/project_modifications_tasks/tasks_042026_1.md`).

Practical example:
- If you need to generate metrics for visualization without overwriting run outputs, you can flush comparison metrics to `TemporaryQueue/metrics_compare.json` and point the dashboard at it (server mode). Track the steps in a focused plan file under `orchestration/project_modifications_tasks/`, and record the final verification (e.g., “AI Brain: eval PASS”) in the active monthly log (currently `orchestration/project_modifications_tasks/tasks_042026_1.md`).
