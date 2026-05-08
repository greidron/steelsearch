#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def file_contains_bytes(path: str, needle: bytes) -> bool:
    return needle in Path(path).read_bytes()


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_tcptransport_close_ordering_instrumentation_path.py <run-opensearch-dev.sh> <probe_java_rust_mixed_membership.sh> <TcpTransport.java> <TcpTransport$ChannelsConnectedListener.class>', file=sys.stderr)
        return 2

    run_script = Path(sys.argv[1]).read_text()
    probe_script = Path(sys.argv[2]).read_text()
    tcp_source = Path(sys.argv[3]).read_text()
    tcp_class = sys.argv[4]
    needle = b'observed close on channelIndex'

    source_has_close_ordering_trace = 'observed close on channelIndex' in tcp_source
    run_script_has_tcptransport_log_level = 'OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL' in run_script and 'logger.org.opensearch.transport.TcpTransport' in run_script
    probe_script_passes_tcptransport_log_level = 'JAVA_RUST_MIXED_MEMBERSHIP_OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL' in probe_script and 'OPENSEARCH_TCP_TRANSPORT_LOG_LEVEL' in probe_script
    compiled_class_has_trace_string = file_contains_bytes(tcp_class, needle)

    result = 'tcptransport_per_channel_close_ordering_instrumentation_path_is_implemented'
    if not all([source_has_close_ordering_trace, run_script_has_tcptransport_log_level, probe_script_passes_tcptransport_log_level, compiled_class_has_trace_string]):
        result = 'tcptransport_close_ordering_instrumentation_path_incomplete'

    print(json.dumps({
        'source_has_close_ordering_trace': source_has_close_ordering_trace,
        'run_script_has_tcptransport_log_level': run_script_has_tcptransport_log_level,
        'probe_script_passes_tcptransport_log_level': probe_script_passes_tcptransport_log_level,
        'compiled_class_has_trace_string': compiled_class_has_trace_string,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
