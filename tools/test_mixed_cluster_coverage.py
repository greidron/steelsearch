import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-mixed-cluster-coverage.py"


def load_report_module():
    module_name = "report_mixed_cluster_coverage"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class MixedClusterCoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = load_report_module()

    def test_shard_movement_summary_extracts_directional_checks(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "movement.json"
            path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [
                            {"phase": "replica_on_rust"},
                            {"phase": "steelsearch_to_opensearch"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = self.report.inspect_shard_movement(path)

            self.assertTrue(report["passed"])
            self.assertTrue(report["checkpoint_drift_ok"])
            self.assertEqual(report["phase_count"], 2)

    def test_cli_requires_all_reports_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value) / "phase-c"
            write_phase_c_fixture(root)
            movement = Path(temp_dir_value) / "movement.json"
            movement.write_text(
                json.dumps(
                    {
                        "summary": {
                            "passed": True,
                            "checkpoint_drift_ok": True,
                            "opensearch_to_steelsearch_passed": True,
                            "steelsearch_to_opensearch_passed": True,
                        },
                        "phases": [{"phase": "replica_on_rust"}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output = Path(temp_dir_value) / "coverage.json"

            result = self.run_cli(
                "--phase-c-root",
                str(root),
                "--shard-movement-report",
                str(movement),
                "--require-passed",
                "--output",
                str(output),
            )

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["phase_c_passed_report_count"], 10)

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


def write_phase_c_fixture(root: Path) -> None:
    paths = [
        "phase-c-mixed-cluster-summary.json",
        "join/mixed-cluster-join-report.json",
        "join/live-join-probe-report.json",
        "join/join-reject-report.json",
        "recovery/mixed-cluster-recovery-report.json",
        "recovery/bounded-peer-recovery-probe-report.json",
        "failure/mixed-cluster-failure-report.json",
        "write-replication/mixed-cluster-write-replication-report.json",
        "publication/mixed-cluster-publication-report.json",
        "allocation/mixed-cluster-allocation-report.json",
    ]
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"summary": {"passed": True}}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
