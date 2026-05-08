#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_multiplicity_conclusion_retirement.py <reinterpretation.json> <hidden_alias_status.json>')

    reinterpretation = load(sys.argv[1])
    hidden_alias = load(sys.argv[2])

    reinterpretation_established = (
        reinterpretation.get('result')
        == 'old_transport_capture_request_peers_burst_is_better_explained_as_repeated_one_shot_sockets_from_single_peer_than_as_multi_address_peer_multiplicity'
    )
    hidden_alias_downgraded = (
        hidden_alias.get('result')
        == 'current_trace_does_not_directly_confirm_hidden_alias_so_previous_hidden_alias_claim_should_be_treated_as_indirect_inference'
    )

    result = (
        'previous_multi_address_hidden_alias_conclusions_should_be_retired_or_downgraded_in_favor_of_single_peer_repeated_one_shot_socket_explanation'
        if reinterpretation_established and hidden_alias_downgraded
        else 'multiplicity_conclusion_retirement_not_fully_established'
    )

    print(json.dumps({
        'reinterpretation_established': reinterpretation_established,
        'hidden_alias_downgraded': hidden_alias_downgraded,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
