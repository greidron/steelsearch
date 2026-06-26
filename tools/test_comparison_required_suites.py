import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ComparisonRequiredSuitesTests(unittest.TestCase):
    def run_checker(self, fixture: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tools/check-comparison-required-suites.py", str(fixture)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_canonical_fixture_requires_vector_ml_and_migration_evidence_reports(self):
        fixture = ROOT / "tools" / "fixtures" / "comparison-harness-required-suites.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))

        self.assertEqual(
            set(data["profiles"]["vector-ml"]["required_reports"]),
            {
                "vector-search-compat-report.json",
                "knn-plugin-compat-report.json",
                "ml-model-surface-compat-report.json",
                "security-authz-compat-report.json",
            },
        )
        self.assertEqual(
            set(data["profiles"]["snapshot-migration"]["required_reports"]),
            {
                "snapshot-lifecycle-compat-report.json",
                "migration-cutover-integration-report.json",
                "migration-acceptance/report.json",
            },
        )

        result = self.run_checker(fixture)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_checker_rejects_vector_ml_missing_promotion_reports(self):
        fixture = ROOT / "tools" / "fixtures" / "comparison-harness-required-suites.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        data["profiles"]["vector-ml"]["required_reports"] = [
            "vector-search-compat-report.json"
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(data, handle)
            temp_path = Path(handle.name)
        try:
            result = self.run_checker(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("vector-ml: required_reports missing entries", result.stderr)

    def test_checker_rejects_snapshot_migration_missing_cutover_report(self):
        fixture = ROOT / "tools" / "fixtures" / "comparison-harness-required-suites.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
        data["profiles"]["snapshot-migration"]["required_reports"] = [
            "snapshot-lifecycle-compat-report.json",
            "migration-acceptance/report.json",
        ]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(data, handle)
            temp_path = Path(handle.name)
        try:
            result = self.run_checker(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot-migration: required_reports missing entries", result.stderr)


if __name__ == "__main__":
    unittest.main()
