import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run-native-closure-validation.py"


def load_runner_module():
    module_name = "run_native_closure_validation"
    spec = importlib.util.spec_from_file_location(
        module_name, RUNNER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class NativeClosureValidationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner_module()

    def test_parse_json_payload_skips_prefix_logs(self):
        payload = self.runner.parse_json_payload('log line\n{"summary":{"passed":true}}\n')

        self.assertEqual(payload, {"summary": {"passed": True}})

    def test_mixed_shard_movement_batch_uses_required_interruption_probe(self):
        batch = self.runner.BATCHES["mixed-shard-movement"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/probe_three_node_shard_movement.py", command)
        self.assertIn("--exercise-interruption", command)
        self.assertIn("--require-interruption", command)

    def test_non_native_inventory_batch_runs_json_report(self):
        batch = self.runner.BATCHES["non-native-inventory"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/report-non-native-paths.py", command)
        self.assertIn("--format", command)
        self.assertIn("json", command)

    def test_e2e_required_parity_batch_checks_no_skips_for_required_suites(self):
        batch = self.runner.BATCHES["e2e-required-parity"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/run-unified-opensearch-e2e.py", command_text)
        self.assertIn("search-semantic", command_text)
        self.assertIn("vector-search", command_text)
        self.assertIn("tools/check-unified-opensearch-e2e-report.py", command_text)
        self.assertIn("--require-no-skips", command_text)

    def test_runtime_lifecycle_batch_includes_explicit_hook_contract(self):
        batch = self.runner.BATCHES["runtime-lifecycle"]

        self.assertTrue(any(
            case.name == "runtime_lifecycle_hooks_describe_shutdown_and_recovery_admission_boundaries"
            for case in batch
        ))
        self.assertTrue(any(case.group == "runtime-lifecycle-shutdown" for case in batch))
        self.assertTrue(any(case.group == "runtime-lifecycle-recovery" for case in batch))

    def test_runtime_peer_backpressure_batch_declares_mixed_query_phase_profile(self):
        batch = self.runner.BATCHES["runtime-peer-backpressure"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/compare_remote_transport_backpressure.py", command)
        self.assertIn("--profile", command)
        self.assertIn("mixed-java-rust-query-phase", command)
        self.assertIn("--output", command)
        self.assertIn("target/runtime-peer-backpressure-current.json", command)

    def test_external_validation_reads_summary_passed(self):
        case = self.runner.ExternalValidation(
            "synthetic_external_validation",
            "synthetic",
            (
                sys.executable,
                "-c",
                "import json; print(json.dumps({'summary': {'passed': True}}))",
            ),
        )

        result = self.runner.run_test(case)

        self.assertTrue(result["ok"])
        self.assertEqual(result["running"], 1)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["failed"], 0)


if __name__ == "__main__":
    unittest.main()
