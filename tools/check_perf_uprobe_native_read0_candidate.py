#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_perf_uprobe_native_read0_candidate.py <summary-json>')
        return 2
    summary = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    counts = summary.get('perf_counts', {})
    socket_hits = counts.get('probe_libnio:ss_socket_read0', 0)
    unix_hits = counts.get('probe_libnio:ss_unix_read0', 0)
    result = {
        'perf_returncode': summary.get('perf_returncode'),
        'report_failure_stage': summary.get('report_failure_stage'),
        'socket_read0_hits': socket_hits,
        'unix_read0_hits': unix_hits,
    }
    if socket_hits > 0 or unix_hits > 0:
        result['checker_result'] = 'perf_uprobe_native_read0_candidate_captures_exact_native_read_boundary'
    elif summary.get('checker_result') == 'late_perf_uprobe_stat_collected_on_failing_probe':
        result['checker_result'] = 'perf_uprobe_native_read0_candidate_collected_but_saw_no_exact_read0_hits'
    else:
        result['checker_result'] = 'perf_uprobe_native_read0_candidate_collection_incomplete'
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
