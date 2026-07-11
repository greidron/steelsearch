#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_publish_with_join_gap_points_to_semantic_not_wire_mismatch.py <artifact.json> <main.rs> <build_java_publish_with_join_response.sh>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout = (Path(artifact['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    main_rs = Path(sys.argv[2]).read_text()
    script = Path(sys.argv[3]).read_text()

    source_uses_native_builder = 'build_native_publish_with_join_response_payload(' in main_rs
    source_can_force_java_builder = 'STEELSEARCH_USE_JAVA_PUBLISH_WITH_JOIN_BUILDER' in main_rs
    script_builds_publish_with_join = 'new PublishWithJoinResponse(' in script
    script_always_includes_join = 'Optional.of(new Join(' in script

    accepted_publish_response_count = stdout.count('handlePublishResponse: accepted publish response')
    committed_value_count = stdout.count('handlePublishResponse: value committed')
    failed_to_commit_cluster_state_count = stdout.count('failed to commit cluster state')

    result = (
        'publish_with_join_gap_points_more_to_semantic_join_or_quorum_mismatch_than_to_missing_java_compatible_wire_builder'
        if source_uses_native_builder
        and source_can_force_java_builder
        and script_builds_publish_with_join
        and script_always_includes_join
        and accepted_publish_response_count == 0
        and committed_value_count == 0
        and failed_to_commit_cluster_state_count > 0
        else 'inconclusive'
    )

    print({
        'work_dir': artifact['work_dir'],
        'source_uses_native_builder': source_uses_native_builder,
        'source_can_force_java_builder': source_can_force_java_builder,
        'script_builds_publish_with_join': script_builds_publish_with_join,
        'script_always_includes_join': script_always_includes_join,
        'accepted_publish_response_count': accepted_publish_response_count,
        'committed_value_count': committed_value_count,
        'failed_to_commit_cluster_state_count': failed_to_commit_cluster_state_count,
        'result': result,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
