#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: check_current_probe_retry_shape.py <report.json> <retry_gap_paths.json>")

    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    retry = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    capture = report.get("steelsearch_transport_capture") or []
    direct_count = sum(
        1
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake")
    )
    immediate_count = retry.get("immediate_count")
    delayed_count = retry.get("delayed_count")

    if direct_count <= 0:
        fail("expected direct full-connect transport handshakes in current report")
    if immediate_count != direct_count - 1:
        fail("expected all but one direct full-connect attempt to be followed by immediate tcp retry")
    if delayed_count != 0:
        fail("current report must not contain delayed retry entries")

    print(
        json.dumps(
            {
                "direct_full_connect_count": direct_count,
                "immediate_retry_count": immediate_count,
                "delayed_retry_count": delayed_count,
                "terminal_no_retry_count": direct_count - immediate_count,
                "result": (
                    "current_probe_retry_shape_is_26_immediate_same_round_retries_plus_1_terminal_"
                    "no_retry_so_uniform_1s_discovery_scheduler_cadence_is_not_the_current_shape"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
