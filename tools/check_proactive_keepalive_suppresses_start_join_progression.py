#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def load_counts(path: Path) -> dict[str, int]:
    report = json.loads(path.read_text())
    counts = collections.Counter()
    for capture in report.get("steelsearch_transport_capture") or []:
        action = (capture.get("first_frame") or {}).get("action_hint")
        if action:
            counts[action] += 1
    return {
        "request_pre_vote": counts.get("internal:cluster/request_pre_vote", 0),
        "start_join": counts.get("internal:cluster/coordination/start_join", 0),
        "publish_state": counts.get("internal:cluster/coordination/publish_state", 0),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_proactive_keepalive_suppresses_start_join_progression.py <baseline.json> <proactive.json>",
            file=sys.stderr,
        )
        return 2

    baseline_path = Path(sys.argv[1])
    proactive_path = Path(sys.argv[2])
    baseline = load_counts(baseline_path)
    proactive = load_counts(proactive_path)

    result = {
        "baseline_report_path": str(baseline_path),
        "proactive_report_path": str(proactive_path),
        "baseline_counts": baseline,
        "proactive_counts": proactive,
        "result": (
            "proactive_keepalive_suppresses_progression_beyond_request_pre_vote"
            if proactive["request_pre_vote"] > 0
            and proactive["start_join"] == 0
            and proactive["publish_state"] == 0
            and baseline["start_join"] > 0
            else "proactive_keepalive_does_not_show_clear_progression_suppression"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
