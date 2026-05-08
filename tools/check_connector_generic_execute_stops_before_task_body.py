#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_connector_generic_execute_stops_before_task_body.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    method_entry = text.count("steelsearch_connector_stage=method_entry")
    before_generic_execute = text.count("steelsearch_connector_stage=before_generic_execute")
    after_generic_execute = text.count("steelsearch_connector_stage=after_generic_execute")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")
    task_rejection = text.count("steelsearch_connector_stage=task_rejection")
    task_failure = text.count("steelsearch_connector_stage=task_failure")
    open_connection_request = text.count("steelsearch_open_connection_stage=request")

    print(f"method_entry={method_entry}")
    print(f"before_generic_execute={before_generic_execute}")
    print(f"after_generic_execute={after_generic_execute}")
    print(f"task_body_entry={task_body_entry}")
    print(f"task_rejection={task_rejection}")
    print(f"task_failure={task_failure}")
    print(f"open_connection_request={open_connection_request}")

    if method_entry > 0 and before_generic_execute > 0 and after_generic_execute > 0 and task_body_entry == 0 and task_rejection == 0:
        print("checker_result=connector_generic_execute_returns_but_task_body_never_starts")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
