import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROLLING_PATH = ROOT / "tools" / "generate-rolling-upgrade-evidence.py"


def load_rolling_module():
    module_name = "generate_rolling_upgrade_evidence"
    spec = importlib.util.spec_from_file_location(module_name, ROLLING_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RollingUpgradeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rolling = load_rolling_module()

    def test_validate_transcript_accepts_fixture_order(self):
        profile = {
            "steps": ["cluster-ready-before", "node-1-upgrade"],
            "transcript_assertions": ["ordered"],
        }
        transcript = {
            "profile": "rolling-upgrade",
            "status": "completed",
            "steps": ["cluster-ready-before", "node-1-upgrade"],
            "transcript": ["cluster-ready-before", "node-1-upgrade"],
            "transcript_assertions": ["ordered"],
        }

        self.assertEqual(self.rolling.validate_transcript(transcript, profile), [])

    def test_validate_transcript_rejects_out_of_order_steps(self):
        profile = {
            "steps": ["cluster-ready-before", "node-1-upgrade"],
            "transcript_assertions": ["ordered"],
        }
        transcript = {
            "profile": "rolling-upgrade",
            "status": "completed",
            "steps": ["cluster-ready-before", "node-1-upgrade"],
            "transcript": ["node-1-upgrade", "cluster-ready-before"],
            "transcript_assertions": ["ordered"],
        }

        errors = self.rolling.validate_transcript(transcript, profile)

        self.assertIn("transcript execution order does not match fixture", errors)

    def test_validate_transcript_rejects_unsatisfied_assertion(self):
        profile = {
            "steps": [
                "cluster-ready-before",
                "node-1-upgrade",
                "cluster-ready-after-node-1",
                "node-2-upgrade",
                "cluster-ready-after-node-2",
                "node-3-upgrade",
                "cluster-ready-after-node-3",
            ],
            "transcript_assertions": ["cluster ready after each upgraded node rejoins"],
        }
        transcript = {
            "profile": "rolling-upgrade",
            "status": "completed",
            "steps": profile["steps"],
            "transcript": [
                "cluster-ready-before",
                "node-1-upgrade",
                "cluster-ready-after-node-1",
                "node-2-upgrade",
                "cluster-ready-after-node-2",
                "node-3-upgrade",
            ],
            "transcript_assertions": ["cluster ready after each upgraded node rejoins"],
        }

        errors = self.rolling.validate_transcript(transcript, profile)

        self.assertIn(
            "transcript assertion not satisfied: cluster ready after each upgraded node rejoins",
            errors,
        )

    def test_cli_writes_rolling_upgrade_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "rolling-upgrade-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROLLING_PATH),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(
                payload["summary"]["coverage_scope"],
                "rolling-upgrade transcript fixture",
            )
            self.assertTrue(all(payload["assertion_hits"].values()))


if __name__ == "__main__":
    unittest.main()
