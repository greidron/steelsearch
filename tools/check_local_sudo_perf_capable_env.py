#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main() -> int:
    sudo_probe = run(["sudo", "-n", "true"])
    perf_probe = run(["sudo", "perf", "stat", "-e", "raw_syscalls:sys_enter", "true"])
    result = {
        "sudo_non_interactive_available": sudo_probe.returncode == 0,
        "sudo_probe_exit_code": sudo_probe.returncode,
        "strace_path": shutil.which("strace"),
        "perf_raw_syscalls_via_sudo_available": perf_probe.returncode == 0,
        "perf_probe_exit_code": perf_probe.returncode,
        "perf_probe_stderr": perf_probe.stderr.strip(),
    }
    result["checker_result"] = (
        "local_sudo_perf_raw_syscalls_capable_environment_is_available_for_read_starvation_branch"
        if result["sudo_non_interactive_available"] and result["perf_raw_syscalls_via_sudo_available"]
        else "local_sudo_perf_raw_syscalls_capable_environment_is_not_available_for_read_starvation_branch"
    )
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
