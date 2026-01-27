Composed: 2026-01-26
Authors: VS Code Agent (GitHub Copilot, GPT-5.2) + Richard I. Craddock

# temp_24.md — Assessment of temp_[n] upgrade progression (what progressed, what’s pending)

## Purpose
Scan the progressive `temp_[n].md` files as an upgrade trail, reconcile them against the repo’s current “Implemented Today” reality (README + `temp_12.md` log), and produce:
- a prioritized tasks list,
- a re-composition proposal (how to consolidate/normalize the project narrative),
- attention points (gaps, drift, and likely next upgrades).

## Inventory of the temp trail (quick map)
This is not exhaustive of every line; it’s the main “what each temp file was trying to do” so the trail is usable.

- `temp_2.md` — early pipeline next-steps: continuous loop, objectives drive behavior, activity tracking.
- `temp_3.md` — missing pieces list: procedural matching, search expansion, post-processing actions.
- `temp_4.md` — early integration sketch (contains hard-coded absolute paths; later corrected in repo).
- `temp_5.md` — big phased plan (collector/concurrency, config integration, observability, IQ tests).
- `temp_6..md` — Phase A–F follow-up plan (deepen objectives, self, external search, multi-window, IQ tests). **Filename typo**: `temp_6..md`.
- `temp_7.md` — safety/infra checklist: schemas, atomic writes, path safety, bootstrap, indexing.
- `temp_8.md` — “description-first cognition” target: cycle orchestrator, `cycle_record`, arbiter, described-info layer, richer repeat/measure outputs.
- `temp_9.md` — policy tuning + CLI snapshot / tasks / determinism notes.
- `temp_10.md` — short status update on policy eval + observability.
- `temp_11.md` — AI_Brain (3D) subproject upgrades (point-cloud ingestion, measurements, spatial memory, FastAPI scaffold).
- `temp_13.md` — workability check + determinism/path safety reconciliation (mostly “already implemented”).
- `temp_14.md` — user’s message to external Copilot app; sets the “branches/packages + outperform LLM reasoning” framing.
- `temp_15.md` — evidence-based assessment: current loop exists; ML frameworks not integrated; key gap = canonical relational state + objective-centric focus/retrieval.
- `temp_16.md` — synthesized response emphasizing canonical relational state + objective-centric focus as next core work.
- `temp_17.md` — re-composed README draft (design-goals heavy; later split into README + DESIGN_GOALS in repo).
- `temp_18.md` — architecture doctrine: modules as brain activities; measurement-first; deterministic cycles; relational state as universal substrate.
- `temp_19.md` — concrete transformation task list to align code with architecture (phased migration).
- `temp_20.md` — meta: “architect role” (specs, golden examples, audits).
- `temp_22.md` — “upgraded activity list” emphasizing measurement/error/want/retrieval as primary loop.
- `temp_23.md` / `temp_23_v2.md` — “new chat continuity” templates (handoff checklist for future sessions).

## What progressed well (observed trajectory)
The strongest trend is that the repo moved from “plans and stubs” → “eval-gated, deterministic, file-based pipeline” with measurable artifacts.

Key progress themes that appear repeatedly across the temp files and now exist in the repo:

- Determinism-first workflow with explicit reporting and CLI controls.
- Storage hardening (atomic writes, safe paths, schema validation) matching `temp_7.md`.
- A coherent end-to-end cycle exists (store → measure → decide/toggle → schedule → log) and is documented in README.
- A dedicated adversarial harness exists (S1–S6) with deterministic reproduction and report artifacts.
- Measurement is becoming more explicit and structured (measurement reports, weights, decisive recommendations).
- Early “hard-coded absolute path” patterns noted in older temps were later removed (per repo docs/logs).

## What appears implemented today (confirmed via docs/logs)
This section is the “current reality snapshot” implied by README + `temp_12.md`.

- Eval harness and deterministic suite exist and are used as a gate.
- Path safety helpers (`sanitize_id`, `safe_join`, `resolve_path`) are in active use.
- Schema validation and atomic writes exist for persisted JSON records.
- Policy tooling exists (policy show/eval/set/tune; activation-rate reporting).
- Snapshot export + housekeeping (GC) exist.
- Collector exists with observability improvements (resource summaries, allowlists, merged outputs).
- Adversarial harness exists with deterministic reproduction and report/bundle tools.
- “Think-deeper” reasoning artifacts exist (distribution + counterfactuals + justification artifacts) with eval gates.
- Conceptual measurement engine exists behind config gating (`measurement_migration`), and Want scaffolding exists behind gating (`want_migration`) per `temp_12.md`.

