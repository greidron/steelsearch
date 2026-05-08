#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_nio_socketchannel_open_vs_wrap_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    before_open = text.count("steelsearch_netty4_open_stage=before_open_socket_channel")
    after_open = text.count("steelsearch_netty4_open_stage=after_open_socket_channel")
    before_direct = text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_parent = text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"before_open_socket_channel={before_open}")
    print(f"after_open_socket_channel={after_open}")
    print(f"before_direct_ctor={before_direct}")
    print(f"after_direct_ctor={after_direct}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if before_open > 0 and after_open == 0:
        print("checker_result=stop_point_is_inside_SelectorProvider_openSocketChannel")
        return 0

    if after_open > 0 and before_direct > 0 and after_super_parent == 0 and after_direct == 0:
        print("checker_result=raw_socket_open_returns_and_stop_point_moves_to_parent_socket_wrapper_super_constructor")
        return 0

    if after_super_parent > 0 and after_direct == 0:
        print("checker_result=parent_socket_super_constructor_returns_and_stop_point_moves_to_post_super_wrapper_body_or_logging")
        return 0

    if after_direct > 0:
        print("checker_result=raw_socket_open_and_wrapper_constructor_return")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
