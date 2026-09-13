import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from core_performance_reports import BASELINE_SHA256, REFERENCE_IMAGE, evaluate_reports, load_report


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/releases/v0.6.0"
SCRIPT = ROOT / "tools/core_performance_reports.py"


class CorePerformanceReportsTests(unittest.TestCase):
    def setUp(self):
        self.baseline = json.loads((BUNDLE / "current.json").read_text())
        self.candidate = copy.deepcopy(self.baseline)
        self.reference = json.loads((BUNDLE / "opensearch.json").read_text())
        self.sha = "a" * 64
        for scenario in self.candidate["scenarios"].values():
            scenario["executable"]["sha256"] = self.sha

    def evaluate(self):
        return evaluate_reports(self.baseline, self.candidate, self.reference, self.sha)

    def scenario(self):
        return self.candidate["scenarios"]["steelsearch-single-node"]

    def test_real_artifacts_pass_integrity_but_not_implementation_acceptance(self):
        result = self.evaluate()
        self.assertTrue(result["report_integrity_passed"])
        self.assertTrue(result["numeric_budget_passed"])
        self.assertFalse(result["acceptance_established"])
        self.assertEqual(len(result["metrics"]), 44)
        self.assertEqual(len(result["opensearch_metrics"]), 44)

    def test_original_baseline_cannot_be_replaced_by_last_candidate(self):
        self.baseline = copy.deepcopy(self.candidate)
        with self.assertRaisesRegex(ValueError, "identity"):
            self.evaluate()

    def test_timeline_is_rejected_even_without_outer_diagnostic_marker(self):
        for owner in (self.candidate, self.scenario()):
            for field in ("config", "payload"):
                if field == "config":
                    owner["config"]["diagnostic_timeline"] = True
                else:
                    owner["timeline"] = {}
                with self.assertRaisesRegex(ValueError, "diagnostic timeline"):
                    self.evaluate()
                owner["config"].pop("diagnostic_timeline", None)
                owner.pop("timeline", None)

    def test_candidate_identity_is_checked_on_both_topologies(self):
        for scenario in self.candidate["scenarios"].values():
            scenario["executable"]["sha256"] = "b" * 64
            with self.assertRaisesRegex(ValueError, "identity"):
                self.evaluate()
            scenario["executable"]["sha256"] = self.sha

    def test_missing_and_explicit_false_timeline_are_equivalent_without_mutating_reports(self):
        for report in (self.candidate, self.reference):
            report["config"]["diagnostic_timeline"] = False
            for scenario in report["scenarios"].values():
                scenario["config"]["diagnostic_timeline"] = False
        before = copy.deepcopy((self.baseline, self.candidate, self.reference))
        self.assertTrue(self.evaluate()["report_integrity_passed"])
        self.assertEqual((self.baseline, self.candidate, self.reference), before)

    def test_timeline_config_requires_literal_false_or_absence(self):
        for owner in (self.candidate, self.scenario()):
            for invalid in (True, None, 0, "", [], {}):
                with self.subTest(value=invalid):
                    owner["config"]["diagnostic_timeline"] = invalid
                    with self.assertRaisesRegex(ValueError, "diagnostic timeline"):
                        self.evaluate()
            del owner["config"]["diagnostic_timeline"]

    def test_unknown_executed_config_is_not_discarded_with_timeline_default(self):
        self.scenario()["config"]["unknown_option"] = False
        with self.assertRaisesRegex(ValueError, "executed configurations differ"):
            self.evaluate()

    def test_same_binary_is_allowed_without_claiming_improvement(self):
        result = evaluate_reports(self.baseline, self.baseline, self.reference, BASELINE_SHA256)
        self.assertTrue(result["numeric_budget_passed"])
        self.assertTrue(all(float(row["regression_percent"]) == 0 for row in result["metrics"]))
        self.assertFalse(result["acceptance_established"])

    def test_missing_and_extra_topology_fail(self):
        saved = self.candidate["scenarios"].pop("steelsearch-three-node")
        with self.assertRaisesRegex(ValueError, "topologies"):
            self.evaluate()
        self.candidate["scenarios"]["steelsearch-three-node"] = saved
        self.candidate["scenarios"]["steelsearch-five-node"] = saved
        with self.assertRaisesRegex(ValueError, "topologies"):
            self.evaluate()

    def test_executed_configuration_cannot_be_relabelled(self):
        for key, value in (("corpus_size", 1), ("clients", True), ("expected_node_count", 3),
                           ("number_of_replicas", 1), ("seed", 99), ("reset", False),
                           ("vector_dimension", 8), ("vector_source", "other")):
            with self.subTest(key=key):
                old = self.scenario()["config"][key]
                self.scenario()["config"][key] = value
                with self.assertRaises(ValueError):
                    self.evaluate()
                self.scenario()["config"][key] = old

    def test_root_timeout_drift_fails(self):
        self.candidate["config"]["timeout_seconds"] = 20
        with self.assertRaisesRegex(ValueError, "configurations"):
            self.evaluate()

    def test_diagnostic_report_and_scenario_fail(self):
        for target in (self.candidate, self.scenario()):
            target["diagnostic_only"] = True
            with self.assertRaisesRegex(ValueError, "diagnostic"):
                self.evaluate()
            del target["diagnostic_only"]

    def test_plugin_workload_fails(self):
        self.candidate["config"]["query_mix"] += ",vector=1"
        with self.assertRaisesRegex(ValueError, "no plugins"):
            self.evaluate()

    def test_failed_load_runner_rejected_even_with_valid_metrics(self):
        for report in (self.baseline, self.candidate, self.reference):
            for scenario in report["scenarios"].values():
                for value in (1, -9, False, "0", None):
                    with self.subTest(value=value):
                        scenario["load_runner_returncode"] = value
                        with self.assertRaisesRegex(ValueError, "load runner"):
                            self.evaluate()
                scenario["load_runner_returncode"] = 0
                self.evaluate()
                scenario["load_runner_error_output"] = "runner failed after writing results"
                with self.assertRaisesRegex(ValueError, "load runner"):
                    self.evaluate()
                del scenario["load_runner_error_output"]
                del scenario["load_runner_returncode"]

    def add_runtime(self):
        for engine, report, sha in (("steelsearch", self.candidate, self.sha),
                                    ("opensearch", self.reference, None)):
            for scenario in report["scenarios"].values():
                nodes = []
                for number in range(scenario["config"]["expected_node_count"]):
                    node = {"pid": number + 1}
                    if engine == "steelsearch":
                        node.update(start_ticks=10, sha256=sha)
                    else:
                        node.update(id=f"{number:064x}", image_id=REFERENCE_IMAGE)
                    nodes.append(node)
                snapshot = {"engine": engine, "captured_at_epoch": 100, "nodes": nodes}
                scenario["runtime_evidence"] = {"before": snapshot, "after": copy.deepcopy(snapshot)}
                scenario["runtime_evidence"]["after"]["captured_at_epoch"] = 200

    def test_runtime_evidence_checked_without_claiming_acceptance(self):
        self.add_runtime()
        self.assertFalse(self.evaluate()["acceptance_established"])
        self.scenario()["runtime_evidence"] = None
        with self.assertRaisesRegex(ValueError, "runtime"):
            self.evaluate()

    def test_runtime_identity_and_settings_mutations_fail(self):
        for field, value in (("pid", False), ("start_ticks", 0), ("sha256", "b" * 64)):
            self.add_runtime()
            for phase in ("before", "after"):
                self.scenario()["runtime_evidence"][phase]["nodes"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.evaluate()
        self.add_runtime()
        self.scenario()["runtime_evidence"]["after"]["nodes"][0]["environment"] = {"MODE": "changed"}
        with self.assertRaisesRegex(ValueError, "settings changed"):
            self.evaluate()

    def test_runtime_topology_and_reference_image_fail_closed(self):
        for engine, report in (("steelsearch", self.candidate), ("opensearch", self.reference)):
            for mutation in ("missing", "duplicate_pid", "identity"):
                self.add_runtime()
                evidence = report["scenarios"][f"{engine}-three-node"]["runtime_evidence"]
                for snapshot in evidence.values():
                    if mutation == "missing":
                        snapshot["nodes"].pop()
                    elif mutation == "duplicate_pid":
                        snapshot["nodes"][1]["pid"] = snapshot["nodes"][0]["pid"]
                    elif engine == "opensearch":
                        snapshot["nodes"][0]["image_id"] = "sha256:" + "0" * 64
                    else:
                        snapshot["engine"] = "opensearch"
                with self.subTest(engine=engine, mutation=mutation), self.assertRaises(ValueError):
                    self.evaluate()

    def test_runtime_timestamp_order_checked(self):
        self.add_runtime()
        self.scenario()["runtime_evidence"]["after"]["captured_at_epoch"] = 99
        with self.assertRaisesRegex(ValueError, "timestamps reversed"):
            self.evaluate()

    def test_missing_and_extra_operation_fail(self):
        operations = self.scenario()["operations"]
        old = operations.pop("write")
        with self.assertRaisesRegex(ValueError, "operation results"):
            self.evaluate()
        operations["write"] = old
        operations["vector"] = old
        with self.assertRaisesRegex(ValueError, "operation results"):
            self.evaluate()

    def test_zero_error_values_are_strictly_numeric(self):
        for value in (1, False, None, "0"):
            self.scenario()["summary"]["error_count"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.evaluate()

    def test_total_and_latency_counts_are_checked(self):
        summary = self.scenario()["summary"]
        summary["operation_count"] += 1
        with self.assertRaisesRegex(ValueError, "counts differ"):
            self.evaluate()
        summary["operation_count"] -= 1
        latency = self.scenario()["operations"]["write"]["latency_ms"]
        latency["count"] += 1
        with self.assertRaisesRegex(ValueError, "latency counts"):
            self.evaluate()

    def test_operation_sum_checked_even_if_local_counts_match(self):
        result = self.scenario()["operations"]["write"]
        result["success_count"] += 1
        result["latency_ms"]["count"] += 1
        with self.assertRaisesRegex(ValueError, "sum"):
            self.evaluate()

    def test_throughput_and_duration_checked(self):
        summary = self.scenario()["summary"]
        summary["throughput_ops_per_second"] *= 2
        with self.assertRaisesRegex(ValueError, "throughput"):
            self.evaluate()
        summary["elapsed_seconds"] = 1
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.evaluate()

    def test_p99_required_and_percentiles_ordered(self):
        latency = self.scenario()["operations"]["write"]["latency_ms"]
        old = latency.pop("p99")
        with self.assertRaises(KeyError):
            self.evaluate()
        latency["p99"] = latency["p95"] / 2
        with self.assertRaisesRegex(ValueError, "percentile"):
            self.evaluate()
        latency["p99"] = old

    def test_reference_is_validated_too(self):
        self.reference["scenarios"]["opensearch-three-node"]["target_identity"]["version"]["number"] = "3.7.0"
        with self.assertRaisesRegex(ValueError, "version"):
            self.evaluate()

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text('{"config": {}, "config": {}}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_report(path)

    def test_cli_exit_codes_and_invalid_report_overwrite_stale_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.json"
            output = root / "result.json"
            command = [sys.executable, str(SCRIPT), "--baseline", str(BUNDLE / "current.json"),
                       "--candidate", str(candidate), "--opensearch", str(BUNDLE / "opensearch.json"),
                       "--candidate-sha256", self.sha, "--output", str(output)]
            candidate.write_text(json.dumps(self.candidate))
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            latency = self.scenario()["operations"]["write"]["latency_ms"]
            latency["p99"] *= 2
            candidate.write_text(json.dumps(self.candidate))
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
            self.assertFalse(json.loads(output.read_text())["numeric_budget_passed"])
            candidate.write_text('{"config":null}')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertFalse(json.loads(output.read_text())["report_integrity_passed"])
            self.assertFalse(json.loads(output.read_text())["acceptance_established"])
            command[-1] = str(candidate)
            saved = candidate.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(candidate.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
