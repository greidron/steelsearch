#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ACTIONS = {
    "internal:transport/handshake",
    "internal:discovery/request_peers",
    "internal:cluster/request_pre_vote",
    "internal:coordination/fault_detection/follower_check",
    "internal:cluster/coordination/publish_state",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_current_probe_has_no_nonrestart_direct_full_connect.py <report.json>")

    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []

    direct = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake")
    ]

    non_restart = []
    for entry in direct:
        end_at = entry.get("connection_end_at_ms")
        later = [
            other
            for other in capture
            if other is not entry
            and other.get("connection_started_at_ms") is not None
            and end_at is not None
            and other.get("connection_started_at_ms") > end_at
            and ((other.get("first_frame") or {}).get("action_hint") in ACTIONS)
        ]
        if not later:
            non_restart.append(entry)

    if non_restart:
        fail("current probe still contains non-restart direct full-connect entries")

    print(
        json.dumps(
            {
                "direct_full_connect_socket_count": len(direct),
                "non_restart_count": len(non_restart),
                "result": (
                    "current_probe_no_longer_contains_the_single_nonrestart_direct_full_connect_"
                    "exception_case"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
