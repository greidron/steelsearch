#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: check_mixed_close_ordering_trigger.py <mixed_report.json>"}))
        return 1

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []
    entries = []
    for e in capture:
        first = (e.get('first_frame') or {}).get('action_hint')
        if first != 'internal:cluster/coordination/publish_state':
            continue
        entries.append(e)

    count = len(entries)
    all_have_hold_open_start = count > 0 and all(e.get('hold_open_started_at_ms') is not None for e in entries)
    all_first_post_event_remote_eof = count > 0 and all(e.get('first_post_response_event') == 'remote_eof' for e in entries)
    all_same_tick_close = count > 0 and all(e.get('response_frame_sent_at_ms') == e.get('connection_end_at_ms') for e in entries)

    if all_have_hold_open_start and all_first_post_event_remote_eof and all_same_tick_close:
        result = 'peer_side_remote_eof_is_first_post_response_event_for_every_publish_state_socket'
    else:
        result = 'close_ordering_trigger_not_uniform'

    print(json.dumps({
        'publish_state_entry_count': count,
        'all_have_hold_open_start': all_have_hold_open_start,
        'all_first_post_response_event_remote_eof': all_first_post_event_remote_eof,
        'all_same_tick_close': all_same_tick_close,
        'result': result,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
