"""Collect bounded, secret-filtered runtime observations outside load timing."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from benchmark_cgroup_evidence import observe_cgroup


ENVIRONMENT_KEYS = (
    "STEELSEARCH_PERSIST_SHARED_RUNTIME_STATE_PER_WRITE",
    "STEELSEARCH_SYNC_SHARED_RUNTIME_STATE_PER_REQUEST",
    "STEELSEARCH_DEFER_DEVELOPMENT_SHARD_PERSIST_PER_WRITE",
    "STEELSEARCH_DEFER_NATIVE_WRITE_UNTIL_REFRESH",
    "STEELSEARCH_MODE", "STEELSEARCH_SECURITY_ENABLED",
    "STEELSEARCH_DEVELOPMENT_SECURITY_MODE",
    "STEELSEARCH_ENABLE_KNN_PLUGIN", "STEELSEARCH_ENABLE_ML_COMMONS",
)
CLI_KEYS = ("--mode", "--development.security_mode", "--extensions.knn", "--extensions.ml_commons")
DOCKER_KEYS = ("DISABLE_SECURITY_PLUGIN", "DISABLE_INSTALL_DEMO_CONFIG")
CPU_FIELDS = ("user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal", "guest", "guest_nice")


def parse_host_cpu_ticks(line):
    fields = line.split()
    if not fields or fields[0] != "cpu" or not 8 <= len(fields) - 1 <= len(CPU_FIELDS):
        raise ValueError("unsupported aggregate CPU counter shape")
    if any(not value.isascii() or not value.isdecimal() for value in fields[1:]):
        raise ValueError("invalid aggregate CPU counter")
    return dict(zip(CPU_FIELDS, map(int, fields[1:])))


def observe_host_cpu(proc_root=Path("/proc")):
    result = {"started_at_epoch": time.time(),
              "scope": "visible host aggregate, not exclusive to benchmark; guest ticks overlap user/nice; iowait may decrease"}
    try:
        with (proc_root / "stat").open() as stream:
            ticks = parse_host_cpu_ticks(stream.readline())
        frequency = os.sysconf("SC_CLK_TCK")
        if frequency <= 0:
            raise ValueError("invalid CPU counter frequency")
        result.update(cpu_ticks=ticks, clock_ticks_per_second=frequency)
    except (OSError, ValueError) as error:
        result.update(cpu_ticks=None, clock_ticks_per_second=None, error=type(error).__name__)
    try:
        result["boot_id"] = (proc_root / "sys/kernel/random/boot_id").read_text().strip()
    except OSError as error:
        result.update(boot_id=None, boot_id_error=type(error).__name__)
    result["finished_at_epoch"] = time.time()
    return result


def selected_environment(entries, keys):
    values = {}
    for entry in entries:
        key, separator, value = entry.partition("=")
        if separator and key in keys:
            if key in values:
                raise ValueError(f"duplicate runtime environment key: {key}")
            values[key] = value
    return {key: values.get(key) for key in keys}


def process_start(path):
    return int((path / "stat").read_text().rsplit(") ", 1)[1].split()[19])


def observe_process(pid, expected_sha256, proc_root=Path("/proc")):
    path = proc_root / str(pid)
    start = process_start(path)
    with (path / "exe").open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    if sha256 != expected_sha256:
        raise ValueError("live process executable differs from selected binary")
    environment = (path / "environ").read_bytes().decode("utf-8").split("\0")
    arguments = (path / "cmdline").read_bytes().decode("utf-8").split("\0")
    options = {}
    for position, arg in enumerate(arguments):
        if arg in CLI_KEYS:
            if arg in options or position + 1 >= len(arguments) or not arguments[position + 1]:
                raise ValueError("ambiguous selected runtime option")
            options[arg] = arguments[position + 1]
    status = {}
    for line in (path / "status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in ("Cpus_allowed_list", "Mems_allowed_list"):
            status[key] = value.strip()
    result = {
        "pid": pid, "start_ticks": start, "sha256": sha256,
        "environment": selected_environment(environment, ENVIRONMENT_KEYS),
        "selected_cli_options": options, "affinity": status,
        "limits": (path / "limits").read_text(),
        "cgroup_membership": (path / "cgroup").read_text(),
    }
    if process_start(path) != start:
        raise ValueError("process changed while runtime evidence was collected")
    return result


def observe_containers(names):
    raw = subprocess.check_output(["docker", "inspect", *names], text=True)
    inspected = json.loads(raw)
    if len(inspected) != len(names):
        raise ValueError("container count differs")
    result = []
    for name, item in zip(names, inspected):
        if item["Name"].lstrip("/") != name or not item["State"]["Running"]:
            raise ValueError("expected live container identity missing")
        environment = item["Config"]["Env"]
        # Heap flags only: JAVA_OPTS may contain credentials or unrelated secrets.
        java = selected_environment(environment, ("OPENSEARCH_JAVA_OPTS",))["OPENSEARCH_JAVA_OPTS"]
        heap = [flag for flag in (java or "").split() if flag.startswith(("-Xms", "-Xmx"))]
        result.append({
            "name": name, "id": item["Id"], "image_id": item["Image"],
            "pid": item["State"]["Pid"], "started_at": item["State"]["StartedAt"],
            "restart_count": item["RestartCount"],
            "environment": selected_environment(environment, DOCKER_KEYS),
            "requested_heap_flags": heap,
            "limits": {key: item["HostConfig"].get(key) for key in (
                "Memory", "MemorySwap", "NanoCpus", "CpuQuota", "CpuPeriod", "CpusetCpus", "CpusetMems")},
        })
    return result


def capture_runtime(pids, container_names, expected_sha256, node_count):
    if container_names:
        if len(container_names) != node_count or len(set(container_names)) != node_count:
            raise ValueError("expected distinct containers for every node")
        nodes = observe_containers(container_names)
        engine = "opensearch"
    else:
        if len(pids) != node_count or len(set(pids)) != node_count:
            raise ValueError("expected distinct live processes for every node")
        nodes = [observe_process(pid, expected_sha256) for pid in pids]
        engine = "steelsearch"
    counters = []
    for node in nodes:
        start = process_start(Path("/proc") / str(node["pid"]))
        node["cgroup"], observed = observe_cgroup(node["pid"])
        if process_start(Path("/proc") / str(node["pid"])) != start:
            raise ValueError("process changed during cgroup observation")
        if engine == "steelsearch" and node["start_ticks"] != start:
            raise ValueError("process changed before cgroup observation")
        if engine == "steelsearch" and node["cgroup_membership"] != node["cgroup"]["membership"]:
            raise ValueError("process moved before cgroup observation")
        node["start_ticks"] = start
        counters.append({"pid": node["pid"], "levels": observed})
    host_cpu = observe_host_cpu()
    return {"captured_at_epoch": time.time(), "engine": engine, "nodes": nodes,
            "resource_counters": counters,
            "host_cpu": host_cpu,
            "scope": "observed settings and visible cgroup constraints; effective resource availability and application enforcement not verified"}


def require_stable_runtime(before, after):
    if before["engine"] != after["engine"] or before["nodes"] != after["nodes"]:
        raise ValueError("runtime identity or selected settings changed during benchmark")
