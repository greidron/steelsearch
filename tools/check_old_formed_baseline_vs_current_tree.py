#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 4:
        print('usage: check_old_formed_baseline_vs_current_tree.py <old-formed-report.json> <current-baseline-report.json> <current-overlay-report.json>', file=sys.stderr)
        return 2

    old_formed = load(sys.argv[1])
    current_baseline = load(sys.argv[2])
    current_overlay = load(sys.argv[3])

    print(f"old_formed_membership={old_formed.get('membership_formed')}")
    print(f"current_baseline_membership={current_baseline.get('membership_formed')}")
    print(f"current_overlay_membership={current_overlay.get('membership_formed')}")
    print(f"old_formed_follow_up={old_formed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"current_baseline_follow_up={current_baseline.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"current_overlay_follow_up={current_overlay.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"current_baseline_failure_stage={current_baseline.get('failure_stage')}")
    print(f"current_overlay_failure_stage={current_overlay.get('failure_stage')}")

    if (
        old_formed.get('membership_formed') is True
        and current_baseline.get('membership_formed') is False
        and current_overlay.get('membership_formed') is False
        and old_formed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and current_baseline.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
        and current_overlay.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
    ):
        print('result=old_formed_artifact_is_not_a_safe_primary_baseline_while_current_tree_cannot_reproduce_fresh_formed_membership')
        return 0

    print('result=baseline_status_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
