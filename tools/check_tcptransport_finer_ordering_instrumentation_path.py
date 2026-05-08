#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_tcptransport_finer_ordering_instrumentation_path.py <TcpTransport.java> <TcpTransport$ChannelsConnectedListener.class>', file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).read_text()
    compiled = Path(sys.argv[2]).read_bytes()
    source_has_close_order = 'closeOrder' in source and 'closeNanoTime' in source and 'closeEventSequence' in source
    class_has_close_order = b'closeOrder' in compiled and b'closeNanoTime' in compiled
    result = 'tcptransport_finer_ordering_instrumentation_path_incomplete'
    if source_has_close_order and class_has_close_order:
        result = 'tcptransport_finer_ordering_instrumentation_path_is_implemented'
    print(json.dumps({
        'source_has_close_order': source_has_close_order,
        'class_has_close_order': class_has_close_order,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
