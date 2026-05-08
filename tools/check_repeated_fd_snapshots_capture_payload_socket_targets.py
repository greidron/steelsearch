#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

HEADER_RE = re.compile(
    r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$'
)
FD_RE = re.compile(r'fd:\s+0x(?P<fd>[0-9a-fA-F]+)')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')


def main() -> int:
    script_path = Path(sys.argv[1])
    snapshot_dir = Path(sys.argv[2])

    payload_fds = Counter()
    for line in script_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = HEADER_RE.match(line)
        if not m:
            continue
        rest = m.group('rest')
        fdm = FD_RE.search(rest)
        cm = COUNT_RE.search(rest)
        if not fdm or not cm:
            continue
        fd = int(fdm.group('fd'), 16)
        count = int(cm.group('count'), 16)
        if count >= 1024:
            payload_fds[fd] += 1

    payload_fd_targets = {fd: [] for fd in payload_fds}
    snapshot_files = sorted(snapshot_dir.glob('*.json'))
    for snap in snapshot_files:
        data = {int(k): v for k, v in json.loads(snap.read_text(encoding='utf-8')).items()}
        for fd in payload_fds:
            target = data.get(fd)
            if target is not None:
                payload_fd_targets[fd].append({'snapshot': snap.name, 'target': target})

    result = {
        'script_path': str(script_path),
        'snapshot_dir': str(snapshot_dir),
        'payload_fds': [{'fd': fd, 'count': c} for fd, c in payload_fds.most_common()],
        'payload_fd_targets': payload_fd_targets,
        'checker_result': (
            'repeated_fd_snapshots_captured_live_socket_targets_for_payload_fds'
            if any(any(item['target'].startswith('socket:[') for item in entries) for entries in payload_fd_targets.values())
            else 'repeated_fd_snapshots_still_did_not_capture_live_socket_targets_for_payload_fds'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
