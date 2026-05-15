# AI_Brain Architecture (3D Measurement Core)

This folder is a dedicated **3D measurement core**. It is designed to be deterministic, auditable, and easy to extend.

The root workspace (one level up) contains the broader “AI Brain” cycle system (storage/measurement/scheduling/toggling) and can optionally attach 3D measurements into each record’s `relational_state`.
## Canonical 3D Measurement Schema

All 3D measurement outputs from the AI_Brain measurement engine **must** conform to the **3D Measurement Schema v1.0** defined in `specs/3d_measurement_schema_v1.yaml` (root workspace).

**Key fields:**
- `version`: Schema version (e.g., "1.0")
- `space_id`: Unique identifier for the 3D space/scenario
- `timestamp`: ISO 8601 UTC timestamp of measurement
- `entities`: List of detected entities with id, type, pose (x,y,z,quaternion), and bounding box
- `constraints`: List of spatial constraints (collision, distance, orientation, etc.)
- `metrics`: Performance and quality (latency_ms, success, seed, point_count, format)
- `source`: Always "3d" for 3D measurements
- `metadata`: Optional extended metadata

**Validation:** The bridge module (`module_ai_brain_bridge.py`, root) provides `validate_3d_measurement_schema()` function that raises `SchemaError` on schema violations.

**Example:**
```json
{
  "version": "1.0",
  "space_id": "space_scenario_001",
  "timestamp": "2025-01-01T00:00:00Z",
  "entities": [
    {
      "id": "entity_001",
      "type": "obstacle",
      "pose": { "x": 10.5, "y": 20.3, "z": 5.0, "quat": [0.0, 0.0, 0.7071, 0.7071] },
      "bbox": { "min": [10.0, 19.5, 4.5], "max": [11.0, 21.0, 5.5] }
    }
  ],
  "constraints": [
    { "type": "collision", "params": { "entities": ["entity_001", "entity_002"], "separation": 15.0 } }
  ],
  "metrics": { "latency_ms": 125, "success": true, "seed": 42, "point_count": 25000, "format": "ply" },
  "source": "3d",
  "metadata": { "mission_id": "mission_123", "operator": "ai_brain_bridge" }
}
```
## Layered modules

## Author Assessment Direction

The following author quote is recorded here because this file defines the AI Brain module system functionalities and their layered responsibilities:

> "Assess the modules of the AI Brain main functionalities tier about referencing memory; scheduling new memory to be referenced; assessing 3D relational measurement in the AI Brain main functionalities where it puts things to observe and assess them the same place as where it puts the main things of said referencing memory. The synthesis of information. The comparisons of similar (matching of information) information. These are methods of thinking which need to be reviewed, assessed, researched, developed, upgraded, improved, tuned - where functions must be composed where needed; where new modules must be integrated where needed in order to compose the main thinking system observation and synthesis and scheduling and remembering actions of the AI Brain."

Richard Isaac Craddock; 251-298-9158; craddock338@gmail.com; yerbro@gmail.com; 207 Hillcrest Rd Apt 133, Mobile, AL 36608; 2026-02-08

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

### Cache + Cost Controls (root integration)

The root bridge (`module_ai_brain_bridge.py`) now provides deterministic caching and rate limiting helpers:

- `get_3d_limits(config=None)`: reads `config.json > 3d_limits` and normalises `3d_max_calls_per_cycle`, `3d_cache_ttl_seconds`, `3d_cache_max_entries`, and `3d_max_latency_ms` (defaults to zero when unset).
- `peek_cached_measurement(...)`, `get_3d_cache()`, `get_cache_stats()`, and `clear_3d_cache()` allow operators to inspect or reset the in-process cache (default cap 64 entries, configurable via `3d_cache_max_entries`, TTL-enforced per config).
- `measure_ai_brain()` tags results with `cache_hit` and warns when measured latency exceeds the configured maximum.

The relational adapter (`module_relational_adapter.py`) enforces per-cycle limits while remaining cache-aware:

- Tracks 3D calls by `cycle_id` (with a 15-minute stale window) and skips new engine work once `3d_max_calls_per_cycle` is reached, returning `status="skipped"` with `reason="3d_call_limit_reached"`.
- Avoids consuming the per-cycle budget when a cached measurement is available, keeping deterministic behaviour intact.
- Injects the raw measurement into `relational_state.spatial_measurement` for traceability even when the measurement reports `ok=False`.

**Metrics:** The bridge records `3d_calls_total`, `3d_failures_total`, `3d_latency_ms_total`, `3d_cache_hits_total`, and `3d_cache_misses_total`. The `run_eval.py --with-3d` flag prints these counters in the `3d_measurement_validation` block.

**Runtime throughput note:** the root pipeline only invokes the guarded measurement path when a spatial asset is available. In live operation, the durable cadence surface is `LongTermStore/Telemetry/SpatialMeasurements/events.jsonl`, which records both `completed` and `skipped` attempts. A high share of `reason="no_spatial_asset_path"` should be interpreted as an asset-availability limit, not automatically as a tier-capacity limit or Blender-engine failure.

