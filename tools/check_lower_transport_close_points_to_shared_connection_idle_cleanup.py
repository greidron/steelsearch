#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

FMT='[%Y-%m-%dT%H:%M:%S,%f]'
PUBLISH_RE = re.compile(r'^(\[[^]]+\]).*action-tagged selected channel index \[4\] type \[STATE\] action \[internal:cluster/coordination/publish_state\]')
FOLLOWER_RE = re.compile(r'^(\[[^]]+\]).*action-tagged selected channel index \[3\] type \[PING\] action \[internal:coordination/fault_detection/follower_check\]')
CLOSE_RE = re.compile(r'^(\[[^]]+\]).*closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.*age \[(\d+)ms\]')


def ts(s: str):
    return datetime.strptime(s, FMT)


def read_source_counts():
    files = [
        Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/PublicationTransportHandler.java'),
        Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/Coordinator.java'),
        Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/cluster/coordination/JoinHelper.java'),
    ]
    hits = []
    for path in files:
        for i, line in enumerate(path.read_text(errors='ignore').splitlines(), 1):
            if '.disconnectFromNode(' in line or ('getConnection(' in line and '.close()' in line):
                hits.append(f'{path}:{i}:{line.strip()}')
    return hits


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    if n % 2:
        return xs[n//2]
    return (xs[n//2-1] + xs[n//2]) / 2


def main():
    if len(sys.argv) != 2:
        print('usage: check_lower_transport_close_points_to_shared_connection_idle_cleanup.py <artifact.json>', file=sys.stderr)
        return 2
    data = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(data['work_dir']) / 'opensearch' / 'stdout.log'

    publish_ts = []
    follower_ts = []
    close_rows = []
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = PUBLISH_RE.search(line)
        if m:
            publish_ts.append(ts(m.group(1)))
            continue
        m = FOLLOWER_RE.search(line)
        if m:
            follower_ts.append(ts(m.group(1)))
            continue
        m = CLOSE_RE.search(line)
        if m:
            close_rows.append((ts(m.group(1)), int(m.group(3))))

    # match each rust close to nearest preceding publish/follower within 1s
    publish_to_close = []
    follower_to_close = []
    band = {'600ms': {'publish_to_close': [], 'follower_to_close': []}, '800ms': {'publish_to_close': [], 'follower_to_close': []}}
    for close_t, age_ms in close_rows:
        pubs = [int((close_t - p).total_seconds()*1000) for p in publish_ts if 0 <= (close_t - p).total_seconds()*1000 <= 1000]
        fcs = [int((close_t - f).total_seconds()*1000) for f in follower_ts if 0 <= (close_t - f).total_seconds()*1000 <= 1000]
        b = '600ms' if age_ms < 700 else '800ms'
        if pubs:
            v = min(pubs)
            publish_to_close.append(v)
            band[b]['publish_to_close'].append(v)
        if fcs:
            v = min(fcs)
            follower_to_close.append(v)
            band[b]['follower_to_close'].append(v)

    publication_close_hits = read_source_counts()
    result = 'lower_transport_close_points_away_from_immediate_publication_response_handling_and_toward_shared_connection_idle_cleanup' if not publication_close_hits and median(publish_to_close) and median(publish_to_close) > 200 else 'inconclusive'
    out = {
        'work_dir': data['work_dir'],
        'publication_side_explicit_close_hits': publication_close_hits,
        'publish_state_count': len(publish_ts),
        'follower_check_count': len(follower_ts),
        'named_rust_close_count': len(close_rows),
        'publish_to_close_median_ms': median(publish_to_close),
        'follower_to_close_median_ms': median(follower_to_close),
        'band_summary': {
            k: {
                'publish_to_close_median_ms': median(v['publish_to_close']),
                'follower_to_close_median_ms': median(v['follower_to_close']),
                'count': len(v['publish_to_close'])
            } for k,v in band.items()
        },
        'result': result,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
