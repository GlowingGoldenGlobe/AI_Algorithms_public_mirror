AI_Algorithms — dashboard.html

What it is:
- dashboard.html is a self-contained, offline-friendly dashboard with two use modes:
  - live AI Brain health panels for `TemporaryQueue/ai_brain_metrics_live.json` and `TemporaryQueue/ops_status.json`
  - historical and offline inspection panels for metrics, adversarial reports, scorecards, and charts

Primary live-health path (recommended when the dashboard server and watcher are running):
- Live Snapshot reads `TemporaryQueue/ai_brain_metrics_live.json`
- Ops Status reads `TemporaryQueue/ops_status.json`
- Analysis mode reuses current live and near-live artifact files only: live health, `TemporaryQueue/activity_scaling_latest.json` (or the fallback history at `ActiveSpace/Observability/activity_counts_history.jsonl`), `TemporaryQueue/hardware_preflight.json`, optional `TemporaryQueue/status_history.jsonl`, and the latest eval output (`run_eval.out` first, `TemporaryQueue/eval_latest.out` when present)
- The Ops Status panel includes an operator freshness/readiness summary that separates global runtime state from guard heartbeat freshness, hardware-preflight timestamp, simulation signal source, observed Blender process state, and current-record readiness evidence.
- Workflow pie payloads must be interpreted by source path and `generated_at`; `TemporaryQueue\composition_workflow_pie_live.json` is the live dashboard attachment surface, while `LongTermStore\composition_workflow_pie_live.json` can be a retained copy with older counts or partial retention evidence.
- Quick open in server mode:
   - `dashboard.html?autofetch=analysis`
  - `dashboard.html?autofetch=live`
  - `dashboard.html?autofetch=ops`
  - `dashboard.html?autofetch=run`

How to use (offline / file://):
1) Open dashboard.html in a browser.
2) For live-health inspection, load these files manually with the pickers:
   - `TemporaryQueue\ai_brain_metrics_live.json`
   - `TemporaryQueue\ops_status.json`
3) For historical analysis, optionally load:
   - `TemporaryQueue\metrics.json` or `TemporaryQueue\metrics_compare.json`
   - `adversarial_report_*.json`
   - `sweep_results.csv`
4) Click the relevant render or fetch actions.

Why file pickers:
- Browsers do not allow reading arbitrary local files or listing directories for security.

Optional “server mode” (enables relative-path fetch):
1) From repo root, run:
   - `AI Brain: dashboard suite (start) (detached)` for the full live-health path, or
   - `c:/Users/yerbr/AI_Algorithms/.venv/Scripts/python.exe scripts/run_dashboard_server.py`
2) Open:
   http://localhost:8000/dashboard.html
3) Use one of:
   - `dashboard.html?autofetch=analysis` to open the analysis-first live and near-live path
   - `dashboard.html?autofetch=live` to open directly into the live-health path
   - `dashboard.html?autofetch=ops` to refresh ops and supporting operational panels
   - `dashboard.html?autofetch=run` or `dashboard.html?autofetch=compare` for the historical metrics path

Note:
- Analysis mode intentionally avoids auto-fetching historical charts or adversarial reports; it prioritizes the live and near-live readiness surfaces first.
- The dashboard cannot discover all adversarial report filenames automatically; server mode still tries only a small set of known report names for the historical report sections.
- The live-health panels are already backed by real runtime artifacts; several analysis inputs are generated or optional rather than guaranteed to exist at every moment.
- If `ops_status.json` reports `ok=true` while the ops-monitor heartbeat is stale, treat the dashboard as active but needing operator attention rather than as fully supervised.
- If global runtime state is active while current-record readiness says `ready_for_live_simulation=false`, use the readiness row as a current-record evidence gap; do not treat it as a runtime-control command or serving-state change.
- `TemporaryQueue/activity_scaling_latest.json` is a generated convenience file; if it has not been emitted yet, the dashboard can fall back to `ActiveSpace/Observability/activity_counts_history.jsonl` in server mode.
- `TemporaryQueue/status_history.jsonl` may be absent during some runs; in that case the evaluation scorecard's speed/context rows remain partial rather than implying zero activity.
- The charts and evaluation sections still depend on historical files such as `metrics.json`, `metrics_compare.json`, `status_history.jsonl`, `eval_latest.out`, and adversarial report files.
- File picker mode remains the most reliable offline fallback.

Non-empty create-tier proposal verification (fixture path):
1) Start the dashboard in server mode.
2) Open the Ops Status panel.
3) Use one of:
    - `Load runtime-gate fixture`
    - `Load initial-selection fixture`
4) Confirm that the Create-Tier Proposal Review panel shows one blocked row with the expected blocking stage and drilldown details.

Expected fixture meanings:
- `tests/fixtures/dashboard_ops_status_runtime_gate_block.json`
   - one `reference_shard_factory` proposal row
   - blocked at `runtime_gate`
   - unsatisfied dry-run gates remain visible in the drilldown
- `tests/fixtures/dashboard_ops_status_initial_selection_block.json`
   - one `simultaneous_context_match` proposal row
   - blocked at `initial_selection`
   - capacity and follow-on guard reasons remain visible in the drilldown

Offline fallback for the same check:
1) Open `dashboard.html` via file://.
2) In the Ops Status panel, click `Load ops status from file`.
3) Select one of the two fixture files under `tests/fixtures/`.
4) The live `TemporaryQueue/ops_status.json` path remains unchanged; the fixture file is only a reproducible non-empty verification surface.
