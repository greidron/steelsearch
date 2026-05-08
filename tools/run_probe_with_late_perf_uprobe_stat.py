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
LIBNIO = Path('/usr/lib/jvm/java-21-openjdk-arm64/lib/libnio.so')
SOCKET_EVENT = 'probe_libnio:ss_socket_read0'
UNIX_EVENT = 'probe_libnio:ss_unix_read0'


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


def ensure_probe(alias: str, symbol: str) -> None:
    subprocess.run(
        ['sudo', 'perf', 'probe', '-x', str(LIBNIO), '--add', f'{alias}={symbol}'],
        capture_output=True,
        text=True,
        check=False,
    )


def delete_probe(alias: str) -> None:
    subprocess.run(
        ['sudo', 'perf', 'probe', '--del', alias],
        capture_output=True,
        text=True,
        check=False,
    )


def parse_perf_stat_csv(text: str) -> dict:
    counts = {}
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3:
            continue
        value, _, event = parts[:3]
        if event not in (SOCKET_EVENT, UNIX_EVENT):
            continue
        try:
            counts[event] = int(float(value))
        except ValueError:
            pass
    return counts


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
    perf_stat_path = work_dir / 'opensearch' / 'late-perf-uprobe-stat.txt'

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

    ensure_probe('ss_socket_read0', 'Java_sun_nio_ch_SocketDispatcher_read0')
    ensure_probe('ss_unix_read0', 'Java_sun_nio_ch_UnixFileDispatcherImpl_read0')

    probe = subprocess.Popen(
        ['bash', str(PROBE)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    perf_rc = None
    perf_counts = {}
    perf_window_start_ms = None
    perf_window_end_ms = None
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
            perf_window_start_ms = int(time.time() * 1000)
            perf = subprocess.run(
                [
                    'sudo', 'perf', 'stat', '-x,',
                    '-e', f'{SOCKET_EVENT},{UNIX_EVENT}',
                    '-p', pid, 'sleep', str(args.record_seconds),
                ],
                capture_output=True,
                text=True,
                timeout=args.record_seconds + 30,
            )
            perf_window_end_ms = int(time.time() * 1000)
            perf_rc = perf.returncode
            perf_stat_path.write_text((perf.stdout or '') + (perf.stderr or ''), encoding='utf-8')
            perf_counts = parse_perf_stat_csv((perf.stdout or '') + '\n' + (perf.stderr or ''))
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
    finally:
        delete_probe('ss_socket_read0')
        delete_probe('ss_unix_read0')

    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else None
    summary = {
        'work_dir': str(work_dir),
        'libnio': str(LIBNIO),
        'perf_stat_path': str(perf_stat_path),
        'perf_returncode': perf_rc,
        'perf_counts': perf_counts,
        'perf_window_start_ms': perf_window_start_ms,
        'perf_window_end_ms': perf_window_end_ms,
        'http_ready_before_record': http_ready,
        'late_start_after_http_ready_seconds': args.late_start_after_http_ready_seconds,
        'record_seconds': args.record_seconds,
        'probe_returncode': probe_returncode,
        'report_failure_stage': None if report is None else report.get('failure_stage'),
        'checker_result': (
            'late_perf_uprobe_stat_collected_on_failing_probe'
            if perf_rc == 0 and report is not None and perf_stat_path.exists()
            else 'late_perf_uprobe_stat_collection_incomplete'
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
