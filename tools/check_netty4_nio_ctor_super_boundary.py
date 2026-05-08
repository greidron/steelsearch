#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_netty4_nio_ctor_super_boundary.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text()

    before_direct = text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_default = text.count("steelsearch_netty4_nio_ctor_stage=after_super_default_ctor")
    after_super_parent = text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"before_direct_ctor={before_direct}")
    print(f"after_direct_ctor={after_direct}")
    print(f"after_super_default_ctor={after_super_default}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if before_direct > 0 and after_super_default == 0 and after_direct == 0:
        print("checker_result=stop_point_is_inside_NioSocketChannel_super_constructor_before_Netty4NioSocketChannel_body")
        return 0

    if after_super_default > 0 and after_direct == 0:
        print("checker_result=super_constructor_returns_and_stop_point_moves_to_Netty4NioSocketChannel_post_super_body_or_logging")
        return 0

    if after_direct > 0:
        print("checker_result=direct_netty4_nio_constructor_returns")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
