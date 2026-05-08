#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_publication_close_is_more_direct_than_pre_vote_dwell.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    counts = collections.Counter(
        (capture.get("first_frame") or {}).get("action_hint")
        for capture in report.get("steelsearch_transport_capture") or []
    )

    result = {
        "report_path": str(report_path),
        "request_pre_vote_count": counts.get("internal:cluster/request_pre_vote", 0),
        "start_join_count": counts.get("internal:cluster/coordination/start_join", 0),
        "publish_state_count": counts.get("internal:cluster/coordination/publish_state", 0),
        "commit_state_count": counts.get("internal:cluster/coordination/commit_state", 0),
        "follower_check_count": counts.get(
            "internal:coordination/fault_detection/follower_check", 0
        ),
        "result": (
            "publication_same_tick_close_is_more_direct_than_pre_vote_dwell_because_progress_reaches_publish_state_but_not_commit_state"
            if counts.get("internal:cluster/request_pre_vote", 0) > 0
            and counts.get("internal:cluster/coordination/start_join", 0) > 0
            and counts.get("internal:cluster/coordination/publish_state", 0) > 0
            and counts.get("internal:cluster/coordination/commit_state", 0) == 0
            else "pre_vote_dwell_vs_publication_close_directness_not_resolved"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
