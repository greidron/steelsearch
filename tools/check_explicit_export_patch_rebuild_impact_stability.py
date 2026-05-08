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
BUILD_CMD = [
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
ROUNDS = 9


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_build_ms() -> int:
    t0 = time.time()
    cp = subprocess.run(
        BUILD_CMD,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def summarize(samples: list[int]) -> dict[str, float | int | list[int]]:
    ordered = sorted(samples)
    return {
        "samples_ms": samples,
        "sorted_samples_ms": ordered,
        "min_ms": min(samples),
        "max_ms": max(samples),
        "median_ms": int(statistics.median(samples)),
        "mean_ms": round(statistics.mean(samples), 2),
    }


def benchmark_mode(lib_text: str) -> dict[str, float | int | list[int]]:
    LIB_RS.write_text(lib_text)
    run_build_ms()
    samples = []
    for _ in range(ROUNDS):
        touch(LEAF)
        samples.append(run_build_ms())
    return summarize(samples)


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
        star_summary = benchmark_mode(star)
        explicit_summary = benchmark_mode(explicit)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "rounds": ROUNDS,
        "star": star_summary,
        "explicit": explicit_summary,
        "median_delta_ms": explicit_summary["median_ms"] - star_summary["median_ms"],
        "mean_delta_ms": round(explicit_summary["mean_ms"] - star_summary["mean_ms"], 2),
        "result": "explicit_export_patch_rebuild_impact_stability_benchmarked_against_star_reexport",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
