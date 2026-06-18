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
        self.assertEqual(
            report["summary"]["matched_probe_count"],
            report["summary"]["probe_count"],
        )
        self.assertEqual(
            report["summary"]["evidenced_family_count"],
            report["summary"]["family_count"],
        )

    def test_markdown_uses_watchpoint_language(self) -> None:
        rendered = load_module().render_markdown(load_module().build_report())

        self.assertIn("| Category | Name | Matched | Source | Watchpoint |", rendered)
        self.assertNotIn("| Category | Name | Matched | Source | Risk |", rendered)


if __name__ == "__main__":
    unittest.main()
