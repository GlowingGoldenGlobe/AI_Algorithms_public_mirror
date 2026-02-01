# temp_deep_research_prompt_algorithms.md — Algorithmic Deep Research Brief

Date: 2026-02-01

## Context Summary

- Project: AI_Algorithms (“AI Brain”) — deterministic, measurement-first system with relational reasoning instead of probabilistic LLM outputs.
- Focus category: AI Brain algorithms; smart; unique methodology (relational measurement, objective reality logic, rational judgment, objective seeking).
- Determinism: enabled with fixed timestamp 2025-01-01T00:00:00Z.
- Latest verification: `python scripts/hardware_limits_check.py` + `python run_eval.py` (PASS) on 2026-02-01 while orchestrator paused.
- Artifact bundle: public_mirror/Copilot_DeepResearch_Package_20260201_Algorithms/ contains curated docs, modules, and results.

## Key Characteristics to Preserve

1. **Relational Measurement** — Structured metrics recorded into `relational_state`, deterministic scoring (module_measure.py, module_concept_measure.py).
2. **Objective Reality Logic** — Decision traces, provenance, and constraint validation (module_provenance.py, RESULTS_PathSafety.md).
3. **Rational Judgment** — Toggle policy, scheduler, `module_reasoning.py` reason chains, `module_want.py` signals.
4. **Objective Seeking** — Objective library + measurements (module_objectives.py, module_select.py).
5. **Deterministic Auditability** — Determinism suite, uncertainty structuring, reproducible eval harness.

## Research Goals

- Identify algorithmic upgrades or repairs that improve reliability while respecting the above characteristics.
- Explore ways to enhance relational measurement depth (compositional metrics, constraint solving) without switching to probabilistic models.
- Suggest mechanisms to strengthen objective-seeking loops (e.g., adaptive planning, reason-chain validation) that remain deterministic.
- Recommend rational-judgment improvements (toggle thresholds, uncertainty handling, conflict resolution) grounded in objective logic.
- Highlight tooling or frameworks that support deterministic reasoning (graph analytics, constraint solvers) appropriate for Windows PowerShell workflow.

## Desired Deliverables

1. Ranked proposal list focusing on algorithmic enhancements (top 5). Each proposal must include:
   - Summary of the idea and how it aligns with the unique methodology.
   - Files/modules to modify (reference items in the attached package).
   - Risk assessment (determinism, complexity, verification cost).
   - Verification plan (commands/tasks, new tests, metrics to monitor).
2. References or prior art supporting deterministic relational reasoning, objective-driven planning, or measurement-first AI.
3. PASS/FAIL checklist covering:
   - Preconditions (e.g., orchestrator paused, determinism on).
   - Implementation steps.
   - Required verification (eval harness, targeted tests, documentation updates).
4. Optional: suggestions for additional artifacts we should collect to aid future algorithmic research (e.g., decision trace metrics, objective fulfillment reports).

## Files to Attach with Prompt

- public_mirror/Copilot_DeepResearch_Package_20260201_Algorithms/README.md
- Docs: README.md, DESIGN_GOALS.md
- Modules: module_measure.py, module_concept_measure.py, module_reasoning.py, module_objectives.py, module_toggle.py, module_want.py, module_select.py, module_scheduler.py, module_metrics.py, module_provenance.py, module_uncertainty.py, module_integration.py
- Results: RESULTS_Phase15_ReasonChains.md, RESULTS_Phase16_ProceduralMemory.md, RESULTS_Phase11_EvidenceCapture.md, RESULTS_PathSafety.md
- temp_deep_research_prompt_algorithms.md (this brief)
- temp_Feb2026_1.md (current log, optional if more context useful)

## Reminders for External Review

- Maintain single-writer discipline (pause orchestrator before changes/tests; resume afterward).
- Use path safety helpers (`sanitize_id`, `safe_join`, `resolve_path`).
- Prefer deterministic libraries or configurable deterministic modes when suggesting new tooling.
- Tailor instructions for Windows PowerShell environment.
