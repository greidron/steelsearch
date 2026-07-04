import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NODE_RUNTIME_COMPONENTS = (
    ROOT / "docs" / "rust-port" / "generated" / "source-node-runtime-components.tsv"
)


class SourceNodeRuntimeComponentsTests(unittest.TestCase):
    def _rows(self):
        with SOURCE_NODE_RUNTIME_COMPONENTS.open(newline="", encoding="utf-8") as source_file:
            return list(csv.DictReader(source_file, delimiter="\t"))

    def _status_for_component(self, component):
        matches = [row for row in self._rows() if row["component"] == component]
        self.assertEqual(len(matches), 1, component)
        return matches[0]["status"]

    def test_runtime_backed_node_components_are_implemented_not_planned(self):
        implemented = [
            "ActionModule",
            "ClusterService",
            "ConsistentSettingsService",
            "GatewayModule",
            "HierarchyCircuitBreakerService",
            "IdentityService",
            "IngestService",
            "IndicesService",
            "NamedWriteableRegistry",
            "NetworkModule",
            "NetworkService",
            "PersistentTasksService",
            "PluginsService",
            "RemoteStoreNodeService",
            "RemoteClusterStateService",
            "RepositoriesModule",
            "RemoteStorePinnedTimestampService",
            "ResourceWatcherService",
            "ScriptService",
            "SearchService",
            "SearchTransportService",
            "SnapshotsService",
            "SystemTemplatesService",
            "TaskCancellationService",
            "TaskResourceTrackingService",
            "TransportService",
            "PeerRecoverySourceService",
            "PeerRecoveryTargetService",
            "SegmentReplicationTargetService",
            "SegmentReplicationSourceService",
            "DiscoveryModule",
            "WorkloadGroupTaskCancellationService",
            "WorkloadGroupResourceUsageTrackerService",
            "WorkloadGroupService",
        ]
        for component in implemented:
            self.assertEqual(
                self._status_for_component(component),
                "implemented",
                component,
            )

    def test_no_node_components_remain_planned(self):
        planned = [
            row["component"] for row in self._rows() if row["status"] == "planned"
        ]
        self.assertEqual(planned, [])


if __name__ == "__main__":
    unittest.main()
