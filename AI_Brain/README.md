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
