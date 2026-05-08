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
    jfr_path = work_dir / 'opensearch' / 'late.jfr'
    jfr_print_path = work_dir / 'opensearch' / 'late-jfr-print.txt'

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

    jfr_start_rc = None
    jfr_print_rc = None
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
            start = subprocess.run([
                'jcmd', pid, 'JFR.start', 'name=steelsearchlate', 'settings=profile',
                f'filename={jfr_path}', f'duration={args.record_seconds}s'
            ], capture_output=True, text=True, timeout=30)
            jfr_start_rc = start.returncode
            if start.returncode == 0:
                time.sleep(args.record_seconds + 2)
                pr = subprocess.run([
                    'jfr', 'print', '--events', 'jdk.ExecutionSample,jdk.NativeMethodSample', str(jfr_path)
                ], capture_output=True, text=True, timeout=60)
                jfr_print_rc = pr.returncode
                jfr_print_path.write_text(pr.stdout + pr.stderr, encoding='utf-8')
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

    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
    summary = {
        'work_dir': str(work_dir),
        'jfr_path': str(jfr_path),
        'jfr_print_path': str(jfr_print_path),
        'jfr_start_rc': jfr_start_rc,
        'jfr_print_rc': jfr_print_rc,
        'http_ready_before_record': http_ready,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'record_seconds': args.record_seconds,
        'probe_returncode': probe_returncode,
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'checker_result': (
            'late_jfr_collected_on_failing_probe'
            if jfr_start_rc == 0 and jfr_print_rc == 0 and report is not None and jfr_path.exists() and jfr_print_path.exists()
            else 'late_jfr_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
