import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run-unified-opensearch-e2e.py"
CHECKER_PATH = ROOT / "tools" / "check-unified-opensearch-e2e-report.py"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class UnifiedOpenSearchE2EReportTests(unittest.TestCase):
    def test_suite_with_missing_fixture_case_is_missing_not_ok(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}, {"name": "uncovered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
                "cases": [{"name": "covered", "status": "passed"}],
            },
        )

        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["classification"]["missing"], 1)
        self.assertEqual(result["case_gaps"]["missing"], ["uncovered"])

    def test_suite_with_extra_report_case_is_not_missing_fixture_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_extra_case")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {"name": "covered", "status": "passed"},
                    {"name": "stale-extra", "status": "passed"},
                ],
            },
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["classification"]["missing"], 0)
        self.assertEqual(result["classification"]["canonical_equal"], 1)
        self.assertEqual(result["case_gaps"]["extra"], ["stale-extra"])

    def test_checker_rejects_required_suite_with_missing_case_without_allow_missing(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_report")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "missing",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "missing",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 1,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 0,
                    "missing": 1,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "missing",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 1,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 0,
                        "failed": 0,
                        "missing": 1,
                    },
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("report has missing required suite evidence", errors)
        self.assertIn("synthetic: missing fixture case evidence", errors)

    def test_checker_rejects_required_skips_when_requested(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_no_skips")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "semantic_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 0,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 1,
                    "failed": 0,
                    "missing": 0,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "ok",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 0,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 1,
                        "failed": 0,
                        "missing": 0,
                    },
                }
            ],
        }

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_skips=True,
        )

        self.assertIn("synthetic: skipped required fixture cases", errors)

    def test_rerun_commands_include_missing_cases(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_rerun")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            "tools/search_compat.py",
            "tools/fixtures/search-compat.json",
            "synthetic-report.json",
            output_arg="--report",
        )

        commands = runner.suite_rerun_commands(
            suite,
            Path("target/e2e"),
            {"missing": ["case-a", "case-b"]},
        )

        self.assertIn("--case case-a --case case-b", commands["unified_command"])
        self.assertIn("--case case-a --case case-b", commands["direct_command"])

    def test_merge_case_reports_preserves_existing_cases_and_recomputes_summary(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_merge")
        base = {
            "name": "synthetic",
            "fixture": "/tmp/fixture.json",
            "targets": {"steelsearch": "old", "opensearch": "old"},
            "summary": {"passed": 1, "failed": 1, "skipped": 0},
            "cases": [
                {"name": "existing-pass", "status": "passed", "area": "search"},
                {"name": "rerun-me", "status": "failed", "area": "search"},
            ],
        }
        partial = {
            "targets": {"steelsearch": "new", "opensearch": "new"},
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "cases": [
                {"name": "rerun-me", "status": "passed", "area": "search"},
            ],
        }

        merged = runner.merge_case_reports(base, partial)

        cases = {case["name"]: case for case in merged["cases"]}
        self.assertEqual(cases["existing-pass"]["status"], "passed")
        self.assertEqual(cases["rerun-me"]["status"], "passed")
        self.assertEqual(merged["targets"], {"steelsearch": "new", "opensearch": "new"})
        self.assertEqual(merged["summary"]["passed"], 2)
        self.assertEqual(merged["summary"]["failed"], 0)
        self.assertEqual(merged["summary"]["skipped"], 0)
        self.assertEqual(merged["summary"]["by_area"]["search"]["passed"], 2)

    def test_load_best_report_prefers_complete_passing_report_over_newer_failed_report(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_best_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" },
    { "name": "case-b" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "nested"
            recursive_dir.mkdir(parents=True)
            passing_report = output_dir / "synthetic-report.json"
            failed_report = recursive_dir / "synthetic-report.json"
            passing_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 2, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" },
    { "name": "case-b", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            time.sleep(0.01)
            failed_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 1, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" },
    { "name": "case-b", "status": "failed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, passing_report)
            self.assertEqual(source, "output-dir")
            self.assertIsNone(unusable)
            self.assertEqual(report["summary"]["failed"], 0)

    def test_search_compat_suite_collects_generic_harness_report_name_by_fixture(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_generic_search_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "search-strict-compat.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "strict-case" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "strict-harness" / "compare"
            recursive_dir.mkdir(parents=True)
            generic_report = recursive_dir / "search-compat-report.json"
            generic_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "strict-case", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    ("search-strict-compat-report.json", "search-compat-report.json"),
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, generic_report)
            self.assertEqual(source, "target-recursive")
            self.assertIsNone(unusable)
            self.assertEqual(report["summary"]["passed"], 1)

    def test_load_best_report_rejects_stale_complete_report_when_age_gate_is_set(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_stale_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            stale_report = output_dir / "synthetic-report.json"
            stale_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            stale_mtime = time.time() - 120.0
            os.utime(stale_report, (stale_mtime, stale_mtime))

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                    max_report_age_seconds=60.0,
                )
                result = runner.collect_suite(
                    runner.Suite(
                        "synthetic",
                        "search",
                        "semantic_parity",
                        None,
                        str(fixture_path),
                        "synthetic-report.json",
                    ),
                    output_dir,
                    max_report_age_seconds=60.0,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, stale_report)
            self.assertIsNone(source)
            self.assertIsNone(report)
            self.assertIsNone(unusable)
            self.assertEqual(result["status"], "missing")
            self.assertEqual(result["report_source"], "missing")
            self.assertIn("max_report_age_seconds=60", result["note"])


if __name__ == "__main__":
    unittest.main()
