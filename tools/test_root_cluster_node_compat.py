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
RUNNER_PATH = ROOT / "tools" / "root_cluster_node_compat.py"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RootClusterNodeCompatTests(unittest.TestCase):
    def test_steelsearch_only_case_selection_requires_http_status_without_opensearch(self):
        runner = load_module(RUNNER_PATH, "root_cluster_node_compat_case_selection")
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture.json"
            output = Path(tmp) / "report.json"
            fixture.write_text(
                json.dumps(
                    {
                        "name": "synthetic-root-cat",
                        "cases": [
                            {"name": "selected", "method": "GET", "path": "/_cat"},
                            {"name": "not-selected", "method": "GET", "path": "/_nodes"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_request(base_url, case, timeout):
                self.assertEqual(base_url, "http://steelsearch")
                self.assertEqual(case["name"], "selected")
                return {"status": 200, "body": {}, "body_text": "{}"}

            old_argv = sys.argv
            try:
                sys.argv = [
                    str(RUNNER_PATH),
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--fixture",
                    str(fixture),
                    "--output",
                    str(output),
                    "--case",
                    "selected",
                ]
                with mock.patch.object(runner, "request_response", side_effect=fake_request):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(runner.main(), 0)
            finally:
                sys.argv = old_argv

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["targets"], {"steelsearch": "http://steelsearch"})
            self.assertEqual(report["summary"], {"passed": 1, "failed": 0})
            self.assertEqual([case["name"] for case in report["cases"]], ["selected"])

    def test_missing_http_status_fails_steelsearch_only_case(self):
        runner = load_module(RUNNER_PATH, "root_cluster_node_compat_missing_status")

        self.assertEqual(
            runner.require_http_response("steelsearch", {"status": None, "error": "refused"}),
            ["steelsearch did not return an HTTP status: refused"],
        )

    def test_comparison_mode_cleans_point_in_time_contexts_before_and_after_cases(self):
        runner = load_module(RUNNER_PATH, "root_cluster_node_compat_pit_cleanup")
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture.json"
            output = Path(tmp) / "report.json"
            fixture.write_text(
                json.dumps(
                    {
                        "name": "synthetic-root-cat",
                        "cases": [
                            {"name": "cat", "method": "GET", "path": "/_cat/pit_segments"},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            calls = []

            def fake_request(base_url, case, timeout):
                calls.append((base_url, case["name"], case["method"], case["path"]))
                if case["name"] == "cleanup_point_in_time_all":
                    return {"status": 200, "body": {"succeeded": True}, "body_text": "{}"}
                return {"status": 200, "body": {}, "body_text": "{}"}

            old_argv = sys.argv
            try:
                sys.argv = [
                    str(RUNNER_PATH),
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--opensearch-url",
                    "http://opensearch",
                    "--fixture",
                    str(fixture),
                    "--output",
                    str(output),
                ]
                with mock.patch.object(runner, "request_response", side_effect=fake_request):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(runner.main(), 0)
            finally:
                sys.argv = old_argv

            cleanup_call = (
                "http://steelsearch",
                "cleanup_point_in_time_all",
                "DELETE",
                "/_search/point_in_time/_all",
            )
            self.assertEqual(calls[0], cleanup_call)
            self.assertEqual(
                calls[1],
                (
                    "http://opensearch",
                    "cleanup_point_in_time_all",
                    "DELETE",
                    "/_search/point_in_time/_all",
                ),
            )
            self.assertEqual(calls[-2], cleanup_call)
            self.assertEqual(
                calls[-1],
                (
                    "http://opensearch",
                    "cleanup_point_in_time_all",
                    "DELETE",
                    "/_search/point_in_time/_all",
                ),
            )

            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"], {"passed": 1, "failed": 0})
            self.assertEqual(report["precleanup"]["name"], "cleanup_point_in_time_all")
            self.assertEqual(report["cleanup"]["name"], "cleanup_point_in_time_all")

    def test_nodes_usage_metric_compare_modes_validate_requested_fields(self):
        runner = load_module(RUNNER_PATH, "root_cluster_node_compat_nodes_usage")

        def response(node):
            return {"status": 200, "body": {"nodes": {"node-a": node}}, "body_text": "{}"}

        self.assertEqual(
            runner.compare_targets(
                {"compare": {"compare_mode": "nodes_usage_all_metrics"}},
                response({"rest_actions": {}, "aggregations": {}}),
                response({"rest_actions": {}, "aggregations": {}}),
            ),
            [],
        )
        self.assertEqual(
            runner.compare_targets(
                {"compare": {"compare_mode": "nodes_usage_unknown_metric"}},
                response({}),
                response({}),
            ),
            [],
        )
        self.assertEqual(
            runner.compare_targets(
                {"compare": {"compare_mode": "nodes_usage_rest_actions_only"}},
                response({"rest_actions": {}}),
                response({"rest_actions": {}, "aggregations": {}}),
            ),
            ["opensearch node [node-a] included unrequested aggregations usage"],
        )


if __name__ == "__main__":
    unittest.main()
