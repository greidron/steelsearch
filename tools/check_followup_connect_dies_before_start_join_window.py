#!/usr/bin/env python3
import collections
import json
import statistics
import sys
from pathlib import Path


def ms_stats(values):
    if not values:
        return None
    return {
        'min': min(values),
        'median': statistics.median(values),
        'max': max(values),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_followup_connect_dies_before_start_join_window.py <mixed_artifact.json>', file=sys.stderr)
        return 2

    report_path = Path(sys.argv[1])
    with report_path.open() as f:
        data = json.load(f)

    capture = data['steelsearch_transport_capture']
    full_connect = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    start_join = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:cluster/coordination/start_join'
    ]

    live_counts = []
    prior_eof_gaps = []
    for action in start_join:
        action_start = action['connection_started_at_ms']
        live = [
            channel for channel in full_connect
            if channel['connection_started_at_ms'] <= action_start < channel['connection_end_at_ms']
        ]
        live_counts.append(len(live))
        earlier = [channel for channel in full_connect if channel['connection_end_at_ms'] <= action_start]
        if earlier:
            prior = max(earlier, key=lambda item: item['connection_end_at_ms'])
            prior_eof_gaps.append(action_start - prior['connection_end_at_ms'])

    live_counter = collections.Counter(live_counts)
    result = {
        'transport_handshake_count': len(full_connect),
        'start_join_count': len(start_join),
        'live_full_connect_count_at_start_join_open': dict(sorted(live_counter.items())),
        'start_join_with_live_full_connect_count': sum(1 for count in live_counts if count > 0),
        'prior_full_connect_eof_to_start_join_gap_ms': ms_stats(prior_eof_gaps),
        'result': 'start_join_opens_fresh_even_while_a_live_full_connect_candidate_often_exists'
        if len(full_connect) > 0 and len(start_join) > 0 and sum(1 for count in live_counts if count > 0) > 0
        else 'no_live_full_connect_candidate_observed_at_start_join_open',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
