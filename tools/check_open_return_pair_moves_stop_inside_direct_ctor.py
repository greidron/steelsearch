#!/usr/bin/env python3
import sys
from pathlib import Path

PREFIXES = [
    "steelsearch_connector_stage=task_body_entry",
    "steelsearch_open_connection_stage=request",
    "steelsearch_netty4_open_stage=before_clone",
    "steelsearch_netty4_open_stage=after_clone",
    "steelsearch_netty4_open_stage=before_get_client_initializer",
    "steelsearch_netty4_open_stage=after_get_client_initializer",
    "steelsearch_netty4_open_stage=before_handler_setter",
    "steelsearch_netty4_open_stage=after_handler_setter",
    "steelsearch_netty4_open_stage=before_remote_address",
    "steelsearch_netty4_open_stage=after_remote_address",
    "steelsearch_netty4_open_stage=before_open_socket_channel",
]


def count(text: str, marker: str) -> int:
    return text.count(marker)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_open_return_pair_moves_stop_inside_direct_ctor.py <left.log> <right.log>")
        return 2

    left = Path(sys.argv[1]).read_text(errors="replace")
    right = Path(sys.argv[2]).read_text(errors="replace")

    same_prefix = all(count(left, marker) > 0 and count(right, marker) > 0 for marker in PREFIXES)
    left_after_open = count(left, "steelsearch_netty4_open_stage=after_open_socket_channel")
    right_after_open = count(right, "steelsearch_netty4_open_stage=after_open_socket_channel")
    right_before_direct = count(right, "steelsearch_netty4_open_stage=before_direct_nio_ctor")
    right_after_direct = count(right, "steelsearch_netty4_open_stage=after_direct_nio_ctor")

    print(f"same_prefix={same_prefix}")
    print(f"left_after_open_socket_channel={left_after_open}")
    print(f"right_after_open_socket_channel={right_after_open}")
    print(f"right_before_direct_nio_ctor={right_before_direct}")
    print(f"right_after_direct_nio_ctor={right_after_direct}")

    if same_prefix and left_after_open == 0 and right_after_open > 0 and right_before_direct > 0 and right_after_direct == 0:
        print(
            "checker_result=open_return_pair_shows_divergence_at_after_open_and_moves_current_stop_inside_direct_nio_ctor_body"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
