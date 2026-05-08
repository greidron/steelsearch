#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print(
        'usage: check_explicitlocalclose_points_away_from_native_handshake_and_secure_dualmode_paths.py '
        '<probe-report.json> <NativeMessageHandler.java> <SecureNetty4Transport.java>',
        file=sys.stderr,
    )
    sys.exit(2)

report = json.loads(Path(sys.argv[1]).read_text())
stdout_log = Path(report['work_dir']) / 'opensearch' / 'stdout.log'
text = stdout_log.read_text(errors='ignore')
native = Path(sys.argv[2]).read_text()
secure = Path(sys.argv[3]).read_text()

failure_port = None
for line in text.splitlines():
    if 'steelsearch_publication_response_class=transport_failure' in line:
        m = re.search(r'\{127\.0\.0\.1:(\d+)\}', line)
        if m:
            failure_port = m.group(1)
            break
if failure_port is None:
    print('result=missing_failure_port')
    sys.exit(1)

native_literal = 'could not send error response to handshake received on ['
secure_literal = 'dual mode handshake and OpenSearch ping has failed during client connection setup, closing channel'

explicit_port_count = len(re.findall(rf'hint \[explicitLocalClose\].*39895|39895.*hint \[explicitLocalClose\]', text))
probe_null_close_count = len(re.findall(rf'netty4 tcp channel close completed for \[\[id: .* L:null ! R:/127\.0\.0\.1:{failure_port}\]\] with hint \[explicitLocalClose\]', text))
node_channel_close_count = len(re.findall(rf'netty4 tcp channel close completed for \[\[id: .*127\.0\.0\.1:{failure_port}\]\] with hint \[explicitLocalClose\]', text))

print(f'failure_port={failure_port}')
print(f'explicit_local_close_count_for_failure_port={explicit_port_count}')
print(f'probe_null_close_count={probe_null_close_count}')
print(f'node_channel_close_count={node_channel_close_count}')
print(f'source_native_handshake_raw_close_exists={native_literal in native and "channel.close();" in native}')
print(f'source_secure_dualmode_raw_close_exists={secure_literal in secure and "ch.close();" in secure}')
print(f'artifact_has_native_handshake_literal={native_literal in text}')
print(f'artifact_has_secure_dualmode_literal={secure_literal in text}')

if (
    explicit_port_count > 0
    and native_literal in native
    and secure_literal in secure
    and native_literal not in text
    and secure_literal not in text
):
    print('result=explicitlocalclose_points_away_from_native_handshake_and_secure_dualmode_exception_paths_and_toward_other_teardown_callers')
else:
    print('result=explicitlocalclose_caller_still_ambiguous_with_native_or_secure_exception_paths')
