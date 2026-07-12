#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path
from typing import Any


EXPECTED_DURABILITY = {
    "peer-recovery",
    "mixed-write-replication",
    "durability-convergence",
}

EXPECTED_DISTRIBUTED = {
    "quorum-evidence",
    "publication-ordering",
    "rolling-stability-transcript",
    "leader-failover",
    "seed-loss-recovery",
}

EXPECTED_DURABILITY_REPORTS = {
    "target/phase-c-mixed-cluster/phase-c-mixed-cluster-summary.json",
    "target/distributed-durability-convergence/primary-relocation/report.json",
    "target/distributed-durability-convergence/replica-catchup/report.json",
    "target/distributed-durability-convergence/node-left-delayed-allocation/report.json",
}

EXPECTED_DISTRIBUTED_REPORTS = {
    "target/phase-c-mixed-cluster/phase-c-mixed-cluster-summary.json",
    "target/rolling-stability/rolling-restart/report.json",
}

EXPECTED_LATEST_REPORTS = EXPECTED_DURABILITY_REPORTS | EXPECTED_DISTRIBUTED_REPORTS

PHASE_C_CHILD_REPORTS = {
    "join": (
        "join/mixed-cluster-join-report.json",
        {"live_join_probe_passed", "join_reject_passed"},
    ),
    "live_join_probe": (
        "join/live-join-probe-report.json",
        {
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
    ),
    "recovery": (
        "recovery/mixed-cluster-recovery-report.json",
        {"bounded_peer_recovery_probe_passed", "recovery_reject_passed"},
    ),
    "bounded_recovery_probe": (
        "recovery/bounded-peer-recovery-probe-report.json",
        {"wire_round_trip_passed"},
    ),
    "failure": (
        "failure/mixed-cluster-failure-report.json",
        {
            "failure_topology_probe_passed",
            "failure_ledger_passed",
            "pit_restart_lifecycle_passed",
            "pit_transport_restart_lifecycle_passed",
            "pit_multi_daemon_lifecycle_passed",
            "java_node_loss_passed",
            "steelsearch_node_loss_publication_passed",
            "steelsearch_node_loss_recovery_passed",
        },
    ),
    "failure_java_node_loss": (
        "failure/java-node-loss-report.json",
        {"java_node_loss_fail_closed_passed"},
    ),
    "failure_steelsearch_node_loss_publication": (
        "failure/steelsearch-node-loss-publication-report.json",
        {"steelsearch_node_loss_publication_fencing_passed"},
    ),
    "failure_steelsearch_node_loss_recovery": (
        "failure/steelsearch-node-loss-recovery-report.json",
        {"steelsearch_node_loss_recovery_fencing_passed"},
    ),
    "write_replication": (
        "write-replication/mixed-cluster-write-replication-report.json",
        {"write_replication_happy_path_passed", "write_replication_reject_passed"},
    ),
    "publication": (
        "publication/mixed-cluster-publication-report.json",
        {
            "publication-full-state-report.json",
            "publication-diff-ack-report.json",
            "publication-reachable-catch-up-report.json",
            "publication-reject-report.json",
            "publication-repeated-diff-monotonicity-report.json",
            "publication-scheduled-catch-up-report.json",
        },
    ),
    "allocation": (
        "allocation/mixed-cluster-allocation-report.json",
        {"routing_convergence_probe_passed", "allocation_reject_passed"},
    ),
}

EXPECTED_FAILURE_EXECUTED_TESTS = (
    "daemon_point_in_time_contexts_do_not_survive_restart",
    "daemon_transport_point_in_time_contexts_do_not_survive_restart",
    "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
    "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    "publication_reject_integration_preserves_cache_and_withholds_ack",
    "shard_search_request_to_unavailable_node_returns_io_error",
)

EXPECTED_FAILURE_CHILD_EXECUTED_TESTS = {
    "pit_restart_lifecycle_report": (
        "daemon_point_in_time_contexts_do_not_survive_restart",
    ),
    "pit_transport_restart_lifecycle_report": (
        "daemon_transport_point_in_time_contexts_do_not_survive_restart",
    ),
    "pit_multi_daemon_lifecycle_report": (
        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    ),
    "java_node_loss_report": (
        "shard_search_request_to_unavailable_node_returns_io_error",
    ),
    "steelsearch_node_loss_publication_report": (
        "publication_reject_integration_preserves_cache_and_withholds_ack",
    ),
    "steelsearch_node_loss_recovery_report": (
        "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
    ),
}

EXPECTED_FAILURE_JAVA_NODE_LOSS_EXECUTED_TESTS = (
    "shard_search_request_to_unavailable_node_returns_io_error",
)

EXPECTED_FAILURE_STEELSEARCH_NODE_LOSS_PUBLICATION_EXECUTED_TESTS = (
    "publication_reject_integration_preserves_cache_and_withholds_ack",
)

EXPECTED_FAILURE_STEELSEARCH_NODE_LOSS_RECOVERY_EXECUTED_TESTS = (
    "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
)

EXPECTED_PUBLICATION_EXECUTED_TESTS = (
    "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
    "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
    "publication_diff_apply_acknowledges_only_after_successful_apply",
    "publication_full_state_receive_apply_replaces_local_cache",
    "publication_reject_integration_preserves_cache_and_withholds_ack",
    "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
)

EXPECTED_PUBLICATION_CHILD_EXECUTED_TESTS = {
    "publication-diff-ack-report.json": (
        "publication_diff_apply_acknowledges_only_after_successful_apply",
    ),
    "publication-full-state-report.json": (
        "publication_full_state_receive_apply_replaces_local_cache",
    ),
    "publication-reachable-catch-up-report.json": (
        "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
    ),
    "publication-reject-report.json": (
        "publication_reject_integration_preserves_cache_and_withholds_ack",
    ),
    "publication-repeated-diff-monotonicity-report.json": (
        "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
    ),
    "publication-scheduled-catch-up-report.json": (
        "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
    ),
}

EXPECTED_RECOVERY_EXECUTED_TESTS = (
    "bounded_peer_recovery_wire_round_trip_probe",
    "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
)

EXPECTED_RECOVERY_CHILD_EXECUTED_TESTS = {
    "bounded_peer_recovery_probe_report": (
        "bounded_peer_recovery_wire_round_trip_probe",
    ),
    "recovery_reject_report": (
        "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
    ),
}

EXPECTED_WRITE_REPLICATION_EXECUTED_TESTS = (
    "mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior",
    "replica_operation_tcp_round_trip_preserves_replication_progress_metadata",
)

EXPECTED_WRITE_REPLICATION_CHILD_EXECUTED_TESTS = {
    "write_replication_happy_path_report": (
        "replica_operation_tcp_round_trip_preserves_replication_progress_metadata",
    ),
    "write_replication_reject_report": (
        "mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior",
    ),
}

EXPECTED_JOIN_EXECUTED_TESTS = (
    "mixed_cluster_live_join_probe",
    "mixed_cluster_join_reject_fixture_matches_validator_behavior",
)

EXPECTED_JOIN_CHILD_EXECUTED_TESTS = {
    "live_join_probe_report": (
        "mixed_cluster_live_join_probe",
    ),
    "join_reject_report": (
        "mixed_cluster_join_reject_fixture_matches_validator_behavior",
    ),
}

EXPECTED_ALLOCATION_EXECUTED_TESTS = (
    "mixed_cluster_allocation_routing_convergence_probe",
    "mixed_cluster_allocation_fail_closed_fixture_matches_validator_behavior",
)

EXPECTED_ALLOCATION_CHILD_EXECUTED_TESTS = {
    "routing_convergence_probe_report": (
        "mixed_cluster_allocation_routing_convergence_probe",
    ),
    "allocation_reject_report": (
        "mixed_cluster_allocation_fail_closed_fixture_matches_validator_behavior",
    ),
}

EXPECTED_LIVE_JOIN_PROBE_EXECUTED_TESTS = (
    "mixed_cluster_live_join_probe",
)

EXPECTED_BOUNDED_RECOVERY_PROBE_EXECUTED_TESTS = (
    "bounded_peer_recovery_wire_round_trip_probe",
)


def fail(message: str) -> None:
    raise SystemExit(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate peer-node promotion gate evidence.")
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/peer-node-promotion-gate.json",
    )
    parser.add_argument(
        "--phase-c-summary",
        default="target/phase-c-mixed-cluster/phase-c-mixed-cluster-summary.json",
        help="Phase-C mixed-cluster summary report.",
    )
    parser.add_argument(
        "--rolling-report",
        default="target/rolling-stability/rolling-restart/report.json",
        help="Rolling stability report.",
    )
    parser.add_argument(
        "--durability-report",
        action="append",
        default=[],
        help="Distributed durability convergence report. Repeatable.",
    )
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="Fail if any required peer-node evidence report is older than this many seconds.",
    )
    return parser.parse_args()


