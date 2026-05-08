#!/usr/bin/env python3
import json
from pathlib import Path
import re
import subprocess

FIXTURE_ROOT = Path("/home/ubuntu/steelsearch/tmp/rmeta_fixture")
TIMINGS_DIR = FIXTURE_ROOT / "target/cargo-timings"
CHECK_CMD = [
    "cargo",
    "check",
    "--timings",
    "--workspace",
    "--manifest-path",
    str(FIXTURE_ROOT / "Cargo.toml"),
]
UNIT_DATA_RE = re.compile(r"const\s+UNIT_DATA\s*=\s*(\[.*?\]);", re.S)


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob("cargo-timing-*.html"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def main() -> int:
    before = set(TIMINGS_DIR.glob("cargo-timing-*.html")) if TIMINGS_DIR.exists() else set()
    subprocess.run(CHECK_CMD, cwd=FIXTURE_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    unit_data = json.loads(UNIT_DATA_RE.search(html.read_text()).group(1))

    producer_units = [
        {
            "name": unit["name"],
            "target": unit["target"],
            "unlocked_rmeta_units": unit.get("unlocked_rmeta_units", []),
            "unlocked_units": unit.get("unlocked_units", []),
        }
        for unit in unit_data
        if unit["name"] == "producer"
    ]
    result = {
        "unit_count": len(unit_data),
        "producer_units": producer_units,
        "producer_with_unlocked_rmeta_count": sum(1 for unit in producer_units if unit["unlocked_rmeta_units"]),
        "result": "minimal_fixture_scanned_for_producer_unlocked_rmeta_units",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
