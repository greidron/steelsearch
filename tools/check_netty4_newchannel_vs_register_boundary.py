#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_newchannel_vs_register_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    enter = text.count("steelsearch_netty4_open_stage=initiateChannel_enter")
    before_new_channel = text.count("steelsearch_netty4_open_stage=before_new_channel")
    after_new_channel = text.count("steelsearch_netty4_open_stage=after_new_channel")
    before_group_register = text.count("steelsearch_netty4_open_stage=before_group_register")
    after_group_register = text.count("steelsearch_netty4_open_stage=after_group_register")
    after_register_channel_fetch = text.count("steelsearch_netty4_open_stage=after_register_channel_fetch")
    before_channel_connect = text.count("steelsearch_netty4_open_stage=before_channel_connect")
    returned = text.count("steelsearch_netty4_open_stage=initiateChannel_return")

    print(f"enter={enter}")
    print(f"before_new_channel={before_new_channel}")
    print(f"after_new_channel={after_new_channel}")
    print(f"before_group_register={before_group_register}")
    print(f"after_group_register={after_group_register}")
    print(f"after_register_channel_fetch={after_register_channel_fetch}")
    print(f"before_channel_connect={before_channel_connect}")
    print(f"returned={returned}")

    if enter > 0 and before_new_channel > 0 and after_new_channel == 0:
        print("checker_result=stop_point_is_inside_channelFactory_newChannel")
        return 0

    if after_new_channel > 0 and before_group_register > 0 and after_group_register == 0:
        print("checker_result=channel_factory_returns_and_stop_point_moves_to_group_register")
        return 0

    if after_group_register > 0 and after_register_channel_fetch == 0:
        print("checker_result=group_register_returns_but_followup_fetch_does_not_complete")
        return 0

    if before_channel_connect > 0 and returned == 0:
        print("checker_result=registration_completes_and_stop_point_moves_beyond_register")
        return 0

    if returned > 0:
        print("checker_result=initiate_channel_returns")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
