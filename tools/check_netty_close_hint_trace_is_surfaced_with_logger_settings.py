#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_netty_close_hint_trace_is_surfaced_with_logger_settings.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    text = stdout_log.read_text(errors='ignore')
    counts = {
        'netty4_tcp_channel_close_completed': len(re.findall(r'netty4 tcp channel close completed', text)),
        'hint_channelInactive': len(re.findall(r'hint \[channelInactive\]', text)),
        'hint_exceptionCaught': len(re.findall(r'hint \[exceptionCaught\]', text)),
        'hint_closeFutureIntercepted': len(re.findall(r'hint \[closeFutureIntercepted\]', text)),
    }
    result = 'netty_close_hint_trace_is_surfaced_in_actual_probe_with_netty4_logger_trace_settings' if counts['netty4_tcp_channel_close_completed'] > 0 else 'inconclusive'
    print(json.dumps({'work_dir': artifact['work_dir'], **counts, 'result': result}, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
