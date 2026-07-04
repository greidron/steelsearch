import importlib.util
import contextlib
import io
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECK_ALL = ROOT / "tools" / "check-all-promotion-gates.py"


def load_check_all_module():
    module_name = "check_all_promotion_gates"
    spec = importlib.util.spec_from_file_location(module_name, CHECK_ALL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class CheckAllPromotionGatesTests(unittest.TestCase):
    def setUp(self):
        self.check_all = load_check_all_module()

    def test_suite_check_names_are_complete_and_ordered(self):
        self.assertEqual(
            [name for name, _command in self.check_all.CHECKS],
            [
                "source-compatibility-drift",
                "root-identity",
                "index-metadata",
                "document-write",
                "bulk",
                "cluster-admin",
                "search",
                "pit-e2e-coverage",
                "snapshot",
                "vector",
                "knn-plugin",
                "ml",
                "peer-node",
                "security-row-reclassification",
                "transport-action-coverage",
                "rest-api-live-source-coverage",
                "mixed-cluster-coverage",
                "external-interop",
                "migration",
                "harness",
            ],
        )

    def test_rest_api_live_source_coverage_gate_uses_full_current_floor(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["rest-api-live-source-coverage"]
        command_text = " ".join(command)

        self.assertIn("tools/report-rest-api-coverage.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json", command_text)
        self.assertIn("--require-live-required-suites", command_text)
        self.assertIn("--min-live-required-matched-source-route-count", command_text)
        self.assertIn("378", command)
        self.assertIn("--min-live-required-matched-source-route-ratio", command_text)
        self.assertIn("1.0", command)
        self.assertIn("target/rest-api-coverage-current-check.json", command)

    def test_suite_check_names_are_unique(self):
        names = [name for name, _command in self.check_all.CHECKS]

        self.assertEqual(len(names), len(set(names)))

    def test_run_check_executes_python_scripts_with_current_interpreter(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            script = temp_dir / "probe.py"
            script.write_text(
                "import pathlib, sys\n"
                "pathlib.Path('python-executable.txt').write_text(sys.executable, encoding='utf-8')\n",
                encoding="utf-8",
            )

            old_root = self.check_all.REPO_ROOT
            try:
                self.check_all.REPO_ROOT = temp_dir
                result = self.check_all.run_check("python-probe", [str(script)])
            finally:
                self.check_all.REPO_ROOT = old_root

            self.assertEqual(result["status"], "ok")
            self.assertEqual(
                (temp_dir / "python-executable.txt").read_text(encoding="utf-8"),
                sys.executable,
            )

    def test_run_check_executes_shell_scripts_directly(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            script = temp_dir / "probe.sh"
            script.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf direct > shell-mode.txt\n",
                encoding="utf-8",
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

            old_root = self.check_all.REPO_ROOT
            try:
                self.check_all.REPO_ROOT = temp_dir
                result = self.check_all.run_check("shell-probe", [str(script)])
            finally:
                self.check_all.REPO_ROOT = old_root

            self.assertEqual(result["status"], "ok")
            self.assertEqual((temp_dir / "shell-mode.txt").read_text(encoding="utf-8"), "direct")

    def test_run_check_reports_failure_with_bounded_output_tails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            script = temp_dir / "fail.sh"
            script.write_text(
                "#!/usr/bin/env bash\n"
                "for i in $(seq 1 25); do echo stdout-$i; done\n"
                "for i in $(seq 1 25); do echo stderr-$i >&2; done\n"
                "exit 7\n",
                encoding="utf-8",
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)

            old_root = self.check_all.REPO_ROOT
            try:
                self.check_all.REPO_ROOT = temp_dir
                result = self.check_all.run_check("failing-probe", [str(script)])
            finally:
                self.check_all.REPO_ROOT = old_root

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["returncode"], 7)
            self.assertNotIn("stdout-5", result["stdout_tail"])
            self.assertIn("stdout-6", result["stdout_tail"])
            self.assertIn("stdout-25", result["stdout_tail"])
            self.assertNotIn("stderr-5", result["stderr_tail"])
            self.assertIn("stderr-6", result["stderr_tail"])
            self.assertIn("stderr-25", result["stderr_tail"])

    def test_main_writes_output_summary_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            output = temp_dir / "promotion-suite.json"

            old_root = self.check_all.REPO_ROOT
            old_checks = self.check_all.CHECKS
            old_argv = sys.argv
            try:
                self.check_all.REPO_ROOT = temp_dir
                self.check_all.CHECKS = [("shell-probe", ["/bin/true"])]
                sys.argv = [str(CHECK_ALL), "--output", str(output)]
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.check_all.main()
            finally:
                self.check_all.REPO_ROOT = old_root
                self.check_all.CHECKS = old_checks
                sys.argv = old_argv

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["passed"], 1)
            self.assertEqual(payload["failed"], 0)
            self.assertEqual(json.loads(stdout.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
