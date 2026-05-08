#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_java_publish_state_capture.py <proxy-capture.json> <primary-stdout.log>",
            file=sys.stderr,
        )
        return 2

    capture_path = Path(sys.argv[1])
    stdout_path = Path(sys.argv[2])
    capture = json.loads(capture_path.read_text(encoding="utf-8")) if capture_path.exists() else []
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    counts = Counter(entry.get("action_hint") for entry in capture if entry.get("action_hint"))

    publish_state_count = counts.get("internal:cluster/coordination/publish_state", 0)
    commit_state_count = counts.get("internal:cluster/coordination/commit_state", 0)
    handshake_count = counts.get("internal:tcp/handshake", 0) + counts.get("internal:transport/handshake", 0)
    followup_failed = "followup connection failed" in stdout_text
    publication_failed = "publication failed" in stdout_text

    result = {
        "capture_path": str(capture_path),
        "publish_state_count": publish_state_count,
        "commit_state_count": commit_state_count,
        "handshake_count": handshake_count,
        "followup_failed": followup_failed,
        "publication_failed": publication_failed,
    }
    if publish_state_count > 0:
        result["result"] = "publish_state_observed"
    elif handshake_count > 0 and followup_failed:
        result["result"] = "stalled_at_followup_connection"
    elif publication_failed:
        result["result"] = "publication_failed_without_captured_publish_state"
    else:
        result["result"] = "java_java_publish_state_capture_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
