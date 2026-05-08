#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_reusable_channel_failure.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
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
    valid_decode_count = 0
    for entry in publish_entries:
        response_frame = entry.get("response_frame") or {}
        body_hex = response_frame.get("body_hex") or ""
        if not body_hex:
            continue
        valid_decode_count += 1

    result = {
        "report_path": str(report_path),
        "publish_state_count": len(publish_entries),
        "valid_decode_artifact_count": valid_decode_count,
        "same_tick_remote_eof_count": same_tick_remote_eof_count,
    }
    if (
        len(publish_entries) > 0
        and valid_decode_count == len(publish_entries)
        and same_tick_remote_eof_count == len(publish_entries)
    ):
        result["result"] = "valid_publish_state_response_still_fails_reusable_state_channel_retention"
    else:
        result["result"] = "publish_state_reusable_channel_failure_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
