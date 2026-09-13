#!/usr/bin/env python3
"""Tests for the search compatibility runner."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("search_compat.py")
SPEC = importlib.util.spec_from_file_location("search_compat", MODULE_PATH)
assert SPEC is not None
search_compat = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(search_compat)


class SearchCompatRunnerTests(unittest.TestCase):
    def test_term_vectors_normalizes_only_valid_elapsed_time(self) -> None:
        body = {"_id": "one", "_version": 2, "found": True, "took": 1,
                "term_vectors": {"body": {"terms": {"alpha": {"term_freq": 2}}}}}
        def extract(value, status=200):
            return search_compat.extract("term_vectors", {"status": status, "body": value})
        expected = extract(body)
        self.assertEqual(expected, extract({**body, "took": 20}))
        self.assertEqual(expected, extract({**body, "took": 0}))
        self.assertEqual(body["took"], 1)
        for invalid in [None, True, False, -1, 1.0, float("nan"), float("inf"), "1", {}]:
            with self.subTest(took=invalid):
                self.assertNotEqual(expected, extract({**body, "took": invalid}))
        self.assertNotEqual(expected, extract({key: value for key, value in body.items() if key != "took"}))
        for key, value in [("_id", "two"), ("_version", 3), ("found", False),
                           ("term_vectors", {}), ("extra", 1)]:
            with self.subTest(key=key):
                self.assertNotEqual(expected, extract({**body, key: value}))
        self.assertNotEqual(expected, extract(body, 404))
        self.assertNotEqual(search_compat.extract("source_body", {"status": 200, "body": body}),
                            search_compat.extract("source_body", {"status": 200, "body": {**body, "took": 20}}))

    def test_alias_single_index_error_normalizes_only_member_order(self) -> None:
        def extract_reason(reason, status=400, error_type="illegal_argument_exception"):
            return search_compat.extract("alias_single_index_error", {
                "status": status, "body": {"error": {"type": error_type, "reason": reason}},
            })

        reason = "alias [route] has more than one index associated with it [a, b], can't execute a single index op"
        expected = extract_reason(reason)
        self.assertEqual(expected, extract_reason(reason.replace("[a, b]", "[b, a]")))
        for changed in [reason.replace("alias", "Alias", 1),
                        reason.replace("[a, b]", "[[a, b]]"),
                        reason.replace("[a, b]", "[a, c]"),
                        reason.replace("[a, b]", "[a, a]"),
                        reason.replace("[route]", "[different]"), None, 12]:
            with self.subTest(reason=changed):
                self.assertNotEqual(expected, extract_reason(changed))
                self.assertEqual(extract_reason(changed)["reason"], changed)
        self.assertNotEqual(expected, extract_reason(reason, status=404))
        self.assertNotEqual(expected, extract_reason(reason, error_type="different"))

    def test_fetch_projection_normalizes_only_top_level_elapsed_time(self) -> None:
        body = {
            "took": 1,
            "hits": {"hits": [{"_id": "one", "_source": {"took": 17}}]},
        }
        expected = search_compat.extract("search_fetch_projection", {"status": 200, "body": body})
        self.assertEqual(
            expected,
            search_compat.extract(
                "search_fetch_projection", {"status": 200, "body": {**body, "took": 20}},
            ),
        )
        self.assertNotEqual(
            expected,
            search_compat.extract(
                "search_fetch_projection",
                {"status": 200, "body": {"hits": {"hits": [{"_id": "one", "_source": {"took": 18}}]}, "took": 1}},
            ),
        )
        self.assertNotEqual(
            expected,
            search_compat.extract(
                "search_fetch_projection", {"status": 200, "body": {"hits": body["hits"]}},
            ),
        )

    def test_default_relevance_scores_allow_only_tolerance_and_exact_ties(self) -> None:
        expected = {
            "status": 200,
            "extract": {
                "status": 200,
                "total": 3,
                "ids": ["first", "second", "third"],
                "scores": [2.0, 1.0, 1.0],
            },
        }
        tied_reordered = {
            "status": 200,
            "extract": {
                "status": 200,
                "total": 3,
                "ids": ["first", "third", "second"],
                "scores": [2.0000005, 1.0000005, 1.0000005],
            },
        }
        self.assertTrue(search_compat.default_relevance_score_extracts_match(tied_reordered, expected))

        non_tie_reordered = {
            **tied_reordered,
            "extract": {**tied_reordered["extract"], "ids": ["second", "first", "third"]},
        }
        self.assertFalse(search_compat.default_relevance_score_extracts_match(non_tie_reordered, expected))

        outside_tolerance = {
            **tied_reordered,
            "extract": {**tied_reordered["extract"], "scores": [2.00001, 1.0, 1.0]},
        }
        self.assertFalse(search_compat.default_relevance_score_extracts_match(outside_tolerance, expected))

    def test_default_relevance_scope_excludes_ranking_controls(self) -> None:
        self.assertTrue(search_compat.case_uses_default_relevance_score_contract({
            "extract": "search_scores", "steps": [{"path": "/logs/_search", "body": {"from": 0}}],
        }))
        for body in [
            {"from": 1}, {"sort": ["rank"]}, {"min_score": 0.1},
            {"search_after": ["a"]}, {"pit": {"id": "pit"}}, {"scroll": "1m"},
        ]:
            with self.subTest(body=body):
                self.assertFalse(search_compat.case_uses_default_relevance_score_contract({
                    "extract": "search_scores", "steps": [{"path": "/logs/_search", "body": body}],
                }))

    def test_search_sort_values_preserve_long_cursor_precision(self) -> None:
        response = {"status": 200, "body": {"hits": {"total": {"value": 2}, "hits": [
            {"_id": "near-max", "sort": [9223372036854775806]},
            {"_id": "missing", "sort": [9223372036854775807]},
        ]}}}
        result = search_compat.extract("search_hits_with_sort_values", response)
        self.assertEqual(result["sort_values"], [[9223372036854775806], [9223372036854775807]])
        self.assertNotEqual(result["sort_values"][0], result["sort_values"][1])

    def test_ingest_simulate_normalizes_only_valid_utc_timestamps(self) -> None:
        def extract_ingest(ingest):
            return search_compat.extract("ingest_simulate", {
                "status": 200,
                "body": {"docs": [{"doc": {"_ingest": ingest}}]},
            })["_ingest"]

        for timestamp in ["2026-09-06T10:00:00Z", "2026-09-06T10:00:00.123456789Z"]:
            self.assertEqual(extract_ingest({"timestamp": timestamp, "custom": 1}), {
                "timestamp": "<valid-utc-timestamp>", "custom": 1,
            })
        for ingest in [None, {}, {"timestamp": None}, {"timestamp": 123},
                       {"timestamp": "2026-02-30T10:00:00Z"},
                       {"timestamp": "2026-09-06T10:00:00"},
                       {"timestamp": "invalid"}]:
            with self.subTest(ingest=ingest):
                self.assertEqual(extract_ingest(ingest), ingest)

    def test_search_error_full_extract_preserves_shard_failure_body(self) -> None:
        response = {
            "status": 500,
            "body": {
                "error": {
                    "type": "search_phase_execution_exception",
                    "reason": "all shards failed",
                    "phase": "query",
                    "grouped": True,
                    "failed_shards": [
                        {
                            "shard": 0,
                            "index": "logs",
                            "reason": {
                                "type": "search_exception",
                                "reason": "bad search",
                            },
                        }
                    ],
                }
            },
        }

        self.assertEqual(
            search_compat.extract("search_error_full", response),
            {
                "status": 500,
                "error": response["body"]["error"],
            },
        )

    def test_required_fixture_keeps_pit_lifecycle_coverage(self) -> None:
        fixture_path = Path(__file__).with_name("fixtures") / "search-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        required_cases = {
            "pit_open_search",
            "pit_search",
            "pit_list_search",
            "pit_clear_search",
            "pit_search_after_close_missing_context",
            "pit_shard_doc_search_after_search",
            "pit_snapshot_after_update_delete_search",
            "msearch_pit_snapshot_after_update_delete_search",
        }
        self.assertTrue(
            required_cases <= set(cases),
            f"missing required PIT cases: {sorted(required_cases - set(cases))}",
        )
        for name in required_cases:
            self.assertTrue(
                search_compat.case_touches_point_in_time(cases[name]),
                f"{name} must be detected as PIT stateful coverage",
            )

        snapshot_steps = {
            step["name"]
            for step in cases["pit_snapshot_after_update_delete_search"]["steps"]
        }
        self.assertTrue(
            {
                "pit-open",
                "update-doc-2",
                "delete-doc-1",
                "index-doc-3-after-pit",
                "live-search-after-mutation",
                "pit-search",
            }
            <= snapshot_steps
        )

    def test_case_touches_point_in_time_detects_paths_extracts_and_bodies(self) -> None:
        self.assertTrue(
            search_compat.case_touches_point_in_time(
                {"extract": "pit_list", "method": "GET", "path": "/_search"}
            )
        )
        self.assertTrue(
            search_compat.case_touches_point_in_time(
                {
                    "method": "POST",
                    "path": "/_search",
                    "body": {"query": {"match_all": {}}, "pit": {"id": "pit-id"}},
                }
            )
        )
        self.assertTrue(
            search_compat.case_touches_point_in_time(
                {
                    "steps": [
                        {
                            "method": "POST",
                            "path": "/logs/_search/point_in_time?keep_alive=1m",
                        }
                    ]
                }
            )
        )
        self.assertFalse(
            search_compat.case_touches_point_in_time(
                {
                    "method": "POST",
                    "path": "/logs/_search",
                    "body": {"query": {"match_all": {}}},
                    "extract": "search_hits",
                }
            )
        )

    def test_response_path_saves_pit_id_from_opensearch_id_field(self) -> None:
        self.assertEqual(
            search_compat.response_path(
                {"body": {"id": "opensearch-pit-id"}},
                "body.pit_id",
            ),
            "opensearch-pit-id",
        )
        self.assertEqual(
            search_compat.response_path(
                {"body": {"pit_id": "steelsearch-pit-id", "id": "fallback"}},
                "body.pit_id",
            ),
            "steelsearch-pit-id",
        )

    def test_security_authz_bucket_derives_steelsearch_status(self) -> None:
        self.assertEqual(
            search_compat.expected_steelsearch_status(
                {"area": "search", "expected_status": 500}
            ),
            500,
        )
        self.assertEqual(
            search_compat.expected_steelsearch_status(
                {"area": "security-authz", "bucket": "missing-credential-401"}
            ),
            401,
        )
        self.assertEqual(
            search_compat.expected_steelsearch_status(
                {"area": "security-authz", "bucket": "insufficient-role-403"}
            ),
            403,
        )
        self.assertEqual(
            search_compat.expected_steelsearch_status(
                {
                    "area": "security-authz",
                    "bucket": "minimum-role-success",
                    "expected_steelsearch_status": 404,
                }
            ),
            404,
        )

    def test_value_contains_matches_nested_expected_subset(self) -> None:
        self.assertTrue(
            search_compat.value_contains(
                {
                    "status": 200,
                    "items": [
                        {"status": 201, "_seq_no": 7},
                        {"status": 403, "error_type": "security_exception", "reason": "denied"},
                    ],
                },
                {
                    "items": [
                        {"status": 201},
                        {"status": 403, "error_type": "security_exception"},
                    ]
                },
            )
        )
        self.assertFalse(
            search_compat.value_contains(
                {"items": [{"status": 201}, {"status": 201}]},
                {"items": [{"status": 201}, {"status": 403}]},
            )
        )

    def test_security_authz_extracts_ignore_format_only_error_differences(self) -> None:
        self.assertTrue(
            search_compat.security_authz_extracts_match(
                {
                    "status": 401,
                    "extract": {
                        "status": 401,
                        "error_type": "security_exception",
                        "reason": "missing authentication credentials",
                        "www_authenticate": 'Basic realm="security" charset="UTF-8"',
                    },
                },
                {
                    "status": 401,
                    "extract": {
                        "status": 401,
                        "error_type": None,
                        "reason": None,
                        "www_authenticate": 'Basic realm="OpenSearch Security"',
                    },
                },
            )
        )
        self.assertTrue(
            search_compat.security_authz_extracts_match(
                {
                    "status": 403,
                    "extract": {
                        "status": 403,
                        "error_type": "security_exception",
                        "reason": "role [writer] denied",
                    },
                },
                {
                    "status": 403,
                    "extract": {
                        "status": 403,
                        "error_type": "security_exception",
                        "reason": "no permissions for action",
                    },
                },
            )
        )
        self.assertFalse(
            search_compat.security_authz_extracts_match(
                {"status": 403, "extract": {"status": 403}},
                {"status": 404, "extract": {"status": 404}},
            )
        )

    def test_run_case_enforces_steelsearch_only_expected_extract(self) -> None:
        original_http_json = search_compat.http_json
        try:
            search_compat.http_json = lambda *_args, **_kwargs: {
                "status": 200,
                "body": {
                    "errors": False,
                    "items": [
                        {"index": {"_index": "logs", "_id": "ok", "status": 201}},
                        {"index": {"_index": ".opensearch-restricted", "_id": "denied", "status": 201}},
                    ],
                },
                "headers": {},
                "error": None,
            }
            result = search_compat.run_case(
                {
                    "name": "bulk-authz",
                    "area": "security-authz",
                    "method": "POST",
                    "path": "/_bulk",
                    "raw": True,
                    "body": "{}\n{}\n",
                    "extract": "bulk_items",
                    "comparison": "steelsearch_only",
                    "expected_steelsearch_status": 200,
                    "expected_steelsearch_extract": {
                        "items": [
                            {"status": 201},
                            {"status": 403, "error_type": "security_exception"},
                        ]
                    },
                },
                {},
                {"steelsearch": "http://steelsearch"},
                1.0,
            )
        finally:
            search_compat.http_json = original_http_json

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["expected_steelsearch_status"], 200)

    def test_generated_bulk_step_indexes_synthetic_vectors(self) -> None:
        calls = []
        original_http_json = search_compat.http_json

        def fake_http_json(_base, method, path, body, _timeout, **kwargs):
            calls.append((method, path, body, kwargs))
            return {"status": 200, "body": {"errors": False}, "headers": {}, "error": None}

        try:
            search_compat.http_json = fake_http_json
            response, steps = search_compat.run_case_request(
                "http://steelsearch",
                {},
                {
                    "name": "generated-training-docs",
                    "area": "knn",
                    "extract": "status_only",
                    "steps": [
                        {
                            "name": "index-training-docs",
                            "expected_status": 200,
                            "generated_bulk": {
                                "index": "vectors-train-compat",
                                "count": 2,
                                "id_prefix": "train-doc",
                                "vector_field": "embedding",
                                "dimension": 3,
                            },
                        }
                    ],
                },
                1.0,
            )
        finally:
            search_compat.http_json = original_http_json

        self.assertEqual(response["status"], 200)
        self.assertEqual(steps[0]["name"], "index-training-docs")
        self.assertTrue(steps[0]["passed"])
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "/vectors-train-compat/_bulk")
        self.assertTrue(calls[0][3]["raw"])
        self.assertIn('"train-doc-0"', calls[0][2])
        self.assertIn('"embedding": [0.0, 0.1, 0.2]', calls[0][2])

    def test_security_authz_bulk_comparison_ignores_denial_reason_text(self) -> None:
        steel = {
            "status": 200,
            "extract": {
                "status": 200,
                "errors": True,
                "items": [
                    {
                        "action": "index",
                        "_index": "logs",
                        "_id": "ok",
                        "status": 201,
                        "result": "created",
                        "_version": 1,
                        "_seq_no": 1,
                        "_primary_term": 1,
                        "forced_refresh": None,
                        "error_type": None,
                    },
                    {
                        "action": "index",
                        "_index": ".opensearch-restricted",
                        "_id": "denied",
                        "status": 403,
                        "result": None,
                        "_version": None,
                        "_seq_no": None,
                        "_primary_term": None,
                        "forced_refresh": None,
                        "error_type": "security_exception",
                        "reason": "local denial text",
                    },
                ],
            },
        }
        opensearch = {
            "status": 200,
            "extract": {
                "status": 200,
                "errors": True,
                "items": [
                    {
                        "action": "index",
                        "_index": "logs",
                        "_id": "ok",
                        "status": 201,
                        "result": "created",
                        "_version": 1,
                        "_seq_no": 1,
                        "_primary_term": 1,
                        "forced_refresh": None,
                        "error_type": None,
                    },
                    {
                        "action": "index",
                        "_index": ".opensearch-restricted",
                        "_id": "denied",
                        "status": 403,
                        "result": None,
                        "_version": None,
                        "_seq_no": None,
                        "_primary_term": None,
                        "forced_refresh": None,
                        "error_type": "security_exception",
                        "reason": "OpenSearch denial text",
                    },
                ],
            },
        }

        self.assertTrue(search_compat.security_authz_extracts_match(steel, opensearch))

    def test_cleanup_case_runtime_state_closes_pits_for_pit_cases(self) -> None:
        calls: list[tuple[str, str]] = []
        original_http_json = search_compat.http_json
        try:
            search_compat.http_json = lambda _base, method, path, *_args, **_kwargs: (
                calls.append((method, path)) or {"status": 200, "body": {"pits": []}}
            )

            steps = search_compat.cleanup_case_runtime_state(
                "http://steelsearch",
                {},
                {
                    "steps": [
                        {
                            "method": "POST",
                            "path": "/logs/_search/point_in_time?keep_alive=1m",
                        }
                    ]
                },
                1.0,
            )
        finally:
            search_compat.http_json = original_http_json

        self.assertEqual(calls, [("DELETE", "/_search/point_in_time/_all")])
        self.assertEqual(steps[0]["name"], "cleanup:point_in_time:_all")
        self.assertTrue(steps[0]["passed"])

    def test_prepare_case_runtime_state_closes_pits_before_pit_cases(self) -> None:
        calls: list[tuple[str, str]] = []
        original_http_json = search_compat.http_json
        try:
            search_compat.http_json = lambda _base, method, path, *_args, **_kwargs: (
                calls.append((method, path)) or {"status": 200, "body": {"pits": []}}
            )

            steps = search_compat.prepare_case_runtime_state(
                "http://steelsearch",
                {},
                {"method": "GET", "path": "/_search/point_in_time/_all", "extract": "pit_list"},
                1.0,
            )
        finally:
            search_compat.http_json = original_http_json

        self.assertEqual(calls, [("DELETE", "/_search/point_in_time/_all")])
        self.assertEqual(steps[0]["name"], "precleanup:point_in_time:_all")
        self.assertTrue(steps[0]["passed"])

    def test_cleanup_case_runtime_state_leaves_non_pit_cases_alone(self) -> None:
        calls: list[tuple[str, str]] = []
        original_http_json = search_compat.http_json
        try:
            search_compat.http_json = lambda _base, method, path, *_args, **_kwargs: (
                calls.append((method, path)) or {"status": 200, "body": {}}
            )

            steps = search_compat.cleanup_case_runtime_state(
                "http://steelsearch",
                {},
                {"method": "POST", "path": "/logs/_search", "body": {"query": {"match_all": {}}}},
                1.0,
            )
        finally:
            search_compat.http_json = original_http_json

        self.assertEqual(calls, [])
        self.assertEqual(steps, [])


if __name__ == "__main__":
    unittest.main()
