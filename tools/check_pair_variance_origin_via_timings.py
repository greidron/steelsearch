#!/usr/bin/env python3
import json
import math
import os
import re
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
TIMINGS_DIR = ROOT / "target/cargo-timings"
ROUNDS = 7
BUILD_CMD = [
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
UNIT_DATA_RE = re.compile(r"const\s+UNIT_DATA\s*=\s*(\[.*?\]);", re.S)


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def sign(value: float) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def run_timed_build() -> dict[str, float]:
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    t0 = time.time()
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    wall_ms = (time.time() - t0) * 1000
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))
    os_node_lib = next(unit for unit in unit_data if unit["name"] == "os-node" and unit["target"] == "")
    lib_ms = os_node_lib["duration"] * 1000
    return {
        "wall_ms": round(wall_ms, 2),
        "os_node_lib_ms": round(lib_ms, 2),
    }


def repeated_pairs() -> dict[str, object]:
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    pairs = []
    wall_deltas = []
    lib_deltas = []
    residual_deltas = []
    sign_match_count = 0
    for _ in range(ROUNDS):
        touch(LEAF)
        first = run_timed_build()
        touch(LEAF)
        second = run_timed_build()
        wall_delta = round(second["wall_ms"] - first["wall_ms"], 2)
        lib_delta = round(second["os_node_lib_ms"] - first["os_node_lib_ms"], 2)
        residual_delta = round(wall_delta - lib_delta, 2)
        if sign(wall_delta) == sign(lib_delta):
            sign_match_count += 1
        wall_deltas.append(wall_delta)
        lib_deltas.append(lib_delta)
        residual_deltas.append(residual_delta)
        pairs.append(
            {
                "first": first,
                "second": second,
                "wall_delta_ms": wall_delta,
                "os_node_lib_delta_ms": lib_delta,
                "residual_delta_ms": residual_delta,
                "sign_match": sign(wall_delta) == sign(lib_delta),
            }
        )
    return {
        "pairs": pairs,
        "sign_match_count": sign_match_count,
        "wall_delta_values_ms": wall_deltas,
        "os_node_lib_delta_values_ms": lib_deltas,
        "residual_delta_values_ms": residual_deltas,
        "wall_delta_range_ms": [min(wall_deltas), max(wall_deltas)],
        "os_node_lib_delta_range_ms": [min(lib_deltas), max(lib_deltas)],
        "residual_delta_range_ms": [min(residual_deltas), max(residual_deltas)],
        "wall_delta_stddev_ms": round(statistics.pstdev(wall_deltas), 2),
        "os_node_lib_delta_stddev_ms": round(statistics.pstdev(lib_deltas), 2),
        "residual_delta_stddev_ms": round(statistics.pstdev(residual_deltas), 2),
    }


def mode_profile(lib_text: str) -> dict[str, object]:
    LIB_RS.write_text(lib_text)
    return repeated_pairs()


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
        "result": "pair_variance_origin_profiled_by_comparing_wall_clock_and_os_node_lib_timing_deltas",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
