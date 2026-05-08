#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_openconnection_callback_not_restored_by_deeper_inner_overlay.py <base-stdout.log> <deeper-stdout.log>",
            file=sys.stderr,
        )
        return 2

    base = Path(sys.argv[1]).read_text()
    deeper = Path(sys.argv[2]).read_text()

    base_open_response = base.count("steelsearch_open_connection_stage=response")
    base_open_failure = base.count("steelsearch_open_connection_stage=failure")
    deeper_open_response = deeper.count("steelsearch_open_connection_stage=response")
    deeper_open_failure = deeper.count("steelsearch_open_connection_stage=failure")
    deeper_open_request = deeper.count("steelsearch_open_connection_stage=request")

    print(f"base_open_response={base_open_response}")
    print(f"base_open_failure={base_open_failure}")
    print(f"deeper_open_request={deeper_open_request}")
    print(f"deeper_open_response={deeper_open_response}")
    print(f"deeper_open_failure={deeper_open_failure}")

    if deeper_open_request > 0 and base_open_response == 0 and base_open_failure == 0 and deeper_open_response == 0 and deeper_open_failure == 0:
        print("checker_result=deeper_openconnection_listener_overlay_does_not_restore_callback_markers")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
