#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

MARKERS = [
    'steelsearch_handlePublishResponse_gate=election_not_won',
    'steelsearch_handlePublishResponse_gate=term_mismatch',
    'steelsearch_handlePublishResponse_gate=version_mismatch',
    'steelsearch_handlePublishResponse_gate=accepted',
    'steelsearch_publication_response_class=transport_failure',
]


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_publish_response_gate_markers_show_acceptance_before_transport_failure.py <opensearch_stdout>', file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    counts = {m: text.count(m) for m in MARKERS}
    for key, value in counts.items():
        print(f'{key}={value}')

    if (
        counts['steelsearch_handlePublishResponse_gate=accepted'] > 0
        and counts['steelsearch_handlePublishResponse_gate=election_not_won'] == 0
        and counts['steelsearch_handlePublishResponse_gate=term_mismatch'] == 0
        and counts['steelsearch_handlePublishResponse_gate=version_mismatch'] == 0
        and counts['steelsearch_publication_response_class=transport_failure'] > 0
    ):
        print('result=publish_response_top_level_term_version_and_election_won_gates_pass_but_transport_failure_still_occurs_later')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
