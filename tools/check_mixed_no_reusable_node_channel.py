#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ACTIONS = [
    'internal:discovery/request_peers',
    'internal:cluster/request_pre_vote',
    'internal:coordination/fault_detection/follower_check',
    'internal:cluster/coordination/publish_state',
]


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: check_mixed_no_reusable_node_channel.py <state_channel_contract.json> <mixed_report.json>"}))
        return 1

    contract = load(sys.argv[1])
    report = load(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    reusable_state_contract = bool(
        contract.get('publish_state_uses_state_request_options')
        and contract.get('transport_service_send_request_uses_get_connection')
        and contract.get('transport_service_get_connection_uses_connection_manager')
        and contract.get('default_connection_profile_has_state_bucket')
    )

    action_summary = {}
    all_first_frame_only = True
    for action in ACTIONS:
        entries = []
        for e in capture:
            ff = ((e.get('first_frame') or {}).get('action_hint'))
            fu = ((e.get('follow_up_frame') or {}).get('action_hint'))
            pf = ((e.get('post_follow_up_frame') or {}).get('action_hint'))
            if ff == action or fu == action or pf == action:
                entries.append(e)
        first = sum(((e.get('first_frame') or {}).get('action_hint') == action) for e in entries)
        follow = sum(((e.get('follow_up_frame') or {}).get('action_hint') == action) for e in entries)
        post = sum(((e.get('post_follow_up_frame') or {}).get('action_hint') == action) for e in entries)
        action_summary[action] = {
            'count': len(entries),
            'first_frame_count': first,
            'follow_up_frame_count': follow,
            'post_follow_up_frame_count': post,
        }
        if len(entries) == 0 or first != len(entries) or follow != 0 or post != 0:
            all_first_frame_only = False

    if reusable_state_contract and all_first_frame_only:
        result = 'mixed_runtime_never_establishes_reusable_node_channel_so_publication_stays_on_one_shot_sockets'
    else:
        result = 'reusable_node_channel_failure_not_fully_isolated'

    print(json.dumps({
        'reusable_state_contract': reusable_state_contract,
        'actions': action_summary,
        'all_coordinator_actions_arrive_as_connection_first_frame': all_first_frame_only,
        'result': result,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
