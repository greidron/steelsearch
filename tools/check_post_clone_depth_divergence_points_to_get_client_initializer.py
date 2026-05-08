#!/usr/bin/env python3
import sys
from pathlib import Path


MARKERS = [
    "steelsearch_netty4_open_stage=before_clone",
    "steelsearch_netty4_open_stage=after_clone",
    "steelsearch_netty4_open_stage=before_get_client_initializer",
    "steelsearch_netty4_open_stage=after_get_client_initializer",
    "steelsearch_netty4_open_stage=before_handler_setter",
    "steelsearch_netty4_open_stage=after_handler_setter",
    "steelsearch_netty4_open_stage=before_remote_address",
    "steelsearch_netty4_open_stage=after_remote_address",
    "steelsearch_netty4_open_stage=before_open_socket_channel",
    "steelsearch_netty4_open_stage=before_direct_nio_ctor",
]


def marker_counts(path: Path) -> dict[str, int]:
    text = path.read_text(errors="replace")
    return {marker.split("=")[-1]: text.count(marker) for marker in MARKERS}


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: check_post_clone_depth_divergence_points_to_get_client_initializer.py <stdout.log>..."
        )
        return 2

    samples = []
    for raw_path in sys.argv[1:]:
        path = Path(raw_path)
        counts = marker_counts(path)
        samples.append((path, counts))
        print(path)
        for key, value in counts.items():
            if value:
                print(f"  {key}={value}")

    after_clone_samples = [counts for _, counts in samples if counts["after_clone"] > 0]
    before_get_client_initializer = sum(
        1 for counts in after_clone_samples if counts["before_get_client_initializer"] > 0
    )
    after_get_client_initializer = sum(
        1 for counts in after_clone_samples if counts["after_get_client_initializer"] > 0
    )
    any_after_handler = any(counts["after_handler_setter"] > 0 for counts in after_clone_samples)
    any_before_direct_ctor = any(counts["before_direct_nio_ctor"] > 0 for counts in after_clone_samples)

    print(f"after_clone_sample_count={len(after_clone_samples)}")
    print(f"before_get_client_initializer_count={before_get_client_initializer}")
    print(f"after_get_client_initializer_count={after_get_client_initializer}")
    print(f"any_after_handler_setter={any_after_handler}")
    print(f"any_before_direct_nio_ctor={any_before_direct_ctor}")

    if (
        after_clone_samples
        and before_get_client_initializer > 0
        and after_get_client_initializer == 0
        and not any_after_handler
        and not any_before_direct_ctor
    ):
        print(
            "checker_result=post_clone_depth_divergence_now_points_to_getClientChannelInitializer_entry_exit_boundary"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
