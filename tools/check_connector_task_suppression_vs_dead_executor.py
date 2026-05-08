#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_connector_task_suppression_vs_dead_executor.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    after_generic_execute = text.count("steelsearch_connector_stage=after_generic_execute")
    post_submit_sentinel_ran = text.count("steelsearch_connector_stage=post_submit_sentinel_ran")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")
    task_rejection = text.count("steelsearch_connector_stage=task_rejection")
    task_failure = text.count("steelsearch_connector_stage=task_failure")

    print(f"after_generic_execute={after_generic_execute}")
    print(f"post_submit_sentinel_ran={post_submit_sentinel_ran}")
    print(f"task_body_entry={task_body_entry}")
    print(f"task_rejection={task_rejection}")
    print(f"task_failure={task_failure}")

    if after_generic_execute > 0 and post_submit_sentinel_ran > 0 and task_body_entry == 0:
        print("checker_result=generic_executor_runs_sentinel_but_not_connector_task_body")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
