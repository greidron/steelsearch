#!/usr/bin/env python3
import re
import sys
from pathlib import Path


LINE_RE = re.compile(
    r"steelsearch_executor_stage=(before_super_execute|after_super_execute) "
    r"unwrapped=(connectToRemoteMasterNode\[[^\]]+\]) "
    r"isShutdown=(true|false) "
    r"isTerminating=(true|false) "
    r"isTerminated=(true|false) "
    r"queueSize=(\d+)"
    r"(?: queuedAfterSubmit=(true|false))?"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_executor_queue_and_shutdown_state_for_connector_task.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()
    before = []
    after = []
    for line in text.splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        item = {
            "stage": m.group(1),
            "isShutdown": m.group(3) == "true",
            "isTerminating": m.group(4) == "true",
            "isTerminated": m.group(5) == "true",
            "queueSize": int(m.group(6)),
            "queuedAfterSubmit": m.group(7) == "true" if m.group(7) else None,
        }
        if item["stage"] == "before_super_execute":
            before.append(item)
        else:
            after.append(item)

    before_count = len(before)
    after_count = len(after)
    before_shutdown_true = sum(1 for x in before if x["isShutdown"])
    before_terminating_true = sum(1 for x in before if x["isTerminating"])
    after_shutdown_true = sum(1 for x in after if x["isShutdown"])
    after_terminating_true = sum(1 for x in after if x["isTerminating"])
    queued_after_submit_true = sum(1 for x in after if x["queuedAfterSubmit"])

    print(f"before_count={before_count}")
    print(f"after_count={after_count}")
    print(f"before_shutdown_true={before_shutdown_true}")
    print(f"before_terminating_true={before_terminating_true}")
    print(f"after_shutdown_true={after_shutdown_true}")
    print(f"after_terminating_true={after_terminating_true}")
    print(f"queued_after_submit_true={queued_after_submit_true}")

    if after_count > 0 and queued_after_submit_true > 0:
        print("checker_result=connector_task_enters_executor_queue_with_observable_shutdown_state")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
