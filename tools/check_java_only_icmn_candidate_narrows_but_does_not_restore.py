#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(report):
    captures = report.get('steelsearch_transport_capture') or []
    tcp_total = 0
    follow_up = 0
    remote_eof = 0
    for c in captures:
        ff = c.get('first_frame') or {}
        if ff.get('action_hint') != 'internal:tcp/handshake':
            continue
        tcp_total += 1
        if c.get('follow_up_frame'):
            follow_up += 1
        if c.get('first_post_response_event') == 'remote_eof':
            remote_eof += 1
    return {
        'initial_cluster_manager_nodes': report.get('initial_cluster_manager_nodes'),
        'membership_formed': report.get('membership_formed'),
        'observed_node_count': report.get('observed_node_count'),
        'failure_stage': report.get('failure_stage'),
        'tcp_total': tcp_total,
        'follow_up_count': follow_up,
        'remote_eof_count': remote_eof,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_java_only_icmn_candidate_narrows_but_does_not_restore.py BASELINE CURRENT')
    baseline = summarize(load(sys.argv[1]))
    current = summarize(load(sys.argv[2]))
    result = 'inconclusive'
    if (
        baseline['membership_formed'] is False
        and current['membership_formed'] is False
        and current['observed_node_count'] > baseline['observed_node_count']
        and current['tcp_total'] < baseline['tcp_total']
        and current['follow_up_count'] == 0
    ):
        result = 'java_only_initial_cluster_manager_nodes_candidate_narrows_failure_shape_but_does_not_restore_formed_handoff'
    print(json.dumps({'baseline': baseline, 'current': current, 'checker_result': result}, indent=2))


if __name__ == '__main__':
    main()
