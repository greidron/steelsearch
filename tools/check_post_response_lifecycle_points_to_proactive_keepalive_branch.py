#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load_json(path):
    with open(path) as f:
        return json.load(f)


def summarize_tcp(entries):
    tcp = [e for e in entries if (e.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake']
    idle = [e for e in tcp if e.get('first_post_response_event') == 'idle_timeout']
    return {
        'tcp_total': len(tcp),
        'tcp_follow_up_count': sum(1 for e in tcp if e.get('follow_up_frame') is not None),
        'tcp_idle_timeout_count': len(idle),
        'tcp_idle_timeout_keepalive_total': sum((e.get('proactive_keepalive_count') or 0) for e in idle),
        'tcp_idle_timeout_keepalive_nonzero': sum(1 for e in idle if (e.get('proactive_keepalive_count') or 0) > 0),
    }


def extract_source_flags(text):
    m = re.search(
        r'if is_request && is_handshake \{([\s\S]*?)\n    \} else if is_request && action_hint\.as_deref\(\) == Some\("internal:transport/handshake"\)',
        text,
    )
    if not m:
        return []
    block = m.group(1)
    return re.findall(
        r'hold_transport_channel_open\([\s\S]*?,\s*(true|false),\s*&mut proactive_keepalive_sent_at_ms,',
        block,
    )


def main():
    if len(sys.argv) != 4:
        print('usage: check_post_response_lifecycle_points_to_proactive_keepalive_branch.py MAIN_RS OLD_CAPTURE CURRENT_CAPTURE', file=sys.stderr)
        return 2

    main_rs = Path(sys.argv[1])
    old_capture = Path(sys.argv[2])
    current_capture = Path(sys.argv[3])

    source_text = main_rs.read_text()
    source_flags = extract_source_flags(source_text)
    old = summarize_tcp(load_json(old_capture))
    current = summarize_tcp(load_json(current_capture))

    print(f'source_file={main_rs}')
    print(f'source_tcp_handshake_hold_open_keepalive_flags={source_flags}')
    print(f'old_capture={old_capture}')
    for k, v in old.items():
        print(f'old_{k}={v}')
    print(f'current_capture={current_capture}')
    for k, v in current.items():
        print(f'current_{k}={v}')

    if (
        source_flags == ['true', 'true']
        and old['tcp_follow_up_count'] > 0
        and old['tcp_idle_timeout_keepalive_total'] == 0
        and current['tcp_follow_up_count'] == 0
        and current['tcp_idle_timeout_count'] > 0
        and current['tcp_idle_timeout_keepalive_nonzero'] == current['tcp_idle_timeout_count']
    ):
        result = 'current_runtime_delta_points_more_directly_to_proactive_keepalive_enabled_no_followup_hold_open_branch_than_pre_first_frame_timeout'
    else:
        result = 'inconclusive'

    print(f'checker_result={result}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
