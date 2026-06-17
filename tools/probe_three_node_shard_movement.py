#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import shutil
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
        timeout: float = 20.0,
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
            with urllib.request.urlopen(request, timeout=timeout) as response:
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


def reserve_unique_ports(count: int) -> list[int]:
    holders: list[socket.socket] = []
    try:
        for _ in range(count):
            bound = socket.socket()
            bound.bind(("127.0.0.1", 0))
            holders.append(bound)
        return [bound.getsockname()[1] for bound in holders]
    finally:
        for bound in holders:
            bound.close()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_logged(command: str, log_path: Path) -> None:
    with log_path.open("ab") as handle:
        subprocess.run(
            ["/bin/bash", "-lc", command],
            cwd="/home/ubuntu/steelsearch",
            stdout=handle,
            stderr=handle,
            check=True,
        )


def start_process(command: str, env: dict[str, str], stdout_path: Path, stderr_path: Path) -> subprocess.Popen[bytes]:
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    return subprocess.Popen(
        ["/bin/bash", "-lc", command],
        cwd="/home/ubuntu/steelsearch",
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        preexec_fn=os.setsid,
    )


def wait_for(predicate, attempts: int, sleep_seconds: float) -> bool:
    for _ in range(attempts):
        if predicate():
            return True
        time.sleep(sleep_seconds)
    return False


def wait_for_http(url: str, attempts: int, sleep_seconds: float) -> bool:
    client = HttpJson(url)
    return wait_for(lambda: _safe_root(client), attempts, sleep_seconds)


def _safe_root(client: HttpJson) -> bool:
    try:
        client.request("GET", "/", expected={200})
        return True
    except Exception:
        return False


def current_node_count(client: HttpJson) -> int:
    _, data = client.request("GET", "/_cluster/health", expected={200})
    value = data.get("number_of_nodes", 0) if isinstance(data, dict) else 0
    return int(value)


def clear_opensearch_cluster_blocks(client: HttpJson) -> None:
    client.request(
        "PUT",
        "/_cluster/settings",
        {
            "persistent": {
                "cluster.blocks.create_index": False,
                "cluster.routing.allocation.disk.threshold_enabled": False,
            },
            "transient": {
                "cluster.blocks.create_index": False,
                "cluster.routing.allocation.disk.threshold_enabled": False,
            },
        },
        expected={200},
    )


def safe_request(client: HttpJson, method: str, path: str, body: Any | None = None) -> dict[str, Any]:
    try:
        status, data = client.request(method, path, body=body, expected={200})
        return {"ok": True, "status": status, "data": data}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def wait_for_node_count(client: HttpJson, expected_count: int, attempts: int, sleep_seconds: float) -> bool:
    return wait_for(lambda: current_node_count(client) >= expected_count, attempts, sleep_seconds)


def get_shards(client: HttpJson, index: str) -> list[dict[str, Any]]:
    _, data = client.request(
        "GET",
        f"/_cat/shards/{urllib.parse.quote(index, safe='')}?format=json",
        expected={200},
    )
    if not isinstance(data, list):
        raise AssertionError(f"unexpected shard payload: {data}")
    return data


def placement(shards: list[dict[str, Any]]) -> dict[str, str | None]:
    primary = next((row for row in shards if row.get("prirep") == "p"), None)
    replica = next((row for row in shards if row.get("prirep") == "r"), None)
    return {
        "primary_node": None if primary is None else primary.get("node"),
        "primary_state": None if primary is None else primary.get("state"),
        "replica_node": None if replica is None else replica.get("node"),
        "replica_state": None if replica is None else replica.get("state"),
    }


def get_search_count(client: HttpJson, index: str) -> int:
    _, data = client.request(
        "POST",
        f"/{urllib.parse.quote(index, safe='')}/_search",
        {"size": 0, "query": {"match_all": {}}},
        expected={200},
    )
    total = data.get("hits", {}).get("total", {})
    if isinstance(total, dict):
        return int(total.get("value", 0))
    if isinstance(total, int):
        return total
    return 0


def recovery_report(client: HttpJson, index: str) -> dict[str, Any]:
    return safe_request(
        client,
        "GET",
        f"/{urllib.parse.quote(index, safe='')}/_recovery",
    )


