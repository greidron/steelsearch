import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOAD_EVIDENCE_PATH = ROOT / "tools" / "generate-load-evidence.py"


def load_module():
    module_name = "generate_load_evidence"
    spec = importlib.util.spec_from_file_location(module_name, LOAD_EVIDENCE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class LoadEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.generator = load_module()

    def test_dry_run_reports_server_and_load_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "http-load-baseline.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(LOAD_EVIDENCE_PATH),
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
            self.assertIn("run-http-load-baseline.py", result.stdout)
            self.assertIn("steelsearch-release-load-current", result.stdout)

    def test_load_command_targets_release_load_output(self):
        command = self.generator.build_load_command(
            root=ROOT,
            output=Path("target/release-load-current/http-load-baseline.json"),
            http_port=19201,
            duration_seconds=30.0,
            clients=4,
            corpus_size=256,
            vector_dimension=8,
            process_pid="123",
            log_dir=Path("target/release-load-current/logs"),
        )

        self.assertIn("tools/run-http-load-baseline.py", command[1])
        self.assertIn("--process-pid", command)
        self.assertIn("target/release-load-current/http-load-baseline.json", command)


if __name__ == "__main__":
    unittest.main()
