#!/usr/bin/env python3
"""Compare append-workload visibility after quiescence; never a performance gate."""

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

from benchmark_runtime_evidence import capture_runtime, require_stable_runtime
from run_core_performance_gate import QUERY_MIX, ROOT, execution_fingerprint, file_hash


def expected_documents(report):
    if report.get("load_runner_returncode", 0) != 0 or report["summary"]["error_count"] != 0:
        raise ValueError("successful load required for cardinality accounting")
    if report["config"]["reset"] is not True:
        raise ValueError("fresh corpus required")
    corpus = report["config"]["corpus_size"]
    writes = report["operations"]["write"]["success_count"]
    if type(corpus) is not int or corpus <= 0 or type(writes) is not int or writes < 0:
        raise ValueError("invalid corpus or write count")
    # LoadRunner uses live-{client_id}-{counter}; seed IDs have a different prefix.
    return corpus + writes


def exact_total(response):
    total = response["hits"]["total"]
    if (total["relation"] != "eq" or type(total["value"]) is not int
            or total["value"] < 0):
        raise ValueError("exact nonnegative hit count required")
    failed = response.get("_shards", {}).get("failed")
    if response.get("timed_out") is not False or type(failed) is not int or failed != 0:
        raise ValueError("incomplete search cannot prove visibility")
    return total["value"]


def observe(matrix, url, index):
    payload = {"size": 0, "track_total_hits": True, "query": {"match_all": {}}}
    native = matrix.http_json(f"{url}/{index}/_search", 10, "POST", payload)
    fallback = matrix.http_json(f"{url}/{index}/_search?ignore_unavailable=false", 10, "POST", payload)
    stats = matrix.http_json(f"{url}/{index}/_stats", 10)
    return {"native_count": exact_total(native), "fallback_count": exact_total(fallback),
            "responses": {"native": native, "fallback": fallback, "stats": stats}}


def observe_endpoints(matrix, urls, index, drain=False):
    refreshes = {}
    if drain:
        for url in urls:
            response = matrix.http_json(f"{url}/{index}/_refresh", 10, "POST")
            failed = response["_shards"]["failed"]
            if type(failed) is not int or failed != 0:
                raise ValueError("post-load refresh failed")
            refreshes[url] = response
    result = []
    for url in urls:
        observation = {"url": url, **observe(matrix, url, index)}
        if drain:
            observation["refresh_response"] = refreshes[url]
        result.append(observation)
    return result


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def select_scenario(matrix, topology):
    return next(scenario for scenario in matrix.SCENARIOS
                if scenario.engine == "steelsearch" and scenario.topology == topology)


