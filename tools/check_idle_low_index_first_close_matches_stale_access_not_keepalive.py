#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

SEL_RE = re.compile(r'action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\].*for \[\{rust-replica-1\}')
OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_idle_low_index_first_close_matches_stale_access_not_keepalive.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    selected = Counter()
    first = Counter()
    conn_rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = SEL_RE.search(line)
        if m:
            selected[int(m.group(1))] += 1
            continue
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            order = int(m.group(3))
            conn_rows.setdefault(cid, []).append((order, idx))
    for cid, rows in conn_rows.items():
        first[sorted(rows)[0][1]] += 1

    src_tcp = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpTransport.java').read_text(errors='ignore')
    src_out = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/OutboundHandler.java').read_text(errors='ignore')
    src_in = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/InboundPipeline.java').read_text(errors='ignore')
    src_keep = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TransportKeepAlive.java').read_text(errors='ignore')

    source_marks_all_channels_at_open = 'ch.getChannelStats().markAccessed(relativeMillisTime);' in src_tcp
    source_marks_active_channels_on_outbound = 'channel.getChannelStats().markAccessed(threadPool.relativeTimeInMillis());' in src_out
    source_marks_active_channels_on_inbound = 'channel.getChannelStats().markAccessed(relativeTimeInMillis.getAsLong());' in src_in
    source_keepalive_registers_all_channels = 'for (TcpChannel channel : nodeChannels)' in src_keep and 'scheduledPing.addChannel(channel);' in src_keep

    idle_first = sum(first[i] for i in (1, 2, 5, 6))
    idle_selected = sum(selected[i] for i in (1, 2, 5, 6))
    result = 'idle_low_index_first_close_best_matches_stale_access_on_unused_siblings_not_selective_keepalive_or_active_bulk_recovery_pressure' if source_marks_all_channels_at_open and source_marks_active_channels_on_outbound and source_marks_active_channels_on_inbound and source_keepalive_registers_all_channels and idle_first > 0 and idle_selected == 0 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'source_marks_all_channels_at_open': source_marks_all_channels_at_open,
        'source_marks_active_channels_on_outbound': source_marks_active_channels_on_outbound,
        'source_marks_active_channels_on_inbound': source_marks_active_channels_on_inbound,
        'source_keepalive_registers_all_channels': source_keepalive_registers_all_channels,
        'selected_index_counts': dict(sorted(selected.items())),
        'earliest_index_distribution': dict(sorted(first.items())),
        'idle_first_count_1_2_5_6': idle_first,
        'idle_selected_count_1_2_5_6': idle_selected,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
