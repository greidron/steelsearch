#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PATTERNS = [
    'steelsearch_handleJoin_entry',
    'steelsearch_handleJoin_rejection_class=term_mismatch',
    'steelsearch_handleJoin_rejection_class=term_not_incremented_after_reboot',
    'steelsearch_handleJoin_rejection_class=better_last_accepted_term',
    'steelsearch_handleJoin_rejection_class=better_last_accepted_version',
    'steelsearch_handleJoin_rejection_class=missing_initial_configuration',
    'steelsearch_publication_response_class=missing_join',
]


def counts(path: Path) -> dict[str, int]:
    text = path.read_text(errors='replace')
    return {pat: text.count(pat) for pat in PATTERNS}


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_join_fields_are_not_direct_rejection_site_in_fallback_runs.py <join_java> <coordination_state_java> <build_bypass_stdout> <full_inprocess_stdout>', file=sys.stderr)
        return 2

    join_java = Path(sys.argv[1]).read_text(errors='replace')
    coordination_java = Path(sys.argv[2]).read_text(errors='replace')
    build_bypass = counts(Path(sys.argv[3]))
    full_inprocess = counts(Path(sys.argv[4]))
    print(f'build_bypass={build_bypass}')
    print(f'full_inprocess={full_inprocess}')
    print(f'source_has_join_source_target_contract={"sourceNode is the node that provides the vote" in join_java and "target node is the node for which this vote is cast" in join_java}')
    print(f'source_has_better_last_accepted_term_reject={"better_last_accepted_term" in coordination_java}')
    print(f'source_has_better_last_accepted_version_reject={"better_last_accepted_version" in coordination_java}')

    build_reject_sum = sum(v for k, v in build_bypass.items() if 'rejection_class=' in k)
    full_reject_sum = sum(v for k, v in full_inprocess.items() if 'rejection_class=' in k)
    if (
        build_bypass['steelsearch_handleJoin_entry'] > 0
        and full_inprocess['steelsearch_handleJoin_entry'] > 0
        and build_reject_sum == 0
        and full_reject_sum == 0
        and build_bypass['steelsearch_publication_response_class=missing_join'] == 0
        and full_inprocess['steelsearch_publication_response_class=missing_join'] == 0
    ):
        print('result=join_lastAccepted_source_target_fields_are_not_the_direct_rejection_site_in_fallback_runs_so_next_split_moves_to_later_publish_response_acceptance_semantics')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
