#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_state_channel_close_fanout_contract.py <TcpTransport.java>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    result = {
        "node_channels_maps_request_type_to_channel_handle": "typeMapping.put(type, handle);" in source,
        "node_channels_supports_state_type_lookup": 'throw new IllegalArgumentException("no type channel for [" + type + "]")' in source,
        "per_channel_close_listener_calls_node_channels_close": "ch.addCloseListener(ActionListener.wrap(nodeChannels::close));" in source,
        "node_channels_close_closes_all_channels": "CloseableChannel.closeChannels(channels, block);" in source,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
