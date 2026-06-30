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
        self.assertEqual(
            coverage["uncovered_in_scope_route_groups"],
            [{"group": "/_cat", "status": "planned", "count": 1}],
        )

    def test_uncovered_route_groups_use_first_stable_api_prefix(self):
        routes = [
            {
                "status": "planned",
                "method": "GET",
                "path": "/{index}/_search",
                "source": "Search.java",
                "line": "1",
            },
            {
                "status": "planned",
                "method": "POST",
                "path": "/{index}/_search",
                "source": "Search.java",
                "line": "2",
            },
            {
                "status": "stubbed",
                "method": "GET",
                "path": "/_cluster/state",
                "source": "Cluster.java",
                "line": "3",
            },
            {
                "status": "planned",
                "method": "GET",
                "path": "String.format(Locale.ROOT, \"/_plugins/_knn/stats\")",
                "source": "Knn.java",
                "line": "4",
            },
            {
                "status": "planned",
                "method": "POST",
                "path": "/{index}/_tier/ + targetTier",
                "source": "Tier.java",
                "line": "5",
            },
            {
                "status": "planned",
                "method": "GET",
                "path": 'KNNPlugin.KNN_BASE_URI + "/stats/"',
                "source": "Knn.java",
                "line": "6",
            },
            {
                "status": "planned",
                "method": "GET",
                "path": "_wlm/stats",
                "source": "RestWlmStatsAction.java",
                "line": "7",
            },
        ]

        self.assertEqual(
            self.report.route_group_counts(routes),
            [
                {"group": "/{index}/_search", "status": "planned", "count": 2},
                {"group": "/_cluster", "status": "stubbed", "count": 1},
                {"group": "/_plugins", "status": "planned", "count": 1},
                {"group": "/_wlm", "status": "planned", "count": 1},
                {"group": "/{index}/_tier", "status": "planned", "count": 1},
                {"group": "dynamic-or-unparsed", "status": "planned", "count": 1},
            ],
        )

    def test_known_java_route_expressions_match_concrete_fixture_paths(self):
        source = [
            {
                "status": "planned",
                "method": "GET",
                "path": "/{index}/ + ENDPOINT",
                "source": "RestRankEvalAction.java",
                "line": "114",
            },
            {
                "status": "planned",
                "method": "POST",
                "path": 'String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)',
                "source": "RestClearCacheHandler.java",
                "line": "58",
            },
        ]
        observed = [
            {
                "method": "GET",
                "path": "/logs-000001/_rank_eval",
                "fixture": "search.json",
            },
            {
                "method": "POST",
                "path": "/_plugins/_knn/clear_cache/vectors",
                "fixture": "knn.json",
            },
        ]

        coverage = self.report.coverage_for_routes(source, observed)

        self.assertEqual(len(coverage["matched_source_route_keys"]), 2)
        self.assertEqual(coverage["uncovered_in_scope_source_routes"], [])
        self.assertEqual(coverage["uncovered_in_scope_route_groups"], [])

    def test_collect_fixture_routes_includes_multi_step_case_routes(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            fixture = Path(temp_dir_value) / "fixture.json"
            fixture.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "multi-step",
                                "steps": [
                                    {
                                        "name": "put-settings",
                                        "method": "PUT",
                                        "path": "/_plugins/_knn/settings",
                                    },
                                    {
                                        "name": "get-settings",
                                        "method": "GET",
                                        "path": "/_plugins/_knn/settings",
                                    },
                                ],
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            routes = self.report.collect_fixture_routes([fixture])

            self.assertEqual(
                [(route["method"], route["path"]) for route in routes],
                [
                    ("PUT", "/_plugins/_knn/settings"),
                    ("GET", "/_plugins/_knn/settings"),
                ],
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

    def test_live_required_fixture_routes_filters_partial_suite_to_reported_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture = temp_dir / "search.json"
            partial_report = temp_dir / "partial-report.json"
            fixture.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "full-search",
                                "method": "POST",
                                "path": "/logs-000001/_search",
                            },
                            {
                                "name": "partial-knn",
                                "method": "GET",
                                "path": "/_plugins/_knn/settings",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            partial_report.write_text(
                json.dumps({"cases": [{"name": "partial-knn", "status": "passed"}]})
                + "\n",
                encoding="utf-8",
            )
            report = {
                "suite_results": [
                    {
                        "name": "full",
                        "required": True,
                        "status": "ok",
                        "fixture_path": str(fixture),
                    },
                    {
                        "name": "partial",
                        "required": True,
                        "status": "ok",
                        "fixture_path": str(fixture),
                        "report_path": str(partial_report),
                        "allow_partial_report": True,
                    },
                ]
            }

            routes = self.report.live_required_fixture_routes(report)

            self.assertEqual(
                [(route["method"], route["path"]) for route in routes],
                [
                    ("POST", "/logs-000001/_search"),
                    ("GET", "/_plugins/_knn/settings"),
                    ("GET", "/_plugins/_knn/settings"),
                ],
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

    def test_live_required_coverage_errors_enforce_minimum_count_and_ratio(self):
        self.assertEqual(
            self.report.live_required_coverage_errors(
                matched_count=15,
                matched_ratio=0.0404,
                min_count=15,
                min_ratio=0.0404,
            ),
            [],
        )

        errors = self.report.live_required_coverage_errors(
            matched_count=14,
            matched_ratio=0.0399,
            min_count=15,
            min_ratio=0.0404,
        )

        self.assertIn(
            "live_required_matched_source_route_count 14 is below required minimum 15",
            errors,
        )
        self.assertIn(
            "live_required_matched_source_route_ratio 0.0399 is below required minimum 0.0404",
            errors,
        )

    def test_cli_fails_when_live_required_source_route_count_is_below_floor(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            fixtures = temp_dir / "fixtures"
            fixtures.mkdir()
            fixture = fixtures / "search.json"
            unified = temp_dir / "unified.json"
            output = temp_dir / "coverage.json"
            source.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                "implemented\tPOST\t/{index}/_search\tActionModule.java\t1\n",
                encoding="utf-8",
            )
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
            unified.write_text(
                json.dumps(
                    {
                        "suite_results": [
                            {
                                "name": "search",
                                "required": True,
                                "status": "ok",
                                "fixture_path": str(fixture),
                                "classification": {
                                    "missing": 0,
                                    "failed": 0,
                                    "known_gap_or_skipped": 0,
                                },
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
                "--unified-report",
                str(unified),
                "--require-live-required-suites",
                "--min-live-required-matched-source-route-count",
                "2",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["live_required_matched_source_route_count"], 1)
            self.assertIn(
                "live_required_matched_source_route_count 1 is below required minimum 2",
                payload["errors"],
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
