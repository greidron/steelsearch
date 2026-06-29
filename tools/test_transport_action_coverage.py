import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-transport-action-coverage.py"
SOURCE_TRANSPORT_ACTIONS = ROOT / "docs" / "rust-port" / "generated" / "source-transport-actions.tsv"
TRANSPORT_INVENTORY = ROOT / "tools" / "fixtures" / "interop-transport-action-inventory.json"


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
            {"status": "partial"},
        ]

        self.assertEqual(
            self.report.status_counts(actions),
            {"implemented": 1, "partial": 1, "planned": 2},
        )
        self.assertEqual(
            self.report.filter_status(actions, "planned"),
            [{"status": "planned"}, {"status": "planned"}],
        )

    def test_action_coverage_claim_reflects_implemented_count(self):
        self.assertIn("no OpenSearch", self.report.action_coverage_claim(0))
        self.assertIn("partial actions", self.report.action_coverage_claim(0, 1))
        self.assertIn("implemented adapters", self.report.action_coverage_claim(1))

    def test_peer_report_passed_requires_summary_passed(self):
        self.assertTrue(self.report.peer_report_passed({"summary": {"passed": True}}))
        self.assertFalse(self.report.peer_report_passed({"summary": {"passed": False}}))
        self.assertFalse(self.report.peer_report_passed(None))

    def test_peer_report_freshness_rejects_stale_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "peer.json"
            path.write_text(json.dumps({"summary": {"passed": True}}) + "\n", encoding="utf-8")
            stale_mtime = time.time() - 120.0
            os.utime(path, (stale_mtime, stale_mtime))

            freshness = self.report.report_fresh(path, 60.0)

            self.assertFalse(freshness["fresh"])
            self.assertIn("stale", freshness["reason"])

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
            self.assertEqual(payload["summary"]["partial_action_count"], 0)
            self.assertEqual(len(payload["actions"]), 1)
            self.assertEqual(len(payload["planned_actions"]), 1)
            self.assertEqual(payload["implemented_actions"], [])
            self.assertEqual(payload["partial_actions"], [])

    def test_cli_reports_current_implemented_and_partial_inventory_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            output = Path(temp_dir_value) / "transport.json"

            result = self.run_cli(
                "--source",
                str(SOURCE_TRANSPORT_ACTIONS),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(payload["summary"]["transport_action_count"], 160)
            self.assertEqual(payload["summary"]["implemented_action_count"], 102)
            self.assertEqual(payload["summary"]["partial_action_count"], 58)
            self.assertEqual(payload["summary"]["planned_action_count"], 0)
            self.assertEqual(len(payload["actions"]), 160)
            self.assertEqual(len(payload["implemented_actions"]), 102)
            self.assertEqual(len(payload["partial_actions"]), 58)
            self.assertEqual(payload["planned_actions"], [])

    def test_locally_handled_transport_actions_are_implemented_in_source_tsv(self):
        implemented_actions = {
            action["action"]
            for action in self.report.load_actions(SOURCE_TRANSPORT_ACTIONS)
            if action["status"] == "implemented"
        }

        expected = {
            "ValidateQueryAction.INSTANCE",
            "FlushAction.INSTANCE",
            "ClearIndicesCacheAction.INSTANCE",
            "ForceMergeAction.INSTANCE",
            "UpgradeAction.INSTANCE",
            "UpgradeStatusAction.INSTANCE",
            "GetIndexAction.INSTANCE",
            "IndicesExistsAction.INSTANCE",
            "ScaleIndexAction.INSTANCE",
            "GetIndexTemplatesAction.INSTANCE",
            "GetComponentTemplateAction.INSTANCE",
            "GetComposableIndexTemplateAction.INSTANCE",
            "PutIndexTemplateAction.INSTANCE",
            "DeleteIndexTemplateAction.INSTANCE",
            "PutComponentTemplateAction.INSTANCE",
            "DeleteComponentTemplateAction.INSTANCE",
            "DeleteComposableIndexTemplateAction.INSTANCE",
            "SimulateIndexTemplateAction.INSTANCE",
            "CreateDataStreamAction.INSTANCE",
            "DeleteDataStreamAction.INSTANCE",
            "ResolveIndexAction.INSTANCE",
            "SearchAction.INSTANCE",
            "StreamSearchAction.INSTANCE",
            "SearchScrollAction.INSTANCE",
            "MultiSearchAction.INSTANCE",
            "ExplainAction.INSTANCE",
            "GetStoredScriptAction.INSTANCE",
            "GetScriptContextAction.INSTANCE",
            "GetScriptLanguageAction.INSTANCE",
        }

        self.assertEqual(expected - implemented_actions, set())

    def test_cli_rejects_stale_peer_backpressure_when_age_gate_is_set(self):
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
            stale_mtime = time.time() - 120.0
            os.utime(peer, (stale_mtime, stale_mtime))

            result = self.run_cli(
                "--source",
                str(source),
                "--peer-backpressure-report",
                str(peer),
                "--require-peer-backpressure",
                "--max-report-age-seconds",
                "60",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertFalse(payload["protocol_evidence"]["peer_backpressure"]["fresh"])

    def test_inventory_actions_are_not_left_planned_in_source_tsv(self):
        source_actions = {
            action["action"].removesuffix(".INSTANCE"): action
            for action in self.report.load_actions(SOURCE_TRANSPORT_ACTIONS)
        }
        inventory = json.loads(TRANSPORT_INVENTORY.read_text(encoding="utf-8"))
        planned = []
        for action in inventory["actions"]:
            source_action = source_actions.get(action["action_type"])
            if source_action is None:
                continue
            if source_action["status"] == "planned":
                planned.append(
                    f"{source_action['action']} line {source_action['line']} "
                    f"covers {action['action_name']} but remains planned"
                )

        self.assertEqual(planned, [])

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
