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
EVENTS = ['syscalls:sys_enter_read', 'syscalls:sys_enter_close']


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
    ap.add_argument('--jcmd-interval-ms', type=int, default=250)
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
    perf_data_path = work_dir / 'opensearch' / 'sudo-perf-record-repeated-jcmd.data'
    perf_script_path = work_dir / 'opensearch' / 'sudo-perf-record-repeated-jcmd.script.txt'
    jcmd_dir = work_dir / 'opensearch' / 'jcmd-repeated'

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

    probe = subprocess.Popen(['bash', str(PROBE)], cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    record_returncode = None
    script_returncode = None
    http_ready = False
    snapshot_count = 0
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
            jcmd_dir.mkdir(parents=True, exist_ok=True)
            perf_proc = subprocess.Popen([
                'sudo', 'perf', 'record', '-g',
                '-o', str(perf_data_path),
                '-e', ','.join(EVENTS),
                '-p', pid,
                '--', 'sleep', str(args.record_seconds),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            deadline = time.time() + args.record_seconds
            interval = max(args.jcmd_interval_ms / 1000.0, 0.05)
            while time.time() < deadline:
                snapshot_count += 1
                out = subprocess.run(['jcmd', pid, 'Thread.print'], capture_output=True, text=True)
                snap_path = jcmd_dir / f'jcmd-{snapshot_count:04d}.txt'
                snap_path.write_text(out.stdout + out.stderr, encoding='utf-8')
                time.sleep(interval)
            perf_stdout, perf_stderr = perf_proc.communicate(timeout=max(args.record_seconds + 10, 30))
            record_returncode = perf_proc.returncode
            if perf_stdout or perf_stderr:
                (work_dir / 'opensearch' / 'sudo-perf-record-repeated-jcmd.stderr.txt').write_text(perf_stdout + perf_stderr, encoding='utf-8')
            script = subprocess.run(['sudo', 'perf', 'script', '-i', str(perf_data_path)], capture_output=True, text=True)
            script_returncode = script.returncode
            perf_script_path.write_text(script.stdout + script.stderr, encoding='utf-8')
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
        'perf_data_path': str(perf_data_path),
        'perf_script_path': str(perf_script_path),
        'jcmd_dir': str(jcmd_dir),
        'record_returncode': record_returncode,
        'script_returncode': script_returncode,
        'http_ready_before_record': http_ready,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'record_seconds': args.record_seconds,
        'jcmd_interval_ms': args.jcmd_interval_ms,
        'snapshot_count': snapshot_count,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'late_repeated_jcmd_and_perf_collected_on_failing_probe'
            if record_returncode == 0 and script_returncode == 0 and http_ready and report is not None and snapshot_count > 0
            else 'late_repeated_jcmd_and_perf_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
