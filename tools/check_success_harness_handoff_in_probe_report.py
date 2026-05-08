#!/usr/bin/env python3
import json
import sys
from pathlib import Path


if len(sys.argv) != 2:
    print('usage: check_success_harness_handoff_in_probe_report.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
handoff = report.get('success_harness_handoff') or {}
cluster_url = handoff.get('cluster_url')
java_node = handoff.get('java_node')
rust_node = handoff.get('rust_node')

print(f'cluster_url={cluster_url}')
print(f'java_node={java_node}')
print(f'rust_node={rust_node}')
if cluster_url and cluster_url.startswith('http://127.0.0.1:') and java_node and rust_node:
    print('result=success_harness_handoff_present_in_probe_report')
else:
    print('result=success_harness_handoff_missing_or_incomplete')
