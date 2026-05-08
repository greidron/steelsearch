#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_join_rejection_log_surface.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
text = report.get('opensearch_stdout', '') + '\n' + report.get('opensearch_stderr', '')
counts = {
    'handleJoin_term_mismatch': len(re.findall(r'handleJoin: ignored join due to term mismatch', text)),
    'handleJoin_reboot': len(re.findall(r'handleJoin: ignored join as term was not incremented yet after reboot', text)),
    'handleJoin_better_term': len(re.findall(r'handleJoin: ignored join as joiner has a better last accepted term', text)),
    'handleJoin_better_version': len(re.findall(r'handleJoin: ignored join as joiner has a better last accepted version', text)),
    'handleJoin_initial_config': len(re.findall(r'handleJoin: rejecting join since this node has not received its initial configuration yet', text)),
    'handleJoin_added': len(re.findall(r'handleJoin: added join', text)),
    'publication_missing_join': len(re.findall(r'publish response from .* contained no join', text)),
    'failed_to_commit_cluster_state': len(re.findall(r'failed to commit cluster state', text)),
}
for key, value in counts.items():
    print(f'{key}={value}')
print(f"failure_stage={report.get('failure_stage')}")
print(f"blocker_class={report.get('blocker_class')}")

has_surface = any(v > 0 for k, v in counts.items() if k != 'failed_to_commit_cluster_state')
if has_surface:
    print('result=join_or_publication_rejection_reason_is_surfaced_in_probe_logs')
else:
    print('result=join_or_publication_rejection_reason_is_not_yet_surfaced_even_with_coordination_publication_loggers')
