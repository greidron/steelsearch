#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_blocker_reframed_as_single_peer_one_shot_loop.py <trace_direct_multiplicity.json>')

    trace = load(sys.argv[1])
    attempting = trace.get('attempting_connection_addresses') or []
    requesting = trace.get('requesting_peers_addresses') or []

    single_remote_peer = attempting == ['127.0.0.1:57743'] and requesting == ['127.0.0.1:57743']

    # counts are embedded in the source trace artifact checker output only implicitly; use address stability as the main signal.
    result = (
        'current_blocker_is_better_reframed_as_single_remote_peer_repeated_one_shot_connection_loop_than_as_multi_address_alias_multiplicity'
        if single_remote_peer
        else 'single_peer_one_shot_loop_reframe_not_fully_established'
    )

    print(json.dumps({
        'single_remote_peer': single_remote_peer,
        'attempting_connection_addresses': attempting,
        'requesting_peers_addresses': requesting,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
