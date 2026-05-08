#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_report(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(report):
    captures = report.get('steelsearch_transport_capture') or []
    tcp_total = 0
    remote_eof = 0
    follow_up = 0
    for c in captures:
        ff = c.get('first_frame') or {}
        if ff.get('action_hint') != 'internal:tcp/handshake':
            continue
        tcp_total += 1
        if c.get('first_post_response_event') == 'remote_eof':
            remote_eof += 1
        if c.get('follow_up_frame'):
            follow_up += 1
    return {
        'membership_formed': report.get('membership_formed'),
        'failure_stage': report.get('failure_stage'),
        'observed_node_count': report.get('observed_node_count'),
        'tcp_total': tcp_total,
        'remote_eof_count': remote_eof,
        'follow_up_count': follow_up,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_skip_active_probes_does_not_restore_formed_handoff.py BASELINE_REPORT NO_ACTIVE_REPORT')
    baseline = summarize(load_report(sys.argv[1]))
    no_active = summarize(load_report(sys.argv[2]))
    result = 'inconclusive'
    if (
        baseline['membership_formed'] is False
        and no_active['membership_formed'] is False
        and baseline['follow_up_count'] == 0
        and no_active['follow_up_count'] == 0
    ):
        result = 'skipping_active_steelsearch_probes_does_not_restore_formed_handoff_or_followup'
    print(json.dumps({
        'baseline': baseline,
        'no_active': no_active,
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
