#!/usr/bin/env python3
"""Summarize mixed-cluster join, recovery, and shard-movement evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHASE_C_ROOT = ROOT / "target/phase-c-mixed-cluster"
DEFAULT_SHARD_MOVEMENT = ROOT / "target/three-node-shard-movement-checkpoint-20260616/report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-c-root", default=str(DEFAULT_PHASE_C_ROOT))
    parser.add_argument("--shard-movement-report", default=str(DEFAULT_SHARD_MOVEMENT))
    parser.add_argument("--output")
    parser.add_argument("--require-passed", action="store_true")
    args = parser.parse_args()

    phase_c_root = Path(args.phase_c_root)
    reports = {
        "phase_c_summary": inspect_report(phase_c_root / "phase-c-mixed-cluster-summary.json"),
        "join": inspect_report(phase_c_root / "join/mixed-cluster-join-report.json"),
        "live_join_probe": inspect_report(phase_c_root / "join/live-join-probe-report.json"),
        "join_reject": inspect_report(phase_c_root / "join/join-reject-report.json"),
        "recovery": inspect_report(phase_c_root / "recovery/mixed-cluster-recovery-report.json"),
        "bounded_recovery_probe": inspect_report(phase_c_root / "recovery/bounded-peer-recovery-probe-report.json"),
        "failure": inspect_report(phase_c_root / "failure/mixed-cluster-failure-report.json"),
        "write_replication": inspect_report(phase_c_root / "write-replication/mixed-cluster-write-replication-report.json"),
        "publication": inspect_report(phase_c_root / "publication/mixed-cluster-publication-report.json"),
        "allocation": inspect_report(phase_c_root / "allocation/mixed-cluster-allocation-report.json"),
    }
    shard_movement = inspect_shard_movement(Path(args.shard_movement_report))
    errors = [
        f"{name} report is missing or not passed"
        for name, report in reports.items()
        if not report["passed"]
    ]
    if not shard_movement["passed"]:
        errors.append("shard movement report is missing or not passed")
    if not args.require_passed:
        errors = []

    passed_reports = sum(1 for report in reports.values() if report["passed"])
    status = "ok" if not errors else "failed"
    report = {
        "status": status,
        "errors": errors,
        "phase_c_root": str(phase_c_root),
        "summary": {
            "passed": not errors,
            "phase_c_report_count": len(reports),
            "phase_c_passed_report_count": passed_reports,
            "shard_movement_passed": shard_movement["passed"],
            "shard_movement_phase_count": shard_movement["phase_count"],
            "checkpoint_drift_ok": shard_movement["checkpoint_drift_ok"],
            "opensearch_to_steelsearch_passed": shard_movement["opensearch_to_steelsearch_passed"],
            "steelsearch_to_opensearch_passed": shard_movement["steelsearch_to_opensearch_passed"],
            "claim_boundary": (
                "representative mixed-cluster join/movement/recovery evidence is present; "
                "generic Java OpenSearch data-node replacement remains outside the current milestone"
            ),
        },
        "reports": reports,
        "shard_movement": shard_movement,
        "out_of_scope": [
            "generic Java OpenSearch data-node replacement inside an arbitrary existing Java cluster",
            "Java plugin hot-path compatibility",
            "Lucene segment/translog binary compatibility",
            "direct OpenSearch snapshot repository import",
        ],
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if status == "ok" else 1


def inspect_report(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary") if isinstance(payload, dict) else None
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "summary": summary if isinstance(summary, dict) else {},
        "checks": payload.get("checks", {}) if isinstance(payload, dict) else {},
    }


def inspect_shard_movement(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    phases = payload.get("phases") if isinstance(payload, dict) else []
    phase_names = [
        str(phase.get("phase"))
        for phase in phases
        if isinstance(phase, dict) and phase.get("phase")
    ] if isinstance(phases, list) else []
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "phase_count": len(phase_names),
        "phase_names": phase_names,
        "checkpoint_drift_ok": bool(summary.get("checkpoint_drift_ok")) if isinstance(summary, dict) else False,
        "opensearch_to_steelsearch_passed": bool(summary.get("opensearch_to_steelsearch_passed")) if isinstance(summary, dict) else False,
        "steelsearch_to_opensearch_passed": bool(summary.get("steelsearch_to_opensearch_passed")) if isinstance(summary, dict) else False,
        "summary": summary if isinstance(summary, dict) else {},
    }


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    sys.exit(main())
