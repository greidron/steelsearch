#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
if len(sys.argv) != 2:
    print('usage: check_publication_entry_markers.py <probe-report.json>', file=sys.stderr)
    sys.exit(2)
report = json.loads(Path(sys.argv[1]).read_text())
text = report.get('opensearch_stdout','') + '\n' + report.get('opensearch_stderr','')
patterns = {
    'publication_onresponse_entry': r'steelsearch_publication_onResponse_entry',
    'handlejoin_entry': r'steelsearch_handleJoin_entry',
    'handlejoin_rejection': r'steelsearch_handleJoin_rejection_class=',
    'publication_response_class': r'steelsearch_publication_response_class=',
}
for k, pat in patterns.items():
    print(f'{k}={len(re.findall(pat, text))}')
print(f"failure_stage={report.get('failure_stage')}")
print(f"blocker_class={report.get('blocker_class')}")
if re.search(patterns['publication_onresponse_entry'], text):
    print('result=publication_entry_marker_surfaced')
else:
    print('result=publication_entry_marker_not_surfaced')
