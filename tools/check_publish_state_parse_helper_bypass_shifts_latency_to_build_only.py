#!/usr/bin/env python3
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path


def series(text: str, key: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf'{re.escape(key)}(\d+)', text)]


def count(text: str, needle: str) -> int:
    return text.count(needle)


def snapshot(stderr_path: Path, stdout_path: Path) -> dict[str, object]:
    stderr_text = stderr_path.read_text(errors='replace')
    stdout_text = stdout_path.read_text(errors='replace')
    return {
        'decode': series(stderr_text, 'steelsearch_publish_state_decode_ms='),
        'build': series(stderr_text, 'steelsearch_publish_state_build_ms='),
        'total': series(stderr_text, 'steelsearch_publish_state_total_before_write_ms='),
        'decode_mode_count': count(stderr_text, 'steelsearch_publish_state_decode_mode=inprocess_state_fallback'),
        'publication_transport_failure': count(stdout_text, 'steelsearch_publication_response_class=transport_failure'),
        'failed_to_commit_cluster_state': count(stdout_text, 'failed to commit cluster state'),
    }


def main() -> int:
    if len(sys.argv) != 7:
        print('usage: check_publish_state_parse_helper_bypass_shifts_latency_to_build_only.py <baseline_stderr> <baseline_stdout> <build_bypass_stderr> <build_bypass_stdout> <parse_bypass_stderr> <parse_bypass_stdout>', file=sys.stderr)
        return 2

    baseline = snapshot(Path(sys.argv[1]), Path(sys.argv[2]))
    build_bypass = snapshot(Path(sys.argv[3]), Path(sys.argv[4]))
    parse_bypass = snapshot(Path(sys.argv[5]), Path(sys.argv[6]))
    print(f'baseline={baseline}')
    print(f'build_bypass={build_bypass}')
    print(f'parse_bypass={parse_bypass}')

    parse_decode_max = max(parse_bypass['decode']) if parse_bypass['decode'] else None
    parse_build_med = statistics.median(parse_bypass['build']) if parse_bypass['build'] else None
    parse_build_max = max(parse_bypass['build']) if parse_bypass['build'] else None
    parse_total_max = max(parse_bypass['total']) if parse_bypass['total'] else None
    baseline_decode_med = statistics.median(baseline['decode']) if baseline['decode'] else None
    build_bypass_build_max = max(build_bypass['build']) if build_bypass['build'] else None

    if (
        parse_decode_max == 0
        and parse_bypass['decode_mode_count'] > 0
        and parse_build_med is not None
        and parse_build_max is not None
        and parse_build_med > 15000
        and parse_build_max > 30000
        and parse_total_max is not None
        and parse_total_max > 30000
        and baseline_decode_med is not None
        and baseline_decode_med > 20000
        and build_bypass_build_max == 0
        and parse_bypass['publication_transport_failure'] >= baseline['publication_transport_failure']
    ):
        print('result=parse_helper_bypass_removes_decode_cost_but_build_helper_still_dominates_and_transport_failure_does_not_improve')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
