#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_discovery_regression_never_enters_probe_connector.py <connector.java> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    lines = Path(sys.argv[2]).read_text().splitlines()

    source_has_probe_markers = "steelsearch_probe_stage=opened_probe_connection" in source
    marker_count = sum(1 for line in lines if "steelsearch_probe_stage=" in line)
    one_node = sum(1 for line in lines if "elected-as-cluster-manager ([1] nodes joined)" in line)

    print(f"source_has_probe_markers={source_has_probe_markers}")
    print(f"marker_count={marker_count}")
    print(f"one_node_election={one_node}")

    if source_has_probe_markers and marker_count == 0 and one_node > 0:
        print(
            "discovery_regression_never_enters_handshaking_transport_address_connector_probe_path"
        )
        return 0

    print("inconclusive_probe_connector_entry")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
