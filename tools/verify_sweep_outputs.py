"""tools/verify_sweep_outputs.py

Verify adversarial sweep outputs.

Checks:
- sweep_results.csv exists and is readable
- each row references a report file that exists
- report filenames follow the canonical pattern:
    adversarial_report_{scenario_id}_{cell_id}_r{repeat}.json
- optional: compare two sweep runs and assert deterministic equality of reports,
  ignoring the report field `report_file` (paths differ across out dirs).

Exit codes:
- 0: success
- 2: verification failed / invalid inputs

Examples:
  py -3 tools/verify_sweep_outputs.py --sweep-dir TemporaryQueue/adversarial_sweep
  py -3 tools/verify_sweep_outputs.py --sweep-dir out_a --compare-dir out_b
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _repo_default_sweep_dir() -> str:
    try:
        from module_storage import resolve_path
        from module_tools import safe_join

        return safe_join(resolve_path("temporary"), "adversarial_sweep")
    except Exception:
        return os.path.join("TemporaryQueue", "adversarial_sweep")


def _read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def _is_abs(p: str) -> bool:
    try:
        return os.path.isabs(p)
    except Exception:
        return False


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return default


def _stable_json_hash(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        s = str(obj)
    # Standard library only: stable content hash
    import hashlib

    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _strip_volatile_fields(report: Any) -> Any:
    if not isinstance(report, dict):
        return report
    out = dict(report)
    out.pop("report_file", None)
    return out


@dataclass(frozen=True)
class RunKey:
    scenario_id: str
    cell_id: str
    repeat: int


@dataclass
class SweepIndex:
    sweep_dir: str
    csv_path: str
    reports_dir: str
    rows: List[Dict[str, str]]

    def expected_filename(self, row: Dict[str, str]) -> str:
        scenario_id = str(row.get("scenario_id", "")).strip()
        cell_id = str(row.get("cell_id", "")).strip()
        repeat = _safe_int(row.get("repeat", 0), 0)
        return f"adversarial_report_{scenario_id}_{cell_id}_r{repeat}.json"

    def row_key(self, row: Dict[str, str]) -> RunKey:
        return RunKey(
            scenario_id=str(row.get("scenario_id", "")).strip(),
            cell_id=str(row.get("cell_id", "")).strip(),
            repeat=_safe_int(row.get("repeat", 0), 0),
        )

    def resolve_report_path(self, row: Dict[str, str]) -> Tuple[str, str]:
        """Returns (resolved_path, resolution_mode)."""
        raw = str(row.get("report_file", "") or "").strip()
        expected = self.expected_filename(row)

        # 1) If CSV includes a path, try it first.
        if raw:
            candidates: List[str] = []
            if _is_abs(raw):
                candidates.append(raw)
            else:
                candidates.append(os.path.join(self.sweep_dir, raw))
                candidates.append(os.path.join(self.reports_dir, raw))
                candidates.append(os.path.join(self.reports_dir, os.path.basename(raw)))

            for c in candidates:
                if os.path.exists(c):
                    return c, "csv_report_file"

        # 2) Fall back to canonical location in reports_dir.
        fallback = os.path.join(self.reports_dir, expected)
        return fallback, "reports_dir_expected"


def _build_index(
    *,
    sweep_dir: str,
    csv_path: Optional[str],
    reports_dir: Optional[str],
) -> SweepIndex:
    sweep_dir = str(sweep_dir)
    csv_path2 = str(csv_path) if csv_path else os.path.join(sweep_dir, "sweep_results.csv")
    reports_dir2 = str(reports_dir) if reports_dir else os.path.join(sweep_dir, "reports")

    rows = _read_csv_rows(csv_path2)
    return SweepIndex(sweep_dir=sweep_dir, csv_path=csv_path2, reports_dir=reports_dir2, rows=rows)


def _verify_index(idx: SweepIndex) -> Tuple[bool, Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    if not os.path.exists(idx.csv_path):
        return False, {"error": f"missing csv: {idx.csv_path}"}

    total = len(idx.rows)
    missing_files = 0
    bad_pattern = 0
    empty_report_file = 0

    for i, row in enumerate(idx.rows):
        expected = idx.expected_filename(row)
        raw = str(row.get("report_file", "") or "").strip()
        if not raw:
            empty_report_file += 1

        report_path, mode = idx.resolve_report_path(row)

        if os.path.basename(report_path) != expected:
            bad_pattern += 1
            if len(issues) < 10:
                issues.append(
                    {
                        "row": i,
                        "scenario_id": row.get("scenario_id"),
                        "cell_id": row.get("cell_id"),
                        "repeat": row.get("repeat"),
                        "expected": expected,
                        "got": os.path.basename(report_path),
                        "resolution_mode": mode,
                    }
                )

        if not os.path.exists(report_path):
            missing_files += 1
            if len(issues) < 10:
                issues.append(
                    {
                        "row": i,
                        "missing": report_path,
                        "expected": expected,
                        "raw_report_file": raw,
                        "resolution_mode": mode,
                    }
                )

    ok = (missing_files == 0) and (bad_pattern == 0)

    summary: Dict[str, Any] = {
        "csv": idx.csv_path,
        "reports_dir": idx.reports_dir,
        "rows": total,
        "missing_files": missing_files,
        "bad_pattern": bad_pattern,
        "empty_report_file": empty_report_file,
        "issues_sample": issues,
    }
    return ok, summary


def _compare_reports(a: SweepIndex, b: SweepIndex) -> Tuple[bool, Dict[str, Any]]:
    # Build key -> row mapping
    map_a: Dict[RunKey, Dict[str, str]] = {a.row_key(r): r for r in a.rows}
    map_b: Dict[RunKey, Dict[str, str]] = {b.row_key(r): r for r in b.rows}

    only_a = sorted(set(map_a.keys()) - set(map_b.keys()), key=lambda k: (k.scenario_id, k.cell_id, k.repeat))
    only_b = sorted(set(map_b.keys()) - set(map_a.keys()), key=lambda k: (k.scenario_id, k.cell_id, k.repeat))

    mismatched = 0
    mismatches: List[Dict[str, Any]] = []

    common_keys = sorted(set(map_a.keys()) & set(map_b.keys()), key=lambda k: (k.scenario_id, k.cell_id, k.repeat))

    for k in common_keys:
        ra = map_a[k]
        rb = map_b[k]

        pa, _ = a.resolve_report_path(ra)
        pb, _ = b.resolve_report_path(rb)

        try:
            ja = _strip_volatile_fields(_load_json(pa))
            jb = _strip_volatile_fields(_load_json(pb))
        except Exception as e:
            mismatched += 1
            if len(mismatches) < 10:
                mismatches.append({"key": k.__dict__, "error": f"read_failed: {e}", "a": pa, "b": pb})
            continue

        if _stable_json_hash(ja) != _stable_json_hash(jb):
            mismatched += 1
            if len(mismatches) < 10:
                mismatches.append(
                    {
                        "key": k.__dict__,
                        "a": pa,
                        "b": pb,
                        "hash_a": _stable_json_hash(ja)[:12],
                        "hash_b": _stable_json_hash(jb)[:12],
                    }
                )

    ok = (not only_a) and (not only_b) and (mismatched == 0)
    summary: Dict[str, Any] = {
        "compare": True,
        "a": a.sweep_dir,
        "b": b.sweep_dir,
        "rows_a": len(a.rows),
        "rows_b": len(b.rows),
        "only_in_a": [k.__dict__ for k in only_a[:10]],
        "only_in_b": [k.__dict__ for k in only_b[:10]],
        "mismatched_reports": mismatched,
        "mismatches_sample": mismatches,
        "deterministic_equal_ignoring_report_file": ok,
    }
    return ok, summary


def _compare_report_dirs(dir_a: str, dir_b: str) -> Tuple[bool, Dict[str, Any]]:
    """Compare two directories of adversarial_report_*.json by basename.

    This is a lighter-weight determinism spot-check that does not require CSVs.
    """

    def scan(d: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        try:
            for name in os.listdir(d):
                if not name.startswith("adversarial_report_") or not name.lower().endswith(".json"):
                    continue
                out[name] = os.path.join(d, name)
        except Exception:
            return {}
        return out

    files_a = scan(str(dir_a))
    files_b = scan(str(dir_b))

    only_a = sorted(set(files_a.keys()) - set(files_b.keys()))
    only_b = sorted(set(files_b.keys()) - set(files_a.keys()))

    mismatched = 0
    mismatches: List[Dict[str, Any]] = []

    for name in sorted(set(files_a.keys()) & set(files_b.keys())):
        pa = files_a[name]
        pb = files_b[name]
        try:
            ja = _strip_volatile_fields(_load_json(pa))
            jb = _strip_volatile_fields(_load_json(pb))
        except Exception as e:
            mismatched += 1
            if len(mismatches) < 10:
                mismatches.append({"file": name, "error": f"read_failed: {e}", "a": pa, "b": pb})
            continue

        if _stable_json_hash(ja) != _stable_json_hash(jb):
            mismatched += 1
            if len(mismatches) < 10:
                mismatches.append(
                    {
                        "file": name,
                        "a": pa,
                        "b": pb,
                        "hash_a": _stable_json_hash(ja)[:12],
                        "hash_b": _stable_json_hash(jb)[:12],
                    }
                )

    ok = (not only_a) and (not only_b) and (mismatched == 0)
    summary: Dict[str, Any] = {
        "compare": True,
        "mode": "report_dirs",
        "a": str(dir_a),
        "b": str(dir_b),
        "files_a": len(files_a),
        "files_b": len(files_b),
        "only_in_a": only_a[:10],
        "only_in_b": only_b[:10],
        "mismatched_reports": mismatched,
        "mismatches_sample": mismatches,
        "deterministic_equal_ignoring_report_file": ok,
    }
    return ok, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep-dir", default=None, help="Sweep output directory (contains sweep_results.csv and reports/)")
    ap.add_argument("--csv", default=None, help="Optional path to sweep_results.csv")
    ap.add_argument("--reports-dir", default=None, help="Optional reports directory (default: <sweep-dir>/reports)")
    ap.add_argument("--compare-dir", default=None, help="Optional second sweep dir to compare determinism")
    ap.add_argument("--compare-csv", default=None, help="Optional second sweep csv path")
    ap.add_argument("--compare-reports-dir", default=None, help="Optional second reports dir")
    ap.add_argument(
        "--detcheck",
        nargs=2,
        metavar=("DIR_A", "DIR_B"),
        help="Alias: compare two report dirs directly (adversarial_report_*.json), ignoring report_file",
    )
    ap.add_argument("--json", action="store_true", help="Print results as JSON")
    args = ap.parse_args()

    sweep_dir = str(args.sweep_dir) if args.sweep_dir else _repo_default_sweep_dir()

    try:
        idx = _build_index(sweep_dir=sweep_dir, csv_path=args.csv, reports_dir=args.reports_dir)
    except Exception as e:
        print(f"failed to load sweep index: {e}")
        return 2

    ok1, summary1 = _verify_index(idx)

    summaries: List[Dict[str, Any]] = [summary1]
    overall_ok = bool(ok1)

    if args.detcheck:
        ok_det, summary_det = _compare_report_dirs(str(args.detcheck[0]), str(args.detcheck[1]))
        summaries.append(summary_det)
        overall_ok = overall_ok and bool(ok_det)

    if args.compare_dir:
        try:
            idx2 = _build_index(
                sweep_dir=str(args.compare_dir),
                csv_path=args.compare_csv,
                reports_dir=args.compare_reports_dir,
            )
        except Exception as e:
            print(f"failed to load compare sweep index: {e}")
            return 2

        ok2, summary2 = _verify_index(idx2)
        ok3, summary3 = _compare_reports(idx, idx2)
        summaries.extend([summary2, summary3])
        overall_ok = overall_ok and bool(ok2) and bool(ok3)

    if args.json:
        print(json.dumps({"ok": overall_ok, "summaries": summaries}, indent=2, sort_keys=True))
    else:
        print(f"ok: {overall_ok}")
        for s in summaries:
            if s.get("compare"):
                print(f"deterministic_equal_ignoring_report_file: {bool(s.get('deterministic_equal_ignoring_report_file'))}")
                print(f"mismatched_reports: {s.get('mismatched_reports')}")
            else:
                print(f"rows: {s.get('rows')} missing_files: {s.get('missing_files')} bad_pattern: {s.get('bad_pattern')} empty_report_file: {s.get('empty_report_file')}")

    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
