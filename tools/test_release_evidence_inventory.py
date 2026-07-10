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
                        },
                        "transcript": {
                            "profile": "rolling-upgrade",
                            "status": "completed",
                        },
                        "assertion_hits": {
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
        path.write_text(
            json.dumps({"summary": {"error_count": 0, "operation_count": 10}}),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

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
        os.utime(path, (now, now))

    def write_valid_pit_e2e(
        self,
        path: Path,
        now: float,
        *,
        missing_case: str | None = None,
        skipped_case: str | None = None,
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
                        "missing": [missing_case] if missing_case in required_cases else [],
                        "skipped": skipped,
                    },
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