def load_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        fail(f"required report is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def report_fresh(path: str | Path, max_age_seconds: float | None) -> dict[str, Any]:
    path = Path(path)
    if max_age_seconds is None:
        return {"fresh": True, "age_seconds": None, "max_age_seconds": None}
    if not path.exists():
        return {"fresh": False, "age_seconds": None, "max_age_seconds": max_age_seconds}
    age_seconds = max(0.0, time.time() - path.stat().st_mtime)
    return {
        "fresh": age_seconds <= max_age_seconds,
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_seconds,
    }


def require_fresh(path: str | Path, label: str, max_age_seconds: float | None) -> None:
    freshness = report_fresh(path, max_age_seconds)
    if freshness["fresh"]:
        return
    if freshness["age_seconds"] is None:
        fail(f"{label} report is missing: {path}")
    fail(
        f"{label} report is stale: age_seconds={freshness['age_seconds']:.0f} "
        f"max_age_seconds={freshness['max_age_seconds']:.0f}"
    )


def validate_phase_c_summary(path: str, max_report_age_seconds: float | None = None) -> dict:
    require_fresh(path, "phase-c summary", max_report_age_seconds)
    report = load_json(path)
    if not report.get("summary", {}).get("passed"):
        fail("phase-c mixed-cluster summary did not pass")
    phase_c_root = Path(path).parent
    required_reports = {
        "generated-api-spec-report.json",
        "mixed-cluster-allocation-report.json",
        "mixed-cluster-failure-report.json",
        "mixed-cluster-join-report.json",
        "mixed-cluster-publication-report.json",
        "mixed-cluster-recovery-report.json",
        "mixed-cluster-write-replication-report.json",
    }
    observed = report.get("reports") or {}
    missing = sorted(required_reports - set(observed))
    failed = sorted(name for name, passed in observed.items() if not passed)
    if missing:
        fail(f"phase-c summary missing reports: {missing}")
    if failed:
        fail(f"phase-c summary has failed reports: {failed}")
    child_reports = validate_phase_c_child_reports(phase_c_root, max_report_age_seconds)
    return {
        "report": str(path),
        "child_reports": child_reports,
        "classes": ["publication-ordering", "peer-recovery", "mixed-write-replication"],
    }


def validate_phase_c_child_reports(
    phase_c_root: Path,
    max_report_age_seconds: float | None = None,
) -> dict:
    validated = {}
    for name, (relative_path, required_checks) in PHASE_C_CHILD_REPORTS.items():
        path = phase_c_root / relative_path
        require_fresh(path, f"phase-c {name}", max_report_age_seconds)
        child = load_json(path)
        if not child.get("summary", {}).get("passed"):
            fail(f"phase-c child report did not pass: {relative_path}")
        checks = child.get("checks") or {}
        missing = sorted(required_checks - set(checks))
        failed = sorted(
            check for check in required_checks if check in checks and checks.get(check) is not True
        )
        if missing:
            fail(f"phase-c child report missing checks for {name}: {missing}")
        if failed:
            fail(f"phase-c child report failed checks for {name}: {failed}")
        if name == "live_join_probe":
            validate_live_join_probe_report(child)
        if name == "join":
            validate_join_child_report(child)
        if name == "bounded_recovery_probe":
            validate_bounded_recovery_probe_report(child)
        if name == "failure":
            validate_failure_child_report(child)
        if name == "failure_java_node_loss":
            validate_node_loss_child_report(
                child,
                EXPECTED_FAILURE_JAVA_NODE_LOSS_EXECUTED_TESTS,
                "java node loss",
            )
        if name == "failure_steelsearch_node_loss_publication":
            validate_node_loss_child_report(
                child,
                EXPECTED_FAILURE_STEELSEARCH_NODE_LOSS_PUBLICATION_EXECUTED_TESTS,
                "steelsearch node loss publication",
            )
        if name == "failure_steelsearch_node_loss_recovery":
            validate_node_loss_child_report(
                child,
                EXPECTED_FAILURE_STEELSEARCH_NODE_LOSS_RECOVERY_EXECUTED_TESTS,
                "steelsearch node loss recovery",
            )
        if name == "recovery":
            validate_recovery_child_report(child)
        if name == "publication":
            validate_publication_child_report(child)
        if name == "write_replication":
            validate_write_replication_child_report(child)
        if name == "allocation":
            validate_allocation_child_report(child)
        validated[name] = {
            "report": str(path),
            "required_checks": sorted(required_checks),
        }
    return validated


def validate_failure_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_FAILURE_EXECUTED_TESTS:
        fail("phase-c failure executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_FAILURE_CHILD_EXECUTED_TESTS:
        fail("phase-c failure child executed tests do not match current baseline")


def validate_node_loss_child_report(
    child: dict,
    expected: tuple[str, ...],
    label: str,
) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != expected:
        fail(f"phase-c {label} executed tests do not match current baseline")


def validate_publication_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_PUBLICATION_EXECUTED_TESTS:
        fail("phase-c publication executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_PUBLICATION_CHILD_EXECUTED_TESTS:
        fail("phase-c publication child executed tests do not match current baseline")


def validate_recovery_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_RECOVERY_EXECUTED_TESTS:
        fail("phase-c recovery executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_RECOVERY_CHILD_EXECUTED_TESTS:
        fail("phase-c recovery child executed tests do not match current baseline")


def validate_write_replication_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_WRITE_REPLICATION_EXECUTED_TESTS:
        fail("phase-c write replication executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_WRITE_REPLICATION_CHILD_EXECUTED_TESTS:
        fail("phase-c write replication child executed tests do not match current baseline")


def validate_join_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_JOIN_EXECUTED_TESTS:
        fail("phase-c join executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_JOIN_CHILD_EXECUTED_TESTS:
        fail("phase-c join child executed tests do not match current baseline")


def validate_allocation_child_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_ALLOCATION_EXECUTED_TESTS:
        fail("phase-c allocation executed tests do not match current baseline")
    child_executed = child.get("child_executed_tests") or {}
    observed = {
        name: tuple(tests or [])
        for name, tests in child_executed.items()
    }
    if observed != EXPECTED_ALLOCATION_CHILD_EXECUTED_TESTS:
        fail("phase-c allocation child executed tests do not match current baseline")


def validate_live_join_probe_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_LIVE_JOIN_PROBE_EXECUTED_TESTS:
        fail("phase-c live join probe executed tests do not match current baseline")


def validate_bounded_recovery_probe_report(child: dict) -> None:
    executed = tuple(child.get("executed_tests") or ())
    if executed != EXPECTED_BOUNDED_RECOVERY_PROBE_EXECUTED_TESTS:
        fail("phase-c bounded recovery probe executed tests do not match current baseline")


def validate_rolling_report(path: str, max_report_age_seconds: float | None = None) -> dict:
    require_fresh(path, "rolling stability", max_report_age_seconds)
    report = load_json(path)
    if report.get("status") != "completed":
        fail("rolling stability report is not completed")
    steps = report.get("steps") or []
    transcript = report.get("stability_transcript") or []
    if len(steps) != len(transcript):
        fail("rolling stability transcript length does not match steps")
    if not steps:
        fail("rolling stability report has no steps")
    for entry in transcript:
        stability = entry.get("stability") or {}
        if stability.get("ready") is not True:
            fail(f"rolling stability step is not ready: {entry.get('step')}")
        if stability.get("node_count") != 3:
            fail(f"rolling stability step does not show three nodes: {entry.get('step')}")
        if stability.get("required_quorum") != 2:
            fail(f"rolling stability step does not show quorum=2: {entry.get('step')}")
    return {
        "report": str(path),
        "classes": ["quorum-evidence", "rolling-stability-transcript", "leader-failover", "seed-loss-recovery"],
    }


def validate_durability_reports(
    paths: list[str],
    max_report_age_seconds: float | None = None,
) -> dict:
    if not paths:
        paths = [
            "target/distributed-durability-convergence/primary-relocation/report.json",
            "target/distributed-durability-convergence/replica-catchup/report.json",
            "target/distributed-durability-convergence/node-left-delayed-allocation/report.json",
        ]
    expected_profiles = {
        "primary-relocation",
        "replica-catchup",
        "node-left-delayed-allocation",
    }
    observed_profiles = set()
    for path in paths:
        require_fresh(path, "durability", max_report_age_seconds)
        report = load_json(path)
        profile = report.get("profile")
        observed_profiles.add(profile)
        if report.get("status") != "completed":
            fail(f"durability report is not completed: {path}")
        if report.get("data_checksum_ok") is not True:
            fail(f"durability report data checksum failed: {path}")
        if report.get("doc_visibility_ok") is not True:
            fail(f"durability report doc visibility failed: {path}")
        if report.get("finalize_phase") != "completed":
            fail(f"durability report finalize phase is not completed: {path}")
    missing = sorted(expected_profiles - observed_profiles)
    if missing:
        fail(f"durability reports missing profiles: {missing}")
    return {
        "reports": [str(path) for path in paths],
        "classes": ["durability-convergence"],
    }


def main() -> None:
    args = parse_args()
    data = load_json(args.fixture)

    if data.get("source_area") != "Steelsearch multi-node runtime":
        fail("unexpected source_area")
    if data.get("profile") != "same-cluster-peer":
        fail("unexpected profile")

    matrix = data.get("matrix_expectation", {})
    if matrix.get("open_search_api_compatibility") != "Implemented":
        fail("open_search_api_compatibility must be Implemented")
    if matrix.get("semantic_parity") != "Implemented":
        fail("semantic_parity must be Implemented")
    if matrix.get("production_readiness") != "Yes":
        fail("production_readiness must be Yes")

    sections = data.get("unified_report_sections", {})
    durability = sections.get("durability_parity")
    distributed = sections.get("distributed_parity")
    if not durability or not distributed:
        fail("durability_parity and distributed_parity required")
    if durability.get("suite") != "same-cluster-peer":
        fail("durability suite mismatch")
    if distributed.get("suite") != "same-cluster-peer":
        fail("distributed suite mismatch")
    if set(durability.get("required_evidence_classes", [])) != EXPECTED_DURABILITY:
        fail("durability evidence mismatch")
    if set(distributed.get("required_evidence_classes", [])) != EXPECTED_DISTRIBUTED:
        fail("distributed evidence mismatch")
    if set(durability.get("required_reports", [])) != EXPECTED_DURABILITY_REPORTS:
        fail("durability reports mismatch")
    if set(distributed.get("required_reports", [])) != EXPECTED_DISTRIBUTED_REPORTS:
        fail("distributed reports mismatch")

    latest = data.get("latest_standalone_gate") or {}
    if set(latest.get("required_reports", [])) != EXPECTED_LATEST_REPORTS:
        fail("latest gate required_reports mismatch")

    phase_c = validate_phase_c_summary(args.phase_c_summary, args.max_report_age_seconds)
    rolling = validate_rolling_report(args.rolling_report, args.max_report_age_seconds)
    durability_reports = validate_durability_reports(
        args.durability_report,
        args.max_report_age_seconds,
    )
    observed_classes = set(phase_c["classes"]) | set(rolling["classes"]) | set(durability_reports["classes"])
    expected_classes = EXPECTED_DURABILITY | EXPECTED_DISTRIBUTED
    missing_classes = sorted(expected_classes - observed_classes)
    if missing_classes:
        fail(f"missing evidence classes from executed reports: {missing_classes}")

    print(
        json.dumps(
            {
                "source_area": data["source_area"],
                "profile": data["profile"],
                "phase_c": phase_c,
                "rolling": rolling,
                "durability": durability_reports,
                "evidence_classes": sorted(observed_classes),
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
