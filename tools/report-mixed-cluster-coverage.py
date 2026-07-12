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
DEFAULT_SHARD_MOVEMENT = ROOT / "target/three-node-shard-movement-interruption-current/report.json"
DEFAULT_TRANSPORT_ADMIN = (
    ROOT
    / "target/phase-a-acceptance-harness/transport-admin-validation-current/compare/multi-node-transport-admin-report.json"
)
REQUIRED_REMOTE_PIT_CASES = {
    "node_a_open_pit",
    "node_b_search_node_a_pit",
    "node_b_close_node_a_pit",
    "node_b_search_node_a_pit_after_close",
    "node_a_list_pits_after_node_b_close",
}
REQUIRED_PUBLICATION_VALIDATION_EVENTS = {
    ("proposal", "connect", "passed"),
    ("proposal", "action_frame", "passed"),
    ("proposal", "publication_semantics", "passed"),
    ("apply", "connect", "passed"),
    ("apply", "action_frame", "passed"),
    ("apply", "publication_semantics", "passed"),
}
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
        "publication-repeated-diff-monotonicity-report.json",
        "publication-reachable-catch-up-report.json",
        "publication-scheduled-catch-up-report.json",
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
    "publication": {
        "publication_full_state_receive_apply_replaces_local_cache",
        "publication_diff_apply_acknowledges_only_after_successful_apply",
        "publication_reject_integration_preserves_cache_and_withholds_ack",
        "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
        "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
        "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
    },
}
REQUIRED_PUBLICATION_STAGES = {
    "full_state_decode",
    "local_cache_replace",
    "apply_ack",
    "diff_decode",
    "diff_apply",
    "apply_ack_after_success",
    "reject_detected",
    "cache_preserved",
    "ack_withheld",
    "repeated_diff_decode",
    "monotonic_version_required",
    "stale_round_rejected",
    "lagging_follower_detected",
    "reachable_catch_up_applied",
    "retry_suppressed",
    "catch_up_scheduled_with_backoff",
    "node_left_retry_after_backoff",
}
REQUIRED_SHARD_MOVEMENT_SUMMARY_FLAGS = {
    "checkpoint_drift_ok",
    "checkpoint_monotonicity_ok",
    "interruption_evidence_ok",
    "interruption_evidence_required",
    "opensearch_to_steelsearch_passed",
    "retention_lease_metadata_ok",
    "steelsearch_to_opensearch_passed",
    "transport_log_ok",
    "unsupported_allocation_explain_ok",
}
REQUIRED_SHARD_MOVEMENT_PHASES = {
    "cluster_formed",
    "unsupported_allocation_explain",
    "initial_primary_on_java1",
    "replica_on_rust",
    "opensearch_to_steelsearch",
    "java1_rejoined_as_replica",
    "steelsearch_to_opensearch",
}
REQUIRED_SHARD_MOVEMENT_INTERRUPTION_PHASES = {
    "interrupt_java_to_steelsearch_recovery",
    "resume_or_restart_java_to_steelsearch_recovery",
    "finalize_java_to_steelsearch_recovery",
    "interrupt_steelsearch_to_opensearch_recovery",
    "resume_or_restart_steelsearch_to_opensearch_recovery",
    "finalize_steelsearch_to_opensearch_recovery",
}
REQUIRED_SHARD_MOVEMENT_PHASE_FIELDS = {
    "cluster_formed": {"node_count"},
    "unsupported_allocation_explain": {"allocation_explain"},
    "initial_primary_on_java1": {"placement", "search_count", "shards"},
    "replica_on_rust": {"placement", "cluster_health", "search_count", "shards"},
    "opensearch_to_steelsearch": {"passed", "placement", "search_count", "shards"},
    "java1_rejoined_as_replica": {"placement", "cluster_health"},
    "steelsearch_to_opensearch": {"passed", "placement", "search_count", "shards"},
    "interrupt_java_to_steelsearch_recovery": {"placement", "recovery", "checkpoint_drift"},
    "resume_or_restart_java_to_steelsearch_recovery": {"placement", "recovery", "checkpoint_drift"},
    "finalize_java_to_steelsearch_recovery": {
        "placement",
        "recovery",
        "cluster_health",
        "checkpoint_drift",
    },
    "interrupt_steelsearch_to_opensearch_recovery": {"placement", "recovery", "checkpoint_drift"},
    "resume_or_restart_steelsearch_to_opensearch_recovery": {
        "placement",
        "recovery",
        "checkpoint_drift",
    },
    "finalize_steelsearch_to_opensearch_recovery": {
        "placement",
        "recovery",
        "cluster_health",
        "checkpoint_drift",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-c-root", default=str(DEFAULT_PHASE_C_ROOT))
    parser.add_argument("--shard-movement-report", default=str(DEFAULT_SHARD_MOVEMENT))
    parser.add_argument("--transport-admin-report", default=str(DEFAULT_TRANSPORT_ADMIN))
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
        "failure_java_node_loss": inspect_report(phase_c_root / "failure/java-node-loss-report.json", args.max_report_age_seconds),
        "failure_steelsearch_node_loss_publication": inspect_report(phase_c_root / "failure/steelsearch-node-loss-publication-report.json", args.max_report_age_seconds),
        "failure_steelsearch_node_loss_recovery": inspect_report(phase_c_root / "failure/steelsearch-node-loss-recovery-report.json", args.max_report_age_seconds),
        "write_replication": inspect_report(phase_c_root / "write-replication/mixed-cluster-write-replication-report.json", args.max_report_age_seconds),
        "publication": inspect_report(phase_c_root / "publication/mixed-cluster-publication-report.json", args.max_report_age_seconds),
        "allocation": inspect_report(phase_c_root / "allocation/mixed-cluster-allocation-report.json", args.max_report_age_seconds),
    }
    shard_movement = inspect_shard_movement(Path(args.shard_movement_report), args.max_report_age_seconds)
    transport_admin = inspect_transport_admin(
        Path(args.transport_admin_report), args.max_report_age_seconds
    )
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
    errors.extend(
        f"{name} report missing required publication stages: {missing}"
        for name, report in reports.items()
        if (missing := report["missing_required_publication_stages"])
    )
    errors.extend(
        f"{name} report missing child publication stage map"
        for name, report in reports.items()
        if report["missing_child_publication_stages"]
    )
    errors.extend(
        f"{name} report publication stages do not match child reports"
        for name, report in reports.items()
        if report["publication_stages_child_mismatch"]
    )
    if not shard_movement["passed"]:
        errors.append("shard movement report is missing or not passed")
    if not transport_admin["passed"]:
        errors.append("transport admin report is missing or not passed")
    if transport_admin["missing_remote_pit_cases"]:
        errors.append(
            "transport admin report missing remote PIT cases: "
            f"{transport_admin['missing_remote_pit_cases']}"
        )
    if transport_admin["failed_remote_pit_cases"]:
        errors.append(
            "transport admin report has failed remote PIT cases: "
            f"{transport_admin['failed_remote_pit_cases']}"
        )
    if transport_admin["remote_pit_semantic_errors"]:
        errors.append(
            "transport admin report has remote PIT semantic errors: "
            f"{transport_admin['remote_pit_semantic_errors']}"
        )
    if transport_admin["publication_validation_errors"]:
        errors.append(
            "transport admin report has publication validation errors: "
            f"{transport_admin['publication_validation_errors']}"
        )
    if shard_movement["failed_required_summary_flags"]:
        errors.append(
            "shard movement report has failed required summary flags: "
            f"{shard_movement['failed_required_summary_flags']}"
        )
    if shard_movement["missing_required_phases"]:
        errors.append(
            "shard movement report missing required phases: "
            f"{shard_movement['missing_required_phases']}"
        )
    if shard_movement["duplicate_required_phases"]:
        errors.append(
            "shard movement report has duplicate required phases: "
            f"{shard_movement['duplicate_required_phases']}"
        )
    if shard_movement["phase_assertion_errors"]:
        errors.append(
            "shard movement report has incomplete required phase evidence: "
            f"{shard_movement['phase_assertion_errors']}"
        )
    errors.extend(
        freshness_error(f"{name} report", report)
        for name, report in reports.items()
        if not report["fresh"]
    )
    if not shard_movement["fresh"]:
        errors.append(freshness_error("shard movement report", shard_movement))
    if not transport_admin["fresh"]:
        errors.append(freshness_error("transport admin report", transport_admin))
    if not args.require_passed:
        errors = []

    passed_reports = sum(1 for report in reports.values() if report["passed"])
    publication_report = reports["publication"]
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
            "failure_node_loss_report_count": 3,
            "failure_node_loss_passed_report_count": sum(
                1
                for name, report in reports.items()
                if name.startswith("failure_") and name != "failure" and report["passed"]
            ),
            "publication_report_count": len(publication_report["required_checks"]),
            "publication_passed_report_count": sum(
                1
                for check in publication_report["required_checks"]
                if publication_report["checks"].get(check) is True
            ),
            "publication_executed_test_count": len(publication_report["executed_tests"]),
            "publication_required_executed_test_count": len(
                publication_report["required_executed_tests"]
            ),
            "publication_required_executed_tests": publication_report[
                "required_executed_tests"
            ],
            "publication_missing_required_executed_test_count": len(
                publication_report["missing_required_executed_tests"]
            ),
            "publication_stage_count": len(publication_report["publication_stages"]),
            "publication_required_stage_count": len(
                publication_report["required_publication_stages"]
            ),
            "publication_required_stages": publication_report[
                "required_publication_stages"
            ],
            "publication_missing_required_stage_count": len(
                publication_report["missing_required_publication_stages"]
            ),
            "shard_movement_passed": shard_movement["passed"],
            "shard_movement_fresh": shard_movement["fresh"],
            "transport_admin_passed": transport_admin["passed"],
            "transport_admin_fresh": transport_admin["fresh"],
            "transport_admin_remote_pit_case_count": transport_admin[
                "remote_pit_case_count"
            ],
            "transport_admin_publication_validation_event_count": transport_admin[
                "publication_validation_event_count"
            ],
            "transport_admin_publication_validation_observed_events": transport_admin[
                "publication_validation_observed_events"
            ],
            "transport_admin_publication_transcript_count": transport_admin[
                "publication_transcript_count"
            ],
            "shard_movement_phase_count": shard_movement["phase_count"],
            "shard_movement_required_phase_count": len(REQUIRED_SHARD_MOVEMENT_PHASES),
            "shard_movement_required_phases": sorted(REQUIRED_SHARD_MOVEMENT_PHASES),
            "shard_movement_required_interruption_phase_count": len(
                REQUIRED_SHARD_MOVEMENT_INTERRUPTION_PHASES
            ),
            "shard_movement_required_interruption_phases": sorted(
                REQUIRED_SHARD_MOVEMENT_INTERRUPTION_PHASES
            ),
            "shard_movement_missing_required_phase_count": len(
                shard_movement["missing_required_phases"]
            ),
            "shard_movement_phase_assertion_error_count": len(
                shard_movement["phase_assertion_errors"]
            ),
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
                "allocation, write-replication, and interrupted shard movement evidence is present"
            ),
        },
        "reports": reports,
        "shard_movement": shard_movement,
        "transport_admin": transport_admin,
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
    publication_stages = payload.get("publication_stages", []) if isinstance(payload, dict) else []
    publication_stage_names = {str(stage) for stage in publication_stages} if isinstance(publication_stages, list) else set()
    required_publication_stages = required_publication_stages_for(path)
    child_publication_stages = payload.get("child_publication_stages", {}) if isinstance(payload, dict) else {}
    child_publication_stage_names = child_publication_stages_union(child_publication_stages)
    missing_child_publication_stages = bool(required_publication_stages) and not isinstance(
        payload.get("child_publication_stages") if isinstance(payload, dict) else None,
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
    missing_required_publication_stages = sorted(
        required_publication_stages - publication_stage_names
    )
    publication_stages_child_mismatch = (
        bool(child_publication_stage_names)
        and child_publication_stage_names != publication_stage_names
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
        "publication_stages": sorted(publication_stage_names),
        "child_publication_stages": child_publication_stages if isinstance(child_publication_stages, dict) else {},
        "child_publication_stages_union": sorted(child_publication_stage_names),
        "required_publication_stages": sorted(required_publication_stages),
        "missing_required_publication_stages": missing_required_publication_stages,
        "missing_child_publication_stages": missing_child_publication_stages,
        "publication_stages_child_mismatch": publication_stages_child_mismatch,
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
    if normalized.endswith("/publication/mixed-cluster-publication-report.json"):
        return REQUIRED_EXECUTED_TESTS["publication"]
    return set()


def required_publication_stages_for(path: Path) -> set[str]:
    if path.as_posix().endswith("/publication/mixed-cluster-publication-report.json"):
        return REQUIRED_PUBLICATION_STAGES
    return set()


def child_executed_tests_union(child_executed_tests: Any) -> set[str]:
    if not isinstance(child_executed_tests, dict):
        return set()
    names: set[str] = set()
    for value in child_executed_tests.values():
        if isinstance(value, list):
            names.update(str(test) for test in value)
    return names


def child_publication_stages_union(child_publication_stages: Any) -> set[str]:
    if not isinstance(child_publication_stages, dict):
        return set()
    names: set[str] = set()
    for value in child_publication_stages.values():
        if isinstance(value, list):
            names.update(str(stage) for stage in value)
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
    required_phases = REQUIRED_SHARD_MOVEMENT_PHASES | REQUIRED_SHARD_MOVEMENT_INTERRUPTION_PHASES
    missing_required_phases = sorted(required_phases - set(phase_names))
    duplicate_required_phases = sorted(
        phase_name
        for phase_name in required_phases
        if phase_names.count(phase_name) > 1
    )
    phases_by_name = {
        str(phase.get("phase")): phase
        for phase in phases
        if isinstance(phase, dict) and phase.get("phase")
    } if isinstance(phases, list) else {}
    phase_assertion_errors = shard_movement_phase_assertion_errors(phases_by_name)
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("passed") is True,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
        "phase_count": len(phase_names),
        "phase_names": phase_names,
        "required_phases": sorted(required_phases),
        "required_interruption_phases": sorted(REQUIRED_SHARD_MOVEMENT_INTERRUPTION_PHASES),
        "missing_required_phases": missing_required_phases,
        "duplicate_required_phases": duplicate_required_phases,
        "phase_assertion_errors": phase_assertion_errors,
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


def inspect_transport_admin(path: Path, max_age_seconds: float | None = None) -> dict[str, Any]:
    payload = load_json(path)
    freshness = report_fresh(path, max_age_seconds)
    summary = payload.get("summary") if isinstance(payload, dict) else {}
    case_statuses = transport_admin_case_statuses(payload)
    missing_remote_pit_cases = sorted(REQUIRED_REMOTE_PIT_CASES - set(case_statuses))
    failed_remote_pit_cases = sorted(
        name
        for name in REQUIRED_REMOTE_PIT_CASES
        if name in case_statuses and case_statuses.get(name) != "passed"
    )
    remote_pit_semantic_errors = (
        []
        if missing_remote_pit_cases or failed_remote_pit_cases
        else transport_admin_remote_pit_semantic_errors(payload)
    )
    publication_validation = transport_admin_publication_validation(payload)
    return {
        "path": str(path),
        "present": payload is not None,
        "passed": isinstance(summary, dict) and summary.get("failed") == 0,
        "fresh": freshness["fresh"],
        "age_seconds": freshness["age_seconds"],
        "max_age_seconds": freshness["max_age_seconds"],
        "summary": summary if isinstance(summary, dict) else {},
        "remote_pit_case_count": len(REQUIRED_REMOTE_PIT_CASES & set(case_statuses)),
        "missing_remote_pit_cases": missing_remote_pit_cases,
        "failed_remote_pit_cases": failed_remote_pit_cases,
        "remote_pit_semantic_errors": remote_pit_semantic_errors,
        "publication_transcript_count": publication_validation["transcript_count"],
        "publication_validation_event_count": publication_validation["event_count"],
        "publication_validation_observed_events": sorted(
            ".".join(event) for event in publication_validation["observed_events"]
        ),
        "publication_validation_errors": publication_validation["errors"],
    }


def transport_admin_case_statuses(payload: Any) -> dict[str, str]:
    statuses: dict[str, str] = {}
    if not isinstance(payload, dict):
        return statuses
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return statuses
    for case in cases:
        if not isinstance(case, dict):
            continue
        name = case.get("name")
        status = case.get("status")
        if isinstance(name, str) and isinstance(status, str):
            statuses[name] = status
    return statuses


def transport_admin_cases_by_name(payload: Any) -> dict[str, dict[str, Any]]:
    cases_by_name: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, dict):
        return cases_by_name
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return cases_by_name
    for case in cases:
        if not isinstance(case, dict):
            continue
        name = case.get("name")
        if isinstance(name, str):
            cases_by_name[name] = case
    return cases_by_name


def transport_admin_remote_pit_semantic_errors(payload: Any) -> list[str]:
    cases = transport_admin_cases_by_name(payload)
    errors: list[str] = []
    open_body = extract_path(cases.get("node_a_open_pit"), "response.body")
    pit_id = extract_path(open_body, "pit_id")
    if not isinstance(pit_id, str) or not pit_id:
        errors.append("node_a_open_pit did not return a non-empty pit_id")
    if extract_path(open_body, "_shards.failed") != 0:
        errors.append("node_a_open_pit did not report _shards.failed=0")

    search_body = extract_path(cases.get("node_b_search_node_a_pit"), "response.body")
    if extract_path(search_body, "hits.total.value") != 1:
        errors.append("node_b_search_node_a_pit did not return one hit")
    if extract_path(search_body, "hits.hits.0._id") != "doc-1":
        errors.append("node_b_search_node_a_pit did not return doc-1")
    if extract_path(search_body, "hits.hits.0._source.message") != "visible-through-pit":
        errors.append("node_b_search_node_a_pit did not return the PIT document source")
    if pit_id and extract_path(search_body, "pit_id") != pit_id:
        errors.append("node_b_search_node_a_pit returned a different pit_id")

    close_body = extract_path(cases.get("node_b_close_node_a_pit"), "response.body")
    if extract_path(close_body, "pits.0.successful") is not True:
        errors.append("node_b_close_node_a_pit did not close the remote PIT successfully")
    if pit_id and extract_path(close_body, "pits.0.pit_id") != pit_id:
        errors.append("node_b_close_node_a_pit closed a different pit_id")

    after_close_body = extract_path(
        cases.get("node_b_search_node_a_pit_after_close"), "response.body"
    )
    if extract_path(after_close_body, "status") != 404:
        errors.append("node_b_search_node_a_pit_after_close did not return status=404")
    if extract_path(after_close_body, "error.type") != "search_phase_execution_exception":
        errors.append(
            "node_b_search_node_a_pit_after_close did not return search_phase_execution_exception"
        )

    list_body = extract_path(cases.get("node_a_list_pits_after_node_b_close"), "response.body")
    if extract_path(list_body, "pits") != []:
        errors.append("node_a_list_pits_after_node_b_close did not return an empty pits list")
    return errors


def transport_admin_publication_validation(payload: Any) -> dict[str, Any]:
    errors: list[str] = []
    transcripts = extract_path(payload, "coordination.publication_transport_transcripts")
    if not isinstance(transcripts, list) or not transcripts:
        return {
            "transcript_count": 0,
            "event_count": 0,
            "observed_events": set(),
            "errors": ["coordination publication transport transcripts are missing"],
        }

    observed_events: set[tuple[str, str, str]] = set()
    event_count = 0
    for index, transcript in enumerate(transcripts):
        if not isinstance(transcript, dict):
            errors.append(f"publication transcript {index} is not an object")
            continue
        events = transcript.get("validation_events")
        if not isinstance(events, list) or not events:
            errors.append(f"publication transcript {index} has no validation_events")
            continue
        for event in events:
            key = publication_validation_event_key(event)
            if key is None:
                errors.append(f"publication transcript {index} has malformed validation event")
                continue
            node_id = event.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"publication transcript {index} validation event is missing node_id")
            if key[2] == "failed":
                reason = event.get("reason")
                if not isinstance(reason, str) or not reason:
                    errors.append(
                        f"publication transcript {index} failed validation event is missing reason"
                    )
            observed_events.add(key)
            event_count += 1

    missing = sorted(REQUIRED_PUBLICATION_VALIDATION_EVENTS - observed_events)
    if missing:
        errors.append(f"missing publication validation event kinds: {missing}")
    if event_count < len(REQUIRED_PUBLICATION_VALIDATION_EVENTS):
        errors.append("publication validation event count is too small")
    return {
        "transcript_count": len(transcripts),
        "event_count": event_count,
        "observed_events": observed_events,
        "errors": errors,
    }


