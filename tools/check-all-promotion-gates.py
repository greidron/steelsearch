#!/usr/bin/env python3
"""Run every repository promotion gate checker as one fail-closed suite."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTION_GATE_OUTPUT = REPO_ROOT / "target/promotion-gate-suite-current.json"
RELEASE_EVIDENCE_CHECK_NAME = "release-evidence-inventory"
COMPATIBILITY_PROFILES = ("legacy-full", "core-no-plugins")
PLUGIN_CHECKS = frozenset({"vector", "knn-plugin", "ml"})

CHECKS = [
    ("source-compatibility-drift", ["tools/check-source-compatibility-drift.sh"]),
    (
        "source-compatibility-closure",
        [
            "tools/run-native-closure-validation.py",
            "--batch",
            "source-compatibility-current",
            "--format",
            "json",
        ],
    ),
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
    (
        "ml",
        [
            "tools/check-ml-promotion-gate.py",
            "--report",
            "target/unified-opensearch-e2e-ml-closed-current/ml-model-surface-compat-report.json",
            "--report",
            "target/unified-opensearch-e2e-broad-current/security-authz-compat-report.json",
        ],
    ),
    (
        "benchmark-evidence",
        [
            "tools/check-benchmark-evidence.py",
            "--jsonl",
            "target/release-benchmarks/deterministic-benchmark-baselines.jsonl",
            "--report",
            "target/release-benchmarks/benchmark-report.json",
            "--comparison-summary",
            "target/search-benchmark-matrix-current-20260630T023334Z/summary.json",
            "--max-age-seconds",
            "604800",
        ],
    ),
    (
        "peer-node",
        [
            "tools/check-peer-node-promotion-gate.py",
            "--max-report-age-seconds",
            "604800",
        ],
    ),
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
            "--require-release-parity",
            "--require-closed-action-statuses",
            "--max-report-age-seconds",
            "604800",
            "--output",
            "target/transport-action-coverage-current-check.json",
        ],
    ),
    (
        "broad-unified-e2e-sections",
        [
            "tools/check-unified-opensearch-e2e-report.py",
            "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json",
            "--max-report-age-seconds",
            "604800",
            "--require-no-unresolved-skips",
            "--require-section",
            "route_parity",
            "--require-section",
            "semantic_parity",
            "--require-section",
            "durability_parity",
            "--require-section",
            "security_parity",
            "--require-section",
            "distributed_parity",
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
            "379",
            "--min-live-required-matched-source-route-ratio",
            "1.0",
            "--min-source-route-count",
            "389",
            "--require-closed-source-statuses",
            "--output",
            "target/rest-api-coverage-current-check.json",
        ],
    ),
    ("e2e-doc-current-counts", ["tools/check-e2e-doc-current-counts.py"]),
    (
        "runtime-control-surface-inventory",
        ["tools/check-current-runtime-control-surface-inventory.py"],
    ),
    (
        "mixed-cluster-coverage",
        [
            "tools/report-mixed-cluster-coverage.py",
            "--require-passed",
            "--max-report-age-seconds",
            "604800",
            "--shard-movement-report",
            "target/three-node-shard-movement-interruption-current/report.json",
            "--output",
            "target/mixed-cluster-coverage-current-check.json",
        ],
    ),
    (
        "release-evidence-inventory",
        [
            "tools/report-release-evidence-inventory.py",
            "--root",
            "target",
            "--max-age-seconds",
            "604800",
            "--require-complete",
            "--output",
            "target/release-evidence-inventory-current-check.json",
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


def checks_for_profile(profile: str) -> tuple[list, list]:
    if profile not in COMPATIBILITY_PROFILES:
        raise ValueError(f"unknown compatibility profile: {profile}")
    checks, excluded = [], []
    for name, command in CHECKS:
        if profile == "core-no-plugins" and name in PLUGIN_CHECKS:
            excluded.append({"name": name, "command": " ".join(command), "status": "excluded",
                             "reason": "OpenSearch plugins are outside core-no-plugins scope"})
        else:
            if profile == "core-no-plugins" and name == "broad-unified-e2e-sections":
                command = [*command, "--compatibility-profile", profile]
                command[1] = "target/unified-opensearch-e2e-core-current/unified-opensearch-e2e-report.json"
            checks.append((name, command))
    if not checks:
        raise ValueError("profile must retain required non-plugin checks")
    return checks, excluded


def suite_summary(results: list[dict[str, object]], profile: str = "legacy-full") -> dict[str, object]:
    if profile not in COMPATIBILITY_PROFILES:
        raise ValueError(f"unknown compatibility profile: {profile}")
    excluded = [result for result in results if result["status"] == "excluded"
                and profile == "core-no-plugins" and result["name"] in PLUGIN_CHECKS]
    failed = [result for result in results if result["status"] not in ("ok", "excluded")
              or (result["status"] == "excluded" and
                  (profile != "core-no-plugins" or result["name"] not in PLUGIN_CHECKS))]
    passed = [result for result in results if result["status"] == "ok"]
    errors = []
    if not passed:
        errors.append("no passing required checks")
    if profile == "core-no-plugins":
        names = [result["name"] for result in results]
        expected = {name for name, _ in CHECKS}
        missing = expected - {RELEASE_EVIDENCE_CHECK_NAME} - set(names)
        if missing:
            errors.append(f"missing required checks: {sorted(missing)}")
        if len(names) != len(set(names)):
            errors.append("duplicate checks")
        if set(names) - expected:
            errors.append("unknown checks")
    return {
        "status": "failed" if failed or errors else "ok",
        "compatibility_profile": profile,
        "passed": len(passed),
        "failed": len(failed),
        "excluded": len(excluded),
        "validation_errors": errors,
        "checks": results,
    }


def write_summary(path: Path, summary: dict[str, object]) -> str:
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write the suite summary JSON to this path.")
    parser.add_argument("--compatibility-profile", choices=COMPATIBILITY_PROFILES, default="legacy-full")
    args = parser.parse_args()

    profile = args.compatibility_profile
    default_output = (DEFAULT_PROMOTION_GATE_OUTPUT if profile == "legacy-full" else
                      REPO_ROOT / "target/core-no-plugins-promotion-gate-suite-current.json")
    output = args.output or default_output
    if profile == "core-no-plugins" and output.resolve() == DEFAULT_PROMOTION_GATE_OUTPUT.resolve():
        parser.error("core profile must not overwrite the legacy full-profile summary")
    selected, excluded = checks_for_profile(profile)
    release_check = next(
        ((name, command) for name, command in selected if name == RELEASE_EVIDENCE_CHECK_NAME),
        None,
    )
    if profile == "core-no-plugins" and release_check is not None:
        name, command = release_check
        command = [*command, "--compatibility-profile", profile, "--promotion-gate-suite", str(output.resolve())]
        command[command.index("--output") + 1] = str(REPO_ROOT / "target/core-no-plugins-release-evidence-inventory-current-check.json")
        release_check = (name, command)
    regular_checks = [
        (name, command) for name, command in selected if name != RELEASE_EVIDENCE_CHECK_NAME
    ]

    results = [run_check(name, command) for name, command in regular_checks] + excluded
    pre_release_summary = suite_summary(results, profile)
    write_summary(output, pre_release_summary)
    if output.resolve() != default_output.resolve():
        write_summary(default_output, pre_release_summary)

    if release_check is not None:
        results.append(run_check(*release_check))

    summary = suite_summary(results, profile)
    rendered = write_summary(output, summary)
    if output.resolve() != default_output.resolve():
        write_summary(default_output, summary)
    print(rendered, end="")
    return 1 if summary["status"] != "ok" else 0


if __name__ == "__main__":
    raise SystemExit(main())
