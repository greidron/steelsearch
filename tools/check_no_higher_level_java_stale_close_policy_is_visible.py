#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_no_higher_level_java_stale_close_policy_is_visible.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    keepalive = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportKeepAlive.java').read_text(errors='ignore')
    result_has_future_comment = 'In the future it is possible that we may want to kill a channel' in keepalive
    result_needs_ping_only = 'if (needsKeepAlivePing(channel)) {' in keepalive and 'sendPing(channel);' in keepalive
    result_no_channel_close_in_do_run = 'channel.close()' not in keepalive and 'closeChannels' not in keepalive and 'nodeChannels.close()' not in keepalive
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'keepalive_has_future_kill_comment': result_has_future_comment,
        'keepalive_currently_only_sends_ping': result_needs_ping_only,
        'keepalive_has_no_channel_close_path': result_no_channel_close_in_do_run,
        'result': 'no_higher_level_java_stale_close_policy_is_visible_so_remaining_candidate_is_lower_transport_socket_layer' if result_has_future_comment and result_needs_ping_only and result_no_channel_close_in_do_run else 'inconclusive'
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
