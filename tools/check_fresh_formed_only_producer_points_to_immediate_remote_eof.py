#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(captures):
    stats = {
        'tcp_total': 0,
        'follow_up_count': 0,
        'remote_eof_count': 0,
        'idle_timeout_count': 0,
        'keepalive_total': 0,
        'follow_up_actions': {},
    }
    for capture in captures:
        first = capture.get('first_frame') or {}
        if first.get('action_hint') != 'internal:tcp/handshake':
            continue
        stats['tcp_total'] += 1
        if capture.get('follow_up_frame'):
            stats['follow_up_count'] += 1
            action = (capture.get('follow_up_frame') or {}).get('action_hint')
            stats['follow_up_actions'][action] = stats['follow_up_actions'].get(action, 0) + 1
        if capture.get('first_post_response_event') == 'remote_eof':
            stats['remote_eof_count'] += 1
        if capture.get('first_post_response_event') == 'idle_timeout':
            stats['idle_timeout_count'] += 1
        stats['keepalive_total'] += capture.get('proactive_keepalive_count', 0)
    return stats


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_fresh_formed_only_producer_points_to_immediate_remote_eof.py OLD_CAPTURE CURRENT_CAPTURE')
    old_stats = summarize(load(sys.argv[1]))
    current_stats = summarize(load(sys.argv[2]))
    result = 'inconclusive'
    if (
        old_stats['follow_up_count'] > 0
        and current_stats['follow_up_count'] == 0
        and current_stats['remote_eof_count'] == current_stats['tcp_total']
        and current_stats['keepalive_total'] == 0
    ):
        result = 'fresh_formed_only_producer_currently_points_to_immediate_remote_eof_after_tcp_handshake_response_before_any_followup'
    print(json.dumps({
        'old': old_stats,
        'current': current_stats,
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
