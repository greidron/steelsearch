#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_initiate_channel_exception_boundary.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    before_initiate = text.count("steelsearch_tcp_open_stage=before_initiateChannel")
    after_initiate = text.count("steelsearch_tcp_open_stage=after_initiateChannel")
    connect_exception = text.count("steelsearch_tcp_open_stage=initiateChannel_connect_exception")
    general_exception = text.count("steelsearch_tcp_open_stage=initiateChannel_general_exception")
    netty_enter = text.count("steelsearch_netty4_open_stage=initiateChannel_enter")
    netty_return = text.count("steelsearch_netty4_open_stage=initiateChannel_return")

    print(f"before_initiate={before_initiate}")
    print(f"after_initiate={after_initiate}")
    print(f"connect_exception={connect_exception}")
    print(f"general_exception={general_exception}")
    print(f"netty_enter={netty_enter}")
    print(f"netty_return={netty_return}")

    if before_initiate > 0 and netty_enter > 0 and after_initiate == 0 and netty_return == 0:
        print("checker_result=stop_point_is_inside_or_below_netty4_initiateChannel_before_return")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
