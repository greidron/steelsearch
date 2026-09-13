from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark_cgroup_evidence import observe_cgroup


class CgroupEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.proc = root / "proc"
        (self.proc / "42").mkdir(parents=True)
        (self.proc / "self").mkdir()
        self.cgroup = root / "group space"
        (self.cgroup / "parent" / "child").mkdir(parents=True)
        self.membership = self.proc / "42" / "cgroup"
        self.membership.write_text("0::/parent/child\n")
        escaped = str(self.cgroup).replace(" ", r"\040")
        self.mountinfo = self.proc / "self" / "mountinfo"
        self.mountinfo.write_text(f"1 0 0:1 / {escaped} rw - cgroup2 cgroup2 rw\n")

    def test_parent_limits_and_dynamic_counters_are_separate(self):
        (self.cgroup / "parent" / "cpu.max").write_text("100000 100000\n")
        (self.cgroup / "parent" / "child" / "cpu.max").write_text("max 100000\n")
        (self.cgroup / "parent" / "cpu.stat").write_text("nr_throttled 4\n")
        settings, counters = observe_cgroup(42, self.proc)
        self.assertEqual(settings["coverage"], "visible-v2-ancestors")
        self.assertEqual([row["path"] for row in settings["levels"]], ["/parent/child", "/parent", "/"])
        self.assertEqual(settings["levels"][1]["settings"]["cpu.max"]["value"], "100000 100000")
        self.assertEqual(counters[1]["counters"]["cpu.stat"]["value"], "nr_throttled 4")
        (self.cgroup / "parent" / "cpu.stat").write_text("nr_throttled 5\n")
        changed, changed_counters = observe_cgroup(42, self.proc)
        self.assertEqual(settings, changed)
        self.assertNotEqual(counters, changed_counters)

    def test_missing_files_are_unknown_not_unlimited(self):
        settings, _ = observe_cgroup(42, self.proc)
        value = settings["levels"][0]["settings"]["memory.max"]
        self.assertIsNone(value["value"])
        self.assertEqual(value["error"], "FileNotFoundError")

    def test_unsupported_or_hidden_root_does_not_claim_coverage(self):
        self.membership.write_text("1:cpu:/parent/child\n")
        settings, _ = observe_cgroup(42, self.proc)
        self.assertEqual(settings["coverage"], "unsupported-cgroup-layout")
        self.membership.write_text("0::/parent/child\n")
        self.mountinfo.write_text(f"1 0 0:1 /hidden {self.cgroup} rw - cgroup2 cgroup2 rw\n")
        settings, _ = observe_cgroup(42, self.proc)
        self.assertEqual(settings["coverage"], "full-root-mount-unavailable")

    def test_traversal_and_symlink_escape_rejected(self):
        self.membership.write_text("0::/../outside\n")
        with self.assertRaisesRegex(ValueError, "invalid"):
            observe_cgroup(42, self.proc)
        (self.cgroup / "escape").symlink_to(self.proc, target_is_directory=True)
        self.membership.write_text("0::/escape\n")
        with self.assertRaisesRegex(ValueError, "escapes"):
            observe_cgroup(42, self.proc)

    def test_membership_change_rejected(self):
        original = Path.read_text
        reads = 0

        def read(path, *args, **kwargs):
            nonlocal reads
            if path == self.membership:
                reads += 1
                if reads == 2:
                    return "0::/moved\n"
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", read), self.assertRaisesRegex(ValueError, "changed"):
            observe_cgroup(42, self.proc)


if __name__ == "__main__":
    unittest.main()
