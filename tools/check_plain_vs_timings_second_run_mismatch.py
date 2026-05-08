#!/usr/bin/env python3
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
PLAIN_BUILD_CMD = [
    "cargo",
    "build",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
    "--bin",
    "steelsearch",
    "--manifest-path",
    str(ROOT / "Cargo.toml"),
]
TIMINGS_BUILD_CMD = [
    "cargo",
    "build",
    "--timings",
    "-p",
    "os-node",
    "--features",
    "standalone-runtime",
    "--bin",
    "steelsearch",
    "--manifest-path",
    str(ROOT / "Cargo.toml"),
]


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_build_ms(cmd: list[str]) -> int:
    t0 = time.time()
    cp = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def pair_profile(cmd: list[str]) -> dict[str, object]:
    run_build_ms(cmd)
    touch(LEAF)
    first = run_build_ms(cmd)
    touch(LEAF)
    second = run_build_ms(cmd)
    return {
        "first_ms": first,
        "second_ms": second,
        "delta_second_minus_first_ms": second - first,
    }


def mode_profile(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    plain = pair_profile(PLAIN_BUILD_CMD)
    timings = pair_profile(TIMINGS_BUILD_CMD)
    return {
        "plain": plain,
        "timings": timings,
        "plain_vs_timings_delta_ms": {
            "first_ms": timings["first_ms"] - plain["first_ms"],
            "second_ms": timings["second_ms"] - plain["second_ms"],
            "delta_second_minus_first_ms": (
                timings["delta_second_minus_first_ms"] - plain["delta_second_minus_first_ms"]
            ),
        },
    }


def main() -> int:
    explicit = LIB_RS.read_text()
    star = re.sub(
        r"pub use standalone_runtime::\{.*?\n\};",
        "pub use standalone_runtime::*;",
        explicit,
        flags=re.S,
    )
    if star == explicit:
        raise SystemExit("explicit export block not found")

    try:
        explicit_mode = mode_profile(explicit)
        star_mode = mode_profile(star)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "explicit_mode": explicit_mode,
        "star_mode": star_mode,
        "result": "plain_vs_timings_second_run_wall_clock_mismatch_profiled",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
