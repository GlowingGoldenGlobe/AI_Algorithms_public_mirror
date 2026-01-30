from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from module_adversarial_test import run_scenario


SCENARIOS = [
    "S1_small_noise",
    "S2_large_outlier",
    "S3_context_swap",
    "S4_poisoned_retrieval",
    "S5_rollback_storm",
    "S6_counterfactual_negative_gain",
]


def main() -> int:
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "TemporaryQueue")
    report_dir = os.path.abspath(report_dir)
    os.makedirs(report_dir, exist_ok=True)

    index: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "deterministic_mode": True,
        "report_dir": report_dir,
        "reports": [],
    }

    for scenario_id in SCENARIOS:
        rep = run_scenario(
            scenario_id,
            deterministic_mode=True,
            write_report=True,
            report_dir=report_dir,
        )
        # Keep index lightweight; link to the full report JSON.
        index["reports"].append(
            {
                "scenario_id": scenario_id,
                "report_file": rep.get("report_file"),
                "has_required_fields": all(
                    k in rep for k in ("scenario_id", "deterministic_mode", "seed_obj", "result", "provenance_snapshot", "report_file")
                ),
            }
        )

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "adversarial_run_index.json")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(json.dumps(index, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
