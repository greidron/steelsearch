#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


TARGETS = {
    "internal:cluster/request_pre_vote",
    "internal:cluster/coordination/start_join",
    "internal:cluster/coordination/publish_state",
}


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_proactive_keepalive_followup_probe.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    captures = report.get("steelsearch_transport_capture") or []

    target_total = 0
    proactive_counts = collections.Counter()
    action_counts = collections.Counter()
    end_counts = collections.Counter()
    for capture in captures:
        first_action = (capture.get("first_frame") or {}).get("action_hint")
        if first_action not in TARGETS:
            continue
        target_total += 1
        action_counts[first_action] += 1
        if capture.get("proactive_keepalive_count"):
            proactive_counts[first_action] += 1
        end_counts[capture.get("connection_end")] += 1

    result = {
        "report_path": str(report_path),
        "target_total": target_total,
        "action_counts": dict(action_counts),
        "proactive_keepalive_counts": dict(proactive_counts),
        "connection_end_counts": dict(end_counts),
        "failure_stage": report.get("failure_stage"),
        "blocker_class": report.get("blocker_class"),
        "result": (
            "proactive_keepalive_followup_observed_but_target_sockets_still_end_in_remote_eof"
            if target_total and sum(proactive_counts.values()) == target_total and end_counts.get("remote_eof") == target_total
            else "proactive_keepalive_followup_not_fully_observed_or_target_shape_changed"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if target_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
