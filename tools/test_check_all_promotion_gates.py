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
INVENTORY = ROOT / "tools" / "report-release-evidence-inventory.py"


def load_check_all_module():
    module_name = "check_all_promotion_gates"
    spec = importlib.util.spec_from_file_location(module_name, CHECK_ALL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_inventory_module():
    module_name = "report_release_evidence_inventory_for_check_all_test"
    spec = importlib.util.spec_from_file_location(module_name, INVENTORY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class CheckAllPromotionGatesTests(unittest.TestCase):
    def setUp(self):
        self.check_all = load_check_all_module()
        self.inventory = load_inventory_module()

    def test_suite_check_names_are_complete_and_ordered(self):
        self.assertEqual(
            [name for name, _command in self.check_all.CHECKS],
            [
                "source-compatibility-drift",
                "source-compatibility-closure",
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
                "benchmark-evidence",
                "peer-node",
                "security-row-reclassification",
                "transport-action-coverage",
                "broad-unified-e2e-sections",
                "rest-api-live-source-coverage",
                "e2e-doc-current-counts",
                "runtime-control-surface-inventory",
                "mixed-cluster-coverage",
                "release-evidence-inventory",
                "external-interop",
                "migration",
                "harness",
            ],
        )

    def test_suite_check_names_match_release_inventory_contract(self):
        runner_names = {name for name, _command in self.check_all.CHECKS}
        inventory_names = (
            set(self.inventory.REQUIRED_PROMOTION_GATE_CHECKS)
            | set(self.inventory.OPTIONAL_PROMOTION_GATE_CHECKS)
        )

        self.assertEqual(runner_names, inventory_names)
        self.assertIn(self.check_all.RELEASE_EVIDENCE_CHECK_NAME, runner_names)
        self.assertIn(
            self.check_all.RELEASE_EVIDENCE_CHECK_NAME,
            self.inventory.OPTIONAL_PROMOTION_GATE_CHECKS,
        )

    def test_source_compatibility_closure_gate_requires_current_matrix_baseline(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["source-compatibility-closure"]

        self.assertEqual(
            command,
            [
                "tools/run-native-closure-validation.py",
                "--batch",
                "source-compatibility-current",
                "--format",
                "json",
            ],
        )

    def test_rest_api_live_source_coverage_gate_uses_full_current_floor(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["rest-api-live-source-coverage"]
        command_text = " ".join(command)

        self.assertIn("tools/report-rest-api-coverage.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)
        self.assertIn("--require-live-required-suites", command_text)
        self.assertIn("--min-live-required-matched-source-route-count", command_text)
        self.assertIn("378", command)
        self.assertIn("--min-live-required-matched-source-route-ratio", command_text)
        self.assertIn("1.0", command)
        self.assertIn("--min-source-route-count", command_text)
        self.assertIn("389", command)
        self.assertIn("--require-closed-source-statuses", command)
        self.assertIn("target/rest-api-coverage-current-check.json", command)

    def test_benchmark_evidence_gate_requires_fresh_complete_report(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["benchmark-evidence"]
        command_text = " ".join(command)

        self.assertIn("tools/check-benchmark-evidence.py", command_text)
        self.assertIn("target/release-benchmarks/deterministic-benchmark-baselines.jsonl", command)
        self.assertIn("target/release-benchmarks/benchmark-report.json", command)
        self.assertIn("--comparison-summary", command)
        self.assertIn("target/search-benchmark-matrix-current-20260630T023334Z/summary.json", command)
        self.assertIn("--max-age-seconds", command)
        self.assertIn("604800", command)

    def test_peer_node_gate_requires_fresh_reports(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["peer-node"]
        command_text = " ".join(command)

        self.assertIn("tools/check-peer-node-promotion-gate.py", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)

    def test_pit_e2e_coverage_gate_requires_fresh_report(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["pit-e2e-coverage"]
        command_text = " ".join(command)

        self.assertIn("tools/check-pit-e2e-coverage.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-pit-current/unified-opensearch-e2e-report.json", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)
        self.assertIn("--require-all-pit-passed", command_text)

    def test_transport_action_coverage_gate_requires_fresh_peer_report(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["transport-action-coverage"]
        command_text = " ".join(command)

        self.assertIn("tools/report-transport-action-coverage.py", command_text)
        self.assertIn("--require-peer-backpressure", command_text)
        self.assertIn("--require-release-parity", command_text)
        self.assertIn("--require-closed-action-statuses", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)
        self.assertIn("target/transport-action-coverage-current-check.json", command)

    def test_broad_unified_e2e_sections_gate_requires_all_parity_sections(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["broad-unified-e2e-sections"]
        command_text = " ".join(command)

        self.assertIn("tools/check-unified-opensearch-e2e-report.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)
        self.assertIn("--require-no-unresolved-skips", command_text)
        for section in (
            "route_parity",
            "semantic_parity",
            "durability_parity",
            "security_parity",
            "distributed_parity",
        ):
            self.assertIn(section, command)

    def test_mixed_cluster_coverage_gate_requires_fresh_reports(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["mixed-cluster-coverage"]
        command_text = " ".join(command)

        self.assertIn("tools/report-mixed-cluster-coverage.py", command_text)
        self.assertIn("--require-passed", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command)
        self.assertIn("--shard-movement-report", command_text)
        self.assertIn("target/three-node-shard-movement-interruption-current/report.json", command)
        self.assertIn("target/mixed-cluster-coverage-current-check.json", command)

    def test_release_evidence_inventory_gate_requires_complete_fresh_record(self):
        checks = dict(self.check_all.CHECKS)
        command = checks["release-evidence-inventory"]
        command_text = " ".join(command)

        self.assertIn("tools/report-release-evidence-inventory.py", command_text)
        self.assertIn("--root", command)
        self.assertIn("target", command)
        self.assertIn("--max-age-seconds", command)
        self.assertIn("604800", command)
        self.assertIn("--require-complete", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-evidence-inventory-current-check.json", command)

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
            old_default_output = self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT
            old_checks = self.check_all.CHECKS
            old_argv = sys.argv
            try:
                self.check_all.REPO_ROOT = temp_dir
                self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT = (
                    temp_dir / "target/promotion-gate-suite-current.json"
                )
                self.check_all.CHECKS = [("shell-probe", ["/bin/true"])]
                sys.argv = [str(CHECK_ALL), "--output", str(output)]
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.check_all.main()
            finally:
                self.check_all.REPO_ROOT = old_root
                self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT = old_default_output
                self.check_all.CHECKS = old_checks
                sys.argv = old_argv

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["passed"], 1)
            self.assertEqual(payload["failed"], 0)
            self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_main_writes_pre_release_suite_before_release_inventory_check(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            tools_dir = temp_dir / "tools"
            tools_dir.mkdir()
            release_probe = tools_dir / "release_probe.py"
            release_probe.write_text(
                "import json, pathlib\n"
                "suite = pathlib.Path('target/promotion-gate-suite-current.json')\n"
                "payload = json.loads(suite.read_text(encoding='utf-8'))\n"
                "names = [check['name'] for check in payload['checks']]\n"
                "assert names == ['core-probe'], names\n"
                "assert payload['status'] == 'ok'\n"
                "pathlib.Path('release-saw-pre-suite.txt').write_text('ok', encoding='utf-8')\n",
                encoding="utf-8",
            )
            output = temp_dir / "final-suite.json"

            old_root = self.check_all.REPO_ROOT
            old_default_output = self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT
            old_checks = self.check_all.CHECKS
            old_argv = sys.argv
            try:
                self.check_all.REPO_ROOT = temp_dir
                self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT = (
                    temp_dir / "target/promotion-gate-suite-current.json"
                )
                self.check_all.CHECKS = [
                    ("core-probe", ["/bin/true"]),
                    (
                        self.check_all.RELEASE_EVIDENCE_CHECK_NAME,
                        ["tools/release_probe.py"],
                    ),
                ]
                sys.argv = [str(CHECK_ALL), "--output", str(output)]
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = self.check_all.main()
            finally:
                self.check_all.REPO_ROOT = old_root
                self.check_all.DEFAULT_PROMOTION_GATE_OUTPUT = old_default_output
                self.check_all.CHECKS = old_checks
                sys.argv = old_argv

            self.assertEqual(result, 0)
            self.assertEqual(
                (temp_dir / "release-saw-pre-suite.txt").read_text(encoding="utf-8"),
                "ok",
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                [check["name"] for check in payload["checks"]],
                ["core-probe", self.check_all.RELEASE_EVIDENCE_CHECK_NAME],
            )
            self.assertEqual(json.loads(stdout.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
