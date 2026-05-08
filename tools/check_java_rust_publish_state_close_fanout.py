#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_close_fanout.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    counts = Counter(
        (entry.get("first_frame") or {}).get("action_hint")
        or ("tcp/handshake" if (entry.get("first_frame") or {}).get("is_handshake") else "unknown")
        for entry in capture
    )

    publish_entries = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/publish_state")
    ]
    same_tick_remote_eof_count = sum(
        1
        for entry in publish_entries
        if entry.get("connection_end") == "remote_eof"
        and entry.get("response_frame_sent_at_ms") == entry.get("connection_end_at_ms")
    )
    commit_state_count = counts.get("internal:cluster/coordination/commit_state", 0)

    result = {
        "report_path": str(report_path),
        "publish_state_count": len(publish_entries),
        "same_tick_remote_eof_count": same_tick_remote_eof_count,
        "commit_state_count": commit_state_count,
    }
    if (
        len(publish_entries) > 0
        and same_tick_remote_eof_count == len(publish_entries)
        and commit_state_count == 0
    ):
        result["result"] = "state_channel_close_fanout_blocks_commit_state_progress"
    else:
        result["result"] = "state_channel_close_fanout_probe_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
