#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_publish_target_failure_contract.py <Publication.java>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    result = {
        "publish_response_failure_sets_target_failed": "setFailed((Exception) exp.getRootCause());" in source,
        "publish_response_failure_triggers_possible_commit_failure": "onPossibleCommitFailure();" in source,
        "faulty_node_marks_target_failed": 'setFailed(new OpenSearchException("faulty node"));' in source,
        "failed_target_acks_once": "ackListener.onNodeAck(discoveryNode, e);" in source,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
