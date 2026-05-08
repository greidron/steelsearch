#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_commit_blocker.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []
    stdout_path = Path((report.get("artifacts") or {}).get("opensearch_stdout", ""))
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""

    action_counts = Counter(
        (entry.get("first_frame") or {}).get("action_hint")
        or ("tcp/handshake" if (entry.get("first_frame") or {}).get("is_handshake") else "unknown")
        for entry in capture
    )

    publish_state_count = action_counts.get("internal:cluster/coordination/publish_state", 0)
    commit_state_count = action_counts.get("internal:cluster/coordination/commit_state", 0)
    follower_disconnected = "FollowerChecker" in stdout_text
    publication_failed = "publication failed" in stdout_text

    if publish_state_count > 0 and commit_state_count == 0 and follower_disconnected and publication_failed:
        result = "publish_state_reached_commit_state_blocked"
    elif publish_state_count > 0 and commit_state_count > 0:
        result = "commit_state_observed"
    else:
        result = "publish_commit_probe_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "publish_state_count": publish_state_count,
                "commit_state_count": commit_state_count,
                "follower_disconnected": follower_disconnected,
                "publication_failed": publication_failed,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
