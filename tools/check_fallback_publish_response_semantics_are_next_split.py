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
        'decode_zero': bool(series(stderr_text, 'steelsearch_publish_state_decode_ms=')) and max(series(stderr_text, 'steelsearch_publish_state_decode_ms=')) == 0,
        'build_zero': bool(series(stderr_text, 'steelsearch_publish_state_build_ms=')) and max(series(stderr_text, 'steelsearch_publish_state_build_ms=')) == 0,
        'decode_mode_count': stderr_text.count('steelsearch_publish_state_decode_mode=inprocess_state_fallback'),
        'publication_transport_failure': stdout_text.count('steelsearch_publication_response_class=transport_failure'),
        'failed_to_commit_cluster_state': stdout_text.count('failed to commit cluster state'),
    }


def main() -> int:
    if len(sys.argv) != 7:
        print('usage: check_fallback_publish_response_semantics_are_next_split.py <baseline_stderr> <baseline_stdout> <build_bypass_stderr> <build_bypass_stdout> <full_inprocess_stderr> <full_inprocess_stdout>', file=sys.stderr)
        return 2

    baseline = snapshot(Path(sys.argv[1]), Path(sys.argv[2]))
    build_bypass = snapshot(Path(sys.argv[3]), Path(sys.argv[4]))
    full_inprocess = snapshot(Path(sys.argv[5]), Path(sys.argv[6]))
    print(f'baseline={baseline}')
    print(f'build_bypass={build_bypass}')
    print(f'full_inprocess={full_inprocess}')

    if (
        build_bypass['decode_mode_count'] == 0
        and not build_bypass['decode_zero']
        and build_bypass['build_zero']
        and build_bypass['publication_transport_failure'] > 0
        and full_inprocess['decode_mode_count'] > 0
        and full_inprocess['decode_zero']
        and full_inprocess['build_zero']
        and full_inprocess['publication_transport_failure'] > 0
    ):
        print('result=real_decode_plus_fallback_builder_still_fails_so_next_split_is_fallback_publish_response_semantics_not_decode_latency')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
