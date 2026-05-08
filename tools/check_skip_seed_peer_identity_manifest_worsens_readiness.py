#!/usr/bin/env python3
import json, sys
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def summarize(r):
    return {
        'membership_formed': r.get('membership_formed'),
        'observed_node_count': r.get('observed_node_count'),
        'bootstrap_uses_seed_peer_identity': (r.get('markers') or {}).get('steelsearch_bootstrap_uses_seed_peer_identity'),
        'native_transport_join_participation': (r.get('markers') or {}).get('steelsearch_native_transport_join_participation'),
        'transport_accepting_connections': (r.get('markers') or {}).get('steelsearch_transport_accepting_connections'),
        'transport_handshake_accepted': (r.get('markers') or {}).get('steelsearch_transport_handshake_accepted'),
    }
base=summarize(load(sys.argv[1]))
cur=summarize(load(sys.argv[2]))
result='inconclusive'
if base['observed_node_count']==1 and cur['observed_node_count']==1 and base['transport_accepting_connections'] is True and cur['transport_accepting_connections'] is False:
    result='skipping_seed_peer_identity_manifest_worsens_transport_readiness_and_is_not_a_restore_candidate'
print(json.dumps({'baseline_java_only': base, 'current_skip_manifest': cur, 'checker_result': result}, indent=2))
