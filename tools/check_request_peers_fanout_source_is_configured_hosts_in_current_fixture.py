#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_request_peers_fanout_source_is_configured_hosts_in_current_fixture.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    probe_script = Path("/home/ubuntu/steelsearch/tools/probe_java_rust_mixed_membership.sh").read_text()
    peerfinder_source = Path("/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/discovery/PeerFinder.java").read_text()

    seed_peer_transport_address = report["seed_peer_identity"]["discovery_node"]["transport_address"]
    rust_transport_address = f"127.0.0.1:{report['steelsearch_transport_probe']['port']}"
    bootstrap_remote_nodes = report["steelsearch_bootstrap_remote_nodes"]
    membership_members = report["steelsearch_membership_members"]

    has_two_seed_hosts = 'SEEDS="127.0.0.1:${OS_TRANSPORT},127.0.0.1:${SS_TRANSPORT}"' in probe_script
    has_local_skip = 'if (transportAddress.equals(getLocalNode().getAddress())) {' in peerfinder_source
    has_cluster_manager_response_probe = "startProbe(peersRequest.getSourceNode().getAddress());" in peerfinder_source
    has_known_peers_response_probe = "peersRequest.getKnownPeers().stream().map(DiscoveryNode::getAddress).forEach(this::startProbe);" in peerfinder_source

    java_and_rust_only = sorted(member["node_name"] for member in membership_members) == ["java-primary-1", "rust-replica-1"]
    bootstrap_remote_is_only_java = len(bootstrap_remote_nodes) == 1 and bootstrap_remote_nodes[0]["transport_address"] == seed_peer_transport_address

    result = {
        "work_dir": report.get("work_dir"),
        "seed_peer_transport_address": seed_peer_transport_address,
        "rust_transport_address": rust_transport_address,
        "bootstrap_remote_nodes": bootstrap_remote_nodes,
        "membership_member_names": sorted(member["node_name"] for member in membership_members),
        "source_has_two_seed_hosts": has_two_seed_hosts,
        "source_has_local_skip": has_local_skip,
        "source_has_cluster_manager_response_probe": has_cluster_manager_response_probe,
        "source_has_known_peers_response_probe": has_known_peers_response_probe,
        "bootstrap_remote_is_only_java": bootstrap_remote_is_only_java,
        "java_and_rust_only_membership": java_and_rust_only,
        "result": (
            "configured_hosts_is_the_primary_non_local_fanout_source_in_the_current_two_node_fixture"
            if has_two_seed_hosts
            and has_local_skip
            and has_cluster_manager_response_probe
            and has_known_peers_response_probe
            and bootstrap_remote_is_only_java
            and java_and_rust_only
            else "current_fixture_does_not_yet_isolate_configured_hosts_as_the_primary_non_local_fanout_source"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith("configured_hosts_is_the_primary_non_local_fanout_source"):
        sys.exit(1)


if __name__ == "__main__":
    main()
