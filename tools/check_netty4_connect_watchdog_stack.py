#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_connect_watchdog_stack.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    lines = Path(sys.argv[1]).read_text().splitlines()

    fired = 0
    frames = []
    for line in lines:
        if "steelsearch_netty4_open_stage=connect_watchdog_fired" in line:
            fired += 1
        if "steelsearch_netty4_open_stage=connect_watchdog_stack frame=" in line:
            frames.append(line.split("frame=", 1)[1])

    first_frames = frames[:8]
    do_resolve = sum("Bootstrap.doResolveAndConnect" in frame for frame in frames)
    register = sum(".register(" in frame or ".register0(" in frame for frame in frames)
    selector = sum("NioEventLoop" in frame or "SingleThreadEventLoop" in frame for frame in frames)
    tcp_open = sum("Netty4Transport.initiateChannel" in frame for frame in frames)

    print(f"watchdog_fired={fired}")
    print(f"stack_frame_count={len(frames)}")
    print(f"do_resolve_frames={do_resolve}")
    print(f"register_frames={register}")
    print(f"selector_frames={selector}")
    print(f"tcp_open_frames={tcp_open}")
    for i, frame in enumerate(first_frames, start=1):
        print(f"frame_{i}={frame}")

    if fired > 0 and do_resolve > 0:
        print("checker_result=connect_blocks_inside_netty_bootstrap_doResolveAndConnect_path")
        return 0

    if fired > 0 and register > 0:
        print("checker_result=connect_blocks_inside_netty_channel_registration_path")
        return 0

    if fired > 0 and selector > 0:
        print("checker_result=connect_blocks_inside_netty_event_loop_path")
        return 0

    if fired > 0 and tcp_open > 0:
        print("checker_result=watchdog_captures_connect_caller_stack_but_lower_netty_frame_needs_manual_read")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
