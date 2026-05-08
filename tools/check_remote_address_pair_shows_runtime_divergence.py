#!/usr/bin/env python3
import sys
from pathlib import Path


MARKERS = [
    "steelsearch_netty4_initializer_stage=client_initializer_static_init",
    "steelsearch_netty4_initializer_stage=client_initializer_instance_init",
    "steelsearch_netty4_initializer_stage=client_initializer_ctor_body",
    "steelsearch_netty4_initializer_stage=after_new_client_initializer",
    "steelsearch_netty4_initializer_stage=method_return",
    "steelsearch_netty4_open_stage=after_handler_setter",
    "steelsearch_netty4_open_stage=before_remote_address",
    "steelsearch_netty4_open_stage=after_remote_address",
]


def counts(path: Path) -> dict[str, int]:
    text = path.read_text(errors="replace")
    return {marker.split("=")[-1]: text.count(marker) for marker in MARKERS}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_remote_address_pair_shows_runtime_divergence.py <before_only.log> <after.log>")
        return 2

    left = counts(Path(sys.argv[1]))
    right = counts(Path(sys.argv[2]))

    print("left_sample")
    for key, value in left.items():
        print(f"  {key}={value}")
    print("right_sample")
    for key, value in right.items():
        print(f"  {key}={value}")

    prefix_keys = [
        "client_initializer_static_init",
        "client_initializer_instance_init",
        "client_initializer_ctor_body",
        "after_new_client_initializer",
        "method_return",
        "after_handler_setter",
        "before_remote_address",
    ]
    same_prefix = all(left[key] > 0 and right[key] > 0 for key in prefix_keys)
    diverged_at_after_remote = left["after_remote_address"] == 0 and right["after_remote_address"] > 0

    print(f"same_prefix={same_prefix}")
    print(f"diverged_at_after_remote={diverged_at_after_remote}")

    if same_prefix and diverged_at_after_remote:
        print("checker_result=remoteAddress_boundary_has_actual_runtime_divergence_not_just_missing_prefix_markers")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
