# AI_Brain — Next Tasks (Action List)

This list is the immediate, actionable follow‑up to the current AI_Brain state.

## 1) Blender‑First Ingestion
- Add a Blender export pipeline (PLY/OBJ/GLB) and a loader in [measurement_engine/3d_pointcloud_processor.py](AI_Brain/measurement_engine/3d_pointcloud_processor.py).
- Document how to generate sample point clouds from Blender in [README.md](AI_Brain/README.md).

## 2) Measurement Expansion
- Add surface area estimation and boundary statistics in [measurement_engine/3d_measurement_core.py](AI_Brain/measurement_engine/3d_measurement_core.py).
- Add unit conversion coverage in [measurement_engine/unit_conversion.py](AI_Brain/measurement_engine/unit_conversion.py).

## 3) Perception Fusion
- Implement a simple Kalman filter in [perception/sensor_fusion.py](AI_Brain/perception/sensor_fusion.py).
- Connect perception output into memory via [brain_memory_router.py](AI_Brain/brain_memory_router.py).

## 4) Spatial Memory Persistence
- Store point clouds and measurements to disk in [memory/spatial_memory_map.py](AI_Brain/memory/spatial_memory_map.py).
- Add trimming policies via [memory/memory_gc.py](AI_Brain/memory/memory_gc.py).

## 5) Diagnostics + Tests
- Add validation rules in [diagnostics/measurement_validation.py](AI_Brain/diagnostics/measurement_validation.py).
- Extend smoke tests in [simulation/sim_measurement_tests.py](AI_Brain/simulation/sim_measurement_tests.py).

## 6) Optional Open3D Integration
- Only add Open3D if Blender is insufficient for a specific measurement task.
