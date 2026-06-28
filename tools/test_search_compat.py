#!/usr/bin/env python3
"""Tests for the search compatibility runner."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("search_compat.py")
SPEC = importlib.util.spec_from_file_location("search_compat", MODULE_PATH)
assert SPEC is not None
search_compat = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(search_compat)


class SearchCompatRunnerTests(unittest.TestCase):
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
