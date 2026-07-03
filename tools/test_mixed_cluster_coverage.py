import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-mixed-cluster-coverage.py"


def load_report_module():
    module_name = "report_mixed_cluster_coverage"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class MixedClusterCoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = load_report_module()

    def test_shard_movement_summary_extracts_directional_checks(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "movement.json"
            path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [
                            {"phase": "replica_on_rust"},
                            {"phase": "steelsearch_to_opensearch"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = self.report.inspect_shard_movement(path)

            self.assertTrue(report["passed"])
            self.assertTrue(report["checkpoint_drift_ok"])
            self.assertEqual(report["phase_count"], 2)

    def test_cli_requires_all_reports_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--output",
                str(output),
            )

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["phase_c_passed_report_count"], 10)
            self.assertEqual(
                payload["reports"]["phase_c_summary"]["missing_required_reports"],
                [],
            )
            self.assertNotIn("out_of_scope", payload)
            self.assertIn(
                "representative mixed-cluster join, movement, recovery",
                payload["summary"]["claim_boundary"],
            )

    def test_cli_rejects_stale_reports_when_age_gate_is_set(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            stale_mtime = time.time() - 120.0
            for path in root.rglob("*.json"):
                os.utime(path, (stale_mtime, stale_mtime))
            os.utime(movement, (stale_mtime, stale_mtime))
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--max-report-age-seconds",
                "60",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["phase_c_fresh_report_count"], 0)
            self.assertFalse(payload["summary"]["shard_movement_fresh"])

    def test_cli_rejects_report_without_required_checks(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            (root / "join/mixed-cluster-join-report.json").write_text(
                json.dumps({"summary": {"passed": True}, "checks": {}}) + "\n",
                encoding="utf-8",
            )
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn(
                "join report missing required checks",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_summary_without_required_child_report_map(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            (root / "phase-c-mixed-cluster-summary.json").write_text(
                json.dumps({"summary": {"passed": True}, "reports": {}}) + "\n",
                encoding="utf-8",
            )
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn(
                "phase_c_summary report missing required child reports",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_failure_executed_tests_not_matching_child_map(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            failure_report = root / "failure/mixed-cluster-failure-report.json"
            payload = json.loads(failure_report.read_text(encoding="utf-8"))
            payload["child_executed_tests"]["pit_multi_daemon_lifecycle_report"] = []
            failure_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn(
                "failure report executed tests do not match child reports",
                "\n".join(payload["errors"]),
            )

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


def write_phase_c_fixture(root: Path) -> None:
    payloads = {
        "phase-c-mixed-cluster-summary.json": {
            "summary": {"passed": True},
            "reports": {
                "mixed-cluster-allocation-report.json": True,
                "mixed-cluster-failure-report.json": True,
                "mixed-cluster-join-report.json": True,
                "mixed-cluster-publication-report.json": True,
                "mixed-cluster-recovery-report.json": True,
                "mixed-cluster-write-replication-report.json": True,
            },
        },
        "join/mixed-cluster-join-report.json": {
            "summary": {"passed": True},
            "checks": {
                "live_join_probe_passed": True,
                "join_reject_passed": True,
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
        },
        "join/join-reject-report.json": {
            "summary": {"passed": True},
        },
        "recovery/mixed-cluster-recovery-report.json": {
            "summary": {"passed": True},
            "checks": {
                "bounded_peer_recovery_probe_passed": True,
                "recovery_reject_passed": True,
            },
        },
        "recovery/bounded-peer-recovery-probe-report.json": {
            "summary": {"passed": True},
            "checks": {
                "wire_round_trip_passed": True,
            },
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
        },
        "publication/mixed-cluster-publication-report.json": {
            "summary": {"passed": True},
            "checks": {
                "publication-full-state-report.json": True,
                "publication-diff-ack-report.json": True,
                "publication-reject-report.json": True,
            },
        },
        "allocation/mixed-cluster-allocation-report.json": {
            "summary": {"passed": True},
            "checks": {
                "routing_convergence_probe_passed": True,
                "allocation_reject_passed": True,
            },
        },
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
