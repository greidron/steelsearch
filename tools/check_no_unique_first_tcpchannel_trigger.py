#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def cluster_rows(rows, tolerance_ms):
    clusters = []
    for row in sorted(rows, key=lambda r: r['start']):
        if not clusters or row['start'] - clusters[-1][-1]['start'] > tolerance_ms:
            clusters.append([row])
        else:
            clusters[-1].append(row)
    return clusters


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_no_unique_first_tcpchannel_trigger.py <report.json>', file=sys.stderr)
        return 2

    report = json.loads(Path(sys.argv[1]).read_text())
    allowed = {
        'internal:transport/handshake',
        'internal:discovery/request_peers',
        'internal:coordination/fault_detection/follower_check',
        'internal:cluster/coordination/publish_state',
    }
    rows = []
    for row in report.get('steelsearch_transport_capture', []) or []:
        first = row.get('first_frame')
        action = first.get('action_hint') if isinstance(first, dict) else first
        if action not in allowed:
            continue
        if row.get('first_post_response_event') != 'remote_eof':
            continue
        start = row.get('connection_started_at_ms')
        end = row.get('connection_end_at_ms')
        if start is None or end is None:
            continue
        rows.append({'action': action, 'start': start, 'end': end})

    burst_count = 0
    unique_earliest_counts = {}
    ambiguous_burst_count = 0

    for cluster in cluster_rows(rows, 5):
        if len(cluster) < 2:
            continue
        burst_count += 1
        min_end = min(r['end'] for r in cluster)
        earliest = sorted({r['action'] for r in cluster if r['end'] - min_end <= 10})
        if len(earliest) == 1:
            unique_earliest_counts[earliest[0]] = unique_earliest_counts.get(earliest[0], 0) + 1
        else:
            ambiguous_burst_count += 1

    total_unique = sum(unique_earliest_counts.values())
    dominant_action = None
    dominant_count = 0
    if unique_earliest_counts:
        dominant_action, dominant_count = max(unique_earliest_counts.items(), key=lambda kv: kv[1])

    if burst_count > 0 and ambiguous_burst_count >= total_unique:
        result = (
            'current_artifact_does_not_identify_a_unique_individual_tcpchannel_as_the_first_nodechannels_fanout_trigger_'
            'and_the_first_close_remains_ambiguous_within_near_simultaneous_bursts'
        )
    else:
        result = 'unique_first_tcpchannel_candidate_exists'

    print(json.dumps({
        'burst_count': burst_count,
        'ambiguous_burst_count': ambiguous_burst_count,
        'unique_earliest_counts': unique_earliest_counts,
        'dominant_unique_earliest_action': dominant_action,
        'dominant_unique_earliest_count': dominant_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
