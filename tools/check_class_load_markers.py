#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
if len(sys.argv) != 2:
    print('usage: check_class_load_markers.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)
report = json.loads(Path(sys.argv[1]).read_text())
text = report.get('opensearch_stdout','') + '\n' + report.get('opensearch_stderr','')
for name in ['CoordinationState', 'Publication']:
    print(f'{name}={len(re.findall(r"steelsearch_class_load_marker=" + name, text))}')
print(f"failure_stage={report.get('failure_stage')}")
print(f"blocker_class={report.get('blocker_class')}")
if 'steelsearch_class_load_marker=Publication' in text or 'steelsearch_class_load_marker=CoordinationState' in text:
    print('result=class_load_marker_surfaced')
else:
    print('result=class_load_marker_not_surfaced')
