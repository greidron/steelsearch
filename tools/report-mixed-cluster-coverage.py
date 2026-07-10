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
DEFAULT_SHARD_MOVEMENT = ROOT / "target/three-node-shard-movement-current/report.json"
REQUIRED_REPORT_CHECKS = {
    "join": {
        "live_join_probe_passed",
        "join_reject_passed",
    },
    "live_join_probe": {
        "remote_transport_version_matches_fixture",
        "response_header_matches_min_compat",
        "transport_payload_matches_fixture",
        "handshake_cluster_name_matches_state",
        "cluster_uuid_present",
        "single_local_node_visible",
        "advertised_roles_match_fixture",
        "required_attributes_present",
        "transport_address_present",
        "node_name_present",
    },
    "recovery": {
        "bounded_peer_recovery_probe_passed",
        "recovery_reject_passed",
    },
    "bounded_recovery_probe": {
        "wire_round_trip_passed",
    },
    "failure": {
        "failure_topology_probe_passed",
        "failure_ledger_passed",
        "pit_restart_lifecycle_passed",
        "pit_transport_restart_lifecycle_passed",
        "pit_multi_daemon_lifecycle_passed",
    },
    "write_replication": {
        "write_replication_happy_path_passed",
        "write_replication_reject_passed",
    },
    "publication": {
        "publication-full-state-report.json",
        "publication-diff-ack-report.json",
        "publication-reject-report.json",
    },
    "allocation": {
        "routing_convergence_probe_passed",
        "allocation_reject_passed",
    },
}
REQUIRED_PHASE_C_SUMMARY_REPORTS = {
    "mixed-cluster-allocation-report.json",
    "mixed-cluster-failure-report.json",
    "mixed-cluster-join-report.json",
    "mixed-cluster-publication-report.json",
    "mixed-cluster-recovery-report.json",
    "mixed-cluster-write-replication-report.json",
}
REQUIRED_EXECUTED_TESTS = {
    "failure": {
        "daemon_point_in_time_contexts_do_not_survive_restart",
        "daemon_transport_point_in_time_contexts_do_not_survive_restart",
        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    },
}
REQUIRED_SHARD_MOVEMENT_SUMMARY_FLAGS = {
    "checkpoint_drift_ok",
    "checkpoint_monotonicity_ok",
    "opensearch_to_steelsearch_passed",
    "retention_lease_metadata_ok",
    "steelsearch_to_opensearch_passed",
    "transport_log_ok",
    "unsupported_allocation_explain_ok",
}


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
    errors.extend(
        f"{name} report missing required checks: {missing}"
        for name, report in reports.items()
        if (missing := report["missing_required_checks"])
    )
    errors.extend(
        f"{name} report has failed required checks: {failed}"
        for name, report in reports.items()
        if (failed := report["failed_required_checks"])
    )
    errors.extend(
        f"{name} report missing required child reports: {missing}"
        for name, report in reports.items()
        if (missing := report["missing_required_reports"])
    )
    errors.extend(
        f"{name} report has failed required child reports: {failed}"
        for name, report in reports.items()
        if (failed := report["failed_required_reports"])
    )
    errors.extend(
        f"{name} report missing required executed tests: {missing}"
        for name, report in reports.items()
        if (missing := report["missing_required_executed_tests"])
    )
    errors.extend(
        f"{name} report missing child executed test map"
        for name, report in reports.items()
        if report["missing_child_executed_tests"]
    )
    errors.extend(
        f"{name} report executed tests do not match child reports"
        for name, report in reports.items()
        if report["executed_tests_child_mismatch"]
    )
    if not shard_movement["passed"]:
        errors.append("shard movement report is missing or not passed")
    if shard_movement["failed_required_summary_flags"]:
        errors.append(
            "shard movement report has failed required summary flags: "
            f"{shard_movement['failed_required_summary_flags']}"
        )
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
            "checkpoint_monotonicity_ok": shard_movement["checkpoint_monotonicity_ok"],
            "opensearch_to_steelsearch_passed": shard_movement["opensearch_to_steelsearch_passed"],
            "retention_lease_metadata_ok": shard_movement["retention_lease_metadata_ok"],
            "steelsearch_to_opensearch_passed": shard_movement["steelsearch_to_opensearch_passed"],
            "transport_log_ok": shard_movement["transport_log_ok"],
            "unsupported_allocation_explain_ok": shard_movement[
                "unsupported_allocation_explain_ok"
            ],
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
    checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
    required_checks = required_checks_for(path)
    child_reports = payload.get("reports", {}) if isinstance(payload, dict) else {}
    required_reports = required_reports_for(path)
    executed_tests = payload.get("executed_tests", []) if isinstance(payload, dict) else []
    executed_test_names = {str(test) for test in executed_tests} if isinstance(executed_tests, list) else set()
    required_executed_tests = required_executed_tests_for(path)
    child_executed_tests = payload.get("child_executed_tests", {}) if isinstance(payload, dict) else {}
    child_executed_test_names = child_executed_tests_union(child_executed_tests)
    missing_child_executed_tests = bool(required_executed_tests) and not isinstance(
        payload.get("child_executed_tests") if isinstance(payload, dict) else None,
        dict,
    )
    missing_required_checks = sorted(required_checks - set(checks))
    failed_required_checks = sorted(
        check for check in required_checks if check in checks and checks.get(check) is not True
    )
    missing_required_reports = sorted(required_reports - set(child_reports))
    failed_required_reports = sorted(
        name
        for name in required_reports
        if name in child_reports and child_reports.get(name) is not True
    )
    missing_required_executed_tests = sorted(required_executed_tests - executed_test_names)
    executed_tests_child_mismatch = (
        bool(child_executed_test_names) and child_executed_test_names != executed_test_names
    )
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
        "summary": summary if isinstance(summary, dict) else {},
        "checks": checks,
        "required_checks": sorted(required_checks),
        "missing_required_checks": missing_required_checks,
        "failed_required_checks": failed_required_checks,
        "reports": child_reports,
        "required_reports": sorted(required_reports),
        "missing_required_reports": missing_required_reports,
        "failed_required_reports": failed_required_reports,
        "executed_tests": sorted(executed_test_names),
        "child_executed_tests": child_executed_tests if isinstance(child_executed_tests, dict) else {},
        "child_executed_tests_union": sorted(child_executed_test_names),
        "required_executed_tests": sorted(required_executed_tests),
        "missing_required_executed_tests": missing_required_executed_tests,
        "missing_child_executed_tests": missing_child_executed_tests,
        "executed_tests_child_mismatch": executed_tests_child_mismatch,
    }


