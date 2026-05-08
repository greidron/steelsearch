import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_netty4_close_hint_trace_in_actual_probe.py <stdout.log>', file=sys.stderr)
        return 1
    text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    hints = re.findall(r'netty4 tcp channel close completed for .*? with hint \[(.*?)\]', text)
    hint_counts = {}
    for hint in hints:
        hint_counts[hint] = hint_counts.get(hint, 0) + 1
    result = 'netty4_close_hint_trace_not_observed'
    if hint_counts:
        result = 'netty4_close_hint_trace_observed_in_actual_probe'
    print(json.dumps({
        'close_hint_trace_count': len(hints),
        'hint_counts': hint_counts,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
