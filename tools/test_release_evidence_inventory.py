import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "tools" / "report-release-evidence-inventory.py"


def load_inventory_module():
    module_name = "report_release_evidence_inventory"
    spec = importlib.util.spec_from_file_location(module_name, INVENTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def promotion_gate_command(name: str) -> str:
    commands = {
        "benchmark-evidence": (
            "tools/check-benchmark-evidence.py --jsonl "
            "target/release-benchmarks/deterministic-benchmark-baselines.jsonl "
            "--report target/release-benchmarks/benchmark-report.json "
            "--comparison-summary target/search-benchmark-matrix-current-20260630T023334Z/summary.json "
            "--max-age-seconds 604800"
        ),
        "broad-unified-e2e-sections": (
            "tools/check-unified-opensearch-e2e-report.py "
            "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json "
            "--max-report-age-seconds 604800 --require-no-unresolved-skips "
            "--require-section route_parity --require-section semantic_parity "
            "--require-section durability_parity --require-section security_parity "
            "--require-section distributed_parity"
        ),
        "mixed-cluster-coverage": (
            "tools/report-mixed-cluster-coverage.py --require-passed "
            "--max-report-age-seconds 604800 --shard-movement-report "
            "target/three-node-shard-movement-interruption-current/report.json "
            "--output target/mixed-cluster-coverage-current-check.json"
        ),
        "peer-node": "tools/check-peer-node-promotion-gate.py --max-report-age-seconds 604800",
        "pit-e2e-coverage": (
            "tools/check-pit-e2e-coverage.py "
            "target/unified-opensearch-e2e-pit-current/unified-opensearch-e2e-report.json "
            "--max-report-age-seconds 604800 --require-all-pit-passed"
        ),
        "rest-api-live-source-coverage": (
            "tools/report-rest-api-coverage.py --unified-report "
            "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json "
            "--max-report-age-seconds 604800 --require-live-required-suites "
            "--min-live-required-matched-source-route-count 379 "
            "--min-live-required-matched-source-route-ratio 1.0 "
            "--min-source-route-count 389 --require-closed-source-statuses "
            "--output target/rest-api-coverage-current-check.json"
        ),
        "transport-action-coverage": (
            "tools/report-transport-action-coverage.py --require-peer-backpressure "
            "--require-release-parity --require-closed-action-statuses "
            "--max-report-age-seconds 604800 --output "
            "target/transport-action-coverage-current-check.json"
        ),
    }
    if name in commands:
        return commands[name]
    return f"tools/check-{name}.py"


class ReleaseEvidenceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = load_inventory_module()

    def test_complete_inventory_reports_all_readiness_items_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            for name in [
                "final-packaging.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))
            self.write_valid_benchmark(temp_dir / "final-benchmark.jsonl", now)
            self.write_valid_chaos(temp_dir / "final-chaos.json", now)
            self.write_valid_load(temp_dir / "final-load-baseline.json", now)
            self.write_valid_load_comparison(temp_dir / "final-load-comparison.json", now)
            self.write_valid_pit_e2e(
                temp_dir / "unified-opensearch-e2e-pit-current" / "unified-opensearch-e2e-report.json",
                now,
            )
            self.write_valid_promotion_gate_suite(
                temp_dir / "promotion-gate-suite-current.json", now
            )
            self.write_valid_rolling_upgrade(temp_dir / "final-rolling-upgrade.json", now)

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=True,
                now=now,
            )

            self.assertTrue(report["summary"]["passed"])
            self.assertTrue(report["summary"]["complete"])
            self.assertEqual(report["summary"]["startup_ready_item_count"], 5)
            self.assertEqual(report["summary"]["readiness_attachment_ready_item_count"], 6)
            self.assertEqual(report["summary"]["release_record_ready_item_count"], 8)
            self.assertEqual(report["summary"]["startup_missing_items"], [])
            self.assertEqual(report["summary"]["readiness_attachment_missing_items"], [])
            self.assertEqual(report["summary"]["release_record_missing_items"], [])
            self.assertIn("--load-comparison-report", report["attach_command_template"])
            self.assertNotIn("promotion_gate_suite", report["attach_command_template"])

    def test_inventory_distinguishes_startup_and_readiness_only_missing_items(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            for name in [
                "final-packaging.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))
            self.write_valid_benchmark(temp_dir / "final-benchmark.jsonl", now)
            self.write_valid_chaos(temp_dir / "final-chaos.json", now)
            self.write_valid_load(temp_dir / "final-load-baseline.json", now)
            self.write_valid_pit_e2e(
                temp_dir / "unified-opensearch-e2e-pit-current" / "unified-opensearch-e2e-report.json",
                now,
            )
            self.write_valid_promotion_gate_suite(
                temp_dir / "promotion-gate-suite-current.json", now
            )
            self.write_valid_rolling_upgrade(temp_dir / "final-rolling-upgrade.json", now)

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=True,
                now=now,
            )

            self.assertFalse(report["summary"]["passed"])
            self.assertEqual(report["summary"]["startup_ready_item_count"], 5)
            self.assertEqual(report["summary"]["readiness_attachment_ready_item_count"], 5)
            self.assertEqual(report["summary"]["release_record_ready_item_count"], 7)
            self.assertEqual(report["summary"]["startup_missing_items"], [])
            self.assertEqual(
                report["summary"]["readiness_attachment_missing_items"],
                ["load_comparison"],
            )
            self.assertEqual(
                report["summary"]["release_record_missing_items"],
                ["load_comparison"],
            )

    def test_inventory_rejects_failed_promotion_gate_suite(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            suite.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "passed": 16,
                        "failed": 1,
                        "checks": [
                            {"name": "search", "status": "ok", "returncode": 0},
                            {"name": "transport", "status": "failed", "returncode": 1},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertFalse(item["ready"])
            self.assertIn("promotion gate suite status mismatch: failed", item["blockers"])
            self.assertIn("promotion gate suite failed=1", item["blockers"])
            self.assertIn("promotion gate suite has failed checks: transport", item["blockers"])

    def test_inventory_rejects_promotion_gate_suite_missing_required_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            checks = [
                {
                    "name": name,
                    "command": promotion_gate_command(name),
                    "status": "ok",
                    "returncode": 0,
                }
                for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
                if name != "benchmark-evidence"
            ]
            suite.write_text(
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
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "promotion gate suite missing required checks: benchmark-evidence",
                item["blockers"],
            )

    def test_inventory_accepts_optional_release_evidence_self_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            checks = [
                {
                    "name": name,
                    "command": promotion_gate_command(name),
                    "status": "ok",
                    "returncode": 0,
                }
                for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
            ]
            checks.append(
                {
                    "name": "release-evidence-inventory",
                    "status": "ok",
                    "returncode": 0,
                }
            )
            suite.write_text(
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
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertTrue(item["ready"])
            self.assertEqual(item["blockers"], [])

    def test_inventory_rejects_peer_node_suite_without_freshness_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            checks = [
                {
                    "name": name,
                    "command": promotion_gate_command(name),
                    "status": "ok",
                    "returncode": 0,
                }
                for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
            ]
            for check in checks:
                if check["name"] == "peer-node":
                    check["command"] = "tools/check-peer-node-promotion-gate.py"
            suite.write_text(
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
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "promotion gate suite check [peer-node] command missing required fragment(s): --max-report-age-seconds, 604800",
                item["blockers"],
            )

    def test_inventory_rejects_transport_suite_without_release_parity_gate(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            checks = [
                {
                    "name": name,
                    "command": promotion_gate_command(name),
                    "status": "ok",
                    "returncode": 0,
                }
                for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
            ]
            for check in checks:
                if check["name"] == "transport-action-coverage":
                    check["command"] = (
                        "tools/report-transport-action-coverage.py "
                        "--require-peer-backpressure --max-report-age-seconds 604800"
                    )
            suite.write_text(
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
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "promotion gate suite check [transport-action-coverage] command missing required fragment(s): --require-release-parity, --require-closed-action-statuses",
                item["blockers"],
            )

    def test_inventory_rejects_command_fragment_prefix_match_only(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            suite = temp_dir / "promotion-gate-suite-current.json"
            checks = [
                {
                    "name": name,
                    "command": promotion_gate_command(name),
                    "status": "ok",
                    "returncode": 0,
                }
                for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
            ]
            for check in checks:
                if check["name"] == "peer-node":
                    check["command"] = (
                        "tools/check-peer-node-promotion-gate.py "
                        "--max-report-age-seconds 6048000"
                    )
            suite.write_text(
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
            os.utime(suite, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["promotion_gate_suite"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "promotion gate suite check [peer-node] command missing required fragment(s): 604800",
                item["blockers"],
            )

    def test_inventory_rejects_pit_e2e_missing_required_case(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            report_path = (
                temp_dir
                / "unified-opensearch-e2e-pit-current"
                / "unified-opensearch-e2e-report.json"
            )
            self.write_valid_pit_e2e(report_path, now, missing_case="pit_search")

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["pit_e2e_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "PIT E2E suite missing passed required cases [search-compat]: pit_search",
                item["blockers"],
            )

    def test_inventory_rejects_pit_e2e_skipped_required_case(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            report_path = (
                temp_dir
                / "unified-opensearch-e2e-pit-current"
                / "unified-opensearch-e2e-report.json"
            )
            self.write_valid_pit_e2e(report_path, now, skipped_case="pit_search")

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["pit_e2e_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "PIT E2E suite missing passed required cases [search-compat]: pit_search",
                item["blockers"],
            )
            self.assertIn(
                "PIT E2E suite has skipped required cases [search-compat]: pit_search",
                item["blockers"],
            )

    def test_inventory_accepts_targeted_pit_report_with_missing_top_level_status(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            report_path = (
                temp_dir
                / "unified-opensearch-e2e-pit-current"
                / "unified-opensearch-e2e-report.json"
            )
            self.write_valid_pit_e2e(
                report_path,
                now,
                non_pit_missing_case="cat_count_json",
                top_level_status="missing",
            )
            self.write_broad_e2e_with_passed_cases(
                temp_dir,
                now,
                {"search-strict": {"cat_count_json": "strict_equal"}},
            )

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["pit_e2e_coverage"]
            self.assertTrue(item["ready"])
            self.assertEqual(item["blockers"], [])
            self.assertEqual(item["diagnostics"]["unified_report_status"], "missing")
            self.assertEqual(item["diagnostics"]["required_pit_passed_count"], 17)
            self.assertEqual(item["diagnostics"]["required_pit_case_count"], 17)
            self.assertEqual(item["diagnostics"]["non_pit_case_gap_counts"]["missing"], 1)
            self.assertEqual(
                item["diagnostics"]["non_pit_case_gap_names"]["missing"],
                ["search-strict:cat_count_json"],
            )
            resolution = item["diagnostics"]["non_pit_case_gap_broad_e2e_resolution"]
            self.assertEqual(resolution["resolved_counts"]["missing"], 1)
            self.assertEqual(
                resolution["resolved_names"]["missing"],
                ["search-strict:cat_count_json=strict_equal"],
            )

    def test_inventory_rejects_structurally_invalid_latest_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            load = temp_dir / "final-load-baseline.json"
            load.write_text(
                json.dumps({"summary": {"error_count": 1, "operation_count": 10}}),
                encoding="utf-8",
            )
            os.utime(load, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_test_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn("load JSON summary.error_count=1", item["blockers"])

    def test_inventory_rejects_load_report_missing_required_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            load = temp_dir / "final-load-baseline.json"
            payload = self.valid_load_payload()
            payload["operations"].pop("hybrid")
            load.write_text(json.dumps(payload), encoding="utf-8")
            os.utime(load, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_test_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn("load JSON operations are missing: hybrid", item["blockers"])

    def test_inventory_rejects_dry_run_load_comparison(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            comparison = temp_dir / "final-load-comparison.json"
            comparison.write_text(
                json.dumps(
                    {
                        "targets": {
                            "steelsearch": {"returncode": 0},
                            "opensearch": {"returncode": 0},
                        },
                        "comparison": {"mode": "dry-run"},
                    }
                ),
                encoding="utf-8",
            )
            os.utime(comparison, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_comparison"]
            self.assertFalse(item["ready"])
            self.assertIn("load comparison is a dry-run report", item["blockers"])

    def test_inventory_rejects_failed_rolling_upgrade_assertion_hit(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            rolling = temp_dir / "final-rolling-upgrade.json"
            rolling.write_text(
                json.dumps(
                    {
                        "ready": True,
                        "passed": True,
                        "blockers": [],
                        "summary": {
                            "passed": True,
                            "error_count": 0,
                            "coverage_scope": "rolling-upgrade transcript fixture",
                            "step_count": 7,
                            "transcript_step_count": 7,
                        },
                        "transcript": {
                            "profile": "rolling-upgrade",
                            "status": "completed",
                            "steps": self.inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                            "transcript": self.inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                            "transcript_assertions": self.inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS,
                        },
                        "assertion_hits": {
                            "cluster ready before upgrade sequence": True,
                            "upgrade steps recorded in order": True,
                            "cluster ready after each upgraded node rejoins": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            os.utime(rolling, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["rolling_upgrade_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "rolling-upgrade assertion_hits failed: cluster ready after each upgraded node rejoins",
                item["blockers"],
            )

    def test_inventory_rejects_rolling_upgrade_without_transcript_steps(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            rolling = temp_dir / "final-rolling-upgrade.json"
            rolling.write_text(
                json.dumps(
                    {
                        "ready": True,
                        "passed": True,
                        "blockers": [],
                        "summary": {
                            "passed": True,
                            "error_count": 0,
                            "coverage_scope": "rolling-upgrade transcript fixture",
                            "step_count": 7,
                            "transcript_step_count": 0,
                        },
                        "transcript": {
                            "profile": "rolling-upgrade",
                            "status": "completed",
                        },
                        "assertion_hits": {
                            assertion: True
                            for assertion in self.inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS
                        },
                    }
                ),
                encoding="utf-8",
            )
            os.utime(rolling, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["rolling_upgrade_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn("rolling-upgrade summary.transcript_step_count mismatch", item["blockers"])
            self.assertIn("rolling-upgrade transcript steps mismatch", item["blockers"])
            self.assertIn("rolling-upgrade transcript execution order mismatch", item["blockers"])
            self.assertIn("rolling-upgrade transcript assertions mismatch", item["blockers"])

    def test_inventory_rejects_chaos_source_failed_child_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            chaos = temp_dir / "final-chaos.json"
            chaos.write_text(
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
                                "failure_ledger_passed": False,
                                "pit_restart_lifecycle_passed": True,
                                "pit_transport_restart_lifecycle_passed": True,
                                "pit_multi_daemon_lifecycle_passed": True,
                            },
                            "executed_tests": [
                                "daemon_point_in_time_contexts_do_not_survive_restart",
                                "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                                "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                            ],
                            "child_executed_tests": {
                                "pit_restart_lifecycle_report": [
                                    "daemon_point_in_time_contexts_do_not_survive_restart"
                                ],
                                "pit_transport_restart_lifecycle_report": [
                                    "daemon_transport_point_in_time_contexts_do_not_survive_restart"
                                ],
                                "pit_multi_daemon_lifecycle_report": [
                                    "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                                ],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            os.utime(chaos, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["chaos_test_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "chaos source_report check is not true: failure_ledger_passed",
                item["blockers"],
            )

    def test_inventory_rejects_chaos_child_executed_test_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            chaos = temp_dir / "final-chaos.json"
            chaos.write_text(
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
                                "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                            ],
                            "child_executed_tests": {
                                "pit_restart_lifecycle_report": [
                                    "daemon_point_in_time_contexts_do_not_survive_restart"
                                ],
                                "pit_transport_restart_lifecycle_report": [
                                    "daemon_transport_point_in_time_contexts_do_not_survive_restart"
                                ],
                                "pit_multi_daemon_lifecycle_report": [],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            os.utime(chaos, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["chaos_test_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "chaos source_report pit_multi_daemon_lifecycle_report executed_tests are missing: multi_daemon_get_all_pits_fans_out_to_seed_peers",
                item["blockers"],
            )
            self.assertIn(
                "chaos source_report executed_tests do not match child_executed_tests",
                item["blockers"],
            )

    def test_inventory_ignores_cargo_fingerprint_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            fingerprint = (
                temp_dir
                / "debug"
                / ".fingerprint"
                / "os-transport-abc"
                / "bin-nodes-reload-secure-settings-reject-wire-benchmark.json"
            )
            fingerprint.parent.mkdir(parents=True)
            fingerprint.write_text(
                json.dumps({"summary": {"error_count": 0, "operation_count": 1}}),
                encoding="utf-8",
            )
            os.utime(fingerprint, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_test_coverage"]
            self.assertEqual(item["candidate_count"], 0)
            self.assertFalse(item["ready"])
            self.assertIn("artifact candidate is missing", item["blockers"])

    def test_inventory_ignores_load_server_log_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            log = temp_dir / "opensearch-release-load_server.json"
            log.write_text(
                json.dumps({"type": "server", "message": "started"}) + "\n"
                + json.dumps({"type": "server", "message": "stopped"}) + "\n",
                encoding="utf-8",
            )
            os.utime(log, (now, now))
            self.write_valid_load(temp_dir / "http-load-baseline.json", now - 1)

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_test_coverage"]
            self.assertTrue(item["ready"])
            self.assertEqual(item["candidate_count"], 1)
            self.assertTrue(item["latest_artifact_path"].endswith("http-load-baseline.json"))

    def test_inventory_rejects_benchmark_missing_expected_record(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            benchmark = temp_dir / "final-benchmark.jsonl"
            records = [
                {
                    "benchmark": name,
                    "operations": 2,
                    "elapsed_nanos": 100,
                    "nanos_per_operation": 50,
                }
                for name in sorted(self.inventory.REQUIRED_BENCHMARKS)
                if name != "hybrid_search"
            ]
            benchmark.write_text(
                "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
                encoding="utf-8",
            )
            os.utime(benchmark, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["benchmark_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn(
                "benchmark JSONL is missing expected records: hybrid_search",
                item["blockers"],
            )

    def test_cli_returns_nonzero_when_complete_inventory_is_required(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            result = subprocess.run(
                [
                    sys.executable,
                    str(INVENTORY_PATH),
                    "--root",
                    temp_dir_value,
                    "--require-complete",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("benchmark_coverage", result.stdout)

    def write_valid_benchmark(self, path: Path, now: float):
        records = [
            {
                "benchmark": name,
                "operations": 2,
                "elapsed_nanos": 100,
                "nanos_per_operation": 50,
            }
            for name in sorted(self.inventory.REQUIRED_BENCHMARKS)
        ]
        path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_valid_load(self, path: Path, now: float):
        path.write_text(json.dumps(self.valid_load_payload()), encoding="utf-8")
        os.utime(path, (now, now))

    def valid_load_payload(self) -> dict:
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
            for name in sorted(self.inventory.REQUIRED_LOAD_OPERATIONS)
        }
        return {
            "summary": {
                "passed": True,
                "error_count": 0,
                "error_rate": 0.0,
                "operation_count": 18,
                "success_count": 18,
                "elapsed_seconds": 1.0,
                "throughput_ops_per_second": 18.0,
            },
            "operations": operations,
            "resource_usage": {
                "memory_rss_bytes": {
                    "before": 1,
                    "after": 2,
                    "delta": 1,
                    "peak": 2,
                },
                "vector_cache_bytes": {
                    "before": 0,
                    "after": 0,
                    "delta": 0,
                    "peak": None,
                },
                "operation_log_bytes": {
                    "before": 0,
                    "after": 0,
                    "delta": 0,
                    "peak": None,
                },
            },
        }

    def write_valid_chaos(self, path: Path, now: float):
        path.write_text(
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
                            "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                        ],
                        "child_executed_tests": {
                            "pit_restart_lifecycle_report": [
                                "daemon_point_in_time_contexts_do_not_survive_restart"
                            ],
                            "pit_transport_restart_lifecycle_report": [
                                "daemon_transport_point_in_time_contexts_do_not_survive_restart"
                            ],
                            "pit_multi_daemon_lifecycle_report": [
                                "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                            ],
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_valid_load_comparison(self, path: Path, now: float):
        path.write_text(
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
        os.utime(path, (now, now))

    def write_valid_rolling_upgrade(self, path: Path, now: float):
        path.write_text(
            json.dumps(
                {
                    "ready": True,
                    "passed": True,
                    "blockers": [],
                    "summary": {
                        "passed": True,
                        "error_count": 0,
                        "coverage_scope": "rolling-upgrade transcript fixture",
                        "step_count": 7,
                        "transcript_step_count": 7,
                    },
                    "transcript": {
                        "profile": "rolling-upgrade",
                        "status": "completed",
                        "steps": self.inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                        "transcript": self.inventory.REQUIRED_ROLLING_UPGRADE_STEPS,
                        "transcript_assertions": self.inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS,
                    },
                    "assertion_hits": {
                        assertion: True
                        for assertion in self.inventory.REQUIRED_ROLLING_UPGRADE_ASSERTIONS
                    },
                }
            ),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_valid_pit_e2e(
        self,
        path: Path,
        now: float,
        *,
        missing_case: str | None = None,
        non_pit_missing_case: str | None = None,
        skipped_case: str | None = None,
        top_level_status: str = "ok",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        suite_results = []
        for suite_name, required_cases in self.inventory.REQUIRED_PIT_CASES.items():
            passed_cases = sorted(
                case
                for case in required_cases
                if case != missing_case and case != skipped_case
            )
            skipped = [skipped_case] if skipped_case in required_cases else []
            suite_results.append(
                {
                    "name": suite_name,
                    "status": "ok",
                    "has_opensearch_target": True,
                    "passed_cases": passed_cases,
                    "case_gaps": {
                        "extra": [],
                        "fail_closed": [],
                        "failed": [],
                        "missing": (
                            [missing_case]
                            if missing_case in required_cases
                            else (
                                [non_pit_missing_case]
                                if non_pit_missing_case and suite_name == "search-strict"
                                else []
                            )
                        ),
                        "skipped": skipped,
                    },
                }
            )
        path.write_text(
            json.dumps({"status": top_level_status, "suite_results": suite_results}),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_broad_e2e_with_passed_cases(
        self,
        root: Path,
        now: float,
        cases_by_suite: dict[str, dict[str, str]],
    ):
        path = (
            root
            / "unified-opensearch-e2e-broad-current"
            / "unified-opensearch-e2e-report.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        suite_results = []
        for suite_name, cases in sorted(cases_by_suite.items()):
            classification_cases: dict[str, list[str]] = {}
            for case_name, classification in sorted(cases.items()):
                classification_cases.setdefault(classification, []).append(case_name)
            suite_results.append(
                {
                    "name": suite_name,
                    "status": "ok",
                    "passed_cases": sorted(cases),
                    "classification_cases": classification_cases,
                }
            )
        path.write_text(
            json.dumps({"status": "ok", "suite_results": suite_results}),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_valid_promotion_gate_suite(self, path: Path, now: float):
        checks = [
            {
                "name": name,
                "command": promotion_gate_command(name),
                "status": "ok",
                "returncode": 0,
            }
            for name in sorted(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
        ]
        path.write_text(
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
        os.utime(path, (now, now))


if __name__ == "__main__":
    unittest.main()
