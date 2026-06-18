import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "tools" / "report-release-evidence-inventory.py"


def load_inventory_module():
    module_name = "report_release_evidence_inventory"
    spec = importlib.util.spec_from_file_location(module_name, INVENTORY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseEvidenceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = load_inventory_module()

    def test_complete_inventory_reports_all_readiness_items_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            for name in [
                "final-benchmark.jsonl",
                "final-load.json",
                "final-load-comparison.json",
                "final-chaos.json",
                "final-packaging.json",
                "final-rolling-upgrade.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=True,
                now=now,
            )

            self.assertTrue(report["summary"]["passed"])
            self.assertTrue(report["summary"]["complete"])
            self.assertEqual(report["summary"]["startup_missing_items"], [])
            self.assertEqual(report["summary"]["readiness_attachment_missing_items"], [])
            self.assertIn("--load-comparison-report", report["attach_command_template"])

    def test_inventory_distinguishes_startup_and_readiness_only_missing_items(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            for name in [
                "final-benchmark.jsonl",
                "final-load.json",
                "final-chaos.json",
                "final-packaging.json",
                "final-rolling-upgrade.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=True,
                now=now,
            )

            self.assertFalse(report["summary"]["passed"])
            self.assertEqual(report["summary"]["startup_missing_items"], [])
            self.assertEqual(
                report["summary"]["readiness_attachment_missing_items"],
                ["load_comparison"],
            )

    def test_cli_returns_nonzero_when_complete_inventory_is_required(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            result = subprocess.run(
                [
                    sys.executable,
                    str(INVENTORY_PATH),
                    "--root",
                    temp_dir_value,
                    "--require-complete",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("benchmark_coverage", result.stdout)


if __name__ == "__main__":
    unittest.main()
