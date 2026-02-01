# AI_Brain Architecture (3D Measurement Core)

This folder is a dedicated **3D measurement core**. It is designed to be deterministic, auditable, and easy to extend.

The root workspace (one level up) contains the broader “AI Brain” cycle system (storage/measurement/scheduling/toggling) and can optionally attach 3D measurements into each record’s `relational_state`.

## Layered modules

- **measurement_engine/**: geometry + point cloud processing + deterministic AABB metrics; ingestion for ASCII `.ply` and simple `.obj`.
- **perception/**: sensor adapters and fusion scaffolding.
- **memory/**: spatial memory persistence (e.g., `memory/spatial_memory.json`).
- **reasoning/**: spatial relations / prediction / planning scaffolding (deterministic-first).
- **learning/**: representation/update scaffolding.
- **interfaces/**: FastAPI scaffold (see [AI_Brain/README.md](README.md) for endpoints and usage).

## Data flow (3D)

1. **Input**: a synthetic point cloud, or a configured `.ply/.obj` file.
2. **Measure**: compute centroid, bounds (AABB), volume/surface-area estimates, and boundary stats.
3. **Validate**: shape/measurement sanity checks (diagnostics endpoint supports returning validation).
4. **Persist**: spatial memory snapshot under `AI_Brain/memory/`.

## Integration into the root pipeline

The root workspace can attach 3D measurements into its canonical `relational_state` representation.

- Bridge: `module_ai_brain_bridge.py` (root)
- Adapter: `module_relational_adapter.py` (root)
- Orchestrator call site: `module_integration.RelationalMeasurement()` (root) runs the adapter in a guarded way when a spatial asset is present.

Attached structure (root record):
- `relational_state.entities` / `relational_state.relations` / `relational_state.constraints`
- `relational_state.spatial_measurement` (raw measurement payload, when available)

## Determinism

The 3D measurement core is intended to be deterministic for the same inputs. The root workspace has an explicit determinism mode (fixed timestamps) that is eval-gated.

## Positioning vs. LLMs (Category Difference)

This subsystem is **not** an LLM and does not perform probabilistic language inference. It is a deterministic, measurement-first engine for **spatial data**, producing auditable metrics that can be replayed and attached to the root pipeline’s `relational_state`.

Key differences from market LLMs (GPT/Claude/Grok/DeepSeek):
- **Inputs:** geometric point clouds/meshes instead of text prompts.
- **Outputs:** structured measurement payloads, not generated text.
- **Determinism:** repeatable measurement for identical inputs.
- **Role:** a measurement provider that feeds a broader rational pipeline, not a general-purpose language model.

## Adherence Notes (Current State)

- Measurement, validation, and persistence are fully aligned with the stated non‑LLM category.
- Reasoning/planning modules remain scaffolding; they are intentionally limited and will mature in the root pipeline’s orchestration.
