import importlib.util
import os
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("core_cpu_diagnostic", Path(__file__).with_name("run-core-cpu-diagnostic.py"))
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class CpuDiagnosticTests(unittest.TestCase):
    def test_futex_capture_targets_only_owned_servers(self):
        cmd = diagnostic.profile_command(Path("out"), {
            11: "server", 12: "load-generator", 13: "server"}, "futex")
        self.assertEqual(cmd[cmd.index("-p") + 1], "11,13")
        self.assertNotIn("-a", cmd)
        self.assertNotIn("-F", cmd)
        self.assertEqual(cmd[cmd.index("-e") + 1], "syscalls:sys_enter_futex")
        self.assertNotIn("--filter", cmd)
        self.assertEqual(cmd[cmd.index("-c") + 1], "100")

    def test_cpu_capture_preserves_existing_targets_and_frequency(self):
        cmd = diagnostic.profile_command(Path("out"), {11: "server", 12: "load-generator"}, "cpu")
        self.assertEqual(cmd[cmd.index("-p") + 1], "11,12")
        self.assertEqual(cmd[cmd.index("-F") + 1], "49")
        self.assertNotIn("--filter", cmd)

    def test_invalid_or_empty_capture_rejected(self):
        for roles, profile in [({}, "cpu"), ({12: "load-generator"}, "futex"),
                               ({11: "server"}, "unknown")]:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                diagnostic.profile_command(Path("out"), roles, profile)

    def test_cpu_frequency_changes_only_sampling_option(self):
        default = diagnostic.profile_command(Path("out"), {11: "server"}, "cpu")
        adjusted = diagnostic.profile_command(Path("out"), {11: "server"}, "cpu", 997)
        expected = default.copy()
        expected[expected.index("-F") + 1] = "997"
        self.assertEqual(adjusted, expected)

    def test_invalid_frequency_and_futex_override_rejected(self):
        for frequency in (0, -1, 2001, True, 49.0, "997"):
            with self.subTest(frequency=frequency), self.assertRaises(ValueError):
                diagnostic.profile_command(Path("out"), {11: "server"}, "cpu", frequency)
        with self.assertRaisesRegex(ValueError, "cpu profile"):
            diagnostic.profile_command(Path("out"), {11: "server"}, "futex", 997)

    def test_sort_filter_diagnostic_preserves_fixed_workload(self):
        self.assertIn("sort_filter", diagnostic.OPERATIONS)
        cmd = diagnostic.diagnostic_command(Path("out"), "sort_filter", "three-node")
        for option, value in {
            "--query-mix": "sort_filter=100",
            "--scenarios": "steelsearch-three-node",
            "--duration-seconds": "45",
            "--corpus-size": "5000",
            "--vector-dimension": "384",
            "--clients": "4",
            "--number-of-shards": "3",
            "--number-of-replicas": "1",
            "--seed": "13",
        }.items():
            self.assertEqual(cmd[cmd.index(option) + 1], value)

    def test_topology_and_isolated_operations(self):
        for topology, servers in diagnostic.TOPOLOGY_NODE_COUNTS.items():
            self.assertEqual(servers, 1 if topology == "single-node" else 3)
            for operation in diagnostic.OPERATIONS:
                cmd = diagnostic.diagnostic_command(Path("out"), operation, topology)
                self.assertEqual(cmd[cmd.index("--scenarios") + 1], f"steelsearch-{topology}")
                if operation == "mixed":
                    self.assertIn("write=15", cmd[cmd.index("--query-mix") + 1])
                elif operation == "write_search":
                    self.assertEqual(
                        cmd[cmd.index("--query-mix") + 1],
                        "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10",
                    )
                else:
                    self.assertEqual(cmd[cmd.index("--query-mix") + 1], f"{operation}=100")
                self.assertEqual(cmd[cmd.index("--clients") + 1], "4")
        with self.assertRaisesRegex(ValueError, "topology"):
            diagnostic.diagnostic_command(Path("out"), "mixed", "unknown")

    def test_all_core_operations_change_only_diagnostic_selection(self):
        self.assertEqual(set(diagnostic.OPERATIONS), {
            "mixed", "write", "lexical", "ranking", "facet", "sort_filter", "nested", "refresh",
            "write_search",
        })
        for topology in diagnostic.TOPOLOGY_NODE_COUNTS:
            for operation in ("facet", "ranking", "refresh"):
                with self.subTest(topology=topology, operation=operation):
                    expected = diagnostic.command("baseline", Path("out") / "matrix")
                    expected[expected.index("--duration-seconds") + 1] = "45"
                    expected[expected.index("--scenarios") + 1] = f"steelsearch-{topology}"
                    expected[expected.index("--query-mix") + 1] = f"{operation}=100"
                    self.assertEqual(diagnostic.diagnostic_command(Path("out"), operation, topology), expected)

    def test_write_search_preset_changes_only_query_mix_from_mixed_both_topologies(self):
        expected_mix = "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10"
        for topology in diagnostic.TOPOLOGY_NODE_COUNTS:
            with self.subTest(topology=topology):
                mixed = diagnostic.diagnostic_command(Path("out"), "mixed", topology)
                write_search = diagnostic.diagnostic_command(Path("out"), "write_search", topology)
                query_mix = write_search.index("--query-mix")

                self.assertEqual(write_search[query_mix + 1], expected_mix)
                self.assertNotIn("refresh", write_search[query_mix + 1])
                self.assertEqual(write_search[:query_mix] + write_search[query_mix + 2:],
                                 mixed[:query_mix] + mixed[query_mix + 2:])

    def test_plugin_operations_remain_rejected(self):
        for operation in ("vector", "hybrid", "knn", "neural"):
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, "operation"):
                diagnostic.diagnostic_command(Path("out"), operation)

    def test_server_identity_uses_selected_path_not_basename(self):
        binary = Path("target/steelsearch-before-native-count").resolve()
        self.assertEqual(diagnostic.diagnostic_process_role([str(binary), "serve"], binary), "server")
        self.assertIsNone(diagnostic.diagnostic_process_role(["/different/steelsearch"], binary))
        self.assertIsNone(diagnostic.diagnostic_process_role([], binary))
        self.assertEqual(diagnostic.diagnostic_process_role(
            ["/usr/bin/python3", "/tools/run-http-load-baseline.py"], binary), "load-generator")

    def test_diagnostic_operation_selection_preserves_mixed_default(self):
        mixed = diagnostic.diagnostic_command(Path("out"), "mixed")
        nested = diagnostic.diagnostic_command(Path("out"), "nested")
        self.assertIn("write=15", mixed[mixed.index("--query-mix") + 1])
        self.assertEqual(nested[nested.index("--query-mix") + 1], "nested=100")
        self.assertEqual(nested[nested.index("--duration-seconds") + 1], "45")
        self.assertEqual(nested[nested.index("--scenarios") + 1], "steelsearch-three-node")
        with self.assertRaises(ValueError):
            diagnostic.diagnostic_command(Path("out"), "unknown")

    def test_selected_binary_identity_and_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate"
            path.write_bytes(b"candidate")
            digest = hashlib.sha256(b"candidate").hexdigest()
            self.assertEqual(diagnostic.verify_binary(path, digest), digest)
            with self.assertRaisesRegex(ValueError, "mismatch"):
                diagnostic.verify_binary(path, diagnostic.BASELINE_SHA256)
            path.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                diagnostic.verify_binary(path, digest)

    def test_malformed_expected_identity_rejected(self):
        for expected in ("", "z" * 64, "A" * 64):
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
                diagnostic.verify_binary(Path("not-read"), expected)

    def test_process_stat_fields_with_parenthesized_command(self):
        fields = ["S"] + ["0"] * 20
        fields[11], fields[12], fields[19] = "123", "45", "678"
        with patch.object(Path, "read_text", return_value="42 (worker (nested) name) " + " ".join(fields)):
            self.assertEqual(diagnostic.cpu_sample(42), {
                "start_ticks": 678, "user_ticks": 123, "system_ticks": 45})

    def test_live_owned_process_sample(self):
        before = diagnostic.cpu_sample(os.getpid())
        after = diagnostic.cpu_sample(os.getpid())
        self.assertEqual(before["start_ticks"], after["start_ticks"])
        for key in ("user_ticks", "system_ticks"):
            self.assertGreaterEqual(after[key], before[key])


if __name__ == "__main__":
    unittest.main()
