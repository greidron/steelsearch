#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def count(path: Path, needle: str) -> int:
    return path.read_text(errors='replace').count(needle)


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_publish_response_top_level_term_version_are_next_gate.py <publish_response_java> <coordination_state_java> <build_bypass_stdout> <full_inprocess_stdout>', file=sys.stderr)
        return 2

    publish_response_java = Path(sys.argv[1]).read_text(errors='replace')
    coordination_state_java = Path(sys.argv[2]).read_text(errors='replace')
    build_stdout = Path(sys.argv[3])
    full_stdout = Path(sys.argv[4])

    build_handlejoin = count(build_stdout, 'steelsearch_handleJoin_entry')
    full_handlejoin = count(full_stdout, 'steelsearch_handleJoin_entry')
    build_join_rejects = sum(
        count(build_stdout, marker)
        for marker in [
            'steelsearch_handleJoin_rejection_class=term_mismatch',
            'steelsearch_handleJoin_rejection_class=term_not_incremented_after_reboot',
            'steelsearch_handleJoin_rejection_class=better_last_accepted_term',
            'steelsearch_handleJoin_rejection_class=better_last_accepted_version',
            'steelsearch_handleJoin_rejection_class=missing_initial_configuration',
        ]
    )
    full_join_rejects = sum(
        count(full_stdout, marker)
        for marker in [
            'steelsearch_handleJoin_rejection_class=term_mismatch',
            'steelsearch_handleJoin_rejection_class=term_not_incremented_after_reboot',
            'steelsearch_handleJoin_rejection_class=better_last_accepted_term',
            'steelsearch_handleJoin_rejection_class=better_last_accepted_version',
            'steelsearch_handleJoin_rejection_class=missing_initial_configuration',
        ]
    )
    build_failures = count(build_stdout, 'steelsearch_publication_response_class=transport_failure')
    full_failures = count(full_stdout, 'steelsearch_publication_response_class=transport_failure')

    source_has_publish_response_term_version = 'private final long term;' in publish_response_java and 'private final long version;' in publish_response_java
    source_publish_acceptance_checks_election_won = 'if (electionWon == false)' in coordination_state_java
    source_publish_acceptance_checks_term = 'publishResponse.getTerm() != getCurrentTerm()' in coordination_state_java
    source_publish_acceptance_checks_version = 'publishResponse.getVersion() != lastPublishedVersion' in coordination_state_java

    print(f'build_handleJoin_entry={build_handlejoin}')
    print(f'full_handleJoin_entry={full_handlejoin}')
    print(f'build_join_rejects={build_join_rejects}')
    print(f'full_join_rejects={full_join_rejects}')
    print(f'build_transport_failures={build_failures}')
    print(f'full_transport_failures={full_failures}')
    print(f'source_has_publish_response_term_version={source_has_publish_response_term_version}')
    print(f'source_publish_acceptance_checks_election_won={source_publish_acceptance_checks_election_won}')
    print(f'source_publish_acceptance_checks_term={source_publish_acceptance_checks_term}')
    print(f'source_publish_acceptance_checks_version={source_publish_acceptance_checks_version}')

    if (
        build_handlejoin > 0
        and full_handlejoin > 0
        and build_join_rejects == 0
        and full_join_rejects == 0
        and build_failures > 0
        and full_failures > 0
        and source_has_publish_response_term_version
        and source_publish_acceptance_checks_election_won
        and source_publish_acceptance_checks_term
        and source_publish_acceptance_checks_version
    ):
        print('result=after_join_the_next_direct_gate_is_top_level_publish_response_term_version_or_election_won_not_join_fields')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
