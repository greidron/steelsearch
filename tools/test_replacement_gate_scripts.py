import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReplacementGateScriptTests(unittest.TestCase):
    def run_command(self, *args, env=None):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            args,
            cwd=ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_development_replacement_gate_dry_run_sequence(self):
        result = self.run_command("./tools/run-development-replacement-gate.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "+ cargo build -p os-node --bin steelsearch",
                "+ cargo build -p os-node --features development-runtime --bin steelsearch",
                "+ cargo test --workspace --no-run",
                "+ tools/run-steelsearch-smoke.sh",
                "+ tools/run-daemon-backed-search-compat.sh",
                "+ tools/run-cargo-test-group.sh unit",
                "+ tools/run-cargo-test-group.sh daemon-integration",
                "+ tools/run-cargo-test-group.sh migration",
                "+ tools/run-cargo-test-group.sh k-nn",
                "+ tools/run-cargo-test-group.sh model-serving",
                "+ tools/run-cargo-test-group.sh multi-node",
            ],
        )

    def test_development_replacement_gate_rejects_unknown_args(self):
        result = self.run_command("./tools/run-development-replacement-gate.sh", "--bogus")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

    def test_daemon_backed_search_compat_dry_run_forwards_report_path(self):
        result = self.run_command(
            "./tools/run-daemon-backed-search-compat.sh",
            "--dry-run",
            "--report",
            "target/test-search-compat-report.json",
            env={"STEELSEARCH_URL": "http://127.0.0.1:9200"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "+ export STEELSEARCH_URL=http://127.0.0.1:9200",
            result.stdout,
        )
        self.assertIn(
            "+ tools/run-search-compat.sh --report target/test-search-compat-report.json",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
