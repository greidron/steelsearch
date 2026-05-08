#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def action_counts(report):
    caps = report.get('steelsearch_transport_capture') or []
    return Counter((entry.get('first_frame') or {}).get('action_hint') for entry in caps)


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_current_baseline_vs_overlay_same_failure.py <baseline-report.json> <overlay-report.json>', file=sys.stderr)
        return 2

    baseline = load(sys.argv[1])
    overlay = load(sys.argv[2])
    baseline_actions = action_counts(baseline)
    overlay_actions = action_counts(overlay)

    print(f"baseline_membership={baseline.get('membership_formed')}")
    print(f"overlay_membership={overlay.get('membership_formed')}")
    print(f"baseline_failure_stage={baseline.get('failure_stage')}")
    print(f"overlay_failure_stage={overlay.get('failure_stage')}")
    print(f"baseline_follow_up={baseline.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"overlay_follow_up={overlay.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"baseline_actions={dict(baseline_actions)}")
    print(f"overlay_actions={dict(overlay_actions)}")

    baseline_tcp_only = set(baseline_actions.keys()) <= {None, 'internal:tcp/handshake'} and baseline_actions.get('internal:tcp/handshake', 0) > 0
    overlay_tcp_only = set(overlay_actions.keys()) <= {None, 'internal:tcp/handshake'} and overlay_actions.get('internal:tcp/handshake', 0) > 0

    if (
        baseline.get('membership_formed') is False
        and overlay.get('membership_formed') is False
        and baseline.get('failure_stage') == 'membership_timeout'
        and overlay.get('failure_stage') == 'membership_timeout'
        and baseline.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
        and overlay.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
        and baseline_tcp_only
        and overlay_tcp_only
    ):
        print('result=current_no_overlay_baseline_and_current_overlay_run_share_same_tcp_handshake_only_membership_timeout_failure')
        return 0

    print('result=baseline_vs_overlay_failure_shape_differs')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
