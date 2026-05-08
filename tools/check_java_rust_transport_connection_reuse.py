#!/usr/bin/env python3
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_transport_connection_reuse.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    interesting_actions = {
        "internal:transport/handshake",
        "internal:discovery/request_peers",
        "internal:cluster/request_pre_vote",
        "internal:coordination/fault_detection/follower_check",
    }
    action_peer_addrs = defaultdict(list)
    for entry in capture:
        first_frame = entry.get("first_frame") or {}
        action = first_frame.get("action_hint")
        if action in interesting_actions:
            peer_addr = entry.get("peer_addr")
            if peer_addr:
                action_peer_addrs[action].append(peer_addr)

    summary = {}
    all_fresh = True
    for action in sorted(interesting_actions):
        addrs = action_peer_addrs.get(action, [])
        unique_count = len(set(addrs))
        if addrs and unique_count != len(addrs):
            all_fresh = False
        summary[action] = {
            "count": len(addrs),
            "unique_peer_addr_count": unique_count,
            "sample_peer_addrs": sorted(set(addrs))[:5],
        }

    result = (
        "all_major_coordinator_actions_arrive_on_fresh_sockets"
        if all_fresh and any(summary[action]["count"] > 0 for action in summary)
        else "some_action_socket_reuse_observed_or_no_actions"
    )
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "actions": summary,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
