#!/usr/bin/env python3
import sys
from pathlib import Path

if len(sys.argv) != 6:
    print(
        "usage: check_join_direction_points_to_source_identity_mismatch.py "
        "<main.rs> <builder.sh> <Join.java> <CoordinationState.java> <DiscoveryNode.java>",
        file=sys.stderr,
    )
    sys.exit(2)

main_rs = Path(sys.argv[1]).read_text()
builder = Path(sys.argv[2]).read_text()
join_java = Path(sys.argv[3]).read_text()
coordination = Path(sys.argv[4]).read_text()
discovery = Path(sys.argv[5]).read_text()

checks = {
    "rust_uses_local_as_join_source": "--local-id" in builder and "Optional.of(new Join(localNode, seedNode, term, lastAcceptedTerm, lastAcceptedVersion))" in builder,
    "join_source_is_vote_provider_by_source_comment": "The source node is the node that provides the vote" in join_java,
    "join_target_is_vote_target_by_source_comment": "the target node is the node for which this vote is cast" in join_java,
    "join_target_matches_only_target_id": "return targetNode.getId().equals(matchingNode.getId());" in join_java,
    "vote_collection_keys_votes_by_source_node_id": "return sourceNode.isClusterManagerNode() && nodes.put(sourceNode.getId(), sourceNode) == null;" in coordination,
    "join_votes_flow_from_join_source_node": "final boolean added = addVote(join.getSourceNode());" in coordination,
    "discovery_node_equals_uses_ephemeral_id": "return ephemeralId.equals(that.ephemeralId);" in discovery,
    "discovery_node_hashcode_uses_ephemeral_id": "return ephemeralId.hashCode();" in discovery,
}

all_required_present = all(checks.values())
for key, value in checks.items():
    print(f"{key}={str(value).lower()}")

if not all_required_present:
    print("result=missing_required_source_evidence")
    sys.exit(1)

print(
    "result=join_source_target_direction_matches_java_contract_and_remaining_risk_points_more_to_source_discoverynode_identity_semantics"
)
