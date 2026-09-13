import json
import unittest

from core_lock_diagnostic import PREFIX, summarize


def line(**changes):
    sample = dict(site="refresh_plan", pid=12, attempt=0, sample_every=64, wait_ns=20, held_ns=30)
    sample.update(changes)
    return PREFIX + json.dumps(sample)


class LockDiagnosticTests(unittest.TestCase):
    def test_samples_group_by_site_and_process_without_percentile_claim(self):
        result = summarize(["normal log", line(), line(attempt=64, wait_ns=40),
                            line(pid=13), line(site="search_snapshot")], {12, 13})
        self.assertTrue(result["diagnostic_only"])
        self.assertFalse(result["acceptance_established"])
        self.assertEqual(len(result["groups"]), 3)
        group = result["groups"][0]
        self.assertEqual((group["samples"], group["wait_ns_sum"], group["wait_ns_max"]), (2, 60, 40))
        self.assertEqual(group["held_ns_sum"], 60)

    def test_missing_invalid_and_duplicate_samples_rejected(self):
        for lines in (["normal log"], [line(), line()], [PREFIX + "invalid"],
                      [line(pid=99)], [line(site="unknown")], [line(wait_ns=-1)],
                      [line(held_ns=True)], [line(sample_every=1)], [line(attempt=1)]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                summarize(lines, {12})

    def test_does_not_estimate_unsampled_events(self):
        group = summarize([line(), line(attempt=640)], {12})["groups"][0]
        self.assertEqual(group["samples"], 2)
        self.assertEqual(group["wait_ns_sum"], 40)


if __name__ == "__main__":
    unittest.main()
