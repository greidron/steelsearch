import json
import unittest

from core_lock_diagnostic import APPEND_PREFIX, PREFIX, parse_append, summarize


def line(**changes):
    sample = dict(site="refresh_plan", pid=12, attempt=0, sample_every=64, wait_ns=20, held_ns=30)
    sample.update(changes)
    return PREFIX + json.dumps(sample)


def append_line(**changes):
    sample = dict(pid=12, batches=1, documents=3, commit_nanos=20)
    sample.update(changes)
    return APPEND_PREFIX + json.dumps(sample)


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

    def test_refresh_writer_is_a_valid_lock_site(self):
        result = summarize([line(site="refresh_writer")], {12})
        self.assertEqual(result["groups"][0]["site"], "refresh_writer")

    def test_append_samples_first_and_64_batch_boundaries(self):
        samples = parse_append([
            append_line(batches=1, documents=2, commit_nanos=1),
            append_line(batches=65, documents=130, commit_nanos=2145),
            append_line(batches=129, documents=258, commit_nanos=8385),
        ], {12})
        self.assertEqual([sample["batches"] for sample in samples], [1, 65, 129])

    def test_append_samples_allow_concurrent_log_arrival_reordering(self):
        samples = parse_append([
            append_line(batches=65, documents=130, commit_nanos=2145),
            append_line(batches=1, documents=2, commit_nanos=1),
        ], {12})
        self.assertEqual([sample["batches"] for sample in samples], [1, 65])

    def test_append_summary_reports_only_final_sample_lower_bound(self):
        result = summarize([
            append_line(batches=1, documents=2, commit_nanos=1),
            append_line(batches=65, documents=130, commit_nanos=2145),
        ], {12})
        group = result["append_groups"][0]
        self.assertEqual(group["samples"], 2)
        self.assertEqual(group["final_sample_lower_bound"],
                         {"batches": 65, "documents": 130, "commit_nanos": 2145})
        self.assertNotIn("documents_sum", group)
        self.assertIn("full rebuilds and failed writes are excluded", result["append_scope"])

    def test_mixed_log_generator_preserves_lock_and_append_samples(self):
        lines = (entry for entry in [line(), append_line()])
        result = summarize(lines, {12})
        self.assertEqual(result["groups"][0]["samples"], 1)
        self.assertEqual(result["append_groups"][0]["samples"], 1)

    def test_invalid_append_samples_are_rejected(self):
        for lines in ([append_line(batches=0)], [append_line(batches=64)],
                      [append_line(documents=True)], [append_line(commit_nanos=-1)],
                      [append_line(pid=99)], [append_line(extra=1)],
                      [APPEND_PREFIX + "[]"], [APPEND_PREFIX + "null"],
                      [APPEND_PREFIX + "0"], [APPEND_PREFIX + "true"],
                      [append_line(), append_line()],
                      [append_line(batches=65, documents=2, commit_nanos=20),
                       append_line(batches=129, documents=1, commit_nanos=21)],
                      [append_line(batches=65, documents=2, commit_nanos=20),
                       append_line(batches=129, documents=3, commit_nanos=19)]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse_append(lines, {12})


if __name__ == "__main__":
    unittest.main()
