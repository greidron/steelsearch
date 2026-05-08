#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_direct_full_connect_close_window.py <report.json> <threshold_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    threshold_ms = int(sys.argv[2])
    capture = report.get('steelsearch_transport_capture') or []

    windows = []
    for entry in capture:
        if ((entry.get('first_frame') or {}).get('action_hint') != 'internal:transport/handshake'):
            continue
        sent = entry.get('response_frame_sent_at_ms')
        end = entry.get('connection_end_at_ms')
        if sent is None or end is None:
            continue
        windows.append(end - sent)

    all_sub_threshold = bool(windows) and all(w < threshold_ms for w in windows)
    result = (
        'direct_full_connect_peer_close_has_consistent_sub_threshold_window'
        if all_sub_threshold
        else 'direct_full_connect_close_window_not_consistently_sub_threshold'
    )

    print(json.dumps({
        'window_count': len(windows),
        'min_window_ms': min(windows) if windows else None,
        'max_window_ms': max(windows) if windows else None,
        'threshold_ms': threshold_ms,
        'all_sub_threshold': all_sub_threshold,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
