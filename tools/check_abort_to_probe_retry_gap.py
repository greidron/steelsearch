#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_abort_to_probe_retry_gap.py <report.json>')

    report = json.loads(Path(sys.argv[1]).read_text())
    capture = report.get('steelsearch_transport_capture') or []

    direct = [
        e for e in capture
        if ((e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')
    ]

    gaps = []
    for entry in direct:
        end_at = entry.get('connection_end_at_ms')
        later_tcp = [
            other for other in capture
            if other is not entry
            and ((other.get('first_frame') or {}).get('action_hint') == 'internal:tcp/handshake')
            and other.get('connection_started_at_ms') is not None
            and end_at is not None
            and other.get('connection_started_at_ms') > end_at
        ]
        if not later_tcp:
            continue
        first_later = min(later_tcp, key=lambda e: e.get('connection_started_at_ms'))
        gaps.append(first_later.get('connection_started_at_ms') - end_at)

    all_immediate = bool(gaps) and all(g <= 5 for g in gaps)
    result = (
        'probe_timeout_scale_abort_is_followed_by_immediate_tcp_handshake_retry'
        if all_immediate
        else 'abort_to_probe_retry_gap_not_immediate_or_not_fully_observed'
    )

    print(json.dumps({
        'gap_count': len(gaps),
        'min_gap_ms': min(gaps) if gaps else None,
        'max_gap_ms': max(gaps) if gaps else None,
        'all_immediate_le_5ms': all_immediate,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
