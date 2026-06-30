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
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command_text)
        self.assertIn("tools/check-unified-opensearch-e2e-report.py", command_text)
        self.assertIn("--require-no-skips", command_text)

    def test_e2e_search_compat_parity_batch_allows_known_skips_but_rejects_failures(self):
        batch = self.runner.BATCHES["e2e-search-compat-parity"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/run-unified-opensearch-e2e.py", command_text)
        self.assertIn("search-compat", command_text)
        self.assertIn("search-strict", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command_text)
        self.assertIn("tools/check-unified-opensearch-e2e-report.py", command_text)
        self.assertNotIn("--require-no-skips", command_text)

    def test_e2e_broad_parity_batch_rejects_required_suite_drift(self):
        batch = self.runner.BATCHES["e2e-broad-parity"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/run-unified-opensearch-e2e.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-broad-current", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command_text)
        self.assertIn("tools/check-unified-opensearch-e2e-report.py", command_text)
        self.assertNotIn("--require-no-skips", command_text)

    def test_rest_api_coverage_current_batch_reports_source_inventory_coverage(self):
        batch = self.runner.BATCHES["rest-api-coverage-current"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/run-unified-opensearch-e2e.py", command_text)
        self.assertIn("target/unified-opensearch-e2e-broad-current", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command_text)
        self.assertIn("tools/report-rest-api-coverage.py", command_text)
        self.assertIn("--require-live-required-suites", command_text)
        self.assertIn("--allow-known-gaps", command_text)
        self.assertIn("--min-live-required-matched-source-route-count", command_text)
        self.assertIn("220", command_text)
        self.assertIn("--min-live-required-matched-source-route-ratio", command_text)
        self.assertIn("0.59", command_text)
        self.assertIn("target/rest-api-coverage-current.json", command_text)

    def test_transport_action_coverage_current_batch_reports_inventory_and_peer_evidence(self):
        batch = self.runner.BATCHES["transport-action-coverage-current"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/report-transport-action-coverage.py", command_text)
        self.assertIn("--require-peer-backpressure", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("604800", command_text)
        self.assertIn("target/transport-action-coverage-current.json", command_text)

    def test_mixed_cluster_coverage_current_batch_reports_join_and_movement_boundary(self):
        batch = self.runner.BATCHES["mixed-cluster-coverage-current"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/report-mixed-cluster-coverage.py", command_text)
        self.assertIn("--require-passed", command_text)
        self.assertIn("--max-report-age-seconds", command_text)
        self.assertIn("5184000", command_text)
        self.assertIn("target/mixed-cluster-coverage-current.json", command_text)

    def test_materialization_priority_current_batch_requires_zero_ranked(self):
        batch = self.runner.BATCHES["materialization-priority-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/check-materialization-priority-report.py", command)
        self.assertIn(
            "target/materialization-priority-targeted-current/materialization-priority.json",
            command,
        )
        self.assertIn("--require-passed", command)
        self.assertIn("--require-zero-ranked", command)

    def test_release_readiness_tooling_batch_runs_writer_and_checker_contract(self):
        batch = self.runner.BATCHES["release-readiness-tooling"]

        self.assertEqual(len(batch), 1)
        command_text = " ".join(batch[0].command)
        self.assertIn("tools/test_replacement_gate_scripts.py", command_text)
        self.assertIn("summary", command_text)
        self.assertIn("passed", command_text)

    def test_current_evidence_gate_collects_non_live_closure_checks(self):
        batch = self.runner.BATCHES["current-evidence-gate"]
        names = {case.name for case in batch}

        self.assertEqual(
            names,
            {
                "non_native_path_inventory_has_no_missing_probe_or_family",
                "search_semantic_and_vector_search_e2e_reports_have_no_failed_missing_or_skipped_cases",
                "search_compat_and_strict_e2e_reports_have_no_failed_or_missing_cases",
                "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites",
                "rest_api_source_inventory_coverage_is_reported_for_broad_required_live_suites",
                "transport_action_inventory_is_reported_with_current_peer_backpressure_evidence",
                "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary",
                "targeted_materialization_priority_report_has_zero_ranked_operations",
                "release_readiness_writer_and_manifest_checker_contract",
            },
        )
        self.assertFalse(any(case.group == "runtime-fairness-peer-backpressure" for case in batch))

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

    def test_runtime_peer_backpressure_current_batch_checks_persisted_report(self):
        batch = self.runner.BATCHES["runtime-peer-backpressure-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/check-runtime-peer-backpressure-report.py", command)
        self.assertIn("target/runtime-peer-backpressure-current.json", command)

    def test_release_evidence_inventory_current_batch_writes_artifact(self):
        batch = self.runner.BATCHES["release-evidence-inventory-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/report-release-evidence-inventory.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-evidence-inventory-current.json", command)

    def test_packaging_evidence_current_batch_writes_release_packaging_report(self):
        batch = self.runner.BATCHES["packaging-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-packaging-evidence.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-packaging/packaging-report.json", command)

    def test_benchmark_evidence_current_batch_writes_release_benchmark_jsonl(self):
        batch = self.runner.BATCHES["benchmark-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-benchmark-evidence.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-benchmarks/deterministic-benchmark-baselines.jsonl", command)
        self.assertIn("--report", command)
        self.assertIn("target/release-benchmarks/benchmark-report.json", command)

    def test_load_evidence_current_batch_writes_release_load_report(self):
        batch = self.runner.BATCHES["load-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-load-evidence.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-load-current/http-load-baseline.json", command)

    def test_load_comparison_evidence_current_batch_writes_release_comparison_report(self):
        batch = self.runner.BATCHES["load-comparison-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-load-comparison-evidence.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-load-comparison/http-load-comparison.json", command)
        self.assertIn("--query-mix", command)
        self.assertIn("write=25,lexical=25,ranking=20,facet=15,sort_filter=10,refresh=5", command)

    def test_rolling_upgrade_evidence_current_batch_writes_release_report(self):
        batch = self.runner.BATCHES["rolling-upgrade-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-rolling-upgrade-evidence.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-rolling-upgrade/rolling-upgrade-report.json", command)

    def test_chaos_evidence_current_batch_writes_release_report(self):
        batch = self.runner.BATCHES["chaos-evidence-current"]

        self.assertEqual(len(batch), 1)
        command = batch[0].command
        self.assertIn("tools/generate-chaos-evidence.py", command)
        self.assertIn("--work-dir", command)
        self.assertIn("target/release-chaos", command)
        self.assertIn("--output", command)
        self.assertIn("target/release-chaos/chaos-report.json", command)

    def test_native_closure_status_current_batch_writes_report_artifact(self):
        batch = self.runner.BATCHES["native-closure-status-current"]

        self.assertEqual(len(batch), 2)
        command = batch[0].command
        self.assertIn("tools/report-native-closure-status.py", command)
        self.assertIn("--output", command)
        self.assertIn("target/native-closure-status-current.json", command)
        check_command = batch[1].command
        self.assertIn("tools/check-native-closure-status-report.py", check_command)
        self.assertIn("target/native-closure-status-current.json", check_command)

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
