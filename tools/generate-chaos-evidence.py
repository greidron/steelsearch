#!/usr/bin/env python3
"""Generate mixed-cluster failure/chaos evidence for release readiness."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/run_mixed_cluster_failure_profile.sh"
REQUIRED_EXECUTED_TESTS = {
    "daemon_point_in_time_contexts_do_not_survive_restart",
    "daemon_transport_point_in_time_contexts_do_not_survive_restart",
    "multi_daemon_get_all_pits_fans_out_to_seed_peers",
}
REQUIRED_CHILD_EXECUTED_TESTS = {
    "pit_restart_lifecycle_report": {
        "daemon_point_in_time_contexts_do_not_survive_restart",
    },
    "pit_transport_restart_lifecycle_report": {
        "daemon_transport_point_in_time_contexts_do_not_survive_restart",
    },
    "pit_multi_daemon_lifecycle_report": {
        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "target/release-chaos")
    parser.add_argument("--output", type=Path, default=ROOT / "target/release-chaos/chaos-report.json")
    args = parser.parse_args()

    report = generate_report(
        args.root.resolve(),
        work_dir=args.work_dir,
        output=args.output,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["passed"] else 1


def generate_report(root: Path, *, work_dir: Path, output: Path) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PHASE_C_FAILURE_WORK_DIR"] = str(work_dir)
    completed = subprocess.run(
        ["bash", str(root / "tools/run_mixed_cluster_failure_profile.sh")],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    source_report_path = work_dir / "mixed-cluster-failure-report.json"
    source_report = load_json(source_report_path)
    blockers = validate_source_report(source_report)
    if completed.returncode != 0:
        blockers.append(f"mixed-cluster failure profile failed: returncode={completed.returncode}")
    return {
        "ready": not blockers,
        "passed": not blockers,
        "blockers": blockers,
        "summary": {
            "passed": not blockers,
            "error_count": len(blockers),
            "coverage_scope": "mixed-cluster failure fixture",
            "source_report": str(source_report_path),
        },
        "metadata": {
            "generated_at_epoch_seconds": int(time.time()),
            "root": str(root),
            "work_dir": str(work_dir),
        },
        "command": ["bash", str(root / "tools/run_mixed_cluster_failure_profile.sh")],
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "source_report": source_report,
    }


def load_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source_report(report: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["mixed-cluster failure report is not a JSON object"]
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("passed") is not True:
        errors.append("mixed-cluster failure summary.passed is not true")
    checks = report.get("checks")
    if not isinstance(checks, dict):
        errors.append("mixed-cluster failure checks are missing")
    else:
        expected = {
            "failure_topology_probe_passed",
            "failure_ledger_passed",
            "pit_restart_lifecycle_passed",
            "pit_transport_restart_lifecycle_passed",
            "pit_multi_daemon_lifecycle_passed",
        }
        missing = sorted(expected - set(checks))
        if missing:
            errors.append(f"mixed-cluster failure checks are missing: {', '.join(missing)}")
        for name in sorted(expected & set(checks)):
            if checks.get(name) is not True:
                errors.append(f"mixed-cluster failure check is not true: {name}")
    reports = report.get("reports")
    if not isinstance(reports, dict) or not reports:
        errors.append("mixed-cluster failure child reports are missing")
    executed_tests = report.get("executed_tests")
    if not isinstance(executed_tests, list):
        errors.append("mixed-cluster failure executed_tests are missing")
    else:
        missing_tests = sorted(REQUIRED_EXECUTED_TESTS - {str(test) for test in executed_tests})
        if missing_tests:
            errors.append(
                f"mixed-cluster failure executed_tests are missing: {', '.join(missing_tests)}"
            )
    errors.extend(validate_child_executed_tests(report))
    return errors


def validate_child_executed_tests(report: dict[str, Any]) -> list[str]:
    child_executed_tests = report.get("child_executed_tests")
    if not isinstance(child_executed_tests, dict):
        return ["mixed-cluster failure child_executed_tests are missing"]
    errors: list[str] = []
    child_union: set[str] = set()
    for child_name, required_tests in sorted(REQUIRED_CHILD_EXECUTED_TESTS.items()):
        child_tests = child_executed_tests.get(child_name)
        if not isinstance(child_tests, list):
            errors.append(f"mixed-cluster failure child_executed_tests are missing: {child_name}")
            continue
        child_test_names = {str(test) for test in child_tests}
        child_union.update(child_test_names)
        missing_tests = sorted(required_tests - child_test_names)
        if missing_tests:
            errors.append(
                f"mixed-cluster failure {child_name} executed_tests are missing: {', '.join(missing_tests)}"
            )
    final_tests = report.get("executed_tests")
    if isinstance(final_tests, list) and child_union != {str(test) for test in final_tests}:
        errors.append("mixed-cluster failure executed_tests do not match child_executed_tests")
    return errors


if __name__ == "__main__":
    sys.exit(main())
