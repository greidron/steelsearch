import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_early_channelinactive_still_unknown.py <handler_trace.json> <unknown_hints.json>', file=sys.stderr)
        return 1
    handler = json.loads(Path(sys.argv[1]).read_text())
    unknown = json.loads(Path(sys.argv[2]).read_text())
    early_handler_observed = handler['inactive_count'] > 0
    unknown_only = unknown['unknown_only']
    result = 'early_channelinactive_vs_unknown_inconclusive'
    if early_handler_observed and unknown_only:
        result = 'even_early_channelinactive_hook_still_arrives_too_late_to_beat_closefuture_for_close_hint_capture'
    print(json.dumps({
        'handler': handler,
        'unknown': unknown,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
