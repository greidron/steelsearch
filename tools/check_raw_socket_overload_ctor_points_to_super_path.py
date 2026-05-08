#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_raw_socket_overload_ctor_points_to_super_path.py <Netty4NioSocketChannel.java> <stdout.log>"
        )
        return 2

    source_text = Path(sys.argv[1]).read_text(errors="replace")
    stdout_text = Path(sys.argv[2]).read_text(errors="replace")

    has_ctor = "public Netty4NioSocketChannel(Channel parent, SocketChannel socket)" in source_text
    has_after_super_marker = "steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor" in source_text

    before_direct = stdout_text.count("steelsearch_netty4_open_stage=before_direct_nio_ctor")
    after_direct = stdout_text.count("steelsearch_netty4_open_stage=after_direct_nio_ctor")
    after_super_parent = stdout_text.count("steelsearch_netty4_nio_ctor_stage=after_super_parent_socket_ctor")

    print(f"has_ctor={has_ctor}")
    print(f"has_after_super_marker={has_after_super_marker}")
    print(f"before_direct_nio_ctor={before_direct}")
    print(f"after_direct_nio_ctor={after_direct}")
    print(f"after_super_parent_socket_ctor={after_super_parent}")

    if has_ctor and has_after_super_marker and before_direct > 0 and after_direct == 0 and after_super_parent == 0:
        print("checker_result=raw_socket_overload_ctor_stop_point_is_inside_super_parent_socket_path_before_ctor_body")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
