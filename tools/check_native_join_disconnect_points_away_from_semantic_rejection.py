#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

obj = json.loads(Path(sys.argv[1]).read_text())
stdout = Path(obj['artifacts']['opensearch_stdout']).read_text(encoding='utf-8', errors='replace').splitlines()
patterns = {
    'handlejoin_entry': re.compile(r'steelsearch_handleJoin_entry'),
    'term_mismatch': re.compile(r'steelsearch_handleJoin_reject_term_mismatch'),
    'reboot_mismatch': re.compile(r'steelsearch_handleJoin_reject_term_not_incremented_after_reboot'),
    'better_term': re.compile(r'steelsearch_handleJoin_reject_better_last_accepted_term'),
    'better_version': re.compile(r'steelsearch_handleJoin_reject_better_last_accepted_version'),
    'missing_initial_config': re.compile(r'steelsearch_handleJoin_reject_missing_initial_configuration'),
    'publication_transport_failure': re.compile(r'steelsearch_publication_response_class=transport_failure'),
    'publish_state_disconnected': re.compile(r'rootCauseMessage=.*\[internal:cluster/coordination/publish_state\] disconnected'),
    'publication_failed': re.compile(r'FailedToCommitClusterStateException: publication failed'),
}
counts = {k: 0 for k in patterns}
for line in stdout:
    for name, pat in patterns.items():
        if pat.search(line):
            counts[name] += 1
result = 'native_join_disconnect_points_away_from_semantic_rejection' if (
    counts['handlejoin_entry'] > 0 and
    counts['publication_transport_failure'] > 0 and
    counts['publish_state_disconnected'] > 0 and
    counts['publication_failed'] > 0 and
    counts['term_mismatch'] == 0 and
    counts['reboot_mismatch'] == 0 and
    counts['better_term'] == 0 and
    counts['better_version'] == 0 and
    counts['missing_initial_config'] == 0
) else 'inconclusive'
counts['result'] = result
print(json.dumps(counts, indent=2))
