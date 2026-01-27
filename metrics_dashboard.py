"""metrics_dashboard.py

Thin wrapper so the command `python metrics_dashboard.py ...` works.

The actual implementation lives in scripts/metrics_dashboard.py.

Examples:
  python metrics_dashboard.py
  python metrics_dashboard.py --reports-dir . --metrics-file metrics.json
  py -3 metrics_dashboard.py --path TemporaryQueue/metrics.json
"""

from __future__ import annotations

import os
import runpy


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "scripts", "metrics_dashboard.py")
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
