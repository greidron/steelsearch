#!/usr/bin/env python3
"""Tests for PIT E2E coverage checker."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import time
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
                    "classification_cases": {
                        "canonical_equal": sorted(required_cases),
                        "strict_equal": [],
                        "semantic_equal": [],
                        "failed": [],
                        "known_gap_or_skipped": [],
                        "missing": [],
                        "steelsearch_fail_closed": [],
                        "steelsearch_only": [],
                    },
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
        self.assertEqual(
            result["summary"]["required_pit_compared_case_count"],
            result["summary"]["required_pit_case_count"],
        )
        self.assertEqual(
            result["summary"]["required_pit_compared_case_name_digest"],
            result["summary"]["required_pit_case_name_digest"],
        )
        self.assertIsInstance(result["summary"]["pit_case_name_digest"], str)
        self.assertTrue(result["summary"]["unified_report_fresh"])

    def test_stable_name_digest_sorts_names_before_hashing(self) -> None:
        self.assertEqual(
            self.checker.stable_name_digest(["b", "a"]),
            self.checker.stable_name_digest(["a", "b"]),
        )
        self.assertNotEqual(
            self.checker.stable_name_digest(["a", "b"]),
            self.checker.stable_name_digest(["a", "c"]),
        )

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
                        "classification_cases": {
                            "canonical_equal": sorted(required_cases),
                            "strict_equal": [],
                            "semantic_equal": [],
                            "failed": [],
                            "known_gap_or_skipped": [],
                            "missing": [],
                            "steelsearch_fail_closed": [],
                            "steelsearch_only": [],
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

    def test_checker_rejects_required_pit_case_classified_as_steelsearch_only(self) -> None:
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
                                    "name": case_name,
                                    "status": "passed",
                                    "steps": [
                                        {
                                            "method": "POST",
                                            "path": "/logs/_search/point_in_time?keep_alive=1m",
                                        }
                                    ],
                                }
                                for case_name in sorted(required_cases)
                            ]
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                compared_cases = sorted(required_cases)
                steel_only_cases = []
                if suite_name == "search-compat":
                    compared_cases = [
                        case for case in compared_cases if case != "pit_search"
                    ]
                    steel_only_cases = ["pit_search"]
                suite_results.append(
                    {
                        "name": suite_name,
                        "has_opensearch_target": True,
                        "report_path": str(report_path),
                        "classification_cases": {
                            "canonical_equal": compared_cases,
                            "strict_equal": [],
                            "semantic_equal": [],
                            "failed": [],
                            "known_gap_or_skipped": [],
                            "missing": [],
                            "steelsearch_fail_closed": [],
                            "steelsearch_only": steel_only_cases,
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

        self.assertEqual(result["status"], "failed")
        self.assertTrue(
            any(
                "required PIT cases are not classified as OpenSearch comparisons: pit_search"
                in error
                for error in result["errors"]
            )
        )
        self.assertTrue(
            any(
                "required PIT cases have non-comparison classifications: pit_search=steelsearch_only"
                in error
                for error in result["errors"]
            )
        )

    def test_checker_rejects_embedded_pit_cases_without_case_gaps_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            suite_results = []
            for suite_name, required_cases in self.checker.REQUIRED_PIT_CASES.items():
                suite_results.append(
                    {
                        "name": suite_name,
                        "has_opensearch_target": True,
                        "report_path": str(temp_dir / f"{suite_name}.json"),
                        "passed_cases": sorted(required_cases),
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

        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("case_gaps must be an object" in error for error in result["errors"]))

    def test_checker_rejects_embedded_pit_cases_with_malformed_gap_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            suite_results = []
            for suite_name, required_cases in self.checker.REQUIRED_PIT_CASES.items():
                suite_results.append(
                    {
                        "name": suite_name,
                        "has_opensearch_target": True,
                        "report_path": str(temp_dir / f"{suite_name}.json"),
                        "passed_cases": sorted(required_cases),
                        "case_gaps": {
                            "missing": [],
                            "extra": [],
                            "failed": "pit_search",
                            "skipped": [""],
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

        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("case_gaps.failed must be a list" in error for error in result["errors"]))
        self.assertTrue(
            any("case_gaps.skipped entries must be non-empty strings" in error for error in result["errors"])
        )

    def test_checker_rejects_stale_unified_report_when_age_gate_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_value:
            unified_path = self.write_report_set(Path(temp_dir_value))
            stale_mtime = time.time() - 120.0
            os.utime(unified_path, (stale_mtime, stale_mtime))

            result = self.checker.check_unified_report(
                unified_path,
                require_all_pit_passed=True,
                max_report_age_seconds=60,
            )

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["summary"]["unified_report_fresh"])
        self.assertTrue(any("stale" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
