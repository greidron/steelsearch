#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: extract_followup_connection_retention_contract.py "
            "<HandshakingTransportAddressConnector.java> <ClusterConnectionManager.java>",
            file=sys.stderr,
        )
        return 2

    connector_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    manager_text = Path(sys.argv[2]).read_text(encoding="utf-8")

    result = {
        "probe_connection_uses_single_reg_channel_profile": "ConnectionProfile.buildSingleChannelProfile(" in connector_text
        and "Type.REG" in connector_text,
        "handshake_success_closes_probe_connection_before_full_connect": "IOUtils.closeWhileHandlingException(connection);" in connector_text,
        "full_connection_happens_via_transport_service_connect_to_node": "transportService.connectToNode(remoteNode, new ActionListener<Void>() {" in connector_text,
        "warns_completed_handshake_but_followup_connection_failed": "completed handshake with [{}] but followup connection failed" in connector_text,
        "cluster_connection_manager_rejects_closed_channel_while_connecting": 'throw new ConnectTransportException(node, "a channel closed while connecting");' in manager_text,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
