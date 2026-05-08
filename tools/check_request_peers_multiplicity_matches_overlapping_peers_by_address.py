#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path


PATTERN = re.compile(
    r"action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\] requestId \[(\d+)\].* for \[(.*)\]$"
)


def load_rows(log_path: Path):
    rows = []
    for line in log_path.read_text(errors="replace").splitlines():
        match = PATTERN.search(line)
        if not match:
            continue
        rows.append(
            {
                "idx": int(match.group(1)),
                "type": match.group(2),
                "action": match.group(3),
                "request_id": int(match.group(4)),
                "node": match.group(5),
            }
        )
    return rows


def split_cycles(rows):
    cycles = []
    current = []
    for row in rows:
        if row["action"] == "internal:transport/handshake" and row["idx"] == 0:
            if current:
                cycles.append(current)
            current = [row]
        elif current:
            current.append(row)
    if current:
        cycles.append(current)
    return cycles


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_request_peers_multiplicity_matches_overlapping_peers_by_address.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    stdout_path = Path(report["artifacts"]["opensearch_stdout"])
    peerfinder_path = Path("/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java")

    rows = load_rows(stdout_path)
    cycles = split_cycles(rows)

    multi_request_cycles = 0
    one_named_handshake_multi_request_cycles = 0
    request_peers_gap_count = 0
    request_peers_multiplicity = Counter()

    for cycle in cycles:
        named_rows = [row for row in cycle if "rust-replica-1" in row["node"]]
        named_request_peers = [
            row for row in named_rows if row["action"] == "internal:discovery/request_peers"
        ]
        named_reg_handshakes = [
            row
            for row in named_rows
            if row["type"] == "REG" and row["action"] == "internal:transport/handshake"
        ]
        request_peers_multiplicity[len(named_request_peers)] += 1
        if len(named_request_peers) > 1:
            multi_request_cycles += 1
            request_peers_gap_count += len(named_request_peers) - 1
            if len(named_reg_handshakes) == 1:
                one_named_handshake_multi_request_cycles += 1

    source = peerfinder_path.read_text()
    has_peers_by_address_compute_if_absent = "peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer)" in source
    has_request_peers_after_connect_success = "discoveryNode.set(remoteNode);" in source and "requestPeers();" in source
    has_request_peers_in_handle_wakeup = "if (peersRequestInFlight == false) {\n                        requestPeers();" in source
    has_found_peers_distinct_by_node = ".distinct()" in source and "peersByAddress.values()" in source

    result = {
        "work_dir": report.get("work_dir"),
        "request_peers_multiplicity_per_cycle": dict(sorted(request_peers_multiplicity.items())),
        "multi_request_cycles": multi_request_cycles,
        "one_named_handshake_multi_request_cycles": one_named_handshake_multi_request_cycles,
        "request_peers_extra_send_count": request_peers_gap_count,
        "source_has_peers_by_address_compute_if_absent": has_peers_by_address_compute_if_absent,
        "source_has_request_peers_after_connect_success": has_request_peers_after_connect_success,
        "source_has_request_peers_in_handle_wakeup": has_request_peers_in_handle_wakeup,
        "source_has_found_peers_distinct_by_node": has_found_peers_distinct_by_node,
        "result": (
            "request_peers_multiplicity_best_matches_overlapping_transport_address_keyed_peers_converging_on_one_discovery_node"
            if multi_request_cycles > 0
            and multi_request_cycles == one_named_handshake_multi_request_cycles
            and has_peers_by_address_compute_if_absent
            and has_request_peers_after_connect_success
            and has_found_peers_distinct_by_node
            else "request_peers_multiplicity_is_not_yet_explained_by_overlapping_transport_address_keyed_peers"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "request_peers_multiplicity_best_matches_overlapping_transport_address_keyed_peers"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
