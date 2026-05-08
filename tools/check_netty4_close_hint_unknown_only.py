import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_netty4_close_hint_unknown_only.py <stdout.log>', file=sys.stderr)
        return 1
    text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    hints = re.findall(r'netty4 tcp channel close completed for .*? with hint \[(.*?)\]', text)
    hint_counts = {}
    for hint in hints:
        hint_counts[hint] = hint_counts.get(hint, 0) + 1
    unknown_only = bool(hint_counts) and set(hint_counts) == {'unknown'}
    result = 'netty4_close_hints_are_unknown_only'
    if not unknown_only:
        result = 'netty4_close_hints_include_non_unknown_values_or_are_absent'
    print(json.dumps({
        'hint_counts': hint_counts,
        'unknown_only': unknown_only,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
