#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

FMT='[%Y-%m-%dT%H:%M:%S,%f]'

CLOSE_RE = re.compile(r'^(\[[^]]+\]).*closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.*age \[(\d+)ms\]')
DISC_RE = re.compile(r'^(\[[^]]+\]).*FollowersChecker .* disconnected')
MARK_RE = re.compile(r'^(\[[^]]+\]).*FollowersChecker .* marking node as faulty')
FAIL_RE = re.compile(r'^(\[[^]]+\]).*failed to join')

CALL_RE = re.compile(r'\.disconnectFromNode\(')
CLOSE_CALL_RE = re.compile(r'getConnection\(.*\)\.close\(|\.close\(\)')


def ts(s: str):
    return datetime.strptime(s, FMT)


def scan_source(root: Path):
    explicit_disconnect_call_count = 0
    transport_close_call_count = 0
    explicit_disconnect_files = []
    transport_close_files = []
    for path in sorted(root.rglob('*.java')):
        text = path.read_text(errors='ignore')
        for i, line in enumerate(text.splitlines(), 1):
            if '.disconnectFromNode(' in line:
                explicit_disconnect_call_count += 1
                explicit_disconnect_files.append(f'{path}:{i}:{line.strip()}')
            if 'getConnection(' in line and '.close()' in line:
                transport_close_call_count += 1
                transport_close_files.append(f'{path}:{i}:{line.strip()}')
    return {
        'explicit_disconnect_call_count': explicit_disconnect_call_count,
        'transport_close_call_count': transport_close_call_count,
        'explicit_disconnect_files': explicit_disconnect_files,
        'transport_close_files': transport_close_files,
    }


def parse_stdout(path: Path):
    rows = []
    for line in path.read_text(errors='ignore').splitlines():
        m = CLOSE_RE.search(line)
        if m:
            rows.append(('close', ts(m.group(1)), int(m.group(3))))
            continue
        for typ, rx in [('disc', DISC_RE), ('mark', MARK_RE), ('fail', FAIL_RE)]:
            m = rx.search(line)
            if m:
                rows.append((typ, ts(m.group(1))))
                break
    closes = [r for r in rows if r[0] == 'close']
    others = [r for r in rows if r[0] != 'close']
    summary = []
    for _, close_ts, age_ms in closes:
        item = {'age_ms': age_ms}
        for typ in ('disc', 'mark', 'fail'):
            matches = [int((o[1] - close_ts).total_seconds() * 1000) for o in others if o[0] == typ and 0 <= (o[1] - close_ts).total_seconds() * 1000 <= 250]
            item[f'{typ}_after_close_ms'] = min(matches) if matches else None
        summary.append(item)
    return summary


def band_name(age_ms: int) -> str:
    return '600ms' if age_ms < 700 else '800ms'


def median_or_none(values):
    values = sorted(values)
    if not values:
        return None
    n = len(values)
    if n % 2:
        return values[n // 2]
    return (values[n // 2 - 1] + values[n // 2]) / 2


def summarize(summary):
    out = {}
    for band in ('600ms', '800ms'):
        vals = [s for s in summary if band_name(s['age_ms']) == band]
        out[band] = {
            'count': len(vals),
            'disc_after_close_count': sum(v['disc_after_close_ms'] is not None for v in vals),
            'mark_after_close_count': sum(v['mark_after_close_ms'] is not None for v in vals),
            'fail_after_close_count': sum(v['fail_after_close_ms'] is not None for v in vals),
            'disc_after_close_median_ms': median_or_none([v['disc_after_close_ms'] for v in vals if v['disc_after_close_ms'] is not None]),
            'mark_after_close_median_ms': median_or_none([v['mark_after_close_ms'] for v in vals if v['mark_after_close_ms'] is not None]),
            'fail_after_close_median_ms': median_or_none([v['fail_after_close_ms'] for v in vals if v['fail_after_close_ms'] is not None]),
        }
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_upstream_transport_close_is_lower_transport_channel_path.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = Path(sys.argv[1])
    data = json.loads(artifact.read_text())
    work_dir = Path(data['work_dir'])
    stdout_log = work_dir / 'opensearch' / 'stdout.log'
    repo_root = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch')
    source_summary = {
        'coordination': scan_source(repo_root / 'cluster' / 'coordination'),
        'discovery': scan_source(repo_root / 'discovery'),
    }
    log_summary = summarize(parse_stdout(stdout_log))
    no_explicit_disconnect = source_summary['coordination']['explicit_disconnect_call_count'] == 0 and source_summary['discovery']['explicit_disconnect_call_count'] == 0
    reactive_after_close = all(log_summary[b]['disc_after_close_median_ms'] == 0 for b in ('600ms', '800ms') if log_summary[b]['disc_after_close_median_ms'] is not None)
    result = 'upstream_transport_close_points_to_lower_transport_channel_close_not_publication_or_followers_shared_connection_teardown' if no_explicit_disconnect and reactive_after_close else 'inconclusive'
    print(json.dumps({
        'work_dir': str(work_dir),
        'coordination_explicit_disconnect_call_count': source_summary['coordination']['explicit_disconnect_call_count'],
        'discovery_explicit_disconnect_call_count': source_summary['discovery']['explicit_disconnect_call_count'],
        'coordination_transport_close_call_count': source_summary['coordination']['transport_close_call_count'],
        'discovery_transport_close_call_count': source_summary['discovery']['transport_close_call_count'],
        'band_summary': log_summary,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
