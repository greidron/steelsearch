#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(report):
    caps = report.get('steelsearch_transport_capture') or []
    tcp = fu = eof = 0
    for c in caps:
        ff = c.get('first_frame') or {}
        if ff.get('action_hint') != 'internal:tcp/handshake':
            continue
        tcp += 1
        if c.get('follow_up_frame'):
            fu += 1
        if c.get('first_post_response_event') == 'remote_eof':
            eof += 1
    return {
        'membership_formed': report.get('membership_formed'),
        'observed_node_count': report.get('observed_node_count'),
        'failure_stage': report.get('failure_stage'),
        'tcp_total': tcp,
        'follow_up_count': fu,
        'remote_eof_count': eof,
        'transport_accepting_connections': (report.get('markers') or {}).get('steelsearch_transport_accepting_connections'),
        'transport_handshake_accepted': (report.get('markers') or {}).get('steelsearch_transport_handshake_accepted'),
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: check_same_one_node_candidate_matrix_practical_stop.py REPORT...')
    reports = {Path(p).name: summarize(load(p)) for p in sys.argv[1:]}
    all_no_followup = all(r['follow_up_count'] == 0 for r in reports.values())
    all_unformed = all(r['membership_formed'] is False for r in reports.values())
    all_one_or_worse = all((r['observed_node_count'] or 0) <= 1 for r in reports.values())
    result = 'inconclusive'
    if all_no_followup and all_unformed and all_one_or_worse:
        result = 'same_one_node_restore_candidate_matrix_reached_practical_stop_without_restoring_followup_or_formed_handoff'
    print(json.dumps({'reports': reports, 'checker_result': result}, indent=2))


if __name__ == '__main__':
    main()
