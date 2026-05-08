#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_hidden_alias_vs_trace_artifact_stage_gap.py <old_report.json> <new_report.json> <new_trace_enabled.json>')

    old_report = load(sys.argv[1])
    new_report = load(sys.argv[2])
    new_trace = load(sys.argv[3])

    old_reaches_post_bootstrap_coordination = (
        old_report.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and old_report.get('membership_formed') is False
        and old_report.get('blocker_class') != 'standalone_only_bootstrap'
    )
    new_trace_artifact_stops_at_standalone_only_bootstrap = (
        new_report.get('blocker_class') == 'standalone_only_bootstrap'
        and new_report.get('observed_node_count') == 0
        and new_report.get('membership_formed') is False
    )
    new_trace_shows_only_single_remote_probe = (
        new_trace.get('result') == 'peerfinder_trace_is_enabled_in_actual_probe_and_exposes_raw_probe_addresses'
        and new_trace.get('remote_probe_addresses') == ['127.0.0.1:57743']
    )

    result = (
        'hidden_alias_hypothesis_and_current_trace_artifact_are_separated_by_artifact_stage_gap_not_direct_contradiction'
        if old_reaches_post_bootstrap_coordination
        and new_trace_artifact_stops_at_standalone_only_bootstrap
        and new_trace_shows_only_single_remote_probe
        else 'hidden_alias_vs_trace_artifact_stage_gap_not_fully_established'
    )

    print(json.dumps({
        'old_reaches_post_bootstrap_coordination': old_reaches_post_bootstrap_coordination,
        'new_trace_artifact_stops_at_standalone_only_bootstrap': new_trace_artifact_stops_at_standalone_only_bootstrap,
        'new_trace_shows_only_single_remote_probe': new_trace_shows_only_single_remote_probe,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
