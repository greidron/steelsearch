#!/usr/bin/env python3
"""Run every repository promotion gate checker as one fail-closed suite."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("source-compatibility-drift", ["tools/check-source-compatibility-drift.sh"]),
    ("root-identity", ["tools/check-root-identity-promotion-gate.py"]),
    ("index-metadata", ["tools/check-index-metadata-promotion-gate.py"]),
    ("document-write", ["tools/check-document-write-promotion-gate.py"]),
    ("bulk", ["tools/check-bulk-promotion-gate.py"]),
    ("cluster-admin", ["tools/check-cluster-admin-promotion-gate.py"]),
    ("search", ["tools/check-search-promotion-gate.py"]),
    (
        "pit-e2e-coverage",
        [
            "tools/check-pit-e2e-coverage.py",
            "target/unified-opensearch-e2e-pit-current/unified-opensearch-e2e-report.json",
            "--max-report-age-seconds",
            "604800",
            "--require-all-pit-passed",
        ],
    ),
    ("snapshot", ["tools/check-snapshot-promotion-gate.py"]),
    ("vector", ["tools/check-vector-promotion-gate.py"]),
    ("knn-plugin", ["tools/check-knn-plugin-promotion-gate.py"]),
    ("ml", ["tools/check-ml-promotion-gate.py"]),
    ("peer-node", ["tools/check-peer-node-promotion-gate.py"]),
    (
        "security-row-reclassification",
        [
            "tools/check-security-row-reclassification-gate.py",
            "tools/fixtures/security-row-reclassification-gate.json",
        ],
    ),
    (
        "transport-action-coverage",
        [
            "tools/report-transport-action-coverage.py",
            "--require-peer-backpressure",
            "--output",
            "target/transport-action-coverage-current-check.json",
        ],
    ),
    (
        "rest-api-live-source-coverage",
        [
            "tools/report-rest-api-coverage.py",
            "--unified-report",
            "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json",
            "--max-report-age-seconds",
            "604800",
            "--require-live-required-suites",
            "--min-live-required-matched-source-route-count",
            "378",
            "--min-live-required-matched-source-route-ratio",
            "1.0",
            "--output",
            "target/rest-api-coverage-current-check.json",
        ],
    ),
    (
        "mixed-cluster-coverage",
        [
            "tools/report-mixed-cluster-coverage.py",
            "--require-passed",
            "--output",
            "target/mixed-cluster-coverage-current-check.json",
        ],
    ),
    (
        "external-interop",
        [
            "tools/check-external-interop-promotion-gate.py",
            "tools/fixtures/external-interop-promotion-gate.json",
        ],
    ),
    (
        "migration",
        [
            "tools/check-migration-promotion-gate.py",
            "tools/fixtures/migration-promotion-gate.json",
        ],
    ),
    (
        "harness",
        [
            "tools/check-harness-promotion-gate.py",
            "tools/fixtures/harness-promotion-gate.json",
        ],
    ),
]


def tail(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def run_check(name: str, command: list[str]) -> dict[str, object]:
    executable = [sys.executable, *command] if command[0].endswith(".py") else command
    proc = subprocess.run(
        executable,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result: dict[str, object] = {
        "name": name,
        "command": " ".join(command),
        "status": "ok" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
    }
    if proc.returncode != 0:
        result["stdout_tail"] = tail(proc.stdout)
        result["stderr_tail"] = tail(proc.stderr)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the suite summary JSON to this path.")
    args = parser.parse_args()

    results = [run_check(name, command) for name, command in CHECKS]
    failed = [result for result in results if result["status"] != "ok"]
    summary = {
        "status": "failed" if failed else "ok",
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "checks": results,
    }
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
