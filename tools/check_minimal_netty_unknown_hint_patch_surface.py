#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 1:
        print('usage: check_minimal_netty_unknown_hint_patch_surface.py', file=sys.stderr)
        return 2
    tcp = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4TcpChannel.java').read_text(errors='ignore')
    transport = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4Transport.java').read_text(errors='ignore')
    close_block = tcp[tcp.find('public void close()'):tcp.find('@Override\n    public boolean isServerChannel()') if '@Override\n    public boolean isServerChannel()' in tcp else tcp.find('public boolean isServerChannel()')]
    source_close_lacks_explicit_hint = 'recordCloseHint(' not in close_block and 'channel.close();' in close_block
    source_has_close_future_intercept_fallback = 'closeFutureIntercepted' in transport
    result = 'minimal_patch_surface_to_reduce_unknown_hint_is_netty4tcpchannel_close_before_channel_close' if source_close_lacks_explicit_hint and source_has_close_future_intercept_fallback else 'inconclusive'
    print(json.dumps({
        'source_close_lacks_explicit_hint': source_close_lacks_explicit_hint,
        'source_has_close_future_intercept_fallback': source_has_close_future_intercept_fallback,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
