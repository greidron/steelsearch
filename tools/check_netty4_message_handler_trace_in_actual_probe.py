import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_netty4_message_handler_trace_in_actual_probe.py <stdout.log>', file=sys.stderr)
        return 1
    text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    exception_count = len(re.findall(r'netty4 message channel handler exceptionCaught on', text))
    inactive_count = len(re.findall(r'netty4 message channel handler channelInactive on', text))
    result = 'netty4_message_handler_trace_not_observed'
    if exception_count or inactive_count:
        result = 'netty4_message_handler_trace_observed_in_actual_probe'
    print(json.dumps({
        'exception_count': exception_count,
        'inactive_count': inactive_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
