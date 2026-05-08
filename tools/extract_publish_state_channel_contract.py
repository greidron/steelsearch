#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_publish_state_channel_contract.py <PublicationTransportHandler.java>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    result = {
        "state_request_options_declared": "private final TransportRequestOptions stateRequestOptions" in source,
        "state_request_options_type_state": ".withType(TransportRequestOptions.Type.STATE)" in source,
        "state_request_options_has_no_timeout_comment": (
            "no need to put a timeout on the options here, because we want the response to eventually be received" in source
        ),
        "publish_state_send_request_uses_state_request_options": (
            "transportService.sendRequest(destination, PUBLISH_STATE_ACTION_NAME, request, stateRequestOptions, responseHandler);" in source
        ),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
