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


def load_module():
    spec = importlib.util.spec_from_file_location(
        "multi_node_transport_admin_integration_test", SCRIPT_PATH
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

            def response_stub(_base_url, _case, _timeout, _case_reports):
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


if __name__ == "__main__":
    unittest.main()
