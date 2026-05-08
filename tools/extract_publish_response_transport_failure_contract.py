#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_publish_response_transport_failure_contract.py "
            "<Publication.java>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")

    result = {
        "publish_response_on_response_sets_waiting_for_quorum": (
            "state = PublicationTargetState.WAITING_FOR_QUORUM;" in source
            and "handlePublishResponse(response.getPublishResponse());" in source
        ),
        "publish_response_on_failure_requires_transport_exception": (
            "assert e instanceof TransportException;" in source
        ),
        "publish_response_on_failure_sets_failed": (
            "setFailed((Exception) exp.getRootCause());" in source
        ),
        "publish_response_on_failure_triggers_possible_commit_failure": (
            "onPossibleCommitFailure();" in source
        ),
        "publish_response_handler_contains_apply_commit_transition": (
            "void sendApplyCommit() {" in source
            and "Publication.this.sendApplyCommit(discoveryNode, applyCommitRequest.get(), new ApplyCommitResponseHandler());" in source
        ),
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