**Continuous-run and cycle-preparation-lag note:** continuous AI Brain activity is not only the narrow moment when Blender is visibly simulating. The real cycle also includes bounded preparation-lag windows where the system is still doing useful work such as asset checks, routing, validation, measurement-handoff preparation, persistence, scheduler follow-through, and later replay/synthesis setup. Those preparation windows should not be mislabeled as a whole-brain pause, but they also should not be overstated as live simulation when no current simulation/measurement commit is occurring. The intended architecture is therefore two-part: report true live simulation/measurement windows honestly, and represent preparation-lag behavior through bounded switches such as **review-only, hold/defer, reject, mirror, schedule follow-up, and later role-switch** so the runtime can keep churning productively without pretending every cycle phase is the same kind of activity.

**Blender runtime note:** the repo includes optional `blender_composition` configuration, the bounded deterministic receiver entrypoint at `scripts/blender_composition_receiver.py`, and now also the live Blender runtime shim `scripts/blender_live_runtime.py`. When `blender_composition.enabled` is true, the receiver can validate starter requests, reject malformed payloads deterministically, launch a real Blender-backed export path, emit deterministic request/response/runtime-artifact bundles under `TemporaryQueue/blender_composition`, and optionally trigger the existing `attach_composition_bridge_outputs()` plus `attach_spatial_relational_state()` sequence for a supplied semantic record. The correct architecture is layered: keep the request/response/recipe/manifest/validation artifacts as the deterministic control and lineage surface, and prefer the emitted Blender export as the geometry/reference target when present rather than replacing the whole scaffold layer. Blender bridge capacity is now its own runtime surface (`blender_composition.max_concurrent_live_jobs`, `blender_composition.request_backlog`, plus `--serve` multi-request receiver mode), and must not be inferred from `3d_max_calls_per_cycle` or from the tier-inventory chart. The recommended scaling pattern is a **few simultaneous Blender scenes with rotating object-slot occupancy**: completed extrapolation outputs persist into the repo’s normal storage/bridge/scheduler surfaces, then the finished object leaves the live scene so its slot can be reused by the next mapped tier or tier-part object. The control axes must stay separate during tuning: **scene quantity**, **objects per scene**, **replacement quantity over a cycle or duration**, and **other bounded factors** such as slot caps, backlog, bridge/storage pressure, soak duration, and asset coverage.

**Operator control note:** the Blender-backed 3D path does **not** make the start daemon part of the AI Brain. The start daemon/orchestrator is an external way to start, pause, resume, inspect, or stop the AI Brain process surfaces; it is not itself an AI Brain tier part or AI Brain module. Use the same orchestrator/dashboard controls documented in `ORCHESTRATOR_QUICKSTART.md` and the root `README.md`: start with **AI Brain: orchestrator (detached start)**, pause with **AI Brain: orchestrator pause**, resume with **AI Brain: orchestrator resume**, inspect with **AI Brain: orchestrator status**, and use **AI Brain: all stop (safe: pause orch + stop dashboard suite)** when you want the bounded full stop path. If the dashboard suite is part of the run, restart it before resume. Also keep the runtime semantics straight: `runtime.running=true` should mean active simulation/measurement work is occurring, while control-plane/daemon liveness alone is not sufficient.

**Top-tier 3D software ownership note:** the intended AI Brain-native architecture keeps the external start daemon/orchestrator separate from one integrated top-tier AI Brain module for Blender-backed 3D software runtime. The start daemon/orchestrator is only the way to start/control AI Brain process surfaces; it is not the Blender runtime owner. The integrated top-tier AI Brain module owns both responsibilities together: it starts Blender, interacts with Blender for 3D simulation and measurement work, reads a JSON registry of required software, detects whether each specified software runtime is currently running, and commits an alert artifact when required software is not running.

