#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: check_handshaking_connector_trace_decision.py <stdout.log>"
        )

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")

    handshake_successful_count = text.count("handshake successful:")
    completed_full_connection_count = text.count("completed full connection with [")
    followup_connection_failed_count = text.count("completed handshake with [")
    handshake_failed_count = text.count("handshake failed for [")

    result = (
        "connector_trace_shows_full_connection_completes_successfully_so_sub_second_abort_happens_after_connect_to_node_completion_not_in_followup_connection_failure_branch"
        if handshake_successful_count > 0
        and completed_full_connection_count > 0
        and followup_connection_failed_count == 0
        else "connector_trace_decision_not_fully_established"
    )

    print(json.dumps({
        "handshake_successful_count": handshake_successful_count,
        "completed_full_connection_count": completed_full_connection_count,
        "followup_connection_failed_count": followup_connection_failed_count,
        "handshake_failed_count": handshake_failed_count,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
