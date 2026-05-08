#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def transport_handshake_count(capture_path: str) -> int:
    captures = json.loads(Path(capture_path).read_text())
    return sum(
        1
        for row in captures
        if (row.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    )


def warn_count(stdout_path: str, needle: str) -> int:
    return sum(1 for line in Path(stdout_path).read_text().splitlines() if needle in line)


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "usage: check_discovery_stop_points_away_from_handshake_payload_mismatch.py <connector.java> <capture-a> <stdout-a> <capture-b> <stdout-b>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    a_transport = transport_handshake_count(sys.argv[2])
    a_warn = warn_count(sys.argv[3], "handshake failed for [")
    b_transport = transport_handshake_count(sys.argv[4])
    b_warn = warn_count(sys.argv[5], "handshake failed for [")

    source_warns_on_high_level_failure = "logger.warn(new ParameterizedMessage(\"handshake failed for [" in source

    print(f"source_warns_on_high_level_failure={source_warns_on_high_level_failure}")
    print(f"run_a_transport_handshake={a_transport}")
    print(f"run_a_handshake_failed_warn={a_warn}")
    print(f"run_b_transport_handshake={b_transport}")
    print(f"run_b_handshake_failed_warn={b_warn}")

    if (
        source_warns_on_high_level_failure
        and a_transport == 0
        and b_transport == 0
        and a_warn == 0
        and b_warn == 0
    ):
        print(
            "discovery_stop_points_away_from_logged_handshake_payload_mismatch_and_toward_pre_high_level_followup_close_path"
        )
        return 0

    print("inconclusive_handshake_payload_mismatch_split")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
