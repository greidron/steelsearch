#!/usr/bin/env python3
"""Check source-derived Node runtime partials have Steelsearch boundary owners."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_NODE_RUNTIME = ROOT / "docs/rust-port/generated/source-node-runtime-components.tsv"
DEFAULT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"

BOUNDARY_OWNERS = {
    "ActionModule": "transport_action_registry plus REST dispatch table",
    "AdmissionControlService": "runtime_task_queue admission gates",
    "AnalysisModule": "analysis route and analyzer settings boundary",
    "BatchedRerouteService": "cluster_reroute_state plus runtime task queue",
    "CacheModule": "request and query cache telemetry boundary",
    "ClusterModule": "cluster state and cluster-manager route boundary",
    "ClusterService": "cluster_state_store plus publication boundary",
    "ConsistentSettingsService": "cluster_settings_state",
    "DataFormatRegistry": "content negotiation and JSON compatibility codecs",
    "DiscoveryModule": "DiscoveryConfig plus production membership store",
    "FsHealthService": "startup data-path preflight and resource watcher state",
    "GatewayModule": "gateway manifest and cluster metadata persistence boundary",
    "HierarchyCircuitBreakerService": "runtime memory accounting counters",
    "IdentityService": "NodeInfo plus security subject boundary",
    "IndexingPressureService": "runtime indexing pressure counters",
    "IndicesModule": "index metadata, mapping, template, and data stream route boundary",
    "IndicesService": "index catalog state plus shard routing view",
    "IngestService": "ingest pipeline route and simulation boundary",
    "InternalClusterInfoService": "cluster info and allocation stats state",
    "InternalSnapshotsInfoService": "snapshot metadata inventory state",
    "LocalClusterService": "local cluster view and membership state",
    "MappingTransformerRegistry": "mapping transformer registry boundary",
    "MetadataCreateDataStreamService": "data stream metadata state",
    "MetadataCreateIndexService": "index creation metadata state",
    "MetadataIndexUpgradeService": "index metadata upgrade route boundary",
    "MetaStateService": "metadata manifest persistence boundary",
    "MonitorService": "node stats and usage route state",
    "NamedWriteableRegistry": "transport named writeable codec registry",
    "NamedXContentRegistry": "REST named content parser registry",
    "NetworkModule": "RestServerConfig and transport discovery config",
    "NetworkService": "HTTP and transport bind preflight boundary",
    "NodeService": "node info, stats, and usage route boundary",
    "NoneCircuitBreakerService": "disabled breaker policy boundary",
    "PeerRecoverySourceService": "mixed-cluster peer recovery admission plus task queue state",
    "PeerRecoveryTargetService": "mixed-cluster peer recovery admission plus task queue state",
    "PersistedClusterStateService": "cluster metadata manifest persistence boundary",
    "PersistedStateRegistry": "persisted cluster state registry boundary",
    "PersistentTasksClusterService": "persistent task cluster-state projection",
    "PersistentTasksExecutorRegistry": "persistent task executor registry boundary",
    "PersistentTasksService": "persistent task lifecycle state",
    "PluginsService": "ExtensionBoundaryRegistry",
    "RemoteClusterStateService": "remote_cluster_state_sync_state plus publication apply",
    "RemoteStoreNodeService": "remote store transport bridge plus recovery manifest state",
    "RemoteStorePinnedTimestampService": "remote_store_pinned_timestamp_state plus recovery source decode",
    "RemoteStoreRestoreService": "remote store restore manifest state",
    "RepositoriesModule": "repository metadata route boundary",
    "ResourceUsageCollectorService": "runtime resource usage collector state",
    "ResourceWatcherService": "resource_watcher_state",
    "ResponseCollectorService": "search response collector telemetry boundary",
    "RestoreService": "snapshot restore metadata state",
    "ScriptModule": "script route and script-context boundary",
    "ScriptService": "stored script state plus script execution policy",
    "SearchBackpressureService": "search runtime queue and rejection counters",
    "SearchModule": "query, aggregation, fetch, and search extension point contracts",
    "SearchPhaseController": "search phase reduce and pagination boundary",
    "SearchPipelineService": "search pipeline metadata state",
    "SearchService": "search execution, PIT, scroll, and cache boundary",
    "SearchTransportService": "query-phase transport route admission boundary",
    "SegmentReplicationSourceService": "segment replication stats transport boundary",
    "SegmentReplicationTargetService": "segment replication stats transport boundary",
    "SettingsModule": "daemon config and cluster settings boundary",
    "SnapshotShardsService": "snapshot shard metadata state",
    "SnapshotsService": "snapshot lifecycle metadata state",
    "StreamSearchTransportService": "stream search transport route boundary",
    "StreamTransportService": "stream transport service boundary",
    "SystemIndexMetadataUpgradeService": "system index metadata upgrade boundary",
    "SystemTemplatesService": "system_template_catalog_state plus template manifest",
    "TaskCancellationMonitoringService": "task cancellation monitoring state",
    "TaskCancellationService": "task cancellation route and runtime state",
    "TaskResourceTrackingService": "runtime task accounting state",
    "TelemetryModule": "node stats, usage, and runtime telemetry boundary",
    "TemplateUpgradeService": "template upgrade manifest boundary",
    "TransportService": "TCP transport listener and frame dispatch boundary",
    "UsageService": "usage route and feature usage state",
    "ViewService": "view metadata route boundary",
    "WorkloadGroupResourceUsageTrackerService": "workload group resource usage state",
    "WorkloadGroupService": "workload group metadata state",
    "WorkloadGroupTaskCancellationService": "workload group state plus task cancellation state",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-node-runtime",
        type=Path,
        default=DEFAULT_SOURCE_NODE_RUNTIME,
    )
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def load_source_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def runtime_boundary_components(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r'opensearch_component:\s*"([^"]+)"', text))


def check_contracts(source_node_runtime: Path, runtime_source: Path) -> dict[str, object]:
    rows = load_source_rows(source_node_runtime)
    partial_components = {row["component"] for row in rows if row["status"] == "partial"}
    non_partial_rows = [
        {
            "component": row["component"],
            "status": row["status"],
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
        if row["status"] != "partial"
    ]
    owner_components = set(BOUNDARY_OWNERS)
    missing_owner_components = sorted(partial_components - owner_components)
    stale_owner_components = sorted(owner_components - partial_components)
    code_visible_components = runtime_boundary_components(runtime_source)
    code_visible_missing_from_source = sorted(code_visible_components - partial_components)
    code_visible_missing_owner = sorted(code_visible_components - owner_components)

    errors = []
    if non_partial_rows:
        errors.append(f"node runtime rows are not partial: {non_partial_rows[:10]}")
    if missing_owner_components:
        errors.append(f"partial node runtime components missing owners: {missing_owner_components[:10]}")
    if stale_owner_components:
        errors.append(f"stale node runtime owner mappings: {stale_owner_components[:10]}")
    if code_visible_missing_from_source:
        errors.append(
            f"runtime boundary components missing from source inventory: {code_visible_missing_from_source[:10]}"
        )
    if code_visible_missing_owner:
        errors.append(
            f"runtime boundary components missing owner mappings: {code_visible_missing_owner[:10]}"
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "source_node_runtime_count": len(rows),
            "partial_component_count": len(partial_components),
            "owner_mapping_count": len(owner_components),
            "code_visible_boundary_count": len(code_visible_components),
            "non_partial_row_count": len(non_partial_rows),
            "missing_owner_count": len(missing_owner_components),
            "stale_owner_count": len(stale_owner_components),
            "code_visible_missing_from_source_count": len(code_visible_missing_from_source),
            "code_visible_missing_owner_count": len(code_visible_missing_owner),
        },
    }


def main() -> int:
    args = parse_args()
    result = check_contracts(args.source_node_runtime, args.runtime_source)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
