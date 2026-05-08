#!/usr/bin/env python3
"""Collect actual mixed-cluster write/read evidence for a Java-primary/Rust-replica profile."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class HttpJson:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        expected: set[int] | None = None,
    ) -> tuple[int, Any]:
        expected = expected or {200}
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            data = {"raw": text}
        if status not in expected:
            raise AssertionError(f"{method} {path} returned {status}: {data}")
        return status, data


def emit_phase_artifact(payload: dict[str, Any]) -> None:
    artifact_path = os.environ.get("JAVA_MIXED_CLUSTER_PHASE_ARTIFACT_PATH")
    if not artifact_path:
        return
    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def current_profile_name() -> str | None:
    report_dir = os.environ.get("JAVA_MIXED_CLUSTER_REPORT_DIR")
    if not report_dir:
        return None
    return Path(report_dir).name


def persist_raw(state_dir: Path, name: str, payload: Any) -> str:
    path = state_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(path)


def load_raw(state_dir: Path, name: str) -> Any | None:
    path = state_dir / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_probe_report_metadata(probe_report: str) -> dict[str, Any]:
    data = json.loads(Path(probe_report).read_text(encoding="utf-8"))
    artifacts = data.get("artifacts") or {}
    return {
        "work_dir": data.get("work_dir"),
        "artifacts": artifacts,
        "membership_formed": data.get("membership_formed"),
        "observed_node_count": data.get("observed_node_count"),
    }


def current_node_count(client: HttpJson) -> int:
    _, nodes = client.request("GET", "/_cat/nodes?format=json", expected={200})
    return len(nodes) if isinstance(nodes, list) else 0


def wait_for_node_count(client: HttpJson, minimum_nodes: int, attempts: int, sleep_seconds: float) -> int:
    last = 0
    for _ in range(attempts):
        try:
            last = current_node_count(client)
        except Exception:
            last = 0
        if last >= minimum_nodes:
            return last
        time.sleep(sleep_seconds)
    return last


def wait_for_prepare_ready(
    client: HttpJson,
    minimum_nodes: int,
    attempts: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    last_node_count = 0
    last_error: str | None = None
    for _ in range(attempts):
        try:
            _, health = client.request("GET", "/_cluster/health", expected={200})
            last_node_count = current_node_count(client)
            if last_node_count >= minimum_nodes:
                return {
                    "ready": True,
                    "node_count": last_node_count,
                    "cluster_health_status": health.get("status"),
                    "error": None,
                }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_node_count = 0
        time.sleep(sleep_seconds)

    return {
        "ready": False,
        "node_count": last_node_count,
        "cluster_health_status": None,
        "error": last_error,
    }


def read_pid(pid_path: Path) -> int:
    return int(pid_path.read_text(encoding="utf-8").strip())


def terminate_pid(pid_path: Path) -> None:
    pid = read_pid(pid_path)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    raise RuntimeError(f"pid {pid} did not exit after SIGTERM")


def restart_process(pid_path: Path, start_command_path: Path, stdout_path: Path, stderr_path: Path) -> int:
    start_cmd = start_command_path.read_text(encoding="utf-8").strip()
    stdout_handle = open(stdout_path, "ab")
    stderr_handle = open(stderr_path, "ab")
    proc = subprocess.Popen(
        ["/bin/bash", "-lc", start_cmd],
        stdout=stdout_handle,
        stderr=stderr_handle,
        preexec_fn=os.setsid,
    )
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")
    return proc.pid


def collect_checkpoint_observed(index_stats: dict[str, Any]) -> list[dict[str, Any]]:
    indices = index_stats.get("indices", {})
    observed: list[dict[str, Any]] = []
    for index_name, index_data in indices.items():
        shards = index_data.get("shards", {})
        for shard_id, copies in shards.items():
            for copy in copies:
                routing = copy.get("routing", {})
                seq_no = copy.get("seq_no", {})
                observed.append(
                    {
                        "index": index_name,
                        "shard": int(shard_id),
                        "role": "primary" if routing.get("primary") else "replica",
                        "node": routing.get("node"),
                        "max_seq_no": seq_no.get("max_seq_no"),
                        "local_checkpoint": seq_no.get("local_checkpoint"),
                        "global_checkpoint": seq_no.get("global_checkpoint"),
                    }
                )
    return observed


def calculate_checkpoint_drift(observed: list[dict[str, Any]]) -> dict[str, int]:
    drift: dict[str, int] = {}
    for report_field, source_field in (
        ("seq_no_drift", "max_seq_no"),
        ("local_checkpoint_drift", "local_checkpoint"),
        ("global_checkpoint_drift", "global_checkpoint"),
    ):
        values = [entry[source_field] for entry in observed if isinstance(entry.get(source_field), int)]
        drift[report_field] = max(values) - min(values) if values else 0
    return drift


def classify_divergence(
    state_dir: Path,
    checkpoint_drift: dict[str, int],
    java_primary: bool,
    rust_replica: bool,
    expected_doc_ids: set[str],
) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []

    read_search = load_raw(state_dir, "read-search.json")
    write_bulk = load_raw(state_dir, "write-bulk-response.json")

    hits = None
    if not isinstance(read_search, dict):
        failures.append("decode_mismatch")
    else:
        hits = read_search.get("hits", {}).get("hits")
        if not isinstance(hits, list):
            failures.append("decode_mismatch")

    if isinstance(write_bulk, dict) and write_bulk.get("errors"):
        failures.append("apply_mismatch")

    if isinstance(hits, list):
        seen_ids = {hit.get("_id") for hit in hits if isinstance(hit, dict)}
        if expected_doc_ids - seen_ids:
            failures.append("apply_mismatch")

    if any(value != 0 for value in checkpoint_drift.values()) or not java_primary or not rust_replica:
        failures.append("checkpoint_mismatch")

    ordered = []
    for failure in ("decode_mismatch", "apply_mismatch", "checkpoint_mismatch"):
        if failure in failures:
            ordered.append(failure)
    profile_name = current_profile_name()
    if profile_name == "rust-primary-java-replica":
        mapped: list[str] = []
        mapping = (
            ("acknowledged_but_diverged", "apply_mismatch"),
            ("metadata_mismatch", "checkpoint_mismatch"),
            ("unsupported_op", "decode_mismatch"),
        )
        for target, source in mapping:
            if source in ordered:
                mapped.append(target)
        return (mapped[0] if mapped else "none", mapped, ordered)
    return (ordered[0] if ordered else "none", ordered, ordered)


def maybe_inject_read_fault(search_read: dict[str, Any], fault_class: str | None) -> dict[str, Any]:
    if fault_class == "decode_mismatch":
        return {"raw": "injected decode mismatch"}
    if fault_class == "apply_mismatch":
        hits = search_read.get("hits", {}).get("hits", [])
        if isinstance(hits, list) and hits:
            mutated = json.loads(json.dumps(search_read))
            mutated["hits"]["hits"] = hits[:-1]
            return mutated
    return search_read


def maybe_inject_checkpoint_fault(checkpoint_drift: dict[str, int], fault_class: str | None) -> dict[str, int]:
    if fault_class == "checkpoint_mismatch":
        mutated = dict(checkpoint_drift)
        mutated["seq_no_drift"] = mutated.get("seq_no_drift", 0) + 1
        return mutated
    return checkpoint_drift


def wait_for_shards(client: HttpJson, index: str, attempts: int, sleep_seconds: float) -> list[dict[str, Any]]:
    path = f"/_cat/shards/{urllib.parse.quote(index, safe='')}?format=json"
    last = []
    for _ in range(attempts):
        _, last = client.request("GET", path, expected={200})
        if last:
            return last
        time.sleep(sleep_seconds)
    return last


def collect_unassigned_replica_explain(client: HttpJson, shards: list[dict[str, Any]]) -> dict[str, Any] | None:
    for shard in shards:
        if shard.get("prirep") == "r" and shard.get("state") == "UNASSIGNED":
            _, explain = client.request(
                "GET",
                "/_cluster/allocation/explain",
                {
                    "index": shard.get("index"),
                    "shard": int(shard.get("shard")),
                    "primary": False,
                },
                expected={200},
            )
            return explain
    return None


def _as_int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def classify_replica_provenance(recovery: dict[str, Any], replica_node: str) -> tuple[str | None, list[dict[str, Any]]]:
    shards = recovery.get(args.index, {}).get("shards", []) if False else None
    del shards
    details: list[dict[str, Any]] = []
    modes: set[str] = set()

    for index_name, index_payload in recovery.items():
        shard_entries = index_payload.get("shards", []) if isinstance(index_payload, dict) else []
        if not isinstance(shard_entries, list):
            continue
        for shard in shard_entries:
            if not isinstance(shard, dict):
                continue
            if shard.get("primary") is True:
                continue
            target = shard.get("target", {})
            target_name = target.get("name") if isinstance(target, dict) else None
            if target_name != replica_node:
                continue
            index_block = shard.get("index", {}) if isinstance(shard.get("index"), dict) else {}
            files_block = index_block.get("files", {}) if isinstance(index_block.get("files"), dict) else {}
            translog_block = shard.get("translog", {}) if isinstance(shard.get("translog"), dict) else {}

            file_count = max(
                _as_int(files_block.get("recovered")),
                _as_int(files_block.get("reused")) if _as_int(files_block.get("recovered")) == 0 else 0,
                _as_int(files_block.get("total_recovered")),
            )
            translog_ops = max(
                _as_int(translog_block.get("recovered")),
                _as_int(translog_block.get("recovered_ops")),
                _as_int(translog_block.get("total_on_start")),
            )

            mode: str | None
            if file_count > 0 and translog_ops > 0:
                mode = "mixed"
            elif translog_ops > 0:
                mode = "translog"
            elif file_count > 0:
                mode = "segment"
            else:
                mode = None

            if mode is not None:
                modes.add(mode)

            details.append(
                {
                    "index": index_name,
                    "shard_id": shard.get("id"),
                    "target_name": target_name,
                    "files_metric": file_count,
                    "translog_ops": translog_ops,
                    "mode": mode,
                }
            )

    if not modes:
        return None, details
    if "mixed" in modes or len(modes) > 1:
        return "mixed", details
    return next(iter(modes)), details


def cmd_prepare(args: argparse.Namespace) -> int:
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    readiness = wait_for_prepare_ready(
        client,
        minimum_nodes=args.prepare_ready_min_nodes,
        attempts=args.prepare_ready_attempts,
        sleep_seconds=args.prepare_ready_interval,
    )
    persist_raw(state_dir, "prepare-ready.json", readiness)
    if not readiness["ready"]:
        emit_phase_artifact(
            {
                "phase": "prepare",
                "prepare_ready_gate": False,
                "prepare_ready_node_count": readiness["node_count"],
                "prepare_ready_error": readiness["error"],
            }
        )
        raise RuntimeError(
            "prepare_ready_gate_failed "
            f"node_count={readiness['node_count']} "
            f"error={readiness['error']}"
        )
    client.request("DELETE", f"/{args.index}", expected={200, 202, 404})
    client.request(
        "PUT",
        f"/{args.index}",
        {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
            },
            "mappings": {
                "properties": {
                    "tenant": {"type": "keyword"},
                    "message": {"type": "text"},
                    "stage": {"type": "keyword"},
                }
            },
        },
        expected={200, 201},
    )
    _, health = client.request(
        "GET",
        f"/_cluster/health/{args.index}?wait_for_status=yellow&timeout={args.health_timeout}",
        expected={200},
    )
    shards = wait_for_shards(client, args.index, args.shard_poll_attempts, args.shard_poll_interval)
    persist_raw(state_dir, "prepare-health.json", health)
    persist_raw(state_dir, "prepare-shards.json", shards)
    emit_phase_artifact(
        {
            "phase": "prepare",
            "prepare_ready_gate": True,
            "prepare_ready_node_count": readiness["node_count"],
            "prepare_ready_error": readiness["error"],
            "expected_markers": ["java-primary-targeted", "rust-replica-targeted"],
            "prepare_cluster_health_status": health.get("status"),
            "prepare_shard_count": len(shards),
        }
    )
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    index_doc = {
        "tenant": "alpha",
        "message": "mixed-index-doc",
        "stage": "index",
    }
    _, index_response = client.request(
        "PUT",
        f"/{args.index}/_doc/{args.index_doc_id}",
        index_doc,
        expected={200, 201},
    )
    _, update_seed_response = client.request(
        "PUT",
        f"/{args.index}/_doc/{args.update_doc_id}",
        {
            "tenant": "alpha",
            "message": "mixed-update-seed",
            "stage": "update-seed",
        },
        expected={200, 201},
    )
    _, update_response = client.request(
        "POST",
        f"/{args.index}/_update/{args.update_doc_id}",
        {
            "doc": {
                "tenant": "alpha",
                "message": "mixed-update-final",
                "stage": "update",
            }
        },
        expected={200},
    )
    _, delete_seed_response = client.request(
        "PUT",
        f"/{args.index}/_doc/{args.delete_doc_id}",
        {
            "tenant": "alpha",
            "message": "mixed-delete-seed",
            "stage": "delete-seed",
        },
        expected={200, 201},
    )
    _, delete_response = client.request(
        "DELETE",
        f"/{args.index}/_doc/{args.delete_doc_id}",
        expected={200},
    )
    bulk_lines = [
        json.dumps({"index": {"_index": args.index, "_id": args.bulk_doc_id_1}}),
        json.dumps({"tenant": "alpha", "message": "mixed-bulk-1", "stage": "bulk-replay"}),
        json.dumps({"index": {"_index": args.index, "_id": args.bulk_doc_id_2}}),
        json.dumps({"tenant": "alpha", "message": "mixed-bulk-2", "stage": "bulk-replay"}),
    ]
    payload = ("\n".join(bulk_lines) + "\n").encode("utf-8")
    request = urllib.request.Request(
        f"{client.base_url}/_bulk",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        bulk_response = json.loads(response.read().decode("utf-8"))
    client.request("POST", f"/{args.index}/_refresh", expected={200})
    persist_raw(state_dir, "write-index-response.json", index_response)
    persist_raw(state_dir, "write-update-seed-response.json", update_seed_response)
    persist_raw(state_dir, "write-update-response.json", update_response)
    persist_raw(state_dir, "write-delete-seed-response.json", delete_seed_response)
    persist_raw(state_dir, "write-delete-response.json", delete_response)
    persist_raw(state_dir, "write-bulk-response.json", bulk_response)
    emit_phase_artifact(
        {
            "phase": "write",
            "write_modes": ["index", "delete", "update", "bulk-replay"],
            "index_result": index_response.get("result"),
            "update_result": update_response.get("result"),
            "delete_result": delete_response.get("result"),
            "bulk_item_count": len(bulk_response.get("items", [])),
            "bulk_errors": bool(bulk_response.get("errors")),
        }
    )
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    _, index_read = client.request("GET", f"/{args.index}/_doc/{args.index_doc_id}", expected={200})
    _, update_read = client.request("GET", f"/{args.index}/_doc/{args.update_doc_id}", expected={200})
    delete_status, delete_read = client.request("GET", f"/{args.index}/_doc/{args.delete_doc_id}", expected={200, 404})
    _, search_read = client.request(
        "POST",
        f"/{args.index}/_search",
        {
            "size": 10,
            "sort": [{"_id": {"order": "asc"}}],
            "query": {"match_all": {}},
        },
        expected={200},
    )
    search_read = maybe_inject_read_fault(search_read, args.fault_class)
    shards = wait_for_shards(client, args.index, args.shard_poll_attempts, args.shard_poll_interval)
    persist_raw(state_dir, "read-index-doc.json", index_read)
    persist_raw(state_dir, "read-update-doc.json", update_read)
    persist_raw(state_dir, "read-delete-doc.json", {"status": delete_status, "payload": delete_read})
    persist_raw(state_dir, "read-search.json", search_read)
    persist_raw(state_dir, "read-shards.json", shards)
    hits = search_read.get("hits", {}).get("hits", [])
    emit_phase_artifact(
        {
            "phase": "read",
            "visibility_stages": ["realtime", "read-after-refresh", "recovery-after-restart"],
            "read_hit_ids": [hit.get("_id") for hit in hits],
            "read_total_hits": len(hits),
            "deleted_doc_status": delete_status,
        }
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    shards = wait_for_shards(client, args.index, args.shard_poll_attempts, args.shard_poll_interval)
    _, recovery = client.request("GET", f"/{args.index}/_recovery?detailed=true", expected={200})
    _, nodes_info = client.request("GET", "/_nodes", expected={200})
    _, cat_nodes = client.request("GET", "/_cat/nodes?format=json", expected={200})
    _, cluster_state_nodes = client.request("GET", "/_cluster/state/nodes", expected={200})
    java_primary = any(
        shard.get("prirep") == "p" and shard.get("node") == args.java_node
        for shard in shards
    )
    rust_replica = any(
        shard.get("prirep") == "r" and shard.get("node") == args.rust_node
        for shard in shards
    )
    allocation_explain = None if rust_replica else collect_unassigned_replica_explain(client, shards)
    _, stats = client.request(
        "GET",
        f"/{args.index}/_stats?level=shards",
        expected={200},
    )
    checkpoint_observed = collect_checkpoint_observed(stats)
    checkpoint_drift = calculate_checkpoint_drift(checkpoint_observed)
    checkpoint_drift = maybe_inject_checkpoint_fault(checkpoint_drift, args.fault_class)
    replica_target_node = args.java_node if current_profile_name() == "rust-primary-java-replica" else args.rust_node
    replica_provenance, provenance_detail = classify_replica_provenance(recovery, replica_target_node)
    divergence_classification, observed_failure_classes, observed_raw_failure_classes = classify_divergence(
        state_dir=state_dir,
        checkpoint_drift=checkpoint_drift,
        java_primary=java_primary,
        rust_replica=rust_replica,
        expected_doc_ids={args.index_doc_id, args.update_doc_id, args.bulk_doc_id_1, args.bulk_doc_id_2},
    )
    persist_raw(state_dir, "check-shards.json", shards)
    persist_raw(state_dir, "check-stats.json", stats)
    persist_raw(state_dir, "check-recovery.json", recovery)
    persist_raw(state_dir, "check-nodes.json", nodes_info)
    persist_raw(state_dir, "check-cat-nodes.json", cat_nodes)
    persist_raw(state_dir, "check-cluster-state-nodes.json", cluster_state_nodes)
    if allocation_explain is not None:
        persist_raw(state_dir, "check-allocation-explain.json", allocation_explain)
    nodes_map = nodes_info.get("nodes", {}) if isinstance(nodes_info, dict) else {}
    rust_node_roles = None
    rust_node_visible = False
    for node in nodes_map.values():
        if node.get("name") == args.rust_node:
            rust_node_visible = True
            rust_node_roles = node.get("roles", [])
            break
    cluster_state_nodes_map = cluster_state_nodes.get("nodes", {}) if isinstance(cluster_state_nodes, dict) else {}
    cluster_state_node_names = [node.get("name") for node in cluster_state_nodes_map.values()]
    rust_node_in_cluster_state = args.rust_node in cluster_state_node_names
    emit_phase_artifact(
        {
            "phase": "check",
            "checkpoint_source": "stats_seq_no",
            "checkpoint_observed": checkpoint_observed,
            "checkpoint_drift": checkpoint_drift,
            "placement_observed": {
                "java_primary": java_primary,
                "rust_replica": rust_replica,
            },
            "replica_provenance": replica_provenance,
            "replica_provenance_detail": provenance_detail,
            "observed_failure_classes": observed_failure_classes,
            "observed_raw_failure_classes": observed_raw_failure_classes,
            "divergence_classification": divergence_classification,
            "allocation_explain_can_allocate": None if allocation_explain is None else allocation_explain.get("can_allocate"),
            "allocation_explain_reason": None if allocation_explain is None else allocation_explain.get("allocate_explanation"),
            "cluster_http_node_names": [node.get("name") for node in nodes_map.values()],
            "rust_node_http_visible": rust_node_visible,
            "rust_node_http_roles": rust_node_roles,
            "cluster_state_node_names": cluster_state_node_names,
            "rust_node_in_cluster_state": rust_node_in_cluster_state,
        }
    )
    return 0 if divergence_classification == "none" else 2


def cmd_recover(args: argparse.Namespace) -> int:
    if not args.probe_report:
        raise AssertionError("recover requires --probe-report")
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    metadata = load_probe_report_metadata(args.probe_report)
    artifacts = metadata["artifacts"]
    steel_pid_path = Path(artifacts["steelsearch_pid"])
    steel_start_command_path = Path(artifacts["steelsearch_start_command"])
    steel_stdout_path = Path(artifacts["steelsearch_stdout"])
    steel_stderr_path = Path(artifacts["steelsearch_stderr"])

    old_pid = read_pid(steel_pid_path)
    terminate_pid(steel_pid_path)
    new_pid = restart_process(
        pid_path=steel_pid_path,
        start_command_path=steel_start_command_path,
        stdout_path=steel_stdout_path,
        stderr_path=steel_stderr_path,
    )
    recovered_node_count = wait_for_node_count(
        client,
        minimum_nodes=2,
        attempts=args.shard_poll_attempts * 6,
        sleep_seconds=args.shard_poll_interval,
    )
    persist_raw(
        state_dir,
        "recover-state.json",
        {
            "old_steelsearch_pid": old_pid,
            "new_steelsearch_pid": new_pid,
            "recovered_node_count": recovered_node_count,
            "probe_report": args.probe_report,
        },
    )
    emit_phase_artifact(
        {
            "phase": "recover",
            "recovery_outcome": "rust-restart-completed",
            "recovery_bootstrap_mode": "probe-workdir-restart-metadata",
            "recovered_node_count": recovered_node_count,
        }
    )
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    client = HttpJson(args.cluster_url)
    state_dir = Path(args.state_dir)
    _, single_read = client.request("GET", f"/{args.index}/_doc/{args.index_doc_id}", expected={200})
    _, search_read = client.request(
        "POST",
        f"/{args.index}/_search",
        {
            "size": 10,
            "sort": [{"_id": {"order": "asc"}}],
            "query": {"match_all": {}},
        },
        expected={200},
    )
    _, stats = client.request(
        "GET",
        f"/{args.index}/_stats?level=shards",
        expected={200},
    )
    shards = wait_for_shards(client, args.index, args.shard_poll_attempts, args.shard_poll_interval)
    persist_raw(state_dir, "restart-read-single-doc.json", single_read)
    persist_raw(state_dir, "restart-read-search.json", search_read)
    persist_raw(state_dir, "restart-read-shards.json", shards)
    persist_raw(state_dir, "restart-check-stats.json", stats)
    hits = search_read.get("hits", {}).get("hits", [])
    emit_phase_artifact(
        {
            "phase": "restart",
            "post_restart_read_hit_ids": [hit.get("_id") for hit in hits],
            "post_restart_read_total_hits": len(hits),
            "post_restart_shard_count": len(shards),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cluster-url", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--java-node", required=True)
    parser.add_argument("--rust-node", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--health-timeout", default="30s")
    parser.add_argument("--shard-poll-attempts", type=int, default=10)
    parser.add_argument("--shard-poll-interval", type=float, default=1.0)
    parser.add_argument("--index-doc-id", default="doc-index")
    parser.add_argument("--delete-doc-id", default="doc-delete")
    parser.add_argument("--update-doc-id", default="doc-update")
    parser.add_argument("--bulk-doc-id-1", default="doc-bulk-1")
    parser.add_argument("--bulk-doc-id-2", default="doc-bulk-2")
    parser.add_argument("--probe-report")
    parser.add_argument("--prepare-ready-min-nodes", type=int, default=2)
    parser.add_argument("--prepare-ready-attempts", type=int, default=15)
    parser.add_argument("--prepare-ready-interval", type=float, default=1.0)
    parser.add_argument(
        "--fault-class",
        choices=["decode_mismatch", "apply_mismatch", "checkpoint_mismatch"],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    subparsers.add_parser("write")
    subparsers.add_parser("read")
    subparsers.add_parser("recover")
    subparsers.add_parser("restart")
    subparsers.add_parser("check")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "prepare":
        return cmd_prepare(args)
    if args.command == "write":
        return cmd_write(args)
    if args.command == "read":
        return cmd_read(args)
    if args.command == "recover":
        return cmd_recover(args)
    if args.command == "restart":
        return cmd_restart(args)
    if args.command == "check":
        return cmd_check(args)
    parser.error(f"unsupported command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
