#!/usr/bin/env python3
import sys
from pathlib import Path

REQUIRED = [
    'Status: closed as a side branch',
    'ordering race',
    'explicitLocalClose',
    'channelInactive',
    'closeFutureIntercepted',
    '1/75',
    'return to the mixed-membership mainline blocker analysis',
]


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_netty_close_hint_branch_decision_note.py <decision-note.md>', file=sys.stderr)
        return 2
    text = Path(sys.argv[1]).read_text()
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        print({'all_required_present': False, 'missing': missing, 'result': 'incomplete'})
        return 1
    print({'all_required_present': True, 'result': 'netty_close_hint_branch_decision_note_documented'})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
