#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_full_inner_overlay_moves_stop_point_to_open_connection_callback.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")
    open_request = text.count("steelsearch_open_connection_stage=request")
    open_response = text.count("steelsearch_open_connection_stage=response")
    open_failure = text.count("steelsearch_open_connection_stage=failure")
    probe_stage = text.count("steelsearch_probe_stage=")
    connection_response = text.count("steelsearch_peerfinder_stage=connection_response")
    connection_failure = text.count("steelsearch_peerfinder_stage=connection_failure")

    print(f"task_body_entry={task_body_entry}")
    print(f"open_request={open_request}")
    print(f"open_response={open_response}")
    print(f"open_failure={open_failure}")
    print(f"probe_stage={probe_stage}")
    print(f"connection_response={connection_response}")
    print(f"connection_failure={connection_failure}")

    if task_body_entry > 0 and open_request > 0 and open_response == 0 and open_failure == 0:
        print("checker_result=full_inner_overlay_moves_stop_point_to_openConnection_callback_after_request")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
