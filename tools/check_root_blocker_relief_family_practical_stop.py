#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path_str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    perfmap_flags_path, perfmap_flags = load(sys.argv[1])
    inject_path, inject = load(sys.argv[2])
    dwarf_summary_path, dwarf_summary = load(sys.argv[3])
    dwarf_checker_path, dwarf_checker = load(sys.argv[4])

    result = {
        'perfmap_flags_path': str(perfmap_flags_path),
        'perfmap_copied': perfmap_flags.get('perf_map_copied'),
        'inject_path': str(inject_path),
        'inject_jit_lines': inject.get('metrics', {}).get('jit_lines'),
        'inject_unknown_tmp_perf_lines': inject.get('metrics', {}).get('unknown_tmp_perf_lines'),
        'dwarf_summary_path': str(dwarf_summary_path),
        'dwarf_summary_result': dwarf_summary.get('checker_result'),
        'dwarf_checker_path': str(dwarf_checker_path),
        'dwarf_checker_result': dwarf_checker.get('checker_result'),
        'dwarf_resolved_after_read0': len(dwarf_checker.get('resolved_after_read0', [])),
    }
    if (
        perfmap_flags.get('perf_map_copied') is False
        and inject.get('metrics', {}).get('jit_lines') == 0
        and inject.get('metrics', {}).get('unknown_tmp_perf_lines', 0) > 0
        and dwarf_summary.get('checker_result') == 'perf_dwarf_capture_collected_on_failing_probe'
        and dwarf_checker.get('checker_result') == 'perf_dwarf_candidate_did_not_recover_non_unknown_higher_caller_frames_after_read0'
    ):
        result['checker_result'] = 'root_blocker_relief_candidate_family_reached_practical_stop_without_recovering_higher_caller_frames'
    else:
        result['checker_result'] = 'root_blocker_relief_candidate_family_needs_more_candidate_work'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
