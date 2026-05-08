#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print(
        'usage: check_direct_join_rejection_instrumentation_is_next_step.py <probe-report.json> <CoordinationState.java> <Publication.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
coord = Path(sys.argv[2]).read_text()
pub = Path(sys.argv[3]).read_text()
text = report.get('opensearch_stdout', '') + '\n' + report.get('opensearch_stderr', '')

checks = {
    'probe_has_no_handlejoin_reason_lines': sum(
        len(re.findall(pat, text))
        for pat in [
            r'handleJoin: ignored join due to term mismatch',
            r'handleJoin: ignored join as term was not incremented yet after reboot',
            r'handleJoin: ignored join as joiner has a better last accepted term',
            r'handleJoin: ignored join as joiner has a better last accepted version',
            r'handleJoin: rejecting join since this node has not received its initial configuration yet',
            r'handleJoin: added join',
            r'publish response from .* contained no join',
        ]
    ) == 0,
    'coordinationstate_has_explicit_reject_sites': all(
        needle in coord for needle in [
            'handleJoin: ignored join due to term mismatch',
            'handleJoin: ignored join as term was not incremented yet after reboot',
            'handleJoin: ignored join as joiner has a better last accepted term',
            'handleJoin: ignored join as joiner has a better last accepted version',
            'handleJoin: rejecting join since this node has not received its initial configuration yet',
        ]
    ),
    'publication_has_missing_join_path': 'publish response from {} contained no join' in pub,
    'publication_has_publish_response_handler': 'private class PublishResponseHandler implements ActionListener<PublishWithJoinResponse>' in pub,
}

for key, value in checks.items():
    print(f'{key}={str(value).lower()}')

if all(checks.values()):
    print('result=direct_join_or_publication_rejection_instrumentation_is_the_next_minimal_path')
else:
    print('result=missing_required_evidence')
    sys.exit(1)
