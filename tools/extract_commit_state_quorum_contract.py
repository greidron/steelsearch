#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: extract_commit_state_quorum_contract.py <CoordinationState.java> <Publication.java>",
            file=sys.stderr,
        )
        return 2

    coordination_state = Path(sys.argv[1]).read_text(encoding="utf-8")
    publication = Path(sys.argv[2]).read_text(encoding="utf-8")

    result = {
        "handle_publish_response_returns_optional_apply_commit": "public Optional<ApplyCommitRequest> handlePublishResponse" in coordination_state,
        "apply_commit_emitted_only_on_publish_response_success": "return Optional.of(new ApplyCommitRequest(localNode, publishResponse.getTerm(), publishResponse.getVersion()));" in coordination_state,
        "publication_reports_non_failed_nodes_do_not_form_quorum": 'new FailedToCommitClusterStateException("non-failed nodes do not form a quorum")' in publication,
        "publication_sends_apply_commit_only_after_publish_phase": "PublicationTarget::sendApplyCommit" in publication,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