**Blender capacity note:** the operator-facing repeatable capacity surface is now `scripts/blender_capacity_benchmark.py`. It benchmarks configured live concurrency levels and one-scene object-count levels against the actual receiver/runtime path, persists latest/history JSON artifacts, and records the effective pool settings plus a compact hardware snapshot. It now also aggregates slot-turnover metrics from the receiver’s live claim/release lifecycle, including release count, reuse cycles, release rate, and average slot turnaround time, so the Stage 6 rotating-scene procedure has a direct measured surface for extrapolation-plus-replacement rate. The latest live benchmark on the current desktop machine completed `1`, `4`, `8`, `16`, `32`, `40`, and **`48`** concurrent Blender jobs successfully for the current simple export workload, so the present configured Blender-bridge software cap is now materially validated on this hardware through **`48` simultaneous live jobs**. At the widened point, the `48`-slot run completed `48/48` jobs with `slot_release_rate_hz=30.2133`, `avg_slot_turnaround_sec=1.2544`, and `unique_slots_used=48`. The widening ladder has still also been exercised above the earlier `32`-slot cap: `64` concurrent requests over the `32`-slot pool completed with `slot_reuse_cycles=32`, `128` concurrent requests over the same pool completed with `slot_reuse_cycles=96`, and `256` concurrent requests over the same pool now complete with `slot_reuse_cycles=224` and `slot_release_rate_hz=25.952`. That grounds the claim that the rotating-slot model is now doing real measured reuse across multiple turnover waves rather than only single-pass slot occupancy. The `256` packet also exposed and closed a Windows-side controller race: `_claim_live_slot()` now retries transient `PermissionError` events during slot-file creation instead of failing the whole packet. The same benchmark also grounded the current one-scene object scale more tightly under the configured `startup_timeout_sec=30`: `10`, `100`, `1000`, `1200`, `1350`, and `1400` requested objects completed, while `1450`, `1500`, `2000`, and `10000` all timed out at that same gate. The follow-on Stage 6 soak review then re-ran the widened tuple and confirmed that the **`48`-slot / `1400`-object / `30s` timeout** baseline remains stable with `48/48` completion, `slot_release_rate_hz=29.0258`, `avg_slot_turnaround_sec=1.259`, and about `3.4s` of remaining time before the `1400`-object checkpoint hits the launcher timeout. That means the current default runtime is now validated through a **`48`-slot live pool** and **`1400` objects in one scene**, and larger-scene claims still require either different timeout/runtime settings or a separate optimized scene-building path before they should be treated as landed capacity.

**Stage 7 workload-mapping note:** the validated `48`-slot / `1400`-object / `30s` tuple is a bounded runtime envelope, not the allocator for which AI Brain work should receive 3D execution. The next gating surfaces are still `scripts/spatial_asset_coverage_report.py` plus scheduler/composition routing, because the repo remains asset-limited on the broader frontier. New 3D workload should therefore map onto the existing real carriers documented in `docs/AI_BRAIN_TIERS.md`—`tier1_main_cognition`, `active_space_support`, `reference_grounding_support`, `retained_memory_support`, `spatial_context_relation_support`, and `correctness_constraint_verification_support`—rather than opening a new Blender-dedicated family. `schedule_mirror` remains the sole serving family, `simultaneous_context_match` remains non-serving, and the current Stage 7 sufficiency review keeps later mass-tier or new-family steps closed: `TemporaryQueue\scheduler_composition_routing_latest.json` currently shows **82** scanned records with **0** routed records / **0** routed requests, while `TemporaryQueue\composition_workflow_chart_latest.json` shows **0** observed mapped slices and **0** observed real groups. Reopen that question only after those artifacts show non-zero explicit routed workload through named existing carriers and later bounded evidence shows those carriers are materially insufficient.

**Operator chart note:** the operator-facing chart/module for this 3D-upgrade wave is `scripts/composition_workflow_chart_report.py`. It now composes runtime-effectiveness, spatial-asset-coverage, runtime-pilot, bounded scheduler-routing evidence, ops-status, config, and rollout-baseline surfaces into one chart payload under `TemporaryQueue/composition_workflow_chart_latest.json`, including workflow quantities, tier/group inventory, direct Blender-dedication labels, and a mapped-utilization table that shows which explicitly routed workload categories and real groups have actually fed bounded 3D runtime work. When the latest routing scan finds no explicit mapped workload, the chart reports that sparse state directly instead of implying always-on live workload. The underlying runtime-effectiveness surface now also exposes wall-clock 30-minute cadence buckets in `TemporaryQueue/runtime_effectiveness_latest.json` under `spatial_telemetry.recent_30m_buckets`; the chart module still renders the older sequence-window view until a later chart follow-through consumes those new bucket rows directly.

**Operator hints:**

```powershell
# Inspect cache entries (path, units, determinism tuple, age)
python -c "from module_ai_brain_bridge import get_cache_stats; import json; print(json.dumps(get_cache_stats(), indent=2))"

# Reset counters and cache (helpful before deterministic replays)
python -c "from module_ai_brain_bridge import clear_3d_cache; from module_relational_adapter import reset_3d_cycle_counters; clear_3d_cache(); reset_3d_cycle_counters(); print('cleared')"

# Snapshot via CLI (optionally clears cache/counters)
python cli.py 3d-cache-status --reset

# View 3D counters inside broader metrics report
python scripts/metrics_dashboard.py

# Build the current operator-facing 3D workflow/tier chart
python scripts/composition_workflow_chart_report.py
```

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

## Terminology Accuracy Rule

AI Brain architecture, schemas, stored artifacts, and emitted summaries must use domain-accurate terminology.

- The system may interpret figures of speech or informal user lingo.
- The system should not deliberately carry inaccurate terminology into schema names, artifact names, reasoning labels, or implementation-facing docs.
- If a term does not accurately describe the measured or persisted concept, replace it with wording that does.
- Examples of inaccurate implementation vocabulary to avoid include `sidecar` and `recipe` when they do not match the real concept.
