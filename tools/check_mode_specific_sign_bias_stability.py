#!/usr/bin/env python3
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ubuntu/steelsearch")
LIB_RS = ROOT / "crates/os-node/src/lib.rs"
LEAF = ROOT / "crates/os-node/src/write_path_invariants.rs"
ROUNDS = 15
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


def classify(delta_ms: int) -> str:
    if delta_ms < 0:
        return "second_faster"
    if delta_ms > 0:
        return "second_slower"
    return "equal"


def binomial_two_sided_p_value(successes: int, trials: int) -> float:
    if trials == 0:
        return 1.0
    observed = math.comb(trials, successes) * (0.5 ** trials)
    total = 0.0
    for k in range(trials + 1):
        prob = math.comb(trials, k) * (0.5 ** trials)
        if prob <= observed + 1e-12:
            total += prob
    return min(total, 1.0)


def repeated_pairs() -> dict[str, object]:
    run_build_ms()
    pairs = []
    counts = {"second_faster": 0, "second_slower": 0, "equal": 0}
    deltas = []
    for _ in range(ROUNDS):
        touch(LEAF)
        first = run_build_ms()
        touch(LEAF)
        second = run_build_ms()
        delta = second - first
        sign = classify(delta)
        counts[sign] += 1
        deltas.append(delta)
        pairs.append(
            {
                "first_ms": first,
                "second_ms": second,
                "delta_second_minus_first_ms": delta,
                "sign": sign,
            }
        )

    informative_trials = counts["second_faster"] + counts["second_slower"]
    second_faster = counts["second_faster"]
    return {
        "pairs": pairs,
        "sign_counts": counts,
        "delta_min_ms": min(deltas),
        "delta_max_ms": max(deltas),
        "delta_values_ms": deltas,
        "informative_trials": informative_trials,
        "second_faster_share": round(second_faster / informative_trials, 3) if informative_trials else 0.0,
        "two_sided_binomial_p": round(
            binomial_two_sided_p_value(second_faster, informative_trials),
            6,
        ),
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
        "result": "mode_specific_second_run_sign_bias_tested_with_larger_plain_build_sample",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
