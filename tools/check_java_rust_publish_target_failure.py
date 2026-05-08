#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_target_failure.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    stdout_path = Path((report.get("artifacts") or {}).get("opensearch_stdout", ""))
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""

    publish_entries = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/publish_state")
    ]
    same_tick_remote_eof_count = sum(
        1
        for entry in publish_entries
        if entry.get("response_frame")
        and entry.get("connection_end") == "remote_eof"
        and entry.get("response_frame_sent_at_ms") == entry.get("connection_end_at_ms")
    )
    publication_failed = "publication failed" in stdout_text
    quorum_failure = "non-failed nodes do not form a quorum" in stdout_text

    result = {
        "report_path": str(report_path),
        "publish_state_count": len(publish_entries),
        "same_tick_remote_eof_count": same_tick_remote_eof_count,
        "publication_failed": publication_failed,
        "quorum_failure": quorum_failure,
    }

    if (
        len(publish_entries) > 0
        and same_tick_remote_eof_count == len(publish_entries)
        and publication_failed
        and quorum_failure
    ):
        result["result"] = "publish_state_channel_close_interpreted_as_target_failure"
    else:
        result["result"] = "publish_state_target_failure_contract_not_fixed"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
