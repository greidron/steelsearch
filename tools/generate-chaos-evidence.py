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
    return errors


if __name__ == "__main__":
    sys.exit(main())
