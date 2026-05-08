#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
PROBE = ROOT / 'tools' / 'probe_java_rust_mixed_membership.sh'


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
    ap.add_argument('--trace-seconds', type=int, default=15)
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
    strace_path = work_dir / 'opensearch' / 'late-strace.log'
    jcmd_path = work_dir / 'opensearch' / 'jcmd-thread-print.txt'

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

    strace_returncode = None
    jcmd_returncode = None
    http_ready = False
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
            trace = subprocess.run([
                'timeout', f'{args.trace_seconds}s',
                'sudo', 'strace', '-f', '-tt', '-T', '-yy', '-s', '256',
                '-e', 'trace=read,close,epoll_pwait,ppoll,futex',
                '-p', pid,
                '-o', str(strace_path),
            ], capture_output=True, text=True)
            strace_returncode = 0 if trace.returncode in (0, 124) else trace.returncode
            jcmd = subprocess.run(['jcmd', pid, 'Thread.print'], capture_output=True, text=True)
            jcmd_returncode = jcmd.returncode
            jcmd_path.write_text(jcmd.stdout + jcmd.stderr, encoding='utf-8')
        probe.communicate(timeout=args.probe_wait_seconds)
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

    summary = {
        'work_dir': str(work_dir),
        'report_path': str(report_path),
        'strace_path': str(strace_path),
        'jcmd_thread_print_path': str(jcmd_path),
        'strace_returncode': strace_returncode,
        'jcmd_returncode': jcmd_returncode,
        'http_ready_before_trace': http_ready,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'trace_seconds': args.trace_seconds,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'late_strace_and_jcmd_collected_on_failing_probe'
            if strace_returncode == 0 and jcmd_returncode == 0 and report is not None and strace_path.exists()
            else 'late_strace_and_jcmd_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
