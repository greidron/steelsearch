#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_lower_transport_direct_cause_is_netty_close_hint_path.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    text = stdout_log.read_text(errors='ignore')
    netty4_tcp = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4TcpChannel.java').read_text(errors='ignore')
    netty4_transport = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4Transport.java').read_text(errors='ignore')
    netty4_handler = Path('/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4MessageChannelHandler.java').read_text(errors='ignore')

    source_has_close_hint_keys = 'CLOSE_HINT_KEY' in netty4_tcp and 'CLOSE_HINT_CAUSE_KEY' in netty4_tcp
    source_has_record_close_hint = 'void recordCloseHint(' in netty4_tcp
    source_installs_close_trace_listener = 'installCloseTraceListener()' in netty4_transport
    source_records_channelinactive = 'recordCloseHint("channelInactive", null);' in netty4_handler
    source_records_exceptioncaught = 'recordCloseHint("exceptionCaught", newCause);' in netty4_handler

    artifact_has_netty_close_hint_logs = 'netty4 tcp channel close completed' in text or 'channelInactive' in text or 'exceptionCaught' in text or 'closeFutureIntercepted' in text
    result = 'lower_transport_direct_cause_is_already_narrowed_to_existing_netty_close_hint_path_but_not_yet_surfaced_in_probe_logs' if source_has_close_hint_keys and source_has_record_close_hint and source_installs_close_trace_listener and source_records_channelinactive and source_records_exceptioncaught and not artifact_has_netty_close_hint_logs else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'source_has_close_hint_keys': source_has_close_hint_keys,
        'source_has_record_close_hint': source_has_record_close_hint,
        'source_installs_close_trace_listener': source_installs_close_trace_listener,
        'source_records_channelinactive': source_records_channelinactive,
        'source_records_exceptioncaught': source_records_exceptioncaught,
        'artifact_has_netty_close_hint_logs': artifact_has_netty_close_hint_logs,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
