#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_peerfinder_trace_logging_route.py <PeerFinder.java> <opensearch_stdout.log>')

    source = Path(sys.argv[1]).read_text()
    stdout_text = Path(sys.argv[2]).read_text()

    source_has_trace_logs_for_raw_probe_flow = (
        'logger.trace("probing cluster-manager nodes from cluster state: {}", lastAcceptedNodes);' in source
        and 'logger.trace("probing resolved transport addresses {}", providedAddresses);' in source
        and 'logger.trace("{} attempting connection", this);' in source
        and 'logger.trace("{} requesting peers", this);' in source
    )
    source_peer_to_string_includes_transport_address_and_discovery_node = (
        "transportAddress=" in source
        and "discoveryNode=" in source
        and "peersRequestInFlight=" in source
    )
    current_stdout_lacks_peerfinder_trace = (
        'probing resolved transport addresses' not in stdout_text
        and 'attempting connection' not in stdout_text
        and 'requesting peers' not in stdout_text
        and 'startProbe(' not in stdout_text
    )

    result = (
        'existing_peerfinder_trace_logging_route_can_expose_raw_probe_keys_but_is_not_enabled_in_current_artifact'
        if source_has_trace_logs_for_raw_probe_flow
        and source_peer_to_string_includes_transport_address_and_discovery_node
        and current_stdout_lacks_peerfinder_trace
        else 'peerfinder_trace_logging_route_not_fully_established'
    )

    print(json.dumps({
        'source_has_trace_logs_for_raw_probe_flow': source_has_trace_logs_for_raw_probe_flow,
        'source_peer_to_string_includes_transport_address_and_discovery_node': source_peer_to_string_includes_transport_address_and_discovery_node,
        'current_stdout_lacks_peerfinder_trace': current_stdout_lacks_peerfinder_trace,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
