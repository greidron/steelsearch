#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_followup_retention_failure.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    stdout_path = Path((report.get("artifacts") or {}).get("opensearch_stdout", ""))
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""

    completed_handshake_followup_failed = "completed handshake with" in stdout_text and "followup connection failed" in stdout_text
    general_node_connection_failure = "general node connection failure" in stdout_text
    channel_closed_while_connecting = "a channel closed while connecting" in stdout_text
    connection_reset = "handshake failed because connection reset" in stdout_text

    if completed_handshake_followup_failed and general_node_connection_failure and connection_reset:
        result = "handshake_succeeded_but_followup_connection_failed_before_retention"
    else:
        result = "followup_retention_failure_not_observed"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "completed_handshake_followup_failed": completed_handshake_followup_failed,
                "general_node_connection_failure": general_node_connection_failure,
                "channel_closed_while_connecting": channel_closed_while_connecting,
                "connection_reset": connection_reset,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
