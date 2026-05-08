#!/usr/bin/env python3
import sys
from pathlib import Path


def count(text: str, marker: str) -> int:
    return text.count(marker)


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: check_same_marker_initializer_boundary_points_to_constructor.py <Netty4Transport.java> <stdout.log>..."
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    source_has_ctor_call = "ClientChannelInitializer initializer = new ClientChannelInitializer();" in source
    source_returns_initializer = "return initializer;" in source
    print(f"source_has_ctor_call={source_has_ctor_call}")
    print(f"source_returns_initializer={source_returns_initializer}")

    after_clone_samples = 0
    before_get = 0
    after_get = 0
    any_after_handler = False

    for raw_path in sys.argv[2:]:
        path = Path(raw_path)
        text = path.read_text(errors="replace")
        c_after_clone = count(text, "steelsearch_netty4_open_stage=after_clone")
        c_before_get = count(text, "steelsearch_netty4_open_stage=before_get_client_initializer")
        c_after_get = count(text, "steelsearch_netty4_open_stage=after_get_client_initializer")
        c_after_handler = count(text, "steelsearch_netty4_open_stage=after_handler_setter")
        print(path)
        print(f"  after_clone={c_after_clone}")
        print(f"  before_get_client_initializer={c_before_get}")
        print(f"  after_get_client_initializer={c_after_get}")
        print(f"  after_handler_setter={c_after_handler}")
        if c_after_clone:
            after_clone_samples += 1
        if c_before_get:
            before_get += 1
        if c_after_get:
            after_get += 1
        if c_after_handler:
            any_after_handler = True

    print(f"after_clone_sample_count={after_clone_samples}")
    print(f"before_get_client_initializer_count={before_get}")
    print(f"after_get_client_initializer_count={after_get}")
    print(f"any_after_handler_setter={any_after_handler}")

    if source_has_ctor_call and source_returns_initializer and before_get > 0 and after_get == 0 and not any_after_handler:
        print(
            "checker_result=same_marker_initializer_boundary_points_to_ClientChannelInitializer_construction_not_handler_path"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
