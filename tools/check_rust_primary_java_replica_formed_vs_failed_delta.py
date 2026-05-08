#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def action_counts(captures):
    return Counter((entry.get('first_frame') or {}).get('action_hint') for entry in captures)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            'usage: check_rust_primary_java_replica_formed_vs_failed_delta.py <formed-report.json> <failed-report.json>',
            file=sys.stderr,
        )
        return 2

    formed = load(sys.argv[1])
    failed = load(sys.argv[2])

    formed_caps = formed.get('steelsearch_transport_capture') or []
    failed_caps = failed.get('steelsearch_transport_capture') or []
    formed_actions = action_counts(formed_caps)
    failed_actions = action_counts(failed_caps)

    formed_follow_up = sum(1 for entry in formed_caps if entry.get('follow_up_frame'))
    failed_follow_up = sum(1 for entry in failed_caps if entry.get('follow_up_frame'))

    print(f"formed_membership={formed.get('membership_formed')}")
    print(f"failed_membership={failed.get('membership_formed')}")
    print(f"formed_failure_stage={formed.get('failure_stage')}")
    print(f"failed_failure_stage={failed.get('failure_stage')}")
    print(f"formed_follow_up_observed={formed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"failed_follow_up_observed={failed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"formed_capture_count={len(formed_caps)}")
    print(f"failed_capture_count={len(failed_caps)}")
    print(f"formed_follow_up_frames={formed_follow_up}")
    print(f"failed_follow_up_frames={failed_follow_up}")
    print(f"formed_actions={dict(formed_actions)}")
    print(f"failed_actions={dict(failed_actions)}")

    formed_has_late_actions = any(
        formed_actions.get(action, 0) > 0
        for action in (
            'internal:transport/handshake',
            'internal:discovery/request_peers',
            'internal:cluster/request_pre_vote',
            'internal:cluster/coordination/start_join',
            'internal:cluster/coordination/publish_state',
            'internal:coordination/fault_detection/follower_check',
        )
    )
    failed_tcp_only = set(failed_actions.keys()) <= {None, 'internal:tcp/handshake'} and failed_actions.get('internal:tcp/handshake', 0) > 0

    if (
        formed.get('membership_formed') is True
        and failed.get('membership_formed') is False
        and formed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and failed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
        and formed_has_late_actions
        and failed_tcp_only
    ):
        print('result=formed_run_reaches_follow_up_actions_but_current_failed_run_stalls_at_tcp_handshake_only')
        return 0

    print('result=formed_vs_failed_delta_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
