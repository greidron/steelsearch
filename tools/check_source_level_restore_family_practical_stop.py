#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load_json(path):
    return json.loads(Path(path).read_text())

def summarize_report(path):
    report = load_json(path)
    capture = report.get('steelsearch_transport_capture') or []
    tcp = [c for c in capture if (c.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake']
    return {
        'membership_formed': report.get('membership_formed'),
        'observed_node_count': report.get('observed_node_count'),
        'failure_stage': report.get('failure_stage'),
        'tcp_total': len(tcp),
        'follow_up_count': sum(1 for c in tcp if c.get('follow_up_frame') is not None),
        'remote_eof_count': sum(1 for c in tcp if c.get('connection_end') == 'remote_eof'),
    }

def marker_count(path, needle):
    p = Path(path)
    if not p.exists():
        return 0
    return p.read_text(errors='ignore').count(needle)

def main():
    if len(sys.argv) != 8:
        print('usage: check_source_level_restore_family_practical_stop.py BASELINE_LIVE DIRECT_HOLD LIVE_PING FORCE_TIMEOUT FORCE_EXEC FORCE_IMMEDIATE STARVATION_STDOUT')
        return 2
    baseline = summarize_report(sys.argv[1])
    candidates = {
        'direct_hold_open': summarize_report(sys.argv[2]),
        'immediate_ping': summarize_report(sys.argv[3]),
        'force_timeout_success': summarize_report(sys.argv[4]),
        'force_exec_listener_success': summarize_report(sys.argv[5]),
        'force_immediate_success': summarize_report(sys.argv[6]),
    }
    starvation_stdout = Path(sys.argv[7]).read_text(errors='ignore')
    starvation = {
        'response_read': starvation_stdout.count('steelsearch_transport_handshaker_stage=response_read'),
        'handle_response': starvation_stdout.count('steelsearch_transport_handshaker_stage=handle_response'),
        'channel_read': starvation_stdout.count('steelsearch_netty4_message_channel_stage=channel_read'),
        'handshake_timeout': starvation_stdout.count('handshake_timeout['),
        'explicit_local_close': starvation_stdout.count('hint=explicitLocalClose'),
    }
    unchanged_family = all(
        cand['membership_formed'] is False
        and cand['observed_node_count'] == baseline['observed_node_count']
        and cand['follow_up_count'] == baseline['follow_up_count']
        for cand in candidates.values()
    )
    result = 'source_level_restore_family_still_has_meaningful_divergence'
    if unchanged_family and starvation['response_read'] == 0 and starvation['handle_response'] == 0:
        result = 'source_level_restore_family_matches_existing_full_read_starvation_practical_stop'
    print(json.dumps({
        'baseline': baseline,
        'candidates': candidates,
        'starvation': starvation,
        'checker_result': result,
    }, indent=2))

if __name__ == '__main__':
    raise SystemExit(main())
