import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

import benchmark_timeline as timeline


spec = importlib.util.spec_from_file_location("timeline_load", Path(__file__).with_name("run-http-load-baseline.py"))
load = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load)


class TimelineTests(unittest.TestCase):
    def test_sidecar_is_hashed_compact_and_never_overwritten(self):
        capture = timeline.DiagnosticTimeline()
        capture.record("nested", 0, 1.0, 2.0, 200)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "baseline.json"
            metadata = timeline.write_timeline_artifact(capture.snapshot(), output)
            path = Path(metadata["artifact"]["path"])
            self.assertNotIn("requests", metadata)
            self.assertNotIn("cpu_samples", metadata)
            self.assertEqual(metadata["recorded_requests"], 1)
            self.assertEqual(metadata["artifact"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(json.loads(path.read_text())["requests"], capture.snapshot()["requests"])
            with self.assertRaises(FileExistsError):
                timeline.write_timeline_artifact(capture.snapshot(), output)

    def test_request_cap_and_sanitized_status(self):
        capture = timeline.DiagnosticTimeline(request_limit=1)
        capture.record("nested", 0, 1.0, 2.0, {"private": "never-copy"})
        capture.record("write", 1, 2.0, 3.0, 201)
        result = capture.snapshot()
        self.assertEqual(len(result["requests"]), 1)
        self.assertEqual(result["dropped_requests"], 1)
        self.assertIsNone(result["requests"][0]["status"])
        self.assertNotIn("never-copy", json.dumps(result))
        self.assertTrue(result["diagnostic_only"])
        self.assertFalse(result["acceptance_established"])

    def test_cpu_cap_and_capture_failure_are_explicit(self):
        capture = timeline.DiagnosticTimeline(sample_limit=1)
        with patch.object(timeline, "observe_host_cpu", side_effect=OSError("private detail")):
            capture.sample()
            capture.sample()
        result = capture.snapshot()
        self.assertEqual(result["dropped_samples"], 1)
        self.assertEqual(result["cpu_samples"][0]["capture_error"], "OSError")
        self.assertNotIn("private detail", json.dumps(result))

    def test_sampler_is_joined_and_cannot_start_twice(self):
        capture = timeline.DiagnosticTimeline(interval=3600)
        with patch.object(timeline, "observe_host_cpu", return_value={}), \
                patch.object(timeline, "read_values", return_value={}):
            capture.start()
            try:
                with self.assertRaises(ValueError):
                    capture.start()
            finally:
                capture.stop()
                capture.stop()
        self.assertFalse(capture.thread.is_alive())
        self.assertEqual(len(capture.snapshot()["cpu_samples"]), 2)
        with self.assertRaises(ValueError):
            capture.start()

    def test_stop_before_start_prevents_background_sampler(self):
        capture = timeline.DiagnosticTimeline()
        capture.stop()
        with self.assertRaises(ValueError):
            capture.start()
        self.assertIsNone(capture.thread)
        self.assertEqual(capture.snapshot()["cpu_samples"], [])

    def test_initial_and_final_samples_bracket_requests(self):
        capture = timeline.DiagnosticTimeline(interval=3600)
        with patch.object(timeline, "observe_host_cpu", return_value={}), \
                patch.object(timeline, "read_values", return_value={}), \
                patch.object(timeline.time, "perf_counter", side_effect=[1, 2, 5, 6]):
            capture.start()
            try:
                capture.record("refresh", 0, 3, 1000, 200)
            finally:
                capture.stop()
        result = capture.snapshot()
        self.assertLessEqual(result["cpu_samples"][0]["finished"], result["requests"][0]["started"])
        self.assertGreaterEqual(result["cpu_samples"][-1]["started"], 4)

    def test_invalid_bounds(self):
        for options in ({"request_limit": -1}, {"sample_limit": -1}, {"interval": 0},
                        {"interval": float("nan")}, {"interval": float("inf")}, {"request_limit": True}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                timeline.DiagnosticTimeline(**options)

    def runner(self, enabled):
        return load.LoadRunner({"seed": 13, "query_mix": {"nested": 1},
                                "base_url": "http://unused", "diagnostic_timeline": enabled}, 1)

    def test_default_does_not_allocate_timeline(self):
        with patch.object(load, "DiagnosticTimeline") as constructor:
            self.assertIsNone(self.runner(False).timeline)
            constructor.assert_not_called()

    def test_worker_records_success_and_exception_without_request_payload(self):
        for failure in (False, True):
            runner = self.runner(True)
            with patch.object(load.time, "monotonic", side_effect=[0, 2]), \
                    patch.object(load.time, "perf_counter", side_effect=[10, 10.025]), \
                    patch.object(runner, "run_operation", side_effect=RuntimeError("private") if failure else None,
                                 return_value={"status": 200, "body": {"private": "payload"}}):
                runner.worker(0, 1, None)
            events = runner.timeline.snapshot()["requests"]
            self.assertEqual(len(events), 1)
            self.assertAlmostEqual(events[0]["elapsed_ms"], 25)
            self.assertEqual(events[0]["status"], None if failure else 200)
            self.assertNotIn("private", json.dumps(events))
            self.assertEqual(runner.errors["nested"], int(failure))


if __name__ == "__main__":
    unittest.main()
