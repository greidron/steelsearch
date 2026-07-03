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
