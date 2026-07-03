#!/usr/bin/env python3
"""Tests for stateful compatibility case filtering."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


def load_tool_module(name: str) -> ModuleType:
    module_path = Path(__file__).with_name(f"{name}.py")
    tools_dir = str(module_path.parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StatefulCompatCaseSelectionTests(unittest.TestCase):
    def test_mapping_case_filter_includes_prefix_dependencies(self) -> None:
        mapping_compat = load_tool_module("mapping_compat")
        fixture = {
            "cases": [
                {"name": "create"},
                {"name": "update"},
                {"name": "read"},
            ],
        }

        selected = mapping_compat.select_cases(fixture, ["read"])

        self.assertEqual([case["name"] for case in selected], ["create", "update", "read"])

    def test_snapshot_case_filter_includes_prefix_dependencies(self) -> None:
        snapshot_lifecycle_compat = load_tool_module("snapshot_lifecycle_compat")
        fixture = {
            "cases": [
                {"name": "register"},
                {"name": "create_snapshot"},
                {"name": "restore_missing"},
            ],
        }

        selected = snapshot_lifecycle_compat.select_cases(fixture, ["restore_missing"])

        self.assertEqual(
            [case["name"] for case in selected],
            ["register", "create_snapshot", "restore_missing"],
        )

    def test_mapping_case_filter_rejects_unknown_cases(self) -> None:
        mapping_compat = load_tool_module("mapping_compat")
        fixture = {"cases": [{"name": "known"}]}

        with self.assertRaisesRegex(SystemExit, "unknown mapping compat case"):
            mapping_compat.select_cases(fixture, ["missing"])

    def test_snapshot_missing_repository_error_is_normalized(self) -> None:
        snapshot_lifecycle_compat = load_tool_module("snapshot_lifecycle_compat")
        case = {"extract": "snapshot_missing_repository"}
        body = {
            "error": {
                "type": "repository_missing_exception",
                "reason": "[repo-missing] missing",
                "root_cause": [
                    {
                        "type": "repository_missing_exception",
                        "reason": "[repo-missing] missing",
                    },
                ],
            },
            "status": 404,
        }

        normalized = snapshot_lifecycle_compat.normalize_snapshot_body(case, body)

        self.assertEqual(
            normalized,
            {
                "status": 404,
                "error_type": "repository_missing_exception",
                "error_reason": "[repo-missing] missing",
                "root_cause_type": "repository_missing_exception",
            },
        )

    def test_stateful_probe_materializes_captured_pit_ids(self) -> None:
        probe = load_tool_module("probe_stateful_route_ledger")
        captures = {"pit_id": "opaque-pit-id"}
        case = {
            "method": "DELETE",
            "path": "/_search/point_in_time",
            "body": {"pit_id": ["${pit_id}"]},
        }

        materialized = probe.materialize_case(case, captures)

        self.assertEqual(
            materialized,
            {
                "method": "DELETE",
                "path": "/_search/point_in_time",
                "body": {"pit_id": ["opaque-pit-id"]},
            },
        )

    def test_stateful_probe_captures_json_pointer_values(self) -> None:
        probe = load_tool_module("probe_stateful_route_ledger")
        captures: dict[str, object] = {}
        case = {"capture_json": {"pit_id": "/pit_id"}}
        result = {"body": '{"pit_id":"opaque-pit-id"}'}

        probe.capture_values(case, result, captures)

        self.assertEqual(captures, {"pit_id": "opaque-pit-id"})

    def test_stateful_probe_ignores_optional_capture_pointer_shape_mismatch(self) -> None:
        probe = load_tool_module("probe_stateful_route_ledger")
        captures: dict[str, object] = {}
        case = {"capture_json": {"next_token": "/next_token"}}
        result = {"body": '[{"workload_group":"default"}]'}

        probe.capture_values(case, result, captures)

        self.assertEqual(captures, {})

    def test_stateful_probe_normalizes_pit_report_values_only_for_report(self) -> None:
        probe = load_tool_module("probe_stateful_route_ledger")
        case = {
            "name": "search_point_in_time_all_get",
            "path": "/_search/point_in_time/_all",
        }
        result = {
            "status": 200,
            "body": '{"pits":[{"pit_id":"opaque-pit-id","creation_time":123,"keep_alive":60000}]}',
        }

        normalized = probe.normalize_result_for_report(case, result)

        self.assertEqual(
            normalized,
            {
                "status": 200,
                "body": '{"pits":[{"creation_time":0,"keep_alive":60000,"pit_id":"<pit_id>"}]}',
            },
        )

    def test_stateful_probe_select_cases_keeps_case_local_setup(self) -> None:
        probe = load_tool_module("probe_stateful_route_ledger")
        fixture = {
            "cases": [
                {
                    "name": "rollover",
                    "setup": [{"method": "PUT", "path": "/source"}],
                    "method": "POST",
                    "path": "/alias/_rollover",
                }
            ]
        }

        selected = probe.select_cases(fixture, ["rollover"])

        self.assertEqual(selected[0]["setup"], [{"method": "PUT", "path": "/source"}])

    def test_runtime_backlog_matches_stateful_probe_by_normalized_inventory_path(self) -> None:
        backlog = load_tool_module("build_runtime_route_backlog")

        stateful_probe = backlog.load_stateful_probe()

        self.assertEqual(
            stateful_probe[
                (
                    "POST",
                    "/_plugins/_knn/clear_cache/{index}",
                )
            ],
            "implemented-stateful",
        )
        self.assertEqual(
            stateful_probe[
                (
                    "POST",
                    "/_plugins/_knn/models/_search",
                )
            ],
            "implemented-stateful",
        )
        self.assertEqual(
            stateful_probe[
                (
                    "POST",
                    "/{index}/_tier/{targetTier}",
                )
            ],
            "implemented-stateful",
        )

    def test_runtime_backlog_rewrite_preserves_following_top_level_sections(self) -> None:
        backlog = load_tool_module("build_runtime_route_backlog")

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = Path(temp_dir) / "tasks.md"
            tasks_path.write_text(
                "\n".join(
                    [
                        "- [x] before",
                        f"- [ ] {backlog.ANCHOR_TEXT}",
                        "  - [ ] stale generated row",
                        "- [x] OpenSearch replacement gap backlog",
                        "  - [x] keep this section",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            original_tasks = backlog.TASKS
            try:
                backlog.TASKS = tasks_path
                backlog.rewrite_tasks(
                    [
                        {
                            "family": "search",
                            "path": "/_search",
                            "method": "GET",
                            "runtime_status": "implemented-read",
                        }
                    ],
                    {},
                    {},
                )
            finally:
                backlog.TASKS = original_tasks

            rewritten = tasks_path.read_text(encoding="utf-8")

        self.assertIn("- [x] OpenSearch replacement gap backlog", rewritten)
        self.assertIn("  - [x] keep this section", rewritten)
        self.assertNotIn("stale generated row", rewritten)


if __name__ == "__main__":
    unittest.main()
