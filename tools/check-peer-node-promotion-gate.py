#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


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
        },
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
            "publication-reject-report.json",
        },
    ),
    "allocation": (
        "allocation/mixed-cluster-allocation-report.json",
        {"routing_convergence_probe_passed", "allocation_reject_passed"},
    ),
}


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
    return parser.parse_args()


def load_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        fail(f"required report is missing: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_phase_c_summary(path: str) -> dict:
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
    child_reports = validate_phase_c_child_reports(phase_c_root)
    return {
        "report": str(path),
        "child_reports": child_reports,
        "classes": ["publication-ordering", "peer-recovery", "mixed-write-replication"],
    }


def validate_phase_c_child_reports(phase_c_root: Path) -> dict:
    validated = {}
    for name, (relative_path, required_checks) in PHASE_C_CHILD_REPORTS.items():
        path = phase_c_root / relative_path
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
        validated[name] = {
            "report": str(path),
            "required_checks": sorted(required_checks),
        }
    return validated


def validate_rolling_report(path: str) -> dict:
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


def validate_durability_reports(paths: list[str]) -> dict:
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

    phase_c = validate_phase_c_summary(args.phase_c_summary)
    rolling = validate_rolling_report(args.rolling_report)
    durability_reports = validate_durability_reports(args.durability_report)
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
