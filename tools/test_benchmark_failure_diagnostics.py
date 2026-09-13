import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location("matrix_failure_tests", Path(__file__).with_name("run-search-benchmark-matrix.py"))
matrix = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = matrix
spec.loader.exec_module(matrix)


class FailureDiagnosticsTests(unittest.TestCase):
    def test_selected_binary_discovery_excludes_launchers_and_other_binaries(self):
        binary = Path("target/before-index-generation").resolve()
        commands = {10: ["/bin/bash", "launcher"], 11: [str(binary)],
                    12: ["/other/steelsearch"], 13: [str(binary), "serve"],
                    14: [], 15: [str(binary)]}
        with patch.object(matrix, "descendant_pids", return_value=[11, 12, 13, 14, 15, 11]), \
                patch.object(matrix, "process_cmdline", side_effect=commands.__getitem__):
            self.assertEqual(matrix.steelsearch_resource_pids(10, binary), [11, 13, 15])
        with patch.object(matrix, "descendant_pids", return_value=[12, 14]), \
                patch.object(matrix, "process_cmdline", side_effect=commands.__getitem__):
            self.assertEqual(matrix.steelsearch_resource_pids(10, binary), [])

    def test_resource_discovery_passes_selected_path_and_preserves_docker(self):
        handle = SimpleNamespace(container_names=[], process=SimpleNamespace(pid=10))
        binary = Path("target/custom-name")
        with patch.object(matrix, "steelsearch_resource_pids", return_value=[11]) as discover:
            self.assertEqual(matrix.resolve_resource_pids(handle, binary), [11])
            discover.assert_called_once_with(10, binary)
            with self.assertRaisesRegex(ValueError, "selected"):
                matrix.resolve_resource_pids(handle, None)
        handle.container_names = ["owned-reference"]
        with patch.object(matrix, "docker_container_pids", return_value=[21]) as discover:
            self.assertEqual(matrix.resolve_resource_pids(handle, None), [21])
            discover.assert_called_once_with(["owned-reference"])

    def test_endpoint_failure_does_not_hide_other_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(matrix, "http_json", side_effect=[{"persistent": {}}, OSError("offline"), {"nodes": {}}]) as request:
                matrix.capture_opensearch_failure("http://localhost:9200", Path(directory), 20)
            data = json.loads((Path(directory) / "failure-diagnostics.json").read_text())
            self.assertTrue(data["diagnostic_only"])
            self.assertFalse(data["acceptance_established"])
            self.assertEqual(data["blocks"], {"capture_error": "offline"})
            self.assertEqual(data["filesystem"], {"nodes": {}})
            self.assertEqual(request.call_count, 3)
            self.assertTrue(all(call.args[1] == 5.0 for call in request.call_args_list))
            self.assertIn("filter_path=", request.call_args_list[0].args[0])

    def test_output_error_does_not_replace_benchmark_failure(self):
        with patch.object(matrix, "http_json", return_value={}), patch.object(Path, "write_text", side_effect=OSError("full")), patch.object(matrix.sys, "stderr"):
            matrix.capture_opensearch_failure("http://localhost:9200", Path("missing"), 1)


if __name__ == "__main__":
    unittest.main()
