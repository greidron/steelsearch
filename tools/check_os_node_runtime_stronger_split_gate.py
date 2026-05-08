#!/usr/bin/env python3
import json
from pathlib import Path

DOC = Path('/home/ubuntu/steelsearch/docs/rust-port/os-node-runtime-stronger-split-go-no-go.md')
text = DOC.read_text()
required = {
    'decision': 'NO-GO',
    'scope': '27 files / 35053 lines',
    'phase1': 'os-node-rest-core',
    'standalone': 'standalone_runtime.rs',
    'go_conditions': '## Go conditions',
    'no_go_action': '## No-go action for now',
}
result = {
    'doc_exists': DOC.exists(),
    'contains': {k: v in text for k, v in required.items()},
}
result['all_required_present'] = all(result['contains'].values())
result['result'] = 'os_node_runtime_stronger_split_go_no_go_gate_documented' if result['all_required_present'] else 'missing_required_gate_content'
print(json.dumps(result, indent=2, sort_keys=True))
