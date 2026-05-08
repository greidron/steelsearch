#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

TARGETS = [
    'internal:cluster/coordination/publish_state',
    'internal:discovery/request_peers',
    'internal:cluster/coordination/start_join',
    'internal:cluster/request_pre_vote',
    'internal:coordination/fault_detection/follower_check',
]


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_publish_state_response_is_late_vs_other_native_actions.py <probe_report_json> <main_rs>', file=sys.stderr)
        return 2

    report = json.loads(Path(sys.argv[1]).read_text())
    main_rs = Path(sys.argv[2]).read_text(errors='replace')
    caps = report.get('steelsearch_transport_capture', [])

    per_action: dict[str, list[int]] = {k: [] for k in TARGETS}
    per_tail: dict[str, list[int]] = {k: [] for k in TARGETS}
    publish_state_end_equals_response = False

    for cap in caps:
        frame = cap.get('first_frame') or {}
        action = frame.get('action_hint')
        if action not in per_action:
            continue
        started = cap.get('connection_started_at_ms')
        responded = cap.get('response_frame_sent_at_ms')
        ended = cap.get('connection_end_at_ms')
        if started is None or responded is None:
            continue
        per_action[action].append(responded - started)
        if ended is not None:
            per_tail[action].append(ended - responded)
        if action == 'internal:cluster/coordination/publish_state' and ended == responded:
            publish_state_end_equals_response = True

    for action in TARGETS:
        vals = per_action[action]
        tails = per_tail[action]
        if vals:
            print(
                f'{action}\tcount={len(vals)}\tresp_ms_min={min(vals)}\tresp_ms_med={statistics.median(vals)}\tresp_ms_max={max(vals)}'
                + (f'\ttail_ms_min={min(tails)}\ttail_ms_med={statistics.median(tails)}\ttail_ms_max={max(tails)}' if tails else '')
            )
        else:
            print(f'{action}\tcount=0')

    source_uses_parse_script = 'tools/parse_java_publish_state_request.sh' in main_rs
    source_uses_build_script = 'tools/build_java_publish_with_join_response.sh' in main_rs
    print(f'source_uses_parse_publish_state_script={source_uses_parse_script}')
    print(f'source_uses_build_publish_response_script={source_uses_build_script}')

    publish_vals = per_action['internal:cluster/coordination/publish_state']
    request_vals = per_action['internal:discovery/request_peers']
    start_join_vals = per_action['internal:cluster/coordination/start_join']
    follower_vals = per_action['internal:coordination/fault_detection/follower_check']

    if (
        publish_vals
        and request_vals
        and start_join_vals
        and follower_vals
        and min(publish_vals) >= 10_000
        and statistics.median(request_vals) < 500
        and statistics.median(follower_vals) < 500
        and publish_state_end_equals_response
        and source_uses_parse_script
        and source_uses_build_script
    ):
        print('result=publish_state_response_is_late_on_rust_side_and_points_to_shell_helper_path_before_java_transport_failure')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
