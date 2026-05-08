#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_single_remote_seed_candidate_in_mixed_probe.py <PeerFinder.java> <probe_java_rust_mixed_membership.sh> <report.json>')

    peerfinder = Path(sys.argv[1]).read_text()
    probe = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_skips_local_probe = (
        'if (transportAddress.equals(getLocalNode().getAddress())) {' in peerfinder
        and 'not probing local node' in peerfinder
    )
    runtime_uses_two_seed_hosts = 'SEEDS="127.0.0.1:${OS_TRANSPORT},127.0.0.1:${SS_TRANSPORT}"' in probe

    seed_peer_identity = report.get('seed_peer_identity') or {}
    seed_transport_address = (seed_peer_identity.get('discovery_node') or {}).get('transport_address')
    runtime_has_single_remote_seed_identity = bool(seed_transport_address)

    result = (
        'mixed_probe_has_two_seed_hosts_but_peerfinder_skips_local_one_so_probe_triggers_collapse_to_single_remote_seed_candidate'
        if source_skips_local_probe and runtime_uses_two_seed_hosts and runtime_has_single_remote_seed_identity
        else 'single_remote_seed_candidate_not_fully_established'
    )

    print(json.dumps({
        'source_skips_local_probe': source_skips_local_probe,
        'runtime_uses_two_seed_hosts': runtime_uses_two_seed_hosts,
        'runtime_has_single_remote_seed_identity': runtime_has_single_remote_seed_identity,
        'seed_transport_address': seed_transport_address,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
