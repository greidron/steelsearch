import importlib.util
import contextlib
import io
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
ACCEPTED_TRANSPORT_EVIDENCE = (
    ROOT / "tools" / "fixtures" / "interop-accepted-transport-action-evidence.json"
)
TRANSPORT_ACTION_SUBSET_LEDGER = ROOT / "tools" / "fixtures" / "transport-action-subset-ledger.json"
TRANSPORT_NEGOTIATION_POLICY = (
    ROOT / "tools" / "fixtures" / "transport-negotiation-exception-policy.json"
)


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

    def test_accepted_transport_evidence_scope_counts_are_reported(self):
        evidence = json.loads(ACCEPTED_TRANSPORT_EVIDENCE.read_text(encoding="utf-8"))
        inventory = json.loads(TRANSPORT_INVENTORY.read_text(encoding="utf-8"))

        self.assertEqual(self.report.accepted_evidence_action_count(evidence), 174)
        self.assertEqual(
            self.report.accepted_evidence_scope_counts(evidence),
            {
                "bounded_local_subset": 170,
                "bounded_seed_peer_fanout_subset": 4,
            },
        )
        self.assertEqual(self.report.accepted_evidence_errors(evidence), [])
        self.assertEqual(
            self.report.accepted_evidence_inventory_coverage(inventory, evidence),
            {
                "inventory_action_count": 174,
                "matched_action_count": 174,
                "missing_actions": [],
                "extra_actions": [],
                "errors": [],
            },
        )
        self.assertEqual(
            self.report.accepted_evidence_scope_inventory_errors(inventory, evidence),
            [],
        )
        profile = (ROOT / "tools" / "run_mixed_cluster_failure_profile.sh").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            self.report.accepted_evidence_profile_errors(evidence, profile),
            [],
        )

    def test_accepted_transport_evidence_inventory_coverage_reports_drift(self):
        inventory = {
            "actions": [
                {"action_name": "cluster:monitor/main"},
                {"action_name": "indices:data/read/search"},
            ]
        }
        evidence = {
            "actions": [
                {"action_name": "cluster:monitor/main"},
                {"action_name": "indices:data/read/get"},
            ]
        }

        coverage = self.report.accepted_evidence_inventory_coverage(inventory, evidence)

        self.assertEqual(coverage["inventory_action_count"], 2)
        self.assertEqual(coverage["matched_action_count"], 1)
        self.assertEqual(coverage["missing_actions"], ["indices:data/read/search"])
        self.assertEqual(coverage["extra_actions"], ["indices:data/read/get"])
        self.assertEqual(len(coverage["errors"]), 2)

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
            self.assertEqual(payload["summary"]["accepted_evidence_action_count"], 174)
            self.assertEqual(payload["summary"]["inventory_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_matched_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_missing_action_count"], 0)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_extra_action_count"], 0)
            self.assertEqual(
                payload["summary"]["accepted_evidence_scope_counts"].get(
                    "bounded_execution_boundary", 0
                ),
                0,
            )
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
            self.assertEqual(payload["summary"]["implemented_action_count"], 160)
            self.assertEqual(payload["summary"]["partial_action_count"], 0)
            self.assertEqual(payload["summary"]["planned_action_count"], 0)
            self.assertEqual(payload["summary"]["accepted_evidence_action_count"], 174)
            self.assertEqual(payload["summary"]["inventory_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_matched_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_missing_action_count"], 0)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_extra_action_count"], 0)
            self.assertEqual(
                payload["summary"]["accepted_evidence_scope_counts"],
                {
                    "bounded_local_subset": 170,
                    "bounded_seed_peer_fanout_subset": 4,
                },
            )
            self.assertEqual(len(payload["actions"]), 160)
            self.assertEqual(len(payload["implemented_actions"]), 160)
            self.assertEqual(len(payload["partial_actions"]), 0)
            self.assertEqual(len(payload["accepted_transport_evidence"]), 174)
            self.assertEqual(payload["planned_actions"], [])

    def test_cli_rejects_invalid_accepted_evidence_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            evidence = temp_dir / "evidence.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "full_parity",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--accepted-evidence",
                str(evidence),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("full_parity", " ".join(payload["errors"]))

    def test_cli_rejects_accepted_evidence_without_request_response_pointers(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            evidence = temp_dir / "evidence.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "bounded_local_subset",
                                "evidence_kind": "live_probe",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--accepted-evidence",
                str(evidence),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("missing request_evidence", " ".join(payload["errors"]))
            self.assertIn("missing response_evidence", " ".join(payload["errors"]))

    def test_cli_rejects_seed_peer_fanout_scope_without_fanout_response_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            evidence = temp_dir / "evidence.json"
            output = temp_dir / "transport.json"
            source_file = temp_dir / "evidence_source.rs"
            source_file.write_text(
                "fn request_wire() {}\nfn local_response() {}\n",
                encoding="utf-8",
            )
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search[update_context]",
                                "disposition": "implemented",
                                "execution_scope": "bounded_seed_peer_fanout_subset",
                                "evidence_kind": "live_probe",
                                "request_evidence": f"{source_file}::request_wire",
                                "response_evidence": f"{source_file}::local_response",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--accepted-evidence",
                str(evidence),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("fanout response test", " ".join(payload["errors"]))

    def test_seed_peer_fanout_scope_requires_inventory_fanout_reason(self):
        inventory = {
            "actions": [
                {
                    "action_name": "indices:data/read/search[update_context]",
                    "reason": "handled locally",
                }
            ]
        }
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search[update_context]",
                    "execution_scope": "bounded_seed_peer_fanout_subset",
                }
            ]
        }

        errors = self.report.accepted_evidence_scope_inventory_errors(inventory, evidence)

        self.assertEqual(len(errors), 1)
        self.assertIn("inventory reason", errors[0])

    def test_seed_peer_fanout_scope_requires_mixed_cluster_profile_entry(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search[update_context]",
                    "execution_scope": "bounded_seed_peer_fanout_subset",
                    "response_evidence": (
                        "crates/os-node/tests/dev_cluster_daemons.rs::"
                        "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                    ),
                }
            ]
        }

        errors = self.report.accepted_evidence_profile_errors(
            evidence,
            "# multi_daemon_get_all_pits_fans_out_to_seed_peers\ncargo test other_case",
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("run exactly in mixed-cluster failure profile", errors[0])

    def test_seed_peer_fanout_scope_accepts_exact_mixed_cluster_profile_entry(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search[update_context]",
                    "execution_scope": "bounded_seed_peer_fanout_subset",
                    "response_evidence": (
                        "crates/os-node/tests/dev_cluster_daemons.rs::"
                        "multi_daemon_get_all_pits_fans_out_to_seed_peers"
                    ),
                }
            ]
        }
        profile = (
            "if cargo test -p os-node --features standalone-runtime "
            "multi_daemon_get_all_pits_fans_out_to_seed_peers "
            "--test dev_cluster_daemons -- --exact --nocapture; then\n"
        )

        errors = self.report.accepted_evidence_profile_errors(evidence, profile)

        self.assertEqual(errors, [])

    def test_cli_rejects_accepted_evidence_pointing_to_missing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            evidence = temp_dir / "evidence.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "bounded_local_subset",
                                "evidence_kind": "live_probe",
                                "request_evidence": "crates/missing/src/action.rs::missing",
                                "response_evidence": "crates/os-node/src/main.rs::search_route",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--accepted-evidence",
                str(evidence),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("request_evidence points to missing file", " ".join(payload["errors"]))

    def test_cli_rejects_accepted_evidence_pointing_to_missing_symbols(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            evidence = temp_dir / "evidence.json"
            output = temp_dir / "transport.json"
            source_file = temp_dir / "evidence_source.rs"
            source_file.write_text(
                "fn present_symbol() {}\n",
                encoding="utf-8",
            )
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            evidence.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "bounded_local_subset",
                                "evidence_kind": "live_probe",
                                "request_evidence": f"{source_file}::missing_symbol",
                                "response_evidence": f"{source_file}::present_symbol",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--accepted-evidence",
                str(evidence),
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("request_evidence symbol missing_symbol not found", " ".join(payload["errors"]))

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
            "UpgradeSettingsAction.INSTANCE",
            "PutRepositoryAction.INSTANCE",
            "DeleteRepositoryAction.INSTANCE",
            "VerifyRepositoryAction.INSTANCE",
            "CleanupRepositoryAction.INSTANCE",
            "GetSnapshotsAction.INSTANCE",
            "DeleteSnapshotAction.INSTANCE",
            "CreateSnapshotAction.INSTANCE",
            "CloneSnapshotAction.INSTANCE",
            "SnapshotsStatusAction.INSTANCE",
            "RestoreRemoteStoreAction.INSTANCE",
            "ClusterRerouteAction.INSTANCE",
            "GetIndexAction.INSTANCE",
            "IndicesExistsAction.INSTANCE",
            "ScaleIndexAction.INSTANCE",
            "ResizeAction.INSTANCE",
            "RolloverAction.INSTANCE",
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
            "CreateViewAction.INSTANCE",
            "DeleteViewAction.INSTANCE",
            "GetViewAction.INSTANCE",
            "UpdateViewAction.INSTANCE",
            "ListViewNamesAction.INSTANCE",
            "SearchViewAction.INSTANCE",
            "KNNStatsAction.INSTANCE",
            "KNNWarmupAction.INSTANCE",
            "UpdateModelMetadataAction.INSTANCE",
            "TrainingJobRouteDecisionInfoAction.INSTANCE",
            "TrainingJobRouterAction.INSTANCE",
            "TrainingModelAction.INSTANCE",
            "GetModelAction.INSTANCE",
            "DeleteModelAction.INSTANCE",
            "SearchModelAction.INSTANCE",
            "ClearCacheAction.INSTANCE",
            "RemoveModelFromCacheAction.INSTANCE",
            "UpdateModelGraveyardAction.INSTANCE",
            "StartPersistentTaskAction.INSTANCE",
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

    def test_transport_subset_and_negotiation_policy_action_dispositions_match(self):
        subset = json.loads(TRANSPORT_ACTION_SUBSET_LEDGER.read_text(encoding="utf-8"))
        policy = json.loads(TRANSPORT_NEGOTIATION_POLICY.read_text(encoding="utf-8"))

        subset_dispositions = {
            case["action"]: case["disposition"] for case in subset.get("cases", [])
        }
        policy_dispositions = {
            case["kind"]: case["disposition"]
            for case in policy.get("cases", [])
            if case.get("category") == "action_classification"
            and case.get("kind") != "unknown_transport_action"
        }

        self.assertEqual(policy_dispositions, subset_dispositions)

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            with contextlib.redirect_stdout(io.StringIO()):
                return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
