#!/usr/bin/env python3
import re
import sys
from pathlib import Path


PRUNE_RE = re.compile(
    r"steelsearch_transport_response_context=prune requestId=(\d+) action=internal:cluster/coordination/publish_state node=\{([^}]*)\}"
)
TIMEOUT_WARNING_RE = re.compile(r"Received response for a request that has timed out|Transport response handler not found of id")


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_publish_state_prune_tracks_connection_close_not_timeout.py <opensearch-stdout.log> <TransportService.java>"
        )
        return 2

    stdout_path = Path(sys.argv[1])
    source_path = Path(sys.argv[2])

    source = source_path.read_text(encoding="utf-8", errors="replace")
    source_on_connection_closed_prunes = "onConnectionClosed(Transport.Connection connection)" in source and "responseHandlers.prune(" in source
    source_timeout_handler_removes = "final Transport.ResponseContext<? extends TransportResponse> holder = responseHandlers.remove(requestId);" in source

    lines = stdout_path.read_text(encoding="utf-8", errors="replace").splitlines()
    timeout_warning_count = 0
    prune_count = 0
    disconnected_before_prune_count = 0

    recent_rust_disconnect_seen = False
    for line in lines:
        if TIMEOUT_WARNING_RE.search(line):
            timeout_warning_count += 1

        if "FollowersChecker" in line and "disconnected" in line and "rust-replica-1" in line:
            recent_rust_disconnect_seen = True
            continue

        m = PRUNE_RE.search(line)
        if m:
            prune_count += 1
            node = m.group(2)
            if recent_rust_disconnect_seen and "rust-replica-1" in node:
                disconnected_before_prune_count += 1

    print(f"source_on_connection_closed_prunes={source_on_connection_closed_prunes}")
    print(f"source_timeout_handler_removes={source_timeout_handler_removes}")
    print(f"prune_count={prune_count}")
    print(f"disconnected_before_prune_count={disconnected_before_prune_count}")
    print(f"timeout_warning_count={timeout_warning_count}")

    if (
        source_on_connection_closed_prunes
        and source_timeout_handler_removes
        and prune_count > 0
        and disconnected_before_prune_count == prune_count
        and timeout_warning_count == 0
    ):
        print("result=publish_state_prune_tracks_connection_close_callback_not_timeout_cleanup")
        return 0

    print("result=publish_state_prune_source_or_ordering_not_yet_decisive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
