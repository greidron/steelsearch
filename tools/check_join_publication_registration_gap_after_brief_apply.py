#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def count(lines, pattern):
    rx = re.compile(pattern)
    return sum(1 for line in lines if rx.search(line))


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_join_publication_registration_gap_after_brief_apply.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text().splitlines()

    rust_join = count(lines, r"steelsearch_handleJoin_entry .*sourceNode=\{rust-replica-1\}")
    rust_publish_accepted = count(
        lines,
        r"steelsearch_handlePublishResponse_gate=accepted .*sourceNode=\{rust-replica-1\}",
    )
    cluster_applier_added_rust = count(
        lines,
        r"ClusterApplierService.*added \{\{rust-replica-1\}",
    )
    rust_transport_failure = count(
        lines,
        r"steelsearch_publication_response_class=transport_failure .*discoveryNode=\{rust-replica-1\}",
    )
    quorum_failure = count(lines, r"non-failed nodes do not form a quorum")
    java_only_reelection = count(
        lines,
        r"elected-as-cluster-manager .*\{previous \[\], current \[\{java-primary-1\}",
    )

    print(f"rust_join={rust_join}")
    print(f"rust_publish_accepted={rust_publish_accepted}")
    print(f"cluster_applier_added_rust={cluster_applier_added_rust}")
    print(f"rust_transport_failure={rust_transport_failure}")
    print(f"quorum_failure={quorum_failure}")
    print(f"java_only_reelection={java_only_reelection}")

    if (
        rust_join > 0
        and rust_publish_accepted > 0
        and cluster_applier_added_rust > 0
        and rust_transport_failure > 0
        and quorum_failure > 0
        and java_only_reelection > 0
    ):
        print(
            "join_publication_briefly_registers_rust_but_repeated_publish_disconnect_and_quorum_failure_prevent_persistent_cluster_state_registration"
        )
        return 0

    print("inconclusive_join_publication_registration_gap")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
