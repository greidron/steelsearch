#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: extract_validator_failure_close_contract.py <ClusterConnectionManager.java>"}))
        return 1

    text = Path(sys.argv[1]).read_text()
    result = {
        "validator_failure_closes_connection": "IOUtils.closeWhileHandlingException(conn);" in text,
        "validator_failure_fails_connection_listeners": "failConnectionListeners(node, releaseOnce, e, currentListener);" in text,
        "registration_happens_only_in_validator_success_branch": "connectedNodes.putIfAbsent(node, conn)" in text,
    }
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
