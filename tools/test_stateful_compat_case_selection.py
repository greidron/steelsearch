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


if __name__ == "__main__":
    unittest.main()
