#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def collect_deltas(report: dict, action: str) -> list[int]:
    deltas = []
    for capture in report.get("steelsearch_transport_capture") or []:
        if (capture.get("first_frame") or {}).get("action_hint") != action:
            continue
        sent = capture.get("response_frame_sent_at_ms")
        end = capture.get("connection_end_at_ms")
        if isinstance(sent, int) and isinstance(end, int):
            deltas.append(end - sent)
    return deltas


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_transport_handshake_idle_dwell_matches_pre_vote_timer_band.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())

    handshake = collect_deltas(report, "internal:transport/handshake")
    pre_vote = collect_deltas(report, "internal:cluster/request_pre_vote")
    handshake_median = statistics.median(handshake)
    pre_vote_median = statistics.median(pre_vote)
    median_delta = handshake_median - pre_vote_median

    result = {
        "report_path": str(report_path),
        "transport_handshake_gap_ms": {
            "count": len(handshake),
            "min": min(handshake),
            "median": handshake_median,
            "max": max(handshake),
        },
        "request_pre_vote_gap_ms": {
            "count": len(pre_vote),
            "min": min(pre_vote),
            "median": pre_vote_median,
            "max": max(pre_vote),
        },
        "median_delta_ms": median_delta,
        "result": (
            "transport_handshake_idle_dwell_is_in_the_same_subsecond_timer_band_as_request_pre_vote_not_a_distinct_identity_only_close"
            if abs(median_delta) < 150
            else "transport_handshake_idle_dwell_looks_distinct_from_request_pre_vote"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
