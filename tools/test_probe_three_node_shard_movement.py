import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "tools" / "probe_three_node_shard_movement.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location(
        "probe_three_node_shard_movement", PROBE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ShardMovementProbeSummaryTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe_module()

    def representative_report(self):
        zero_drift = {
            "seq_no_drift": 0,
            "local_checkpoint_drift": 0,
            "global_checkpoint_drift": 0,
        }
        return {
            "phases": [
                {
                    "phase": "opensearch_to_steelsearch",
                    "passed": True,
                    "checkpoint_drift": zero_drift,
                },
                {
                    "phase": "steelsearch_to_opensearch",
                    "passed": True,
                    "checkpoint_drift": zero_drift,
                },
            ]
        }

    def test_representative_summary_keeps_existing_pass_criteria(self):
        summary = self.probe.summarize_movement_report(self.representative_report())

        self.assertTrue(summary["passed"])
        self.assertTrue(summary["opensearch_to_steelsearch_passed"])
        self.assertTrue(summary["steelsearch_to_opensearch_passed"])
        self.assertTrue(summary["checkpoint_drift_ok"])
        self.assertTrue(summary["checkpoint_monotonicity_ok"])
        self.assertFalse(summary["interruption_evidence_ok"])
        self.assertFalse(summary["interruption_evidence_required"])

    def test_require_interruption_cli_defaults_to_representative_mode(self):
        args = self.probe.build_arg_parser().parse_args([])

        self.assertFalse(args.require_interruption)

    def test_require_interruption_cli_enables_final_gate_requirement(self):
        args = self.probe.build_arg_parser().parse_args(["--require-interruption"])

        self.assertTrue(args.require_interruption)

    def test_exercise_interruption_cli_is_explicit(self):
        default_args = self.probe.build_arg_parser().parse_args([])
        enabled_args = self.probe.build_arg_parser().parse_args(["--exercise-interruption"])

        self.assertFalse(default_args.exercise_interruption)
        self.assertTrue(enabled_args.exercise_interruption)

    def test_required_interruption_fails_without_interrupted_resume_phases(self):
        summary = self.probe.summarize_movement_report(
            self.representative_report(), require_interruption=True
        )

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["interruption_evidence_ok"])
        self.assertTrue(summary["interruption_evidence_required"])

    def test_required_interruption_still_fails_with_one_direction_only(self):
        report = self.representative_report()
        report["phases"].extend(
            {"phase": phase}
            for phase in [
                "interrupt_java_to_steelsearch_recovery",
                "resume_or_restart_java_to_steelsearch_recovery",
                "finalize_java_to_steelsearch_recovery",
            ]
        )

        summary = self.probe.summarize_movement_report(
            report, require_interruption=True
        )

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["interruption_evidence_ok"])

    def test_required_interruption_passes_with_both_direction_phase_contract(self):
        report = self.representative_report()
        report["phases"].extend(
            {"phase": phase}
            for phase in [
                "interrupt_java_to_steelsearch_recovery",
                "resume_or_restart_java_to_steelsearch_recovery",
                "finalize_java_to_steelsearch_recovery",
                "interrupt_steelsearch_to_opensearch_recovery",
                "resume_or_restart_steelsearch_to_opensearch_recovery",
                "finalize_steelsearch_to_opensearch_recovery",
            ]
        )

        summary = self.probe.summarize_movement_report(
            report, require_interruption=True
        )

        self.assertTrue(summary["passed"])
        self.assertTrue(summary["interruption_evidence_ok"])

    def test_checkpoint_drift_still_fails_summary(self):
        report = self.representative_report()
        report["phases"][0]["checkpoint_drift"]["local_checkpoint_drift"] = 1

        summary = self.probe.summarize_movement_report(report)

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["checkpoint_drift_ok"])

    def test_checkpoint_monotonicity_fails_on_regression(self):
        report = self.representative_report()
        report["phases"][0]["checkpoint_observed"] = [
            {
                "shard": 0,
                "role": "primary",
                "max_seq_no": 5,
                "local_checkpoint": 5,
                "global_checkpoint": 5,
            }
        ]
        report["phases"][1]["checkpoint_observed"] = [
            {
                "shard": 0,
                "role": "primary",
                "max_seq_no": 4,
                "local_checkpoint": 4,
                "global_checkpoint": 4,
            }
        ]

        summary = self.probe.summarize_movement_report(report)

        self.assertFalse(summary["passed"])
        self.assertFalse(summary["checkpoint_monotonicity_ok"])


if __name__ == "__main__":
    unittest.main()
