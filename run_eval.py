# run_eval.py (public mirror)
#
# Minimal eval harness for the public mirror.
# Runs only adversarial-related gates so the mirror stays small.

from __future__ import annotations

import json

from module_adversarial_test import run_scenario


def _case(name: str, ok: bool, details: dict | None = None) -> dict:
    return {"case": name, "passed": bool(ok), "details": details or {}}


def logic_adversarial_report_shape() -> dict:
    rep = run_scenario("S1_small_noise", deterministic_mode=True)
    ok = isinstance(rep, dict)
    ok = ok and isinstance(rep.get("scenario_id"), str)
    ok = ok and isinstance(rep.get("result"), dict)
    ok = ok and isinstance(rep.get("deterministic_mode"), bool)
    ok = ok and isinstance(rep.get("seed_obj"), dict)
    ok = ok and ("provenance_snapshot" in rep)
    return _case("logic_adversarial_report_shape", ok)


def logic_adversarial_deterministic_repro() -> dict:
    a = run_scenario("S1_small_noise", deterministic_mode=True)
    b = run_scenario("S1_small_noise", deterministic_mode=True)
    ok = a == b
    return _case("logic_adversarial_deterministic_repro", ok)


def logic_adversarial_escalation_policy() -> dict:
    rep = run_scenario("S5_rollback_storm", deterministic_mode=True)
    res = rep.get("result") if isinstance(rep, dict) else None
    ok = isinstance(res, dict) and res.get("escalation_action") == "escalate"
    return _case("logic_adversarial_escalation_policy", ok)


def main() -> int:
    cases = [
        logic_adversarial_report_shape,
        logic_adversarial_deterministic_repro,
        logic_adversarial_escalation_policy,
    ]

    results = []
    failures = 0
    for fn in cases:
        try:
            r = fn()
        except Exception as e:
            r = _case(getattr(fn, "__name__", "unknown"), False, {"error": str(e)})
        results.append(r)
        if not r.get("passed"):
            failures += 1

    print("Case Results:")
    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"- {r.get('case')}: {status}")

    # Machine-readable summary for callers
    summary = {"failures": failures, "results": results}
    with open("eval_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