## Gaps / items likely needing attention (compared to the target architecture)
These are the recurring “next missing pieces” implied by the temp trail (esp. `temp_8.md`, `temp_15.md`, `temp_18.md`, `temp_19.md`).

1) Canonical relational state unification (text/context + 3D)
- The repo has a relational_state concept and a 3D measurement engine, but the temp trail repeatedly identifies the missing step as a single canonical state representation shared across:
  - semantic records,
  - objective links,
  - 3D measurement outputs,
  - reasoning constraints and decision traces.

2) Objective-centric memory: focus/concentration is not yet fully operational
- The temp trail consistently calls for objective-driven:
  - storage (what to keep and how),
  - retrieval (what to pull next),
  - scheduling (what to revisit).
- Current behavior appears more “objective-influenced signals” than “objective-centric indexing + retrieval + scheduling.”

3) “Description-first cognition” layer (Phase 7–9 in `temp_8.md`)
- `temp_8.md` wants a structured `description` object (entities/claims/constraints/questions/action_candidates) as the primary cognition substrate.
- The repo has moved toward richer measurement artifacts, but the described-info layer is not clearly established as the universal unit across modules.

4) Cycle record + arbiter as first-class persisted artifact
- Some of this exists (decision traces, activity logs), but `temp_8.md` emphasizes:
  - a single `cycle_record` per run,
  - arbiter rationale for conflict resolution,
  - an “atomic commit” rule (apply moves/schedules only after arbiter finalizes).

5) ActivityQueue as real scheduler of multi-activity work
- The directory `ActivityQueue/` exists (from `temp_12.md`), but the temp trail’s “multi-activity manager” vision needs a clear, deterministic queue contract:
  - task schema,
  - priority semantics,
  - retry/escalation rules,
  - integration into `RelationalMeasurement()`.

6) AI_Brain (3D) subsystem integration closure
- `temp_11.md` shows rapid evolution on the 3D side (ingestion, memory, FastAPI scaffold).
- The integration gap remains: how the root pipeline discovers/uses 3D assets and attaches them into the same relational_state and decision_trace.

## Repo hygiene / narrative recomposition opportunities
These are low-risk improvements that make the upgrade trail easier to use.

- Normalize the temp file naming:
  - Rename `temp_6..md` → `temp_6.md` (or archive it) to avoid tooling/path confusion.
- Establish a clear “canonical log vs archive” rule:
  - `temp_12.md` is already the canonical task log; older `temp_[n]` files can be treated as historical snapshots.
- Consider adding a lightweight index file (no refactor required), e.g. `TEMP_TRAIL_INDEX.md`, listing:
  - the key temp files,
  - what decisions they introduced,
  - which are superseded by current code.

## Prioritized tasks list (recommended)
This is a practical ordering that aligns to the temp trail’s intent and preserves the repo’s eval-gated style.

### P0 — Consistency + narrative control (small, high leverage)
- Update/replace older temp artifacts that conflict with current reality (e.g., those that assume modules exist with APIs that differ).
- Normalize the temp naming (`temp_6..md`) and optionally add an index doc.

### P1 — Canonical relational state boundary decision
- Decide: relational_state embedded in `LongTermStore/Semantic/<id>.json` vs sibling file.
- Create/lock a minimal schema that both text measurement and 3D measurement can populate.

### P2 — Objective-centric focus + objective_links
- Make focus/concentration operational:
  - focus_state influences retrieval selection, storage enrichment, and scheduling.
  - objective_links become measurable, not just labels.

### P3 — Description-first cognition (Phase 7)
- Implement a deterministic `describe()` representation and store it alongside semantic content.
- Ensure repeat/refinement updates the description and drives scheduling.

### P4 — Activity manager + queue contracts
- Define a durable ActivityQueue record schema and an execution loop.
- Integrate it into the cycle orchestrator in a non-breaking, gated way.

### P5 — 3D integration closure
- Add a clear contract for attaching 3D measurement outputs into the canonical relational state.
- Add an eval gate for “semantic + 3D unify” on a tiny synthetic asset.

## Suggested verification (keep the repo’s discipline)
- Use the existing VS Code task “AI Brain: eval”.
- For any determinism-impacting change, also check `cli.py status` determinism summary.

---
End of assessment.
