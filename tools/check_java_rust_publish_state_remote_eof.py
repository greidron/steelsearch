#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def classify_entry(entry: dict) -> bool:
    frame = entry.get("first_frame") or {}
    if frame.get("action_hint") != "internal:cluster/coordination/publish_state":
        return False
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_remote_eof.py <mixed-report.json>",
            file=sys.stderr,
        )
        return 1

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    entries = [entry for entry in capture if classify_entry(entry)]

    publish_state_count = len(entries)
    response_written_count = sum(1 for e in entries if e.get("response_frame"))
    remote_eof_count = sum(1 for e in entries if e.get("connection_end") == "remote_eof")
    same_tick_remote_eof_count = sum(
        1
        for e in entries
        if e.get("response_frame")
        and e.get("connection_end") == "remote_eof"
        and e.get("response_frame_sent_at_ms") == e.get("connection_end_at_ms")
    )
    commit_state_count = sum(
        1
        for e in capture
        if ((e.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/commit_state")
    )

    result = {
        "report_path": str(report_path),
        "publish_state_count": publish_state_count,
        "response_written_count": response_written_count,
        "remote_eof_count": remote_eof_count,
        "same_tick_remote_eof_count": same_tick_remote_eof_count,
        "commit_state_count": commit_state_count,
    }

    if (
        publish_state_count > 0
        and response_written_count == publish_state_count
        and same_tick_remote_eof_count == publish_state_count
        and commit_state_count == 0
    ):
        result["result"] = "publish_state_response_written_but_same_tick_remote_eof_before_commit_state"
    else:
        result["result"] = "publish_state_remote_eof_pattern_not_fixed"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