def collect_checkpoint_observed(client: HttpJson, index: str) -> list[dict[str, Any]]:
    _, stats = client.request(
        "GET",
        f"/{urllib.parse.quote(index, safe='')}/_stats?level=shards",
        expected={200},
    )
    indices = stats.get("indices", {}) if isinstance(stats, dict) else {}
    index_data = indices.get(index, {}) if isinstance(indices, dict) else {}
    shards = index_data.get("shards", {}) if isinstance(index_data, dict) else {}
    observed: list[dict[str, Any]] = []
    for shard_id, copies in shards.items():
        if not isinstance(copies, list):
            continue
        for copy in copies:
            if not isinstance(copy, dict):
                continue
            routing = copy.get("routing", {}) if isinstance(copy.get("routing"), dict) else {}
            seq_no = copy.get("seq_no", {}) if isinstance(copy.get("seq_no"), dict) else {}
            observed.append(
                {
                    "index": index,
                    "shard": int(shard_id),
                    "role": "primary" if routing.get("primary") else "replica",
                    "node": routing.get("node"),
                    "max_seq_no": seq_no.get("max_seq_no"),
                    "local_checkpoint": seq_no.get("local_checkpoint"),
                    "global_checkpoint": seq_no.get("global_checkpoint"),
                }
            )
    return observed


def checkpoint_drift(observed: list[dict[str, Any]]) -> dict[str, int]:
    drift: dict[str, int] = {}
    for report_field, source_field in (
        ("seq_no_drift", "max_seq_no"),
        ("local_checkpoint_drift", "local_checkpoint"),
        ("global_checkpoint_drift", "global_checkpoint"),
    ):
        values = [entry[source_field] for entry in observed if isinstance(entry.get(source_field), int)]
        drift[report_field] = max(values) - min(values) if values else 0
    return drift


def checkpoint_report(client: HttpJson, index: str) -> dict[str, Any]:
    observed = collect_checkpoint_observed(client, index)
    return {
        "checkpoint_observed": observed,
        "checkpoint_drift": checkpoint_drift(observed),
    }


def update_index_settings(client: HttpJson, index: str, settings: dict[str, Any]) -> None:
    client.request("PUT", f"/{index}/_settings", {"index": settings}, expected={200})


def wait_for_index_health(client: HttpJson, index: str, expected_status: str, attempts: int, sleep_seconds: float) -> dict[str, Any]:
    latest: dict[str, Any] = {}

    def predicate() -> bool:
        nonlocal latest
        _, latest = client.request("GET", f"/_cluster/health/{index}", expected={200})
        return latest.get("status") == expected_status

    if not wait_for(predicate, attempts, sleep_seconds):
        raise RuntimeError(f"timed out waiting for {index} health={expected_status}: {latest}")
    return latest


def wait_for_shard_condition(client: HttpJson, index: str, predicate) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []

    def wrapped() -> bool:
        nonlocal latest
        latest = get_shards(client, index)
        return predicate(latest)

    if not wait_for(wrapped, attempts=180, sleep_seconds=1.0):
        raise RuntimeError(f"timed out waiting for shard condition on {index}: {latest}")
    return latest