def publication_validation_event_key(event: Any) -> tuple[str, str, str] | None:
    if not isinstance(event, dict):
        return None
    phase = event.get("phase")
    step = event.get("step")
    status = event.get("status")
    if not all(isinstance(value, str) for value in (phase, step, status)):
        return None
    return phase, step, status


def extract_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def shard_movement_phase_assertion_errors(phases_by_name: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for phase_name, required_fields in sorted(REQUIRED_SHARD_MOVEMENT_PHASE_FIELDS.items()):
        phase = phases_by_name.get(phase_name)
        if not isinstance(phase, dict):
            continue
        missing_fields = sorted(
            field
            for field in required_fields
            if field not in phase or phase.get(field) in (None, [], {})
        )
        if missing_fields:
            errors.append(f"{phase_name}: missing fields {missing_fields}")
        if phase.get("passed") is False:
            errors.append(f"{phase_name}: passed is false")
        if "search_count" in required_fields:
            search_count = phase.get("search_count")
            if not isinstance(search_count, int) or search_count <= 0:
                errors.append(f"{phase_name}: search_count must be a positive integer")
        if "cluster_health" in required_fields:
            cluster_health = phase.get("cluster_health")
            if not isinstance(cluster_health, dict) or cluster_health.get("status") != "green":
                errors.append(f"{phase_name}: cluster_health.status must be green")
        if "placement" in required_fields:
            placement = phase.get("placement")
            if not isinstance(placement, dict) or placement.get("primary_state") != "STARTED":
                errors.append(f"{phase_name}: placement.primary_state must be STARTED")
    return errors


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
