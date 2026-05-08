#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    perfmap_summary_path, perfmap_summary = load(sys.argv[1])
    inject_path, inject = load(sys.argv[2])
    repeated_jcmd_summary_path, repeated_jcmd_summary = load(sys.argv[3])

    result = {
        'perfmap_summary_path': str(perfmap_summary_path),
        'perfmap_flags_map_copied': perfmap_summary.get('perf_map_copied'),
        'perfmap_flags_failure_stage': perfmap_summary.get('report_failure_stage'),
        'inject_path': str(inject_path),
        'inject_returncode': inject.get('inject_returncode'),
        'inject_jit_lines': inject.get('metrics', {}).get('jit_lines'),
        'inject_unknown_tmp_perf_lines': inject.get('metrics', {}).get('unknown_tmp_perf_lines'),
        'repeated_jcmd_summary_path': str(repeated_jcmd_summary_path),
        'repeated_jcmd_snapshot_count': repeated_jcmd_summary.get('snapshot_count'),
        'repeated_jcmd_failure_stage': repeated_jcmd_summary.get('report_failure_stage'),
    }

    if (
        perfmap_summary.get('perf_map_copied') is False
        and inject.get('inject_returncode') == 0
        and inject.get('metrics', {}).get('jit_lines') == 0
        and inject.get('metrics', {}).get('unknown_tmp_perf_lines', 0) > 0
        and repeated_jcmd_summary.get('snapshot_count', 0) > 0
    ):
        result['checker_result'] = 'non_intrusive_jit_symbol_family_reached_practical_stop_without_recovering_higher_caller_frames'
    else:
        result['checker_result'] = 'non_intrusive_jit_symbol_family_needs_more_candidate_work'

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
