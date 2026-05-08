#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_peerfinder_trace_enabled_actual_probe.py <opensearch_stdout.log>')

    text = Path(sys.argv[1]).read_text()
    probing_resolved_count = text.count('probing resolved transport addresses')
    attempting_connection_count = text.count('attempting connection')
    requesting_peers_count = text.count('requesting peers')
    skipped_local = sorted(set(re.findall(r'startProbe\((127\.0\.0\.1:\d+)\) not probing local node', text)))
    remote_probe_addresses = sorted(set(re.findall(r'probing resolved transport addresses \[(127\.0\.0\.1:\d+)\]', text)))
    attempting_addresses = sorted(set(re.findall(r'Peer\{transportAddress=(127\.0\.0\.1:\d+), discoveryNode=', text)))

    result = (
        'peerfinder_trace_is_enabled_in_actual_probe_and_exposes_raw_probe_addresses'
        if probing_resolved_count > 0 and attempting_connection_count > 0 and requesting_peers_count > 0 and remote_probe_addresses
        else 'peerfinder_trace_not_observed_in_actual_probe'
    )

    print(json.dumps({
        'probing_resolved_count': probing_resolved_count,
        'attempting_connection_count': attempting_connection_count,
        'requesting_peers_count': requesting_peers_count,
        'skipped_local_addresses': skipped_local,
        'remote_probe_addresses': remote_probe_addresses,
        'attempting_connection_addresses': attempting_addresses,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
