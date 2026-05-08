#!/usr/bin/env python3
import re
import sys
from pathlib import Path


ADD_RE = re.compile(
    r"steelsearch_transport_response_context=add requestId=\d+ action=internal:cluster/coordination/publish_state node=\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}"
)
DISCONNECTED_RE = re.compile(r"FollowersChecker.*\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}.* disconnected")
EXPLICIT_RE = re.compile(r"netty4 tcp channel close completed .* R:(?:127\.0\.0\.1/)?/127\.0\.0\.1:(\d+)\]\] with hint \[explicitLocalClose\]")
CLOSEFUTURE_RE = re.compile(r"netty4 tcp channel close completed .* R:(?:127\.0\.0\.1/)?/127\.0\.0\.1:(\d+)\]\] with hint \[closeFutureIntercepted\]")
CHANNELINACTIVE_RE = re.compile(r"netty4 message channel handler channelInactive .*remoteAddress=(?:127\.0\.0\.1/)?/127\.0\.0\.1:(\d+)\]")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_rust_publish_prune_points_to_java_client_teardown.py <opensearch-stdout.log>")
        return 2

    path = Path(sys.argv[1])
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    rust_port = None
    first_disconnect_idx = None
    for idx, line in enumerate(lines):
        if rust_port is None:
            m = ADD_RE.search(line)
            if m:
                rust_port = m.group(1)
        if rust_port is not None:
            m = DISCONNECTED_RE.search(line)
            if m and m.group(1) == rust_port:
                first_disconnect_idx = idx
                break

    if rust_port is None or first_disconnect_idx is None:
        print("result=missing_rust_publish_add_or_disconnect_window")
        return 1

    explicit_before_disconnect = 0
    closefuture_before_disconnect = 0
    channelinactive_before_disconnect = 0

    for line in lines[: first_disconnect_idx + 1]:
        m = EXPLICIT_RE.search(line)
        if m and m.group(1) == rust_port:
            explicit_before_disconnect += 1
        m = CLOSEFUTURE_RE.search(line)
        if m and m.group(1) == rust_port:
            closefuture_before_disconnect += 1
        m = CHANNELINACTIVE_RE.search(line)
        if m and m.group(1) == rust_port:
            channelinactive_before_disconnect += 1

    print(f"rust_port={rust_port}")
    print(f"first_disconnect_line={first_disconnect_idx + 1}")
    print(f"explicit_before_disconnect={explicit_before_disconnect}")
    print(f"closefuture_before_disconnect={closefuture_before_disconnect}")
    print(f"channelinactive_before_disconnect={channelinactive_before_disconnect}")

    if explicit_before_disconnect > 0:
        print("result=rust_publish_prune_points_to_java_client_side_teardown_not_remote_close_first")
        return 0

    print("result=rust_publish_prune_direction_not_yet_decisive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
