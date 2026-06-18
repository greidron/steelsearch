#!/usr/bin/env python3
"""Tests for REST compatibility report validation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check-rest-compat-report.py")
SPEC = importlib.util.spec_from_file_location("check_rest_compat_report", MODULE_PATH)
assert SPEC is not None
check_rest_compat_report = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_rest_compat_report)


class RestCompatReportTests(unittest.TestCase):
    def test_partial_report_allows_missing_fixture_cases(self) -> None:
        fixture = {
            "cases": [
                {"name": "included"},
                {"name": "not_selected"},
            ],
        }
        report = {
            "cases": [
                {"name": "included", "status": "passed"},
            ],
            "summary": {"passed": 1, "failed": 0, "skipped": 0, "skips": []},
        }

        errors = check_rest_compat_report.validate_report(
            fixture,
            report,
            allow_partial=True,
        )

        self.assertEqual(errors, [])

    def test_complete_report_rejects_missing_fixture_cases(self) -> None:
        fixture = {
            "cases": [
                {"name": "included"},
                {"name": "not_selected"},
            ],
        }
        report = {
            "cases": [
                {"name": "included", "status": "passed"},
            ],
            "summary": {"passed": 1, "failed": 0, "skipped": 0, "skips": []},
        }

        errors = check_rest_compat_report.validate_report(fixture, report)

        self.assertEqual(
            errors,
            ["report is missing fixture cases: not_selected"],
        )

    def test_partial_report_still_rejects_failed_cases(self) -> None:
        fixture = {"cases": [{"name": "included"}]}
        report = {
            "cases": [
                {"name": "included", "status": "failed"},
            ],
            "summary": {"passed": 0, "failed": 1, "skipped": 0, "skips": []},
        }

        errors = check_rest_compat_report.validate_report(
            fixture,
            report,
            allow_partial=True,
        )

        self.assertEqual(errors, ["failed cases: included"])


if __name__ == "__main__":
    unittest.main()
