#!/usr/bin/env python3
import re
import sys
from pathlib import Path


LINE_RE = re.compile(
    r"steelsearch_executor_stage=after_super_execute "
    r"unwrapped=connectToRemoteMasterNode\[[^\]]+\] "
    r"isShutdown=(true|false) "
    r"isTerminating=(true|false) "
    r"isTerminated=(true|false) "
    r"queueSize=(\d+) "
    r"queuedAfterSubmit=(true|false)"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_executor_submit_points_away_from_shutdown_queue_edge.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()
    matches = [LINE_RE.search(line) for line in text.splitlines()]
    matches = [m for m in matches if m]

    after_count = len(matches)
    shutdown_true = sum(1 for m in matches if m.group(1) == "true")
    terminating_true = sum(1 for m in matches if m.group(2) == "true")
    terminated_true = sum(1 for m in matches if m.group(3) == "true")
    queued_after_submit_true = sum(1 for m in matches if m.group(5) == "true")

    print(f"after_count={after_count}")
    print(f"shutdown_true={shutdown_true}")
    print(f"terminating_true={terminating_true}")
    print(f"terminated_true={terminated_true}")
    print(f"queued_after_submit_true={queued_after_submit_true}")

    if after_count > 0 and shutdown_true == 0 and terminating_true == 0 and terminated_true == 0 and queued_after_submit_true == 0:
        print("checker_result=executor_submit_points_away_from_shutdown_queue_edge_and_toward_direct_handoff_or_worker_start_gap")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
