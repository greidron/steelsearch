#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
ROUNDS = 7
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


def classify(delta_ms: int) -> str:
    if delta_ms < 0:
        return "second_faster"
    if delta_ms > 0:
        return "second_slower"
    return "equal"


def pair_profile(cmd: list[str]) -> dict[str, int | str]:
    run_build_ms(cmd)
    touch(LEAF)
    first = run_build_ms(cmd)
    touch(LEAF)
    second = run_build_ms(cmd)
    delta = second - first
    return {
        "first_ms": first,
        "second_ms": second,
        "delta_second_minus_first_ms": delta,
        "sign": classify(delta),
    }


def repeated_pairs(cmd: list[str]) -> dict[str, object]:
    pairs = [pair_profile(cmd) for _ in range(ROUNDS)]
    sign_counts = {"second_faster": 0, "second_slower": 0, "equal": 0}
    deltas = []
    for pair in pairs:
        sign_counts[pair["sign"]] += 1
        deltas.append(pair["delta_second_minus_first_ms"])
    return {
        "pairs": pairs,
        "sign_counts": sign_counts,
        "delta_min_ms": min(deltas),
        "delta_max_ms": max(deltas),
        "delta_values_ms": deltas,
    }


def mode_profile(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    return {
        "plain": repeated_pairs(PLAIN_BUILD_CMD),
        "timings": repeated_pairs(TIMINGS_BUILD_CMD),
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
        "rounds": ROUNDS,
        "explicit_mode": explicit_mode,
        "star_mode": star_mode,
        "result": "second_run_sign_stability_profiled_for_plain_and_timings_builds",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
