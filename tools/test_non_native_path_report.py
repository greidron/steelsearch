#!/usr/bin/env python3
"""Tests for the non-native path inventory report."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "report-non-native-paths.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "report_non_native_paths",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["report_non_native_paths"] = module
    spec.loader.exec_module(module)
    return module


class NonNativePathReportTests(unittest.TestCase):
    def test_report_excludes_format_and_binary_compatibility(self) -> None:
        report = load_module().build_report()

        self.assertEqual(
            report["scope"]["excluded"],
            [
                "OpenSearch response formatting",
                "OpenSearch snapshot-file compatibility",
                "Lucene segment or translog binary compatibility",
            ],
        )

    def test_current_inventory_has_no_missing_evidence(self) -> None:
        report = load_module().build_report()

        self.assertEqual(report["summary"]["missing_probe_count"], 0)
        self.assertEqual(report["summary"]["missing_family_count"], 0)
        self.assertEqual(report["summary"]["missing_category_count"], 0)
        self.assertEqual(report["summary"]["missing_categories"], [])
        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(
            report["summary"]["matched_probe_count"],
            report["summary"]["probe_count"],
        )
        self.assertEqual(
            report["summary"]["evidenced_family_count"],
            report["summary"]["family_count"],
        )

    def test_current_inventory_covers_every_required_workstream_category(self) -> None:
        report = load_module().build_report()

        self.assertEqual(
            set(report["summary"]["required_categories"]),
            {
                "source-backed query",
                "materialization",
                "vector-hybrid",
                "mixed-cluster",
                "runtime",
                "security",
            },
        )
        self.assertEqual(
            set(report["summary"]["required_categories"]) - set(report["summary"]["covered_categories"]),
            set(),
        )

    def test_markdown_uses_watchpoint_language(self) -> None:
        rendered = load_module().render_markdown(load_module().build_report())

        self.assertIn("| Category | Name | Matched | Source | Watchpoint |", rendered)
        self.assertNotIn("| Category | Name | Matched | Source | Risk |", rendered)

    def test_release_readiness_next_action_requires_manifest_checker(self) -> None:
        report = load_module().build_report()
        production_security = next(
            family
            for family in report["families"]
            if family["category"] == "security" and family["name"] == "production security"
        )

        self.assertIn(
            "check-release-readiness-evidence.py --require-passed",
            production_security["next_action"],
        )
        self.assertIn(
            "report-release-evidence-inventory.py --require-complete",
            production_security["next_action"],
        )
        self.assertIn("promotion-gate-suite", production_security["next_action"])
        self.assertIn("promotion gate suite artifact", production_security["status"])

    def test_nested_filtered_knn_is_reported_as_vector_native_boundary(self) -> None:
        report = load_module().build_report()

        probe = next(
            probe
            for probe in report["probes"]
            if probe["name"] == "nested filtered kNN parity and native boundary"
        )
        family = next(
            family
            for family in report["families"]
            if family["name"] == "nested filtered kNN"
        )

        self.assertTrue(probe["matched"])
        self.assertTrue(family["evidenced"])
        self.assertIn("OpenSearch-parity scenario covered", family["status"])
        self.assertIn("native child-ordinal execution", family["status"])
        self.assertIn("min_score or max_distance", family["next_action"])


if __name__ == "__main__":
    unittest.main()
