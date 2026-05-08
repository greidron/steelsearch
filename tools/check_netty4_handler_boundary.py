#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_handler_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    after_clone = text.count("steelsearch_netty4_open_stage=after_clone")
    before_get = text.count("steelsearch_netty4_open_stage=before_get_client_initializer")
    after_get = text.count("steelsearch_netty4_open_stage=after_get_client_initializer")
    before_setter = text.count("steelsearch_netty4_open_stage=before_handler_setter")
    after_setter = text.count("steelsearch_netty4_open_stage=after_handler_setter")
    before_remote = text.count("steelsearch_netty4_open_stage=before_remote_address")

    print(f"after_clone={after_clone}")
    print(f"before_get_client_initializer={before_get}")
    print(f"after_get_client_initializer={after_get}")
    print(f"before_handler_setter={before_setter}")
    print(f"after_handler_setter={after_setter}")
    print(f"before_remote_address={before_remote}")

    if after_clone > 0 and before_get > 0 and after_get == 0:
        print("checker_result=stop_point_is_inside_getClientChannelInitializer")
        return 0

    if after_get > 0 and before_setter > 0 and after_setter == 0:
        print("checker_result=initializer_returns_and_stop_point_moves_to_Bootstrap_handler_setter")
        return 0

    if after_setter > 0 and before_remote == 0:
        print("checker_result=handler_setter_returns_but_stop_point_is_before_remoteAddress")
        return 0

    if before_remote > 0:
        print("checker_result=handler_path_completes_and_stop_point_moves_beyond_handler_setup")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
