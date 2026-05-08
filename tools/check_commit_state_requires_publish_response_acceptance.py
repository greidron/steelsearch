#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_commit_state_requires_publish_response_acceptance.py <artifact.json> <coordination_state.java> <publication_transport_handler.java>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout = (Path(artifact['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    coordination_state = Path(sys.argv[2]).read_text()
    publication_handler = Path(sys.argv[3]).read_text()

    source_commit_created_on_quorum = 'if (isPublishQuorum(publishVotes))' in coordination_state and 'return Optional.of(new ApplyCommitRequest(' in coordination_state
    source_publish_reads_publishwithjoin = 'return new PublishWithJoinResponse(in);' in publication_handler

    accepted_publish_response_count = stdout.count('handlePublishResponse: accepted publish response')
    committed_value_count = stdout.count('handlePublishResponse: value committed')
    failed_to_commit_cluster_state_count = stdout.count('failed to commit cluster state')
    publish_response_from_count = stdout.count('publish response from')

    result = (
        'missing_commit_state_best_matches_missing_publish_response_acceptance_or_quorum_precondition_not_first_frame_commit_handler'
        if source_commit_created_on_quorum
        and source_publish_reads_publishwithjoin
        and accepted_publish_response_count == 0
        and committed_value_count == 0
        and failed_to_commit_cluster_state_count > 0
        else 'inconclusive'
    )

    print({
        'work_dir': artifact['work_dir'],
        'failure_stage': artifact.get('failure_stage'),
        'blocker_class': artifact.get('blocker_class'),
        'source_commit_created_on_quorum': source_commit_created_on_quorum,
        'source_publish_reads_publishwithjoin': source_publish_reads_publishwithjoin,
        'accepted_publish_response_count': accepted_publish_response_count,
        'committed_value_count': committed_value_count,
        'publish_response_from_count': publish_response_from_count,
        'failed_to_commit_cluster_state_count': failed_to_commit_cluster_state_count,
        'result': result,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
