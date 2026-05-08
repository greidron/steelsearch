#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path

LATE_ACTIONS = {
    'internal:transport/handshake',
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:cluster/coordination/start_join',
    'internal:cluster/coordination/publish_state',
    'internal:coordination/fault_detection/follower_check',
}


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def action_counts(report):
    caps = report.get('steelsearch_transport_capture') or []
    return Counter((entry.get('first_frame') or {}).get('action_hint') for entry in caps)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_old_formed_vs_current_baseline_points_to_rust_runtime.py <old-formed-report.json> <current-baseline-report.json>', file=sys.stderr)
        return 2

    old_formed = load(sys.argv[1])
    current = load(sys.argv[2])
    old_actions = action_counts(old_formed)
    current_actions = action_counts(current)

    old_late = sum(old_actions.get(action, 0) for action in LATE_ACTIONS)
    current_late = sum(current_actions.get(action, 0) for action in LATE_ACTIONS)

    print(f"old_formed_membership={old_formed.get('membership_formed')}")
    print(f"current_membership={current.get('membership_formed')}")
    print(f"old_follow_up={old_formed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"current_follow_up={current.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"old_late_action_count={old_late}")
    print(f"current_late_action_count={current_late}")
    print(f"old_actions={dict(old_actions)}")
    print(f"current_actions={dict(current_actions)}")

    if (
        old_formed.get('membership_formed') is True
        and current.get('membership_formed') is False
        and old_formed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and current.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
        and old_late > 0
        and current_late == 0
        and current_actions.get('internal:tcp/handshake', 0) > 0
    ):
        print('result=remaining_non_overlay_regression_points_to_current_rust_post_tcp_handshake_runtime_branch_not_java_launch_or_overlay')
        return 0

    print('result=remaining_regression_candidate_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
