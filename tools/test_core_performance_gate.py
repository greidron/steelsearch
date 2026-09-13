import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_core_performance_gate as gate


class RepeatedGateTests(unittest.TestCase):
    def test_execution_fingerprint_includes_load_collectors_launchers_and_baseline(self):
        fingerprint = gate.execution_fingerprint()
        self.assertEqual(set(fingerprint), set(gate.EXECUTION_FILES))
        self.assertEqual(fingerprint[gate.PUBLISHED_REPORT], gate.PUBLISHED_REPORT_SHA256)
        for name in ("tools/run-http-load-baseline.py", "tools/benchmark_cgroup_evidence.py",
                     "tools/run-opensearch-cluster-dev.sh", "tools/core_performance_budget.py"):
            self.assertIn(name, fingerprint)

    def test_changed_execution_inputs_and_plan_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan = Path(temporary) / "plan.json"
            plan.write_text("{}")
            digest = gate.file_hash(plan)
            fingerprint = gate.execution_fingerprint()
            gate.verify_execution_inputs(fingerprint, plan, digest)
            for name in gate.EXECUTION_FILES:
                changed = dict(fingerprint)
                changed[name] = "0" * 64
                with patch.object(gate, "execution_fingerprint", return_value=changed), \
                        self.subTest(name=name), self.assertRaisesRegex(ValueError, "execution inputs changed"):
                    gate.verify_execution_inputs(fingerprint, plan, digest)
            plan.write_text('{"changed": true}')
            with self.assertRaisesRegex(ValueError, "plan changed"):
                gate.verify_execution_inputs(fingerprint, plan, digest)

    def test_published_report_is_pinned_independently_of_plan(self):
        with patch.object(gate, "load_report", return_value=({}, {"sha256": "0" * 64})), \
                self.assertRaisesRegex(ValueError, "published v0.6.0 report changed"):
            gate.execution_fingerprint()

    def reports(self):
        steel = json.loads((gate.ROOT / "docs/releases/v0.6.0/current.json").read_text())
        reference = json.loads((gate.ROOT / "docs/releases/v0.6.0/opensearch.json").read_text())
        for engine, report in (("steelsearch", steel), ("opensearch", reference)):
            for scenario in report["scenarios"].values():
                nodes = []
                for number in range(scenario["config"]["expected_node_count"]):
                    node = {"pid": number + 1}
                    if engine == "steelsearch":
                        node.update(start_ticks=1, sha256=gate.BASELINE_SHA256)
                    else:
                        node.update(id=f"{number:064x}", image_id=gate.REFERENCE_IMAGE)
                    nodes.append(node)
                snapshot = {"engine": engine, "captured_at_epoch": 100, "nodes": nodes}
                scenario["runtime_evidence"] = {"before": snapshot, "after": copy.deepcopy(snapshot)}
        return [copy.deepcopy(reference if role == "opensearch" else steel) for role in gate.ORDER]

    def test_fixed_order_and_full_workload(self):
        self.assertEqual(gate.ORDER, ("baseline", "candidate", "opensearch", "opensearch", "candidate", "baseline"))
        for role in gate.ORDER:
            command = gate.command(role, Path("out"))
            self.assertIn("--capture-runtime-evidence", command)
            self.assertIn(gate.QUERY_MIX, command)
            self.assertNotIn("--skip-existing", command)
            scenarios = command[command.index("--scenarios") + 1]
            self.assertEqual(len(scenarios.split(",")), 2)

    def test_all_repetitions_pass_without_acceptance_claim(self):
        result = gate.assess(self.reports(), gate.BASELINE_SHA256)
        self.assertTrue(result["numeric_budget_passed"])
        self.assertFalse(result["acceptance_established"])
        self.assertEqual([check["run_indices"] for check in result["checks"]], [[0, 1, 2], [5, 4, 3]])

    def test_second_repetition_cannot_be_hidden_by_first(self):
        reports = self.reports()
        reports[4]["scenarios"]["steelsearch-three-node"]["operations"]["ranking"]["latency_ms"]["p99"] *= 1.06
        result = gate.assess(reports, gate.BASELINE_SHA256)
        self.assertFalse(result["numeric_budget_passed"])
        self.assertTrue(result["checks"][0]["published"]["numeric_budget_passed"])
        self.assertFalse(result["checks"][1]["published"]["numeric_budget_passed"])

    def test_baseline_drift_does_not_reset_published_budget(self):
        reports = self.reports()
        for index in (0, 1, 4, 5):
            reports[index]["scenarios"]["steelsearch-three-node"]["operations"]["ranking"]["latency_ms"]["p99"] *= 1.06
        result = gate.assess(reports, gate.BASELINE_SHA256)
        self.assertFalse(result["numeric_budget_passed"])
        self.assertTrue(result["checks"][0]["paired"]["numeric_budget_passed"])
        self.assertFalse(result["checks"][0]["baseline_drift"]["numeric_budget_passed"])

    def test_partial_and_missing_runtime_rejected(self):
        with self.assertRaisesRegex(ValueError, "six"):
            gate.assess(self.reports()[:-1], gate.BASELINE_SHA256)
        for index in range(6):
            reports = self.reports()
            del next(iter(reports[index]["scenarios"].values()))["runtime_evidence"]
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "runtime evidence"):
                gate.assess(reports, gate.BASELINE_SHA256)

    def test_preparation_does_not_execute_or_allow_directory_reuse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "binary"
            binary.write_bytes(b"fixture")
            output = root / "run"
            args = ["gate", "--baseline-binary", str(binary), "--candidate-binary", str(binary),
                    "--output-dir", str(output), "--prepare-only"]
            with patch.object(gate.sys, "argv", args), patch.object(gate, "file_hash", return_value=gate.BASELINE_SHA256), \
                    patch.object(gate.platform, "platform", return_value="fixture"), \
                    patch.object(gate.subprocess, "run") as run:
                self.assertEqual(gate.main(), 0)
                run.assert_not_called()
                plan = json.loads((output / "plan.json").read_text())
                self.assertEqual(len(plan["jobs"]), 6)
                self.assertFalse((output / "result.json").exists())
                with self.assertRaises(FileExistsError):
                    gate.main()

    def test_execution_preserves_numeric_failure_and_stops_on_infrastructure_error(self):
        for failed_index in (None, 2, "changed_inputs"):
            with self.subTest(failed_index=failed_index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                binary = root / "binary"
                binary.write_bytes(b"fixture")
                output = root / "run"
                reports = self.reports()
                reports[1]["scenarios"]["steelsearch-single-node"]["operations"]["ranking"]["latency_ms"]["p99"] *= 1.06
                executed = []
                verify = gate.verify_execution_inputs

                def verify_inputs(*args):
                    verify(*args)
                    if failed_index == "changed_inputs" and executed:
                        raise ValueError("benchmark execution inputs changed")

                def run(command, **kwargs):
                    self.assertTrue((output / "plan.json").is_file())
                    index = len(executed)
                    executed.append(command)
                    if index == failed_index:
                        return SimpleNamespace(returncode=9)
                    destination = Path(command[command.index("--output-dir") + 1])
                    destination.mkdir()
                    (destination / "summary.json").write_text(json.dumps(reports[index]))
                    return SimpleNamespace(returncode=0)

                args = ["gate", "--baseline-binary", str(binary), "--candidate-binary", str(binary),
                        "--output-dir", str(output)]
                with patch.object(gate.sys, "argv", args), patch.object(gate, "file_hash", return_value=gate.BASELINE_SHA256), \
                        patch.object(gate.platform, "platform", return_value="fixture"), \
                        patch.object(gate, "verify_execution_inputs", side_effect=verify_inputs), \
                        patch.object(gate.subprocess, "run", side_effect=run):
                    self.assertEqual(gate.main(), 1 if failed_index is None else 2)
                self.assertEqual(len(executed), 6 if failed_index is None else (1 if failed_index == "changed_inputs" else 3))
                result = json.loads((output / "result.json").read_text())
                self.assertFalse(result["numeric_budget_passed"])
                self.assertFalse(result["acceptance_established"])
                self.assertEqual(result["execution_inputs_verified"], failed_index is None)
                self.assertEqual(len(result["runs"]), len(executed))


if __name__ == "__main__":
    unittest.main()
