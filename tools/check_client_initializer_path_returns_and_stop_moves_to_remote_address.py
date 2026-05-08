#!/usr/bin/env python3
import sys
from pathlib import Path


MARKERS = [
    "steelsearch_netty4_initializer_stage=client_initializer_static_init",
    "steelsearch_netty4_initializer_stage=client_initializer_instance_init",
    "steelsearch_netty4_initializer_stage=client_initializer_ctor_body",
    "steelsearch_netty4_initializer_stage=after_new_client_initializer",
    "steelsearch_netty4_initializer_stage=method_return",
    "steelsearch_netty4_open_stage=after_get_client_initializer",
    "steelsearch_netty4_open_stage=before_handler_setter",
    "steelsearch_netty4_open_stage=after_handler_setter",
    "steelsearch_netty4_open_stage=before_remote_address",
    "steelsearch_netty4_open_stage=after_remote_address",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_client_initializer_path_returns_and_stop_moves_to_remote_address.py <stdout.log>")
        return 2

    text = Path(sys.argv[1]).read_text(errors="replace")
    counts = {marker.split("=")[-1]: text.count(marker) for marker in MARKERS}
    for key, value in counts.items():
        print(f"{key}={value}")

    if (
        counts["client_initializer_static_init"] > 0
        and counts["client_initializer_instance_init"] > 0
        and counts["client_initializer_ctor_body"] > 0
        and counts["after_new_client_initializer"] > 0
        and counts["method_return"] > 0
        and counts["after_handler_setter"] > 0
        and counts["before_remote_address"] > 0
        and counts["after_remote_address"] == 0
    ):
        print(
            "checker_result=client_initializer_path_returns_fully_and_current_stop_moves_downstream_to_remoteAddress_setter"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
