import importlib.util
import json
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
                "final-chaos.json",
                "final-packaging.json",
                "final-rolling-upgrade.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))
            self.write_valid_benchmark(temp_dir / "final-benchmark.jsonl", now)
            self.write_valid_load(temp_dir / "final-load.json", now)
            self.write_valid_load_comparison(temp_dir / "final-load-comparison.json", now)

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
                "final-chaos.json",
                "final-packaging.json",
                "final-rolling-upgrade.json",
            ]:
                path = temp_dir / name
                path.write_text("{}\n", encoding="utf-8")
                os.utime(path, (now, now))
            self.write_valid_benchmark(temp_dir / "final-benchmark.jsonl", now)
            self.write_valid_load(temp_dir / "final-load.json", now)

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

    def test_inventory_rejects_structurally_invalid_latest_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            load = temp_dir / "final-load.json"
            load.write_text(
                json.dumps({"summary": {"error_count": 1, "operation_count": 10}}),
                encoding="utf-8",
            )
            os.utime(load, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_test_coverage"]
            self.assertFalse(item["ready"])
            self.assertIn("load JSON summary.error_count=1", item["blockers"])

    def test_inventory_rejects_dry_run_load_comparison(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            now = 1_000_000.0
            comparison = temp_dir / "final-load-comparison.json"
            comparison.write_text(
                json.dumps(
                    {
                        "targets": {
                            "steelsearch": {"returncode": 0},
                            "opensearch": {"returncode": 0},
                        },
                        "comparison": {"mode": "dry-run"},
                    }
                ),
                encoding="utf-8",
            )
            os.utime(comparison, (now, now))

            report = self.inventory.build_inventory(
                temp_dir,
                max_age_seconds=60.0,
                require_complete=False,
                now=now,
            )

            item = report["items"]["load_comparison"]
            self.assertFalse(item["ready"])
            self.assertIn("load comparison is a dry-run report", item["blockers"])

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

    def write_valid_benchmark(self, path: Path, now: float):
        path.write_text(json.dumps({"benchmark": "final-smoke"}) + "\n", encoding="utf-8")
        os.utime(path, (now, now))

    def write_valid_load(self, path: Path, now: float):
        path.write_text(
            json.dumps({"summary": {"error_count": 0, "operation_count": 10}}),
            encoding="utf-8",
        )
        os.utime(path, (now, now))

    def write_valid_load_comparison(self, path: Path, now: float):
        path.write_text(
            json.dumps(
                {
                    "targets": {
                        "steelsearch": {"returncode": 0},
                        "opensearch": {"returncode": 0},
                    },
                    "comparison": {"mode": "completed"},
                }
            ),
            encoding="utf-8",
        )
        os.utime(path, (now, now))


if __name__ == "__main__":
    unittest.main()
