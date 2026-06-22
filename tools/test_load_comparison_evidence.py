import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate-load-comparison-evidence.py"


class LoadComparisonEvidenceTests(unittest.TestCase):
    def test_dry_run_reports_opensearch_and_comparison_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "http-load-comparison.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--dry-run",
                    "--output",
                    str(output),
                    "--work-dir",
                    temp_dir_value,
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("run-opensearch-dev.sh", result.stdout)
            self.assertIn("run-http-load-comparison.py", result.stdout)
            self.assertIn("steelsearch-release-load-comparison", result.stdout)
            self.assertIn("write=25,lexical=25,ranking=20,facet=15,sort_filter=10,refresh=5", result.stdout)


if __name__ == "__main__":
    unittest.main()
