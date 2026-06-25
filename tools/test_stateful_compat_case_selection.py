#!/usr/bin/env python3
"""Tests for stateful compatibility case filtering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType


def load_tool_module(name: str) -> ModuleType:
    module_path = Path(__file__).with_name(f"{name}.py")
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


if __name__ == "__main__":
    unittest.main()
