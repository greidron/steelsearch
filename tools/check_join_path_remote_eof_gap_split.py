#!/usr/bin/env python3
import collections
import json
import statistics
import sys
from pathlib import Path


TARGETS = (
    "internal:cluster/request_pre_vote",
    "internal:cluster/coordination/start_join",
    "internal:cluster/coordination/publish_state",
)


def summarize(values: list[int]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_join_path_remote_eof_gap_split.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())

    gaps = collections.defaultdict(list)
    for capture in report.get("steelsearch_transport_capture") or []:
        action = (capture.get("first_frame") or {}).get("action_hint")
        if action not in TARGETS:
            continue
        sent = capture.get("response_frame_sent_at_ms")
        end = capture.get("connection_end_at_ms")
        if isinstance(sent, int) and isinstance(end, int):
            gaps[action].append(end - sent)

    result = {
        "report_path": str(report_path),
        "gap_summary_ms": {
            action: summarize(values) for action, values in gaps.items() if values
        },
        "result": (
            "join_path_remote_eof_gap_split_is_pre_vote_dwell_vs_same_tick_start_join_publish_state_close"
            if gaps.get("internal:cluster/request_pre_vote")
            and gaps.get("internal:cluster/coordination/start_join")
            and max(gaps["internal:cluster/coordination/start_join"]) == 0
            and max(gaps.get("internal:cluster/coordination/publish_state", [0])) == 0
            and min(gaps["internal:cluster/request_pre_vote"]) > 0
            else "join_path_remote_eof_gap_split_not_observed"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
