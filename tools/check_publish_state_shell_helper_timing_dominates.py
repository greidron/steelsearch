#!/usr/bin/env python3
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path


def extract_series(text: str, key: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf'{re.escape(key)}(\d+)', text)]


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_publish_state_shell_helper_timing_dominates.py <steelsearch_stderr> <opensearch_stdout>', file=sys.stderr)
        return 2

    stderr_text = Path(sys.argv[1]).read_text(errors='replace')
    stdout_text = Path(sys.argv[2]).read_text(errors='replace')

    decode = extract_series(stderr_text, 'steelsearch_publish_state_decode_ms=')
    build = extract_series(stderr_text, 'steelsearch_publish_state_build_ms=')
    total = extract_series(stderr_text, 'steelsearch_publish_state_total_before_write_ms=')

    print(f'decode_ms={decode}')
    print(f'build_ms={build}')
    print(f'total_before_write_ms={total}')
    print(f'publication_transport_failure={stdout_text.count("steelsearch_publication_response_class=transport_failure")}')
    print(f'failed_to_commit_cluster_state={stdout_text.count("failed to commit cluster state")}')

    decode_med = statistics.median(decode) if decode else None
    build_med = statistics.median(build) if build else None
    total_max = max(total) if total else None

    if (
        len(decode) >= 3
        and len(build) >= 3
        and len(total) >= 3
        and decode_med is not None
        and build_med is not None
        and total_max is not None
        and decode_med >= 20_000
        and build_med >= 30_000
        and total_max >= 60_000
        and stdout_text.count('steelsearch_publication_response_class=transport_failure') > 0
    ):
        print('result=publish_state_shell_helper_timing_dominates_before_java_publication_transport_failure')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
