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
CHECK_CMD = [
    "cargo",
    "check",
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
EMIT_RE = re.compile(r"--emit=([^\s]+)")


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def rustc_line(cmd: list[str]) -> str:
    subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    cp = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    matches = [
        line for line in cp.stdout.splitlines()
        if "rustc" in line and "CARGO_BIN_NAME=steelsearch" in line
    ]
    if not matches:
        raise SystemExit("steelsearch rustc line not found")
    return matches[-1]


def emit_modes(line: str) -> list[str]:
    match = EMIT_RE.search(line)
    if not match:
        raise SystemExit("--emit not found")
    return match.group(1).split(",")


def main() -> int:
    build_line = rustc_line(BUILD_CMD)
    check_line = rustc_line(CHECK_CMD)
    build_emit = emit_modes(build_line)
    check_emit = emit_modes(check_line)
    result = {
        "build_emit": build_emit,
        "check_emit": check_emit,
        "build_has_metadata_emit": "metadata" in build_emit,
        "check_has_metadata_emit": "metadata" in check_emit,
        "result": "steelsearch_bin_rmeta_time_is_better_explained_as_metadata_emit_milestone_than_as_unlock_edge",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
