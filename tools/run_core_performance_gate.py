"""Run a predeclared repeated core benchmark; never grants implementation acceptance."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from core_performance_reports import (
    BASELINE_SHA256, REFERENCE_IMAGE, evaluate_reports, load_report, validate_report,
)
from core_performance_budget import compare_metrics


ROOT = Path(__file__).resolve().parents[1]
ORDER = ("baseline", "candidate", "opensearch", "opensearch", "candidate", "baseline")
QUERY_MIX = "write=15,lexical=15,ranking=15,facet=15,sort_filter=10,nested=10,refresh=5"
PUBLISHED_REPORT = "docs/releases/v0.6.0/current.json"
PUBLISHED_REPORT_SHA256 = "d2fdabfa447830f91b320aaebd734e01606deb70219e71b53d10c9281538c788"
EXECUTION_FILES = (
    "tools/run_core_performance_gate.py", "tools/run-search-benchmark-matrix.py",
    "tools/run-http-load-baseline.py", "tools/run-steelsearch-dev.sh",
    "tools/run-steelsearch-cluster-dev.sh", "tools/run-opensearch-vector-dev.sh",
    "tools/run-opensearch-cluster-dev.sh", "tools/benchmark_runtime_evidence.py",
    "tools/benchmark_cgroup_evidence.py", "tools/core_performance_reports.py",
    "tools/benchmark_timeline.py",
    "tools/core_performance_budget.py", "tools/release_notes.py", PUBLISHED_REPORT,
)


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def execution_fingerprint():
    _, origin = load_report(ROOT / PUBLISHED_REPORT)
    if origin["sha256"] != PUBLISHED_REPORT_SHA256:
        raise ValueError("published v0.6.0 report changed")
    return {name: file_hash(ROOT / name) for name in EXECUTION_FILES}


def verify_execution_inputs(expected, plan_path, plan_sha256):
    if file_hash(plan_path) != plan_sha256:
        raise ValueError("predeclared benchmark plan changed")
    if execution_fingerprint() != expected:
        raise ValueError("benchmark execution inputs changed")


def command(role, output):
    engine = "opensearch" if role == "opensearch" else "steelsearch"
    return [sys.executable, str(ROOT / "tools/run-search-benchmark-matrix.py"),
            "--capture-runtime-evidence", "--reuse-steelsearch-binary",
            "--profile", "minilm-knn", "--corpus-size", "5000", "--vector-dimension", "384",
            "--duration-seconds", "60", "--clients", "4", "--number-of-shards", "3",
            "--number-of-replicas", "1", "--timeout-seconds", "10", "--seed", "13",
            "--query-mix", QUERY_MIX, "--scenarios", f"{engine}-single-node,{engine}-three-node",
            "--output-dir", str(output)]


def assess(reports, candidate_sha):
    if len(reports) != len(ORDER):
        raise ValueError("all six planned runs required")
    published, origin = load_report(ROOT / "docs/releases/v0.6.0/current.json")
    published_metrics, _, _ = validate_report(published, "steelsearch", BASELINE_SHA256)
    checks = []
    for indices in ((0, 1, 2), (5, 4, 3)):
        baseline, candidate, reference = (reports[index] for index in indices)
        for report in (baseline, candidate, reference):
            for scenario in report["scenarios"].values():
                if "runtime_evidence" not in scenario:
                    raise ValueError("fresh runtime evidence required for every run")
        paired = evaluate_reports(baseline, candidate, reference, candidate_sha)
        original = evaluate_reports(published, candidate, reference, candidate_sha)
        fresh_metrics, _, _ = validate_report(baseline, "steelsearch", BASELINE_SHA256)
        checks.append({"run_indices": list(indices), "paired": paired, "published": original,
                       "baseline_drift": compare_metrics(published_metrics, fresh_metrics)})
    return {"acceptance_established": False,
            "scope": "repeated numeric and artifact checks; source build and effective runtime enforcement unverified",
            "numeric_budget_passed": all(check[kind]["numeric_budget_passed"]
                                         for check in checks for kind in ("paired", "published", "baseline_drift")),
            "published_baseline": origin, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-binary", type=Path, required=True)
    parser.add_argument("--candidate-binary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true",
                        help="write a predeclared run directory without executing load")
    args = parser.parse_args()
    binaries = {role: path.resolve(strict=True) for role, path in
                (("baseline", args.baseline_binary), ("candidate", args.candidate_binary))}
    hashes = {role: file_hash(path) for role, path in binaries.items()}
    if hashes["baseline"] != BASELINE_SHA256:
        parser.error("baseline executable must match the initial v0.6.0 SHA-256")
    fingerprint = execution_fingerprint()
    output = args.output_dir.resolve()
    # A run directory is never reused, including after infrastructure failure.
    output.mkdir(parents=True, exist_ok=False)
    jobs = [{"role": role, "command": command(role, output / f"{index:02d}-{role}")}
            for index, role in enumerate(ORDER)]
    plan = {"created_at_epoch": time.time(), "order": list(ORDER), "jobs": jobs,
            "binaries": {role: {"path": str(path), "sha256": hashes[role]} for role, path in binaries.items()},
            "host": {"node": platform.node(), "machine": platform.machine(), "platform": platform.platform()},
            "runner_sha256": file_hash(Path(__file__)),
            "matrix_sha256": file_hash(ROOT / "tools/run-search-benchmark-matrix.py"),
            "execution_files": fingerprint,
            "opensearch_image": "opensearchproject/opensearch@" + REFERENCE_IMAGE,
            "java_opts": "-Xms512m -Xmx512m", "prepare_only": args.prepare_only,
            "policy": {"repetitions": 2, "numeric_check": "every run against published and paired v0.6.0; baseline drift also checked",
                       "percentiles": "individual run values only; no pooling or averaging",
                       "retry": "none; retain all results; infrastructure failure stops the run",
                       "numeric_failure": "finish all planned measurements, then fail",
                       "acceptance_established": False}}
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    if args.prepare_only:
        print(f"Prepared only: {output / 'plan.json'}; no benchmark executed")
        return 0
    result = {"acceptance_established": False, "numeric_budget_passed": False, "runs": [],
              "execution_inputs_verified": False,
              "plan_sha256": file_hash(output / "plan.json")}
    try:
        reports = []
        for index, job in enumerate(jobs):
            role = job["role"]
            verify_execution_inputs(fingerprint, output / "plan.json", result["plan_sha256"])
            if any(file_hash(path) != hashes[name] for name, path in binaries.items()):
                raise ValueError("selected binary changed after plan creation")
            env = os.environ.copy()
            env.update(OPENSEARCH_VECTOR_DOCKER_IMAGE=plan["opensearch_image"],
                       OPENSEARCH_JAVA_OPTS=plan["java_opts"])
            if role != "opensearch":
                env["STEELSEARCH_BINARY_PATH"] = str(binaries[role])
            started = time.time()
            print(f"Starting {index + 1}/{len(jobs)}: {role}", flush=True)
            with (output / f"{index:02d}-{role}.log").open("x") as log:
                completed = subprocess.run(job["command"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            record = {"index": index, "role": role, "started_at_epoch": started,
                      "finished_at_epoch": time.time(), "returncode": completed.returncode}
            result["runs"].append(record)
            if completed.returncode != 0:
                raise ValueError(f"planned run {index} failed with exit {completed.returncode}")
            verify_execution_inputs(fingerprint, output / "plan.json", result["plan_sha256"])
            if any(file_hash(path) != hashes[name] for name, path in binaries.items()):
                raise ValueError("selected binary changed during execution")
            report, origin = load_report(output / f"{index:02d}-{role}" / "summary.json")
            record["report"] = origin
            reports.append(report)
            (output / "progress.json").write_text(json.dumps(result, indent=2) + "\n")
        assessment = assess(reports, hashes["candidate"])
        verify_execution_inputs(fingerprint, output / "plan.json", result["plan_sha256"])
        result.update(assessment)
        result["execution_inputs_verified"] = True
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        result["error"] = str(error)
        code = 2
    else:
        code = 0 if result["numeric_budget_passed"] else 1
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Result: {output / 'result.json'}; exit={code}; implementation acceptance=false")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
