# Promotion PR Template — Adaptive Sampling

Copy/paste this into your PR description.

```md
Title: Promote adaptive sampling to production (gradual rollout)

Summary:
Enable adaptive Monte Carlo sampling in production behind the intended flag/config for a gradual rollout.
This change promotes the staging-tested adaptive sampling + rollback-storm policy monitoring.

Files changed:
- config.json (enable verifier.adaptive_sampling.enabled)
- docs/RELEASE_NOTES.md (add rollout note + date)
- docs/PRODUCTION_ROLLOUT.md (runbook reference)

Rollout plan:
1. Merge PR to main.
2. Deploy to canary (small blast radius) for 24 hours.
3. Run monitoring checks each cycle:
   - py -3 -m pytest tests/test_adversarial.py -q
   - py -3 run_eval.py
   - python metrics_dashboard.py --reports-dir TemporaryQueue --metrics-file metrics.json
   - py -3 scripts/check_rollback_storm_escalation_gate.py --use-config
   - (optional) py -3 tools/verify_sweep_outputs.py --sweep-dir TemporaryQueue/adversarial_sweep
4. If canary passes, expand rollout (e.g., 50% for 48 hours) then full rollout.

Acceptance thresholds:
- Sample reduction ≥ 30% vs baseline
- Decision disagreement ≤ 1% on fixed-seed regression
- Escalations at/below baseline (default 0)
- Determinism spot check passes (ignoring report_file paths)

Rollback plan:
- Revert config change (set verifier.adaptive_sampling.enabled -> false) and redeploy.
- Re-run the same monitoring checks to confirm baseline restored.

Triage plan on failure:
- Create a ticket with:
  - TemporaryQueue/metrics.json
  - pytest_adversarial.out, run_eval.out, metrics_summary.out
  - Any relevant adversarial reports/sweep outputs

Contacts:
- Feature owner: <name>
- Oncall: <email>
- QA lead: <name>

Notes:
- Keep CI regression gating enabled during rollout.
- If escalation rate rises, rollback immediately and attach provenance bundles for diagnosis.
```
