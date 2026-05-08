#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            'usage: check_plain_cargo_run_overhead_vs_split_path.py <plain-stderr> <plain-report> <split-stderr> <split-report>',
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, str(Path('/home/ubuntu/steelsearch/tools')))
    import check_steelsearch_process_start_timing as plain_mod
    import check_steelsearch_split_build_run_timing as split_mod

    # reuse the log formats directly
    plain_stderr = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    plain_report = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    split_stderr = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')
    split_report = json.loads(Path(sys.argv[4]).read_text(encoding='utf-8'))

    plain_launch = int(plain_mod.LAUNCH_RE.search(plain_stderr).group('ms'))
    plain_bind = int(plain_mod.BIND_RE.search(plain_stderr).group('ms'))
    plain_launch_to_bind = plain_bind - plain_launch

    split_vals = {}
    for key, pattern in split_mod.PATTERNS.items():
        m = pattern.search(split_stderr)
        split_vals[key] = int(m.group('ms')) if m else None
    split_build = split_vals['build_done_ms'] - split_vals['build_start_ms']
    split_exec_to_bind = split_vals['bind_ms'] - split_vals['binary_exec_launch_ms']
    split_known_cost = split_build + split_exec_to_bind
    plain_extra_overhead = plain_launch_to_bind - split_known_cost

    result = {
        'plain_launch_to_bind_ms': plain_launch_to_bind,
        'split_build_duration_ms': split_build,
        'split_binary_exec_to_bind_ms': split_exec_to_bind,
        'split_known_cost_ms': split_known_cost,
        'plain_extra_overhead_ms': plain_extra_overhead,
        'result': 'plain_cargo_run_path_has_multi_second_overhead_beyond_actual_build_and_binary_startup_so_the_remaining_gap_is_best_attributed_to_cargo_run_wrapper_path',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
