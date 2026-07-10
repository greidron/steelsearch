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
