#!/usr/bin/env python3
import re
import sys
from pathlib import Path


ADD_RE = re.compile(
    r"steelsearch_transport_response_context=add requestId=\d+ action=internal:cluster/coordination/publish_state node=\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}"
)
DISCONNECTED_RE = re.compile(r"FollowersChecker.*\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(\d+)\}.* disconnected")
OBSERVED_CLOSE_RE = re.compile(
    r"node connection \[2\] observed close on channelIndex \[(\d+)\].*remoteAddress=127\.0\.0\.1/127\.0\.0\.1:(\d+).*closeOrder \[(\d+)\]"
)
HINT_RE = re.compile(
    r"netty4 tcp channel close completed .*L:/127\.0\.0\.1:(\d+) ! R:127\.0\.0\.1/127\.0\.0\.1:(\d+)\]\] with hint \[(explicitLocalClose|closeFutureIntercepted)\]"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_publish_state_fanout_starter_hint.py <opensearch-stdout.log>")
        return 2

    lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()

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

    observed = []
    hints_by_local_port = {}
    for line in lines[add_idx : disconnect_idx + 1]:
        m = OBSERVED_CLOSE_RE.search(line)
        if m and m.group(2) == rust_port:
            observed.append((int(m.group(3)), int(m.group(1)), line))
        m = HINT_RE.search(line)
        if m and m.group(2) == rust_port:
            hints_by_local_port[m.group(1)] = m.group(3)

    observed.sort()
    first_three = []
    closefuture_first_count = 0
    explicit_first_count = 0
    for close_order, channel_index, line in observed[:3]:
        local_port = line.split("localAddress=/127.0.0.1:", 1)[1].split(",", 1)[0]
        hint = hints_by_local_port.get(local_port, "unknown")
        first_three.append((close_order, channel_index, local_port, hint))
        if hint == "closeFutureIntercepted":
            closefuture_first_count += 1
        elif hint == "explicitLocalClose":
            explicit_first_count += 1

    print(f"rust_port={rust_port}")
    print(f"publish_add_line={add_idx + 1}")
    print(f"first_disconnect_line={disconnect_idx + 1}")
    print(f"first_three={first_three}")
    print(f"closefuture_first_count={closefuture_first_count}")
    print(f"explicit_first_count={explicit_first_count}")

    if first_three and closefuture_first_count >= 2 and explicit_first_count == 0:
        print("result=publish_state_fanout_starter_is_closefutureintercepted_edge_slot_not_explicitlocalclose")
        return 0

    print("result=publish_state_fanout_starter_not_yet_decisive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
