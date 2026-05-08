#!/usr/bin/env python3
import sys
from pathlib import Path


MARKERS = [
    "steelsearch_netty4_initializer_stage=method_entry",
    "steelsearch_netty4_initializer_stage=before_new_client_initializer",
    "steelsearch_netty4_initializer_stage=client_initializer_ctor_body",
    "steelsearch_netty4_initializer_stage=after_new_client_initializer",
    "steelsearch_netty4_initializer_stage=method_return",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_inner_class_overlay_constructor_call_boundary.py <stdout.log>")
        return 2

    text = Path(sys.argv[1]).read_text(errors="replace")
    counts = {marker.split("=")[-1]: text.count(marker) for marker in MARKERS}
    for key, value in counts.items():
        print(f"{key}={value}")

    if (
        counts["method_entry"] > 0
        and counts["before_new_client_initializer"] > 0
        and counts["client_initializer_ctor_body"] == 0
        and counts["after_new_client_initializer"] == 0
        and counts["method_return"] == 0
    ):
        print(
            "checker_result=inner_class_overlay_sample_stops_at_new_ClientChannelInitializer_call_before_ctor_body_or_return"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
