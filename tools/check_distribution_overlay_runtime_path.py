#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_distribution_overlay_runtime_path.py <run-opensearch-dev.sh> <probe_java_rust_mixed_membership.sh> <jar>', file=sys.stderr)
        return 2
    run_script = Path(sys.argv[1]).read_text()
    probe_script = Path(sys.argv[2]).read_text()
    jar_bytes = Path(sys.argv[3]).read_bytes()
    run_has_overlay = 'OPENSEARCH_CLASS_OVERLAY_DIR' in run_script and 'OPENSEARCH_CLASS_OVERLAY_FILES' in run_script and 'jar uf' in run_script
    probe_has_overlay = 'JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_DIR' in probe_script and 'JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_CLASS_OVERLAY_FILES' in probe_script
    jar_has_finer_trace = b'closeOrder' in jar_bytes and b'closeNanoTime' in jar_bytes
    result = 'distribution_overlay_runtime_path_incomplete'
    if run_has_overlay and probe_has_overlay:
        result = 'distribution_overlay_runtime_path_is_implemented'
    print(json.dumps({
        'run_has_overlay': run_has_overlay,
        'probe_has_overlay': probe_has_overlay,
        'jar_has_finer_trace': jar_has_finer_trace,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
