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
    if len(sys.argv) != 4:
        print(
            'usage: check_lower_transport_source_is_nodechannels_close_fanout.py '
            '<TcpTransport.java> <ClusterConnectionManager.java> <report.json>',
            file=sys.stderr,
        )
        return 2

    tcp_transport = Path(sys.argv[1]).read_text()
    cluster_src = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_any_channel_close_fans_out = 'ch.addCloseListener(ActionListener.wrap(nodeChannels::close));' in tcp_transport
    source_nodechannels_close_closes_all = 'CloseableChannel.closeChannels(channels, block);' in tcp_transport
    source_cluster_manager_only_observes_close_signal = (
        'connectedNodes.remove(node, finalConnection);' in cluster_src
        and 'connectionListener.onNodeDisconnected(node, conn);' in cluster_src
    )

    rows = []
    for row in report.get('steelsearch_transport_capture', []) or []:
        first = row.get('first_frame')
        action = first.get('action_hint') if isinstance(first, dict) else first
        if action not in {
            'internal:transport/handshake',
            'internal:discovery/request_peers',
            'internal:coordination/fault_detection/follower_check',
            'internal:cluster/coordination/publish_state',
        }:
            continue
        if row.get('first_post_response_event') != 'remote_eof':
            continue
        start = row.get('connection_started_at_ms')
        end = row.get('connection_end_at_ms')
        if start is None or end is None:
            continue
        rows.append({'action': action, 'start': start, 'end': end})

    burst_count = 0
    nearly_simultaneous_burst_count = 0
    for cluster in cluster_rows(rows, 5):
        actions = {r['action'] for r in cluster}
        if 'internal:transport/handshake' not in actions:
            continue
        if not ({'internal:discovery/request_peers', 'internal:coordination/fault_detection/follower_check', 'internal:cluster/coordination/publish_state'} & actions):
            continue
        burst_count += 1
        ends = [r['end'] for r in cluster]
        if max(ends) - min(ends) <= 25:
            nearly_simultaneous_burst_count += 1

    if (
        source_any_channel_close_fans_out
        and source_nodechannels_close_closes_all
        and source_cluster_manager_only_observes_close_signal
        and nearly_simultaneous_burst_count > 0
    ):
        result = (
            'lower_transport_source_of_the_upstream_close_signal_is_best_explained_as_tcptransport_nodechannels_close_fanout_'
            'rather_than_as_a_higher_level_followers_checker_or_coordinator_decision'
        )
    else:
        result = 'lower_transport_source_inconclusive'

    print(json.dumps({
        'source_any_channel_close_fans_out': source_any_channel_close_fans_out,
        'source_nodechannels_close_closes_all': source_nodechannels_close_closes_all,
        'source_cluster_manager_only_observes_close_signal': source_cluster_manager_only_observes_close_signal,
        'burst_count': burst_count,
        'nearly_simultaneous_burst_count': nearly_simultaneous_burst_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
