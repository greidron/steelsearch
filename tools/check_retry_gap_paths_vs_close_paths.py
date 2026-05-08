#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_retry_gap_paths_vs_close_paths.py <retry_gap_paths.json> <close_paths.json>')

    retry = load(sys.argv[1])
    close = load(sys.argv[2])

    immediate_matches_restart = retry.get('immediate_count') == close.get('restart_loop_count')

    delayed_entries = retry.get('delayed_entries') or []
    close_exception_entries = close.get('exception_entries') or []
    delayed_peer = delayed_entries[0].get('peer_addr') if len(delayed_entries) == 1 else None
    close_exception_peer = close_exception_entries[0].get('peer_addr') if len(close_exception_entries) == 1 else None
    delayed_matches_exception = delayed_peer is not None and delayed_peer == close_exception_peer

    result = (
        'retry_gap_split_maps_cleanly_to_restart_loop_vs_exception_close_paths'
        if immediate_matches_restart and delayed_matches_exception
        else 'retry_gap_split_does_not_cleanly_map_to_close_paths'
    )

    print(json.dumps({
        'immediate_matches_restart_loop_count': immediate_matches_restart,
        'delayed_peer_matches_exception_peer': delayed_matches_exception,
        'delayed_peer': delayed_peer,
        'exception_peer': close_exception_peer,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
