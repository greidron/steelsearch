import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "multi_node_transport_admin_integration.py"
CHECKER_PATH = ROOT / "tools" / "check-multi-node-transport-admin-report.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "multi_node_transport_admin_integration_test", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "check_multi_node_transport_admin_report_test", CHECKER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MultiNodeTransportAdminIntegrationTests(unittest.TestCase):
    def test_summary_counts_cases_not_post_checks(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture = temp_dir / "fixture.json"
            output = temp_dir / "report.json"
            fixture.write_text(
                json.dumps(
                    {
                        "name": "multi-node-transport-admin",
                        "cases": [
                            {
                                "name": "node_a_health",
                                "target": "node_a",
                                "method": "GET",
                                "path": "/_cluster/health",
                                "compare": {
                                    "expected_status": 200,
                                    "body_paths_equal": {"status": "green"},
                                },
                            }
                        ],
                        "post_checks": [
                            {
                                "name": "post_check_status",
                                "left": {"case": "node_a_health", "path": "response.body.status"},
                                "right": {"case": "node_a_health", "path": "response.body.status"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def response_stub(_base_url, case, _timeout, _case_reports):
                if case["path"] == "/_steelsearch/dev/cluster":
                    return {
                        "status": 200,
                        "body": {
                            "coordination": {
                                "publication_transport_transcripts": [
                                    {
                                        "validation_events": [
                                            {
                                                "phase": "proposal",
                                                "node_id": "node-b",
                                                "step": "connect",
                                                "status": "passed",
                                            }
                                        ]
                                    }
                                ]
                            }
                        },
                        "body_text": "{}",
                    }
                return {"status": 200, "body": {"status": "green"}, "body_text": "{}"}

            argv = [
                "multi_node_transport_admin_integration.py",
                "--node-a-url",
                "http://node-a",
                "--node-b-url",
                "http://node-b",
                "--fixture",
                str(fixture),
                "--output",
                str(output),
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                module, "request_response", response_stub
            ), redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 0)

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"], {"passed": 1, "failed": 0})
            self.assertEqual(len(report["cases"]), 1)
            self.assertEqual(len(report["post_checks"]), 1)
            self.assertEqual(
                report["coordination"]["publication_transport_transcripts"][0][
                    "validation_events"
                ][0],
                {
                    "phase": "proposal",
                    "node_id": "node-b",
                    "step": "connect",
                    "status": "passed",
                },
            )

    def test_remote_pit_checker_validates_response_semantics(self):
        checker = load_checker_module()
        report = {
            "cases": [
                {
                    "name": "node_a_open_pit",
                    "status": "passed",
                    "response": {
                        "body": {
                            "pit_id": "pit-1",
                            "_shards": {"failed": 0},
                        }
                    },
                },
                {
                    "name": "node_b_search_node_a_pit",
                    "status": "passed",
                    "response": {
                        "body": {
                            "pit_id": "pit-1",
                            "hits": {
                                "total": {"value": 1},
                                "hits": [
                                    {
                                        "_id": "doc-1",
                                        "_source": {"message": "visible-through-pit"},
                                    }
                                ],
                            },
                        }
                    },
                },
                {
                    "name": "node_b_close_node_a_pit",
                    "status": "passed",
                    "response": {
                        "body": {
                            "pits": [
                                {
                                    "pit_id": "pit-1",
                                    "successful": True,
                                }
                            ]
                        }
                    },
                },
                {
                    "name": "node_b_search_node_a_pit_after_close",
                    "status": "passed",
                    "response": {
                        "body": {
                            "status": 404,
                            "error": {"type": "search_phase_execution_exception"},
                        }
                    },
                },
                {
                    "name": "node_a_list_pits_after_node_b_close",
                    "status": "passed",
                    "response": {"body": {"pits": []}},
                },
            ]
        }

        self.assertEqual(checker.validate_remote_pit_semantics(report), [])

        report["cases"][1]["response"]["body"]["hits"]["hits"][0]["_id"] = "other"
        self.assertEqual(
            checker.validate_remote_pit_semantics(report),
            ["node_b_search_node_a_pit did not return doc-1"],
        )

    def test_remote_pit_checker_summary_reports_case_names(self):
        checker = load_checker_module()
        report = {
            "summary": {"failed": 0},
            "cases": [
                {
                    "name": "node_a_open_pit",
                    "status": "passed",
                    "response": {"body": {"pit_id": "pit-1", "_shards": {"failed": 0}}},
                },
                {
                    "name": "node_b_search_node_a_pit",
                    "status": "passed",
                    "response": {
                        "body": {
                            "pit_id": "pit-1",
                            "hits": {
                                "total": {"value": 1},
                                "hits": [
                                    {
                                        "_id": "doc-1",
                                        "_source": {"message": "visible-through-pit"},
                                    }
                                ],
                            },
                        }
                    },
                },
                {
                    "name": "node_b_close_node_a_pit",
                    "status": "passed",
                    "response": {"body": {"pits": [{"pit_id": "pit-1", "successful": True}]}},
                },
                {
                    "name": "node_b_search_node_a_pit_after_close",
                    "status": "passed",
                    "response": {
                        "body": {
                            "status": 404,
                            "error": {"type": "search_phase_execution_exception"},
                        }
                    },
                },
                {
                    "name": "node_a_list_pits_after_node_b_close",
                    "status": "passed",
                    "response": {"body": {"pits": []}},
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            argv = [
                "check-multi-node-transport-admin-report.py",
                str(path),
                "--require-remote-pit",
            ]
            output = io.StringIO()
            with mock.patch.object(sys, "argv", argv), redirect_stdout(output):
                self.assertEqual(checker.main(), 0)

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["summary"]["remote_pit_case_count"], 5)
        self.assertEqual(
            payload["summary"]["remote_pit_cases"],
            [
                "node_a_list_pits_after_node_b_close",
                "node_a_open_pit",
                "node_b_close_node_a_pit",
                "node_b_search_node_a_pit",
                "node_b_search_node_a_pit_after_close",
            ],
        )

    def test_publication_validation_event_checker_requires_protocol_steps(self):
        checker = load_checker_module()
        report = {
            "coordination": {
                "publication_transport_transcripts": [
                    {
                        "validation_events": [
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "connect",
                                "status": "passed",
                            },
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "action_frame",
                                "status": "passed",
                            },
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "publication_semantics",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "connect",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "action_frame",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "publication_semantics",
                                "status": "passed",
                            },
                        ]
                    }
                ]
            }
        }

        self.assertEqual(checker.validate_publication_validation_events(report), [])

        report["coordination"]["publication_transport_transcripts"][0]["validation_events"].pop()
        self.assertEqual(
            checker.validate_publication_validation_events(report),
            [
                "missing publication validation event kinds: "
                "[('apply', 'publication_semantics', 'passed')]",
                "publication validation event count is too small",
            ],
        )

    def test_publication_validation_event_checker_rejects_missing_failure_reason(self):
        checker = load_checker_module()
        report = {
            "coordination": {
                "publication_transport_transcripts": [
                    {
                        "validation_events": [
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "connect",
                                "status": "passed",
                            },
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "action_frame",
                                "status": "passed",
                            },
                            {
                                "phase": "proposal",
                                "node_id": "node-b",
                                "step": "publication_semantics",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "connect",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "action_frame",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-b",
                                "step": "publication_semantics",
                                "status": "passed",
                            },
                            {
                                "phase": "apply",
                                "node_id": "node-c",
                                "step": "connect",
                                "status": "failed",
                            },
                        ]
                    }
                ]
            }
        }

        self.assertEqual(
            checker.validate_publication_validation_events(report),
            ["publication transcript 0 failed validation event is missing reason"],
        )


if __name__ == "__main__":
    unittest.main()
