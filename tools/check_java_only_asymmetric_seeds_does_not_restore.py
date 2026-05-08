#!/usr/bin/env python3
import json, sys
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def summarize(r):
    caps=r.get('steelsearch_transport_capture') or []
    tcp=fu=eof=0
    for c in caps:
        ff=(c.get('first_frame') or {})
        if ff.get('action_hint')!='internal:tcp/handshake':
            continue
        tcp += 1
        if c.get('follow_up_frame'):
            fu += 1
        if c.get('first_post_response_event')=='remote_eof':
            eof += 1
    return {'membership_formed': r.get('membership_formed'), 'observed_node_count': r.get('observed_node_count'), 'failure_stage': r.get('failure_stage'), 'tcp_total': tcp, 'follow_up_count': fu, 'remote_eof_count': eof}

base=summarize(load(sys.argv[1]))
cur=summarize(load(sys.argv[2]))
result='inconclusive'
if base['membership_formed'] is False and cur['membership_formed'] is False and base['observed_node_count']==1 and cur['observed_node_count']==1 and base['follow_up_count']==0 and cur['follow_up_count']==0:
    result='java_only_asymmetric_seeds_candidate_does_not_restore_followup_or_formed_handoff'
print(json.dumps({'baseline_java_only': base, 'current_java_only_asymmetric': cur, 'checker_result': result}, indent=2))
