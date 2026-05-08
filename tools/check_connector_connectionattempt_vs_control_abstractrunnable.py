#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_connector_connectionattempt_vs_control_abstractrunnable.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    post_submit_sentinel_ran = text.count("steelsearch_connector_stage=post_submit_sentinel_ran")
    abstract_control_task_ran = text.count("steelsearch_connector_stage=abstract_control_task_ran")
    abstract_control_task_failure = text.count("steelsearch_connector_stage=abstract_control_task_failure")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")
    task_failure = text.count("steelsearch_connector_stage=task_failure")
    task_rejection = text.count("steelsearch_connector_stage=task_rejection")

    print(f"post_submit_sentinel_ran={post_submit_sentinel_ran}")
    print(f"abstract_control_task_ran={abstract_control_task_ran}")
    print(f"abstract_control_task_failure={abstract_control_task_failure}")
    print(f"task_body_entry={task_body_entry}")
    print(f"task_failure={task_failure}")
    print(f"task_rejection={task_rejection}")

    if post_submit_sentinel_ran > 0 and abstract_control_task_ran > 0 and task_body_entry == 0:
        print("checker_result=generic_executor_runs_control_abstractrunnable_but_not_connectionattempt")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
