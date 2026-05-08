#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_hidden_alias_hypothesis_status_after_trace.py <old_report.json> <new_report.json> <new_trace_enabled.json>')

    old_report = load(sys.argv[1])
    new_report = load(sys.argv[2])
    new_trace = load(sys.argv[3])

    same_stage = (
        old_report.get('blocker_class') == 'standalone_only_bootstrap'
        and new_report.get('blocker_class') == 'standalone_only_bootstrap'
        and old_report.get('membership_formed') is False
        and new_report.get('membership_formed') is False
    )
    current_trace_shows_only_single_remote_probe = (
        new_trace.get('result') == 'peerfinder_trace_is_enabled_in_actual_probe_and_exposes_raw_probe_addresses'
        and new_trace.get('remote_probe_addresses') == ['127.0.0.1:57743']
        and new_trace.get('attempting_connection_addresses') == ['127.0.0.1:57743']
    )
    old_artifact_only_implied_hidden_alias_indirectly = (
        old_report.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and old_report.get('blocker_class') == 'standalone_only_bootstrap'
    )

    result = (
        'current_trace_does_not_directly_confirm_hidden_alias_so_previous_hidden_alias_claim_should_be_treated_as_indirect_inference'
        if same_stage and current_trace_shows_only_single_remote_probe and old_artifact_only_implied_hidden_alias_indirectly
        else 'hidden_alias_hypothesis_status_after_trace_not_fully_established'
    )

    print(json.dumps({
        'same_stage': same_stage,
        'current_trace_shows_only_single_remote_probe': current_trace_shows_only_single_remote_probe,
        'old_artifact_only_implied_hidden_alias_indirectly': old_artifact_only_implied_hidden_alias_indirectly,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
