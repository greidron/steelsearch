import importlib.util
import sys
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


if __name__ == "__main__":
    unittest.main()
