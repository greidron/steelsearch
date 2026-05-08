#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> int:
    if len(sys.argv) != 6:
        print(
            'usage: check_combined_strace_uprobe_timing_artifact.py <uprobe-only-summary-json> <combined-summary-json> <strace-only-payload-identity-json> <strace-only-markers-json> <combined-payload-identity-json>'
        )
        return 2

    uprobe_only = load(sys.argv[1])
    combined = load(sys.argv[2])
    strace_only_payload = load(sys.argv[3])
    strace_only_markers = load(sys.argv[4])
    combined_payload = load(sys.argv[5])

    uprobe_only_socket = uprobe_only.get('perf_counts', {}).get('probe_libnio:ss_socket_read0', 0)
    combined_socket = combined.get('perf_counts', {}).get('probe_libnio:ss_socket_read0', 0)
    strace_only_exact = len(strace_only_payload.get('matched_reads', []))
    combined_exact = len(combined_payload.get('matched_reads', []))
    strace_only_29b = strace_only_markers.get('transport_worker_tcp_payload_read_29b_count', 0)

    result = {
        'uprobe_only_socket_read0_hits': uprobe_only_socket,
        'combined_socket_read0_hits': combined_socket,
        'strace_only_exact_handshake_reads': strace_only_exact,
        'strace_only_transport_worker_29b_reads': strace_only_29b,
        'combined_exact_handshake_reads': combined_exact,
    }

    if (
        uprobe_only_socket == strace_only_exact
        and strace_only_exact == strace_only_29b
        and combined_socket > 0
        and combined_exact == 0
        and combined_socket != uprobe_only_socket
    ):
        result['checker_result'] = (
            'combined_strace_plus_uprobe_run_most_directly_points_to_trace_attach_timing_perturbation_of_exact_29b_payload_identity_while_preserving_socket_read0_branch'
        )
    else:
        result['checker_result'] = 'combined_strace_uprobe_timing_artifact_not_yet_demonstrated'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
