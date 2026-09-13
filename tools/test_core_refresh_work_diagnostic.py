import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
from types import SimpleNamespace


spec = importlib.util.spec_from_file_location("refresh_work", Path(__file__).with_name("run-core-refresh-work-diagnostic.py"))
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class RefreshWorkDiagnosticTests(unittest.TestCase):
    def test_scenario_selection_uses_engine_and_topology(self):
        scenarios = [SimpleNamespace(engine=engine, topology=topology)
                     for engine in ("opensearch", "steelsearch")
                     for topology in ("single-node", "three-node")]
        matrix = SimpleNamespace(SCENARIOS=scenarios)
        for topology in ("single-node", "three-node"):
            selected = diagnostic.select_scenario(matrix, topology)
            self.assertEqual((selected.engine, selected.topology), ("steelsearch", topology))

    def test_endpoint_drains_all_nodes_before_observing_each(self):
        matrix = Mock()
        refresh = {"_shards": {"failed": 0}}
        matrix.http_json.side_effect = [refresh, refresh, self.response(12), self.response(12), {},
                                       self.response(9), self.response(9), {}]
        result = diagnostic.observe_endpoints(matrix, ["a", "b"], "idx", drain=True)
        self.assertEqual([row["native_count"] for row in result], [12, 9])
        self.assertEqual([row["url"] for row in result], ["a", "b"])
        self.assertEqual([call.args[0] for call in matrix.http_json.call_args_list[:2]],
                         ["a/idx/_refresh", "b/idx/_refresh"])
        self.assertTrue(all(row["refresh_response"] == refresh for row in result))

    def test_endpoint_failed_drain_prevents_visibility_claim(self):
        matrix = Mock()
        for failed in (1, True, None):
            matrix.http_json.return_value = {"_shards": {"failed": failed}}
            with self.assertRaises(ValueError):
                diagnostic.observe_endpoints(matrix, ["a"], "idx", drain=True)

    def counter_response(self, node_id="local"):
        values = {f"refresh_tantivy_{part}_nanos": i
                  for i, part in enumerate(("document_add", "commit", "reload", "doc_id_lookup"))}
        return {"nodes": {node_id: {"steelsearch": {"search_cache": values}},
                          "remote": {"steelsearch": {"search_cache": {}}}}}

    def test_node_counters_preserve_raw_local_values_without_remote_double_count(self):
        matrix = Mock()
        responses = [self.counter_response(str(i)) for i in range(3)]
        matrix.http_json.side_effect = responses
        result = diagnostic.observe_node_counters(matrix, ["a", "b", "c"], 3)
        self.assertEqual([row["node_id"] for row in result], ["0", "1", "2"])
        self.assertEqual([row["response"] for row in result], responses)
        self.assertEqual(result[0]["counters"]["refresh_tantivy_commit_nanos"], 1)

    def test_node_counters_reject_incomplete_or_duplicated_evidence(self):
        matrix = Mock()
        for urls in (["a"], ["a", "a"]):
            with self.assertRaises(ValueError):
                diagnostic.observe_node_counters(matrix, urls, 2)
        matrix.http_json.side_effect = [self.counter_response(), self.counter_response()]
        with self.assertRaises(ValueError):
            diagnostic.observe_node_counters(matrix, ["a", "b"], 2)
        matrix.http_json.side_effect = None
        for invalid in (None, True, -1, "1"):
            response = self.counter_response()
            response["nodes"]["local"]["steelsearch"]["search_cache"]["refresh_tantivy_commit_nanos"] = invalid
            matrix.http_json.return_value = response
            with self.assertRaises(ValueError):
                diagnostic.observe_node_counters(matrix, ["a"], 1)
        matrix.http_json.return_value = {"nodes": {}}
        with self.assertRaises(ValueError):
            diagnostic.observe_node_counters(matrix, ["a"], 1)

    def test_expected_count_requires_success_and_fresh_unique_write_workload(self):
        report = {"summary": {"error_count": 0}, "config": {"reset": True, "corpus_size": 5000},
                  "operations": {"write": {"success_count": 123}}}
        self.assertEqual(diagnostic.expected_documents(report), 5123)
        for path, value in ((["load_runner_returncode"], 1), (["summary", "error_count"], 1),
                            (["config", "reset"], False), (["config", "corpus_size"], True),
                            (["operations", "write", "success_count"], -1)):
            changed = copy.deepcopy(report)
            parent = changed
            for part in path[:-1]:
                parent = parent[part]
            parent[path[-1]] = value
            with self.assertRaises(ValueError):
                diagnostic.expected_documents(changed)

    def response(self, total=12):
        return {"hits": {"total": {"value": total, "relation": "eq"}},
                "timed_out": False, "_shards": {"failed": 0}}

    def test_search_count_rejects_partial_approximate_or_malformed_evidence(self):
        self.assertEqual(diagnostic.exact_total(self.response()), 12)
        for value in (True, -1, "12", None):
            with self.assertRaises(ValueError):
                diagnostic.exact_total(self.response(value))
        for path, value in ((["hits", "total", "relation"], "gte"), (["timed_out"], True),
                            (["_shards", "failed"], 1), (["_shards", "failed"], False)):
            response = self.response()
            parent = response
            for part in path[:-1]:
                parent = parent[part]
            parent[path[-1]] = value
            with self.assertRaises(ValueError):
                diagnostic.exact_total(response)
        response = self.response()
        del response["_shards"]
        with self.assertRaises(ValueError):
            diagnostic.exact_total(response)

    def test_observation_preserves_both_counts_and_raw_responses(self):
        matrix = Mock()
        native, fallback, stats = self.response(12), self.response(13), {"raw": "stats"}
        matrix.http_json.side_effect = [native, fallback, stats]
        result = diagnostic.observe(matrix, "http://localhost", "test-index")
        self.assertEqual((result["native_count"], result["fallback_count"]), (12, 13))
        self.assertEqual(result["responses"], {"native": native, "fallback": fallback, "stats": stats})
        self.assertEqual(matrix.http_json.call_args_list[0].args[3]["track_total_hits"], True)
        self.assertIn("ignore_unavailable=false", matrix.http_json.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
