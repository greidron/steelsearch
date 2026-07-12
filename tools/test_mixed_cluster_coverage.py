import importlib.util
import contextlib
import io
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
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = self.report.inspect_shard_movement(path)

            self.assertTrue(report["passed"])
            self.assertTrue(report["checkpoint_drift_ok"])
            self.assertTrue(report["checkpoint_monotonicity_ok"])
            self.assertTrue(report["retention_lease_metadata_ok"])
            self.assertTrue(report["transport_log_ok"])
            self.assertTrue(report["unsupported_allocation_explain_ok"])
            self.assertEqual(report["failed_required_summary_flags"], [])
            self.assertEqual(report["missing_required_phases"], [])
            self.assertEqual(report["phase_count"], 13)

    def test_default_shard_movement_report_uses_current_evidence_path(self):
        self.assertEqual(
            self.report.DEFAULT_SHARD_MOVEMENT,
            ROOT / "target/three-node-shard-movement-interruption-current/report.json",
        )

    def test_cli_requires_all_reports_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
            self.assertEqual(payload["summary"]["phase_c_passed_report_count"], 13)
            self.assertEqual(payload["summary"]["failure_node_loss_passed_report_count"], 3)
            self.assertEqual(
                payload["summary"]["failure_node_loss_report_names"],
                [
                    "failure_java_node_loss",
                    "failure_steelsearch_node_loss_publication",
                    "failure_steelsearch_node_loss_recovery",
                ],
            )
            self.assertEqual(
                payload["summary"]["failure_node_loss_passed_report_names"],
                [
                    "failure_java_node_loss",
                    "failure_steelsearch_node_loss_publication",
                    "failure_steelsearch_node_loss_recovery",
                ],
            )
            self.assertEqual(payload["summary"]["publication_report_count"], 6)
            self.assertEqual(payload["summary"]["publication_passed_report_count"], 6)
            self.assertEqual(payload["summary"]["publication_executed_test_count"], 6)
            self.assertEqual(payload["summary"]["publication_required_executed_test_count"], 6)
            self.assertEqual(
                payload["summary"]["publication_missing_required_executed_test_count"],
                0,
            )
            self.assertEqual(payload["summary"]["publication_stage_count"], 17)
            self.assertEqual(payload["summary"]["publication_required_stage_count"], 17)
            self.assertEqual(payload["summary"]["publication_missing_required_stage_count"], 0)
            self.assertEqual(payload["summary"]["shard_movement_required_phase_count"], 7)
            self.assertEqual(payload["summary"]["shard_movement_required_interruption_phase_count"], 6)
            self.assertEqual(
                payload["summary"]["shard_movement_phase_names"],
                [
                    "cluster_formed",
                    "unsupported_allocation_explain",
                    "initial_primary_on_java1",
                    "interrupt_java_to_steelsearch_recovery",
                    "resume_or_restart_java_to_steelsearch_recovery",
                    "replica_on_rust",
                    "finalize_java_to_steelsearch_recovery",
                    "opensearch_to_steelsearch",
                    "interrupt_steelsearch_to_opensearch_recovery",
                    "resume_or_restart_steelsearch_to_opensearch_recovery",
                    "java1_rejoined_as_replica",
                    "finalize_steelsearch_to_opensearch_recovery",
                    "steelsearch_to_opensearch",
                ],
            )
            self.assertEqual(
                payload["summary"]["shard_movement_duplicate_required_phase_count"],
                0,
            )
            self.assertEqual(payload["summary"]["shard_movement_missing_required_phase_count"], 0)
            self.assertEqual(payload["summary"]["shard_movement_phase_assertion_error_count"], 0)
            self.assertEqual(
                payload["summary"]["shard_movement_required_phase_fields"][
                    "opensearch_to_steelsearch"
                ],
                ["passed", "placement", "search_count", "shards"],
            )
            self.assertIn(
                "interruption_evidence_required",
                payload["summary"]["shard_movement_required_summary_flags"],
            )
            self.assertEqual(
                payload["summary"]["shard_movement_failed_required_summary_flag_count"],
                0,
            )
            self.assertTrue(payload["summary"]["transport_admin_passed"])
            self.assertEqual(payload["summary"]["transport_admin_remote_pit_case_count"], 5)
            self.assertEqual(
                payload["summary"]["transport_admin_remote_pit_cases"],
                [
                    "node_a_list_pits_after_node_b_close",
                    "node_a_open_pit",
                    "node_b_close_node_a_pit",
                    "node_b_search_node_a_pit",
                    "node_b_search_node_a_pit_after_close",
                ],
            )
            self.assertEqual(
                payload["summary"]["transport_admin_remote_pit_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["transport_admin_publication_validation_event_count"],
                6,
            )
            self.assertEqual(
                payload["summary"][
                    "transport_admin_publication_validation_observed_events"
                ],
                [
                    "apply.action_frame.passed",
                    "apply.connect.passed",
                    "apply.publication_semantics.passed",
                    "proposal.action_frame.passed",
                    "proposal.connect.passed",
                    "proposal.publication_semantics.passed",
                ],
            )
            self.assertEqual(
                payload["summary"]["transport_admin_publication_transcript_count"],
                1,
            )
            self.assertEqual(
                payload["reports"]["phase_c_summary"]["missing_required_reports"],
                [],
            )
            self.assertNotIn("out_of_scope", payload)
            self.assertIn(
                "representative mixed-cluster join, movement, recovery",
                payload["summary"]["claim_boundary"],
            )
            self.assertIn(
                "interrupted shard movement evidence",
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
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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

    def test_cli_rejects_failure_executed_tests_without_child_map(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            failure_report = root / "failure/mixed-cluster-failure-report.json"
            payload = json.loads(failure_report.read_text(encoding="utf-8"))
            payload.pop("child_executed_tests")
            failure_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
                "failure report missing child executed test map",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_publication_report_without_required_stage(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            publication_report = root / "publication/mixed-cluster-publication-report.json"
            payload = json.loads(publication_report.read_text(encoding="utf-8"))
            payload["publication_stages"].remove("ack_withheld")
            payload["child_publication_stages"]["publication-reject-report.json"].remove(
                "ack_withheld"
            )
            publication_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            **passed_shard_movement_summary(),
                        },
                        "phases": passed_shard_movement_phases(),
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
                "publication report missing required publication stages",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_shard_movement_missing_required_summary_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            summary = passed_shard_movement_summary()
            summary["retention_lease_metadata_ok"] = False
            movement.write_text(
                json.dumps(
                    {
                        "summary": summary,
                        "phases": passed_shard_movement_phases(),
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
                "shard movement report has failed required summary flags",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_shard_movement_missing_required_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            phases = [
                phase
                for phase in passed_shard_movement_phases()
                if phase["phase"] != "steelsearch_to_opensearch"
            ]
            movement.write_text(
                json.dumps(
                    {
                        "summary": passed_shard_movement_summary(),
                        "phases": phases,
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
            self.assertEqual(
                payload["summary"]["shard_movement_missing_required_phase_count"],
                1,
            )
            self.assertIn(
                "shard movement report missing required phases",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_shard_movement_missing_interruption_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            phases = [
                phase
                for phase in passed_shard_movement_phases()
                if phase["phase"] != "resume_or_restart_steelsearch_to_opensearch_recovery"
            ]
            movement.write_text(
                json.dumps(
                    {
                        "summary": passed_shard_movement_summary(),
                        "phases": phases,
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
                "resume_or_restart_steelsearch_to_opensearch_recovery",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_shard_movement_phase_without_required_evidence_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            phases = passed_shard_movement_phases()
            for phase in phases:
                if phase["phase"] == "opensearch_to_steelsearch":
                    phase.pop("search_count")
            movement.write_text(
                json.dumps(
                    {
                        "summary": passed_shard_movement_summary(),
                        "phases": phases,
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
            self.assertEqual(payload["summary"]["shard_movement_phase_assertion_error_count"], 2)
            self.assertIn(
                "opensearch_to_steelsearch: missing fields ['search_count']",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_shard_movement_phase_with_failed_cluster_health(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            phases = passed_shard_movement_phases()
            for phase in phases:
                if phase["phase"] == "replica_on_rust":
                    phase["cluster_health"] = {"status": "yellow"}
            movement.write_text(
                json.dumps(
                    {
                        "summary": passed_shard_movement_summary(),
                        "phases": phases,
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
                "replica_on_rust: cluster_health.status must be green",
                "\n".join(payload["errors"]),
            )

    def test_cli_rejects_transport_admin_without_publication_validation_events(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": passed_shard_movement_summary(),
                        "phases": passed_shard_movement_phases(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            transport_admin = Path(temp_dir_value) / "transport-admin.json"
            write_transport_admin_fixture(transport_admin)
            payload = json.loads(transport_admin.read_text(encoding="utf-8"))
            payload.pop("coordination")
            transport_admin.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--transport-admin-report",
                str(transport_admin),
                "--require-passed",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn(
                "transport admin report has publication validation errors",
                "\n".join(payload["errors"]),
            )

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        transport_temp = None
        cli_args = list(args)
        try:
            if "--transport-admin-report" not in cli_args:
                transport_temp = tempfile.TemporaryDirectory()
                transport_admin = Path(transport_temp.name) / "transport-admin.json"
                write_transport_admin_fixture(transport_admin)
                cli_args.extend(["--transport-admin-report", str(transport_admin)])
            sys.argv = [str(REPORT_PATH), *cli_args]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                io.StringIO()
            ):
                return self.report.main()
        finally:
            sys.argv = old_argv
            if transport_temp is not None:
                transport_temp.cleanup()


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
        "failure/java-node-loss-report.json": {
            "summary": {"passed": True},
        },
        "failure/steelsearch-node-loss-publication-report.json": {
            "summary": {"passed": True},
        },
        "failure/steelsearch-node-loss-recovery-report.json": {
            "summary": {"passed": True},
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
                "publication-repeated-diff-monotonicity-report.json": True,
                "publication-reachable-catch-up-report.json": True,
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
                "publication-full-state-report.json": [
                    "publication_full_state_receive_apply_replaces_local_cache",
                ],
                "publication-diff-ack-report.json": [
                    "publication_diff_apply_acknowledges_only_after_successful_apply",
                ],
                "publication-reject-report.json": [
                    "publication_reject_integration_preserves_cache_and_withholds_ack",
                ],
                "publication-repeated-diff-monotonicity-report.json": [
                    "repeated_publication_diff_apply_requires_monotonic_versions_before_ack",
                ],
                "publication-reachable-catch-up-report.json": [
                    "periodic_liveness_catches_up_reachable_lagging_publication_follower_before_retry",
                ],
                "publication-scheduled-catch-up-report.json": [
                    "periodic_liveness_schedules_node_left_publication_retry_before_fencing_manager",
                ],
            },
            "publication_stages": [
                "ack_withheld",
                "apply_ack",
                "apply_ack_after_success",
                "cache_preserved",
                "catch_up_scheduled_with_backoff",
                "diff_apply",
                "diff_decode",
                "full_state_decode",
                "lagging_follower_detected",
                "local_cache_replace",
                "monotonic_version_required",
                "node_left_retry_after_backoff",
                "reachable_catch_up_applied",
                "reject_detected",
                "repeated_diff_decode",
                "retry_suppressed",
                "stale_round_rejected",
            ],
            "child_publication_stages": {
                "publication-full-state-report.json": [
                    "full_state_decode",
                    "local_cache_replace",
                    "apply_ack",
                ],
                "publication-diff-ack-report.json": [
                    "diff_decode",
                    "diff_apply",
                    "apply_ack_after_success",
                ],
                "publication-reject-report.json": [
                    "reject_detected",
                    "cache_preserved",
                    "ack_withheld",
                ],
                "publication-repeated-diff-monotonicity-report.json": [
                    "repeated_diff_decode",
                    "monotonic_version_required",
                    "stale_round_rejected",
                ],
                "publication-reachable-catch-up-report.json": [
                    "lagging_follower_detected",
                    "reachable_catch_up_applied",
                    "retry_suppressed",
                ],
                "publication-scheduled-catch-up-report.json": [
                    "lagging_follower_detected",
                    "catch_up_scheduled_with_backoff",
                    "node_left_retry_after_backoff",
                ],
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


def write_transport_admin_fixture(path: Path) -> None:
    pit_id = "pit-current"
    payload = {
        "summary": {"failed": 0, "passed": 15},
        "cases": [
            {
                "name": "node_a_open_pit",
                "status": "passed",
                "response": {
                    "body": {
                        "pit_id": pit_id,
                        "_shards": {"failed": 0},
                    }
                },
            },
            {
                "name": "node_b_search_node_a_pit",
                "status": "passed",
                "response": {
                    "body": {
                        "pit_id": pit_id,
                        "hits": {
                            "total": {"value": 1},
                            "hits": [
                                {
                                    "_id": "doc-1",
                                    "_source": {"message": "visible-through-pit"},
                                }
                            ],
                        },
                    }
                },
            },
            {
                "name": "node_b_close_node_a_pit",
                "status": "passed",
                "response": {
                    "body": {
                        "pits": [
                            {
                                "pit_id": pit_id,
                                "successful": True,
                            }
                        ]
                    }
                },
            },
            {
                "name": "node_b_search_node_a_pit_after_close",
                "status": "passed",
                "response": {
                    "body": {
                        "status": 404,
                        "error": {"type": "search_phase_execution_exception"},
                    }
                },
            },
            {
                "name": "node_a_list_pits_after_node_b_close",
                "status": "passed",
                "response": {"body": {"pits": []}},
            },
        ],
        "coordination": {
            "publication_transport_transcripts": [
                {
                    "validation_events": [
                        publication_validation_event("proposal", "connect"),
                        publication_validation_event("proposal", "action_frame"),
                        publication_validation_event("proposal", "publication_semantics"),
                        publication_validation_event("apply", "connect"),
                        publication_validation_event("apply", "action_frame"),
                        publication_validation_event("apply", "publication_semantics"),
                    ]
                }
            ]
        },
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def publication_validation_event(phase: str, step: str) -> dict:
    return {
        "phase": phase,
        "step": step,
        "status": "passed",
        "node_id": "node-b",
    }


def passed_shard_movement_summary() -> dict:
    return {
        "passed": True,
        "checkpoint_drift_ok": True,
        "checkpoint_monotonicity_ok": True,
        "interruption_evidence_ok": True,
        "interruption_evidence_required": True,
        "opensearch_to_steelsearch_passed": True,
        "retention_lease_metadata_ok": True,
        "steelsearch_to_opensearch_passed": True,
        "transport_log_ok": True,
        "unsupported_allocation_explain_ok": True,
    }


def passed_shard_movement_phases() -> list[dict]:
    placement_java_primary = {
        "primary_node": "java-primary-1",
        "primary_state": "STARTED",
        "replica_node": None,
        "replica_state": None,
    }
    placement_java_primary_rust_replica = {
        "primary_node": "java-primary-1",
        "primary_state": "STARTED",
        "replica_node": "rust-replica-1",
        "replica_state": "STARTED",
    }
    placement_rust_primary = {
        "primary_node": "rust-replica-1",
        "primary_state": "STARTED",
        "replica_node": None,
        "replica_state": "UNASSIGNED",
    }
    placement_rust_primary_java_replica = {
        "primary_node": "rust-replica-1",
        "primary_state": "STARTED",
        "replica_node": "java-primary-1",
        "replica_state": "STARTED",
    }
    cluster_green = {"status": "green"}
    recovery = {"ok": True, "status": 200}
    checkpoint_drift = {
        "seq_no_drift": 0,
        "local_checkpoint_drift": 0,
        "global_checkpoint_drift": 0,
    }
    shards = [{"state": "STARTED", "prirep": "p"}]
    return [
        {"phase": "cluster_formed", "node_count": 3},
        {"phase": "unsupported_allocation_explain", "allocation_explain": {"can_allocate": "no"}},
        {
            "phase": "initial_primary_on_java1",
            "placement": placement_java_primary,
            "search_count": 5,
            "shards": shards,
        },
        {
            "phase": "interrupt_java_to_steelsearch_recovery",
            "placement": placement_java_primary,
            "recovery": recovery,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "resume_or_restart_java_to_steelsearch_recovery",
            "placement": placement_java_primary,
            "recovery": recovery,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "replica_on_rust",
            "placement": placement_java_primary_rust_replica,
            "cluster_health": cluster_green,
            "search_count": 5,
            "shards": shards,
        },
        {
            "phase": "finalize_java_to_steelsearch_recovery",
            "placement": placement_java_primary_rust_replica,
            "recovery": recovery,
            "cluster_health": cluster_green,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "opensearch_to_steelsearch",
            "passed": True,
            "placement": placement_rust_primary,
            "search_count": 5,
            "shards": shards,
        },
        {
            "phase": "interrupt_steelsearch_to_opensearch_recovery",
            "placement": placement_rust_primary,
            "recovery": recovery,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "resume_or_restart_steelsearch_to_opensearch_recovery",
            "placement": placement_rust_primary,
            "recovery": recovery,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "java1_rejoined_as_replica",
            "placement": placement_rust_primary_java_replica,
            "cluster_health": cluster_green,
        },
        {
            "phase": "finalize_steelsearch_to_opensearch_recovery",
            "placement": placement_rust_primary_java_replica,
            "recovery": recovery,
            "cluster_health": cluster_green,
            "checkpoint_drift": checkpoint_drift,
        },
        {
            "phase": "steelsearch_to_opensearch",
            "passed": True,
            "placement": placement_java_primary,
            "search_count": 5,
            "shards": shards,
        },
    ]


if __name__ == "__main__":
    unittest.main()
