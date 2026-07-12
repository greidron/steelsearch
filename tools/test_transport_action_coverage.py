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
TRANSPORT_RELEASE_EVIDENCE = (
    ROOT / "tools" / "fixtures" / "transport-release-parity-evidence.json"
)
TRANSPORT_ACTION_SUBSET_LEDGER = ROOT / "tools" / "fixtures" / "transport-action-subset-ledger.json"
TRANSPORT_NEGOTIATION_POLICY = (
    ROOT / "tools" / "fixtures" / "transport-negotiation-exception-policy.json"
)
SOURCE_COMPATIBILITY_MATRIX_DOC = (
    ROOT / "docs" / "rust-port" / "source-compatibility-matrix.md"
)
TRANSPORT_COUNT_DOCS = (
    SOURCE_COMPATIBILITY_MATRIX_DOC,
    ROOT / "docs" / "rust-port" / "opensearch-e2e-gap-inventory.md",
    ROOT / "docs" / "rust-port" / "transport-action-priority.md",
)


def valid_peer_backpressure_report() -> dict:
    return {
        "summary": {
            "passed": True,
            "mode": "both",
            "profile": "mixed-java-rust-query-phase",
            "steelsearch_passed": True,
            "opensearch_passed": True,
        },
        "profile": {
            "required_readbacks": [
                "Rust receiver rejects excess query-phase remote transport work",
                "Rust receiver exposes remote_transport rejected/completed through _cat and _nodes/stats",
                "Java peer exposes analogous search thread-pool rejection through _cat and _nodes/stats",
                "profile report records both surfaces through live transport and REST counter readbacks",
            ],
        },
        "results": {
            "steelsearch": {
                "passed": True,
                "pool": "remote_transport",
                "active_row": {"active": "1"},
                "rejected_row": {"rejected": "1"},
                "completed_row": {"completed": "1"},
                "node_stats": {"rejected": 1, "completed": 1},
            },
            "opensearch": {
                "passed": True,
                "pool": "search",
                "before_row": {"rejected": "0"},
                "after_row": {"rejected": "3"},
                "node_stats": {"rejected": 3},
                "http_429_count": 3,
                "error_samples": [{"status": 429}],
            },
        },
    }


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

    def test_stable_name_digest_sorts_names_before_hashing(self):
        self.assertEqual(
            self.report.stable_name_digest(["b", "a"]),
            self.report.stable_name_digest(["a", "b"]),
        )
        self.assertNotEqual(
            self.report.stable_name_digest(["a", "b"]),
            self.report.stable_name_digest(["a", "c"]),
        )

    def test_accepted_transport_evidence_scope_counts_are_reported(self):
        evidence = json.loads(ACCEPTED_TRANSPORT_EVIDENCE.read_text(encoding="utf-8"))
        release_evidence = json.loads(TRANSPORT_RELEASE_EVIDENCE.read_text(encoding="utf-8"))
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
            self.report.release_evidence_inventory_coverage(inventory, release_evidence),
            {
                "inventory_action_count": 174,
                "matched_action_count": 174,
                "missing_actions": [],
                "extra_actions": [],
                "errors": [],
            },
        )
        self.assertEqual(
            self.report.transport_evidence_action_binding_errors(
                inventory,
                evidence,
                "accepted",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_action_binding_errors(
                inventory,
                release_evidence,
                "release",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_shared_pointer_errors(
                evidence,
                "accepted",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_shared_pointer_errors(
                release_evidence,
                "release",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_response_semantic_errors(
                evidence,
                "accepted",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_response_semantic_errors(
                release_evidence,
                "release",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_request_semantic_errors(
                evidence,
                "accepted",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_request_semantic_errors(
                release_evidence,
                "release",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_pointer_test_errors(
                evidence,
                "accepted",
            ),
            [],
        )
        self.assertEqual(
            self.report.transport_evidence_pointer_test_errors(
                release_evidence,
                "release",
            ),
            [],
        )
        self.assertEqual(
            self.report.release_accepted_evidence_drift_errors(
                evidence,
                release_evidence,
            ),
            [],
        )
        self.assertEqual(
            self.report.accepted_evidence_scope_inventory_errors(inventory, evidence),
            [],
        )
        release_parity = self.report.transport_release_parity_evidence(
            self.report.load_actions(SOURCE_TRANSPORT_ACTIONS),
            inventory,
            release_evidence,
        )
        self.assertTrue(release_parity["complete"])
        self.assertEqual(release_parity["source_implemented_action_count"], 174)
        self.assertEqual(release_parity["release_evidence_action_count"], 174)
        self.assertEqual(release_parity["matched_source_action_count"], 174)
        self.assertEqual(len(release_parity["missing_source_actions"]), 0)
        self.assertEqual(release_parity["blocking_reasons"], [])
        self.assertEqual(self.report.release_evidence_errors(release_evidence), [])
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

    def test_release_transport_evidence_inventory_coverage_reports_drift(self):
        inventory = {
            "actions": [
                {"action_name": "cluster:monitor/main"},
                {"action_name": "indices:data/read/search"},
            ]
        }
        release_evidence = {
            "actions": [
                {"action_name": "cluster:monitor/main"},
                {"action_name": "indices:data/read/get"},
            ]
        }

        coverage = self.report.release_evidence_inventory_coverage(
            inventory,
            release_evidence,
        )

        self.assertEqual(coverage["inventory_action_count"], 2)
        self.assertEqual(coverage["matched_action_count"], 1)
        self.assertEqual(coverage["missing_actions"], ["indices:data/read/search"])
        self.assertEqual(coverage["extra_actions"], ["indices:data/read/get"])
        self.assertEqual(len(coverage["errors"]), 2)

    def test_release_accepted_evidence_drift_reports_pointer_mismatch(self):
        accepted = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "disposition": "implemented",
                    "evidence_kind": "live_probe",
                    "request_evidence": "crates/os-transport/src/action.rs::search_request_wire",
                    "response_evidence": "crates/os-node/src/main.rs::search_route_returns_hits",
                }
            ]
        }
        release = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "disposition": "implemented",
                    "evidence_kind": "live_probe",
                    "request_evidence": "crates/os-transport/src/action.rs::bulk_request_wire",
                    "response_evidence": "crates/os-node/src/main.rs::search_route_returns_hits",
                }
            ]
        }

        errors = self.report.release_accepted_evidence_drift_errors(
            accepted,
            release,
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("request_evidence", errors[0])

    def test_transport_evidence_action_binding_reports_unrelated_pointers(self):
        inventory = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "action_type": "SearchAction",
                    "transport_action": "TransportSearchAction",
                    "request_wire_type": "SearchRequest",
                    "response_wire_type": "SearchResponse",
                }
            ]
        }
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": "crates/os-transport/src/action.rs::bulk_wire_round_trips",
                    "response_evidence": "crates/os-node/src/main.rs::bulk_route_returns_items",
                }
            ]
        }

        errors = self.report.transport_evidence_action_binding_errors(
            inventory,
            evidence,
            "accepted",
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("indices:data/read/search", errors[0])
        self.assertIn("do not mention action metadata", errors[0])

    def test_transport_evidence_action_binding_accepts_action_metadata_token(self):
        inventory = {
            "actions": [
                {
                    "action_name": "indices:data/read/mget",
                    "action_type": "MultiGetAction",
                    "transport_action": "TransportMultiGetAction",
                    "request_wire_type": "MultiGetRequest",
                    "response_wire_type": "MultiGetResponse",
                }
            ]
        }
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/mget",
                    "request_evidence": "crates/os-node/src/main.rs::multi_get_transport_route",
                    "response_evidence": "crates/os-node/src/main.rs::multi_get_transport_route",
                }
            ]
        }

        self.assertEqual(
            self.report.transport_evidence_action_binding_errors(
                inventory,
                evidence,
                "accepted",
            ),
            [],
        )

    def test_transport_evidence_shared_pointer_requires_runtime_semantic_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": "crates/os-node/src/main.rs::search_helper",
                    "response_evidence": "crates/os-node/src/main.rs::search_helper",
                }
            ]
        }

        errors = self.report.transport_evidence_shared_pointer_errors(
            evidence,
            "accepted",
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("without a runtime semantic symbol", errors[0])

    def test_transport_evidence_shared_pointer_accepts_runtime_route_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": "crates/os-node/src/main.rs::search_transport_route",
                    "response_evidence": "crates/os-node/src/main.rs::search_transport_route",
                }
            ]
        }

        self.assertEqual(
            self.report.transport_evidence_shared_pointer_errors(
                evidence,
                "accepted",
            ),
            [],
        )

    def test_transport_evidence_response_semantic_requires_meaningful_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "response_evidence": "crates/os-node/src/main.rs::search_helper",
                }
            ]
        }

        errors = self.report.transport_evidence_response_semantic_errors(
            evidence,
            "accepted",
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("lacks a semantic verb", errors[0])

    def test_transport_evidence_response_semantic_accepts_route_result_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "response_evidence": (
                        "crates/os-node/src/main.rs::"
                        "search_transport_route_returns_local_hits"
                    ),
                }
            ]
        }

        self.assertEqual(
            self.report.transport_evidence_response_semantic_errors(
                evidence,
                "accepted",
            ),
            [],
        )

    def test_transport_evidence_request_semantic_requires_wire_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": "crates/os-node/src/main.rs::search_helper",
                    "response_evidence": (
                        "crates/os-node/src/main.rs::"
                        "search_transport_route_returns_local_hits"
                    ),
                }
            ]
        }

        errors = self.report.transport_evidence_request_semantic_errors(
            evidence,
            "accepted",
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("wire/request semantic token", errors[0])

    def test_transport_evidence_request_semantic_accepts_wire_symbol(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": (
                        "crates/os-transport/src/action.rs::"
                        "search_transport_messages_bind_action_frame"
                    ),
                    "response_evidence": (
                        "crates/os-node/src/main.rs::"
                        "search_transport_route_returns_local_hits"
                    ),
                }
            ]
        }

        self.assertEqual(
            self.report.transport_evidence_request_semantic_errors(
                evidence,
                "accepted",
            ),
            [],
        )

    def test_transport_evidence_request_semantic_accepts_shared_runtime_route(self):
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "request_evidence": (
                        "crates/os-node/src/main.rs::"
                        "query_phase_transport_route_uses_remote_transport_queue_gate"
                    ),
                    "response_evidence": (
                        "crates/os-node/src/main.rs::"
                        "query_phase_transport_route_uses_remote_transport_queue_gate"
                    ),
                }
            ]
        }

        self.assertEqual(
            self.report.transport_evidence_request_semantic_errors(
                evidence,
                "accepted",
            ),
            [],
        )

    def test_transport_evidence_pointer_test_rejects_plain_rust_helper(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source_file = Path(temp_dir_value) / "evidence.rs"
            source_file.write_text("fn search_transport_route() {}\n", encoding="utf-8")
            evidence = {
                "actions": [
                    {
                        "action_name": "indices:data/read/search",
                        "request_evidence": f"{source_file}::search_transport_route",
                        "response_evidence": f"{source_file}::search_transport_route",
                    }
                ]
            }

            errors = self.report.transport_evidence_pointer_test_errors(
                evidence,
                "accepted",
            )

            self.assertEqual(len(errors), 2)
            self.assertIn("is not a Rust test", errors[0])

    def test_transport_evidence_pointer_test_accepts_rust_test(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source_file = Path(temp_dir_value) / "evidence.rs"
            source_file.write_text(
                "#[test]\nfn search_transport_route() {}\n",
                encoding="utf-8",
            )
            evidence = {
                "actions": [
                    {
                        "action_name": "indices:data/read/search",
                        "request_evidence": f"{source_file}::search_transport_route",
                        "response_evidence": f"{source_file}::search_transport_route",
                    }
                ]
            }

            self.assertEqual(
                self.report.transport_evidence_pointer_test_errors(
                    evidence,
                    "accepted",
                ),
                [],
            )

    def test_peer_report_passed_requires_summary_passed(self):
        self.assertTrue(self.report.peer_report_passed(valid_peer_backpressure_report()))
        failed = valid_peer_backpressure_report()
        failed["summary"]["passed"] = False
        self.assertFalse(self.report.peer_report_passed(failed))
        self.assertFalse(self.report.peer_report_passed(None))

    def test_peer_report_passed_requires_counter_readbacks(self):
        payload = valid_peer_backpressure_report()
        payload["results"]["opensearch"]["after_row"]["rejected"] = "0"

        self.assertFalse(self.report.peer_report_passed(payload))
        self.assertIn(
            "peer backpressure opensearch rejected counter did not increase",
            self.report.peer_backpressure_readback_errors(payload),
        )

    def test_peer_report_freshness_rejects_stale_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "peer.json"
            path.write_text(json.dumps({"summary": {"passed": True}}) + "\n", encoding="utf-8")
            stale_mtime = time.time() - 120.0
            os.utime(path, (stale_mtime, stale_mtime))

            freshness = self.report.report_fresh(path, 60.0)

            self.assertFalse(freshness["fresh"])
            self.assertIn("stale", freshness["reason"])

    def test_handshake_matrix_current_document_has_required_reject_classes(self):
        self.assertEqual(
            self.report.handshake_matrix_validation_errors(self.report.HANDSHAKE_MATRIX),
            [],
        )

    def test_handshake_matrix_validation_rejects_missing_fixture_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "matrix.md"
            path.write_text(
                "# Transport Handshake\n\n"
                "supported / observe-only\n"
                "reject by default\n"
                "newer peer wire version outside current validated gates\n"
                "older peer wire version outside current validated gates\n"
                "unknown or malformed reported version\n"
                "fail closed\n",
                encoding="utf-8",
            )

            errors = self.report.handshake_matrix_validation_errors(path)

            self.assertIn(
                "handshake version-skew matrix missing bad handshake fixture rejection: bad handshake frame",
                errors,
            )
            self.assertIn(
                "handshake version-skew matrix missing unexpected action fixture rejection: unexpected action after handshake",
                errors,
            )
            self.assertIn(
                "handshake version-skew matrix missing version mismatch fixture rejection: version mismatch",
                errors,
            )

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
            peer.write_text(json.dumps(valid_peer_backpressure_report()) + "\n", encoding="utf-8")

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
            self.assertEqual(
                payload["summary"]["release_evidence_scope_counts"],
                {"runtime_action_parity": 174},
            )
            self.assertIn(
                "scoped runtime-action evidence",
                payload["summary"]["transport_execution_claim_boundary"],
            )
            self.assertFalse(payload["summary"]["release_parity_evidence_complete"])
            self.assertEqual(payload["summary"]["release_parity_action_count"], 174)
            self.assertEqual(payload["summary"]["release_parity_source_matched_action_count"], 0)
            self.assertEqual(payload["summary"]["release_parity_source_missing_action_count"], 0)
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_matched_action_count"],
                174,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_missing_action_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_extra_action_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["accepted_evidence_action_binding_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_action_binding_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["accepted_evidence_shared_pointer_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_shared_pointer_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["accepted_evidence_response_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_response_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["accepted_evidence_request_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_request_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["accepted_evidence_pointer_test_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_pointer_test_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_accepted_evidence_drift_error_count"],
                0,
            )
            self.assertEqual(len(payload["actions"]), 1)
            self.assertEqual(len(payload["planned_actions"]), 1)
            self.assertEqual(payload["implemented_actions"], [])
            self.assertEqual(payload["partial_actions"], [])

    def test_action_status_errors_reject_non_closed_statuses(self):
        self.assertEqual(self.report.action_status_errors({"implemented": 174}), [])
        self.assertEqual(
            self.report.action_status_errors({"implemented": 173, "planned": 1}),
            ["transport action inventory has non-closed statuses: planned=1"],
        )

    def test_cli_require_closed_action_statuses_rejects_planned_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "planned\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--require-closed-action-statuses",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["planned_action_count"], 1)
            self.assertIn(
                "transport action inventory has non-closed statuses: planned=1",
                payload["errors"],
            )

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
            self.assertEqual(payload["summary"]["transport_action_count"], 174)
            self.assertEqual(payload["summary"]["implemented_action_count"], 174)
            self.assertEqual(
                payload["summary"]["source_implemented_action_name_digest"],
                "5450a12b7cdad6e631ff87a953b7779c4e65e0800d79b672812a65de7336e290",
            )
            self.assertEqual(payload["summary"]["partial_action_count"], 0)
            self.assertEqual(payload["summary"]["planned_action_count"], 0)
            self.assertEqual(payload["summary"]["accepted_evidence_action_count"], 174)
            self.assertEqual(
                payload["summary"]["accepted_evidence_action_name_digest"],
                "9e3236a43431ed6ed6098d7f14c8deada7c6aaf060d914f0d47041ed88fdca17",
            )
            self.assertEqual(payload["summary"]["inventory_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_matched_action_count"], 174)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_missing_action_count"], 0)
            self.assertEqual(payload["summary"]["accepted_evidence_inventory_extra_action_count"], 0)
            self.assertEqual(payload["summary"]["source_implemented_inventory_matched_action_count"], 174)
            self.assertEqual(payload["summary"]["source_implemented_inventory_missing_action_count"], 0)
            self.assertEqual(payload["summary"]["source_implemented_evidence_missing_action_count"], 0)
            self.assertEqual(
                payload["summary"]["accepted_evidence_scope_counts"],
                {
                    "bounded_local_subset": 170,
                    "bounded_seed_peer_fanout_subset": 4,
                },
            )
            self.assertEqual(
                payload["summary"]["release_evidence_scope_counts"],
                {"runtime_action_parity": 174},
            )
            self.assertIn(
                "does not promote generic transport action execution",
                payload["summary"]["transport_execution_claim_boundary"],
            )
            self.assertTrue(payload["summary"]["release_parity_evidence_complete"])
            self.assertEqual(payload["summary"]["release_parity_action_count"], 174)
            self.assertEqual(
                payload["summary"]["release_evidence_action_name_digest"],
                "9e3236a43431ed6ed6098d7f14c8deada7c6aaf060d914f0d47041ed88fdca17",
            )
            self.assertEqual(payload["summary"]["release_parity_source_matched_action_count"], 174)
            self.assertEqual(payload["summary"]["release_parity_source_missing_action_count"], 0)
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_matched_action_count"],
                174,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_missing_action_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_inventory_extra_action_count"],
                0,
            )
            self.assertEqual(
                payload["release_evidence_inventory_coverage"]["matched_action_count"],
                174,
            )
            self.assertEqual(payload["release_evidence_inventory_coverage"]["missing_actions"], [])
            self.assertEqual(payload["release_evidence_inventory_coverage"]["extra_actions"], [])
            self.assertEqual(
                payload["summary"]["accepted_evidence_action_binding_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_action_binding_error_count"],
                0,
            )
            self.assertEqual(payload["accepted_evidence_action_binding_errors"], [])
            self.assertEqual(payload["release_evidence_action_binding_errors"], [])
            self.assertEqual(
                payload["summary"]["accepted_evidence_shared_pointer_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_shared_pointer_error_count"],
                0,
            )
            self.assertEqual(payload["accepted_evidence_shared_pointer_errors"], [])
            self.assertEqual(payload["release_evidence_shared_pointer_errors"], [])
            self.assertEqual(
                payload["summary"]["accepted_evidence_response_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_response_semantic_error_count"],
                0,
            )
            self.assertEqual(payload["accepted_evidence_response_semantic_errors"], [])
            self.assertEqual(payload["release_evidence_response_semantic_errors"], [])
            self.assertEqual(
                payload["summary"]["accepted_evidence_request_semantic_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_request_semantic_error_count"],
                0,
            )
            self.assertEqual(payload["accepted_evidence_request_semantic_errors"], [])
            self.assertEqual(payload["release_evidence_request_semantic_errors"], [])
            self.assertEqual(
                payload["summary"]["accepted_evidence_pointer_test_error_count"],
                0,
            )
            self.assertEqual(
                payload["summary"]["release_evidence_pointer_test_error_count"],
                0,
            )
            self.assertEqual(payload["accepted_evidence_pointer_test_errors"], [])
            self.assertEqual(payload["release_evidence_pointer_test_errors"], [])
            self.assertEqual(
                payload["summary"]["release_accepted_evidence_drift_error_count"],
                0,
            )
            self.assertEqual(payload["release_accepted_evidence_drift_errors"], [])
            self.assertEqual(
                payload["release_parity_evidence"]["source_implemented_action_count"],
                174,
            )
            self.assertEqual(
                payload["release_parity_evidence"]["release_evidence_action_count"],
                174,
            )
            self.assertEqual(
                payload["release_parity_evidence"]["matched_source_action_count"],
                174,
            )
            self.assertEqual(payload["release_parity_evidence"]["blocking_reasons"], [])
            self.assertEqual(len(payload["actions"]), 174)
            self.assertEqual(len(payload["implemented_actions"]), 174)
            self.assertEqual(len(payload["partial_actions"]), 0)
            self.assertEqual(len(payload["accepted_transport_evidence"]), 174)
            self.assertEqual(payload["planned_actions"], [])
            self.assertEqual(
                payload["source_implemented_evidence_coverage"][
                    "source_implemented_action_count"
                ],
                174,
            )
            self.assertEqual(
                payload["source_implemented_evidence_coverage"][
                    "missing_inventory_actions"
                ],
                [],
            )
            self.assertEqual(
                payload["source_implemented_evidence_coverage"][
                    "missing_evidence_actions"
                ],
                [],
            )

    def test_source_compatibility_matrix_transport_counts_are_current(self):
        actions = self.report.load_actions(SOURCE_TRANSPORT_ACTIONS)
        action_count = len(actions)
        source_doc = SOURCE_COMPATIBILITY_MATRIX_DOC.read_text(encoding="utf-8")
        docs = {
            path: path.read_text(encoding="utf-8")
            for path in TRANSPORT_COUNT_DOCS
        }

        self.assertEqual(action_count, 174)
        self.assertIn(
            f"{action_count} generated transport action rows",
            source_doc,
        )
        self.assertIn(
            f"all {action_count} source-derived actions",
            source_doc,
        )
        self.assertIn("generated matrix currently has 768 rows", source_doc)
        for doc in docs.values():
            self.assertNotIn("160 generated transport action rows", doc)
            self.assertNotIn("all 160 source-derived", doc)
            self.assertNotIn("160/160 source-derived", doc)

    def test_transport_release_parity_evidence_passes_with_runtime_action_scope(self):
        source = [
            {"status": "implemented", "action": "SearchAction.INSTANCE"},
            {"status": "implemented", "action": "GetAction.INSTANCE"},
        ]
        inventory = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "action_type": "SearchAction",
                },
                {
                    "action_name": "indices:data/read/get",
                    "action_type": "GetAction",
                },
            ]
        }
        evidence = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "execution_scope": "runtime_action_parity",
                },
                {
                    "action_name": "indices:data/read/get",
                    "execution_scope": "runtime_action_parity",
                },
            ]
        }

        parity = self.report.transport_release_parity_evidence(source, inventory, evidence)

        self.assertTrue(parity["complete"])
        self.assertEqual(parity["release_evidence_action_count"], 2)
        self.assertEqual(parity["matched_source_action_count"], 2)
        self.assertEqual(parity["blocking_reasons"], [])

    def test_cli_requires_release_parity_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            inventory = temp_dir / "inventory.json"
            accepted = temp_dir / "accepted.json"
            release = temp_dir / "release.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            inventory.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "action_type": "SearchAction",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            accepted.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "bounded_local_subset",
                                "evidence_kind": "live_probe",
                                "request_evidence": "tools/report-transport-action-coverage.py::main",
                                "response_evidence": "tools/report-transport-action-coverage.py::main",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            release.write_text(json.dumps({"actions": []}) + "\n", encoding="utf-8")

            result = self.run_cli(
                "--source",
                str(source),
                "--inventory",
                str(inventory),
                "--accepted-evidence",
                str(accepted),
                "--release-evidence",
                str(release),
                "--require-release-parity",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertFalse(payload["summary"]["release_parity_evidence_complete"])
            self.assertIn("release transport parity evidence is incomplete", " ".join(payload["errors"]))

    def test_cli_rejects_release_evidence_outside_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            inventory = temp_dir / "inventory.json"
            accepted = temp_dir / "accepted.json"
            release = temp_dir / "release.json"
            output = temp_dir / "transport.json"
            source.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t1\n",
                encoding="utf-8",
            )
            inventory.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "action_type": "SearchAction",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            accepted.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "bounded_local_subset",
                                "evidence_kind": "live_probe",
                                "request_evidence": "tools/report-transport-action-coverage.py::main",
                                "response_evidence": "tools/report-transport-action-coverage.py::main",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            release.write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_name": "indices:data/read/search",
                                "disposition": "implemented",
                                "execution_scope": "runtime_action_parity",
                                "evidence_kind": "live_probe",
                                "request_evidence": "tools/report-transport-action-coverage.py::main",
                                "response_evidence": "tools/report-transport-action-coverage.py::main",
                            },
                            {
                                "action_name": "indices:data/read/extra",
                                "disposition": "implemented",
                                "execution_scope": "runtime_action_parity",
                                "evidence_kind": "live_probe",
                                "request_evidence": "tools/report-transport-action-coverage.py::main",
                                "response_evidence": "tools/report-transport-action-coverage.py::main",
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--inventory",
                str(inventory),
                "--accepted-evidence",
                str(accepted),
                "--release-evidence",
                str(release),
                "--require-release-parity",
                "--output",
                str(output),
            )

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result, 1)
            self.assertFalse(payload["summary"]["passed"])
            self.assertIn("actions outside inventory", " ".join(payload["errors"]))

    def test_source_implemented_evidence_coverage_reports_missing_inventory_and_evidence(self):
        source = [
            {
                "status": "implemented",
                "action": "SearchAction.INSTANCE",
                "source": "ActionModule.java",
                "line": "1",
            },
            {
                "status": "implemented",
                "action": "GetAction.INSTANCE",
                "source": "ActionModule.java",
                "line": "2",
            },
        ]
        inventory = {
            "actions": [
                {
                    "action_name": "indices:data/read/search",
                    "action_type": "SearchAction",
                }
            ]
        }
        evidence = {"actions": []}

        coverage = self.report.source_implemented_evidence_coverage(
            source,
            inventory,
            evidence,
        )

        self.assertEqual(coverage["source_implemented_action_count"], 2)
        self.assertEqual(coverage["matched_source_action_count"], 1)
        self.assertEqual(
            [action["action"] for action in coverage["missing_inventory_actions"]],
            ["GetAction.INSTANCE"],
        )
        self.assertEqual(
            [action["action"] for action in coverage["missing_evidence_actions"]],
            ["SearchAction.INSTANCE"],
        )
        self.assertEqual(len(coverage["errors"]), 2)

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

    def test_accepted_evidence_requires_symbol_function_definition_not_comment(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source_file = Path(temp_dir_value) / "evidence_source.rs"
            source_file.write_text(
                "// fn request_wire() {}\n"
                "#[test]\n"
                "fn response_returns_items() {}\n",
                encoding="utf-8",
            )
            evidence = {
                "actions": [
                    {
                        "action_name": "indices:data/read/search",
                        "disposition": "implemented",
                        "execution_scope": "bounded_local_subset",
                        "evidence_kind": "live_probe",
                        "request_evidence": f"{source_file}::request_wire",
                        "response_evidence": f"{source_file}::response_returns_items",
                    }
                ]
            }

            errors = self.report.accepted_evidence_errors(evidence)

        self.assertTrue(
            any("request_evidence symbol request_wire not found" in error for error in errors)
        )

    def test_release_evidence_requires_symbol_function_definition_not_string_literal(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source_file = Path(temp_dir_value) / "evidence_source.rs"
            source_file.write_text(
                "const REQUEST: &str = \"request_wire\";\n"
                "#[test]\n"
                "fn response_returns_items() {}\n",
                encoding="utf-8",
            )
            evidence = {
                "actions": [
                    {
                        "action_name": "indices:data/read/search",
                        "disposition": "implemented",
                        "execution_scope": "runtime_action_parity",
                        "evidence_kind": "live_probe",
                        "request_evidence": f"{source_file}::request_wire",
                        "response_evidence": f"{source_file}::response_returns_items",
                    }
                ]
            }

            errors = self.report.release_evidence_errors(evidence)

        self.assertTrue(
            any("request_evidence symbol request_wire not found" in error for error in errors)
        )

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

    def test_phase_a_tier1_transport_admin_actions_are_implemented_in_source_tsv(self):
        implemented_actions = {
            action["action"]
            for action in self.report.load_actions(SOURCE_TRANSPORT_ACTIONS)
            if action["status"] == "implemented"
        }

        tier1_actions = {
            "ClusterHealthAction.INSTANCE",
            "ClusterStateAction.INSTANCE",
            "ClusterUpdateSettingsAction.INSTANCE",
            "ListTasksAction.INSTANCE",
            "CancelTasksAction.INSTANCE",
            "NodesStatsAction.INSTANCE",
            "ClusterStatsAction.INSTANCE",
            "IndicesStatsAction.INSTANCE",
        }

        self.assertEqual(tier1_actions - implemented_actions, set())

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
            peer.write_text(json.dumps(valid_peer_backpressure_report()) + "\n", encoding="utf-8")
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
