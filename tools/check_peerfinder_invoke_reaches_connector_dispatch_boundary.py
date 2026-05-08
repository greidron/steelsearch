#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_peerfinder_invoke_reaches_connector_dispatch_boundary.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    establish_connection = text.count("steelsearch_peerfinder_stage=establish_connection")
    before_connector_invoke = text.count("steelsearch_peerfinder_stage=before_connector_invoke")
    after_connector_invoke = text.count("steelsearch_peerfinder_stage=after_connector_invoke")
    connector_invoke_threw = text.count("steelsearch_peerfinder_stage=connector_invoke_threw")
    open_connection_request = text.count("steelsearch_open_connection_stage=request")
    probe_stage = text.count("steelsearch_probe_stage=")

    print(f"establish_connection={establish_connection}")
    print(f"before_connector_invoke={before_connector_invoke}")
    print(f"after_connector_invoke={after_connector_invoke}")
    print(f"connector_invoke_threw={connector_invoke_threw}")
    print(f"open_connection_request={open_connection_request}")
    print(f"probe_stage={probe_stage}")

    if before_connector_invoke > 0 and after_connector_invoke > 0 and connector_invoke_threw == 0 and open_connection_request == 0:
        print("checker_result=peerfinder_invokes_connector_but_connector_body_dispatch_never_starts")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
