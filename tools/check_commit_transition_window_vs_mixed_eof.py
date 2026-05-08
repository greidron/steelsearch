#!/usr/bin/env python3
import datetime as dt
import json
import re
import sys
from pathlib import Path


TRACE_PATTERN = re.compile(
    r"^\[(?P<ts>[^\]]+)\].*\[(?P<action>internal:cluster/coordination/(?:publish_state|commit_state))\] (?P<event>sent response|sent to)"
)


def extract_reference_gap_ms(latest_json_path: Path) -> int:
    latest = json.loads(latest_json_path.read_text())
    log_path = Path(latest["work_dir"]) / "primary" / "logs" / "java-java-trace-ref.log"
    records = []
    for line in log_path.read_text().splitlines():
        match = TRACE_PATTERN.search(line)
        if not match:
            continue
        records.append(
            (
                dt.datetime.strptime(match.group("ts"), "%Y-%m-%dT%H:%M:%S,%f"),
                match.group("action"),
                match.group("event"),
            )
        )
    for index, (timestamp, action, event) in enumerate(records):
        if action != "internal:cluster/coordination/publish_state" or event != "sent response":
            continue
        for next_timestamp, next_action, next_event in records[index + 1 :]:
            if next_action == "internal:cluster/coordination/commit_state" and next_event == "sent to":
                return int((next_timestamp - timestamp).total_seconds() * 1000)
    raise RuntimeError("reference publish->commit transition not found")


def extract_mixed_publish_eof_gap_ms(mixed_report_path: Path) -> int:
    mixed = json.loads(mixed_report_path.read_text())
    for capture in mixed.get("steelsearch_transport_capture") or []:
        if (capture.get("first_frame") or {}).get("action_hint") != "internal:cluster/coordination/publish_state":
            continue
        return capture["connection_end_at_ms"] - capture["response_frame_sent_at_ms"]
    raise RuntimeError("mixed publish_state capture not found")


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_commit_transition_window_vs_mixed_eof.py <mixed_probe_report.json> <java_trace_latest.json>",
            file=sys.stderr,
        )
        return 2

    mixed_path = Path(sys.argv[1])
    latest_json_path = Path(sys.argv[2])
    mixed_gap_ms = extract_mixed_publish_eof_gap_ms(mixed_path)
    reference_gap_ms = extract_reference_gap_ms(latest_json_path)

    result = {
        "mixed_report_path": str(mixed_path),
        "java_trace_latest_path": str(latest_json_path),
        "mixed_publish_response_to_eof_gap_ms": mixed_gap_ms,
        "java_reference_publish_response_to_commit_send_gap_ms": reference_gap_ms,
        "result": (
            "mixed_publish_socket_closes_before_the_reference_commit_transition_window"
            if mixed_gap_ms < reference_gap_ms
            else "mixed_publish_socket_survives_at_least_the_reference_commit_transition_window"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
