import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_closefuture_interception_still_unknown.py <handler_trace.json> <unknown_hints.json>', file=sys.stderr)
        return 1
    handler = json.loads(Path(sys.argv[1]).read_text())
    unknown = json.loads(Path(sys.argv[2]).read_text())
    result = 'closefuture_interception_effect_inconclusive'
    if handler['inactive_count'] > 0 and unknown['unknown_only']:
        result = 'even_closefuture_interception_before_dispatcher_still_leaves_unknown_only_hints_so_next_step_is_listener_registration_order'
    print(json.dumps({
        'handler': handler,
        'unknown': unknown,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
