#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_follower_check_channel_reuse.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    peer_addrs = []
    for entry in capture:
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:coordination/fault_detection/follower_check":
            peer_addrs.append(entry.get("peer_addr"))

    unique_peer_addrs = sorted({addr for addr in peer_addrs if addr})
    total = len(peer_addrs)
    unique = len(unique_peer_addrs)

    if total > 0 and total == unique:
        result = "follower_check_arrives_on_fresh_socket_every_time"
    elif total > 0 and unique < total:
        result = "follower_check_socket_reuse_observed"
    else:
        result = "no_follower_check_observed"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "follower_check_count": total,
                "unique_peer_addr_count": unique,
                "sample_peer_addrs": unique_peer_addrs[:10],
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
