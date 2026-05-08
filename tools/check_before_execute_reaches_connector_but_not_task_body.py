#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_before_execute_reaches_connector_but_not_task_body.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    before_execute_connector = text.count("unwrapped=connectToRemoteMasterNode[")
    before_execute_plain = text.count("unwrapped=steelsearch_plain_sentinel")
    before_execute_abstract_control = text.count("unwrapped=steelsearch_abstract_control")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")
    task_failure = text.count("steelsearch_connector_stage=task_failure")
    task_rejection = text.count("steelsearch_connector_stage=task_rejection")

    print(f"before_execute_connector={before_execute_connector}")
    print(f"before_execute_plain={before_execute_plain}")
    print(f"before_execute_abstract_control={before_execute_abstract_control}")
    print(f"task_body_entry={task_body_entry}")
    print(f"task_failure={task_failure}")
    print(f"task_rejection={task_rejection}")

    if before_execute_connector > 0 and task_body_entry == 0 and task_failure == 0 and task_rejection == 0:
        print("checker_result=connector_reaches_beforeExecute_but_not_original_doRun")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
