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
INVENTORY_PATH = ROOT / "tools" / "report-release-evidence-inventory.py"


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


def load_inventory_module():
    module_name = "report_release_evidence_inventory_for_status_tests"
    spec = importlib.util.spec_from_file_location(module_name, INVENTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def transport_release_parity_result(
    *,
    complete: bool = True,
    missing_count: int = 0,
    matched_count: int = 174,
):
    return {
        "group": "transport-action-coverage-current",
        "name": "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
        "ok": True,
        "status": "ok",
        "returncode": 0,
        "summary": {
            "release_parity_evidence_complete": complete,
            "release_parity_source_missing_action_count": missing_count,
            "release_parity_source_matched_action_count": matched_count,
        },
    }


def current_evidence_report(reporter):
    results = [transport_release_parity_result()]
    return {
        "passed": True,
        "command": list(reporter.CURRENT_EVIDENCE_COMMAND),
        "returncode": 0,
        "summary": {
            "batch": "current-evidence-gate",
            "failed_count": 0,
            "passed_count": len(results),
            "test_count": len(results),
            "zero_test_count": 0,
        },
        "required_groups": list(reporter.CURRENT_EVIDENCE_GROUPS),
        "groups": {
            group: {"ok": True, "status": "ok", "returncode": 0}
            for group in reporter.CURRENT_EVIDENCE_GROUPS
        },
        "results": results,
    }


def runtime_peer_backpressure_report(reporter):
    return {
        "name": "runtime-peer-backpressure-current",
        "passed": True,
        "command": list(reporter.RUNTIME_PEER_BACKPRESSURE_COMMAND),
        "returncode": 0,
        "summary": {
            "batch": "runtime-peer-backpressure-current",
            "failed_count": 0,
            "passed_count": 1,
            "test_count": 1,
            "zero_test_count": 0,
        },
        "groups": {
            "runtime-fairness-peer-backpressure-current": {
                "ok": True,
                "returncode": 0,
                "status": "ok",
            }
        },
        "results": [
            {
                "group": "runtime-fairness-peer-backpressure-current",
                "name": "runtime_peer_backpressure_current_report_preserves_profile_and_counters",
                "ok": True,
                "returncode": 0,
                "status": "ok",
                "summary": {
                    "opensearch_completed": 1,
                    "opensearch_http_429_count": 1,
                    "opensearch_rejected": 1,
                    "passed": True,
                    "profile": "mixed-java-rust-query-phase",
                    "steelsearch_completed": 1,
                    "steelsearch_rejected": 1,
                },
            }
        ],
    }


def final_cutover_report(reporter):
    startup = list(reporter.FINAL_CUTOVER_ITEMS)
    readiness = list(reporter.READINESS_ATTACHMENT_INPUTS)
    release_record = list(reporter.RELEASE_RECORD_ITEMS)
    return {
        "name": "release-readiness",
        "passed": True,
        "status": "ok",
        "returncode": 0,
        "errors": [],
        "readiness_attachment_errors": [],
        "required_item_inputs": {},
        "startup_manifest_items": startup,
        "readiness_attachment_items": readiness,
        "missing_items": [],
        "readiness_attachment_missing_items": [],
        "release_record_missing_items": [],
        "summary": {
            "checked_items": len(startup),
            "ready_items": len(startup),
            "required_items": len(startup),
        },
        "evidence_inventory": {
            "returncode": 0,
            "summary": {
                "complete": True,
                "passed": True,
                "startup_missing_items": [],
                "readiness_attachment_missing_items": [],
                "release_record_missing_items": [],
                "startup_ready_items": startup,
                "readiness_attachment_ready_items": readiness,
                "release_record_ready_items": release_record,
            },
        },
    }


class NativeClosureStatusReportTests(unittest.TestCase):
    def setUp(self):
        self.reporter = load_report_module()

    def test_status_is_pending_when_current_evidence_passes_without_final_cutover(self):
        report = self.reporter.build_status_report(
            current_evidence=current_evidence_report(self.reporter),
            peer_backpressure=runtime_peer_backpressure_report(self.reporter),
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
            current_evidence=current_evidence_report(self.reporter),
            peer_backpressure=runtime_peer_backpressure_report(self.reporter),
            final_cutover={"passed": False, "status": "pending"},
            require_final_cutover=True,
        )

        self.assertFalse(report["summary"]["passed"])
        self.assertEqual(report["summary"]["status"], "final-cutover-missing")

    def test_status_is_ready_when_all_gates_pass(self):
        report = self.reporter.build_status_report(
            current_evidence=current_evidence_report(self.reporter),
            peer_backpressure=runtime_peer_backpressure_report(self.reporter),
            final_cutover=final_cutover_report(self.reporter),
            require_final_cutover=True,
        )

        self.assertTrue(report["summary"]["passed"])
        self.assertTrue(report["summary"]["current_evidence_ready"])
        self.assertTrue(report["summary"]["runtime_peer_backpressure_ready"])
        self.assertTrue(report["summary"]["final_cutover_ready"])
        self.assertTrue(report["summary"]["final_cutover_required"])
        self.assertEqual(report["summary"]["status"], "ready")
        self.assertEqual(
            report["gates"]["current_evidence"]["results"][0]["summary"][
                "release_parity_source_matched_action_count"
            ],
            174,
        )

    def test_final_cutover_ready_requires_complete_release_evidence_envelope(self):
        final_cutover = final_cutover_report(self.reporter)

        self.assertTrue(self.reporter.final_cutover_gate_ready(final_cutover))

        final_cutover = final_cutover_report(self.reporter)
        final_cutover["returncode"] = 1

        self.assertFalse(self.reporter.final_cutover_gate_ready(final_cutover))

        final_cutover = final_cutover_report(self.reporter)
        final_cutover["readiness_attachment_errors"] = ["missing load comparison"]

        self.assertFalse(self.reporter.final_cutover_gate_ready(final_cutover))

        final_cutover = final_cutover_report(self.reporter)
        final_cutover["summary"]["ready_items"] = 4

        self.assertFalse(self.reporter.final_cutover_gate_ready(final_cutover))

        final_cutover = final_cutover_report(self.reporter)
        final_cutover["evidence_inventory"]["summary"]["complete"] = False

        self.assertFalse(self.reporter.final_cutover_gate_ready(final_cutover))

    def test_current_evidence_gate_ready_requires_all_groups_when_group_statuses_are_present(self):
        groups = {
            group: {"ok": True, "status": "ok", "returncode": 0}
            for group in self.reporter.CURRENT_EVIDENCE_GROUPS
        }
        current_evidence = {
            "passed": True,
            "command": list(self.reporter.CURRENT_EVIDENCE_COMMAND),
            "returncode": 0,
            "summary": {
                "batch": "current-evidence-gate",
                "failed_count": 0,
                "passed_count": 1,
                "test_count": 1,
                "zero_test_count": 0,
            },
            "required_groups": list(self.reporter.CURRENT_EVIDENCE_GROUPS),
            "groups": groups,
            "results": [transport_release_parity_result()],
        }

        self.assertTrue(self.reporter.current_evidence_gate_ready(current_evidence))

        groups["mixed-cluster-coverage-current"]["ok"] = False

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["groups"]["mixed-cluster-coverage-current"]["status"] = "failed"

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["groups"]["mixed-cluster-coverage-current"]["returncode"] = 1

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_current_evidence_gate_ready_requires_exact_required_groups(self):
        current_evidence = current_evidence_report(self.reporter)
        current_evidence["required_groups"] = list(self.reporter.CURRENT_EVIDENCE_GROUPS[:-1])

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_current_evidence_gate_ready_requires_current_command_and_returncode(self):
        current_evidence = current_evidence_report(self.reporter)
        current_evidence["command"] = [
            sys.executable,
            "tools/run-native-closure-validation.py",
            "--batch",
            "old-current-evidence-gate",
            "--format",
            "json",
        ]

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["returncode"] = 1

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_current_evidence_gate_ready_rejects_summary_or_result_envelope_drift(self):
        current_evidence = current_evidence_report(self.reporter)
        current_evidence["summary"]["batch"] = "old-current-evidence-gate"

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["summary"]["test_count"] = 2

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["summary"]["failed_count"] = 1

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["results"][0]["ok"] = False

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["results"][0]["status"] = "failed"

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence = current_evidence_report(self.reporter)
        current_evidence["results"][0]["returncode"] = 1

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_current_evidence_gate_ready_requires_transport_release_parity_summary(self):
        current_evidence = current_evidence_report(self.reporter)
        current_evidence["results"] = []

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

        current_evidence["results"] = [
            transport_release_parity_result(complete=False, missing_count=1, matched_count=0)
        ]

        self.assertFalse(self.reporter.current_evidence_gate_ready(current_evidence))

    def test_runtime_peer_backpressure_ready_requires_current_envelope(self):
        peer = runtime_peer_backpressure_report(self.reporter)

        self.assertTrue(self.reporter.runtime_peer_backpressure_gate_ready(peer))

        peer = runtime_peer_backpressure_report(self.reporter)
        peer["command"] = list(peer["command"])
        peer["command"][3] = "old-runtime-peer-backpressure"

        self.assertFalse(self.reporter.runtime_peer_backpressure_gate_ready(peer))

        peer = runtime_peer_backpressure_report(self.reporter)
        peer["returncode"] = 1

        self.assertFalse(self.reporter.runtime_peer_backpressure_gate_ready(peer))

        peer = runtime_peer_backpressure_report(self.reporter)
        peer["summary"]["batch"] = "old-runtime-peer-backpressure"

        self.assertFalse(self.reporter.runtime_peer_backpressure_gate_ready(peer))

        peer = runtime_peer_backpressure_report(self.reporter)
        peer["groups"]["runtime-fairness-peer-backpressure-current"]["status"] = "failed"

        self.assertFalse(self.reporter.runtime_peer_backpressure_gate_ready(peer))

        peer = runtime_peer_backpressure_report(self.reporter)
        peer["results"][0]["summary"]["opensearch_http_429_count"] = 0

        self.assertFalse(self.reporter.runtime_peer_backpressure_gate_ready(peer))

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
                "pit_e2e_coverage",
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
        self.assertIn(
            "--benchmark-comparison-summary",
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
            (temp_dir / "benchmark-comparison-summary.json").write_text(
                json.dumps(valid_benchmark_comparison_summary()),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(release_readiness_manifest_items(artifacts)),
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
                json.dumps(release_readiness_manifest_items(artifacts)),
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
                current_evidence=current_evidence_report(self.reporter),
                peer_backpressure=runtime_peer_backpressure_report(self.reporter),
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
                json.dumps(release_readiness_manifest_items(artifacts)),
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

    def test_cli_can_reuse_existing_current_evidence_report_for_final_cutover_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            current_report = temp_dir / "current-native-closure-status.json"
            output = temp_dir / "native-closure-status.json"
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
            current_report.write_text(
                json.dumps(
                    {
                        "gates": {
                            "current_evidence": current_evidence_report(self.reporter),
                            "runtime_peer_backpressure_current": runtime_peer_backpressure_report(self.reporter),
                        }
                    }
                ),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(release_readiness_manifest_items(artifacts)),
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

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPORT_PATH),
                    "--current-evidence-report",
                    str(current_report),
                    "--release-readiness-file",
                    str(manifest),
                    "--readiness-report",
                    str(readiness),
                    "--release-evidence-root",
                    str(temp_dir),
                    "--release-evidence-max-age-seconds",
                    "60",
                    "--require-final-cutover",
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
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["current_evidence_ready"])
            self.assertTrue(payload["summary"]["runtime_peer_backpressure_ready"])
            self.assertTrue(payload["summary"]["final_cutover_ready"])
            self.assertTrue(payload["summary"]["final_cutover_required"])
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["status"], "ready")
            self.assertEqual(
                payload["gates"]["final_cutover"]["release_record_missing_items"],
                [],
            )
            self.assertEqual(
                payload["gates"]["current_evidence"]["results"][0]["summary"][
                    "release_parity_source_matched_action_count"
                ],
                174,
            )

    def test_cli_writes_status_report_to_output_path(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            output = temp_dir / "nested" / "native-closure-status.json"
            current_report = temp_dir / "current-native-closure-status.json"
            current_report.write_text(
                json.dumps(
                    {
                        "gates": {
                            "current_evidence": current_evidence_report(self.reporter),
                            "runtime_peer_backpressure_current": runtime_peer_backpressure_report(self.reporter),
                        }
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPORT_PATH),
                    "--current-evidence-report",
                    str(current_report),
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
    inventory = load_inventory_module()
    (temp_dir / artifacts["benchmark_coverage"]).write_text(
        "".join(
            json.dumps(
                {
                    "benchmark": name,
                    "operations": 2,
                    "elapsed_nanos": 100,
                    "nanos_per_operation": 50,
                },
                sort_keys=True,
            )
            + "\n"
            for name in sorted(inventory.REQUIRED_BENCHMARKS)
        ),
        encoding="utf-8",
    )
    (temp_dir / "benchmark-comparison-summary.json").write_text(
        json.dumps(valid_benchmark_comparison_summary()),
        encoding="utf-8",
    )
    (temp_dir / artifacts["load_test_coverage"]).write_text(
        json.dumps(valid_load_payload(inventory)),
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
                    "step_count": len(inventory.REQUIRED_ROLLING_UPGRADE_STEPS),
                    "transcript_step_count": len(inventory.REQUIRED_ROLLING_UPGRADE_STEPS),
                },
                "transcript": {
                    "profile": "rolling-upgrade",
                    "status": "completed",
                    "steps": inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                    "transcript": inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                    "transcript_assertions": inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS,
                },
                "assertion_hits": {
                    assertion: True
                    for assertion in inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS
                },
            }
        ),
        encoding="utf-8",
    )
    checks = [
        {"name": name, "status": "ok", "returncode": 0}
        for name in sorted(inventory.REQUIRED_PROMOTION_GATE_CHECKS)
    ]
    (temp_dir / "promotion-gate-suite-current.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "passed": len(checks),
                "failed": 0,
                "checks": checks,
            }
        ),
        encoding="utf-8",
    )
    pit_dir = temp_dir / "unified-opensearch-e2e-pit-current"
    pit_dir.mkdir()
    pit_cases = {
        "search-compat": [
            "msearch_pit_snapshot_after_update_delete_search",
            "pit_clear_search",
            "pit_list_search",
            "pit_open_search",
            "pit_search",
            "pit_search_after_close_missing_context",
            "pit_shard_doc_search_after_search",
            "pit_snapshot_after_update_delete_search",
        ],
        "search-strict": [
            "pit_clear_search",
            "pit_list_search",
            "pit_open_search",
            "pit_search",
            "pit_search_after_close_missing_context",
            "pit_shard_doc_search_after_search",
            "pit_snapshot_after_update_delete_search",
        ],
        "search-semantic": [
            "pit_search_after_close_missing_context_semantic",
            "pit_snapshot_after_update_delete_semantic",
        ],
    }
    (pit_dir / "unified-opensearch-e2e-report.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "suite_results": [
                    {
                        "name": suite_name,
                        "status": "ok",
                        "has_opensearch_target": True,
                        "passed_cases": cases,
                        "case_gaps": {
                            "extra": [],
                            "fail_closed": [],
                            "failed": [],
                            "missing": [],
                            "skipped": [],
                        },
                    }
                    for suite_name, cases in pit_cases.items()
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


def valid_load_payload(inventory) -> dict:
    operations = {
        name: {
            "success_count": 2,
            "error_count": 0,
            "error_examples": [],
            "latency_ms": {
                "count": 2,
                "min": 1.0,
                "p50": 1.1,
                "p90": 1.2,
                "p95": 1.3,
                "p99": 1.4,
                "mean": 1.15,
                "max": 1.5,
            },
        }
        for name in sorted(inventory.REQUIRED_LOAD_OPERATIONS)
    }
    return {
        "summary": {
            "passed": True,
            "error_count": 0,
            "error_rate": 0.0,
            "operation_count": sum(item["success_count"] for item in operations.values()),
            "success_count": sum(item["success_count"] for item in operations.values()),
            "elapsed_seconds": 1.0,
            "throughput_ops_per_second": 18.0,
        },
        "operations": operations,
        "resource_usage": {
            name: {"before": 1, "after": 2, "delta": 1, "peak": 2}
            for name in sorted(inventory.REQUIRED_LOAD_RESOURCE_COUNTERS)
        },
    }


def release_readiness_manifest_items(artifacts: dict[str, str]) -> dict[str, dict]:
    inventory = load_inventory_module()
    items = {
        name: {
            "passed": True,
            "artifact_path": artifact,
            "blockers": [],
            "summary": {"passed": True},
        }
        for name, artifact in artifacts.items()
    }
    items["benchmark_coverage"].update(
        {
            "record_count": len(inventory.REQUIRED_BENCHMARKS),
            "benchmarks": sorted(inventory.REQUIRED_BENCHMARKS),
            "comparison_summary_path": "benchmark-comparison-summary.json",
            "comparison_summary": {
                "operation_ratio_count": 2,
                "rss_peak_ratio_count": 2,
                "topologies": ["single-node", "three-node"],
            },
        }
    )
    return items


def valid_benchmark_comparison_summary() -> dict:
    operation = {
        "throughput_ops_per_second": {"steelsearch": 1.0, "opensearch": 2.0, "ratio": 0.5},
        "p50_ms": {"steelsearch": 2.0, "opensearch": 1.0, "ratio": 2.0},
        "p95_ms": {"steelsearch": 3.0, "opensearch": 1.5, "ratio": 2.0},
        "p99_ms": {"steelsearch": 4.0, "opensearch": 2.0, "ratio": 2.0},
        "mean_ms": {"steelsearch": 2.5, "opensearch": 1.25, "ratio": 2.0},
    }
    topology = {
        "throughput_ops_per_second": {"steelsearch": 1.0, "opensearch": 2.0, "ratio": 0.5},
        "resource_usage": {
            "memory_rss_bytes": {
                "peak": {"steelsearch": 100, "opensearch": 200, "ratio": 0.5}
            }
        },
        "operations": {"lexical": operation},
    }
    return {
        "comparisons": {
            "single-node": topology,
            "three-node": json.loads(json.dumps(topology)),
        }
    }


if __name__ == "__main__":
    unittest.main()
