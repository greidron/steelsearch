#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PATTERNS = {
    "handlejoin_entry": "steelsearch_handleJoin_entry",
    "publication_transport_failure": "steelsearch_publication_response_class=transport_failure",
    "cluster_manager_not_discovered": "cluster-manager not discovered yet",
    "initial_discovery_timeout": "timed out while waiting for initial discovery state",
    "named_connection_2": "node connection [2]",
}


def count_patterns(path: Path) -> dict[str, int]:
    text = path.read_text(errors="replace")
    return {key: text.count(value) for key, value in PATTERNS.items()}


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_channel_touch_experiments_deprioritize_java_patch_line.py "
            "<baseline_stdout> <global_shift_stdout> <targeted_access_stdout>",
            file=sys.stderr,
        )
        return 2

    baseline_path = Path(sys.argv[1])
    global_shift_path = Path(sys.argv[2])
    targeted_access_path = Path(sys.argv[3])

    baseline = count_patterns(baseline_path)
    global_shift = count_patterns(global_shift_path)
    targeted_access = count_patterns(targeted_access_path)

    print(f"baseline={baseline}")
    print(f"global_shift={global_shift}")
    print(f"targeted_access={targeted_access}")

    same_timeout_signature = all(
        sample["cluster_manager_not_discovered"] > 0 and sample["initial_discovery_timeout"] > 0
        for sample in (baseline, global_shift, targeted_access)
    )
    baseline_stronger_than_global = (
        baseline["handlejoin_entry"] > global_shift["handlejoin_entry"]
        and baseline["publication_transport_failure"] > global_shift["publication_transport_failure"]
    )
    global_stronger_than_targeted = (
        global_shift["handlejoin_entry"] > targeted_access["handlejoin_entry"]
        and global_shift["publication_transport_failure"] > targeted_access["publication_transport_failure"]
    )
    all_reach_named_conn2 = all(sample["named_connection_2"] > 0 for sample in (baseline, global_shift, targeted_access))

    if same_timeout_signature and baseline_stronger_than_global and global_stronger_than_targeted and all_reach_named_conn2:
        print("result=channel_touch_experiments_deprioritize_java_patch_line_and_point_back_to_native_rust_mainline")
        return 0

    print("result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
