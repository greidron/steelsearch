#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


CONNECTION_FAILED_RE = re.compile(
    r"Peer\{transportAddress=(?P<addr>[^,]+), discoveryNode=(?P<node>[^,]+), peersRequestInFlight=(?P<inflight>[^}]+)\} connection failed"
)


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_single_peer_remote_eof_maps_to_peerfinder_failure.py "
            "<peerfinder.java> <stdout.log> <report.json>"
        )

    source = Path(sys.argv[1]).read_text()
    stdout = Path(sys.argv[2]).read_text().splitlines()
    report = load_json(sys.argv[3])

    capture = report.get("steelsearch_transport_capture") or []
    direct_full_connect = [
        entry for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]
    remote_eof_before_post = [
        entry for entry in direct_full_connect
        if entry.get("first_post_response_event") == "remote_eof"
        and entry.get("post_follow_up_frame") is None
    ]

    failure_matches = []
    for line in stdout:
        match = CONNECTION_FAILED_RE.search(line)
        if match:
            failure_matches.append(match.groupdict())

    failure_addresses = sorted({m["addr"] for m in failure_matches})
    null_discovery_failures = [
        m for m in failure_matches if m["node"] == "null"
    ]

    source_has_set_before_request = "discoveryNode.set(remoteNode);" in source and "requestPeers();" in source
    source_has_failure_remove = 'logger.debug(() -> new ParameterizedMessage("{} connection failed", Peer.this), e);' in source and \
        "peersByAddress.remove(transportAddress, Peer.this);" in source

    result = (
        "single_peer_direct_full_connect_remote_eof_maps_to_peerfinder_connect_to_remote_master_failure_branch"
        if source_has_set_before_request
        and source_has_failure_remove
        and len(direct_full_connect) > 0
        and len(remote_eof_before_post) == len(direct_full_connect)
        and failure_addresses == ["127.0.0.1:57743"]
        and len(null_discovery_failures) >= len(direct_full_connect)
        else "single_peer_remote_eof_to_peerfinder_failure_mapping_not_fully_established"
    )

    print(json.dumps({
        "source_sets_discovery_node_before_request_peers": source_has_set_before_request,
        "source_failure_branch_removes_peer": source_has_failure_remove,
        "direct_full_connect_count": len(direct_full_connect),
        "remote_eof_before_post_request_count": len(remote_eof_before_post),
        "peerfinder_connection_failed_count": len(failure_matches),
        "peerfinder_connection_failed_addresses": failure_addresses,
        "null_discovery_connection_failed_count": len(null_discovery_failures),
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
