#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_raw_probe_address_not_directly_exposed.py <report.json> <gateway-state.json> <opensearch-stdout.log>')

    report = load(sys.argv[1])
    gateway = load(sys.argv[2])
    stdout_text = Path(sys.argv[3]).read_text()

    report_has_seed_identity_only = bool(report.get('seed_peer_identity'))
    report_has_no_java_peerfinder_map = 'peersByAddress' not in json.dumps(report, ensure_ascii=False)

    gateway_nodes = ((gateway.get('cluster_state') or {}).get('nodes') or [])
    gateway_transport_addresses = sorted({n.get('transport_address') for n in gateway_nodes if n.get('transport_address')})
    gateway_only_exposes_canonical_addresses = gateway_transport_addresses == ['127.0.0.1:38113', '127.0.0.1:48417']

    stdout_has_no_raw_peerfinder_probe_key_dump = 'peersByAddress' not in stdout_text and 'probing resolved transport addresses' not in stdout_text

    result = (
        'current_artifact_does_not_directly_expose_java_peerfinder_raw_probe_addresses'
        if report_has_seed_identity_only
        and report_has_no_java_peerfinder_map
        and gateway_only_exposes_canonical_addresses
        and stdout_has_no_raw_peerfinder_probe_key_dump
        else 'raw_probe_address_direct_exposure_not_yet_ruled_out'
    )

    print(json.dumps({
        'report_has_seed_identity_only': report_has_seed_identity_only,
        'report_has_no_java_peerfinder_map': report_has_no_java_peerfinder_map,
        'gateway_transport_addresses': gateway_transport_addresses,
        'gateway_only_exposes_canonical_addresses': gateway_only_exposes_canonical_addresses,
        'stdout_has_no_raw_peerfinder_probe_key_dump': stdout_has_no_raw_peerfinder_probe_key_dump,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
