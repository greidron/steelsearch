#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_remote_eof_split_points_away_from_rust_side_timeout_branch.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = json.loads(Path(report["artifacts"]["steelsearch_transport_capture"]).read_text())
    main_rs = Path("/home/ubuntu/steelsearch/crates/os-node/src/main.rs").read_text()

    target_actions = {
        "internal:cluster/request_pre_vote",
        "internal:cluster/coordination/start_join",
        "internal:cluster/coordination/publish_state",
        "internal:coordination/fault_detection/follower_check",
    }

    end_counts = Counter()
    target_count = 0
    for item in capture:
        action = ((item.get("first_frame") or {}).get("action_hint"))
        if action in target_actions:
            target_count += 1
            end_counts[item.get("connection_end")] += 1

    has_long_hold_for_publish = "Some(\"internal:cluster/coordination/publish_state\")" in main_rs and "Duration::from_secs(20)" in main_rs
    has_long_hold_for_follower = "Some(\"internal:coordination/fault_detection/follower_check\")" in main_rs and "Duration::from_secs(20)" in main_rs
    has_idle_timeout_branch = "\"idle_timeout\"" in main_rs
    has_remote_eof_branch = "\"remote_eof\"" in main_rs

    result = {
        "work_dir": report.get("work_dir"),
        "target_action_connection_count": target_count,
        "connection_end_counts": dict(end_counts),
        "source_has_long_hold_for_publish": has_long_hold_for_publish,
        "source_has_long_hold_for_follower": has_long_hold_for_follower,
        "source_has_idle_timeout_branch": has_idle_timeout_branch,
        "source_has_remote_eof_branch": has_remote_eof_branch,
        "result": (
            "remote_eof_split_points_away_from_rust_side_timeout_or_active_close_branch"
            if target_count > 0
            and end_counts.get("remote_eof", 0) == target_count
            and end_counts.get("idle_timeout", 0) == 0
            and has_long_hold_for_publish
            and has_long_hold_for_follower
            and has_idle_timeout_branch
            and has_remote_eof_branch
            else "remote_eof_split_is_not_yet_isolated_from_rust_side_timeout_or_active_close_branch"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "remote_eof_split_points_away_from_rust_side_timeout_or_active_close_branch"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