def required_checks_for(path: Path) -> set[str]:
    normalized = path.as_posix()
    for name, required_checks in REQUIRED_REPORT_CHECKS.items():
        if name == "live_join_probe" and normalized.endswith("/join/live-join-probe-report.json"):
            return required_checks
        if name == "join" and normalized.endswith("/join/mixed-cluster-join-report.json"):
            return required_checks
        if name == "bounded_recovery_probe" and normalized.endswith(
            "/recovery/bounded-peer-recovery-probe-report.json"
        ):
            return required_checks
        if name == "recovery" and normalized.endswith("/recovery/mixed-cluster-recovery-report.json"):
            return required_checks
        if name == "failure" and normalized.endswith("/failure/mixed-cluster-failure-report.json"):
            return required_checks
        if name == "write_replication" and normalized.endswith(
            "/write-replication/mixed-cluster-write-replication-report.json"
        ):
            return required_checks
        if name == "publication" and normalized.endswith(
            "/publication/mixed-cluster-publication-report.json"
        ):
            return required_checks
        if name == "allocation" and normalized.endswith(
            "/allocation/mixed-cluster-allocation-report.json"
        ):
            return required_checks
    return set()


def required_reports_for(path: Path) -> set[str]:
    if path.as_posix().endswith("/phase-c-mixed-cluster-summary.json"):
        return REQUIRED_PHASE_C_SUMMARY_REPORTS
    return set()


def required_executed_tests_for(path: Path) -> set[str]:
    normalized = path.as_posix()
    if normalized.endswith("/failure/mixed-cluster-failure-report.json"):
        return REQUIRED_EXECUTED_TESTS["failure"]
    return set()


def child_executed_tests_union(child_executed_tests: Any) -> set[str]:
    if not isinstance(child_executed_tests, dict):
        return set()
    names: set[str] = set()
    for value in child_executed_tests.values():
        if isinstance(value, list):
            names.update(str(test) for test in value)
    return names


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
    failed_required_summary_flags = sorted(
        flag
        for flag in REQUIRED_SHARD_MOVEMENT_SUMMARY_FLAGS
        if not (isinstance(summary, dict) and summary.get(flag) is True)
    )
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
        "phase_count": len(phase_names),
        "phase_names": phase_names,
        "checkpoint_drift_ok": bool(summary.get("checkpoint_drift_ok"))
        if isinstance(summary, dict)
        else False,
        "checkpoint_monotonicity_ok": bool(summary.get("checkpoint_monotonicity_ok"))
        if isinstance(summary, dict)
        else False,
        "opensearch_to_steelsearch_passed": bool(
            summary.get("opensearch_to_steelsearch_passed")
        )
        if isinstance(summary, dict)
        else False,
        "retention_lease_metadata_ok": bool(summary.get("retention_lease_metadata_ok"))
        if isinstance(summary, dict)
        else False,
        "steelsearch_to_opensearch_passed": bool(
            summary.get("steelsearch_to_opensearch_passed")
        )
        if isinstance(summary, dict)
        else False,
        "transport_log_ok": bool(summary.get("transport_log_ok"))
        if isinstance(summary, dict)
        else False,
        "unsupported_allocation_explain_ok": bool(
            summary.get("unsupported_allocation_explain_ok")
        )
        if isinstance(summary, dict)
        else False,
        "required_summary_flags": sorted(REQUIRED_SHARD_MOVEMENT_SUMMARY_FLAGS),
        "failed_required_summary_flags": failed_required_summary_flags,
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
