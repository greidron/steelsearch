#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_generic_executor_contract_points_to_wrap_or_silent_queue.py "
            "<ThreadPool.java> <OpenSearchThreadPoolExecutor.java> <TimedRunnable.java> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    threadpool = Path(sys.argv[1]).read_text()
    executor = Path(sys.argv[2]).read_text()
    timed = Path(sys.argv[3]).read_text()
    stdout = Path(sys.argv[4]).read_text()

    source_generic_silent_queue_warning = "silently queue it and not run it" in threadpool
    source_execute_wraps_context = "command = wrapRunnable(command);" in executor and "return contextHolder.preserveContext(command);" in executor
    source_timedrunnable_runs_original = "original.run();" in timed

    post_submit_sentinel_ran = stdout.count("steelsearch_connector_stage=post_submit_sentinel_ran")
    abstract_control_task_ran = stdout.count("steelsearch_connector_stage=abstract_control_task_ran")
    task_body_entry = stdout.count("steelsearch_connector_stage=task_body_entry")
    task_failure = stdout.count("steelsearch_connector_stage=task_failure")
    task_rejection = stdout.count("steelsearch_connector_stage=task_rejection")

    print(f"source_generic_silent_queue_warning={source_generic_silent_queue_warning}")
    print(f"source_execute_wraps_context={source_execute_wraps_context}")
    print(f"source_timedrunnable_runs_original={source_timedrunnable_runs_original}")
    print(f"post_submit_sentinel_ran={post_submit_sentinel_ran}")
    print(f"abstract_control_task_ran={abstract_control_task_ran}")
    print(f"task_body_entry={task_body_entry}")
    print(f"task_failure={task_failure}")
    print(f"task_rejection={task_rejection}")

    if (
        source_generic_silent_queue_warning
        and source_execute_wraps_context
        and source_timedrunnable_runs_original
        and post_submit_sentinel_ran > 0
        and abstract_control_task_ran == 0
        and task_body_entry == 0
        and task_failure == 0
        and task_rejection == 0
    ):
        print("checker_result=generic_executor_contract_points_to_preserveContext_wrap_or_silent_queue_not_explicit_rejection")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