def terminate_process(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait(timeout=10)


def phase_result(name: str, **kwargs: Any) -> dict[str, Any]:
    result = {"phase": name}
    result.update(kwargs)
    return result


def phase_names(report: dict[str, Any]) -> set[str]:
    phases = report.get("phases", [])
    if not isinstance(phases, list):
        return set()
    return {
        phase["phase"]
        for phase in phases
        if isinstance(phase, dict) and isinstance(phase.get("phase"), str)
    }


def phase_passed(report: dict[str, Any], name: str) -> bool:
    phases = report.get("phases", [])
    if not isinstance(phases, list):
        return False
    return any(
        isinstance(phase, dict) and phase.get("phase") == name and bool(phase.get("passed"))
        for phase in phases
    )


def checkpoint_drift_passed(report: dict[str, Any]) -> bool:
    phases = report.get("phases", [])
    if not isinstance(phases, list):
        return False
    checkpoint_phases = [
        phase
        for phase in phases
        if isinstance(phase, dict) and isinstance(phase.get("checkpoint_drift"), dict)
    ]
    return all(
        all(value == 0 for value in phase["checkpoint_drift"].values())
        for phase in checkpoint_phases
    )


def interruption_evidence_passed(report: dict[str, Any]) -> bool:
    expected = {
        "interrupt_java_to_steelsearch_recovery",
        "resume_or_restart_java_to_steelsearch_recovery",
        "finalize_java_to_steelsearch_recovery",
        "interrupt_steelsearch_to_opensearch_recovery",
        "resume_or_restart_steelsearch_to_opensearch_recovery",
        "finalize_steelsearch_to_opensearch_recovery",
    }
    return expected.issubset(phase_names(report))


def summarize_movement_report(
    report: dict[str, Any], *, require_interruption: bool = False
) -> dict[str, Any]:
    opensearch_to_steelsearch_passed = phase_passed(report, "opensearch_to_steelsearch")
    steelsearch_to_opensearch_passed = phase_passed(report, "steelsearch_to_opensearch")
    checkpoint_drift_ok = checkpoint_drift_passed(report)
    interruption_evidence_ok = interruption_evidence_passed(report)
    return {
        "passed": opensearch_to_steelsearch_passed
        and steelsearch_to_opensearch_passed
        and checkpoint_drift_ok
        and (interruption_evidence_ok or not require_interruption),
        "opensearch_to_steelsearch_passed": opensearch_to_steelsearch_passed,
        "steelsearch_to_opensearch_passed": steelsearch_to_opensearch_passed,
        "checkpoint_drift_ok": checkpoint_drift_ok,
        "interruption_evidence_ok": interruption_evidence_ok,
        "interruption_evidence_required": require_interruption,
    }


def collect_seed_identity(root: Path, java_transport_port: int, java_http_port: int, label: str) -> Path:
    identity_dir = root / "transport-identity"
    identity_dir.mkdir(parents=True, exist_ok=True)
    frame_dump = subprocess.run(
        ["/bin/bash", "-lc", "bash tools/dump_java_transport_handshake_frame.sh"],
        cwd="/home/ubuntu/steelsearch",
        capture_output=True,
        text=True,
        check=True,
    )
    frame_hex = frame_dump.stdout.strip()
    report_path = identity_dir / f"transport-handshake-report-{label}.json"
    parsed_path = identity_dir / f"transport-handshake-response-parsed-{label}.json"
    run_logged(
        "python3 tools/send_opensearch_tcp_handshake_probe.py "
        f"--host 127.0.0.1 --port {java_transport_port} "
        "--action internal:transport/handshake "
        f"--frame-hex {frame_hex} "
        "--timeout-seconds 2.0 "
        f"--report-path {report_path}",
        identity_dir / f"probe-{label}.log",
    )
    response_hex = read_json(report_path).get("response_hex", "")
    if not response_hex:
        raise RuntimeError("failed to collect OpenSearch transport handshake response")
    run_logged(
        f"bash tools/parse_java_transport_handshake_response.sh --response-hex {response_hex} --report-path {parsed_path} --http-address 127.0.0.1:{java_http_port}",
        identity_dir / f"parse-{label}.log",
    )
    return parsed_path


def make_env(extra: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra)
    return env


def steelsearch_dev_env(
    *,
    rust_http: int,
    rust_transport: int,
    seeds: str,
    rust_dir: Path,
    seed_identities: list[Path],
) -> dict[str, str]:
    return make_env(
        {
            "STEELSEARCH_HTTP_HOST": "127.0.0.1",
            "STEELSEARCH_TRANSPORT_HOST": "127.0.0.1",
            "STEELSEARCH_HTTP_ACCESS_HOST": "127.0.0.1",
            "STEELSEARCH_TRANSPORT_ACCESS_HOST": "127.0.0.1",
            "STEELSEARCH_HTTP_PORT": str(rust_http),
            "STEELSEARCH_TRANSPORT_PORT": str(rust_transport),
            "STEELSEARCH_CLUSTER_NAME": "mixed-three-node-dev",
            "STEELSEARCH_NODE_NAME": "rust-replica-1",
            "STEELSEARCH_NODE_ID": "rust-replica-1",
            "STEELSEARCH_DISCOVERY_SEED_HOSTS": seeds,
            "STEELSEARCH_WORK_DIR": str(rust_dir),
            "STEELSEARCH_NODE_ROLES": "cluster_manager,data,ingest,remote_cluster_client",
            "STEELSEARCH_JAVA_WRITE_FORWARDING_VALIDATED": "true",
            "STEELSEARCH_SPLIT_BUILD_RUN": "1",
            "STEELSEARCH_INTEROP_SEED_PEER_IDENTITY_MANIFEST": ",".join(
                str(path) for path in seed_identities
            ),
        }
    )


def opensearch_dev_env(
    *,
    http_port: int,
    transport_port: int,
    node_name: str,
    seeds: str,
    initial_managers: str,
    work_dir: Path,
) -> dict[str, str]:
    return make_env(
        {
            "OPENSEARCH_HTTP_PORT": str(http_port),
            "OPENSEARCH_TRANSPORT_PORT": str(transport_port),
            "OPENSEARCH_CLUSTER_NAME": "mixed-three-node-dev",
            "OPENSEARCH_NODE_NAME": node_name,
            "OPENSEARCH_DISCOVERY_SEED_HOSTS": seeds,
            "OPENSEARCH_INITIAL_CLUSTER_MANAGER_NODES": initial_managers,
            "OPENSEARCH_WORK_DIR": str(work_dir),
        }
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", default="/tmp/three-node-shard-movement.latest")
    parser.add_argument("--index", default="three-node-shard-movement-000001")
    parser.add_argument("--doc-count", type=int, default=5)
    parser.add_argument(
        "--require-interruption",
        action="store_true",
        help="fail the final summary unless both-direction interruption/resume/finalize phases are recorded",
    )
    parser.add_argument(
        "--exercise-interruption",
        action="store_true",
        help="restart recovery targets while shard movement is in progress and record interruption phases",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    work_dir = Path(args.work_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    report_path = work_dir / "report.json"
    ports = reserve_unique_ports(6)
    java1_http, java1_transport, java2_http, java2_transport, rust_http, rust_transport = ports
    seeds = f"127.0.0.1:{java1_transport},127.0.0.1:{java2_transport},127.0.0.1:{rust_transport}"
    initial_managers = "java-primary-1,java-primary-2,rust-replica-1"

    java1_dir = work_dir / "java-primary-1"
    java2_dir = work_dir / "java-primary-2"
    rust_dir = work_dir / "rust-replica-1"
    for path in (java1_dir, java2_dir, rust_dir):
        path.mkdir(parents=True, exist_ok=True)

    java1_proc: subprocess.Popen[bytes] | None = None
    java2_proc: subprocess.Popen[bytes] | None = None
    rust_proc: subprocess.Popen[bytes] | None = None

    report: dict[str, Any] = {
        "work_dir": str(work_dir),
        "index": args.index,
        "doc_count": args.doc_count,
        "ports": {
            "java1_http": java1_http,
            "java1_transport": java1_transport,
            "java2_http": java2_http,
            "java2_transport": java2_transport,
            "rust_http": rust_http,
            "rust_transport": rust_transport,
        },
        "phases": [],
        "summary": {"passed": False},
    }
    java1_client: HttpJson | None = None
    java2_client: HttpJson | None = None

    try:
        java1_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            opensearch_dev_env(
                http_port=java1_http,
                transport_port=java1_transport,
                node_name="java-primary-1",
                seeds=seeds,
                initial_managers=initial_managers,
                work_dir=java1_dir,
            ),
            java1_dir / "stdout.log",
            java1_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java1_http}", attempts=120, sleep_seconds=1.0):
            raise RuntimeError("java-primary-1 did not start")

        java2_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            opensearch_dev_env(
                http_port=java2_http,
                transport_port=java2_transport,
                node_name="java-primary-2",
                seeds=seeds,
                initial_managers=initial_managers,
                work_dir=java2_dir,
            ),
            java2_dir / "stdout.log",
            java2_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java2_http}", attempts=120, sleep_seconds=1.0):
            raise RuntimeError("java-primary-2 did not start")

        seed_identities = [
            collect_seed_identity(work_dir, java1_transport, java1_http, "java-primary-1"),
            collect_seed_identity(work_dir, java2_transport, java2_http, "java-primary-2"),
        ]

        rust_proc = start_process(
            "bash tools/run-steelsearch-dev.sh",
            steelsearch_dev_env(
                rust_http=rust_http,
                rust_transport=rust_transport,
                seeds=seeds,
                rust_dir=rust_dir,
                seed_identities=seed_identities,
            ),
            rust_dir / "stdout.log",
            rust_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{rust_http}", attempts=120, sleep_seconds=1.0):
            raise RuntimeError("rust-replica-1 did not start")

        java1_client = HttpJson(f"http://127.0.0.1:{java1_http}")
        java2_client = HttpJson(f"http://127.0.0.1:{java2_http}")

        if not wait_for_node_count(java1_client, expected_count=3, attempts=45, sleep_seconds=1.0):
            raise RuntimeError(f"three-node mixed cluster did not form; java_view_node_count={current_node_count(java1_client)}")
        clear_opensearch_cluster_blocks(java1_client)
        report["phases"].append(phase_result("cluster_formed", node_count=current_node_count(java1_client)))

        java1_client.request("DELETE", f"/{args.index}?ignore_unavailable=true", expected={200, 404})
        java1_client.request(
            "PUT",
            f"/{args.index}",
            {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "routing": {"allocation": {"include": {"_name": "java-primary-1"}}},
                    }
                }
            },
            expected={200},
        )
        wait_for_index_health(java1_client, args.index, expected_status="green", attempts=120, sleep_seconds=1.0)
        for seq in range(args.doc_count):
            java1_client.request(
                "PUT",
                f"/{args.index}/_doc/doc-{seq}",
                {"seq": seq, "message": f"movement-doc-{seq}"},
                expected={200, 201},
            )
        java1_client.request("POST", f"/{args.index}/_refresh", expected={200})
        initial_shards = wait_for_shard_condition(
            java1_client,
            args.index,
            lambda rows: placement(rows)["primary_node"] == "java-primary-1",
        )
        report["phases"].append(
            phase_result(
                "initial_primary_on_java1",
                shards=initial_shards,
                placement=placement(initial_shards),
                search_count=get_search_count(java1_client, args.index),
            )
        )

        update_index_settings(
            java1_client,
            args.index,
            {
                "number_of_replicas": 1,
                "routing.allocation.include._name": "java-primary-1,rust-replica-1",
            },
        )
        if args.exercise_interruption:
            interrupted_shards = wait_for_shard_condition(
                java1_client,
                args.index,
                lambda rows: placement(rows)["primary_node"] == "java-primary-1"
                and placement(rows)["replica_node"] in {"rust-replica-1", None},
            )
            report["phases"].append(
                phase_result(
                    "interrupt_java_to_steelsearch_recovery",
                    shards=interrupted_shards,
                    placement=placement(interrupted_shards),
                    recovery=recovery_report(java1_client, args.index),
                    **checkpoint_report(java1_client, args.index),
                )
            )
            terminate_process(rust_proc)
            rust_proc = None

            rust_proc = start_process(
                "bash tools/run-steelsearch-dev.sh",
                steelsearch_dev_env(
                    rust_http=rust_http,
                    rust_transport=rust_transport,
                    seeds=seeds,
                    rust_dir=rust_dir,
                    seed_identities=seed_identities,
                ),
                rust_dir / "stdout.log",
                rust_dir / "stderr.log",
            )
            if not wait_for_http(f"http://127.0.0.1:{rust_http}", attempts=120, sleep_seconds=1.0):
                raise RuntimeError("rust-replica-1 did not restart after interrupted recovery")
            if not wait_for_node_count(java1_client, expected_count=3, attempts=45, sleep_seconds=1.0):
                raise RuntimeError(
                    "three-node cluster did not reform after interrupted Java-to-SteelSearch recovery"
                )
            resumed_shards = get_shards(java1_client, args.index)
            report["phases"].append(
                phase_result(
                    "resume_or_restart_java_to_steelsearch_recovery",
                    shards=resumed_shards,
                    placement=placement(resumed_shards),
                    recovery=recovery_report(java1_client, args.index),
                    search_count=get_search_count(java1_client, args.index),
                    **checkpoint_report(java1_client, args.index),
                )
            )

        green_on_java_rust = wait_for_index_health(java1_client, args.index, expected_status="green", attempts=180, sleep_seconds=1.0)
        java_to_rust_ready = wait_for_shard_condition(
            java1_client,
            args.index,
            lambda rows: placement(rows)["primary_node"] == "java-primary-1"
            and placement(rows)["replica_node"] == "rust-replica-1"
            and placement(rows)["replica_state"] == "STARTED",
        )
        report["phases"].append(
            phase_result(
                "replica_on_rust",
                cluster_health=green_on_java_rust,
                shards=java_to_rust_ready,
                placement=placement(java_to_rust_ready),
                search_count=get_search_count(java1_client, args.index),
                **checkpoint_report(java1_client, args.index),
            )
        )
        if args.exercise_interruption:
            report["phases"].append(
                phase_result(
                    "finalize_java_to_steelsearch_recovery",
                    cluster_health=green_on_java_rust,
                    shards=java_to_rust_ready,
                    placement=placement(java_to_rust_ready),
                    recovery=recovery_report(java1_client, args.index),
                    search_count=get_search_count(java1_client, args.index),
                    **checkpoint_report(java1_client, args.index),
                )
            )

        terminate_process(java1_proc)
        java1_proc = None
        failover_to_rust = wait_for_shard_condition(
            java2_client,
            args.index,
            lambda rows: placement(rows)["primary_node"] == "rust-replica-1"
            and placement(rows)["primary_state"] == "STARTED",
        )
        rust_primary_count = get_search_count(java2_client, args.index)
        report["phases"].append(
            phase_result(
                "opensearch_to_steelsearch",
                shards=failover_to_rust,
                placement=placement(failover_to_rust),
                search_count=rust_primary_count,
                **checkpoint_report(java2_client, args.index),
                passed=rust_primary_count == args.doc_count,
            )
        )

        java1_proc = start_process(
            "bash tools/run-opensearch-dev.sh",
            opensearch_dev_env(
                http_port=java1_http,
                transport_port=java1_transport,
                node_name="java-primary-1",
                seeds=seeds,
                initial_managers=initial_managers,
                work_dir=java1_dir,
            ),
            java1_dir / "stdout.log",
            java1_dir / "stderr.log",
        )
        if not wait_for_http(f"http://127.0.0.1:{java1_http}", attempts=120, sleep_seconds=1.0):
            raise RuntimeError("java-primary-1 did not restart")
        if not wait_for_node_count(java2_client, expected_count=3, attempts=45, sleep_seconds=1.0):
            raise RuntimeError(f"three-node cluster did not reform after java1 restart; java_view_node_count={current_node_count(java2_client)}")
        if args.exercise_interruption:
            interrupted_shards = get_shards(java2_client, args.index)
            report["phases"].append(
                phase_result(
                    "interrupt_steelsearch_to_opensearch_recovery",
                    shards=interrupted_shards,
                    placement=placement(interrupted_shards),
                    recovery=recovery_report(java2_client, args.index),
                    **checkpoint_report(java2_client, args.index),
                )
            )
            terminate_process(java1_proc)
            java1_proc = None

            java1_proc = start_process(
                "bash tools/run-opensearch-dev.sh",
                opensearch_dev_env(
                    http_port=java1_http,
                    transport_port=java1_transport,
                    node_name="java-primary-1",
                    seeds=seeds,
                    initial_managers=initial_managers,
                    work_dir=java1_dir,
                ),
                java1_dir / "stdout.log",
                java1_dir / "stderr.log",
            )
            if not wait_for_http(f"http://127.0.0.1:{java1_http}", attempts=120, sleep_seconds=1.0):
                raise RuntimeError("java-primary-1 did not restart after interrupted recovery")
            if not wait_for_node_count(java2_client, expected_count=3, attempts=45, sleep_seconds=1.0):
                raise RuntimeError(
                    "three-node cluster did not reform after interrupted SteelSearch-to-OpenSearch recovery"
                )
            resumed_shards = get_shards(java2_client, args.index)
            report["phases"].append(
                phase_result(
                    "resume_or_restart_steelsearch_to_opensearch_recovery",
                    shards=resumed_shards,
                    placement=placement(resumed_shards),
                    recovery=recovery_report(java2_client, args.index),
                    search_count=get_search_count(java2_client, args.index),
                    **checkpoint_report(java2_client, args.index),
                )
            )
        green_on_rust_java = wait_for_index_health(java2_client, args.index, expected_status="green", attempts=180, sleep_seconds=1.0)
        rust_primary_java_replica = wait_for_shard_condition(
            java2_client,
            args.index,
            lambda rows: placement(rows)["primary_node"] == "rust-replica-1"
            and placement(rows)["replica_node"] == "java-primary-1"
            and placement(rows)["replica_state"] == "STARTED",
        )
        report["phases"].append(
            phase_result(
                "java1_rejoined_as_replica",
                cluster_health=green_on_rust_java,
                shards=rust_primary_java_replica,
                placement=placement(rust_primary_java_replica),
                search_count=get_search_count(java2_client, args.index),
                **checkpoint_report(java2_client, args.index),
            )
        )
        if args.exercise_interruption:
            report["phases"].append(
                phase_result(
                    "finalize_steelsearch_to_opensearch_recovery",
                    cluster_health=green_on_rust_java,
                    shards=rust_primary_java_replica,
                    placement=placement(rust_primary_java_replica),
                    recovery=recovery_report(java2_client, args.index),
                    search_count=get_search_count(java2_client, args.index),
                    **checkpoint_report(java2_client, args.index),
                )
            )

        terminate_process(rust_proc)
        rust_proc = None
        failover_to_java = wait_for_shard_condition(
            java2_client,
            args.index,
            lambda rows: placement(rows)["primary_node"] == "java-primary-1"
            and placement(rows)["primary_state"] == "STARTED",
        )
        java_primary_count = get_search_count(java2_client, args.index)
        report["phases"].append(
            phase_result(
                "steelsearch_to_opensearch",
                shards=failover_to_java,
                placement=placement(failover_to_java),
                search_count=java_primary_count,
                **checkpoint_report(java2_client, args.index),
                passed=java_primary_count == args.doc_count,
            )
        )

        report["summary"] = summarize_movement_report(
            report, require_interruption=args.require_interruption
        )
    except Exception as exc:
        report["failure_context"] = {
            "java1_nodes": None if java1_client is None else safe_request(java1_client, "GET", "/_cat/nodes?format=json"),
            "java2_nodes": None if java2_client is None else safe_request(java2_client, "GET", "/_cat/nodes?format=json"),
            "java1_cluster_health": (
                None
                if java1_client is None
                else safe_request(
                    java1_client,
                    "GET",
                    f"/_cluster/health/{urllib.parse.quote(args.index, safe='')}",
                )
            ),
            "java2_cluster_health": (
                None
                if java2_client is None
                else safe_request(
                    java2_client,
                    "GET",
                    f"/_cluster/health/{urllib.parse.quote(args.index, safe='')}",
                )
            ),
            "java1_shards": (
                None
                if java1_client is None
                else safe_request(
                    java1_client,
                    "GET",
                    f"/_cat/shards/{urllib.parse.quote(args.index, safe='')}?format=json",
                )
            ),
            "java2_shards": (
                None
                if java2_client is None
                else safe_request(
                    java2_client,
                    "GET",
                    f"/_cat/shards/{urllib.parse.quote(args.index, safe='')}?format=json",
                )
            ),
            "java1_allocation_explain": (
                None
                if java1_client is None
                else safe_request(java1_client, "GET", "/_cluster/allocation/explain", {})
            ),
            "java2_allocation_explain": (
                None
                if java2_client is None
                else safe_request(java2_client, "GET", "/_cluster/allocation/explain", {})
            ),
            "java1_recovery": (
                None
                if java1_client is None
                else safe_request(
                    java1_client,
                    "GET",
                    f"/{urllib.parse.quote(args.index, safe='')}/_recovery",
                )
            ),
            "java2_recovery": (
                None
                if java2_client is None
                else safe_request(
                    java2_client,
                    "GET",
                    f"/{urllib.parse.quote(args.index, safe='')}/_recovery",
                )
            ),
            "rust_membership": (
                read_json(rust_dir / "data" / "production-membership.json")
                if (rust_dir / "data" / "production-membership.json").exists()
                else None
            ),
            "rust_gateway_state": (
                read_json(rust_dir / "data" / "gateway-state.json")
                if (rust_dir / "data" / "gateway-state.json").exists()
                else None
            ),
        }
        report["summary"] = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1
    finally:
        for proc in (rust_proc, java2_proc, java1_proc):
            if proc is not None:
                try:
                    terminate_process(proc)
                except Exception:
                    pass

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
