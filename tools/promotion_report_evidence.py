#!/usr/bin/env python3
"""Helpers for binding promotion gate requirements to executed reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PASS_STATUSES = {"passed", "canonical_equal", "strict_equal", "semantic_equal"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _case_evidence_classes(case: dict[str, Any]) -> set[str]:
    evidence: set[str] = set()
    for key in ("evidence_class", "evidence_classes"):
        for item in _as_list(case.get(key)):
            if item:
                evidence.add(str(item))
    metadata = case.get("metadata") or {}
    if isinstance(metadata, dict):
        for key in ("evidence_class", "evidence_classes"):
            for item in _as_list(metadata.get(key)):
                if item:
                    evidence.add(str(item))
    return evidence


def _iter_cases(report: dict[str, Any]) -> list[dict[str, Any]]:
    cases = report.get("cases")
    if isinstance(cases, list):
        return [case for case in cases if isinstance(case, dict)]

    suite_cases: list[dict[str, Any]] = []
    for suite in report.get("suite_results") or []:
        if not isinstance(suite, dict):
            continue
        for case in suite.get("cases") or []:
            if isinstance(case, dict):
                suite_cases.append(case)
    return suite_cases


def load_report_evidence(report_paths: list[Path]) -> dict[str, Any]:
    cases_by_name: dict[str, dict[str, Any]] = {}
    evidence_classes: set[str] = set()
    loaded_reports: list[str] = []

    for report_path in report_paths:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        loaded_reports.append(str(report_path))
        for case in _iter_cases(report):
            name = case.get("name")
            if not name:
                continue
            case_name = str(name)
            cases_by_name[case_name] = case
            if case.get("status") in PASS_STATUSES:
                evidence_classes.update(_case_evidence_classes(case))

    return {
        "cases_by_name": cases_by_name,
        "evidence_classes": evidence_classes,
        "loaded_reports": loaded_reports,
    }


def validate_report_evidence(
    report_paths: list[Path],
    required_cases: set[str],
    required_evidence_classes: set[str],
) -> list[str]:
    evidence = load_report_evidence(report_paths)
    cases_by_name: dict[str, dict[str, Any]] = evidence["cases_by_name"]
    observed_evidence_classes: set[str] = evidence["evidence_classes"]

    errors: list[str] = []
    missing_cases = sorted(required_cases - set(cases_by_name))
    if missing_cases:
        errors.append(f"report evidence missing required cases: {missing_cases}")

    non_passed_cases = sorted(
        case_name
        for case_name in required_cases
        if case_name in cases_by_name and cases_by_name[case_name].get("status") not in PASS_STATUSES
    )
    if non_passed_cases:
        errors.append(f"report evidence has non-passed required cases: {non_passed_cases}")

    missing_evidence = sorted(required_evidence_classes - observed_evidence_classes)
    if missing_evidence:
        errors.append(f"report evidence missing required evidence classes: {missing_evidence}")

    return errors
