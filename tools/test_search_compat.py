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
    def test_snapshot_json_selected_columns_allows_empty_state_but_validates_rows(self) -> None:
        extract = lambda body: search_compat.extract("cat_snapshot_json_selected_columns", {
            "status": 200, "body": body,
        })
        expected = {
            "dur": "1ms", "ete": "1", "eti": "00:00:01", "fs": "0", "i": "1",
            "r": None, "s": "SUCCESS", "snapshot": "snap", "ss": "1", "ste": "1",
            "sti": "00:00:01", "ts": "1",
        }
        self.assertEqual(extract({}), {"status": 200, "selected_columns_valid": True})
        self.assertEqual(extract([expected]), {"status": 200, "selected_columns_valid": True})
        self.assertEqual(extract([{**expected, "unexpected": "value"}]), {
            "status": 200, "selected_columns_valid": False,
        })

    def test_term_vectors_excludes_elapsed_time(self) -> None:
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
                self.assertEqual(expected, extract({**body, "took": invalid}))
        self.assertEqual(expected, extract({key: value for key, value in body.items() if key != "took"}))
        for key, value in [("_id", "two"), ("_version", 3), ("found", False),
                           ("term_vectors", {}), ("extra", 1)]:
            with self.subTest(key=key):
                self.assertNotEqual(expected, extract({**body, key: value}))
        self.assertNotEqual(expected, extract(body, 404))
        self.assertEqual(search_compat.extract("source_body", {"status": 200, "body": body}),
                         search_compat.extract("source_body", {"status": 200, "body": {**body, "took": 20}}))

    def test_term_vectors_preserves_document_fields_named_took(self) -> None:
        def extract(frequency, elapsed):
            return search_compat.extract("term_vectors", {"status": 200, "body": {
                "took": elapsed, "found": True, "_id": "one", "_version": 1,
                "term_vectors": {"took": {"terms": {"took": {"term_freq": frequency}}}},
            }})
        self.assertEqual(extract(1, 0), extract(1, 73))
        self.assertNotEqual(extract(1, 0), extract(2, 73))

    def test_array_position_fixture_uses_term_vector_elapsed_time_contract(self) -> None:
        fixture = json.loads((MODULE_PATH.parent / "fixtures" /
            "search-native-array-positions-compat.json").read_text())
        positions = [case for case in fixture["cases"] if case.get("family") == "positions"]
        self.assertTrue(positions)
        for case in positions:
            with self.subTest(case=case["name"]):
                self.assertEqual(case["extract"], "term_vectors")

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

    def test_search_sort_values_preserve_long_cursor_precision(self) -> None:
        response = {"status": 200, "body": {"hits": {"total": {"value": 2}, "hits": [
            {"_id": "near-max", "sort": [9223372036854775806]},
            {"_id": "missing", "sort": [9223372036854775807]},
        ]}}}
        result = search_compat.extract("search_hits_with_sort_values", response)
        self.assertEqual(result["sort_values"], [[9223372036854775806], [9223372036854775807]])
        self.assertNotEqual(result["sort_values"][0], result["sort_values"][1])

    def test_default_score_ranking_canonicalizes_only_exact_score_ties(self) -> None:
        response = {"status": 200, "body": {"hits": {"total": {"value": 5}, "hits": [
            {"_id": "first", "_score": 3.0},
            {"_id": "zulu", "_score": 2.0},
            {"_id": "alpha", "_score": 2.0},
            {"_id": "bravo", "_score": 1.0},
            {"_id": "charlie", "_score": 0.999999},
        ]}}}
        self.assertEqual(
            search_compat.extract("search_default_score_ranking", response),
            {
                "status": 200,
                "total": 5,
                "ids": ["first", "alpha", "zulu", "bravo", "charlie"],
                "scores": [3.0, 2.0, 2.0, 1.0, 0.999999],
            },
        )

    def test_default_score_ranking_requires_exact_structure_and_bounded_scores(self) -> None:
        expected = {"status": 200, "total": 2, "ids": ["one", "two"],
                    "scores": [1.2933937, 0.25]}
        within_tolerance = {"status": 200, "total": 2, "ids": ["one", "two"],
                            "scores": [1.2933934926986694, 0.2500008]}
        self.assertTrue(search_compat.default_score_ranking_extracts_match(
            within_tolerance, expected))
        for mismatch in [
            {**within_tolerance, "status": 201},
            {**within_tolerance, "total": 3},
            {**within_tolerance, "ids": ["two", "one"]},
            {**within_tolerance, "scores": [1.293392, 0.25]},
        ]:
            with self.subTest(mismatch=mismatch):
                self.assertFalse(search_compat.default_score_ranking_extracts_match(
                    mismatch, expected))

    def test_search_scores_normalizes_equivalent_f32_json_literals(self) -> None:
        def response(score: float) -> dict:
            return {"status": 200, "body": {"hits": {"total": {"value": 1}, "hits": [
                {"_id": "one", "_score": score},
            ]}}}

        self.assertEqual(
            search_compat.extract("search_scores", response(0.2926715)),
            search_compat.extract("search_scores", response(0.2926715016365051)),
        )

    def test_default_score_ranking_scope_excludes_result_controls_and_pages(self) -> None:
        default_case = {"extract": "search_scores", "steps": [{"body": {"from": 0}}]}
        self.assertTrue(search_compat.case_uses_default_score_ranking(default_case))
        for body in [
            {"sort": ["latency"]},
            {"min_score": 1.0},
            {"search_after": [1]},
            {"pit": {"id": "pit"}},
            {"scroll": "1m"},
            {"from": 1},
        ]:
            with self.subTest(body=body):
                self.assertFalse(search_compat.case_uses_default_score_ranking(
                    {"extract": "search_scores", "steps": [{"body": body}]}))
        self.assertFalse(search_compat.case_uses_default_score_ranking(
            {"extract": "search_hits", "steps": [{"body": {}}]}))

    def test_phrase_frequency_fixture_uses_default_score_ranking_only_without_sort(self) -> None:
        fixture = json.loads((MODULE_PATH.parent / "fixtures" /
            "search-native-phrase-frequency-compat.json").read_text())
        for case in fixture["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(case["extract"], "search_default_score_ranking")
                self.assertTrue(search_compat.case_uses_default_score_ranking(case))
                for step in case["steps"]:
                    body = step.get("body") or {}
                    for control in ("sort", "min_score", "search_after", "pit", "scroll"):
                        self.assertNotIn(control, body)

    def test_search_fetch_projection_preserves_source_visibility_and_fields(self) -> None:
        response = {
            "status": 200,
            "body": {
                "hits": {
                    "total": {"value": 3},
                    "hits": [
                        {"_id": "absent", "fields": {"stored": ["a"]}},
                        {"_id": "null", "_source": None, "fields": {"stored": ["b"]}},
                        {
                            "_id": "filtered",
                            "_source": {"kept": "value"},
                            "fields": {"stored": ["c"]},
                        },
                    ],
                }
            },
        }

        self.assertEqual(
            search_compat.extract("search_fetch_projection", response),
            {
                "status": 200,
                "total": 3,
                "ids": ["absent", "filtered", "null"],
                "fields": {
                    "absent": {"stored": ["a"]},
                    "null": {"stored": ["b"]},
                    "filtered": {"stored": ["c"]},
                },
                "sources": {
                    "absent": {"present": False, "value": None},
                    "null": {"present": True, "value": None},
                    "filtered": {"present": True, "value": {"kept": "value"}},
                },
            },
        )

    def test_search_fields_remains_backward_compatible(self) -> None:
        response = {
            "status": 200,
            "body": {
                "hits": {
                    "total": 1,
                    "hits": [{
                        "_id": "one",
                        "_source": {"leaked": "default-source"},
                        "fields": {"stored": ["value"]},
                    }],
                }
            },
        }

        self.assertEqual(
            search_compat.extract("search_fields", response),
            {
                "status": 200,
                "total": 1,
                "ids": ["one"],
                "fields": {"one": {"stored": ["value"]}},
            },
        )

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
