#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_netty4_initiate_channel_connect_boundary.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    enter = text.count("steelsearch_netty4_open_stage=initiateChannel_enter")
    before_connect = text.count("steelsearch_netty4_open_stage=before_connect")
    after_connect = text.count("steelsearch_netty4_open_stage=after_connect")
    after_channel_fetch = text.count("steelsearch_netty4_open_stage=after_channel_fetch")
    channel_null = text.count("steelsearch_netty4_open_stage=channel_null")
    returned = text.count("steelsearch_netty4_open_stage=initiateChannel_return")

    print(f"enter={enter}")
    print(f"before_connect={before_connect}")
    print(f"after_connect={after_connect}")
    print(f"after_channel_fetch={after_channel_fetch}")
    print(f"channel_null={channel_null}")
    print(f"returned={returned}")

    if enter > 0 and before_connect > 0 and after_connect == 0:
        print("checker_result=stop_point_is_inside_bootstrap_connect_call_before_future_return")
        return 0

    if after_connect > 0 and after_channel_fetch == 0:
        print("checker_result=stop_point_is_between_connect_return_and_channel_fetch")
        return 0

    if after_channel_fetch > 0 and channel_null > 0 and returned == 0:
        print("checker_result=connect_returns_but_channel_is_null_immediate_path")
        return 0

    if after_channel_fetch > 0 and channel_null == 0 and returned == 0:
        print("checker_result=connect_returns_with_non_null_channel_but_stops_before_netty_channel_wrap_return")
        return 0

    if returned > 0:
        print("checker_result=initiate_channel_returns")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
