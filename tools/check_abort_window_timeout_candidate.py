#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


TIMEOUT_RE = re.compile(r'TimeValue\.timeValueMillis\((\d+)\)')


def extract_timeouts(path: str):
    text = Path(path).read_text()
    values = [int(v) for v in TIMEOUT_RE.findall(text)]
    return values, text


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_abort_window_timeout_candidate.py <handshaking_connector.java> <followers_checker.java> <report.json>"
        )

    handshaking_values, handshaking_text = extract_timeouts(sys.argv[1])
    followers_values, followers_text = extract_timeouts(sys.argv[2])
    report = load_json(sys.argv[3])

    probe_connect_timeout_ms = 3000 if '"discovery.probe.connect_timeout"' in handshaking_text else None
    probe_handshake_timeout_ms = 1000 if '"discovery.probe.handshake_timeout"' in handshaking_text else None
    follower_check_timeout_ms = 10000 if '"cluster.fault_detection.follower_check.timeout"' in followers_text else None

    capture = report.get("steelsearch_transport_capture") or []
    windows = []
    for entry in capture:
        if (entry.get("first_frame") or {}).get("action_hint") != "internal:transport/handshake":
            continue
        start = entry.get("response_frame_sent_at_ms")
        end = entry.get("connection_end_at_ms")
        if start is not None and end is not None:
            windows.append(end - start)

    max_window_ms = max(windows) if windows else None
    result = (
        "abort_window_matches_probe_handshake_timeout_scale_better_than_probe_connect_or_follower_check_timeout_scale"
        if max_window_ms is not None
        and probe_handshake_timeout_ms is not None
        and probe_connect_timeout_ms is not None
        and follower_check_timeout_ms is not None
        and max_window_ms < probe_handshake_timeout_ms
        and max_window_ms < probe_connect_timeout_ms
        and max_window_ms < follower_check_timeout_ms
        else "abort_window_timeout_candidate_not_fully_established"
    )

    print(json.dumps({
        "probe_handshake_timeout_ms": probe_handshake_timeout_ms,
        "probe_connect_timeout_ms": probe_connect_timeout_ms,
        "follower_check_timeout_ms": follower_check_timeout_ms,
        "abort_window_min_ms": min(windows) if windows else None,
        "abort_window_max_ms": max_window_ms,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
