"""Bounded opt-in timelines; never suitable for performance acceptance."""

from pathlib import Path
import hashlib
import json
import math
import threading
import time

from benchmark_cgroup_evidence import read_values
from benchmark_runtime_evidence import observe_host_cpu


def write_timeline_artifact(snapshot, output):
    path = Path(output).with_suffix(".timeline.json").resolve()
    with path.open("x", encoding="utf-8") as stream:
        json.dump(snapshot, stream, separators=(",", ":"))
        stream.write("\n")
    with path.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    metadata = {key: value for key, value in snapshot.items() if key not in ("requests", "cpu_samples")}
    metadata.update(recorded_requests=len(snapshot["requests"]),
                    recorded_cpu_samples=len(snapshot["cpu_samples"]),
                    artifact={"path": str(path), "sha256": sha256, "size_bytes": path.stat().st_size})
    return metadata


class DiagnosticTimeline:
    def __init__(self, request_limit=100000, sample_limit=4096, interval=0.25):
        if (type(request_limit) is not int or type(sample_limit) is not int
                or request_limit < 0 or sample_limit < 0
                or not math.isfinite(interval) or interval <= 0):
            raise ValueError("invalid timeline bounds")
        self.request_limit = request_limit
        self.sample_limit = sample_limit
        self.interval = interval
        self.requests = []
        self.cpu_samples = []
        self.dropped_requests = 0
        self.dropped_samples = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None

    def record(self, operation, client_id, started, elapsed_ms, status):
        with self.lock:
            if len(self.requests) >= self.request_limit:
                self.dropped_requests += 1
                return
            self.requests.append({"operation": operation, "client_id": client_id,
                                  "started": started, "elapsed_ms": elapsed_ms,
                                  "status": status if type(status) is int else None})

    def sample(self):
        started = time.perf_counter()
        sample = {"started": started}
        try:
            sample.update(host_cpu=observe_host_cpu(),
                          host_pressure=read_values(Path("/proc"), ("pressure/cpu",)))
        except Exception as error:
            sample["capture_error"] = type(error).__name__
        sample["finished"] = time.perf_counter()
        with self.lock:
            if len(self.cpu_samples) >= self.sample_limit:
                self.dropped_samples += 1
            else:
                self.cpu_samples.append(sample)

    def start(self):
        if self.thread is not None or self.stop_event.is_set():
            raise ValueError("timeline already started")
        self.sample()

        def run():
            while not self.stop_event.wait(self.interval):
                self.sample()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        already_stopped = self.stop_event.is_set()
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()
            if not already_stopped:
                self.sample()

    def snapshot(self):
        with self.lock:
            return {"diagnostic_only": True, "acceptance_established": False,
                    "clock": "time.perf_counter seconds in the load-generator process",
                    "scope": "request durations and host-wide sampled counters; correlation is not causality",
                    "request_limit": self.request_limit, "sample_limit": self.sample_limit,
                    "sample_interval_seconds": self.interval,
                    "dropped_requests": self.dropped_requests, "dropped_samples": self.dropped_samples,
                    "requests": list(self.requests), "cpu_samples": list(self.cpu_samples)}
