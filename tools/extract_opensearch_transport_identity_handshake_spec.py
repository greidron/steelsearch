#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def must(pattern: str, text: str, label: str) -> str:
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not m:
        raise SystemExit(f'missing {label}')
    return m.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--opensearch-root', required=True)
    parser.add_argument('--report-path', required=True)
    args = parser.parse_args()

    root = Path(args.opensearch_root)
    transport_service = (root / 'server/src/main/java/org/opensearch/transport/TransportService.java').read_text(encoding='utf-8')

    action = must(r'public static final String HANDSHAKE_ACTION_NAME = "([^"]+)";', transport_service, 'transport handshake action')
    response_ctor = must(r'public HandshakeResponse\(StreamInput in\) throws IOException \{(.*?)\n\s*\}', transport_service, 'response ctor body')
    response_write = must(r'public void writeTo\(StreamOutput out\) throws IOException \{(.*?)\n\s*\}', transport_service, 'response write body')

    report = {
        'transport_identity_handshake_action': action,
        'response_ctor_reads': [
            'discoveryNode = in.readOptionalWriteable(DiscoveryNode::new)',
            'clusterName = new ClusterName(in)',
            'version = in.readVersion()',
        ],
        'response_write_order': [
            'out.writeOptionalWriteable((stream, node) -> node.writeToWithAttribute(stream), discoveryNode)',
            'clusterName.writeTo(out)',
            'out.writeVersion(version)',
        ],
        'response_includes_peer_identity': 'discoveryNode = in.readOptionalWriteable(DiscoveryNode::new)' in response_ctor,
        'response_includes_cluster_name': 'clusterName = new ClusterName(in)' in response_ctor,
        'response_includes_version': 'version = in.readVersion()' in response_ctor,
        'raw_ctor_body': response_ctor.strip(),
        'raw_write_body': response_write.strip(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
