#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
BUILD_CMD = [
    "cargo",
    "build",
    "-vv",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
    "--bin",
    "steelsearch",
    "--manifest-path",
    str(ROOT / "Cargo.toml"),
]
EXTERN_RE = re.compile(r"--extern\s+os_node=([^\s]+)")


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    cp = subprocess.run(
        BUILD_CMD,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )

    steelsearch_lines = [
        line for line in cp.stdout.splitlines()
        if "rustc" in line and "CARGO_BIN_NAME=steelsearch" in line
    ]
    if not steelsearch_lines:
        raise SystemExit("steelsearch rustc line not found")
    rustc_line = steelsearch_lines[-1]
    match = EXTERN_RE.search(rustc_line)
    if not match:
        raise SystemExit("--extern os_node not found in steelsearch rustc line")
    extern_path = match.group(1)

    result = {
        "steelsearch_rustc_line": rustc_line,
        "os_node_extern_path": extern_path,
        "extern_uses_rlib": extern_path.endswith(".rlib"),
        "extern_uses_rmeta": extern_path.endswith(".rmeta"),
        "result": "steelsearch_bin_uses_os_node_rlib_dependency_path_in_verbose_rustc_invocation",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
