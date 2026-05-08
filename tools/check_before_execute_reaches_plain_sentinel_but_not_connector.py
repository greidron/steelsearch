#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_before_execute_reaches_plain_sentinel_but_not_connector.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    before_execute_connector = text.count("steelsearch_executor_stage=before_execute thread=") and text.count("unwrapped=connectToRemoteMasterNode[")
    before_execute_plain = text.count("unwrapped=steelsearch_plain_sentinel")
    before_execute_abstract_control = text.count("unwrapped=steelsearch_abstract_control")
    task_body_entry = text.count("steelsearch_connector_stage=task_body_entry")

    print(f"before_execute_connector={text.count('unwrapped=connectToRemoteMasterNode[')}")
    print(f"before_execute_plain={before_execute_plain}")
    print(f"before_execute_abstract_control={before_execute_abstract_control}")
    print(f"task_body_entry={task_body_entry}")

    if before_execute_plain > 0 and before_execute_abstract_control == 0 and task_body_entry == 0:
        print("checker_result=beforeExecute_reaches_plain_sentinel_but_not_abstract_control_or_connector")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