def observe_node_counters(matrix, urls, expected_nodes):
    if len(urls) != expected_nodes or len(set(urls)) != expected_nodes:
        raise ValueError("one distinct endpoint per owned node required")
    counters = ("refresh_tantivy_document_add_nanos", "refresh_tantivy_commit_nanos",
                "refresh_tantivy_reload_nanos", "refresh_tantivy_doc_id_lookup_nanos")
    observations = []
    seen = set()
    for url in urls:
        response = matrix.http_json(f"{url}/_nodes/stats", 10)
        # Development stats contain remote placeholders; only the local entry has counters.
        local = [(node_id, node["steelsearch"]["search_cache"])
                 for node_id, node in response["nodes"].items()
                 if node.get("steelsearch", {}).get("search_cache", {})]
        if len(local) != 1 or local[0][0] in seen:
            raise ValueError("exactly one distinct local counter set per endpoint required")
        node_id, values = local[0]
        if any(type(values.get(key)) is not int or values[key] < 0 for key in counters):
            raise ValueError("nonnegative integer refresh counters required")
        seen.add(node_id)
        observations.append({"url": url, "node_id": node_id,
                             "counters": {key: values[key] for key in counters},
                             "response": response})
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ("before", "after"):
        parser.add_argument(f"--{role}-binary", type=Path, required=True)
        parser.add_argument(f"--{role}-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--duration-seconds", type=float, default=60)
    parser.add_argument("--topology", choices=("single-node", "three-node"), default="single-node")
    parser.add_argument("--node-counters", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.duration_seconds) or args.duration_seconds <= 0:
        parser.error("positive finite duration required")
    os.environ["RUN_HTTP_LOAD_TESTS"] = "1"
    binaries = {role: getattr(args, f"{role}_binary").resolve(strict=True) for role in ("before", "after")}
    hashes = {role: getattr(args, f"{role}_sha256") for role in binaries}
    for role in binaries:
        if file_hash(binaries[role]) != hashes[role]:
            parser.error(f"{role} executable hash mismatch")
    spec = importlib.util.spec_from_file_location("refresh_work_matrix", ROOT / "tools/run-search-benchmark-matrix.py")
    matrix = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = matrix
    spec.loader.exec_module(matrix)
    scenario = select_scenario(matrix, args.topology)
    workload = argparse.Namespace(clients=4, number_of_shards=3, number_of_replicas=0 if scenario.node_count == 1 else 1,
        corpus_size=5000, vector_dimension=384, vector_source="default", vector_space_type="default",
        duration_seconds=args.duration_seconds, query_mix=QUERY_MIX, timeout_seconds=10,
        seed=13, operation_resource_deltas=False, diagnostic_timeline=False)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    fingerprint = execution_fingerprint()
    fingerprint[str(Path(__file__).resolve())] = file_hash(Path(__file__))
    plan = {"diagnostic_only": True, "acceptance_established": False,
        "scope": f"{args.topology} cardinality and post-load refresh observations; not ID/content completeness or a full gate",
        "topology": args.topology, "node_counters": args.node_counters,
        "order": ["before", "after", "after", "before"], "workload": vars(workload),
        "binaries": {role: {"path": str(path), "sha256": hashes[role]} for role, path in binaries.items()},
        "execution_files": fingerprint, "drains": 2,
        "limitations": "post-load probes are outside the timed interval; runtime and resource snapshots and cumulative node counters include preparation; sequential node snapshots are not atomic; endpoint counts must not be summed as proof of global unique cardinality; no periodic visibility probes"}
    plan_path = output / "plan.json"
    write_json(plan_path, plan)
    plan_hash = file_hash(plan_path)
    result = {"diagnostic_only": True, "acceptance_established": False, "plan_sha256": plan_hash, "runs": []}
    try:
        for number, role in enumerate(plan["order"]):
            if file_hash(plan_path) != plan_hash or any(file_hash(ROOT / path) != digest for path, digest in fingerprint.items()):
                raise ValueError("diagnostic plan or tools changed")
            if any(file_hash(path) != hashes[name] for name, path in binaries.items()):
                raise ValueError("diagnostic executable changed")
            row = {"role": role, "binary_sha256": hashes[role]}
            result["runs"].append(row)
            directory = output / f"{number:02d}-{role}"
            handle = matrix.start_cluster(scenario, directory, binaries[role])
            try:
                matrix.wait_for_cluster(scenario, handle.base_url, 10)
                pids = matrix.resolve_resource_pids(handle, binaries[role])
                before = capture_runtime(pids, [], hashes[role], scenario.node_count)
                baseline_path = directory / "baseline.json"
                baseline = matrix.run_baseline(scenario, handle, baseline_path, workload, pids)
                row.update(expected_documents=expected_documents(baseline),
                    baseline={"path": str(baseline_path), "sha256": file_hash(baseline_path)},
                    summary=baseline["summary"], refresh=baseline["operations"]["refresh"],
                    resources=baseline["resource_usage"], observations=[])
                index = f"search-benchmark-{scenario.key}"
                if args.node_counters:
                    row["node_counters_after_load"] = observe_node_counters(
                        matrix, handle.base_urls, scenario.node_count)
                endpoint_rounds = [observe_endpoints(matrix, handle.base_urls, index)]
                row["endpoint_observations"] = endpoint_rounds
                row["observations"].append(endpoint_rounds[-1][0])
                for _ in range(2):
                    endpoint_rounds.append(observe_endpoints(matrix, handle.base_urls, index, drain=True))
                    row["observations"].append(endpoint_rounds[-1][0])
                if args.node_counters:
                    row["node_counters_after_drains"] = observe_node_counters(
                        matrix, handle.base_urls, scenario.node_count)
                after = capture_runtime(pids, [], hashes[role], scenario.node_count)
                require_stable_runtime(before, after)
                row["runtime_evidence"] = {"before": before, "after": after}
            finally:
                handle.stop()
            if any(file_hash(ROOT / path) != digest for path, digest in fingerprint.items()) or file_hash(plan_path) != plan_hash:
                raise ValueError("diagnostic inputs changed during execution")
            if any(file_hash(path) != hashes[name] for name, path in binaries.items()):
                raise ValueError("diagnostic executable changed during execution")
            write_json(directory / "observation.json", row)
            print(json.dumps({"run": number, "role": role, "expected": row["expected_documents"],
                "observed": [{key: observation[key] for key in ("native_count", "fallback_count")}
                             for observation in row["observations"]]}), flush=True)
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        write_json(output / "result.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
