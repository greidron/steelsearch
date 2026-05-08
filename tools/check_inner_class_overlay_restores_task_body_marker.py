#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_inner_class_overlay_restores_task_body_marker.py <old-stdout.log> <new-stdout.log>",
            file=sys.stderr,
        )
        return 2

    old = Path(sys.argv[1]).read_text()
    new = Path(sys.argv[2]).read_text()

    old_task_body_entry = old.count("steelsearch_connector_stage=task_body_entry")
    new_task_body_entry = new.count("steelsearch_connector_stage=task_body_entry")
    new_open_request = new.count("steelsearch_open_connection_stage=request")

    print(f"old_task_body_entry={old_task_body_entry}")
    print(f"new_task_body_entry={new_task_body_entry}")
    print(f"new_open_request={new_open_request}")

    if old_task_body_entry == 0 and new_task_body_entry > 0 and new_open_request > 0:
        print("checker_result=anonymous_inner_class_overlay_restores_connector_task_body_marker")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
