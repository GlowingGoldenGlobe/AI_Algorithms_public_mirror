# AI Brain (3D Measurement Core)

This folder is a new, dedicated **AI_Brain** workspace focused on 3D measurement and spatial reasoning. It bootstraps a minimal, runnable core and leaves clear extension points for the rest of the system.

## Quick Start (Windows PowerShell)

```powershell
cd path\to\AI_Algorithms\AI_Brain
.\.venv\Scripts\Activate.ps1
python brain_init.py
```

### FastAPI Server
```powershell
cd path\to\AI_Algorithms\AI_Brain
.\.venv\Scripts\Activate.ps1
python -m uvicorn interfaces.api_server:app --reload
```
Endpoints:
- `GET /health`
- `POST /measure` → `{ "points": [[x,y,z], ...] }`
- `POST /diagnostics` → returns measurement + validation

Expected output includes a small 3D measurement report for a synthetic point cloud, including AABB surface area and boundary stats.

### Estimated First Run
- Estimated first successful run: **2026-01-24T21:44:06Z** (from `brain_state.last_tick_ts`).
- Logged in [AI_Brain/logs/brain.log](AI_Brain/logs/brain.log).

### Project Creation
- Verified project creation: **2025-12-12T03:47:11** (from folder properties).
- Logged in [AI_Brain/logs/brain.log](AI_Brain/logs/brain.log).

### Blender Point‑Cloud Input
- In Blender: File → Export → **PLY** (set “Format” to **ASCII**) or **OBJ**.
- Keep only vertex positions (no need for UVs or normals for basic measurement).
- Set `measurement.point_cloud_path` in [brain_config.yaml](AI_Brain/brain_config.yaml).
- Supported formats: `.ply` (ASCII), `.obj` (vertex lines only). `.glb/.gltf` are currently not supported.

Example:
```yaml
measurement:
	point_cloud_path: "AI_Brain/sample_mesh.ply"
```

Blender file test:
```powershell
python -c "import sys, pathlib; sys.path.insert(0, str(pathlib.Path('AI_Brain').resolve())); from simulation.sim_measurement_tests import run_blender_sample; import json; print(json.dumps(run_blender_sample(r'C:/path/to/export.ply'), indent=2))"
```

## What’s Included

- Core bootstrapping: `brain_init.py`, `brain_config.yaml`, `brain_state.json`
- 3D measurement engine: minimal geometry, point cloud processing, AABB volume + surface area
- Perception/memory/reasoning/learning scaffolds with clean extension points
- Diagnostics hooks and a lightweight simulation stub
- Spatial memory persistence to `memory/spatial_memory.json`

Legacy durable-memory contract:
- `brain_state.json` stores the latest summarized measurement state.
- `memory/spatial_memory.json` stores the durable spatial-memory artifact for the same legacy run path.
- Relative `paths.memory_dir` config values are resolved from the `AI_Brain` directory, so running `python AI_Brain/brain_init.py` from the repo root still writes to `AI_Brain/memory/spatial_memory.json` rather than a repo-root `memory/` folder.

## Positioning vs. LLMs (Category Difference)

This 3D core is **not** a language model. It is a deterministic measurement engine that produces **auditable spatial metrics** (centroid, bounds, AABB area/volume, boundary stats) for structured reasoning and memory.

Unlike LLMs (e.g., GPT/Claude/Grok/DeepSeek), which infer next tokens probabilistically, this core:
- Operates on **explicit geometry** (points/meshes), not text patterns.
- Produces **structured measurements** that can be inspected and replayed.
- Is designed to attach to a broader **measurement-first relational pipeline** (root workspace) rather than replace it.

## Adherence to the Intended Difference (Current State)

- **Strongly aligned:** deterministic measurement, auditable outputs, and file-backed spatial memory.
- **Intentionally limited:** reasoning/planning layers are scaffolds; higher-level “thinking” happens in the root pipeline.
- **Integration path:** measurements are attached to `relational_state` via the root bridge/adapter, keeping the system measurement-first rather than pattern-first.

## Terminology Accuracy

The AI Brain should use domain-accurate terminology for persisted artifacts, measurement outputs, reasoning summaries, and implementation-facing documentation.

- Assessment and comprehension should include understanding figures of speech, user shorthand, or informal lingo when that is necessary to interpret intent correctly.
- It is not acceptable to deliberately repeat, implement, normalize, or preserve inaccurate terminology in AI Brain outputs, plans, or docs after that assessment has already been made.
- When an older or informal label is inaccurate for the actual concept, replace it with terminology that matches the real measured or stored concept.
- Examples of inaccurate vocabulary to avoid as implementation terminology include `sidecar` and `recipe` when those words do not accurately describe the actual AI Brain artifact or contract.

## Comprehension Progression

The AI Brain builds comprehension through staged, auditable actions. Each stage produces artifacts that can be inspected and re-run deterministically:

Interpreting user intent is part of that progression. Understanding shorthand, lingo, or figures of speech can be necessary for correct assessment, but the resulting stored or emitted terminology should still be literal and domain-accurate.

1. **Signal intake:** capture raw measurements (point clouds, bounds, centroid) from the measurement engine.
2. **Structuring:** normalize and summarize measurements into stable, structured outputs (AABB, boundary stats).
3. **Validation:** verify deterministic recomputation and check for mismatches or drift across cycles.
4. **Retention:** persist validated artifacts to spatial memory for later comparison and retrieval.

Evidence for each stage should be present in measurement outputs, diagnostics responses, and stored memory files.

Re-composed description (author intent): the AI Brain can expose optional parameter instances that mirror existing module behaviors, running in parallel or in sequence and reacting to the primary parameter stream when those behaviors are learnable and describable. This adds multi-location comprehension, where the main context and scheduled memory remain the primary locus of understanding while the mirrored parameter options provide an additional interpretive layer that observes, reacts, and describes the same processed information.

## Upgrade Highlights

- **3D measurement pipeline** with centroid, bounds, AABB surface area, and volume estimate
- **Safe configuration loading** with fallbacks
- **Dynamic loader** that can safely load files with numeric prefixes (e.g., `3d_*`)
- **Blender point‑cloud ingestion** for ASCII PLY/OBJ

## Next Steps

- Implement real sensor adapters in `perception/`
- Use Blender as the primary 3D tool for mesh and point‑cloud generation
- Treat Open3D as optional unless Blender is insufficient for a specific task
- Extend `memory/` with voxel or TSDF maps
- Add FastAPI endpoints in `interfaces/` once dependencies are installed
