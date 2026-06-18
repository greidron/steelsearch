import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-transport-action-coverage.py"


def load_report_module():
    module_name = "report_transport_action_coverage"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TransportActionCoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = load_report_module()

    def test_status_counts_transport_actions(self):
        actions = [
            {"status": "planned"},
            {"status": "planned"},
            {"status": "implemented"},
        ]

        self.assertEqual(
            self.report.status_counts(actions),
            {"implemented": 1, "planned": 2},
        )

    def test_peer_report_passed_requires_summary_passed(self):
        self.assertTrue(self.report.peer_report_passed({"summary": {"passed": True}}))
        self.assertFalse(self.report.peer_report_passed({"summary": {"passed": False}}))
        self.assertFalse(self.report.peer_report_passed(None))

    def test_cli_requires_peer_backpressure_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            peer = temp_dir / "peer.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "planned\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            peer.write_text(json.dumps({"summary": {"passed": True}}) + "\n", encoding="utf-8")

            result = self.run_cli(
                "--source",
                str(source),
                "--peer-backpressure-report",
                str(peer),
                "--require-peer-backpressure",
                "--output",
                str(output),
            )

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["transport_action_count"], 1)
            self.assertEqual(payload["summary"]["planned_action_count"], 1)
            self.assertEqual(payload["summary"]["implemented_action_count"], 0)

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
