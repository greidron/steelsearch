import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "probe_stateful_route_ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("probe_stateful_route_ledger_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["probe_stateful_route_ledger_test"] = module
    spec.loader.exec_module(module)
    return module


class StatefulRouteProbeTests(unittest.TestCase):
    def test_json_pointer_get_falls_back_to_opensearch_pit_id_field(self):
        probe = load_module()

        self.assertEqual(probe.json_pointer_get({"id": "pit-from-opensearch"}, "/pit_id"), "pit-from-opensearch")

    def test_opensearch_comparison_is_recorded_per_case(self):
        probe = load_module()
        fixture = {
            "setup": [],
            "cases": [
                {
                    "name": "compared",
                    "family": "search",
                    "method": "GET",
                    "path": "/_rank_eval",
                    "expected_runtime_status": "stateful-route-present",
                    "opensearch_comparison": True,
                },
                {
                    "name": "steel-only",
                    "family": "search",
                    "method": "GET",
                    "path": "/_search",
                    "expected_runtime_status": "stateful-route-present",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "fixture.json"
            report_path = Path(tmp) / "report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

            original_argv = sys.argv
            original_request = probe.request
            try:
                sys.argv = [
                    "probe",
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--opensearch-url",
                    "http://opensearch",
                    "--fixture",
                    str(fixture_path),
                    "--report",
                    str(report_path),
                ]
                probe.request = lambda _base, _case, _timeout=3.0: {"status": 400, "body": "{}"}

                self.assertEqual(probe.main(), 0)
            finally:
                sys.argv = original_argv
                probe.request = original_request

            report = json.loads(report_path.read_text(encoding="utf-8"))
            cases = {case["name"]: case for case in report["cases"]}

        self.assertIn("opensearch", report["targets"])
        self.assertIn("opensearch", cases["compared"]["targets"])
        self.assertNotIn("opensearch", cases["steel-only"]["targets"])


if __name__ == "__main__":
    unittest.main()
