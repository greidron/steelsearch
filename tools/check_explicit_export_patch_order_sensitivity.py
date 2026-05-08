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
ROUNDS = 3


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


def benchmark_mode(lib_text: str) -> list[int]:
    LIB_RS.write_text(lib_text)
    run_build_ms()
    samples = []
    for _ in range(ROUNDS):
        touch(LEAF)
        samples.append(run_build_ms())
    return samples


def summarize(samples: list[int]) -> dict[str, object]:
    return {
        "samples_ms": samples,
        "median_ms": int(statistics.median(samples)),
        "mean_ms": round(statistics.mean(samples), 2),
    }


def run_order(first_name: str, first_text: str, second_name: str, second_text: str) -> dict[str, object]:
    first = summarize(benchmark_mode(first_text))
    second = summarize(benchmark_mode(second_text))
    return {
        "order": f"{first_name}_then_{second_name}",
        first_name: first,
        second_name: second,
        "median_delta_ms": second["median_ms"] - first["median_ms"],
        "mean_delta_ms": round(second["mean_ms"] - first["mean_ms"], 2),
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
        star_then_explicit = run_order("star", star, "explicit", explicit)
        explicit_then_star = run_order("explicit", explicit, "star", star)
    finally:
        LIB_RS.write_text(explicit)

    result = {
        "rounds": ROUNDS,
        "star_then_explicit": star_then_explicit,
        "explicit_then_star": explicit_then_star,
        "result": "explicit_export_patch_order_sensitivity_benchmarked",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
