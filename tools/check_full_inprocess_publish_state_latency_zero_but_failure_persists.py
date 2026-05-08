#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def series(text: str, key: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf'{re.escape(key)}(\d+)', text)]


def snapshot(stderr_path: Path, stdout_path: Path) -> dict[str, object]:
    stderr_text = stderr_path.read_text(errors='replace')
    stdout_text = stdout_path.read_text(errors='replace')
    return {
        'decode': series(stderr_text, 'steelsearch_publish_state_decode_ms='),
        'build': series(stderr_text, 'steelsearch_publish_state_build_ms='),
        'total': series(stderr_text, 'steelsearch_publish_state_total_before_write_ms='),
        'decode_mode_count': stderr_text.count('steelsearch_publish_state_decode_mode=inprocess_state_fallback'),
        'publication_transport_failure': stdout_text.count('steelsearch_publication_response_class=transport_failure'),
        'failed_to_commit_cluster_state': stdout_text.count('failed to commit cluster state'),
    }


def main() -> int:
    if len(sys.argv) != 9:
        print('usage: check_full_inprocess_publish_state_latency_zero_but_failure_persists.py <baseline_stderr> <baseline_stdout> <build_bypass_stderr> <build_bypass_stdout> <parse_bypass_stderr> <parse_bypass_stdout> <full_inprocess_stderr> <full_inprocess_stdout>', file=sys.stderr)
        return 2

    baseline = snapshot(Path(sys.argv[1]), Path(sys.argv[2]))
    build_bypass = snapshot(Path(sys.argv[3]), Path(sys.argv[4]))
    parse_bypass = snapshot(Path(sys.argv[5]), Path(sys.argv[6]))
    full_inprocess = snapshot(Path(sys.argv[7]), Path(sys.argv[8]))
    print(f'baseline={baseline}')
    print(f'build_bypass={build_bypass}')
    print(f'parse_bypass={parse_bypass}')
    print(f'full_inprocess={full_inprocess}')

    if (
        full_inprocess['decode']
        and full_inprocess['build']
        and full_inprocess['total']
        and max(full_inprocess['decode']) == 0
        and max(full_inprocess['build']) == 0
        and max(full_inprocess['total']) <= 4
        and full_inprocess['decode_mode_count'] > 0
        and full_inprocess['publication_transport_failure'] > 0
        and full_inprocess['publication_transport_failure'] >= baseline['publication_transport_failure']
    ):
        print('result=full_inprocess_publish_state_removes_shell_helper_latency_but_publication_transport_failure_persists_so_remaining_blocker_points_to_response_semantics')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
