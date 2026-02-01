# Design Goals — AI Brain (Target Architecture)

This document is the authoritative **target architecture** for the AI Brain system in this repo.

It intentionally contains design constraints that may not be fully implemented yet. The root [README.md](README.md) describes **implemented behavior**.

## Non-negotiables

- **Determinism first:** when determinism is enabled, the system must be reproducible and eval-gated.
- **Measurement-first cognition:** the system should prefer explicit, recorded measurements over implicit pattern association.
- **File-system grounded memory:** records persist as inspectable files (JSON) with atomic writes and auditability.
- **Relational substrate:** `relational_state` is the universal measured representation for both semantic and 3D inputs.
- **No “LLM brain”:** LLMs/search (if enabled) are optional tools, not the core reasoning mechanism.

## Intelligence loop (target)

The target loop is:

measure → record → repeat → modify → measure → compare → record → categorize → repeat

plus scheduling and multiple concurrent *activities* (even if executed sequentially).

## Modules as brain activities (target mapping)

- **Store Information:** persist record, occurrence_count, timestamps, repetition_profile, relational_state skeleton.
- **Repeat Information:** re-observe stored items and update recurrence/stability measurements.
- **Measure Information:** compute measurable signals (recurrence, constraint satisfaction, objective scores, etc.) and produce a report.
- **Want Awareness / Want Information:** trigger information-seeking and schedule evidence/measurement tasks when gaps/contradictions exist.
- **Select Information:** choose what to process based on measurable relevance to objectives.
- **Toggle Information:** move items between TemporaryQueue/ActiveSpace/HoldingSpace/DiscardSpace based on deterministic policy.
- **Schedule Information:** label and schedule future activities (review, synthesis, contradiction resolution).
- **Integrate and Log:** persist decision traces and cycle activity logs.

## Measurement over pattern matching (migration note)

Some current implementations use deterministic token/keyword heuristics (e.g., similarity and usefulness). Those are considered **transitional**.

Target direction:
- Replace token similarity with measurement-based metrics (recurrence similarity, constraint satisfaction, objective link scoring, structural similarity over relational_state).
- Replace keyword usefulness/objective alignment with objective_links scoring + measured evidence.

## 3D measurement as template

3D measurement is the canonical reference for “understanding”:
- load a 3D object (point cloud/mesh)
- measure centroid/bounds/volume/extents
- record measurements as structured data
- attach to relational_state (entities/relations/constraints/spatial_measurement)

All other modalities (semantic/procedural) should be treated analogously: measurable structures first, not vague pattern association.
