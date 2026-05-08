#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_probe_retry_1s_tick_alignment.py <report.json> <tolerance_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    tolerance_ms = int(sys.argv[2])
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

    aligned = 0
    tick_buckets = {}
    for gap in gaps:
        nearest_tick = int(round(gap / 1000.0))
        tick_buckets[nearest_tick] = tick_buckets.get(nearest_tick, 0) + 1
        if abs(gap - nearest_tick * 1000) <= tolerance_ms:
            aligned += 1

    result = (
        'probe_retry_gaps_show_1s_tick_alignment'
        if gaps and aligned == len(gaps)
        else 'probe_retry_gaps_do_not_uniformly_align_to_1s_ticks'
    )

    print(json.dumps({
        'gap_count': len(gaps),
        'aligned_count': aligned,
        'tolerance_ms': tolerance_ms,
        'tick_buckets': tick_buckets,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
