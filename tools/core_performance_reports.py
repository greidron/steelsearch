"""Validate core matrix artifacts before calculating the v0.6.0 budget.

Artifact consistency is not proof of runtime settings or a fresh full-suite run.
The runner must supply that evidence separately before implementation acceptance.
"""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from core_performance_budget import compare_metrics, measurement
from release_notes import OPERATIONS, TOPOLOGIES, count, query_weights, require


BASELINE_SHA256 = "db2441338521dfe3e7c345000886b5154f851f89ff22fb4f4dcb5af8bf7f1f57"
REFERENCE_VERSION = "2.19.0"
REFERENCE_IMAGE = "sha256:1f8b88245a6af61e7aa500afe0e87d43401e4b33140bb47230a919428ce3f7cb"
CONFIG_FIELDS = (
    "corpus_size", "vector_dimension", "vector_source", "vector_space_type",
    "duration_seconds", "clients", "number_of_shards", "number_of_replicas",
    "seed", "operation_resource_deltas",
)


def digest(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            f"{label}: SHA-256 required")
    return value


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_report(path):
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=no_duplicates)
    require(isinstance(value, dict), f"{path}: expected object")
    return value, {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}


def zero(value, label):
    require(type(value) in (int, float) and value == 0, f"{label}: zero errors required")


def validate_runtime(evidence, engine, nodes, expected_identity):
    require(isinstance(evidence, dict), "runtime evidence object required")
    snapshots = []
    times = []
    for phase in ("before", "after"):
        snapshot = evidence[phase]
        require(isinstance(snapshot, dict), "runtime snapshot object required")
        require(snapshot["engine"] == engine, "runtime engine mismatch")
        times.append(measurement(snapshot["captured_at_epoch"], "runtime timestamp"))
        observed = snapshot["nodes"]
        require(isinstance(observed, list) and len(observed) == nodes, "runtime node count differs")
        identities = set()
        pids = set()
        for node in observed:
            require(isinstance(node, dict), "runtime node object required")
            pid = count(node["pid"], "runtime pid")
            require(pid not in pids, "duplicate runtime pid")
            pids.add(pid)
            if engine == "steelsearch":
                count(node["start_ticks"], "runtime start ticks")
                require(digest(node["sha256"], "runtime executable") == expected_identity,
                        "runtime executable mismatch")
            else:
                identity = digest(node["id"], "runtime container")
                require(identity not in identities, "duplicate runtime container")
                identities.add(identity)
                require(node["image_id"] == REFERENCE_IMAGE, "runtime reference image mismatch")
        snapshots.append(observed)
    require(times[1] >= times[0], "runtime timestamps reversed")
    require(snapshots[0] == snapshots[1], "runtime identity or settings changed")


