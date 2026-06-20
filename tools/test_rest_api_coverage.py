import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-rest-api-coverage.py"


def load_report_module():
    module_name = "report_rest_api_coverage"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RestApiCoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = load_report_module()

    def test_template_source_route_matches_concrete_fixture_path(self):
        source = [
            {
                "status": "implemented",
                "method": "POST",
                "path": "/{index}/_search",
                "source": "ActionModule.java",
                "line": "1",
            },
            {
                "status": "planned",
                "method": "GET",
                "path": "/_cat/shards",
                "source": "ActionModule.java",
                "line": "2",
            },
        ]
        observed = [
            {
                "method": "POST",
                "path": "/logs-000001/_search?size=1",
                "fixture": "fixture.json",
            }
        ]

        coverage = self.report.coverage_for_routes(source, observed)

        self.assertEqual(len(coverage["matched_source_route_keys"]), 1)
        self.assertEqual(
            coverage["uncovered_in_scope_source_routes"],
            [source[1]],
        )

    def test_live_required_fixture_paths_only_uses_ok_required_suites(self):
        report = {
            "suite_results": [
                {
                    "name": "search",
                    "required": True,
                    "status": "ok",
                    "fixture_path": "/tmp/search.json",
                },
                {
                    "name": "optional",
                    "required": False,
                    "status": "ok",
                    "fixture_path": "/tmp/optional.json",
                },
                {
                    "name": "missing",
                    "required": True,
                    "status": "missing",
                    "fixture_path": "/tmp/missing.json",
                },
            ]
        }

        self.assertEqual(
            self.report.live_required_fixture_paths(report),
            [Path("/tmp/search.json")],
        )

    def test_cli_writes_coverage_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            fixtures = temp_dir / "fixtures"
            fixtures.mkdir()
            output = temp_dir / "coverage.json"
            source.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                "implemented\tPOST\t/{index}/_search\tActionModule.java\t1\n"
                "planned\tGET\t/_cat/shards\tActionModule.java\t2\n",
                encoding="utf-8",
            )
            fixture = fixtures / "search.json"
            fixture.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "search",
                                "method": "POST",
                                "path": "/logs-000001/_search",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--fixtures-dir",
                str(fixtures),
                "--output",
                str(output),
            )

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["fixture_matched_source_route_count"], 1)
            self.assertEqual(payload["summary"]["fixture_uncovered_in_scope_route_count"], 1)
            self.assertEqual(payload["summary"]["fixture_matched_source_route_ratio"], 0.5)

    def test_required_suite_errors_can_tolerate_known_gaps_without_tolerating_failures(self):
        report = {
            "suite_results": [
                {
                    "name": "search",
                    "required": True,
                    "status": "ok",
                    "classification": {
                        "passed": 10,
                        "missing": 0,
                        "failed": 0,
                        "known_gap_or_skipped": 2,
                    },
                },
                {
                    "name": "strict",
                    "required": True,
                    "status": "ok",
                    "classification": {
                        "passed": 8,
                        "missing": 0,
                        "failed": 1,
                        "known_gap_or_skipped": 0,
                    },
                },
            ]
        }

        strict_errors = self.report.unified_required_suite_errors(report)
        allowed_gap_errors = self.report.unified_required_suite_errors(
            report,
            allow_known_gaps=True,
        )

        self.assertIn("search: known_gap_or_skipped=2", strict_errors)
        self.assertNotIn("search: known_gap_or_skipped=2", allowed_gap_errors)
        self.assertIn("strict: failed=1", allowed_gap_errors)

    def test_required_suite_classification_totals_required_suites_only(self):
        report = {
            "suite_results": [
                {
                    "required": True,
                    "classification": {
                        "canonical_equal": 3,
                        "strict_equal": 5,
                        "semantic_equal": 7,
                        "steelsearch_fail_closed": 11,
                        "steelsearch_only": 13,
                        "missing": 1,
                        "failed": 2,
                        "known_gap_or_skipped": 4,
                    },
                },
                {
                    "required": False,
                    "classification": {
                        "canonical_equal": 30,
                        "strict_equal": 50,
                        "semantic_equal": 70,
                        "steelsearch_fail_closed": 110,
                        "steelsearch_only": 130,
                        "missing": 10,
                        "failed": 20,
                        "known_gap_or_skipped": 40,
                    },
                },
            ]
        }

        self.assertEqual(
            self.report.required_suite_classification(report),
            {
                "canonical_equal": 3,
                "strict_equal": 5,
                "semantic_equal": 7,
                "steelsearch_fail_closed": 11,
                "steelsearch_only": 13,
                "missing": 1,
                "failed": 2,
                "known_gap_or_skipped": 4,
                "passed": 0,
                "total_equal": 26,
            },
        )

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
