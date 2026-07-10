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

    def test_report_rejects_per_status_summary_drift(self) -> None:
        fixture = {"cases": [{"name": "included"}]}
        report = {
            "cases": [
                {"name": "included", "status": "failed"},
            ],
            "summary": {"passed": 1, "failed": 0, "skipped": 0, "skips": []},
        }

        errors = check_rest_compat_report.validate_report(
            fixture,
            report,
            allow_partial=True,
        )

        self.assertIn("summary passed drift: cases=0 summary=1", errors)
        self.assertIn("summary failed drift: cases=1 summary=0", errors)

    def test_partial_fixture_validation_ignores_unselected_cases(self) -> None:
        fixture = {
            "cases": [
                {"name": "included"},
                {
                    "name": "not_selected",
                    "comparison": "steelsearch_only",
                    "expected_steelsearch_status": 400,
                },
            ],
        }

        errors = check_rest_compat_report.validate_fixture(
            fixture,
            selected_cases={"included"},
        )

        self.assertEqual(errors, [])

    def test_partial_fixture_validation_still_checks_selected_cases(self) -> None:
        fixture = {
            "cases": [
                {
                    "name": "included",
                    "comparison": "steelsearch_only",
                    "expected_steelsearch_status": 400,
                },
            ],
        }

        errors = check_rest_compat_report.validate_fixture(
            fixture,
            selected_cases={"included"},
        )

        self.assertEqual(
            errors,
            [
                "steelsearch_only case [included] is missing skip_scope",
                "steelsearch_only case [included] is missing reason",
                "steelsearch-only evidence case [included] is missing expected_steelsearch_extract",
            ],
        )

    def test_security_authz_plugin_and_repository_cases_require_extract_contract(self) -> None:
        fixture = {
            "cases": [
                {
                    "name": "security_bad_password_ml_register_401",
                    "area": "security-authz",
                    "path": "/_plugins/_ml/models/_register",
                },
                {
                    "name": "security_admin_repository_read_missing_repo",
                    "area": "security-authz",
                    "path": "/_snapshot/security-authz-repo",
                    "expected_steelsearch_extract": {"status": 404},
                },
            ],
        }

        errors = check_rest_compat_report.validate_fixture(fixture)

        self.assertEqual(
            errors,
            [
                "steelsearch-only evidence case [security_bad_password_ml_register_401] is missing expected_steelsearch_extract"
            ],
        )


if __name__ == "__main__":
    unittest.main()
