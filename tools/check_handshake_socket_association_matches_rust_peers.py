#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_handshake_socket_association_matches_rust_peers.py "
            "<opensearch-stdout.log> <transport-seed-capture.json>",
            file=sys.stderr,
        )
        return 2

    stdout_path = Path(sys.argv[1])
    capture_path = Path(sys.argv[2])

    stdout = stdout_path.read_text(errors="replace")
    capture = json.loads(capture_path.read_text())

    java_local_ports = {
        int(match.group(1))
        for match in re.finditer(
            r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
            r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ "
            r"bytesLength=55",
            stdout,
        )
    }

    rust_peer_ports = set()
    for entry in capture:
        first_frame = entry.get("first_frame") or {}
        if first_frame.get("action_hint") != "internal:tcp/handshake":
            continue
        peer_addr = entry.get("peer_addr") or ""
        if ":" not in peer_addr:
            continue
        rust_peer_ports.add(int(peer_addr.rsplit(":", 1)[1]))

    overlap = java_local_ports & rust_peer_ports
    only_java = sorted(java_local_ports - rust_peer_ports)
    only_rust = sorted(rust_peer_ports - java_local_ports)

    print(f"java_low_level_handshake_write_ports={len(java_local_ports)}")
    print(f"rust_tcp_handshake_peer_ports={len(rust_peer_ports)}")
    print(f"overlap_ports={len(overlap)}")
    print(f"java_only_ports={only_java}")
    print(f"rust_only_ports={only_rust}")

    if len(java_local_ports) == 0 or len(rust_peer_ports) == 0:
        print("checker_result=inconclusive_missing_socket_sets")
        return 1

    if len(overlap) >= min(len(java_local_ports), len(rust_peer_ports)) - 1:
        print(
            "checker_result="
            "connection_association_matches_same_client_sockets_"
            "so_sibling_socket_mismatch_is_unlikely"
        )
        return 0

    print("checker_result=socket_sets_diverge_more_than_expected")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
