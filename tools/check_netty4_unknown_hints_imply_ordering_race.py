import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_netty4_unknown_hints_imply_ordering_race.py <handler_trace.json> <unknown_hints.json>', file=sys.stderr)
        return 1
    handler = json.loads(Path(sys.argv[1]).read_text())
    unknown = json.loads(Path(sys.argv[2]).read_text())
    handler_trace_observed = handler['exception_count'] > 0 or handler['inactive_count'] > 0
    unknown_only = unknown['unknown_only']
    result = 'netty4_unknown_hints_vs_ordering_inconclusive'
    if handler_trace_observed and unknown_only:
        result = 'netty4_handler_overlay_is_active_so_unknown_only_hints_point_to_closefuture_vs_recordCloseHint_ordering_race'
    print(json.dumps({
        'handler_trace_observed': handler_trace_observed,
        'handler': handler,
        'unknown': unknown,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
