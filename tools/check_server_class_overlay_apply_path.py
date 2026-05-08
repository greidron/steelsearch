#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print('usage: check_server_class_overlay_apply_path.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
work_dir = Path(report['work_dir'])
jar_path = work_dir / 'opensearch' / 'lib' / 'opensearch-3.7.0-SNAPSHOT.jar'
if not jar_path.exists():
    print(f'jar_exists=false')
    print(f'jar_path={jar_path}')
    print('result=missing_runtime_jar')
    sys.exit(1)

needles = {
    'coordination_canary': 'steelsearch_class_load_marker=CoordinationState',
    'publication_canary': 'steelsearch_class_load_marker=Publication',
    'publication_entry_canary': 'steelsearch_publication_onResponse_entry',
    'handlejoin_entry_canary': 'steelsearch_handleJoin_entry',
}

strings_output = subprocess.check_output(['strings', str(jar_path)], text=True, errors='ignore')
print(f'jar_exists=true')
print(f'jar_path={jar_path}')
for key, needle in needles.items():
    print(f'{key}={str(needle in strings_output).lower()}')

if any(needle in strings_output for needle in needles.values()):
    print('result=server_overlay_canary_is_present_in_runtime_jar')
else:
    print('result=server_overlay_canary_is_not_present_in_runtime_jar')
