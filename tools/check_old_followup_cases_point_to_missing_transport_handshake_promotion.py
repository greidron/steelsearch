#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def old_summary(capture):
    tcp = [e for e in capture if (e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake']
    follow = [e for e in tcp if e.get('follow_up_frame') is not None]
    actions = sorted({(e.get('follow_up_frame') or {}).get('action_hint') for e in follow})
    deltas = []
    for e in follow:
        resp = e.get('response_frame_sent_at_ms')
        foll = e.get('follow_up_frame_received_at_ms')
        if resp is not None and foll is not None:
            deltas.append(foll - resp)
    return {
        'tcp_total': len(tcp),
        'follow_up_count': len(follow),
        'follow_up_actions': actions,
        'follow_up_delta_min_ms': min(deltas) if deltas else None,
        'follow_up_delta_max_ms': max(deltas) if deltas else None,
    }


def current_summary(report, stdout_text):
    markers = report.get('markers') or {}
    transport_send = len(re.findall(r'action=internal:transport/handshake\b', stdout_text))
    tcp_send = len(re.findall(r'action=internal:tcp/handshake\b', stdout_text))
    return {
        'membership_formed': report.get('membership_formed'),
        'follow_up_observed': markers.get('steelsearch_transport_follow_up_observed'),
        'transport_handshake_send_meta': transport_send,
        'tcp_handshake_send_meta': tcp_send,
    }


def main():
    if len(sys.argv) != 4:
        print('usage: check_old_followup_cases_point_to_missing_transport_handshake_promotion.py OLD_CAPTURE CURRENT_REPORT CURRENT_STDOUT', file=sys.stderr)
        return 2
    old_capture_path = Path(sys.argv[1])
    current_report_path = Path(sys.argv[2])
    current_stdout_path = Path(sys.argv[3])

    old = old_summary(load_json(old_capture_path))
    current = current_summary(load_json(current_report_path), current_stdout_path.read_text())

    print(f'old_capture={old_capture_path}')
    for k, v in old.items():
        print(f'old_{k}={v}')
    print(f'current_report={current_report_path}')
    for k, v in current.items():
        print(f'current_{k}={v}')

    if (
        old['follow_up_count'] > 0
        and old['follow_up_actions'] == ['internal:transport/handshake']
        and old['follow_up_delta_max_ms'] is not None
        and old['follow_up_delta_max_ms'] <= 400
        and current['transport_handshake_send_meta'] == 0
        and current['tcp_handshake_send_meta'] > 0
        and current['follow_up_observed'] is False
    ):
        result = 'old_formed_followup_path_is_immediate_transport_handshake_promotion_and_current_tree_never_enters_that_java_path'
    else:
        result = 'inconclusive'
    print(f'checker_result={result}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
