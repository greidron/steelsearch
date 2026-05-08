#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 1:
        print('usage: check_minimal_close_metadata_patch_is_likely_sufficient.py', file=sys.stderr)
        return 2
    tcpchannel = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpChannel.java').read_text(errors='ignore')
    tcptransport = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpTransport.java').read_text(errors='ignore')
    transport_netty4 = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4').exists()

    source_has_is_server_channel = 'boolean isServerChannel();' in tcpchannel
    source_has_last_accessed_api = 'long lastAccessedTime()' in tcpchannel
    source_close_logger_has_close_time = 'long closeTimeMillis = threadPool.relativeTimeInMillis();' in tcptransport
    source_close_logger_lacks_last_accessed = 'lastAccessedTime()' not in tcptransport[tcptransport.find('private class ChannelCloseLogger'):]
    source_close_logger_lacks_server_flag = 'isServerChannel()' not in tcptransport[tcptransport.find('private class ChannelCloseLogger'):]

    result = 'minimal_patch_of_isServerChannel_plus_lastAccessed_age_is_the_next_direct_step_before_netty_close_cause' if source_has_is_server_channel and source_has_last_accessed_api and source_close_logger_has_close_time and source_close_logger_lacks_last_accessed and source_close_logger_lacks_server_flag and transport_netty4 else 'inconclusive'
    print(json.dumps({
        'source_has_is_server_channel': source_has_is_server_channel,
        'source_has_last_accessed_api': source_has_last_accessed_api,
        'source_close_logger_has_close_time': source_close_logger_has_close_time,
        'source_close_logger_lacks_last_accessed': source_close_logger_lacks_last_accessed,
        'source_close_logger_lacks_server_flag': source_close_logger_lacks_server_flag,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
