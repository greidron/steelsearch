#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: extract_followup_close_fanout_contract.py <TcpTransport.java> <ClusterConnectionManager.java>",
            file=sys.stderr,
        )
        return 2

    tcp_transport = Path(sys.argv[1]).read_text(encoding="utf-8")
    cluster_manager = Path(sys.argv[2]).read_text(encoding="utf-8")

    result = {
        "node_channels_register_per_channel_close_listener": "ch.addCloseListener(ActionListener.wrap(nodeChannels::close));" in tcp_transport,
        "node_channels_close_closes_all_channels": "CloseableChannel.closeChannels(channels, block);" in tcp_transport,
        "cluster_connection_manager_fails_if_connection_already_closed": 'throw new ConnectTransportException(node, "a channel closed while connecting");' in cluster_manager,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
