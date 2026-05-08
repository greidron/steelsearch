#!/usr/bin/env python3
import re
import sys
from collections import Counter
from pathlib import Path


ADD_RE = re.compile(
    r"steelsearch_transport_response_context=add requestId=\d+ action=internal:cluster/coordination/publish_state node=\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}"
)
DISCONNECTED_RE = re.compile(r"FollowersChecker.*\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}.* disconnected")
def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_publish_state_teardown_caller_after_request_add.py <opensearch-stdout.log>")
        return 2

    path = Path(sys.argv[1])
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    rust_port = None
    add_idx = None
    disconnect_idx = None
    for idx, line in enumerate(lines):
        if rust_port is None:
            m = ADD_RE.search(line)
            if m:
                rust_port = m.group(1)
                add_idx = idx
                continue
        if rust_port is not None:
            m = DISCONNECTED_RE.search(line)
            if m and m.group(1) == rust_port:
                disconnect_idx = idx
                break

    if rust_port is None or add_idx is None or disconnect_idx is None:
        print("result=missing_publish_add_or_disconnect_window")
        return 1

    gg_counts = Counter()
    ggg_counts = Counter()
    for line in lines[add_idx : disconnect_idx + 1]:
        if "steelsearch_netty4tcpchannel_close_caller" not in line:
            continue
        if f":{rust_port}]]" not in line:
            continue
        gg_marker = "callerGreatGreatGrandparent ["
        ggg_marker = "callerGreatGreatGreatGrandparent ["
        if gg_marker not in line or ggg_marker not in line:
            continue
        gg = line.split(gg_marker, 1)[1].split("]", 1)[0]
        ggg = line.split(ggg_marker, 1)[1].split("]", 1)[0]
        gg_counts[gg] += 1
        ggg_counts[ggg] += 1

    print(f"rust_port={rust_port}")
    print(f"publish_add_line={add_idx + 1}")
    print(f"first_disconnect_line={disconnect_idx + 1}")
    print(f"callerGreatGreatGrandparent_counts={dict(gg_counts)}")
    print(f"callerGreatGreatGreatGrandparent_counts={dict(ggg_counts)}")

    gg_top = gg_counts.most_common(1)
    ggg_top = ggg_counts.most_common(1)
    if gg_top and ggg_top:
        print(
            "result=publish_state_teardown_caller_after_request_add_is_"
            + gg_top[0][0].replace(":", "_")
            + "__"
            + ggg_top[0][0].replace(":", "_")
        )
        return 0

    print("result=publish_state_teardown_caller_window_empty")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
