#!/usr/bin/env python3
"""Summarize mixed-cluster join, recovery, and shard-movement evidence."""

from __future__ import annotations

import argparse
import json
import sys
import time
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
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="fail if any required mixed-cluster evidence file is older than this many seconds",
    )
    args = parser.parse_args()

    phase_c_root = Path(args.phase_c_root)
    reports = {
        "phase_c_summary": inspect_report(phase_c_root / "phase-c-mixed-cluster-summary.json", args.max_report_age_seconds),
        "join": inspect_report(phase_c_root / "join/mixed-cluster-join-report.json", args.max_report_age_seconds),
        "live_join_probe": inspect_report(phase_c_root / "join/live-join-probe-report.json", args.max_report_age_seconds),
        "join_reject": inspect_report(phase_c_root / "join/join-reject-report.json", args.max_report_age_seconds),
        "recovery": inspect_report(phase_c_root / "recovery/mixed-cluster-recovery-report.json", args.max_report_age_seconds),
        "bounded_recovery_probe": inspect_report(phase_c_root / "recovery/bounded-peer-recovery-probe-report.json", args.max_report_age_seconds),
        "failure": inspect_report(phase_c_root / "failure/mixed-cluster-failure-report.json", args.max_report_age_seconds),
        "write_replication": inspect_report(phase_c_root / "write-replication/mixed-cluster-write-replication-report.json", args.max_report_age_seconds),
        "publication": inspect_report(phase_c_root / "publication/mixed-cluster-publication-report.json", args.max_report_age_seconds),
        "allocation": inspect_report(phase_c_root / "allocation/mixed-cluster-allocation-report.json", args.max_report_age_seconds),
    }
    shard_movement = inspect_shard_movement(Path(args.shard_movement_report), args.max_report_age_seconds)
    errors = [
        f"{name} report is missing or not passed"
        for name, report in reports.items()
        if not report["passed"]
    ]
    if not shard_movement["passed"]:
        errors.append("shard movement report is missing or not passed")
    errors.extend(
        freshness_error(f"{name} report", report)
        for name, report in reports.items()
        if not report["fresh"]
    )
    if not shard_movement["fresh"]:
        errors.append(freshness_error("shard movement report", shard_movement))
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
            "phase_c_fresh_report_count": sum(1 for report in reports.values() if report["fresh"]),
            "shard_movement_passed": shard_movement["passed"],
            "shard_movement_fresh": shard_movement["fresh"],
            "shard_movement_phase_count": shard_movement["phase_count"],
            "checkpoint_drift_ok": shard_movement["checkpoint_drift_ok"],
            "opensearch_to_steelsearch_passed": shard_movement["opensearch_to_steelsearch_passed"],
            "steelsearch_to_opensearch_passed": shard_movement["steelsearch_to_opensearch_passed"],
            "claim_boundary": (
                "representative mixed-cluster join, movement, recovery, failure, publication, "
                "allocation, and write-replication evidence is present"
            ),
        },
        "reports": reports,
        "shard_movement": shard_movement,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if status == "ok" else 1


def inspect_report(path: Path, max_age_seconds: float | None = None) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary") if isinstance(payload, dict) else None
    freshness = report_fresh(path, max_age_seconds)
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
        "summary": summary if isinstance(summary, dict) else {},
        "checks": payload.get("checks", {}) if isinstance(payload, dict) else {},
    }


def inspect_shard_movement(path: Path, max_age_seconds: float | None = None) -> dict[str, Any]:
    payload = load_json(path)
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    phases = payload.get("phases") if isinstance(payload, dict) else []
    freshness = report_fresh(path, max_age_seconds)
    phase_names = [
        str(phase.get("phase"))
        for phase in phases
        if isinstance(phase, dict) and phase.get("phase")
    ] if isinstance(phases, list) else []
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
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


def report_fresh(path: Path, max_age_seconds: float | None) -> dict[str, Any]:
    if max_age_seconds is None:
        return {"fresh": True, "age_seconds": None, "max_age_seconds": None}
    if not path.is_file():
        return {"fresh": False, "age_seconds": None, "max_age_seconds": max_age_seconds}
    age_seconds = time.time() - path.stat().st_mtime
    return {
        "fresh": age_seconds <= max_age_seconds,
        "age_seconds": round(age_seconds, 3),
        "max_age_seconds": max_age_seconds,
    }


def freshness_error(label: str, report: dict[str, Any]) -> str:
    if report["age_seconds"] is None:
        return f"{label} is missing"
    return (
        f"{label} is stale: age_seconds={report['age_seconds']:.0f} "
        f"max_age_seconds={report['max_age_seconds']:.0f}"
    )


if __name__ == "__main__":
    sys.exit(main())
