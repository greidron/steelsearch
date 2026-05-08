#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_channel_retention.py <mixed-report.json>",
            file=sys.stderr,
        )
        return 1

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    entries = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/publish_state")
    ]

    same_tick_remote_eof = sum(
        1
        for entry in entries
        if entry.get("response_frame")
        and entry.get("connection_end") == "remote_eof"
        and entry.get("response_frame_sent_at_ms") == entry.get("connection_end_at_ms")
    )

    result = {
        "report_path": str(report_path),
        "publish_state_count": len(entries),
        "same_tick_remote_eof_count": same_tick_remote_eof,
    }

    if len(entries) > 0 and same_tick_remote_eof == len(entries):
        result["result"] = "publish_state_state_channel_same_tick_remote_eof_every_time"
    else:
        result["result"] = "publish_state_channel_retention_pattern_not_fixed"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
