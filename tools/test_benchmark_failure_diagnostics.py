import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location("matrix_failure_tests", Path(__file__).with_name("run-search-benchmark-matrix.py"))
matrix = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = matrix
spec.loader.exec_module(matrix)


class FailureDiagnosticsTests(unittest.TestCase):
    def safety_responses(self, enabled=True, blocks=None):
        return [
            {"transient": {}, "persistent": {},
             "defaults": {"cluster": {"routing": {"allocation": {"disk": {
                 "threshold_enabled": enabled}}}}}},
            {"_nodes": {"total": 2, "successful": 2, "failed": 0},
             "nodes": {"a": {"settings": {}}, "b": {"settings": {}}}},
            {"blocks": blocks if blocks is not None else {"global": {}, "indices": {}}},
        ]

    def test_safety_check_only_reads_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            responses = self.safety_responses()
            with patch.object(matrix, "http_json", side_effect=responses) as request:
                evidence = matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
            self.assertEqual(evidence["settings"], responses[0])
            self.assertEqual(json.loads((Path(directory) / "opensearch-safety-before.json").read_text()), evidence)
            self.assertEqual(request.call_count, 3)
            for call in request.call_args_list:
                self.assertNotIn("method", call.kwargs)
                self.assertNotIn("payload", call.kwargs)

    def test_safety_check_rejects_disabled_missing_and_blocked_settings(self):
        for enabled in [False, "false", None, 1]:
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as directory:
                with patch.object(matrix, "http_json", side_effect=self.safety_responses(enabled)):
                    with self.assertRaisesRegex(RuntimeError, "disabled or unverified"):
                        matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
                self.assertTrue((Path(directory) / "opensearch-safety-before.json").exists())
        for blocks in [{"global": {"6": {}}, "indices": {}},
                       {"global": {}, "indices": {"index": {"12": {}}}}]:
            with self.subTest(blocks=blocks), tempfile.TemporaryDirectory() as directory:
                with patch.object(matrix, "http_json", side_effect=self.safety_responses(blocks=blocks)):
                    with self.assertRaisesRegex(RuntimeError, "blocks"):
                        matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "after")

    def test_safety_check_observes_node_and_cluster_override_precedence(self):
        key = "cluster.routing.allocation.disk.threshold_enabled"
        with tempfile.TemporaryDirectory() as directory:
            responses = self.safety_responses()
            responses[1]["nodes"]["b"]["settings"][key] = "false"
            with patch.object(matrix, "http_json", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, "node b"):
                    matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
            responses[0]["persistent"] = {key: "true"}
            with patch.object(matrix, "http_json", side_effect=responses):
                matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
            responses[0]["transient"] = {key: "false"}
            with patch.object(matrix, "http_json", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, "disabled"):
                    matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
            responses[0]["transient"] = {"cluster.blocks.create_index": "true"}
            with patch.object(matrix, "http_json", side_effect=responses):
                with self.assertRaisesRegex(RuntimeError, "create_index"):
                    matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")

    def test_safety_check_rejects_incomplete_or_malformed_node_settings(self):
        invalid_nodes = [
            {},
            {"_nodes": {"total": 2, "successful": 2, "failed": 0}, "nodes": {}},
            {"_nodes": {"total": 2, "successful": 1, "failed": 1},
             "nodes": {"a": {"settings": {}}, "b": {"settings": {}}}},
            {"_nodes": {"total": 3, "successful": 3, "failed": 0},
             "nodes": {"a": {"settings": {}}, "b": {"settings": {}}}},
            {"_nodes": {"total": 2, "successful": 2, "failed": 0},
             "nodes": {"a": {"settings": {}}, "b": {}}},
        ]
        for node_response in invalid_nodes:
            with self.subTest(node_response=node_response), tempfile.TemporaryDirectory() as directory:
                responses = self.safety_responses()
                responses[1] = node_response
                with patch.object(matrix, "http_json", side_effect=responses):
                    with self.assertRaisesRegex(RuntimeError, "node settings"):
                        matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")
                self.assertTrue((Path(directory) / "opensearch-safety-before.json").exists())

    def test_safety_check_rejects_malformed_settings_and_block_containers(self):
        invalid_responses = [
            ({"transient": {}, "persistent": {}, "defaults": []}, self.safety_responses()[2]),
            (self.safety_responses()[0], {"blocks": {"global": [], "indices": {}}}),
            (self.safety_responses()[0], {"blocks": {"global": {}, "indices": None}}),
        ]
        for settings, blocks in invalid_responses:
            with self.subTest(settings=settings, blocks=blocks), tempfile.TemporaryDirectory() as directory:
                responses = self.safety_responses()
                responses[0] = settings
                responses[2] = blocks
                with patch.object(matrix, "http_json", side_effect=responses):
                    with self.assertRaisesRegex(RuntimeError, "malformed"):
                        matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "after")

    def test_safety_check_accepts_actual_empty_blocks_response(self):
        with tempfile.TemporaryDirectory() as directory:
            responses = self.safety_responses()
            responses[2] = {
                "cluster_name": "docker-cluster",
                "cluster_uuid": "mVrp6w3KSCuGn5sT0D9Qvw",
                "blocks": {},
            }
            with patch.object(matrix, "http_json", side_effect=responses):
                matrix.require_opensearch_safety("http://localhost", Path(directory), 5, "before")

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
            with patch.object(matrix, "http_json", side_effect=[
                {"status": "red"}, {"persistent": {}}, OSError("offline"),
                {"allocate_explanation": "unassigned"}, {"nodes": {}},
            ]) as request:
                matrix.capture_opensearch_failure("http://localhost:9200", Path(directory), 20)
            data = json.loads((Path(directory) / "failure-diagnostics.json").read_text())
            self.assertTrue(data["diagnostic_only"])
            self.assertFalse(data["acceptance_established"])
            self.assertEqual(data["health"], {"status": "red"})
            self.assertEqual(data["blocks"], {"capture_error": "offline"})
            self.assertEqual(data["allocation_explain"], {"allocate_explanation": "unassigned"})
            self.assertEqual(data["filesystem"], {"nodes": {}})
            self.assertEqual(request.call_count, 5)
            self.assertTrue(all(call.args[1] == 5.0 for call in request.call_args_list))
            self.assertEqual(request.call_args_list[0].args[0], "http://localhost:9200/_cluster/health")
            self.assertIn("filter_path=", request.call_args_list[1].args[0])
            self.assertEqual(request.call_args_list[3].args[0], "http://localhost:9200/_cluster/allocation/explain")

    def test_readiness_failure_captures_before_cleanup_and_preserves_original_error(self):
        opensearch = matrix.Scenario("opensearch", "single-node", 1, "OpenSearch 1-node")
        steelsearch = matrix.Scenario("steelsearch", "single-node", 1, "Steelsearch 1-node")
        args = SimpleNamespace(
            capture_runtime_evidence=False,
            profile="quick-minilm-knn",
            corpus_size=1500,
            vector_dimension=384,
            duration_seconds=8.0,
            clients=4,
            query_mix="write=100",
            vector_source="default",
            vector_space_type="default",
            number_of_shards=3,
            number_of_replicas=1,
            timeout_seconds=1.0,
            seed=13,
            operation_resource_deltas=False,
            diagnostic_timeline=False,
            reuse_steelsearch_binary=False,
            aggregate_only=False,
            skip_existing=False,
            dry_run=False,
            scenarios="opensearch-single-node",
        )
        original_capture = matrix.capture_opensearch_failure

        for scenario, capture_expected in ((opensearch, True), (steelsearch, False)):
            with self.subTest(scenario=scenario.key), tempfile.TemporaryDirectory() as directory:
                events = []
                args.output_dir = directory
                handle = MagicMock(base_url="http://localhost:9200")
                handle.stop.side_effect = lambda: events.append("cleanup")

                def capture(*capture_args):
                    events.append("capture")
                    original_capture(*capture_args)

                with patch.object(matrix.argparse.ArgumentParser, "parse_args", return_value=args), \
                        patch.object(matrix, "selected_scenarios", return_value=(scenario,)), \
                        patch.object(matrix, "build_steelsearch_release_binary", return_value=Path("unused")), \
                        patch.object(matrix, "executable_evidence", return_value={"path": "unused", "sha256": "unused"}), \
                        patch.object(matrix, "start_cluster", return_value=handle), \
                        patch.object(matrix, "wait_for_cluster", side_effect=RuntimeError("readiness failed")), \
                        patch.object(matrix, "http_json", side_effect=[
                            OSError("offline"), {"unexpected": True}, OSError("offline"), [], OSError("offline"),
                        ]), \
                        patch.object(matrix, "capture_opensearch_failure", side_effect=capture):
                    with self.assertRaisesRegex(RuntimeError, "readiness failed"):
                        matrix.main()

                self.assertEqual(events, ["capture", "cleanup"] if capture_expected else ["cleanup"])
                diagnostics = Path(directory) / scenario.key / "failure-diagnostics.json"
                self.assertEqual(diagnostics.exists(), capture_expected)
                if capture_expected:
                    data = json.loads(diagnostics.read_text())
                    self.assertEqual(data["health"], {"capture_error": "offline"})
                    self.assertEqual(data["allocation_explain"], [])

    def test_output_error_does_not_replace_benchmark_failure(self):
        with patch.object(matrix, "http_json", return_value={}), patch.object(Path, "write_text", side_effect=OSError("full")), patch.object(matrix.sys, "stderr"):
            matrix.capture_opensearch_failure("http://localhost:9200", Path("missing"), 1)


if __name__ == "__main__":
    unittest.main()
