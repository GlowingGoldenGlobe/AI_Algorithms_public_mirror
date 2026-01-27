# Determinism & Activity Logging Results

Date: 2025-12-14

Highlights:
- Collector outputs use fixed timestamps under `determinism.deterministic_mode` (timestamp, end_ts).
- `RelationalMeasurement()` writes `cycle_ts` and activity logs maintain `cycles` + `last_cycle_ts` under `ActiveSpace/activity.json` and `LongTermStore/ActiveSpace/activity.json`.
- Semantic index builds stabilized with fixed `last_build_ts` and sorted IDs.

Eval Coverage:
- Deterministic collector timestamps: PASS
- Activity `last_cycle_ts` presence (ActiveSpace and LongTermStore): PASS
- Integration cycle record presence: PASS

Files touched:
- module_collector.py — fixed timestamps in subprocess outputs.
- module_integration.py — `cycle_ts` and LongTermStore activity updates; arbiter honors decisive measurement.
- module_current_activity.py — deterministic timestamps and `cycles` + `last_cycle_ts` population.
- module_tools.py — stable index build.
- run_eval.py — deterministic and activity evals.

Notes:
- Determinism is configurable via `config.json > determinism`.
- Measurement now emits `weighted_score` and `decisive_recommendation` to guide arbiter decisions.
