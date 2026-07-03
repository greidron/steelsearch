import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-native-closure-status.py"
RUNNER_PATH = ROOT / "tools" / "run-native-closure-validation.py"


def load_report_module():
    module_name = "report_native_closure_status"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_runner_module():
    module_name = "run_native_closure_validation"
    spec = importlib.util.spec_from_file_location(module_name, RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class NativeClosureStatusReportTests(unittest.TestCase):
    def setUp(self):
        self.reporter = load_report_module()

    def test_status_is_pending_when_current_evidence_passes_without_final_cutover(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": False, "status": "pending"},
            require_final_cutover=False,
            metadata={"git_head": "abc123", "generated_at_epoch_seconds": 1},
        )

        self.assertEqual(report["metadata"]["git_head"], "abc123")
        self.assertTrue(report["summary"]["passed"])
        self.assertTrue(report["summary"]["current_evidence_ready"])
        self.assertFalse(report["summary"]["final_cutover_ready"])
        self.assertEqual(
            report["summary"]["status"],
            "current-evidence-ready-final-cutover-pending",
        )

    def test_status_fails_when_final_cutover_is_required_but_missing(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": False, "status": "pending"},
            require_final_cutover=True,
        )

        self.assertFalse(report["summary"]["passed"])
        self.assertEqual(report["summary"]["status"], "final-cutover-missing")

    def test_status_is_ready_when_all_gates_pass(self):
        report = self.reporter.build_status_report(
            current_evidence={"passed": True},
            peer_backpressure={"passed": True},
            final_cutover={"passed": True, "status": "ok"},
            require_final_cutover=True,
        )

        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["status"], "ready")

    def test_current_evidence_gate_ready_requires_all_groups_when_group_statuses_are_present(self):
        groups = {
            group: {"ok": True, "status": "ok", "returncode": 0}
            for group in self.reporter.CURRENT_EVIDENCE_GROUPS
        }
        current_evidence = {"passed": True, "groups": groups}

        self.assertTrue(self.reporter.current_evidence_gate_ready(current_evidence))

        groups["mixed-cluster-coverage-current"]["ok"] = False

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_current_evidence_groups_match_validation_batch_groups(self):
        runner = load_runner_module()
        batch_groups = tuple(
            dict.fromkeys(test.group for test in runner.CURRENT_EVIDENCE_GATE_BATCH)
        )

        self.assertEqual(self.reporter.CURRENT_EVIDENCE_GROUPS, batch_groups)

    def test_group_statuses_preserve_result_group_ok_and_returncode(self):
        statuses = self.reporter.group_statuses(
            [
                {
                    "group": "transport-action-coverage-current",
                    "ok": True,
                    "status": "ok",
                    "returncode": 0,
                }
            ]
        )

        self.assertEqual(
            statuses["transport-action-coverage-current"],
            {"ok": True, "status": "ok", "returncode": 0},
        )

    def test_missing_manifest_lists_required_final_cutover_items(self):
        final_cutover = self.reporter.inspect_release_readiness(None)

        self.assertEqual(final_cutover["status"], "pending")
        self.assertEqual(
            final_cutover["missing_items"],
            [
                "benchmark_coverage",
                "load_test_coverage",
                "chaos_test_coverage",
                "packaging_verified",
                "rolling_upgrade_coverage",
            ],
        )
        self.assertEqual(final_cutover["startup_manifest_items"], final_cutover["missing_items"])
        self.assertIn("load_comparison", final_cutover["readiness_attachment_items"])
        self.assertNotIn("load_comparison", final_cutover["startup_manifest_items"])
        self.assertEqual(
            final_cutover["readiness_attachment_missing_items"],
            [
                "benchmark_coverage",
                "load_test_coverage",
                "chaos_test_coverage",
                "packaging_verified",
                "rolling_upgrade_coverage",
                "load_comparison",
            ],
        )
        self.assertEqual(
            final_cutover["release_record_missing_items"],
            [
                "benchmark_coverage",
                "load_test_coverage",
                "chaos_test_coverage",
                "packaging_verified",
                "rolling_upgrade_coverage",
                "load_comparison",
                "promotion_gate_suite",
            ],
        )
        self.assertEqual(
            final_cutover["required_item_inputs"]["benchmark_coverage"]["attach_argument"],
            "--benchmark-report",
        )
        self.assertIn(
            "--release-readiness-file",
            final_cutover["manifest_command_template"],
        )
        self.assertEqual(
            final_cutover["readiness_attachment_inputs"]["load_comparison"]["attach_argument"],
            "--load-comparison-report",
        )
        self.assertIn(
            "--load-comparison-report",
            final_cutover["manifest_command_template"],
        )
        self.assertIn("evidence_inventory", final_cutover)
        self.assertIn("summary", final_cutover["evidence_inventory"])

    def test_missing_release_items_reports_only_failed_or_missing_items(self):
        missing = self.reporter.missing_release_items(
            {
                "items": {
                    "benchmark_coverage": {"passed": True, "errors": []},
                    "load_test_coverage": {"passed": False, "errors": ["blocked"]},
                    "chaos_test_coverage": {"passed": True, "errors": []},
                    "packaging_verified": {"passed": True, "errors": []},
                }
            }
        )

        self.assertEqual(missing, ["load_test_coverage", "rolling_upgrade_coverage"])

    def test_final_cutover_item_inputs_are_limited_to_requested_items(self):
        inputs = self.reporter.final_cutover_item_inputs(
            ["load_test_coverage", "rolling_upgrade_coverage"]
        )

        self.assertEqual(set(inputs), {"load_test_coverage", "rolling_upgrade_coverage"})
        self.assertEqual(inputs["load_test_coverage"]["attach_argument"], "--load-report")

    def test_complete_release_readiness_manifest_still_requires_load_comparison_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            manifest = temp_dir / "release-readiness.json"
            artifacts = {
                "benchmark_coverage": "benchmark.jsonl",
                "load_test_coverage": "load-baseline.json",
                "chaos_test_coverage": "chaos.json",
                "packaging_verified": "packaging.json",
                "rolling_upgrade_coverage": "rolling.json",
            }
            for artifact in artifacts.values():
                (temp_dir / artifact).write_text("{}\n", encoding="utf-8")
            manifest.write_text(
                json.dumps(
                    {
                        name: {
                            "passed": True,
                            "artifact_path": artifact,
                            "blockers": [],
                        }
                        for name, artifact in artifacts.items()
                    }
                ),
                encoding="utf-8",
            )

            final_cutover = self.reporter.inspect_release_readiness(manifest)

            self.assertFalse(final_cutover["passed"])
            self.assertEqual(final_cutover["missing_items"], [])
            self.assertEqual(final_cutover["readiness_attachment_missing_items"], ["load_comparison"])
            self.assertIn(
                "readiness report path is not configured",
                final_cutover["readiness_attachment_errors"],
            )

    def test_complete_readiness_attachments_mark_final_cutover_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            manifest = temp_dir / "release-readiness.json"
            readiness = temp_dir / "readiness.json"
            artifacts = {
                "benchmark_coverage": "benchmark.jsonl",
                "load_test_coverage": "load-baseline.json",
                "chaos_test_coverage": "chaos.json",
                "packaging_verified": "packaging.json",
                "rolling_upgrade_coverage": "rolling.json",
            }
            load_comparison = write_valid_release_inventory_artifacts(temp_dir, artifacts)
            manifest.write_text(
                json.dumps(
                    {
                        name: {
                            "passed": True,
                            "artifact_path": artifact,
                            "blockers": [],
                        }
                        for name, artifact in artifacts.items()
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "release_evidence": {
                            "load_comparison": {
                                "ready": True,
                                "path": str(load_comparison),
                                "blockers": [],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            final_cutover = self.reporter.inspect_release_readiness(
                manifest,
                readiness_report_path=readiness,
                evidence_root=temp_dir,
                evidence_max_age_seconds=60.0,
            )
            report = self.reporter.build_status_report(
                current_evidence={"passed": True},
                peer_backpressure={"passed": True},
                final_cutover=final_cutover,
                require_final_cutover=True,
            )

            self.assertTrue(final_cutover["passed"])
            self.assertEqual(final_cutover["missing_items"], [])
            self.assertEqual(final_cutover["readiness_attachment_missing_items"], [])
            self.assertEqual(final_cutover["release_record_missing_items"], [])
            self.assertTrue(final_cutover["evidence_inventory"]["summary"]["complete"])
            self.assertTrue(report["summary"]["passed"])
            self.assertEqual(report["summary"]["status"], "ready")

    def test_complete_manifest_and_readiness_still_fail_when_inventory_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            manifest = temp_dir / "release-readiness.json"
            readiness = temp_dir / "readiness.json"
            load_comparison = temp_dir / "final-load-comparison.json"
            load_comparison.write_text(
                json.dumps(
                    {
                        "targets": {
                            "steelsearch": {"returncode": 0},
                            "opensearch": {"returncode": 0},
                        },
                        "comparison": {"mode": "completed"},
                    }
                ),
                encoding="utf-8",
            )
            artifacts = {
                "benchmark_coverage": "benchmark.jsonl",
                "load_test_coverage": "load.json",
                "chaos_test_coverage": "chaos.json",
                "packaging_verified": "packaging.json",
                "rolling_upgrade_coverage": "rolling.json",
            }
            for artifact in artifacts.values():
                (temp_dir / artifact).write_text("{}\n", encoding="utf-8")
            manifest.write_text(
                json.dumps(
                    {
                        name: {
                            "passed": True,
                            "artifact_path": artifact,
                            "blockers": [],
                        }
                        for name, artifact in artifacts.items()
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "release_evidence": {
                            "load_comparison": {
                                "ready": True,
                                "path": str(load_comparison),
                                "blockers": [],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            final_cutover = self.reporter.inspect_release_readiness(
                manifest,
                readiness_report_path=readiness,
                evidence_root=temp_dir,
                evidence_max_age_seconds=60.0,
            )

            self.assertFalse(final_cutover["passed"])
            self.assertIn(
                "release evidence inventory is incomplete",
                final_cutover["readiness_attachment_errors"],
            )

    def test_release_evidence_inventory_is_reported_with_summary_and_command_template(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            inventory = self.reporter.inspect_release_evidence_inventory(
                temp_dir,
                max_age_seconds=60.0,
            )

            self.assertEqual(inventory["returncode"], 0)
            self.assertEqual(inventory["summary"]["complete"], False)
            self.assertIn("benchmark_coverage", inventory["summary"]["startup_missing_items"])
            self.assertIn("--root", inventory["command"])
            self.assertIn("--release-readiness-file", inventory["attach_command_template"])

    def test_cli_writes_status_report_to_output_path(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "nested" / "native-closure-status.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPORT_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            stdout_payload = json.loads(result.stdout)
            file_payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_payload["summary"], file_payload["summary"])
            self.assertIn("git_head", file_payload["metadata"])
            self.assertIn("generated_at_epoch_seconds", file_payload["metadata"])
            self.assertIn("git_clean", file_payload["metadata"])
            self.assertIn("git_status_short", file_payload["metadata"])
            self.assertEqual(file_payload["summary"]["current_evidence_ready"], True)
            current = file_payload["gates"]["current_evidence"]
            self.assertEqual(
                current["required_groups"],
                list(self.reporter.CURRENT_EVIDENCE_GROUPS),
            )
            self.assertTrue(current["groups"]["transport-action-coverage-current"]["ok"])
            self.assertTrue(current["groups"]["mixed-cluster-coverage-current"]["ok"])


def write_valid_release_inventory_artifacts(temp_dir: Path, artifacts: dict[str, str]) -> Path:
    (temp_dir / artifacts["benchmark_coverage"]).write_text(
        json.dumps({"benchmark": "final-smoke"}) + "\n",
        encoding="utf-8",
    )
    (temp_dir / artifacts["load_test_coverage"]).write_text(
        json.dumps({"summary": {"error_count": 0, "operation_count": 10}}),
        encoding="utf-8",
    )
    (temp_dir / artifacts["chaos_test_coverage"]).write_text(
        json.dumps(
            {
                "ready": True,
                "passed": True,
                "blockers": [],
                "summary": {
                    "passed": True,
                    "error_count": 0,
                    "coverage_scope": "mixed-cluster failure fixture",
                },
                "source_report": {
                    "summary": {"passed": True},
                    "checks": {
                        "failure_topology_probe_passed": True,
                        "failure_ledger_passed": True,
                        "pit_restart_lifecycle_passed": True,
                        "pit_transport_restart_lifecycle_passed": True,
                        "pit_multi_daemon_lifecycle_passed": True,
                    },
                    "executed_tests": [
                        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (temp_dir / artifacts["packaging_verified"]).write_text("{}\n", encoding="utf-8")
    (temp_dir / artifacts["rolling_upgrade_coverage"]).write_text(
        json.dumps(
            {
                "ready": True,
                "passed": True,
                "blockers": [],
                "summary": {
                    "passed": True,
                    "error_count": 0,
                    "coverage_scope": "rolling-upgrade transcript fixture",
                },
                "transcript": {
                    "profile": "rolling-upgrade",
                    "status": "completed",
                },
                "assertion_hits": {
                    "cluster ready before upgrade sequence": True,
                    "upgrade steps recorded in order": True,
                    "cluster ready after each upgraded node rejoins": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (temp_dir / "promotion-gate-suite-current.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "passed": 2,
                "failed": 0,
                "checks": [
                    {"name": "source-compatibility-drift", "status": "ok", "returncode": 0},
                    {"name": "mixed-cluster-coverage", "status": "ok", "returncode": 0},
                ],
            }
        ),
        encoding="utf-8",
    )
    load_comparison = temp_dir / "final-load-comparison.json"
    load_comparison.write_text(
        json.dumps(
            {
                "targets": {
                    "steelsearch": {"returncode": 0},
                    "opensearch": {"returncode": 0},
                },
                "comparison": {"mode": "completed"},
            }
        ),
        encoding="utf-8",
    )
    return load_comparison


if __name__ == "__main__":
    unittest.main()