def validate_report(report, engine, expected_identity):
    require(isinstance(report, dict), "report object required")
    require(not report.get("diagnostic_only", False), "diagnostic report rejected")
    config = report["config"]
    require(isinstance(config, dict), "config object required")
    require(config.get("diagnostic_timeline", False) is False and "timeline" not in report,
            "diagnostic timeline rejected")
    normalized = {key: config[key] for key in CONFIG_FIELDS}
    for key in ("corpus_size", "vector_dimension", "clients", "number_of_shards"):
        count(normalized[key], key)
    measurement(normalized["duration_seconds"], "duration_seconds")
    require(type(normalized["seed"]) is int, "integer seed required")
    replicas = normalized["number_of_replicas"]
    require(type(replicas) is int and replicas >= 0, "invalid replicas")
    require(type(normalized["operation_resource_deltas"]) is bool, "invalid resource sampling mode")
    for key in ("vector_source", "vector_space_type"):
        require(isinstance(normalized[key], str) and normalized[key], f"invalid {key}")
    normalized["timeout_seconds"] = str(measurement(config["timeout_seconds"], "timeout_seconds"))
    weights = query_weights(config["query_mix"])
    require(set(weights) == set(OPERATIONS), "all seven core operations required; no plugins")
    normalized["query_mix"] = weights
    scenarios = report["scenarios"]
    require(isinstance(scenarios, dict), "scenarios object required")
    require(set(scenarios) == {f"{engine}-{topology}" for topology in TOPOLOGIES},
            "exactly both expected topologies required")
    metrics = {}
    executed_configs = {}
    for topology in TOPOLOGIES:
        scenario = scenarios[f"{engine}-{topology}"]
        require(isinstance(scenario, dict), "scenario object required")
        require(not scenario.get("diagnostic_only", False), "diagnostic scenario rejected")
        returncode = scenario.get("load_runner_returncode", 0)
        require(type(returncode) is int and returncode == 0,
                "load runner did not complete successfully")
        require(not scenario.get("load_runner_error_output"), "load runner error output present")
        executed = scenario["config"]
        require(isinstance(executed, dict), "executed config object required")
        require(executed.get("diagnostic_timeline", False) is False and "timeline" not in scenario,
                "diagnostic timeline rejected")
        for key in CONFIG_FIELDS:
            expected = normalized[key]
            if key == "number_of_replicas":
                expected = 0 if topology == "single-node" else min(replicas, 2)
            require(type(executed[key]) is type(expected) and executed[key] == expected,
                    f"{topology}: executed {key} differs")
        require(query_weights(executed["query_mix"]) == weights, "executed query mix differs")
        nodes = 1 if topology == "single-node" else 3
        require(type(executed["expected_node_count"]) is int and executed["expected_node_count"] == nodes,
                "executed node count differs")
        if "runtime_evidence" in scenario:
            validate_runtime(scenario["runtime_evidence"], engine, nodes, expected_identity)
        require(executed["reset"] is True, "fresh corpus reset required")
        executed_configs[topology] = {key: value for key, value in executed.items()
                                      if key not in ("base_url", "base_urls", "index", "query_mix", "diagnostic_timeline")}
        executed_configs[topology]["query_mix"] = weights
        if engine == "steelsearch":
            executable = scenario["executable"]
            require(isinstance(executable, dict), "executable object required")
            require(digest(executable["sha256"], "executable") == expected_identity,
                    f"{topology}: executable does not match expected identity")
            require(isinstance(executable["path"], str) and executable["path"].strip(),
                    "executable path required")
        else:
            require(scenario["target_identity"]["version"]["number"] == expected_identity,
                    "OpenSearch version mismatch")
        summary = scenario["summary"]
        require(isinstance(summary, dict), "summary object required")
        zero(summary["error_count"], "scenario errors")
        zero(summary["error_rate"], "scenario error rate")
        successful = count(summary["success_count"], "successful requests")
        require(count(summary["operation_count"], "total requests") == successful,
                "total and successful counts differ")
        elapsed = measurement(summary["elapsed_seconds"], "elapsed")
        require(elapsed >= measurement(config["duration_seconds"], "duration"), "incomplete timed run")
        throughput = measurement(summary["throughput_ops_per_second"], "throughput")
        require(math.isclose(float(throughput), successful / float(elapsed), rel_tol=1e-6),
                "throughput does not match count and elapsed time")
        metrics[f"{topology}/throughput"] = throughput
        operations = scenario["operations"]
        require(isinstance(operations, dict), "operations object required")
        require(set(operations) == set(OPERATIONS), "exactly seven operation results required")
        total = 0
        for operation in OPERATIONS:
            result = operations[operation]
            require(isinstance(result, dict), "operation object required")
            zero(result["error_count"], f"{operation} errors")
            samples = count(result["success_count"], f"{operation} samples")
            total += samples
            latency = result["latency_ms"]
            require(isinstance(latency, dict), "latency object required")
            require(count(latency["count"], "latency samples") == samples, "latency counts differ")
            for metric in ("mean", "p95", "p99"):
                metrics[f"{topology}/{operation}/{metric}"] = measurement(latency[metric], metric)
            require(measurement(latency["p95"], "p95") <= measurement(latency["p99"], "p99"),
                    "percentile order invalid")
        require(total == successful, "operation counts do not sum to scenario total")
    return metrics, normalized, executed_configs


def evaluate_reports(baseline, candidate, reference, candidate_sha256):
    digest(candidate_sha256, "candidate identity")
    before, config, executed = validate_report(baseline, "steelsearch", BASELINE_SHA256)
    after, after_config, after_executed = validate_report(candidate, "steelsearch", candidate_sha256)
    opensearch, ref_config, ref_executed = validate_report(reference, "opensearch", REFERENCE_VERSION)
    require(config == after_config == ref_config, "workload configurations differ")
    require(executed == after_executed == ref_executed, "executed configurations differ")
    result = compare_metrics(before, after)
    result.update({
        "scope": "artifact consistency and cumulative numeric budget; not implementation acceptance",
        "report_integrity_passed": True,
        "baseline_release": "v0.6.0",
        "baseline_sha256": BASELINE_SHA256,
        "candidate_sha256": candidate_sha256,
        "opensearch_version": REFERENCE_VERSION,
        "opensearch_metrics": {key: str(value) for key, value in opensearch.items()},
        "unverified_requirements": ["fresh full-suite runner provenance", "actual runtime/security/durability/resource settings",
                                    "source-to-binary provenance", "predefined repeated-measurement procedure"],
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ("baseline", "candidate", "opensearch"):
        parser.add_argument(f"--{role}", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {getattr(args, role).resolve() for role in ("baseline", "candidate", "opensearch")}:
        parser.error("output must not overwrite an input report")
    try:
        inputs = [load_report(getattr(args, role)) for role in ("baseline", "candidate", "opensearch")]
        result = evaluate_reports(*(item[0] for item in inputs), args.candidate_sha256)
        result["reports"] = dict(zip(("baseline", "candidate", "opensearch"), (item[1] for item in inputs)))
        code = 0 if result["numeric_budget_passed"] else 1
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        result = {"acceptance_established": False, "report_integrity_passed": False,
                  "numeric_budget_passed": False, "error": str(error)}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in ("metrics", "opensearch_metrics")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
