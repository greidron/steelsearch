import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "matrix_cluster_readiness_tests",
    Path(__file__).with_name("run-search-benchmark-matrix.py"),
)
matrix = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = matrix
assert spec.loader is not None
spec.loader.exec_module(matrix)


OPEN_SEARCH = matrix.Scenario("opensearch", "three-node", 3, "OpenSearch 3-node")
STEELSEARCH = matrix.Scenario("steelsearch", "three-node", 3, "Steelsearch 3-node")
HEALTHY = {"number_of_nodes": 3, "status": "green"}
INITIALIZING_BLOCKS = {
    "blocks": {
        "global": {
            "1": {
                "description": "state not recovered / initialized",
                "retryable": True,
                "disable_state_persistence": True,
            }
        }
    }
}


class ClusterReadinessTests(unittest.TestCase):
    def test_unhealthy_or_incomplete_cluster_is_not_ready(self):
        for payload in (None, {}, {"number_of_nodes": 2, "status": "green"},
                        {"number_of_nodes": 3, "status": "yellow"},
                        {"number_of_nodes": 3, "status": "red"}):
            with self.subTest(payload=payload), \
                    patch.object(matrix, "http_json", return_value=payload) as request, \
                    patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0, 181.0]), \
                    patch.object(matrix.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "did not become ready"):
                    matrix.wait_for_cluster(OPEN_SEARCH, "http://localhost:9200", 1)
                self.assertEqual(request.call_count, 1)

    def test_block_state_requires_well_formed_empty_containers(self):
        for payload in (None, [], {}, {"blocks": None}, {"blocks": []},
                        {"blocks": {"unknown": {}}}, {"blocks": {"indices": []}},
                        {"blocks": {"indices": {"index": {"12": {}}}}}):
            with self.subTest(payload=payload):
                self.assertFalse(matrix.opensearch_cluster_blocks_ready(payload))
        for blocks in ({}, {"global": {}}, {"indices": {}}, {"global": {}, "indices": {}}):
            self.assertTrue(matrix.opensearch_cluster_blocks_ready({"blocks": blocks}))

    def test_opensearch_waits_for_initialization_block_to_clear(self):
        responses = [HEALTHY, INITIALIZING_BLOCKS, HEALTHY, {"blocks": {}}]
        with patch.object(matrix, "http_json", side_effect=responses) as request, \
                patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0, 0.5, 0.5, 1.0]), \
                patch.object(matrix.time, "sleep") as sleep:
            matrix.wait_for_cluster(OPEN_SEARCH, "http://localhost:9200", 1)

        self.assertEqual(request.call_count, 4)
        self.assertEqual(request.call_args_list[1].args[0], "http://localhost:9200/_cluster/state/blocks")
        self.assertEqual(request.call_args_list[3].args[0], "http://localhost:9200/_cluster/state/blocks")
        sleep.assert_called_once_with(0.5)

    def test_opensearch_rejects_permanent_and_unknown_blocks_until_deadline(self):
        for description in ("cluster create-index blocked (api)", "unrecognized cluster block"):
            with self.subTest(description=description):
                blocks = {"blocks": {"global": {"10": {"description": description}}}}
                with patch.object(matrix, "http_json", side_effect=[HEALTHY, blocks]), \
                        patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0, 181.0]), \
                        patch.object(matrix.time, "sleep"):
                    with self.assertRaisesRegex(RuntimeError, "did not become ready"):
                        matrix.wait_for_cluster(OPEN_SEARCH, "http://localhost:9200", 1)

    def test_opensearch_times_out_when_health_never_arrives(self):
        with patch.object(matrix, "http_json", side_effect=OSError("offline")), \
                patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0, 181.0]), \
                patch.object(matrix.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "did not become ready"):
                matrix.wait_for_cluster(OPEN_SEARCH, "http://localhost:9200", 1)

    def test_opensearch_rejects_malformed_blocks_until_deadline(self):
        malformed = {"blocks": {"global": []}}
        with patch.object(matrix, "http_json", side_effect=[HEALTHY, malformed]), \
                patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0, 181.0]), \
                patch.object(matrix.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "did not become ready"):
                matrix.wait_for_cluster(OPEN_SEARCH, "http://localhost:9200", 1)

    def test_steelsearch_keeps_node_count_only_readiness(self):
        with patch.object(matrix, "http_json", return_value={"number_of_nodes": 3}) as request, \
                patch.object(matrix.time, "monotonic", side_effect=[0.0, 0.0]):
            matrix.wait_for_cluster(STEELSEARCH, "http://localhost:9200", 1)

        request.assert_called_once_with("http://localhost:9200/_cluster/health", 1)


if __name__ == "__main__":
    unittest.main()
