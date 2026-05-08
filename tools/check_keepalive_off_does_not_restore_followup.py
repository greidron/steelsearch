#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def summarize(report):
    capture = report['steelsearch_transport_capture']
    tcp = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake']
    return {
        'membership_formed': report.get('membership_formed'),
        'failure_stage': report.get('failure_stage'),
        'follow_up_observed': (report.get('markers') or {}).get('steelsearch_transport_follow_up_observed'),
        'tcp_total': len(tcp),
        'tcp_follow_up_count': sum(1 for e in tcp if e.get('follow_up_frame') is not None),
        'tcp_remote_eof_count': sum(1 for e in tcp if e.get('first_post_response_event') == 'remote_eof'),
        'tcp_idle_timeout_count': sum(1 for e in tcp if e.get('first_post_response_event') == 'idle_timeout'),
        'tcp_keepalive_total': sum((e.get('proactive_keepalive_count') or 0) for e in tcp),
    }


def main():
    if len(sys.argv) != 3:
        print('usage: check_keepalive_off_does_not_restore_followup.py BASELINE_REPORT PATCHED_REPORT', file=sys.stderr)
        return 2
    baseline_path = Path(sys.argv[1])
    patched_path = Path(sys.argv[2])
    baseline = summarize(load_json(baseline_path))
    patched = summarize(load_json(patched_path))
    print(f'baseline_report={baseline_path}')
    for k, v in baseline.items():
        print(f'baseline_{k}={v}')
    print(f'patched_report={patched_path}')
    for k, v in patched.items():
        print(f'patched_{k}={v}')

    if (
        baseline['membership_formed'] is False
        and patched['membership_formed'] is False
        and baseline['follow_up_observed'] is False
        and patched['follow_up_observed'] is False
        and baseline['tcp_follow_up_count'] == 0
        and patched['tcp_follow_up_count'] == 0
        and baseline['tcp_keepalive_total'] > 0
        and patched['tcp_keepalive_total'] == 0
    ):
        result = 'disabling_tcp_no_followup_proactive_keepalive_changes_lifecycle_shape_but_does_not_restore_followup_or_membership'
    else:
        result = 'inconclusive'
    print(f'checker_result={result}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
