#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
stdout_path = Path(report['artifacts']['opensearch_stdout'])
lines = stdout_path.read_text(encoding='utf-8', errors='replace').splitlines()

patterns = {
    'followers_disconnected': re.compile(r'FollowersChecker.*disconnected'),
    'followers_marking_faulty': re.compile(r'FollowersChecker.*marking node as faulty'),
    'publication_transport_failure': re.compile(r'steelsearch_publication_response_class=transport_failure'),
    'publish_state_disconnected': re.compile(r'rootCauseMessage=.*\[internal:cluster/coordination/publish_state\] disconnected'),
    'publication_failed': re.compile(r'FailedToCommitClusterStateException: publication failed'),
    'non_failed_quorum': re.compile(r'non-failed nodes do not form a quorum'),
    'commit_state': re.compile(r'internal:cluster/coordination/commit_state'),
}

indices = {name: [] for name in patterns}
for i, line in enumerate(lines):
    for name, pattern in patterns.items():
        if pattern.search(line):
            indices[name].append(i)

summary = {
    name: len(vals) for name, vals in indices.items()
}
summary['ordering'] = {
    'first_followers_disconnected_before_first_transport_failure': (
        bool(indices['followers_disconnected'] and indices['publication_transport_failure'])
        and indices['followers_disconnected'][0] < indices['publication_transport_failure'][0]
    ),
    'first_transport_failure_before_first_publication_failed': (
        bool(indices['publication_transport_failure'] and indices['publication_failed'])
        and indices['publication_transport_failure'][0] < indices['publication_failed'][0]
    ),
    'first_publication_failed_before_first_non_failed_quorum': (
        bool(indices['publication_failed'] and indices['non_failed_quorum'])
        and indices['publication_failed'][0] <= indices['non_failed_quorum'][0]
    ),
}

result = 'quorum_failure_tracks_transport_disconnect' if (
    summary['publication_transport_failure'] > 0 and
    summary['publish_state_disconnected'] > 0 and
    summary['followers_disconnected'] > 0 and
    summary['ordering']['first_followers_disconnected_before_first_transport_failure'] and
    summary['ordering']['first_transport_failure_before_first_publication_failed'] and
    summary['ordering']['first_publication_failed_before_first_non_failed_quorum']
) else 'inconclusive'
summary['result'] = result
print(json.dumps(summary, indent=2))
