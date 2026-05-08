#!/usr/bin/env python3
import argparse
import urllib.request
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
PROBE = ROOT / 'tools' / 'probe_java_rust_mixed_membership.sh'
DEFAULT_EVENTS = [
    'syscalls:sys_enter_read',
    'syscalls:sys_enter_close',
    'syscalls:sys_enter_epoll_pwait',
    'syscalls:sys_enter_epoll_pwait2',
]


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


def syscall_counts(text: str, events):
    counts = {}
    for event in events:
        name = event.split('sys_enter_', 1)[1] if 'sys_enter_' in event else event
        counts[name] = text.count(event)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--work-dir', required=True)
    ap.add_argument('--trace-duration-ms', type=int, default=15000)
    ap.add_argument('--membership-timeout-seconds', type=int, default=60)
    ap.add_argument('--probe-wait-seconds', type=int, default=300)
    ap.add_argument('--summary-path', required=True)
    ap.add_argument('--events', nargs='*', default=DEFAULT_EVENTS)
    ap.add_argument('--late-start-after-http-ready-seconds', type=int, default=0)
    args = ap.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary_path)
    live_path = Path(f"{work_dir}.live.json")
    formed_path = Path(f"{work_dir}.formed.json")
    trace_out = work_dir / 'opensearch' / 'sudo-perf-trace.txt'
    pid_path = work_dir / 'opensearch' / 'pid'
    launch_env_path = work_dir / 'opensearch' / 'launch-env.json'
    report_path = work_dir / 'report.json'

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

    trace_returncode = None
    combined_trace = ''
    http_ready = False
    try:
        pid = None
        if wait_for_file(pid_path, 90):
            pid = pid_path.read_text(encoding='utf-8').strip()
            if args.late_start_after_http_ready_seconds > 0 and wait_for_file(launch_env_path, 30):
                launch_env = json.loads(launch_env_path.read_text(encoding='utf-8'))
                http_port = launch_env.get('OPENSEARCH_HTTP_PORT')
                if http_port:
                    http_ready = wait_for_http(f'http://127.0.0.1:{http_port}', 120)
                    if http_ready:
                        time.sleep(args.late_start_after_http_ready_seconds)
            trace_cmd = [
                'timeout', f'{max(1, args.trace_duration_ms // 1000)}s',
                'sudo', 'perf', 'trace',
                '-e', ','.join(args.events),
                '-p', pid,
            ]
            trace = subprocess.run(trace_cmd, capture_output=True, text=True)
            trace_returncode = 0 if trace.returncode in (0, 124) else trace.returncode
            combined_trace = (trace.stdout or '') + '\n' + (trace.stderr or '')
            trace_out.parent.mkdir(parents=True, exist_ok=True)
            trace_out.write_text(combined_trace, encoding='utf-8')
        stdout, stderr = probe.communicate(timeout=args.probe_wait_seconds)
        probe_returncode = probe.returncode
    except subprocess.TimeoutExpired:
        probe.terminate()
        try:
            stdout, stderr = probe.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            probe.kill()
            stdout, stderr = probe.communicate()
        probe_returncode = probe.returncode

    report = None
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding='utf-8'))

    counts = syscall_counts(combined_trace, args.events)
    summary = {
        'work_dir': str(work_dir),
        'report_path': str(report_path),
        'live_handoff_path': str(live_path),
        'formed_handoff_path': str(formed_path),
        'trace_output_path': str(trace_out),
        'trace_returncode': trace_returncode,
        'trace_duration_ms': args.trace_duration_ms,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'http_ready_before_trace': http_ready,
        'events': args.events,
        'syscall_counts': counts,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'sudo_perf_trace_collected_on_failing_probe'
            if trace_returncode == 0 and report is not None
            else 'sudo_perf_trace_probe_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
