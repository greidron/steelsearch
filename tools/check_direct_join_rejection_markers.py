#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_direct_join_rejection_markers.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
text = report.get('opensearch_stdout', '') + '\n' + report.get('opensearch_stderr', '')
patterns = {
    'term_mismatch': r'steelsearch_handleJoin_rejection_class=term_mismatch',
    'term_not_incremented_after_reboot': r'steelsearch_handleJoin_rejection_class=term_not_incremented_after_reboot',
    'better_last_accepted_term': r'steelsearch_handleJoin_rejection_class=better_last_accepted_term',
    'better_last_accepted_version': r'steelsearch_handleJoin_rejection_class=better_last_accepted_version',
    'missing_initial_configuration': r'steelsearch_handleJoin_rejection_class=missing_initial_configuration',
    'publication_missing_join': r'steelsearch_publication_response_class=missing_join',
    'publication_transport_failure': r'steelsearch_publication_response_class=transport_failure',
}
counts = {k: len(re.findall(v, text)) for k, v in patterns.items()}
for k, v in counts.items():
    print(f'{k}={v}')
print(f"failure_stage={report.get('failure_stage')}")
print(f"blocker_class={report.get('blocker_class')}")
nonzero = {k: v for k, v in counts.items() if v > 0}
if nonzero:
    winner = max(nonzero.items(), key=lambda kv: kv[1])
    print(f'winning_marker={winner[0]}')
    print('result=direct_join_or_publication_rejection_marker_surfaced')
else:
    print('result=no_direct_join_or_publication_rejection_marker_surfaced')
