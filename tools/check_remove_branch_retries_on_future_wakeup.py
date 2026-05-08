#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def parse_find_peers_interval_ms(text: str):
    m = re.search(r'DISCOVERY_FIND_PEERS_INTERVAL_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', text, re.S)
    return int(m.group(1)) if m else None


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_remove_branch_retries_on_future_wakeup.py <PeerFinder.java> <retry_gap_paths.json>')

    source = Path(sys.argv[1]).read_text()
    retry = load(sys.argv[2])

    source_remove_branch_retries_via_future_wakeup = (
        'peersByAddress.remove(transportAddress, Peer.this);' in source
        and 'scheduleUnlessShuttingDown(findPeersInterval' in source
        and 'providedAddresses.forEach(this::startProbe);' in source
        and 'peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer);' in source
    )
    find_peers_interval_ms = parse_find_peers_interval_ms(source)
    delayed_entries = retry.get('delayed_entries') or []
    delayed_gap_ms = delayed_entries[0].get('gap_ms') if len(delayed_entries) == 1 else None
    delayed_exceeds_single_wakeup = delayed_gap_ms is not None and find_peers_interval_ms is not None and delayed_gap_ms > find_peers_interval_ms

    result = (
        'remove_branch_long_gap_is_consistent_with_retry_on_future_peerfinder_wakeup_rounds'
        if source_remove_branch_retries_via_future_wakeup and delayed_exceeds_single_wakeup
        else 'remove_branch_future_wakeup_retry_not_fully_established'
    )

    print(json.dumps({
        'source_remove_branch_retries_via_future_wakeup': source_remove_branch_retries_via_future_wakeup,
        'find_peers_interval_ms': find_peers_interval_ms,
        'delayed_gap_ms': delayed_gap_ms,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
