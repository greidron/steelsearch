#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
PROBE = ROOT / 'tools' / 'probe_java_rust_mixed_membership.sh'
COUNT_RE = re.compile(r'^\s*([0-9,]+)\s+raw_syscalls:(sys_enter|sys_exit)\b')


def parse_perf_counts(text: str):
    counts = {}
    for line in text.splitlines():
        m = COUNT_RE.match(line)
        if m:
            counts[m.group(2)] = int(m.group(1).replace(',', ''))
    return counts


def wait_for_file(path: Path, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.read_text(encoding='utf-8', errors='ignore').strip():
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--work-dir', required=True)
    ap.add_argument('--perf-seconds', type=int, default=15)
    ap.add_argument('--membership-timeout-seconds', type=int, default=60)
    ap.add_argument('--summary-path', required=True)
    ap.add_argument('--probe-wait-seconds', type=int, default=300)
    args = ap.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary_path)
    live_path = Path(f"{work_dir}.live.json")
    formed_path = Path(f"{work_dir}.formed.json")
    perf_out = work_dir / 'opensearch' / 'sudo-perf-stat.txt'
    pid_path = work_dir / 'opensearch' / 'pid'
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

    perf_returncode = None
    perf_counts = {}
    perf_stderr = ''
    try:
        if wait_for_file(pid_path, 90):
            pid = pid_path.read_text(encoding='utf-8').strip()
            perf_cmd = [
                'sudo', 'perf', 'stat',
                '-e', 'raw_syscalls:sys_enter,raw_syscalls:sys_exit',
                '-p', pid,
                '--', 'sleep', str(args.perf_seconds),
            ]
            perf = subprocess.run(perf_cmd, capture_output=True, text=True)
            perf_returncode = perf.returncode
            perf_stderr = perf.stderr
            perf_counts = parse_perf_counts(perf.stderr)
            perf_out.parent.mkdir(parents=True, exist_ok=True)
            perf_out.write_text(perf.stderr, encoding='utf-8')
        else:
            pid = None
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

    summary = {
        'work_dir': str(work_dir),
        'report_path': str(report_path),
        'live_handoff_path': str(live_path),
        'formed_handoff_path': str(formed_path),
        'opensearch_pid_path': str(pid_path),
        'perf_output_path': str(perf_out),
        'perf_returncode': perf_returncode,
        'perf_counts': perf_counts,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'sudo_perf_stat_collected_on_failing_probe'
            if perf_returncode == 0 and report is not None
            else 'sudo_perf_stat_probe_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
