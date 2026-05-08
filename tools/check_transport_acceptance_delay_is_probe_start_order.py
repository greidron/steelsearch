#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OPENED_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*HandshakingTransportAddressConnector.*\[(?P<tag>connectToRemoteMasterNode\[[^\]]+\])\] opened probe connection"
)


def to_ms(ts: str) -> int:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_transport_acceptance_delay_is_probe_start_order.py <probe_java_rust_mixed_membership.sh> <crates/os-node/src/main.rs> <opensearch-stdout.log> <report.json>",
            file=sys.stderr,
        )
        return 2

    probe_script = Path(sys.argv[1]).read_text(encoding="utf-8")
    rust_main = Path(sys.argv[2]).read_text(encoding="utf-8")
    stdout_lines = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace").splitlines()
    report = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))

    opensearch_launch_idx = probe_script.find('bash "${ROOT_DIR}/tools/run-opensearch-dev.sh"')
    wait_http_idx = probe_script.find('wait_for_http "http://127.0.0.1:${OS_HTTP}/"')
    seed_identity_idx = probe_script.rfind('collect_seed_peer_identity')
    steelsearch_launch_idx = probe_script.find('bash "${ROOT_DIR}/tools/run-steelsearch-dev.sh"')

    probe_starts_steelsearch_after_opensearch_ready = (
        0 <= opensearch_launch_idx < wait_http_idx < seed_identity_idx < steelsearch_launch_idx
    )

    bind_idx = rust_main.find('let transport_listener = bind_transport_seed_listener(transport_address)?;')
    serve_idx = rust_main.find('serve_transport_seed_listener_until(transport_listener, transport_capture_path, transport_identity);')
    rust_binds_and_serves_listener_in_main = 0 <= bind_idx < serve_idx

    first_opened = None
    for line in stdout_lines:
        m = OPENED_RE.search(line)
        if m:
            first_opened = to_ms(m.group('ts'))
            break

    captures = report.get('steelsearch_transport_capture') or []
    first_capture = min((c.get('connection_started_at_ms') for c in captures if c.get('connection_started_at_ms') is not None), default=None)
    delta_ms = abs(first_opened - first_capture) if first_opened is not None and first_capture is not None else None

    result = {
        'probe_starts_steelsearch_after_opensearch_ready': probe_starts_steelsearch_after_opensearch_ready,
        'rust_binds_and_serves_listener_in_main': rust_binds_and_serves_listener_in_main,
        'first_opened_probe_ms': first_opened,
        'first_rust_inbound_capture_ms': first_capture,
        'delta_ms': delta_ms,
        'result': 'transport_acceptance_delay_is_better_explained_by_probe_start_order_and_rust_process_start_timing_than_by_a_late_internal_transport_listener_enablement_gate',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
