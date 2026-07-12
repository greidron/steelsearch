import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-peer-node-promotion-gate.py"


def load_checker_module():
    module_name = "check_peer_node_promotion_gate"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PeerNodePromotionGateTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_phase_c_summary_requires_child_report_checks(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)

            result = self.checker.validate_phase_c_summary(
                str(phase_c_root / "phase-c-mixed-cluster-summary.json")
            )

            self.assertIn("child_reports", result)
            self.assertEqual(
                set(result["child_reports"]),
                {
                    "join",
                    "live_join_probe",
                    "recovery",
                    "bounded_recovery_probe",
                    "failure",
                    "write_replication",
                    "publication",
                    "allocation",
                },
            )

    def test_phase_c_summary_rejects_missing_child_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            join_report = phase_c_root / "join/mixed-cluster-join-report.json"
            join_report.write_text(
                json.dumps(
                    {
                        "summary": {"passed": True},
                        "checks": {"live_join_probe_passed": True},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "missing checks for join"):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_failure_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            failure_report = phase_c_root / "failure/mixed-cluster-failure-report.json"
            payload = json.loads(failure_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = [
                "daemon_point_in_time_contexts_do_not_survive_restart"
            ]
            failure_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c failure executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_failure_child_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            failure_report = phase_c_root / "failure/mixed-cluster-failure-report.json"
            payload = json.loads(failure_report.read_text(encoding="utf-8"))
            payload["child_executed_tests"]["pit_multi_daemon_lifecycle_report"] = []
            failure_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c failure child executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_publication_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            publication_report = phase_c_root / "publication/mixed-cluster-publication-report.json"
            payload = json.loads(publication_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = [
                "publication_full_state_receive_apply_replaces_local_cache"
            ]
            publication_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c publication executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_publication_child_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            publication_report = phase_c_root / "publication/mixed-cluster-publication-report.json"
            payload = json.loads(publication_report.read_text(encoding="utf-8"))
            payload["child_executed_tests"]["publication-reject-report.json"] = []
            publication_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c publication child executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_recovery_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            recovery_report = phase_c_root / "recovery/mixed-cluster-recovery-report.json"
            payload = json.loads(recovery_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = [
                "bounded_peer_recovery_wire_round_trip_probe",
            ]
            recovery_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c recovery executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_write_replication_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            write_report = (
                phase_c_root
                / "write-replication/mixed-cluster-write-replication-report.json"
            )
            payload = json.loads(write_report.read_text(encoding="utf-8"))
            payload["child_executed_tests"]["write_replication_reject_report"] = []
            write_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c write replication child executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_join_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            join_report = phase_c_root / "join/mixed-cluster-join-report.json"
            payload = json.loads(join_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = ["mixed_cluster_live_join_probe"]
            join_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c join executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_allocation_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            allocation_report = phase_c_root / "allocation/mixed-cluster-allocation-report.json"
            payload = json.loads(allocation_report.read_text(encoding="utf-8"))
            payload["child_executed_tests"]["allocation_reject_report"] = []
            allocation_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c allocation child executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_live_join_probe_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            live_join_report = phase_c_root / "join/live-join-probe-report.json"
            payload = json.loads(live_join_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = []
            live_join_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c live join probe executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )

    def test_phase_c_summary_rejects_bounded_recovery_probe_executed_test_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            phase_c_root = root / "phase-c"
            write_phase_c_reports(phase_c_root)
            recovery_report = phase_c_root / "recovery/bounded-peer-recovery-probe-report.json"
            payload = json.loads(recovery_report.read_text(encoding="utf-8"))
            payload["executed_tests"] = []
            recovery_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                SystemExit,
                "phase-c bounded recovery probe executed tests do not match current baseline",
            ):
                self.checker.validate_phase_c_summary(
                    str(phase_c_root / "phase-c-mixed-cluster-summary.json")
                )


def write_phase_c_reports(root: Path) -> None:
    summary_reports = {
        "generated-api-spec-report.json": True,
        "mixed-cluster-allocation-report.json": True,
        "mixed-cluster-failure-report.json": True,
        "mixed-cluster-join-report.json": True,
        "mixed-cluster-publication-report.json": True,
        "mixed-cluster-recovery-report.json": True,
        "mixed-cluster-write-replication-report.json": True,
    }
    payloads = {
        "phase-c-mixed-cluster-summary.json": {
            "summary": {"passed": True},
            "reports": summary_reports,
        },
        "join/mixed-cluster-join-report.json": {
            "summary": {"passed": True},
            "checks": {
                "live_join_probe_passed": True,
                "join_reject_passed": True,
            },
            "executed_tests": [
                "mixed_cluster_live_join_probe",
                "mixed_cluster_join_reject_fixture_matches_validator_behavior",
            ],
            "child_executed_tests": {
                "live_join_probe_report": [
                    "mixed_cluster_live_join_probe",
                ],
                "join_reject_report": [
                    "mixed_cluster_join_reject_fixture_matches_validator_behavior",
                ],
            },
        },
        "join/live-join-probe-report.json": {
            "summary": {"passed": True},
            "checks": {
                "remote_transport_version_matches_fixture": True,
                "response_header_matches_min_compat": True,
                "transport_payload_matches_fixture": True,
                "handshake_cluster_name_matches_state": True,
                "cluster_uuid_present": True,
                "single_local_node_visible": True,
                "advertised_roles_match_fixture": True,
                "required_attributes_present": True,
                "transport_address_present": True,
                "node_name_present": True,
            },
            "executed_tests": [
                "mixed_cluster_live_join_probe",
            ],
        },
        "recovery/mixed-cluster-recovery-report.json": {
            "summary": {"passed": True},
            "checks": {
                "bounded_peer_recovery_probe_passed": True,
                "recovery_reject_passed": True,
            },
            "executed_tests": [
                "bounded_peer_recovery_wire_round_trip_probe",
                "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
            ],
            "child_executed_tests": {
                "bounded_peer_recovery_probe_report": [
                    "bounded_peer_recovery_wire_round_trip_probe",
                ],
                "recovery_reject_report": [
                    "mixed_cluster_recovery_fail_closed_fixture_matches_validator_behavior",
                ],
            },
        },
        "recovery/bounded-peer-recovery-probe-report.json": {
            "summary": {"passed": True},
            "checks": {"wire_round_trip_passed": True},
            "executed_tests": [
                "bounded_peer_recovery_wire_round_trip_probe",
            ],
        },
        "failure/mixed-cluster-failure-report.json": {
            "summary": {"passed": True},
            "checks": {
                "failure_topology_probe_passed": True,
                "failure_ledger_passed": True,
                "pit_restart_lifecycle_passed": True,
                "pit_transport_restart_lifecycle_passed": True,
                "pit_multi_daemon_lifecycle_passed": True,
            },
            "executed_tests": [
                "daemon_point_in_time_contexts_do_not_survive_restart",
                "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                "multi_daemon_get_all_pits_fans_out_to_seed_peers",
            ],
            "child_executed_tests": {
                "pit_restart_lifecycle_report": [
                    "daemon_point_in_time_contexts_do_not_survive_restart",
                ],
                "pit_transport_restart_lifecycle_report": [
                    "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                ],
                "pit_multi_daemon_lifecycle_report": [
                    "multi_daemon_get_all_pits_fans_out_to_seed_peers",
                ],
            },
        },
        "write-replication/mixed-cluster-write-replication-report.json": {
            "summary": {"passed": True},
            "checks": {
                "write_replication_happy_path_passed": True,
                "write_replication_reject_passed": True,
            },
            "executed_tests": [
                "mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior",
                "replica_operation_tcp_round_trip_preserves_replication_progress_metadata",
            ],
            "child_executed_tests": {
                "write_replication_happy_path_report": [
                    "replica_operation_tcp_round_trip_preserves_replication_progress_metadata",
                ],
                "write_replication_reject_report": [
                    "mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior",
                ],
            },
        },
        "publication/mixed-cluster-publication-report.json": {
            "summary": {"passed": True},
            "checks": {
                "publication-full-state-report.json": True,
                "publication-diff-ack-report.json": True,
                "publication-reachable-catch-up-report.json": True,
                "publication-reject-report.json": True,
                "publication-repeated-diff-monotonicity-report.json": True,
                "publication-scheduled-catch-up-report.json": True,
            },
            "executed_tests": [
                "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
                "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
                "publication_diff_apply_acknowledges_only_after_successful_apply",
                "publication_full_state_receive_apply_replaces_local_cache",
                "publication_reject_integration_preserves_cache_and_withholds_ack",
                "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
            ],
            "child_executed_tests": {
                "publication-diff-ack-report.json": [
                    "publication_diff_apply_acknowledges_only_after_successful_apply",
                ],
                "publication-full-state-report.json": [
                    "publication_full_state_receive_apply_replaces_local_cache",
                ],
                "publication-reachable-catch-up-report.json": [
                    "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
                ],
                "publication-reject-report.json": [
                    "publication_reject_integration_preserves_cache_and_withholds_ack",
                ],
                "publication-repeated-diff-monotonicity-report.json": [
                    "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
                ],
                "publication-scheduled-catch-up-report.json": [
                    "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
                ],
            },
        },
        "allocation/mixed-cluster-allocation-report.json": {
            "summary": {"passed": True},
            "checks": {
                "routing_convergence_probe_passed": True,
                "allocation_reject_passed": True,
            },
            "executed_tests": [
                "mixed_cluster_allocation_routing_convergence_probe",
                "mixed_cluster_allocation_fail_closed_fixture_matches_validator_behavior",
            ],
            "child_executed_tests": {
                "routing_convergence_probe_report": [
                    "mixed_cluster_allocation_routing_convergence_probe",
                ],
                "allocation_reject_report": [
                    "mixed_cluster_allocation_fail_closed_fixture_matches_validator_behavior",
                ],
            },
        },
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
