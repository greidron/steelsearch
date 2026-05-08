#!/usr/bin/env python3
import sys
from pathlib import Path


def count(text: str, marker: str) -> int:
    return text.count(marker)


def summarize(path: str) -> dict[str, int]:
    text = Path(path).read_text()
    return {
        "task_body_entry": count(text, "steelsearch_connector_stage=task_body_entry"),
        "open_request": count(text, "steelsearch_open_connection_stage=request"),
        "before_clone": count(text, "steelsearch_netty4_open_stage=before_clone"),
        "after_clone": count(text, "steelsearch_netty4_open_stage=after_clone"),
        "before_direct_ctor": count(text, "steelsearch_netty4_open_stage=before_direct_nio_ctor"),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_same_overlay_ab_points_to_runtime_nondeterminism.py <deeper-run.log> <regression-run.log>",
            file=sys.stderr,
        )
        return 2

    deeper = summarize(sys.argv[1])
    regression = summarize(sys.argv[2])

    for prefix, data in (("deeper", deeper), ("regression", regression)):
        for key, value in data.items():
            print(f"{prefix}_{key}={value}")

    same_connector_entry = (
        deeper["task_body_entry"] > 0
        and regression["task_body_entry"] > 0
        and deeper["open_request"] > 0
        and regression["open_request"] > 0
    )
    diverged_clone_boundary = deeper["after_clone"] > 0 and regression["after_clone"] == 0
    diverged_depth = deeper["before_direct_ctor"] > 0 and regression["before_direct_ctor"] == 0

    if same_connector_entry and diverged_clone_boundary and diverged_depth:
        print("checker_result=same_overlay_ab_points_to_runtime_nondeterminism_more_than_overlay_omission")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
