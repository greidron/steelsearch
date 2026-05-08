#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_context_wrapper_reaches_inner_dorun_boundary.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    before_execute_connector = text.count("unwrapped=connectToRemoteMasterNode[")
    timed_before_original_run = text.count("steelsearch_timed_runnable_stage=before_original_run")
    context_doRun_entry = text.count("steelsearch_context_preserving_stage=doRun_entry")
    context_after_stash = text.count("steelsearch_context_preserving_stage=after_stash")
    context_after_restore = text.count("steelsearch_context_preserving_stage=after_restore")
    context_before_inner_dorun = text.count("steelsearch_context_preserving_stage=before_inner_doRun")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")

    print(f"before_execute_connector={before_execute_connector}")
    print(f"timed_before_original_run={timed_before_original_run}")
    print(f"context_doRun_entry={context_doRun_entry}")
    print(f"context_after_stash={context_after_stash}")
    print(f"context_after_restore={context_after_restore}")
    print(f"context_before_inner_dorun={context_before_inner_dorun}")
    print(f"task_body_entry={task_body_entry}")

    if context_before_inner_dorun > 0 and task_body_entry == 0:
        print("checker_result=context_wrapper_reaches_inner_dorun_boundary_but_original_task_body_never_logs")
        return 0

    if timed_before_original_run > 0 and context_doRun_entry == 0:
        print("checker_result=timed_runnable_calls_original_run_but_context_wrapper_never_enters")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
