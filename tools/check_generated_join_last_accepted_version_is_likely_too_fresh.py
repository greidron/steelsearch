#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_generated_join_last_accepted_version_is_likely_too_fresh.py <main.rs> <coordination_state.java> <publication.java>', file=sys.stderr)
        return 2
    main_rs = Path(sys.argv[1]).read_text()
    coordination_state = Path(sys.argv[2]).read_text()
    publication = Path(sys.argv[3]).read_text()

    rust_updates_last_accepted_on_publish = (
        'coordination_state.last_accepted_term = term;' in main_rs
        and 'coordination_state.last_accepted_version = version;' in main_rs
    )
    rust_builds_join_from_coordination_state = (
        'build_native_publish_with_join_response_payload(' in main_rs
        and 'Optional.of(new Join(localNode, seedNode, term, lastAcceptedTerm, lastAcceptedVersion))' in Path('tools/build_java_publish_with_join_response.sh').read_text()
    )
    java_rejects_better_last_accepted_version = (
        'join.getLastAcceptedTerm() == lastAcceptedTerm && join.getLastAcceptedVersion() > getLastAcceptedVersionOrMetadataVersion()' in coordination_state
    )
    java_handles_join_before_publish_response = (
        'onJoin(join);' in publication and 'handlePublishResponse(response.getPublishResponse());' in publication
        and publication.index('onJoin(join);') < publication.index('handlePublishResponse(response.getPublishResponse());')
    )

    result = (
        'generated_join_lastAcceptedVersion_is_the_most_likely_semantic_mismatch_because_rust_advertises_the_fresh_publish_version_before_java_accepts_it'
        if rust_updates_last_accepted_on_publish
        and rust_builds_join_from_coordination_state
        and java_rejects_better_last_accepted_version
        and java_handles_join_before_publish_response
        else 'inconclusive'
    )

    print({
        'rust_updates_last_accepted_on_publish': rust_updates_last_accepted_on_publish,
        'rust_builds_join_from_coordination_state': rust_builds_join_from_coordination_state,
        'java_rejects_better_last_accepted_version': java_rejects_better_last_accepted_version,
        'java_handles_join_before_publish_response': java_handles_join_before_publish_response,
        'result': result,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
