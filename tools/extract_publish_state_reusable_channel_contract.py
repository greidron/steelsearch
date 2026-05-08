#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: extract_publish_state_reusable_channel_contract.py "
            "<PublicationTransportHandler.java> <TransportService.java> <ConnectionProfile.java>",
            file=sys.stderr,
        )
        return 1

    publication_source = Path(sys.argv[1]).read_text(encoding="utf-8")
    transport_service_source = Path(sys.argv[2]).read_text(encoding="utf-8")
    connection_profile_source = Path(sys.argv[3]).read_text(encoding="utf-8")

    result = {
        "publish_state_uses_state_request_options": (
            "transportService.sendRequest(destination, PUBLISH_STATE_ACTION_NAME, request, stateRequestOptions, responseHandler);"
            in publication_source
        ),
        "transport_service_send_request_uses_get_connection": (
            "Transport.Connection connection = getConnection(node);" in transport_service_source
            or "connection = getConnection(node);" in transport_service_source
        ),
        "transport_service_get_connection_uses_connection_manager": (
            "return connectionManager.getConnection(node);" in transport_service_source
        ),
        "default_connection_profile_has_state_bucket": (
            "TransportRequestOptions.Type.STATE" in connection_profile_source
            and "connectionsPerNodeState" in connection_profile_source
        ),
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
