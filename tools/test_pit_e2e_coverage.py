#!/usr/bin/env python3
"""Tests for PIT E2E coverage checker."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


def load_tool_module() -> ModuleType:
    module_path = Path(__file__).with_name("check-pit-e2e-coverage.py")
    spec = importlib.util.spec_from_file_location("check_pit_e2e_coverage", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PitE2ECoverageCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.checker = load_tool_module()

    def write_report_set(
        self,
        temp_dir: Path,
        *,
        missing_case: str | None = None,
        non_passed_case: str | None = None,
    ) -> Path:
        suite_results = []
        for suite_name, required_cases in self.checker.REQUIRED_PIT_CASES.items():
            report_path = temp_dir / f"{suite_name}.json"
            cases = []
            for case_name in sorted(required_cases):
                if case_name == missing_case:
                    continue
                cases.append(
                    {
                        "name": case_name,
                        "status": "skipped" if case_name == non_passed_case else "passed",
                        "extract": "pit_open" if case_name == "pit_open_search" else "search_hits",
                        "steps": [
                            {
                                "method": "POST",
                                "path": "/logs/_search/point_in_time?keep_alive=1m",
                            }
                        ],
                    }
                )
            report_path.write_text(
                json.dumps({"cases": cases}, indent=2) + "\n",
                encoding="utf-8",
            )
            suite_results.append(
                {
                    "name": suite_name,
                    "has_opensearch_target": True,
                    "report_path": str(report_path),
                }
            )
        unified_path = temp_dir / "unified.json"
        unified_path.write_text(
            json.dumps({"suite_results": suite_results}, indent=2) + "\n",
            encoding="utf-8",
        )
        return unified_path

    def test_checker_accepts_required_pit_cases_when_all_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            unified_path = self.write_report_set(Path(temp_dir_value))

            result = self.checker.check_unified_report(
                unified_path,
                require_all_pit_passed=True,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["non_passed_pit_case_count"], 0)
        self.assertEqual(result["summary"]["suite_count"], 3)

    def test_checker_rejects_missing_required_pit_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            unified_path = self.write_report_set(
                Path(temp_dir_value),
                missing_case="pit_search",
            )

            result = self.checker.check_unified_report(
                unified_path,
                require_all_pit_passed=True,
            )

        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("missing required PIT cases: pit_search" in error for error in result["errors"])
        )

    def test_checker_rejects_skipped_pit_case_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            unified_path = self.write_report_set(
                Path(temp_dir_value),
                non_passed_case="pit_search",
            )

            result = self.checker.check_unified_report(
                unified_path,
                require_all_pit_passed=True,
            )

        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any("has non-passed PIT cases: pit_search" in error for error in result["errors"])
        )

    def test_checker_prefers_embedded_unified_cases_over_mutable_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            suite_results = []
            for suite_name, required_cases in self.checker.REQUIRED_PIT_CASES.items():
                report_path = temp_dir / f"{suite_name}.json"
                report_path.write_text(
                    json.dumps(
                        {
                            "cases": [
                                {
                                    "name": "later-partial-non-pit-case",
                                    "status": "passed",
                                }
                            ]
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                suite_results.append(
                    {
                        "name": suite_name,
                        "has_opensearch_target": True,
                        "report_path": str(report_path),
                        "passed_cases": sorted(required_cases),
                        "case_gaps": {
                            "missing": [],
                            "extra": [],
                            "failed": [],
                            "skipped": [],
                        },
                    }
                )
            unified_path = temp_dir / "unified.json"
            unified_path.write_text(
                json.dumps({"suite_results": suite_results}, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.checker.check_unified_report(
                unified_path,
                require_all_pit_passed=True,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["non_passed_pit_case_count"], 0)


if __name__ == "__main__":
    unittest.main()
