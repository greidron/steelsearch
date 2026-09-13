import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import benchmark_runtime_evidence as evidence


class RuntimeEvidenceTests(unittest.TestCase):
    def test_host_cpu_ticks_preserve_guest_and_missing_optional_fields(self):
        ticks = evidence.parse_host_cpu_ticks("cpu 100 2 30 400 5 6 7 8 9 1\n")
        self.assertEqual(ticks["user"], 100)
        self.assertEqual(ticks["guest"], 9)
        self.assertEqual(ticks["steal"], 8)
        self.assertNotIn("guest", evidence.parse_host_cpu_ticks("cpu 1 2 3 4 5 6 7 8"))

    def test_host_cpu_rejects_malformed_counters(self):
        for line in ("", "cpu0 1 2 3 4 5 6 7 8", "cpu 1 2 3", "cpu 1 2 3 4 5 6 7 -1",
                     "cpu 1 2 3 4 5 6 7 nan", "cpu 1 2 3 4 5 6 7 8 9 10 11"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                evidence.parse_host_cpu_ticks(line)

    def test_host_cpu_observation_is_bounded_and_reports_missing_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing = evidence.observe_host_cpu(root)
            self.assertIsNone(missing["cpu_ticks"])
            self.assertEqual(missing["error"], "FileNotFoundError")
            (root / "stat").write_text("cpu 1 2 3 4 5 6 7 8\nsecret-not-a-cpu-counter\n")
            with patch.object(evidence.os, "sysconf", return_value=100):
                observed = evidence.observe_host_cpu(root)
            self.assertEqual(observed["cpu_ticks"]["steal"], 8)
            self.assertEqual(observed["clock_ticks_per_second"], 100)
            self.assertIsNone(observed["boot_id"])
            self.assertNotIn("secret-not-a-cpu-counter", json.dumps(observed))
            self.assertLessEqual(observed["started_at_epoch"], observed["finished_at_epoch"])
            with patch.object(evidence.os, "sysconf", return_value=-1):
                self.assertIsNone(evidence.observe_host_cpu(root)["cpu_ticks"])

    def test_host_cpu_counters_are_observations_not_runtime_settings(self):
        before = {"engine": "steelsearch", "nodes": [], "host_cpu": {"cpu_ticks": {"steal": 1}}}
        after = copy.deepcopy(before)
        after["host_cpu"]["cpu_ticks"]["steal"] = 2
        evidence.require_stable_runtime(before, after)

    def test_process_identity_and_secret_filtering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "42"
            proc.mkdir()
            (proc / "stat").write_text("42 (test process) " + " ".join(["S"] + ["0"] * 18 + ["123"]))
            (proc / "exe").write_bytes(b"binary")
            (proc / "environ").write_bytes(b"SECRET=never-copy\0STEELSEARCH_MODE=development\0")
            (proc / "cmdline").write_bytes(b"steelsearch\0--mode\0development\0--password\0never-copy\0")
            (proc / "status").write_text("Cpus_allowed_list:\t0-2\nMems_allowed_list:\t0\n")
            (proc / "limits").write_text("fixture limits")
            (proc / "cgroup").write_text("0::/fixture")
            sha = hashlib.sha256(b"binary").hexdigest()
            result = evidence.observe_process(42, sha, root)
            self.assertEqual(result["start_ticks"], 123)
            self.assertEqual(result["selected_cli_options"], {"--mode": "development"})
            self.assertNotIn("never-copy", json.dumps(result))
            self.assertIsNone(result["environment"]["STEELSEARCH_SECURITY_ENABLED"])
            with self.assertRaisesRegex(ValueError, "executable"):
                evidence.observe_process(42, "0" * 64, root)
            with patch.object(evidence, "process_start", side_effect=[123, 124]):
                with self.assertRaisesRegex(ValueError, "process changed"):
                    evidence.observe_process(42, sha, root)

    def test_duplicate_selected_environment_rejected(self):
        with self.assertRaises(ValueError):
            evidence.selected_environment(["MODE=a", "MODE=b"], ("MODE",))

    def test_node_cardinality_rejected_before_reading_processes(self):
        for pids in ([1], [1, 1, 2], []):
            with self.subTest(pids=pids), self.assertRaises(ValueError):
                evidence.capture_runtime(pids, [], "0" * 64, 3)

    def test_runtime_mutations_rejected(self):
        before = {"engine": "steelsearch", "nodes": [{"pid": 1, "start_ticks": 123, "sha256": "a"}]}
        evidence.require_stable_runtime(before, copy.deepcopy(before))
        after = copy.deepcopy(before)
        after["nodes"][0]["start_ticks"] = 124
        with self.assertRaises(ValueError):
            evidence.require_stable_runtime(before, after)

    def test_container_cardinality_rejected_before_inspection(self):
        with patch.object(evidence, "observe_containers") as observe:
            for names in (["a"], ["a", "a", "b"], ["a", "b", "c", "a"]):
                with self.subTest(names=names), self.assertRaises(ValueError):
                    evidence.capture_runtime([], names, None, 3)
            observe.assert_not_called()

    def test_cgroup_counters_can_change_but_settings_cannot(self):
        node = {"pid": 42, "id": "container"}
        settings = {"coverage": "visible-v2-ancestors", "membership": "0::/test"}
        with patch.object(evidence, "observe_containers", side_effect=lambda names: [copy.deepcopy(node)]), \
                patch.object(evidence, "process_start", return_value=10), \
                patch.object(evidence, "observe_cgroup", side_effect=[(settings, [1]), (settings, [2])]):
            before = evidence.capture_runtime([], ["node"], None, 1)
            after = evidence.capture_runtime([], ["node"], None, 1)
        evidence.require_stable_runtime(before, after)
        self.assertNotEqual(before["resource_counters"], after["resource_counters"])
        self.assertIn("host_cpu", before)
        self.assertIn("cpu_ticks", before["host_cpu"])
        self.assertLessEqual(before["host_cpu"]["finished_at_epoch"], before["captured_at_epoch"])
        after["nodes"][0]["cgroup"] = {"membership": "0::/different"}
        with self.assertRaisesRegex(ValueError, "settings changed"):
            evidence.require_stable_runtime(before, after)

    def test_container_identity_limits_and_secret_filtering(self):
        item = {"Name": "/node", "Id": "container-id", "Image": "image-id", "RestartCount": 0,
                "State": {"Running": True, "Pid": 42, "StartedAt": "start"},
                "Config": {"Env": ["SECRET=never-copy", "DISABLE_SECURITY_PLUGIN=true",
                                   "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m -Dpassword=never-copy"]},
                "HostConfig": {"Memory": 0, "NanoCpus": 0}}
        with patch.object(evidence.subprocess, "check_output", return_value=json.dumps([item])):
            result = evidence.observe_containers(["node"])
        self.assertNotIn("never-copy", json.dumps(result))
        self.assertEqual(result[0]["requested_heap_flags"], ["-Xms512m", "-Xmx512m"])
        self.assertEqual(result[0]["limits"]["Memory"], 0)
        self.assertIsNone(result[0]["limits"]["MemorySwap"])
        item["State"]["Running"] = False
        with patch.object(evidence.subprocess, "check_output", return_value=json.dumps([item])):
            with self.assertRaises(ValueError):
                evidence.observe_containers(["node"])


if __name__ == "__main__":
    unittest.main()
