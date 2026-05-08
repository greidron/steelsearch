#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    blocked_path, blocked = load(sys.argv[1])
    strace_path, strace = load(sys.argv[2])
    result = {
        'blocked_path': str(blocked_path),
        'blocked_result': blocked.get('checker_result'),
        'strace_path': str(strace_path),
        'strace_result': strace.get('checker_result'),
    }
    if (
        blocked.get('checker_result') == 'read_starvation_subtree_should_remain_blocked_until_materially_different_capability_or_new_relief_candidate_appears'
        and strace.get('checker_result') == 'strace_binary_exists_but_attach_is_not_usable_in_current_session'
    ):
        result['checker_result'] = 'blocked_state_must_be_preserved_because_no_actually_usable_new_relief_capability_is_available'
    else:
        result['checker_result'] = 'blocked_state_preservation_without_usable_capability_remains_unclear'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
