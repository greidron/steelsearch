#!/usr/bin/env python3
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path


def series(text: str, key: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf'{re.escape(key)}(\d+)', text)]


def read_counts(stderr_path: Path, stdout_path: Path) -> dict[str, object]:
    stderr_text = stderr_path.read_text(errors='replace')
    stdout_text = stdout_path.read_text(errors='replace')
    decode = series(stderr_text, 'steelsearch_publish_state_decode_ms=')
    build = series(stderr_text, 'steelsearch_publish_state_build_ms=')
    total = series(stderr_text, 'steelsearch_publish_state_total_before_write_ms=')
    return {
        'decode': decode,
        'build': build,
        'total': total,
        'publication_transport_failure': stdout_text.count('steelsearch_publication_response_class=transport_failure'),
        'failed_to_commit_cluster_state': stdout_text.count('failed to commit cluster state'),
    }


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_publish_state_build_helper_bypass_shifts_latency_to_decode_only.py <baseline_stderr> <baseline_stdout> <bypass_stderr> <bypass_stdout>', file=sys.stderr)
        return 2

    baseline = read_counts(Path(sys.argv[1]), Path(sys.argv[2]))
    bypass = read_counts(Path(sys.argv[3]), Path(sys.argv[4]))
    print(f'baseline={baseline}')
    print(f'bypass={bypass}')

    baseline_build_med = statistics.median(baseline['build']) if baseline['build'] else None
    bypass_build_max = max(bypass['build']) if bypass['build'] else None
    baseline_total_max = max(baseline['total']) if baseline['total'] else None
    bypass_total_max = max(bypass['total']) if bypass['total'] else None
    bypass_decode_med = statistics.median(bypass['decode']) if bypass['decode'] else None

    if (
        baseline_build_med is not None
        and bypass_build_max is not None
        and baseline_total_max is not None
        and bypass_total_max is not None
        and bypass_decode_med is not None
        and baseline_build_med > 30000
        and bypass_build_max == 0
        and bypass_decode_med > 20000
        and bypass_total_max > 40000
        and bypass['publication_transport_failure'] >= baseline['publication_transport_failure']
    ):
        print('result=build_helper_bypass_removes_build_cost_but_decode_helper_still_dominates_and_transport_failure_does_not_improve')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
