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
HEADER_RE = re.compile(r'^\s*(?P<comm>\S+)\s+(?P<pid>\d+)\/(?P<tid>\d+)\s+')
EVENT_MARKER = 'syscalls:sys_enter_futex:'


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
    ap.add_argument('--record-seconds', type=int, default=15)
    ap.add_argument('--membership-timeout-seconds', type=int, default=60)
    ap.add_argument('--probe-wait-seconds', type=int, default=300)
    ap.add_argument('--summary-path', required=True)
    args = ap.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary_path)
    live_path = Path(f"{work_dir}.live.json")
    formed_path = Path(f"{work_dir}.formed.json")
    pid_path = work_dir / 'opensearch' / 'pid'
    report_path = work_dir / 'report.json'
    perf_data_path = work_dir / 'opensearch' / 'sudo-perf-record-futex.data'
    perf_script_path = work_dir / 'opensearch' / 'sudo-perf-record-futex.script.txt'

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
    futex_threads = []
    futex_event_count = 0
    try:
        if wait_for_file(pid_path, 90):
            pid = pid_path.read_text(encoding='utf-8').strip()
            perf_data_path.parent.mkdir(parents=True, exist_ok=True)
            record_cmd = [
                'timeout', f'{args.record_seconds}s',
                'sudo', 'perf', 'record', '-g',
                '-o', str(perf_data_path),
                '-e', 'syscalls:sys_enter_futex',
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
            seen = set()
            for line in script.stdout.splitlines():
                if EVENT_MARKER not in line:
                    continue
                futex_event_count += 1
                m = HEADER_RE.match(line)
                if not m:
                    continue
                key = (m.group('comm'), int(m.group('pid')), int(m.group('tid')))
                if key not in seen:
                    seen.add(key)
                    futex_threads.append({'comm': key[0], 'pid': key[1], 'tid': key[2]})
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
        'perf_data_path': str(perf_data_path),
        'perf_script_path': str(perf_script_path),
        'record_returncode': record_returncode,
        'script_returncode': script_returncode,
        'futex_event_count': futex_event_count,
        'futex_threads': futex_threads,
        'probe_returncode': probe_returncode,
        'report_membership_formed': None if report is None else report.get('membership_formed'),
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'report_observed_node_count': None if report is None else report.get('observed_node_count'),
        'checker_result': (
            'sudo_perf_record_futex_thread_identity_collected_on_failing_probe'
            if record_returncode == 0 and script_returncode == 0 and report is not None
            else 'sudo_perf_record_futex_thread_identity_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
