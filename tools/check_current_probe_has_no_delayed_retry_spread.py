#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_current_probe_has_no_delayed_retry_spread.py <retry_gap_paths.json>")

    retry = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    immediate_count = retry.get("immediate_count")
    delayed_count = retry.get("delayed_count")
    delayed_entries = retry.get("delayed_entries") or []

    if immediate_count != 26:
        fail("expected 26 immediate retry entries in current probe")
    if delayed_count != 0:
        fail("expected no delayed retry entries in current probe")
    if delayed_entries:
        fail("delayed_entries must be empty in current probe")

    print(
        json.dumps(
            {
                "immediate_count": immediate_count,
                "delayed_count": delayed_count,
                "result": (
                    "current_probe_no_longer_shows_a_6ms_to_17627ms_delayed_retry_spread_and_"
                    "only_retains_the_immediate_retry_bucket"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
