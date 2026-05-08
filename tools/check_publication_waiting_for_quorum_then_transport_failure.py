#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

MARKERS = [
    'steelsearch_handlePublishResponse_gate=accepted',
    'steelsearch_publication_target_state=waiting_for_quorum',
    'steelsearch_publication_target_state=failed',
    'steelsearch_publication_response_class=transport_failure',
]


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_publication_waiting_for_quorum_then_transport_failure.py <opensearch_stdout>', file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    counts = {m: text.count(m) for m in MARKERS}
    for key, value in counts.items():
        print(f'{key}={value}')

    if (
        counts['steelsearch_handlePublishResponse_gate=accepted'] > 0
        and counts['steelsearch_publication_target_state=waiting_for_quorum'] == counts['steelsearch_handlePublishResponse_gate=accepted']
        and counts['steelsearch_publication_response_class=transport_failure'] == counts['steelsearch_handlePublishResponse_gate=accepted']
        and counts['steelsearch_publication_target_state=failed'] >= counts['steelsearch_publication_response_class=transport_failure']
    ):
        print('result=accepted_publish_responses_reach_waiting_for_quorum_and_then_fail_via_later_transport_callback_chain')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
