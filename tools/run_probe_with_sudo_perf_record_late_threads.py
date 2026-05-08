#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
PROBE = ROOT / 'tools' / 'probe_java_rust_mixed_membership.sh'
EVENTS = [
    'syscalls:sys_enter_read',
    'syscalls:sys_enter_close',
    'syscalls:sys_enter_epoll_pwait',
    'syscalls:sys_enter_epoll_pwait2',
]
HEADER_RE = re.compile(
    r'^(?P<comm>\S+)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+(?P<event>syscalls:sys_enter_[^:]+):'
)


def wait_for_file(path: Path, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.read_text(encoding='utf-8', errors='ignore').strip():
            return True
        time.sleep(0.5)
    return False


def wait_for_http(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--work-dir', required=True)
    ap.add_argument('--record-seconds', type=int, default=15)
    ap.add_argument('--membership-timeout-seconds', type=int, default=60)
    ap.add_argument('--probe-wait-seconds', type=int, default=300)
    ap.add_argument('--late-start-after-http-ready-seconds', type=int, default=20)
    ap.add_argument('--summary-path', required=True)
    args = ap.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary_path)
    live_path = Path(f"{work_dir}.live.json")
    formed_path = Path(f"{work_dir}.formed.json")
    pid_path = work_dir / 'opensearch' / 'pid'
    launch_env_path = work_dir / 'opensearch' / 'launch-env.json'
    report_path = work_dir / 'report.json'
    perf_data_path = work_dir / 'opensearch' / 'sudo-perf-record-late-threads.data'
    perf_script_path = work_dir / 'opensearch' / 'sudo-perf-record-late-threads.script.txt'

    env = os.environ.copy()
    env.update({
        'JAVA_RUST_MIXED_MEMBERSHIP_WORK_DIR': str(work_dir),
        'JAVA_RUST_MIXED_MEMBERSHIP_LIVE_HANDOFF_REPORT_PATH': str(live_path),
        'JAVA_RUST_MIXED_MEMBERSHIP_FORMED_HANDOFF_REPORT_PATH': str(formed_path),
        'JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED': 'true',
        'JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_SPLIT_BUILD_RUN': '1',
        'JAVA_RUST_MIXED_MEMBERSHIP_STEELSEARCH_TRANSPORT_PRE_FIRST_FRAME_TIMEOUT_MS': '5000',
        'JAVA_RUST_MIXED_MEMBERSHIP_MEMBERSHIP_TIMEOUT_SECONDS': str(args.membership_timeout_seconds),
    })

    probe = subprocess.Popen(
        ['bash', str(PROBE)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    record_returncode = None
    script_returncode = None
    http_ready = False
    thread_event_counts = defaultdict(lambda: {'comm': None, 'read': 0, 'close': 0, 'epoll_pwait': 0, 'epoll_pwait2': 0})
    try:
        if wait_for_file(pid_path, 90):
            pid = pid_path.read_text(encoding='utf-8').strip()
            if wait_for_file(launch_env_path, 30):
                launch_env = json.loads(launch_env_path.read_text(encoding='utf-8'))
                http_port = launch_env.get('OPENSEARCH_HTTP_PORT')
                if http_port:
                    http_ready = wait_for_http(f'http://127.0.0.1:{http_port}', 120)
                    if http_ready:
                        time.sleep(args.late_start_after_http_ready_seconds)
            perf_data_path.parent.mkdir(parents=True, exist_ok=True)
            record_cmd = [
                'timeout', f'{args.record_seconds}s',
                'sudo', 'perf', 'record',
                '-o', str(perf_data_path),
                '-e', ','.join(EVENTS),
                '-p', pid,
                '--', 'sleep', str(args.record_seconds),
            ]
            record = subprocess.run(record_cmd, capture_output=True, text=True)
            record_returncode = 0 if record.returncode in (0, 124) else record.returncode
            script = subprocess.run(
                ['sudo', 'perf', 'script', '-i', str(perf_data_path)],
                capture_output=True,
                text=True,
            )
            script_returncode = script.returncode
            perf_script_path.write_text(script.stdout + script.stderr, encoding='utf-8')
            for line in script.stdout.splitlines():
                m = HEADER_RE.match(line)
                if not m:
                    continue
                tid = int(m.group('tid'))
                comm = m.group('comm')
                event = m.group('event').split('sys_enter_', 1)[1]
                bucket = thread_event_counts[tid]
                bucket['comm'] = comm
                if event in bucket:
                    bucket[event] += 1
        _, _ = probe.communicate(timeout=args.probe_wait_seconds)
        probe_returncode = probe.returncode
    except subprocess.TimeoutExpired:
        probe.terminate()
        try:
            probe.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            probe.kill()
            probe.communicate()
        probe_returncode = probe.returncode

    report = None
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding='utf-8'))

    threads = []
    overlap_threads = []
    wait_only_threads = []
    read_only_threads = []
    for tid, counts in sorted(thread_event_counts.items()):
        row = {'tid': tid, **counts}
        threads.append(row)
        has_wait = counts['epoll_pwait'] > 0 or counts['epoll_pwait2'] > 0
        has_read = counts['read'] > 0
        if has_wait and has_read:
            overlap_threads.append(row)
        elif has_wait:
            wait_only_threads.append(row)
        elif has_read:
            read_only_threads.append(row)

    summary = {
        'work_dir': str(work_dir),
        'report_path': str(report_path),
        'live_handoff_path': str(live_path),
        'formed_handoff_path': str(formed_path),
        'perf_data_path': str(perf_data_path),
        'perf_script_path': str(perf_script_path),
        'record_returncode': record_returncode,
        'script_returncode': script_returncode,
        'http_ready_before_record': http_ready,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'record_seconds': args.record_seconds,
        'thread_count': len(threads),
        'overlap_threads': overlap_threads,
        'wait_only_threads': wait_only_threads,
        'read_only_threads': read_only_threads,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'late_thread_aware_perf_record_collected_on_failing_probe'
            if record_returncode == 0 and script_returncode == 0 and report is not None
            else 'late_thread_aware_perf_record_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
