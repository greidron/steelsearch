#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_current_signal_requires_extra_close_metadata.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    text = stdout_log.read_text(errors='ignore')
    counts = {
        'opened_transport_connection_using_channels': len(re.findall(r'opened transport connection \[\d+\] to \[\{rust-replica-1\}.*using channels \[', text)),
        'observed_close_on_channelIndex': len(re.findall(r'node connection \[\d+\] observed close on channelIndex \[\d+\].*for \[\{rust-replica-1\}', text)),
        'action_tagged_selected_channel': len(re.findall(r'action-tagged selected channel index \[\d+\].*for \[\{rust-replica-1\}', text)),
        'close_lines_with_server_flag': len(re.findall(r'isServerChannel|serverChannel', text)),
        'close_lines_with_close_cause': len(re.findall(r'close cause|closeCause|exception=.*close', text)),
        'close_lines_with_last_accessed_age': len(re.findall(r'lastAccessed|idleFor|sinceLastAccess', text)),
    }
    src_tcp = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpTransport.java').read_text(errors='ignore')
    src_channel = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpChannel.java').read_text(errors='ignore')
    source_has_server_flag_api = 'boolean isServerChannel();' in src_channel
    source_has_channel_stats_api = 'ChannelStats getChannelStats();' in src_channel
    result = 'current_signal_is_good_enough_for_structure_but_still_needs_extra_close_metadata_to_resolve_peer_detail' if counts['opened_transport_connection_using_channels'] and counts['observed_close_on_channelIndex'] and counts['action_tagged_selected_channel'] and counts['close_lines_with_server_flag'] == 0 and counts['close_lines_with_close_cause'] == 0 and counts['close_lines_with_last_accessed_age'] == 0 and source_has_server_flag_api and source_has_channel_stats_api else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        **counts,
        'source_has_server_flag_api': source_has_server_flag_api,
        'source_has_channel_stats_api': source_has_channel_stats_api,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
