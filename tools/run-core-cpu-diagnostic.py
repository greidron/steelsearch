#!/usr/bin/env python3
"""Profile owned core-load processes; all resulting measurements are diagnostic."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from run_core_performance_gate import BASELINE_SHA256, command


ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_NODE_COUNTS = {"single-node": 1, "three-node": 3}
OPERATIONS = ("mixed", "write", "lexical", "ranking", "facet", "sort_filter", "nested", "refresh")


def verify_binary(binary, expected):
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("expected executable identity must be a lowercase SHA-256")
    with binary.open("rb") as stream:
        identity = hashlib.file_digest(stream, "sha256").hexdigest()
    if identity != expected:
        raise ValueError("diagnostic executable SHA-256 mismatch")
    return identity


def cpu_sample(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    return {"start_ticks": int(fields[19]), "user_ticks": int(fields[11]), "system_ticks": int(fields[12])}


def diagnostic_command(output, operation, topology="three-node"):
    if operation not in OPERATIONS:
        raise ValueError("unsupported diagnostic operation")
    if topology not in TOPOLOGY_NODE_COUNTS:
        raise ValueError("unsupported diagnostic topology")
    cmd = command("baseline", output / "matrix")
    cmd[cmd.index("--duration-seconds") + 1] = "45"
    cmd[cmd.index("--scenarios") + 1] = f"steelsearch-{topology}"
    if operation != "mixed":
        cmd[cmd.index("--query-mix") + 1] = f"{operation}=100"
    return cmd


def diagnostic_process_role(args, binary):
    if args and Path(args[0]).resolve() == binary:
        return "server"
    if any(Path(arg).name == "run-http-load-baseline.py" for arg in args):
        return "load-generator"
    return None


def validate_frequency(profile, frequency_hz):
    if type(frequency_hz) is not int or not 1 <= frequency_hz <= 2000:
        raise ValueError("CPU sampling frequency must be an integer from 1 to 2000 Hz")
    if profile != "cpu" and frequency_hz != 49:
        raise ValueError("custom CPU sampling frequency requires the cpu profile")


def profile_command(output, roles, profile, frequency_hz=49):
    validate_frequency(profile, frequency_hz)
    if profile == "cpu":
        events = ["-e", "cpu-clock", "-F", str(frequency_hz)]
        pids = list(roles)
    elif profile == "futex":
        events = ["-e", "syscalls:sys_enter_futex", "-c", "100"]
        pids = [pid for pid, role in roles.items() if role == "server"]
    else:
        raise ValueError("unsupported diagnostic profile")
    if not pids:
        raise ValueError("no owned profiling targets")
    return ["sudo", "-n", "perf", "record", *events,
            "--call-graph", "dwarf,8192", "-p", ",".join(map(str, pids)),
            "-o", str(output / "perf.data"), "--", "sleep", "20"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/release/steelsearch")
    parser.add_argument("--expected-sha256", default=BASELINE_SHA256)
    parser.add_argument("--operation", choices=OPERATIONS, default="mixed")
    parser.add_argument("--profile", choices=("cpu", "futex"), default="cpu")
    parser.add_argument("--cpu-frequency-hz", type=int, default=49,
                        help="CPU profile frequency, 1-2000 Hz; higher rates add profiling overhead")
    parser.add_argument("--topology", choices=tuple(TOPOLOGY_NODE_COUNTS), default="three-node")
    args = parser.parse_args()
    try:
        validate_frequency(args.profile, args.cpu_frequency_hz)
    except ValueError as error:
        parser.error(str(error))
    binary = args.binary.resolve(strict=True)
    identity = verify_binary(binary, args.expected_sha256)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("diagnostic_matrix", ROOT / "tools/run-search-benchmark-matrix.py")
    matrix = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = matrix
    spec.loader.exec_module(matrix)
    cmd = diagnostic_command(output, args.operation, args.topology)
    expected_servers = TOPOLOGY_NODE_COUNTS[args.topology]
    env = dict(os.environ, STEELSEARCH_BINARY_PATH=str(binary))
    result = {"diagnostic_only": True, "acceptance_established": False,
              "profile": args.profile,
              "cpu_frequency_hz": args.cpu_frequency_hz if args.profile == "cpu" else None,
              "profile_limitations": "Futex entries are sampled every 100 events and include waits and wakes, not blocked duration or HTTP latency attribution; CPU samples exclude off-CPU time; short-lived worker coverage and profiling overhead can vary with frequency, so percentages across frequencies are not speedup evidence.",
              "operation": args.operation,
              "topology": args.topology, "expected_servers": expected_servers,
              "binary_path": str(binary), "binary_sha256": identity, "command": cmd, "scope": "20-second diagnostic capture within a profiled 45-second run; not a performance gate"}
    (output / "plan.json").write_text(json.dumps(result, indent=2) + "\n")
    with (output / "matrix.log").open("x") as log:
        process = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 120
            roles = {}
            while time.monotonic() < deadline and process.poll() is None:
                roles = {}
                for pid in matrix.descendant_pids(process.pid):
                    role = diagnostic_process_role(matrix.process_cmdline(pid), binary)
                    if role is not None:
                        roles[pid] = role
                if list(roles.values()).count("server") == expected_servers and list(roles.values()).count("load-generator") == 1:
                    break
                time.sleep(0.25)
            else:
                raise ValueError("owned server/load process set not found")
            time.sleep(8)
            for pid, role in roles.items():
                if role == "server":
                    verify_binary(Path(f"/proc/{pid}/exe"), identity)
            started = time.monotonic()
            before = {pid: cpu_sample(pid) for pid in roles}
            perf_cmd = profile_command(output, roles, args.profile, args.cpu_frequency_hz)
            result["perf_command"] = perf_cmd
            with (output / "perf.log").open("x") as perf_log:
                recorded = subprocess.Popen(perf_cmd, stdout=perf_log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                try:
                    recorded.wait(timeout=35)
                finally:
                    if recorded.poll() is None:
                        # sudo may spawn a privileged child; terminate the owned session.
                        subprocess.run(["sudo", "-n", "kill", "-KILL", "--",
                                        f"-{recorded.pid}"], check=True, timeout=10)
                        recorded.wait(timeout=10)
            after = {pid: cpu_sample(pid) for pid in roles}
            elapsed = time.monotonic() - started
            ticks = os.sysconf("SC_CLK_TCK")
            samples = []
            for pid, role in roles.items():
                if before[pid]["start_ticks"] != after[pid]["start_ticks"]:
                    raise ValueError("observed process identity changed")
                samples.append({"pid": pid, "role": role, "before": before[pid], "after": after[pid],
                                "cpu_seconds": sum(after[pid][key] - before[pid][key] for key in ("user_ticks", "system_ticks")) / ticks})
            result.update(perf_command=perf_cmd, perf_returncode=recorded.returncode,
                          observation_seconds=elapsed, clock_ticks_per_second=ticks, processes=samples)
            result["matrix_returncode"] = process.wait(timeout=120)
            result["binary_sha256_after"] = verify_binary(binary, identity)
            summary = output / "matrix/summary.json"
            if summary.exists():
                report = json.loads(summary.read_text())
                report["diagnostic_only"] = True
                for name, scenario in report["scenarios"].items():
                    scenario["diagnostic_only"] = True
                    (output / "matrix" / name / "baseline.json").write_text(json.dumps(scenario, indent=2) + "\n")
                summary.write_text(json.dumps(report, indent=2) + "\n")
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            (output / "diagnostic.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result.get("matrix_returncode") == 0 and result.get("perf_returncode") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
