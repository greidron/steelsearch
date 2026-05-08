#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_transport_handshake_channels_die_after_subsecond_idle_without_reuse.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())

    deltas = []
    follow_up_seen = 0
    post_follow_up_seen = 0
    remote_eof_count = 0
    for capture in report.get("steelsearch_transport_capture") or []:
        if (capture.get("first_frame") or {}).get("action_hint") != "internal:transport/handshake":
            continue
        if capture.get("follow_up_frame") is not None:
            follow_up_seen += 1
        if capture.get("post_follow_up_frame") is not None:
            post_follow_up_seen += 1
        if capture.get("connection_end") == "remote_eof":
            remote_eof_count += 1
        sent = capture.get("response_frame_sent_at_ms")
        end = capture.get("connection_end_at_ms")
        if isinstance(sent, int) and isinstance(end, int):
            deltas.append(end - sent)

    result = {
        "report_path": str(report_path),
        "transport_handshake_count": len(deltas),
        "follow_up_seen": follow_up_seen,
        "post_follow_up_seen": post_follow_up_seen,
        "remote_eof_count": remote_eof_count,
        "response_to_eof_gap_ms": {
            "min": min(deltas) if deltas else None,
            "median": statistics.median(deltas) if deltas else None,
            "max": max(deltas) if deltas else None,
        },
        "result": (
            "transport_handshake_channels_die_after_subsecond_idle_without_any_reuse"
            if deltas
            and follow_up_seen == 0
            and post_follow_up_seen == 0
            and remote_eof_count == len(deltas)
            and min(deltas) > 0
            and max(deltas) < 1000
            else "transport_handshake_channel_shape_not_resolved"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if deltas else 1


if __name__ == "__main__":
    raise SystemExit(main())
