import importlib.util
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock
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

    def test_stable_route_digest_sorts_keys_before_hashing(self):
        self.assertEqual(
            self.report.stable_route_digest(["b", "a"]),
            self.report.stable_route_digest(["a", "b"]),
        )
        self.assertNotEqual(
            self.report.stable_route_digest(["a", "b"]),
            self.report.stable_route_digest(["a", "c"]),
        )

    def test_source_owner_uses_opensearch_module_plugin_and_server_roots(self):
        self.assertEqual(
            self.report.source_owner(
                {
                    "source": (
                        "/home/ubuntu/OpenSearch/modules/lang-mustache/src/main/java/"
                        "org/opensearch/script/mustache/RestSearchTemplateAction.java"
                    )
                }
            ),
            "modules/lang-mustache",
        )
        self.assertEqual(
            self.report.source_owner(
                {
                    "source": (
                        "/home/ubuntu/OpenSearch/plugins/workload-management/src/main/java/"
                        "org/opensearch/plugin/wlm/rest/RestGetWorkloadGroupAction.java"
                    )
                }
            ),
            "plugins/workload-management",
        )
        self.assertEqual(
            self.report.source_owner(
                {
                    "source": (
                        "/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/rest/"
                        "action/RestMainAction.java"
                    )
                }
            ),
            "server",
        )
        self.assertEqual(
            self.report.source_owner(
                {
                    "source": (
                        "/home/ubuntu/k-NN/src/main/java/org/opensearch/knn/plugin/rest/"
                        "RestKNNStatsHandler.java"
                    )
                }
            ),
            "plugins/k-NN",
        )

    def test_matched_route_owner_counts_follow_matched_source_keys(self):
        routes = [
            {
                "status": "implemented",
                "method": "GET",
                "path": "/",
                "source": "/home/ubuntu/OpenSearch/server/src/main/java/RestMainAction.java",
                "line": "1",
            },
            {
                "status": "implemented",
                "method": "GET",
                "path": "/_plugins/_knn/stats",
                "source": "/home/ubuntu/k-NN/src/main/java/RestKNNStatsHandler.java",
                "line": "2",
            },
        ]
        routes_by_key = {self.report.source_key(route): route for route in routes}

        self.assertEqual(
            self.report.matched_route_owner_counts(
                [self.report.source_key(routes[1])],
                routes_by_key,
            ),
            {"plugins/k-NN": 1},
        )

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
                            {
                                "name": "failed-bulk",
                                "method": "POST",
                                "path": "/_bulk",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            partial_report.write_text(
                json.dumps(
                    {
                        "cases": [
                            {"name": "partial-knn", "status": "passed"},
                            {"name": "failed-bulk", "status": "failed"},
                            {"name": "skipped-case", "status": "skipped"},
                        ]
                    }
                )
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
                    ("POST", "/_bulk"),
                    ("GET", "/_plugins/_knn/settings"),
                ],
            )

    def test_report_case_names_only_counts_passed_cases_for_partial_live_coverage(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = Path(temp_dir_value) / "partial-report.json"
            report.write_text(
                json.dumps(
                    {
                        "cases": [
                            {"name": "passed-search", "status": "passed"},
                            {"name": "failed-bulk", "status": "failed"},
                            {"name": "skipped-pit", "status": "skipped"},
                            {"name": "missing-status"},
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self.report.report_case_names(str(report)),
                {"passed-search"},
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

    def test_cli_require_fixture_coverage_fails_on_uncovered_source_route(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            fixtures = temp_dir / "fixtures"
            fixtures.mkdir()
            output = temp_dir / "coverage.json"
            source.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                "implemented\tPOST\t/{index}/_search\tActionModule.java\t1\n"
                "implemented\tGET\t/_cat/shards\tActionModule.java\t2\n",
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
                "--require-fixture-coverage",
                "--summary-only",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["fixture_uncovered_in_scope_route_count"], 1)
            self.assertIn(
                "fixture_uncovered_in_scope_route_count 1 is above required maximum 0",
                payload["errors"],
            )

    def test_cli_require_fixture_coverage_passes_current_source_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--source",
                str(ROOT / "docs/rust-port/generated/source-rest-routes.tsv"),
                "--fixtures-dir",
                str(ROOT / "tools/fixtures"),
                "--require-fixture-coverage",
                "--summary-only",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["in_scope_source_route_count"], 378)
            self.assertEqual(
                payload["summary"]["source_route_key_digest"],
                "37eb92f02b22dff2148de748707e601534e365d81302211534a6e0d41e5333e2",
            )
            self.assertEqual(
                payload["summary"]["source_route_owner_counts"],
                {
                    "modules/ingest-common": 1,
                    "modules/lang-mustache": 12,
                    "modules/lang-painless": 3,
                    "modules/opensearch-dashboards": 1,
                    "modules/rank-eval": 4,
                    "modules/reindex": 6,
                    "plugins/arrow-flight-rpc": 4,
                    "plugins/examples": 2,
                    "plugins/k-NN": 12,
                    "plugins/persistent-task-live-fixture": 2,
                    "plugins/transport-reactor-netty4": 1,
                    "plugins/workload-management": 7,
                    "server": 334,
                },
            )
            self.assertEqual(
                payload["summary"]["in_scope_source_route_key_digest"],
                "86fc1075a36e70dc38a22e4ccfa897113871c2b1524f205d26965e7e79fa5a74",
            )
            expected_owner_counts = {
                "modules/ingest-common": 1,
                "modules/lang-mustache": 12,
                "modules/lang-painless": 3,
                "modules/rank-eval": 4,
                "modules/reindex": 6,
                "plugins/k-NN": 12,
                "plugins/workload-management": 7,
                "server": 333,
            }
            self.assertEqual(
                payload["summary"]["in_scope_source_route_owner_counts"],
                expected_owner_counts,
            )
            self.assertEqual(
                payload["summary"]["in_scope_source_route_owner_digest"],
                "2d460e3569716bfffc3e66c65a8b86d2cfb876908c5966a3b34082ac5d9dd0b7",
            )
            self.assertEqual(payload["summary"]["fixture_matched_source_route_count"], 378)
            self.assertEqual(
                payload["summary"]["fixture_matched_source_route_key_digest"],
                "86fc1075a36e70dc38a22e4ccfa897113871c2b1524f205d26965e7e79fa5a74",
            )
            self.assertEqual(
                payload["summary"]["fixture_matched_source_route_owner_counts"],
                expected_owner_counts,
            )
            self.assertEqual(
                payload["summary"]["fixture_matched_source_route_owner_digest"],
                "2d460e3569716bfffc3e66c65a8b86d2cfb876908c5966a3b34082ac5d9dd0b7",
            )
            self.assertEqual(payload["summary"]["fixture_uncovered_in_scope_route_count"], 0)

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

    def test_required_suite_errors_use_effective_known_gap_count_when_available(self):
        report = {
            "coverage_summary": {
                "effective_case_classification": {
                    "canonical_equal": 10,
                    "strict_equal": 20,
                    "semantic_equal": 30,
                    "steelsearch_fail_closed": 1,
                    "steelsearch_only": 2,
                    "missing": 0,
                    "failed": 0,
                    "known_gap_or_skipped": 0,
                    "passed": 0,
                },
            },
            "suite_results": [
                {
                    "name": "search",
                    "required": True,
                    "status": "ok",
                    "classification": {
                        "missing": 0,
                        "failed": 0,
                        "known_gap_or_skipped": 2,
                    },
                },
            ],
        }

        self.assertEqual(self.report.unified_required_suite_errors(report), [])
        self.assertEqual(
            self.report.effective_suite_classification(report),
            {
                "canonical_equal": 10,
                "strict_equal": 20,
                "semantic_equal": 30,
                "steelsearch_fail_closed": 1,
                "steelsearch_only": 2,
                "missing": 0,
                "failed": 0,
                "known_gap_or_skipped": 0,
                "passed": 0,
                "total_equal": 61,
            },
        )

        report["coverage_summary"]["effective_case_classification"]["known_gap_or_skipped"] = 1
        self.assertEqual(
            self.report.unified_required_suite_errors(report),
            ["effective known_gap_or_skipped=1"],
        )

    def test_required_suite_skip_resolution_summarizes_cross_suite_coverage(self):
        report = {
            "coverage_summary": {
                "case_gap_resolution": {
                    "skipped": {
                        "total_count": 3,
                        "resolved_by_other_suite_count": 2,
                        "unresolved_count": 1,
                        "resolved": [
                            {
                                "suite": "search-compat",
                                "case": "knn_search",
                                "covered_by": ["vector-search"],
                            }
                        ],
                        "unresolved": [
                            {
                                "suite": "search-compat",
                                "case": "missing-case",
                            }
                        ],
                    }
                }
            }
        }

        self.assertEqual(
            self.report.required_suite_skip_resolution(report),
            {
                "total_count": 3,
                "resolved_by_other_suite_count": 2,
                "unresolved_count": 1,
            },
        )

    def test_required_suite_steelsearch_only_breakdown_lists_required_suites(self):
        report = {
            "suite_results": [
                {
                    "name": "runtime",
                    "required": True,
                    "fixture_path": "/fixtures/runtime.json",
                    "report_path": "/reports/runtime.json",
                    "classification": {"steelsearch_only": 9},
                },
                {
                    "name": "search",
                    "required": True,
                    "fixture_path": "/fixtures/search.json",
                    "report_path": "/reports/search.json",
                    "classification": {"steelsearch_only": 0},
                },
                {
                    "name": "optional",
                    "required": False,
                    "fixture_path": "/fixtures/optional.json",
                    "report_path": "/reports/optional.json",
                    "classification": {"steelsearch_only": 100},
                },
                {
                    "name": "security",
                    "required": True,
                    "fixture_path": "/fixtures/security.json",
                    "report_path": "/reports/security.json",
                    "classification": {"steelsearch_only": 2},
                },
            ]
        }

        self.assertEqual(
            self.report.required_suite_steelsearch_only_summary(report),
            {
                "breakdown_total": 11,
                "non_required_breakdown_total": 100,
                "raw_total": 11,
                "effective_total": 11,
                "raw_delta": 0,
                "effective_delta": 0,
                "effective_unexplained_delta": 0,
            },
        )
        self.assertEqual(
            self.report.required_suite_steelsearch_only_breakdown(report),
            [
                {
                    "suite": "runtime",
                    "steelsearch_only": 9,
                    "fixture_path": "/fixtures/runtime.json",
                    "report_path": "/reports/runtime.json",
                },
                {
                    "suite": "security",
                    "steelsearch_only": 2,
                    "fixture_path": "/fixtures/security.json",
                    "report_path": "/reports/security.json",
                },
            ],
        )
        self.assertEqual(
            self.report.non_required_suite_steelsearch_only_breakdown(report),
            [
                {
                    "suite": "optional",
                    "steelsearch_only": 100,
                    "fixture_path": "/fixtures/optional.json",
                    "report_path": "/reports/optional.json",
                },
            ],
        )

    def test_required_suite_steelsearch_only_breakdown_errors_on_raw_total_drift(self):
        report = {
            "suite_results": [
                {
                    "name": "runtime",
                    "required": True,
                    "classification": {"steelsearch_only": 9},
                },
                {
                    "name": "security",
                    "required": True,
                    "classification": {"steelsearch_only": 2},
                },
            ]
        }

        with mock.patch.object(
            self.report,
            "required_suite_steelsearch_only_breakdown",
            return_value=[{"suite": "runtime", "steelsearch_only": 9}],
        ):
            self.assertEqual(
                self.report.required_suite_steelsearch_only_breakdown_errors(report),
                [
                    "steelsearch_only breakdown total 9 does not match raw required-suite total 11"
                ],
            )

    def test_required_suite_steelsearch_only_summary_reports_effective_delta(self):
        report = {
            "coverage_summary": {
                "effective_case_classification": {
                    "steelsearch_only": 13,
                },
            },
            "suite_results": [
                {
                    "name": "runtime",
                    "required": True,
                    "classification": {"steelsearch_only": 9},
                },
                {
                    "name": "security",
                    "required": True,
                    "classification": {"steelsearch_only": 2},
                },
            ],
        }

        self.assertEqual(
            self.report.required_suite_steelsearch_only_summary(report),
            {
                "breakdown_total": 11,
                "non_required_breakdown_total": 0,
                "raw_total": 11,
                "effective_total": 13,
                "raw_delta": 0,
                "effective_delta": 2,
                "effective_unexplained_delta": 2,
            },
        )

        self.assertEqual(
            self.report.required_suite_steelsearch_only_breakdown_errors(report),
            [
                "steelsearch_only effective total has unexplained delta 2 "
                "after non-required suite breakdown"
            ],
        )

    def test_required_suite_steelsearch_only_summary_accounts_for_non_required_delta(self):
        report = {
            "coverage_summary": {
                "effective_case_classification": {
                    "steelsearch_only": 13,
                },
            },
            "suite_results": [
                {
                    "name": "runtime",
                    "required": True,
                    "classification": {"steelsearch_only": 11},
                },
                {
                    "name": "optional",
                    "required": False,
                    "classification": {"steelsearch_only": 2},
                },
            ],
        }

        self.assertEqual(
            self.report.required_suite_steelsearch_only_summary(report),
            {
                "breakdown_total": 11,
                "non_required_breakdown_total": 2,
                "raw_total": 11,
                "effective_total": 13,
                "raw_delta": 0,
                "effective_delta": 2,
                "effective_unexplained_delta": 0,
            },
        )
        self.assertEqual(self.report.required_suite_steelsearch_only_breakdown_errors(report), [])

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

    def test_source_inventory_errors_enforce_minimum_count(self):
        self.assertEqual(
            self.report.source_inventory_errors(
                source_route_count=389,
                min_source_route_count=389,
            ),
            [],
        )

        self.assertEqual(
            self.report.source_inventory_errors(
                source_route_count=388,
                min_source_route_count=389,
            ),
            ["source_route_count 388 is below required minimum 389"],
        )

    def test_source_status_errors_reject_non_closed_statuses(self):
        self.assertEqual(
            self.report.source_status_errors({"implemented": 378, "out-of-scope": 11}),
            [],
        )

        self.assertEqual(
            self.report.source_status_errors(
                {"implemented": 377, "out-of-scope": 11, "planned": 1}
            ),
            ["source route inventory has non-closed statuses: planned=1"],
        )

    def test_cli_require_closed_source_statuses_rejects_planned_routes(self):
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

            result = self.run_cli(
                "--source",
                str(source),
                "--fixtures-dir",
                str(fixtures),
                "--require-closed-source-statuses",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["source_status_counts"]["planned"], 1)
            self.assertIn(
                "source route inventory has non-closed statuses: planned=1",
                payload["errors"],
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

    def test_cli_fails_when_source_inventory_count_is_below_floor(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            fixtures = temp_dir / "fixtures"
            fixtures.mkdir()
            output = temp_dir / "coverage.json"
            source.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                "implemented\tPOST\t/{index}/_search\tActionModule.java\t1\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--fixtures-dir",
                str(fixtures),
                "--min-source-route-count",
                "2",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["source_route_count"], 1)
            self.assertIn(
                "source_route_count 1 is below required minimum 2",
                payload["errors"],
            )

    def test_cli_rejects_stale_unified_report_when_age_gate_is_set(self):
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
            stale_mtime = time.time() - 120.0
            os.utime(unified, (stale_mtime, stale_mtime))

            result = self.run_cli(
                "--source",
                str(source),
                "--fixtures-dir",
                str(fixtures),
                "--unified-report",
                str(unified),
                "--require-live-required-suites",
                "--max-report-age-seconds",
                "60",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertFalse(payload["summary"]["unified_report_fresh"])
            self.assertTrue(any("stale" in error for error in payload["errors"]))

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            with contextlib.redirect_stdout(io.StringIO()):
                return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
