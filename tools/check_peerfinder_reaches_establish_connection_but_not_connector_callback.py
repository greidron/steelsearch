#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_peerfinder_reaches_establish_connection_but_not_connector_callback.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text().splitlines()
    resolved = sum(1 for line in lines if "steelsearch_peerfinder_stage=resolved_configured_hosts" in line)
    start_probe = sum(1 for line in lines if "steelsearch_peerfinder_stage=start_probe" in line)
    establish = sum(1 for line in lines if "steelsearch_peerfinder_stage=establish_connection" in line)
    conn_response = sum(1 for line in lines if "steelsearch_peerfinder_stage=connection_response" in line)
    conn_failure = sum(1 for line in lines if "steelsearch_peerfinder_stage=connection_failure" in line)
    probe_marker = sum(1 for line in lines if "steelsearch_probe_stage=" in line)

    print(f"resolved_configured_hosts={resolved}")
    print(f"start_probe={start_probe}")
    print(f"establish_connection={establish}")
    print(f"connection_response={conn_response}")
    print(f"connection_failure={conn_failure}")
    print(f"probe_marker={probe_marker}")

    if resolved > 0 and start_probe > 0 and establish > 0 and conn_response == 0 and conn_failure == 0 and probe_marker == 0:
        print(
            "peerfinder_reaches_establish_connection_but_never_sees_connector_callback_or_probe_entry"
        )
        return 0

    print("inconclusive_peerfinder_connector_boundary")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
