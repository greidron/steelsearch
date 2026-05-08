#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_register_vs_connect_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    enter = text.count("steelsearch_netty4_open_stage=initiateChannel_enter")
    before_register = text.count("steelsearch_netty4_open_stage=before_register")
    after_register = text.count("steelsearch_netty4_open_stage=after_register")
    after_register_channel_fetch = text.count("steelsearch_netty4_open_stage=after_register_channel_fetch")
    register_channel_null = text.count("steelsearch_netty4_open_stage=register_channel_null")
    before_channel_connect = text.count("steelsearch_netty4_open_stage=before_channel_connect")
    after_channel_connect = text.count("steelsearch_netty4_open_stage=after_channel_connect")
    after_channel_fetch = text.count("steelsearch_netty4_open_stage=after_channel_fetch")
    returned = text.count("steelsearch_netty4_open_stage=initiateChannel_return")

    print(f"enter={enter}")
    print(f"before_register={before_register}")
    print(f"after_register={after_register}")
    print(f"after_register_channel_fetch={after_register_channel_fetch}")
    print(f"register_channel_null={register_channel_null}")
    print(f"before_channel_connect={before_channel_connect}")
    print(f"after_channel_connect={after_channel_connect}")
    print(f"after_channel_fetch={after_channel_fetch}")
    print(f"returned={returned}")

    if enter > 0 and before_register > 0 and after_register == 0:
        print("checker_result=stop_point_is_inside_bootstrap_register_before_future_return")
        return 0

    if after_register > 0 and after_register_channel_fetch == 0:
        print("checker_result=register_returns_but_channel_fetch_does_not_complete")
        return 0

    if after_register_channel_fetch > 0 and register_channel_null > 0:
        print("checker_result=register_returns_with_null_channel")
        return 0

    if before_channel_connect > 0 and after_channel_connect == 0:
        print("checker_result=registration_completes_and_stop_point_moves_to_channel_connect_call")
        return 0

    if after_channel_connect > 0 and returned == 0:
        print("checker_result=channel_connect_returns_but_stop_point_is_after_connect_future_before_return")
        return 0

    if returned > 0:
        print("checker_result=initiate_channel_returns")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
