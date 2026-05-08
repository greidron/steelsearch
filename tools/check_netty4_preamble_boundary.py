#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_preamble_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    enter = text.count("steelsearch_netty4_open_stage=initiateChannel_enter")
    before_clone = text.count("steelsearch_netty4_open_stage=before_clone")
    after_clone = text.count("steelsearch_netty4_open_stage=after_clone")
    before_handler = text.count("steelsearch_netty4_open_stage=before_handler")
    after_handler = text.count("steelsearch_netty4_open_stage=after_handler")
    before_remote = text.count("steelsearch_netty4_open_stage=before_remote_address")
    after_remote = text.count("steelsearch_netty4_open_stage=after_remote_address")
    before_ctor = text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")

    print(f"enter={enter}")
    print(f"before_clone={before_clone}")
    print(f"after_clone={after_clone}")
    print(f"before_handler={before_handler}")
    print(f"after_handler={after_handler}")
    print(f"before_remote_address={before_remote}")
    print(f"after_remote_address={after_remote}")
    print(f"before_direct_ctor={before_ctor}")

    if enter > 0 and before_clone > 0 and after_clone == 0:
        print("checker_result=stop_point_is_inside_clientBootstrap_clone")
        return 0

    if after_clone > 0 and before_handler > 0 and after_handler == 0:
        print("checker_result=clone_returns_and_stop_point_moves_to_handler_setup")
        return 0

    if after_handler > 0 and before_remote > 0 and after_remote == 0:
        print("checker_result=handler_setup_returns_and_stop_point_moves_to_remoteAddress")
        return 0

    if after_remote > 0 and before_ctor == 0:
        print("checker_result=remoteAddress_returns_but_stop_point_is_before_direct_constructor")
        return 0

    if before_ctor > 0:
        print("checker_result=preamble_completes_and_stop_point_moves_beyond_remoteAddress")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
