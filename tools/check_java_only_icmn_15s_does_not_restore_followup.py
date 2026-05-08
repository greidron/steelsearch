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
        'membership_formed': report.get('membership_formed'),
        'observed_node_count': report.get('observed_node_count'),
        'failure_stage': report.get('failure_stage'),
        'tcp_total': tcp_total,
        'follow_up_count': follow_up,
        'remote_eof_count': remote_eof,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_java_only_icmn_15s_does_not_restore_followup.py BASE5S LIVE15S')
    base = summarize(load(sys.argv[1]))
    cur = summarize(load(sys.argv[2]))
    result = 'inconclusive'
    if (
        base['membership_formed'] is False and cur['membership_formed'] is False and
        base['observed_node_count'] == 1 and cur['observed_node_count'] == 1 and
        base['follow_up_count'] == 0 and cur['follow_up_count'] == 0
    ):
        result = 'raising_pre_first_frame_timeout_to_15000ms_on_java_only_icmn_does_not_restore_followup_or_formed_handoff'
    print(json.dumps({'baseline_java_only_5s': base, 'current_java_only_15s': cur, 'checker_result': result}, indent=2))


if __name__ == '__main__':
    main()
