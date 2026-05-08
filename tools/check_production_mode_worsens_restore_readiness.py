#!/usr/bin/env python3
import json, sys
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def summarize(r):
    return {
        'membership_formed': r.get('membership_formed'),
        'observed_node_count': r.get('observed_node_count'),
        'failure_stage': r.get('failure_stage'),
        'blocker_class': r.get('blocker_class'),
        'transport_accepting_connections': (r.get('markers') or {}).get('steelsearch_transport_accepting_connections'),
        'transport_handshake_accepted': (r.get('markers') or {}).get('steelsearch_transport_handshake_accepted'),
        'production_mode_blocked': (r.get('markers') or {}).get('steelsearch_production_mode_blocked'),
    }
base=summarize(load(sys.argv[1]))
cur=summarize(load(sys.argv[2]))
result='inconclusive'
if base['transport_accepting_connections'] is True and cur['transport_accepting_connections'] is False and cur['production_mode_blocked'] is True:
    result='forcing_production_mode_blocks_transport_readiness_and_is_not_a_restore_candidate'
print(json.dumps({'baseline_zero_node': base, 'current_production_mode': cur, 'checker_result': result}, indent=2))
