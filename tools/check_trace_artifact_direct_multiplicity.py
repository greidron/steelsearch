#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_trace_artifact_direct_multiplicity.py <opensearch_stdout.log>')

    text = Path(sys.argv[1]).read_text()
    attempting = sorted(set(re.findall(r'Peer\{transportAddress=(127\.0\.0\.1:\d+), discoveryNode=.*?\} attempting connection', text)))
    requesting = sorted(set(re.findall(r'Peer\{transportAddress=(127\.0\.0\.1:\d+), discoveryNode=.*?\} requesting peers', text)))
    resolved = sorted(set(re.findall(r'probing resolved transport addresses \[(127\.0\.0\.1:\d+)\]', text)))

    result = (
        'trace_enabled_artifact_currently_reproduces_single_address_peer_activity_not_direct_alias_multiplicity'
        if len(attempting) == 1 and len(requesting) == 1 and len(resolved) == 1
        else 'trace_artifact_direct_multiplicity_not_fully_established'
    )

    print(json.dumps({
        'attempting_connection_addresses': attempting,
        'requesting_peers_addresses': requesting,
        'resolved_probe_addresses': resolved,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
