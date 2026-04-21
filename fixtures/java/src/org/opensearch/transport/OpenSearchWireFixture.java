package org.opensearch.transport;

import org.opensearch.Version;
import org.opensearch.action.admin.indices.rollover.Condition;
import org.opensearch.action.admin.indices.rollover.MaxAgeCondition;
import org.opensearch.action.admin.indices.rollover.MaxDocsCondition;
import org.opensearch.action.admin.indices.rollover.MaxSizeCondition;
import org.opensearch.action.admin.indices.rollover.RolloverInfo;
import org.opensearch.action.admin.cluster.state.ClusterStateAction;
import org.opensearch.action.admin.cluster.state.ClusterStateRequest;
import org.opensearch.action.admin.cluster.state.ClusterStateResponse;
import org.opensearch.cluster.ClusterName;
import org.opensearch.cluster.RepositoryCleanupInProgress;
import org.opensearch.cluster.RestoreInProgress;
import org.opensearch.cluster.SnapshotDeletionsInProgress;
import org.opensearch.cluster.SnapshotsInProgress;
import org.opensearch.cluster.ClusterState;
import org.opensearch.cluster.block.ClusterBlock;
import org.opensearch.cluster.block.ClusterBlockLevel;
import org.opensearch.cluster.block.ClusterBlocks;
import org.opensearch.cluster.decommission.DecommissionAttribute;
import org.opensearch.cluster.decommission.DecommissionAttributeMetadata;
import org.opensearch.cluster.decommission.DecommissionStatus;
import org.opensearch.cluster.metadata.AliasMetadata;
import org.opensearch.cluster.metadata.ComposableIndexTemplate;
import org.opensearch.cluster.metadata.ComposableIndexTemplateMetadata;
import org.opensearch.cluster.metadata.ComponentTemplate;
import org.opensearch.cluster.metadata.ComponentTemplateMetadata;
import org.opensearch.cluster.metadata.Context;
import org.opensearch.cluster.metadata.CryptoMetadata;
import org.opensearch.cluster.metadata.DataStream;
import org.opensearch.cluster.metadata.DataStreamMetadata;
import org.opensearch.cluster.metadata.IndexMetadata;
import org.opensearch.cluster.metadata.IndexTemplateMetadata;
import org.opensearch.cluster.metadata.IndexGraveyard;
import org.opensearch.cluster.metadata.Metadata;
import org.opensearch.cluster.metadata.RepositoriesMetadata;
import org.opensearch.cluster.metadata.RepositoryMetadata;
import org.opensearch.cluster.metadata.SplitShardsMetadata;
import org.opensearch.cluster.metadata.Template;
import org.opensearch.cluster.metadata.View;
import org.opensearch.cluster.metadata.ViewMetadata;
import org.opensearch.cluster.metadata.WeightedRoutingMetadata;
import org.opensearch.cluster.metadata.WorkloadGroup;
import org.opensearch.cluster.metadata.WorkloadGroupMetadata;
import org.opensearch.cluster.node.DiscoveryNode;
import org.opensearch.cluster.node.DiscoveryNodeRole;
import org.opensearch.cluster.node.DiscoveryNodes;
import org.opensearch.cluster.routing.IndexShardRoutingTable;
import org.opensearch.cluster.routing.IndexRoutingTable;
import org.opensearch.cluster.routing.RecoverySource;
import org.opensearch.cluster.routing.RoutingTable;
import org.opensearch.cluster.routing.ShardRouting;
import org.opensearch.cluster.routing.UnassignedInfo;
import org.opensearch.cluster.routing.WeightedRouting;
import org.opensearch.common.io.stream.BytesStreamOutput;
import org.opensearch.common.compress.CompressedXContent;
import org.opensearch.common.settings.Settings;
import org.opensearch.common.unit.TimeValue;
import org.opensearch.common.util.concurrent.ThreadContext;
import org.opensearch.core.common.bytes.BytesReference;
import org.opensearch.core.common.bytes.BytesArray;
import org.opensearch.core.common.transport.TransportAddress;
import org.opensearch.core.common.io.stream.StreamOutput;
import org.opensearch.core.common.unit.ByteSizeValue;
import org.opensearch.core.index.Index;
import org.opensearch.core.index.shard.ShardId;
import org.opensearch.core.rest.RestStatus;
import org.opensearch.core.xcontent.XContentBuilder;
import org.opensearch.core.xcontent.MediaTypeRegistry;
import org.opensearch.ingest.IngestMetadata;
import org.opensearch.ingest.PipelineConfiguration;
import org.opensearch.persistent.PersistentTaskParams;
import org.opensearch.persistent.PersistentTaskState;
import org.opensearch.persistent.PersistentTasksCustomMetadata;
import org.opensearch.repositories.IndexId;
import org.opensearch.repositories.RepositoryShardId;
import org.opensearch.search.pipeline.SearchPipelineMetadata;
import org.opensearch.script.ScriptMetadata;
import org.opensearch.script.StoredScriptSource;
import org.opensearch.snapshots.Snapshot;
import org.opensearch.snapshots.SnapshotId;
import org.opensearch.wlm.MutableWorkloadGroupFragment;
import org.opensearch.wlm.ResourceType;

import java.io.IOException;
import java.net.InetAddress;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.Date;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.Map;

public final class OpenSearchWireFixture {
    private static final Base64.Encoder BASE64 = Base64.getEncoder();

    public static void main(String[] args) throws Exception {
        emit("string_steelsearch_search", serializeString("steelsearch 검색"));
        emit("string_array_features", serializeStringArray(new String[] { "feature-a", "feature-b" }));
        emit(
            "variable_header_request",
            serializeVariableHeader("internal:transport/handshake", new String[] { "feature-a", "feature-b" })
        );
        emit("tcp_handshake_request", serializeTcpHandshakeRequest(1L));
        emit("transport_handshake_request", serializeTransportHandshakeRequest(2L));
        emit("cluster_state_request_default", serializeClusterStateRequestDefault());
        emit("cluster_state_transport_request_default", serializeClusterStateTransportRequestDefault(3L));
        emit("cluster_state_response_minimal", serializeClusterStateResponseMinimal());
        emit("cluster_state_publication_diff_empty", serializeClusterStatePublicationDiffEmpty());
        emit(
            "cluster_state_publication_diff_delete_custom",
            serializeClusterStatePublicationDiffDeleteCustom()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom",
            serializeClusterStatePublicationDiffUpsertCustom()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom_snapshots_entry",
            serializeClusterStatePublicationDiffUpsertCustomSnapshotsEntry()
        );
        emit(
            "cluster_state_publication_diff_named_custom_snapshots_shard_status",
            serializeClusterStatePublicationDiffNamedCustomSnapshotsShardStatus()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom_restore",
            serializeClusterStatePublicationDiffUpsertCustomRestore()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom_restore_shard_status",
            serializeClusterStatePublicationDiffUpsertCustomRestoreShardStatus()
        );
        emit(
            "cluster_state_publication_diff_named_custom_restore_shard_status",
            serializeClusterStatePublicationDiffNamedCustomRestoreShardStatus()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom_snapshot_deletions",
            serializeClusterStatePublicationDiffUpsertCustomSnapshotDeletions()
        );
        emit(
            "cluster_state_publication_diff_named_custom_snapshot_deletions",
            serializeClusterStatePublicationDiffNamedCustomSnapshotDeletions()
        );
        emit(
            "cluster_state_publication_diff_upsert_custom_repository_cleanup",
            serializeClusterStatePublicationDiffUpsertCustomRepositoryCleanup()
        );
        emit(
            "cluster_state_publication_diff_named_custom_repository_cleanup",
            serializeClusterStatePublicationDiffNamedCustomRepositoryCleanup()
        );
        emit(
            "cluster_state_publication_diff_delete_routing_index",
            serializeClusterStatePublicationDiffDeleteRoutingIndex()
        );
        emit(
            "cluster_state_publication_diff_delete_metadata_index",
            serializeClusterStatePublicationDiffDeleteMetadataIndex()
        );
        emit(
            "cluster_state_publication_diff_delete_metadata_template",
            serializeClusterStatePublicationDiffDeleteMetadataTemplate()
        );
        emit(
            "cluster_state_publication_diff_delete_metadata_custom",
            serializeClusterStatePublicationDiffDeleteMetadataCustom()
        );
        emit(
            "cluster_state_publication_diff_delete_consistent_setting_hash",
            serializeClusterStatePublicationDiffDeleteConsistentSettingHash()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_index",
            serializeClusterStatePublicationDiffUpsertMetadataIndex()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index",
            serializeClusterStatePublicationDiffNamedMetadataIndex()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_mapping",
            serializeClusterStatePublicationDiffNamedMetadataIndexMapping()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_alias",
            serializeClusterStatePublicationDiffNamedMetadataIndexAlias()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_custom_data",
            serializeClusterStatePublicationDiffNamedMetadataIndexCustomData()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_rollover",
            serializeClusterStatePublicationDiffNamedMetadataIndexRollover()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_in_sync",
            serializeClusterStatePublicationDiffNamedMetadataIndexInSync()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_index_split_shards",
            serializeClusterStatePublicationDiffNamedMetadataIndexSplitShards()
        );
        emit(
            "cluster_state_publication_diff_upsert_routing_index",
            serializeClusterStatePublicationDiffUpsertRoutingIndex()
        );
        emit(
            "cluster_state_publication_diff_named_routing_index",
            serializeClusterStatePublicationDiffNamedRoutingIndex()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_template",
            serializeClusterStatePublicationDiffUpsertMetadataTemplate()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_template",
            serializeClusterStatePublicationDiffNamedMetadataTemplate()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_template_mapping_alias",
            serializeClusterStatePublicationDiffNamedMetadataTemplateMappingAlias()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom",
            serializeClusterStatePublicationDiffUpsertMetadataCustom()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_repositories",
            serializeClusterStatePublicationDiffNamedMetadataCustomRepositories()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_component_template",
            serializeClusterStatePublicationDiffUpsertMetadataCustomComponentTemplate()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_index_template",
            serializeClusterStatePublicationDiffUpsertMetadataCustomIndexTemplate()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_data_stream",
            serializeClusterStatePublicationDiffUpsertMetadataCustomDataStream()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_ingest",
            serializeClusterStatePublicationDiffUpsertMetadataCustomIngest()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_search_pipeline",
            serializeClusterStatePublicationDiffUpsertMetadataCustomSearchPipeline()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_stored_scripts",
            serializeClusterStatePublicationDiffUpsertMetadataCustomStoredScripts()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_index_graveyard",
            serializeClusterStatePublicationDiffUpsertMetadataCustomIndexGraveyard()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_persistent_tasks",
            serializeClusterStatePublicationDiffUpsertMetadataCustomPersistentTasks()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_decommission",
            serializeClusterStatePublicationDiffUpsertMetadataCustomDecommission()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_decommission",
            serializeClusterStatePublicationDiffNamedMetadataCustomDecommission()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_weighted_routing",
            serializeClusterStatePublicationDiffUpsertMetadataCustomWeightedRouting()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_weighted_routing",
            serializeClusterStatePublicationDiffNamedMetadataCustomWeightedRouting()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_view",
            serializeClusterStatePublicationDiffUpsertMetadataCustomView()
        );
        emit(
            "cluster_state_publication_diff_upsert_metadata_custom_workload_group",
            serializeClusterStatePublicationDiffUpsertMetadataCustomWorkloadGroup()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_view",
            serializeClusterStatePublicationDiffNamedMetadataCustomView()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_workload_group",
            serializeClusterStatePublicationDiffNamedMetadataCustomWorkloadGroup()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_data_stream",
            serializeClusterStatePublicationDiffNamedMetadataCustomDataStream()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_component_template",
            serializeClusterStatePublicationDiffNamedMetadataCustomComponentTemplate()
        );
        emit(
            "cluster_state_publication_diff_named_metadata_custom_index_template",
            serializeClusterStatePublicationDiffNamedMetadataCustomIndexTemplate()
        );
        emit("cluster_state_response_repository_cleanup_custom", serializeClusterStateResponseRepositoryCleanupCustom());
        emit("cluster_state_response_snapshot_deletions_custom", serializeClusterStateResponseSnapshotDeletionsCustom());
        emit("cluster_state_response_restore_custom", serializeClusterStateResponseRestoreCustom());
        emit("cluster_state_response_restore_custom_shard_status", serializeClusterStateResponseRestoreCustomShardStatus());
        emit("cluster_state_response_snapshots_custom", serializeClusterStateResponseSnapshotsCustom());
        emit("cluster_state_response_snapshots_custom_shard_status", serializeClusterStateResponseSnapshotsCustomShardStatus());
        emit("cluster_state_response_snapshots_custom_clone", serializeClusterStateResponseSnapshotsCustomClone());
        emit("cluster_state_response_snapshots_custom_user_metadata", serializeClusterStateResponseSnapshotsCustomUserMetadata());
        emit("cluster_state_response_single_node", serializeClusterStateResponseSingleNode());
        emit("cluster_state_response_global_block", serializeClusterStateResponseGlobalBlock());
        emit("cluster_state_response_index_block", serializeClusterStateResponseIndexBlock());
        emit("cluster_state_response_metadata_settings", serializeClusterStateResponseMetadataSettings());
        emit("cluster_state_response_consistent_setting_hashes", serializeClusterStateResponseConsistentSettingHashes());
        emit("cluster_state_response_index_graveyard_tombstone", serializeClusterStateResponseIndexGraveyardTombstone());
        emit("cluster_state_response_component_template", serializeClusterStateResponseComponentTemplate());
        emit(
            "cluster_state_response_component_template_mapping_alias",
            serializeClusterStateResponseComponentTemplateMappingAlias()
        );
        emit(
            "cluster_state_response_component_template_metadata",
            serializeClusterStateResponseComponentTemplateMetadata()
        );
        emit(
            "cluster_state_response_composable_index_template",
            serializeClusterStateResponseComposableIndexTemplate()
        );
        emit(
            "cluster_state_response_composable_index_template_mapping_alias",
            serializeClusterStateResponseComposableIndexTemplateMappingAlias()
        );
        emit(
            "cluster_state_response_composable_index_template_data_stream_context",
            serializeClusterStateResponseComposableIndexTemplateDataStreamContext()
        );
        emit("cluster_state_response_metadata_mixed_templates", serializeClusterStateResponseMetadataMixedTemplates());
        emit("cluster_state_response_metadata_mixed_data_stream", serializeClusterStateResponseMetadataMixedDataStream());
        emit("cluster_state_response_data_stream_metadata", serializeClusterStateResponseDataStreamMetadata());
        emit("cluster_state_response_ingest_metadata", serializeClusterStateResponseIngestMetadata());
        emit("cluster_state_response_search_pipeline_metadata", serializeClusterStateResponseSearchPipelineMetadata());
        emit("cluster_state_response_script_metadata", serializeClusterStateResponseScriptMetadata());
        emit("cluster_state_response_persistent_tasks_metadata", serializeClusterStateResponsePersistentTasksMetadata());
        emit("cluster_state_response_decommission_metadata", serializeClusterStateResponseDecommissionMetadata());
        emit("cluster_state_response_repositories_metadata", serializeClusterStateResponseRepositoriesMetadata());
        emit("cluster_state_response_repositories_multi", serializeClusterStateResponseRepositoriesMulti());
        emit(
            "cluster_state_response_repository_workload_group_multi",
            serializeClusterStateResponseRepositoryWorkloadGroupMulti()
        );
        emit("cluster_state_response_repository_crypto_metadata", serializeClusterStateResponseRepositoryCryptoMetadata());
        emit("cluster_state_response_weighted_routing_metadata", serializeClusterStateResponseWeightedRoutingMetadata());
        emit("cluster_state_response_view_metadata", serializeClusterStateResponseViewMetadata());
        emit("cluster_state_response_workload_group_metadata", serializeClusterStateResponseWorkloadGroupMetadata());
        emit("cluster_state_response_misc_custom_metadata", serializeClusterStateResponseMiscCustomMetadata());
        emit("cluster_state_response_legacy_index_template", serializeClusterStateResponseLegacyIndexTemplate());
        emit(
            "cluster_state_response_legacy_index_template_mapping_alias",
            serializeClusterStateResponseLegacyIndexTemplateMappingAlias()
        );
        emit("cluster_state_response_index_routing", serializeClusterStateResponseIndexRouting());
        emit("cluster_state_response_index_metadata", serializeClusterStateResponseIndexMetadata());
        emit("cluster_state_response_index_metadata_mapping_alias", serializeClusterStateResponseIndexMetadataMappingAlias());
        emit("cluster_state_response_index_metadata_custom_data", serializeClusterStateResponseIndexMetadataCustomData());
        emit("cluster_state_response_index_metadata_rollover_info", serializeClusterStateResponseIndexMetadataRolloverInfo());
        emit(
            "cluster_state_response_index_metadata_rollover_condition",
            serializeClusterStateResponseIndexMetadataRolloverCondition()
        );
        emit(
            "cluster_state_response_index_metadata_rollover_size_age_conditions",
            serializeClusterStateResponseIndexMetadataRolloverSizeAgeConditions()
        );
        emit("cluster_state_response_index_metadata_split_shards", serializeClusterStateResponseIndexMetadataSplitShards());
        emit("cluster_state_response_shard_routing", serializeClusterStateResponseShardRouting());
        emit(
            "cluster_state_response_unassigned_failure",
            serializeClusterStateResponseUnassignedFailure()
        );
        emit("cluster_state_response_started_shard_routing", serializeClusterStateResponseStartedShardRouting());
        emit("cluster_state_response_initializing_shard_routing", serializeClusterStateResponseInitializingShardRouting());
        emit(
            "cluster_state_response_existing_store_recovery_source",
            serializeClusterStateResponseExistingStoreRecoverySource()
        );
        emit("cluster_state_response_snapshot_recovery_source", serializeClusterStateResponseSnapshotRecoverySource());
        emit("cluster_state_response_remote_store_recovery_source", serializeClusterStateResponseRemoteStoreRecoverySource());
        emit("cluster_state_response_relocating_shard_routing", serializeClusterStateResponseRelocatingShardRouting());
        emit("cluster_state_response_replica_shard_routing", serializeClusterStateResponseReplicaShardRouting());
        emit("cluster_state_response_minimal_wire_version", serializeVersion(Version.CURRENT));
    }

    private static byte[] serializeString(String value) throws IOException {
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.writeString(value);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeStringArray(String[] values) throws IOException {
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.writeStringArray(values);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeVariableHeader(String action, String[] features) throws IOException {
        ThreadContext threadContext = new ThreadContext(Settings.EMPTY);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            threadContext.writeTo(out);
            out.writeStringArray(features);
            out.writeString(action);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeTcpHandshakeRequest(long requestId) throws IOException {
        Version current = Version.CURRENT;
        Version minCompat = current.minimumCompatibilityVersion();
        return serializeRequest(
            TransportHandshaker.HANDSHAKE_ACTION_NAME,
            new TransportHandshaker.HandshakeRequest(current),
            minCompat,
            requestId,
            new String[0],
            true
        );
    }

    private static byte[] serializeTransportHandshakeRequest(long requestId) throws IOException {
        return serializeRequest(
            TransportService.HANDSHAKE_ACTION_NAME,
            TransportService.HandshakeRequest.INSTANCE,
            Version.CURRENT,
            requestId,
            new String[0],
            false
        );
    }

    private static byte[] serializeClusterStateResponseMinimal() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName).version(7L).stateUUID("fixture-state-uuid").build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStatePublicationDiffEmpty() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName).version(1L).stateUUID("fixture-diff-from").build();
        ClusterState after = ClusterState.builder(clusterName).version(2L).stateUUID("fixture-diff-to").build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-custom-from")
            .putCustom(SnapshotsInProgress.TYPE, SnapshotsInProgress.EMPTY)
            .build();
        ClusterState after = ClusterState.builder(clusterName).version(2L).stateUUID("fixture-diff-custom-to").build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-to")
            .putCustom(SnapshotsInProgress.TYPE, SnapshotsInProgress.EMPTY)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustomSnapshotsEntry() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-snapshots-entry-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-snapshots-entry-to")
            .putCustom(SnapshotsInProgress.TYPE, fixtureSnapshotsInProgress())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedCustomSnapshotsShardStatus() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-custom-snapshots-shard-status-from")
            .putCustom(SnapshotsInProgress.TYPE, fixtureSnapshotsInProgress())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-custom-snapshots-shard-status-to")
            .putCustom(SnapshotsInProgress.TYPE, fixtureSnapshotsInProgressWithShardStatus())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustomRestore() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-restore-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-restore-to")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgress())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustomRestoreShardStatus() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-restore-shard-status-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-restore-shard-status-to")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgressWithShardStatus())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedCustomRestoreShardStatus() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-custom-restore-shard-status-from")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgress())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-custom-restore-shard-status-to")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgressWithShardStatus())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustomSnapshotDeletions() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-snapshot-deletions-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-snapshot-deletions-to")
            .putCustom(SnapshotDeletionsInProgress.TYPE, fixtureSnapshotDeletionsInProgress())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedCustomSnapshotDeletions() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-custom-snapshot-deletions-from")
            .putCustom(SnapshotDeletionsInProgress.TYPE, fixtureSnapshotDeletionsInProgress())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-custom-snapshot-deletions-to")
            .putCustom(SnapshotDeletionsInProgress.TYPE, fixtureSnapshotDeletionsInProgressChanged())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertCustomRepositoryCleanup() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-custom-repository-cleanup-from")
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-custom-repository-cleanup-to")
            .putCustom(RepositoryCleanupInProgress.TYPE, fixtureRepositoryCleanupInProgress())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedCustomRepositoryCleanup() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-custom-repository-cleanup-from")
            .putCustom(RepositoryCleanupInProgress.TYPE, fixtureRepositoryCleanupInProgress(42L))
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-custom-repository-cleanup-to")
            .putCustom(RepositoryCleanupInProgress.TYPE, fixtureRepositoryCleanupInProgress(43L))
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteRoutingIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexRoutingTable indexRouting = IndexRoutingTable.builder(
            new Index("fixture-deleted-routing-index", "fixture-deleted-routing-index-uuid")
        ).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-routing-from")
            .routingTable(RoutingTable.builder().version(1L).add(indexRouting).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-routing-to")
            .routingTable(RoutingTable.builder().version(2L).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertRoutingIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexRoutingTable indexRouting = IndexRoutingTable.builder(
            new Index("fixture-upsert-routing-index", "fixture-upsert-routing-index-uuid")
        ).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-routing-from")
            .routingTable(RoutingTable.builder().version(1L).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-routing-to")
            .routingTable(RoutingTable.builder().version(2L).add(indexRouting).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedRoutingIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Index index = new Index("fixture-named-routing-index", "fixture-named-routing-index-uuid");
        IndexRoutingTable beforeIndexRouting = IndexRoutingTable.builder(index).build();
        ShardId shardId = new ShardId(index, 0);
        ShardRouting shard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "fixture named routing shard")
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(shard).build();
        IndexRoutingTable afterIndexRouting = IndexRoutingTable.builder(index).addIndexShard(shardRoutingTable).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-routing-from")
            .routingTable(RoutingTable.builder().version(1L).add(beforeIndexRouting).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-routing-to")
            .routingTable(RoutingTable.builder().version(2L).add(afterIndexRouting).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteMetadataIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-deleted-metadata-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-deleted-metadata-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-metadata-from")
            .metadata(metadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-metadata-to")
            .metadata(Metadata.builder().build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteMetadataTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata template = IndexTemplateMetadata.builder("fixture-deleted-template")
            .patterns(Collections.singletonList("fixture-deleted-*"))
            .order(5)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(9)
            .build();
        Metadata metadata = Metadata.builder().put(template).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-template-from")
            .metadata(metadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-template-to")
            .metadata(Metadata.builder().build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata template = IndexTemplateMetadata.builder("fixture-upsert-template")
            .patterns(Collections.singletonList("fixture-upsert-*"))
            .order(6)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(10)
            .build();
        Metadata metadata = Metadata.builder().put(template).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-template-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-template-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata beforeTemplate = IndexTemplateMetadata.builder("fixture-diff-template")
            .patterns(Collections.singletonList("fixture-diff-before-*"))
            .order(6)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(10)
            .build();
        IndexTemplateMetadata afterTemplate = IndexTemplateMetadata.builder("fixture-diff-template")
            .patterns(Collections.singletonList("fixture-diff-after-*"))
            .order(7)
            .settings(Settings.builder().put("index.number_of_shards", 2).build())
            .version(11)
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-template-from")
            .metadata(Metadata.builder().put(beforeTemplate).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-template-to")
            .metadata(Metadata.builder().put(afterTemplate).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataTemplateMappingAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata beforeTemplate = IndexTemplateMetadata.builder("fixture-diff-template-mapping-alias")
            .patterns(Collections.singletonList("fixture-diff-map-before-*"))
            .order(8)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(12)
            .build();
        IndexTemplateMetadata afterTemplate = IndexTemplateMetadata.builder("fixture-diff-template-mapping-alias")
            .patterns(Collections.singletonList("fixture-diff-map-after-*"))
            .order(9)
            .settings(Settings.builder().put("index.number_of_shards", 2).build())
            .putMapping("_doc", "{\"properties\":{\"title\":{\"type\":\"keyword\"}}}")
            .putAlias(AliasMetadata.builder("fixture-diff-template-alias").build())
            .version(13)
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-template-mapping-alias-from")
            .metadata(Metadata.builder().put(beforeTemplate).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-template-mapping-alias-to")
            .metadata(Metadata.builder().put(afterTemplate).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteMetadataCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repository = new RepositoryMetadata(
            "fixture-deleted-repo",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-deleted-repo").build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Collections.singletonList(repository));
        Metadata metadata = Metadata.builder().putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-metadata-custom-from")
            .metadata(metadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-metadata-custom-to")
            .metadata(Metadata.builder().build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repository = new RepositoryMetadata(
            "fixture-upsert-repo",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-upsert-repo").build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Collections.singletonList(repository));
        Metadata metadata = Metadata.builder().putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomRepositories() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata beforeRepository = new RepositoryMetadata(
            "fixture-diff-repo-a",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-diff-repo-before").build()
        );
        RepositoryMetadata afterRepositoryA = new RepositoryMetadata(
            "fixture-diff-repo-a",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-diff-repo-after").build()
        );
        RepositoryMetadata afterRepositoryB = new RepositoryMetadata(
            "fixture-diff-repo-b",
            "url",
            Settings.builder().put("url", "file:/tmp/fixture-diff-repo-b").build()
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(RepositoriesMetadata.TYPE, new RepositoriesMetadata(Collections.singletonList(beforeRepository)))
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(RepositoriesMetadata.TYPE, new RepositoriesMetadata(Arrays.asList(afterRepositoryA, afterRepositoryB)))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-repositories-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-repositories-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomComponentTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComponentTemplate componentTemplate = new ComponentTemplate(template, 9L, null);
        ComponentTemplateMetadata componentTemplateMetadata = new ComponentTemplateMetadata(
            Collections.singletonMap("fixture-upsert-component-template", componentTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComponentTemplateMetadata.TYPE, componentTemplateMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-component-template-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-component-template-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomIndexTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Arrays.asList("fixture-upsert-compose-*", "fixture-upsert-compose-alt-*"),
            template,
            Collections.singletonList("fixture-upsert-component-template"),
            31L,
            32L,
            Collections.<String, Object>singletonMap("fixture-upsert-meta", "fixture-upsert-value")
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-upsert-composable-template", indexTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-index-template-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-index-template-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomDataStream() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DataStream dataStream = new DataStream(
            "fixture-upsert-data-stream",
            new DataStream.TimestampField("event_time"),
            Collections.singletonList(new Index(".ds-fixture-upsert-data-stream-000001", "fixture-upsert-backing-index-uuid")),
            3L
        );
        DataStreamMetadata dataStreamMetadata = new DataStreamMetadata(
            Collections.singletonMap("fixture-upsert-data-stream", dataStream)
        );
        Metadata metadata = Metadata.builder().putCustom(DataStreamMetadata.TYPE, dataStreamMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-data-stream-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-data-stream-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomIngest() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        PipelineConfiguration pipeline = new PipelineConfiguration(
            "fixture-upsert-pipeline",
            new BytesArray("{\"description\":\"fixture upsert ingest pipeline\",\"processors\":[]}"),
            MediaTypeRegistry.JSON
        );
        IngestMetadata ingestMetadata = new IngestMetadata(Collections.singletonMap("fixture-upsert-pipeline", pipeline));
        Metadata metadata = Metadata.builder().putCustom(IngestMetadata.TYPE, ingestMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-ingest-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-ingest-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomSearchPipeline() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        org.opensearch.search.pipeline.PipelineConfiguration pipeline = new org.opensearch.search.pipeline.PipelineConfiguration(
            "fixture-upsert-search-pipeline",
            new BytesArray("{\"description\":\"fixture upsert search pipeline\",\"request_processors\":[],\"response_processors\":[]}"),
            MediaTypeRegistry.JSON
        );
        SearchPipelineMetadata searchPipelineMetadata = new SearchPipelineMetadata(
            Collections.singletonMap("fixture-upsert-search-pipeline", pipeline)
        );
        Metadata metadata = Metadata.builder().putCustom(SearchPipelineMetadata.TYPE, searchPipelineMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-search-pipeline-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-search-pipeline-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomStoredScripts() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        StoredScriptSource scriptSource = new StoredScriptSource(
            "painless",
            "return params.upsert_value;",
            Collections.singletonMap("content_type", "application/json")
        );
        ScriptMetadata scriptMetadata = new ScriptMetadata.Builder(null).storeScript("fixture-upsert-script", scriptSource).build();
        Metadata metadata = Metadata.builder().putCustom(ScriptMetadata.TYPE, scriptMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-stored-scripts-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-stored-scripts-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomIndexGraveyard() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexGraveyard graveyard = IndexGraveyard.builder()
            .addTombstone(new Index("fixture-upsert-deleted-index", "fixture-upsert-deleted-index-uuid"))
            .build();
        Metadata beforeMetadata = Metadata.builder().removeCustom(IndexGraveyard.TYPE).build();
        Metadata afterMetadata = Metadata.builder().indexGraveyard(graveyard).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-index-graveyard-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-index-graveyard-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomPersistentTasks() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        PersistentTasksCustomMetadata.Builder tasks = PersistentTasksCustomMetadata.builder();
        tasks.addTask(
            "fixture-upsert-task",
            FixturePersistentTaskParams.NAME,
            new FixturePersistentTaskParams(),
            new PersistentTasksCustomMetadata.Assignment("fixture-upsert-node-id", "assigned for upsert fixture")
        );
        tasks.updateTaskState("fixture-upsert-task", new FixturePersistentTaskState());
        Metadata metadata = Metadata.builder().putCustom(PersistentTasksCustomMetadata.TYPE, tasks.build()).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-persistent-tasks-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-persistent-tasks-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomDecommission() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DecommissionAttributeMetadata decommissionMetadata = new DecommissionAttributeMetadata(
            new DecommissionAttribute("zone", "zone-upsert"),
            DecommissionStatus.DRAINING,
            "fixture-upsert-decommission-request"
        );
        Metadata metadata = Metadata.builder().putCustom(DecommissionAttributeMetadata.TYPE, decommissionMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-decommission-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-decommission-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomDecommission() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DecommissionAttributeMetadata beforeDecommissionMetadata = new DecommissionAttributeMetadata(
            new DecommissionAttribute("zone", "zone-diff"),
            DecommissionStatus.INIT,
            "fixture-diff-decommission-request-before"
        );
        DecommissionAttributeMetadata afterDecommissionMetadata = new DecommissionAttributeMetadata(
            new DecommissionAttribute("zone", "zone-diff"),
            DecommissionStatus.DRAINING,
            "fixture-diff-decommission-request-after"
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(DecommissionAttributeMetadata.TYPE, beforeDecommissionMetadata)
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(DecommissionAttributeMetadata.TYPE, afterDecommissionMetadata)
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-decommission-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-decommission-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomWeightedRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        WeightedRouting weightedRouting = new WeightedRouting("zone", Collections.singletonMap("zone-upsert", 0.5d));
        WeightedRoutingMetadata weightedRoutingMetadata = new WeightedRoutingMetadata(weightedRouting, 33L);
        Metadata metadata = Metadata.builder().putCustom(WeightedRoutingMetadata.TYPE, weightedRoutingMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-weighted-routing-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-weighted-routing-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomWeightedRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        WeightedRouting beforeWeightedRouting = new WeightedRouting("zone", Collections.singletonMap("zone-before", 0.25d));
        WeightedRoutingMetadata beforeWeightedRoutingMetadata = new WeightedRoutingMetadata(beforeWeightedRouting, 44L);
        WeightedRouting afterWeightedRouting = new WeightedRouting("zone", Collections.singletonMap("zone-after", 0.75d));
        WeightedRoutingMetadata afterWeightedRoutingMetadata = new WeightedRoutingMetadata(afterWeightedRouting, 45L);
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(WeightedRoutingMetadata.TYPE, beforeWeightedRoutingMetadata)
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(WeightedRoutingMetadata.TYPE, afterWeightedRoutingMetadata)
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-weighted-routing-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-weighted-routing-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomView() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        View view = new View(
            "fixture-upsert-view",
            "fixture upsert view source",
            789L,
            1011L,
            Collections.singleton(new View.Target("fixture-upsert-view-*"))
        );
        ViewMetadata viewMetadata = new ViewMetadata(Collections.singletonMap("fixture-upsert-view", view));
        Metadata metadata = Metadata.builder().putCustom(ViewMetadata.TYPE, viewMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-view-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-view-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataCustomWorkloadGroup() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Map<ResourceType, Double> resourceLimits = new LinkedHashMap<>();
        resourceLimits.put(ResourceType.CPU, 0.6d);
        resourceLimits.put(ResourceType.MEMORY, 0.4d);
        Map<String, String> searchSettings = new LinkedHashMap<>();
        searchSettings.put("timeout", "15s");
        MutableWorkloadGroupFragment fragment = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.MONITOR,
            resourceLimits,
            searchSettings
        );
        WorkloadGroup workloadGroup = new WorkloadGroup(
            "fixture-upsert-workload",
            "fixture-upsert-workload-id",
            fragment,
            567890L
        );
        WorkloadGroupMetadata workloadGroupMetadata = new WorkloadGroupMetadata(
            Collections.singletonMap("fixture-upsert-workload-id", workloadGroup)
        );
        Metadata metadata = Metadata.builder().putCustom(WorkloadGroupMetadata.TYPE, workloadGroupMetadata).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-custom-workload-group-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-custom-workload-group-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomView() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        View beforeView = new View(
            "fixture-diff-view",
            "fixture view before",
            100L,
            200L,
            Collections.singleton(new View.Target("fixture-diff-view-before-*"))
        );
        View afterView = new View(
            "fixture-diff-view",
            "fixture view after",
            101L,
            201L,
            Collections.singleton(new View.Target("fixture-diff-view-after-*"))
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(ViewMetadata.TYPE, new ViewMetadata(Collections.singletonMap("fixture-diff-view", beforeView)))
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(ViewMetadata.TYPE, new ViewMetadata(Collections.singletonMap("fixture-diff-view", afterView)))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-view-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-view-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomWorkloadGroup() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Map<ResourceType, Double> beforeResourceLimits = new LinkedHashMap<>();
        beforeResourceLimits.put(ResourceType.CPU, 0.2d);
        Map<String, String> beforeSearchSettings = new LinkedHashMap<>();
        beforeSearchSettings.put("timeout", "5s");
        MutableWorkloadGroupFragment beforeFragment = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.ENFORCED,
            beforeResourceLimits,
            beforeSearchSettings
        );
        WorkloadGroup beforeWorkloadGroup = new WorkloadGroup(
            "fixture-diff-workload",
            "fixture-diff-workload-id",
            beforeFragment,
            111111L
        );

        Map<ResourceType, Double> afterResourceLimits = new LinkedHashMap<>();
        afterResourceLimits.put(ResourceType.CPU, 0.7d);
        afterResourceLimits.put(ResourceType.MEMORY, 0.2d);
        Map<String, String> afterSearchSettings = new LinkedHashMap<>();
        afterSearchSettings.put("timeout", "25s");
        MutableWorkloadGroupFragment afterFragment = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.SOFT,
            afterResourceLimits,
            afterSearchSettings
        );
        WorkloadGroup afterWorkloadGroup = new WorkloadGroup(
            "fixture-diff-workload",
            "fixture-diff-workload-id",
            afterFragment,
            222222L
        );

        Metadata beforeMetadata = Metadata.builder()
            .putCustom(
                WorkloadGroupMetadata.TYPE,
                new WorkloadGroupMetadata(Collections.singletonMap("fixture-diff-workload-id", beforeWorkloadGroup))
            )
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(
                WorkloadGroupMetadata.TYPE,
                new WorkloadGroupMetadata(Collections.singletonMap("fixture-diff-workload-id", afterWorkloadGroup))
            )
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-workload-group-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-workload-group-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomDataStream() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DataStream beforeDataStream = new DataStream(
            "fixture-diff-data-stream",
            new DataStream.TimestampField("event_time"),
            Collections.singletonList(new Index(".ds-fixture-diff-data-stream-000001", "fixture-diff-backing-before-uuid")),
            1L
        );
        DataStream afterDataStream = new DataStream(
            "fixture-diff-data-stream",
            new DataStream.TimestampField("event_time"),
            Arrays.asList(
                new Index(".ds-fixture-diff-data-stream-000001", "fixture-diff-backing-before-uuid"),
                new Index(".ds-fixture-diff-data-stream-000002", "fixture-diff-backing-after-uuid")
            ),
            2L
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(
                DataStreamMetadata.TYPE,
                new DataStreamMetadata(Collections.singletonMap("fixture-diff-data-stream", beforeDataStream))
            )
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(
                DataStreamMetadata.TYPE,
                new DataStreamMetadata(Collections.singletonMap("fixture-diff-data-stream", afterDataStream))
            )
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-data-stream-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-data-stream-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomComponentTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ComponentTemplate beforeTemplate = new ComponentTemplate(
            new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null),
            1L,
            null
        );
        ComponentTemplate afterTemplate = new ComponentTemplate(
            new Template(Settings.builder().put("index.number_of_shards", 2).build(), null, null),
            2L,
            Collections.<String, Object>singletonMap("fixture-diff-meta", "after")
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(
                ComponentTemplateMetadata.TYPE,
                new ComponentTemplateMetadata(Collections.singletonMap("fixture-diff-component-template", beforeTemplate))
            )
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(
                ComponentTemplateMetadata.TYPE,
                new ComponentTemplateMetadata(Collections.singletonMap("fixture-diff-component-template", afterTemplate))
            )
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-component-template-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-component-template-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataCustomIndexTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ComposableIndexTemplate beforeTemplate = new ComposableIndexTemplate(
            Collections.singletonList("fixture-diff-compose-before-*"),
            new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null),
            Collections.singletonList("fixture-before-component-template"),
            10L,
            11L,
            Collections.<String, Object>singletonMap("fixture-diff-meta", "before")
        );
        ComposableIndexTemplate afterTemplate = new ComposableIndexTemplate(
            Arrays.asList("fixture-diff-compose-after-*", "fixture-diff-compose-alt-*"),
            new Template(Settings.builder().put("index.number_of_shards", 2).build(), null, null),
            Collections.singletonList("fixture-after-component-template"),
            20L,
            21L,
            Collections.<String, Object>singletonMap("fixture-diff-meta", "after")
        );
        Metadata beforeMetadata = Metadata.builder()
            .putCustom(
                ComposableIndexTemplateMetadata.TYPE,
                new ComposableIndexTemplateMetadata(Collections.singletonMap("fixture-diff-composable-template", beforeTemplate))
            )
            .build();
        Metadata afterMetadata = Metadata.builder()
            .putCustom(
                ComposableIndexTemplateMetadata.TYPE,
                new ComposableIndexTemplateMetadata(Collections.singletonMap("fixture-diff-composable-template", afterTemplate))
            )
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-index-template-from")
            .metadata(beforeMetadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-index-template-to")
            .metadata(afterMetadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffDeleteConsistentSettingHash() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Metadata metadata = Metadata.builder()
            .hashesOfConsistentSettings(Collections.singletonMap("fixture.secure.setting", "hash-value"))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-consistent-hash-from")
            .metadata(metadata)
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-consistent-hash-to")
            .metadata(Metadata.builder().build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffUpsertMetadataIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-upsert-metadata-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-upsert-metadata-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-upsert-metadata-from")
            .metadata(Metadata.builder().build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-upsert-metadata-to")
            .metadata(metadata)
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndex() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexMapping() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-mapping-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-mapping")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .putMapping("{\"properties\":{\"title\":{\"type\":\"keyword\"}}}")
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-mapping")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .putMapping("{\"properties\":{\"title\":{\"type\":\"text\"}}}")
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-mapping-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-mapping-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-alias-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-alias")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .putAlias(AliasMetadata.builder("fixture-nested-alias").routing("before-route").build())
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-alias")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .putAlias(AliasMetadata.builder("fixture-nested-alias").routing("after-route").build())
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-alias-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-alias-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexCustomData() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-custom-data-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-custom-data")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .putCustom("fixture-nested-custom", Collections.singletonMap("fixture-custom-key", "before-value"))
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-custom-data")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .putCustom("fixture-nested-custom", Collections.singletonMap("fixture-custom-key", "after-value"))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-custom-data-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-custom-data-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexRollover() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-rollover-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-rollover")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .putRolloverInfo(new RolloverInfo("fixture-nested-rollover", Collections.emptyList(), 111L))
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-rollover")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .putRolloverInfo(new RolloverInfo("fixture-nested-rollover", Collections.emptyList(), 222L))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-rollover-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-rollover-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexInSync() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-in-sync-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-in-sync")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(1L)
            .putInSyncAllocationIds(0, Collections.singleton("before-allocation"))
            .build();
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-in-sync")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .version(2L)
            .putInSyncAllocationIds(0, Collections.singleton("after-allocation"))
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-in-sync-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-in-sync-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiffNamedMetadataIndexSplitShards() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-named-metadata-index-split-shards-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 3)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata beforeIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-split-shards")
            .settings(settings)
            .numberOfShards(3)
            .numberOfReplicas(0)
            .version(1L)
            .build();
        SplitShardsMetadata.Builder splitShardsBuilder = new SplitShardsMetadata.Builder(3);
        splitShardsBuilder.splitShard(0, 3);
        IndexMetadata afterIndexMetadata = IndexMetadata.builder("fixture-named-metadata-index-split-shards")
            .settings(settings)
            .numberOfShards(3)
            .numberOfReplicas(0)
            .version(2L)
            .splitShardsMetadata(splitShardsBuilder.build())
            .build();
        ClusterState before = ClusterState.builder(clusterName)
            .version(1L)
            .stateUUID("fixture-diff-named-metadata-split-shards-from")
            .metadata(Metadata.builder().put(beforeIndexMetadata, false).build())
            .build();
        ClusterState after = ClusterState.builder(clusterName)
            .version(2L)
            .stateUUID("fixture-diff-named-metadata-split-shards-to")
            .metadata(Metadata.builder().put(afterIndexMetadata, false).build())
            .build();
        return serializeClusterStatePublicationDiff(before, after);
    }

    private static byte[] serializeClusterStatePublicationDiff(ClusterState before, ClusterState after) throws IOException {
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            out.writeBoolean(false);
            after.diff(before).writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRepositoryCleanupCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(21L)
            .stateUUID("fixture-state-with-repository-cleanup")
            .putCustom(RepositoryCleanupInProgress.TYPE, fixtureRepositoryCleanupInProgress())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static RepositoryCleanupInProgress fixtureRepositoryCleanupInProgress() {
        return fixtureRepositoryCleanupInProgress(42L);
    }

    private static RepositoryCleanupInProgress fixtureRepositoryCleanupInProgress(long repositoryStateId) {
        return new RepositoryCleanupInProgress(
            Collections.singletonList(RepositoryCleanupInProgress.startedEntry("fixture-repository", repositoryStateId))
        );
    }

    private static byte[] serializeClusterStateResponseSnapshotDeletionsCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(22L)
            .stateUUID("fixture-state-with-snapshot-deletions")
            .putCustom(SnapshotDeletionsInProgress.TYPE, fixtureSnapshotDeletionsInProgress())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static SnapshotDeletionsInProgress fixtureSnapshotDeletionsInProgress() {
        SnapshotDeletionsInProgress.Entry entry = new SnapshotDeletionsInProgress.Entry(
            Collections.singletonList(new SnapshotId("fixture-delete-snapshot", "fixture-delete-snapshot-uuid")),
            "fixture-repository",
            123456789L,
            43L,
            SnapshotDeletionsInProgress.State.STARTED
        );
        return SnapshotDeletionsInProgress.of(Collections.singletonList(entry));
    }

    private static SnapshotDeletionsInProgress fixtureSnapshotDeletionsInProgressChanged() {
        SnapshotDeletionsInProgress.Entry entry = fixtureSnapshotDeletionsInProgress()
            .getEntries()
            .get(0)
            .withSnapshots(
                Arrays.asList(
                    new SnapshotId("fixture-delete-snapshot", "fixture-delete-snapshot-uuid"),
                    new SnapshotId("fixture-delete-snapshot-after", "fixture-delete-snapshot-after-uuid")
                )
            )
            .withRepoGen(44L);
        return SnapshotDeletionsInProgress.of(Collections.singletonList(entry));
    }

    private static byte[] serializeClusterStateResponseRestoreCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(23L)
            .stateUUID("fixture-state-with-restore")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgress())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static RestoreInProgress fixtureRestoreInProgress() {
        RestoreInProgress.Entry entry = new RestoreInProgress.Entry(
            "fixture-restore-entry-uuid",
            new Snapshot("fixture-repository", new SnapshotId("fixture-restore-snapshot", "fixture-restore-snapshot-uuid")),
            RestoreInProgress.State.STARTED,
            Collections.singletonList("fixture-index"),
            Collections.emptyMap()
        );
        return new RestoreInProgress.Builder().add(entry).build();
    }

    private static byte[] serializeClusterStateResponseRestoreCustomShardStatus() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(25L)
            .stateUUID("fixture-state-with-restore-shard-status")
            .putCustom(RestoreInProgress.TYPE, fixtureRestoreInProgressWithShardStatus())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static RestoreInProgress fixtureRestoreInProgressWithShardStatus() {
        RestoreInProgress.Entry entry = new RestoreInProgress.Entry(
            "fixture-restore-shard-entry-uuid",
            new Snapshot("fixture-repository", new SnapshotId("fixture-restore-shard-snapshot", "fixture-restore-shard-snapshot-uuid")),
            RestoreInProgress.State.STARTED,
            Collections.singletonList("fixture-restore-shard-index"),
            Collections.singletonMap(
                new ShardId(new Index("fixture-restore-shard-index", "fixture-restore-shard-index-uuid"), 0),
                new RestoreInProgress.ShardRestoreStatus(
                    "fixture-restore-node-id",
                    RestoreInProgress.State.STARTED,
                    "fixture-restore-reason"
                )
            )
        );
        return new RestoreInProgress.Builder().add(entry).build();
    }

    private static byte[] serializeClusterStateResponseSnapshotsCustom() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(24L)
            .stateUUID("fixture-state-with-snapshots")
            .putCustom(SnapshotsInProgress.TYPE, fixtureSnapshotsInProgress())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static SnapshotsInProgress fixtureSnapshotsInProgress() {
        SnapshotsInProgress.Entry entry = SnapshotsInProgress.startedEntry(
            new Snapshot("fixture-repository", new SnapshotId("fixture-snapshot-in-progress", "fixture-snapshot-in-progress-uuid")),
            true,
            false,
            Collections.singletonList(new IndexId("fixture-index", "fixture-snapshot-index-id")),
            Collections.singletonList("fixture-data-stream"),
            123456789L,
            44L,
            Collections.emptyMap(),
            Collections.emptyMap(),
            Version.CURRENT,
            false,
            false
        );
        return SnapshotsInProgress.of(Collections.singletonList(entry));
    }

    private static byte[] serializeClusterStateResponseSnapshotsCustomShardStatus() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        SnapshotsInProgress snapshots = fixtureSnapshotsInProgressWithShardStatus();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(26L)
            .stateUUID("fixture-state-with-snapshots-shard-status")
            .putCustom(SnapshotsInProgress.TYPE, snapshots)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static SnapshotsInProgress fixtureSnapshotsInProgressWithShardStatus() {
        SnapshotsInProgress.Entry entry = SnapshotsInProgress.startedEntry(
            new Snapshot(
                "fixture-repository",
                new SnapshotId("fixture-snapshot-shard-in-progress", "fixture-snapshot-shard-in-progress-uuid")
            ),
            true,
            false,
            Collections.singletonList(new IndexId("fixture-snapshot-shard-index", "fixture-snapshot-shard-index-id")),
            Collections.singletonList("fixture-snapshot-shard-data-stream"),
            223456789L,
            45L,
            Collections.singletonMap(
                new ShardId(new Index("fixture-snapshot-shard-index", "fixture-snapshot-shard-index-uuid"), 0),
                new SnapshotsInProgress.ShardSnapshotStatus("fixture-snapshot-node-id", "fixture-snapshot-generation")
            ),
            Collections.emptyMap(),
            Version.CURRENT,
            false,
            false
        );
        return SnapshotsInProgress.of(Collections.singletonList(entry));
    }

    private static byte[] serializeClusterStateResponseSnapshotsCustomClone() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        SnapshotsInProgress.Entry entry = SnapshotsInProgress.startClone(
            new Snapshot("fixture-repository", new SnapshotId("fixture-snapshot-clone", "fixture-snapshot-clone-uuid")),
            new SnapshotId("fixture-source-snapshot", "fixture-source-snapshot-uuid"),
            Collections.singletonList(new IndexId("fixture-clone-index", "fixture-clone-index-id")),
            323456789L,
            46L,
            Version.CURRENT
        ).withClones(
            Collections.singletonMap(
                new RepositoryShardId(new IndexId("fixture-clone-index", "fixture-clone-index-id"), 0),
                new SnapshotsInProgress.ShardSnapshotStatus("fixture-clone-node-id", "fixture-clone-generation")
            )
        );
        SnapshotsInProgress snapshots = SnapshotsInProgress.of(Collections.singletonList(entry));
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(27L)
            .stateUUID("fixture-state-with-snapshots-clone")
            .putCustom(SnapshotsInProgress.TYPE, snapshots)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseSnapshotsCustomUserMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Map<String, Object> userMetadata = new LinkedHashMap<>();
        userMetadata.put("fixture-user-string", "fixture-user-value");
        userMetadata.put("fixture-user-int", 7);
        userMetadata.put("fixture-user-long", 8L);
        userMetadata.put("fixture-user-bool", true);
        userMetadata.put("fixture-user-null", null);
        userMetadata.put("fixture-user-byte", (byte) 11);
        userMetadata.put("fixture-user-short", (short) 12);
        userMetadata.put("fixture-user-float", 1.5f);
        userMetadata.put("fixture-user-double", 2.5d);
        userMetadata.put("fixture-user-date", new Date(123456789L));
        userMetadata.put("fixture-user-bytes", new byte[] { 1, 2, 3 });
        userMetadata.put("fixture-user-list", Arrays.asList("fixture-list-value", 9, false));
        userMetadata.put("fixture-user-array", new Object[] { "fixture-array-value", 10L });
        Map<String, Object> nestedUserMetadata = new LinkedHashMap<>();
        nestedUserMetadata.put("nested-string", "nested-value");
        nestedUserMetadata.put("nested-bool", false);
        userMetadata.put("fixture-user-map", nestedUserMetadata);
        SnapshotsInProgress.Entry entry = SnapshotsInProgress.startedEntry(
            new Snapshot(
                "fixture-repository",
                new SnapshotId("fixture-snapshot-user-metadata", "fixture-snapshot-user-metadata-uuid")
            ),
            true,
            false,
            Collections.singletonList(new IndexId("fixture-user-metadata-index", "fixture-user-metadata-index-id")),
            Collections.singletonList("fixture-user-metadata-data-stream"),
            423456789L,
            47L,
            Collections.emptyMap(),
            userMetadata,
            Version.CURRENT,
            false,
            false
        );
        SnapshotsInProgress snapshots = SnapshotsInProgress.of(Collections.singletonList(entry));
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(28L)
            .stateUUID("fixture-state-with-snapshots-user-metadata")
            .putCustom(SnapshotsInProgress.TYPE, snapshots)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseSingleNode() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DiscoveryNode node = new DiscoveryNode(
            "fixture-node",
            "fixture-node-id",
            "fixture-ephemeral-id",
            "127.0.0.1",
            "127.0.0.1",
            new TransportAddress(InetAddress.getByName("127.0.0.1"), 9300),
            Collections.emptyMap(),
            Collections.singleton(DiscoveryNodeRole.CLUSTER_MANAGER_ROLE),
            Version.CURRENT
        );
        DiscoveryNodes nodes = DiscoveryNodes.builder().add(node).clusterManagerNodeId("fixture-node-id").localNodeId("fixture-node-id").build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(8L)
            .stateUUID("fixture-state-with-node")
            .nodes(nodes)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseGlobalBlock() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterBlock block = new ClusterBlock(
            42,
            "fixture-block-uuid",
            "fixture global block",
            true,
            false,
            true,
            RestStatus.SERVICE_UNAVAILABLE,
            EnumSet.of(ClusterBlockLevel.METADATA_WRITE, ClusterBlockLevel.WRITE)
        );
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(9L)
            .stateUUID("fixture-state-with-block")
            .blocks(ClusterBlocks.builder().addGlobalBlock(block).build())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexBlock() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        ClusterBlock block = new ClusterBlock(
            43,
            "fixture-index-block-uuid",
            "fixture index block",
            false,
            false,
            false,
            RestStatus.FORBIDDEN,
            EnumSet.of(ClusterBlockLevel.READ, ClusterBlockLevel.METADATA_READ)
        );
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(17L)
            .stateUUID("fixture-state-with-index-block")
            .blocks(ClusterBlocks.builder().addIndexBlock("fixture-index", block).build())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseMetadataSettings() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Metadata metadata = Metadata.builder()
            .transientSettings(Settings.builder().put("fixture.transient.setting", "transient-value").build())
            .persistentSettings(Settings.builder().put("fixture.persistent.setting", "persistent-value").build())
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(18L)
            .stateUUID("fixture-state-with-metadata-settings")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseConsistentSettingHashes() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Metadata metadata = Metadata.builder()
            .hashesOfConsistentSettings(Collections.singletonMap("fixture.secure.setting", "hash-value"))
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(19L)
            .stateUUID("fixture-state-with-consistent-setting-hashes")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexGraveyardTombstone() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexGraveyard graveyard = IndexGraveyard.builder()
            .addTombstone(new Index("fixture-deleted-index", "fixture-deleted-index-uuid"))
            .build();
        Metadata metadata = Metadata.builder().indexGraveyard(graveyard).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(28L)
            .stateUUID("fixture-state-with-index-graveyard-tombstone")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComponentTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComponentTemplate componentTemplate = new ComponentTemplate(template, 5L, null);
        ComponentTemplateMetadata componentTemplateMetadata = new ComponentTemplateMetadata(
            Collections.singletonMap("fixture-component-template", componentTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComponentTemplateMetadata.TYPE, componentTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(29L)
            .stateUUID("fixture-state-with-component-template")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComponentTemplateMappingAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(
            Settings.builder().put("index.number_of_shards", 1).build(),
            new CompressedXContent("{\"properties\":{\"title\":{\"type\":\"keyword\"}}}"),
            Collections.singletonMap("fixture-component-alias", AliasMetadata.builder("fixture-component-alias").build())
        );
        ComponentTemplate componentTemplate = new ComponentTemplate(template, 6L, null);
        ComponentTemplateMetadata componentTemplateMetadata = new ComponentTemplateMetadata(
            Collections.singletonMap("fixture-component-template-mapping-alias", componentTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComponentTemplateMetadata.TYPE, componentTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(30L)
            .stateUUID("fixture-state-with-component-template-mapping-alias")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComponentTemplateMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComponentTemplate componentTemplate = new ComponentTemplate(
            template,
            7L,
            Collections.<String, Object>singletonMap("fixture-meta-key", "fixture-meta-value")
        );
        ComponentTemplateMetadata componentTemplateMetadata = new ComponentTemplateMetadata(
            Collections.singletonMap("fixture-component-template-metadata", componentTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComponentTemplateMetadata.TYPE, componentTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(31L)
            .stateUUID("fixture-state-with-component-template-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComposableIndexTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Arrays.asList("fixture-compose-*", "fixture-compose-alt-*"),
            template,
            Collections.singletonList("fixture-component-template"),
            11L,
            12L,
            Collections.<String, Object>singletonMap("fixture-template-meta", "fixture-template-meta-value")
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-composable-template", indexTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(32L)
            .stateUUID("fixture-state-with-composable-index-template")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComposableIndexTemplateMappingAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(
            Settings.builder().put("index.number_of_shards", 1).build(),
            new CompressedXContent("{\"properties\":{\"sku\":{\"type\":\"keyword\"}}}"),
            Collections.singletonMap("fixture-composable-alias", AliasMetadata.builder("fixture-composable-alias").build())
        );
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Collections.singletonList("fixture-compose-map-*"),
            template,
            Collections.singletonList("fixture-component-template"),
            13L,
            14L,
            Collections.<String, Object>singletonMap("fixture-template-meta", "fixture-template-meta-value")
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-composable-template-mapping-alias", indexTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(33L)
            .stateUUID("fixture-state-with-composable-index-template-mapping-alias")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseComposableIndexTemplateDataStreamContext() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComposableIndexTemplate.DataStreamTemplate dataStreamTemplate =
            new ComposableIndexTemplate.DataStreamTemplate(new DataStream.TimestampField("event_time"));
        Context context = new Context(
            "fixture-context",
            "2",
            Collections.<String, Object>singletonMap("fixture-context-param", "fixture-context-value")
        );
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Collections.singletonList("fixture-compose-data-stream-*"),
            template,
            Collections.singletonList("fixture-component-template"),
            15L,
            16L,
            Collections.<String, Object>singletonMap("fixture-template-meta", "fixture-template-meta-value"),
            dataStreamTemplate,
            context
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-composable-template-data-stream-context", indexTemplate)
        );
        Metadata metadata = Metadata.builder().putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(34L)
            .stateUUID("fixture-state-with-composable-index-template-data-stream-context")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseMetadataMixedTemplates() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata legacyTemplate = IndexTemplateMetadata.builder("fixture-mixed-legacy-template")
            .patterns(Collections.singletonList("fixture-mixed-legacy-*"))
            .order(9)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(19)
            .build();
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComponentTemplate componentTemplate = new ComponentTemplate(template, 20L, null);
        ComponentTemplateMetadata componentTemplateMetadata = new ComponentTemplateMetadata(
            Collections.singletonMap("fixture-mixed-component-template", componentTemplate)
        );
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Collections.singletonList("fixture-mixed-compose-*"),
            template,
            Collections.singletonList("fixture-mixed-component-template"),
            21L,
            22L,
            Collections.<String, Object>singletonMap("fixture-mixed-meta", "fixture-mixed-value")
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-mixed-composable-template", indexTemplate)
        );
        Metadata metadata = Metadata.builder()
            .put(legacyTemplate)
            .putCustom(ComponentTemplateMetadata.TYPE, componentTemplateMetadata)
            .putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata)
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(42L)
            .stateUUID("fixture-state-with-metadata-mixed-templates")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseMetadataMixedDataStream() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DataStream dataStream = new DataStream(
            "fixture-mixed-data-stream",
            new DataStream.TimestampField("event_time"),
            Collections.singletonList(new Index(".ds-fixture-mixed-data-stream-000001", "fixture-mixed-backing-index-uuid")),
            1L
        );
        DataStreamMetadata dataStreamMetadata = new DataStreamMetadata(
            Collections.singletonMap("fixture-mixed-data-stream", dataStream)
        );
        Template template = new Template(Settings.builder().put("index.number_of_shards", 1).build(), null, null);
        ComposableIndexTemplate.DataStreamTemplate dataStreamTemplate =
            new ComposableIndexTemplate.DataStreamTemplate(new DataStream.TimestampField("event_time"));
        ComposableIndexTemplate indexTemplate = new ComposableIndexTemplate(
            Collections.singletonList("fixture-mixed-data-*"),
            template,
            Collections.emptyList(),
            23L,
            24L,
            Collections.<String, Object>singletonMap("fixture-mixed-ds-meta", "fixture-mixed-ds-value"),
            dataStreamTemplate
        );
        ComposableIndexTemplateMetadata indexTemplateMetadata = new ComposableIndexTemplateMetadata(
            Collections.singletonMap("fixture-mixed-data-stream-template", indexTemplate)
        );
        Metadata metadata = Metadata.builder()
            .putCustom(DataStreamMetadata.TYPE, dataStreamMetadata)
            .putCustom(ComposableIndexTemplateMetadata.TYPE, indexTemplateMetadata)
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(43L)
            .stateUUID("fixture-state-with-metadata-mixed-data-stream")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseDataStreamMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DataStream dataStream = new DataStream(
            "fixture-data-stream",
            new DataStream.TimestampField("event_time"),
            Collections.singletonList(new Index(".ds-fixture-data-stream-000001", "fixture-backing-index-uuid")),
            1L
        );
        DataStreamMetadata dataStreamMetadata = new DataStreamMetadata(
            Collections.singletonMap("fixture-data-stream", dataStream)
        );
        Metadata metadata = Metadata.builder().putCustom(DataStreamMetadata.TYPE, dataStreamMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(35L)
            .stateUUID("fixture-state-with-data-stream-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRepositoriesMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repository = new RepositoryMetadata(
            "fixture-repo",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-repo").build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Collections.singletonList(repository));
        Metadata metadata = Metadata.builder().putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(36L)
            .stateUUID("fixture-state-with-repositories-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRepositoriesMulti() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repositoryA = new RepositoryMetadata(
            "fixture-repo-a",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-repo-a").build()
        );
        RepositoryMetadata repositoryB = new RepositoryMetadata(
            "fixture-repo-b",
            "url",
            Settings.builder().put("url", "file:/tmp/fixture-repo-b").build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Arrays.asList(repositoryA, repositoryB));
        Metadata metadata = Metadata.builder().putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(41L)
            .stateUUID("fixture-state-with-repositories-multi")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRepositoryWorkloadGroupMulti() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repositoryA = new RepositoryMetadata(
            "fixture-rich-repo-a",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-rich-repo-a").put("compress", true).build()
        );
        RepositoryMetadata repositoryB = new RepositoryMetadata(
            "fixture-rich-repo-b",
            "url",
            Settings.builder().put("url", "file:/tmp/fixture-rich-repo-b").put("readonly", true).build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Arrays.asList(repositoryA, repositoryB));

        Map<ResourceType, Double> limitsA = new LinkedHashMap<>();
        limitsA.put(ResourceType.CPU, 0.5d);
        limitsA.put(ResourceType.MEMORY, 0.25d);
        Map<String, String> searchSettingsA = new LinkedHashMap<>();
        searchSettingsA.put("timeout", "10s");
        MutableWorkloadGroupFragment fragmentA = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.ENFORCED,
            limitsA,
            searchSettingsA
        );
        Map<ResourceType, Double> limitsB = new LinkedHashMap<>();
        limitsB.put(ResourceType.CPU, 0.3d);
        Map<String, String> searchSettingsB = new LinkedHashMap<>();
        searchSettingsB.put("timeout", "5s");
        MutableWorkloadGroupFragment fragmentB = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.MONITOR,
            limitsB,
            searchSettingsB
        );
        WorkloadGroup workloadGroupA = new WorkloadGroup("fixture-rich-workload-a", "fixture-rich-workload-id-a", fragmentA, 345678L);
        WorkloadGroup workloadGroupB = new WorkloadGroup("fixture-rich-workload-b", "fixture-rich-workload-id-b", fragmentB, 456789L);
        Map<String, WorkloadGroup> workloadGroups = new LinkedHashMap<>();
        workloadGroups.put("fixture-rich-workload-id-a", workloadGroupA);
        workloadGroups.put("fixture-rich-workload-id-b", workloadGroupB);
        WorkloadGroupMetadata workloadGroupMetadata = new WorkloadGroupMetadata(workloadGroups);

        Metadata metadata = Metadata.builder()
            .putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata)
            .putCustom(WorkloadGroupMetadata.TYPE, workloadGroupMetadata)
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(42L)
            .stateUUID("fixture-state-with-repository-workload-group-multi")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRepositoryCryptoMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        CryptoMetadata cryptoMetadata = new CryptoMetadata(
            "fixture-key-provider",
            "aws-kms",
            Settings.builder().put("kms.key_arn", "fixture-key-arn").build()
        );
        RepositoryMetadata repository = new RepositoryMetadata(
            "fixture-crypto-repo",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-crypto-repo").build(),
            cryptoMetadata
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Collections.singletonList(repository));
        Metadata metadata = Metadata.builder().putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(40L)
            .stateUUID("fixture-state-with-repository-crypto-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseWeightedRoutingMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        WeightedRouting weightedRouting = new WeightedRouting("zone", Collections.singletonMap("zone-a", 1.0d));
        WeightedRoutingMetadata weightedRoutingMetadata = new WeightedRoutingMetadata(weightedRouting, 17L);
        Metadata metadata = Metadata.builder().putCustom(WeightedRoutingMetadata.TYPE, weightedRoutingMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(37L)
            .stateUUID("fixture-state-with-weighted-routing-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseViewMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        View view = new View(
            "fixture-view",
            "fixture source",
            123L,
            456L,
            Collections.singleton(new View.Target("fixture-view-*"))
        );
        ViewMetadata viewMetadata = new ViewMetadata(Collections.singletonMap("fixture-view", view));
        Metadata metadata = Metadata.builder().putCustom(ViewMetadata.TYPE, viewMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(38L)
            .stateUUID("fixture-state-with-view-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseWorkloadGroupMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        MutableWorkloadGroupFragment fragment = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.ENFORCED,
            Collections.singletonMap(ResourceType.CPU, 0.5d),
            Collections.emptyMap()
        );
        WorkloadGroup workloadGroup = new WorkloadGroup("fixture-workload", "fixture-workload-id", fragment, 123456L);
        WorkloadGroupMetadata workloadGroupMetadata = new WorkloadGroupMetadata(
            Collections.singletonMap("fixture-workload-id", workloadGroup)
        );
        Metadata metadata = Metadata.builder().putCustom(WorkloadGroupMetadata.TYPE, workloadGroupMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(39L)
            .stateUUID("fixture-state-with-workload-group-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIngestMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        PipelineConfiguration pipeline = new PipelineConfiguration(
            "fixture-pipeline",
            new BytesArray("{\"description\":\"fixture ingest pipeline\",\"processors\":[]}"),
            MediaTypeRegistry.JSON
        );
        IngestMetadata ingestMetadata = new IngestMetadata(Collections.singletonMap("fixture-pipeline", pipeline));
        Metadata metadata = Metadata.builder().putCustom(IngestMetadata.TYPE, ingestMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(43L)
            .stateUUID("fixture-state-with-ingest-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseSearchPipelineMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        org.opensearch.search.pipeline.PipelineConfiguration pipeline = new org.opensearch.search.pipeline.PipelineConfiguration(
            "fixture-search-pipeline",
            new BytesArray("{\"description\":\"fixture search pipeline\",\"request_processors\":[],\"response_processors\":[]}"),
            MediaTypeRegistry.JSON
        );
        SearchPipelineMetadata searchPipelineMetadata = new SearchPipelineMetadata(
            Collections.singletonMap("fixture-search-pipeline", pipeline)
        );
        Metadata metadata = Metadata.builder().putCustom(SearchPipelineMetadata.TYPE, searchPipelineMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(44L)
            .stateUUID("fixture-state-with-search-pipeline-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseScriptMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        StoredScriptSource scriptSource = new StoredScriptSource(
            "painless",
            "return params.value;",
            Collections.singletonMap("content_type", "application/json")
        );
        ScriptMetadata scriptMetadata = new ScriptMetadata.Builder(null).storeScript("fixture-script", scriptSource).build();
        Metadata metadata = Metadata.builder().putCustom(ScriptMetadata.TYPE, scriptMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(45L)
            .stateUUID("fixture-state-with-script-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponsePersistentTasksMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        PersistentTasksCustomMetadata.Builder tasks = PersistentTasksCustomMetadata.builder();
        tasks.addTask(
            "fixture-task",
            FixturePersistentTaskParams.NAME,
            new FixturePersistentTaskParams(),
            new PersistentTasksCustomMetadata.Assignment("fixture-node-id", "assigned for fixture")
        );
        tasks.updateTaskState("fixture-task", new FixturePersistentTaskState());
        Metadata metadata = Metadata.builder().putCustom(PersistentTasksCustomMetadata.TYPE, tasks.build()).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(46L)
            .stateUUID("fixture-state-with-persistent-tasks-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseDecommissionMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        DecommissionAttributeMetadata decommissionMetadata = new DecommissionAttributeMetadata(
            new DecommissionAttribute("zone", "zone-c"),
            DecommissionStatus.DRAINING,
            "fixture-decommission-request"
        );
        Metadata metadata = Metadata.builder().putCustom(DecommissionAttributeMetadata.TYPE, decommissionMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(47L)
            .stateUUID("fixture-state-with-decommission-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseMiscCustomMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        RepositoryMetadata repository = new RepositoryMetadata(
            "fixture-aggregate-repo",
            "fs",
            Settings.builder().put("location", "/tmp/fixture-aggregate-repo").build()
        );
        RepositoriesMetadata repositoriesMetadata = new RepositoriesMetadata(Collections.singletonList(repository));
        WeightedRouting weightedRouting = new WeightedRouting("zone", Collections.singletonMap("zone-b", 0.75d));
        WeightedRoutingMetadata weightedRoutingMetadata = new WeightedRoutingMetadata(weightedRouting, 25L);
        View view = new View(
            "fixture-aggregate-view",
            "fixture aggregate source",
            789L,
            987L,
            Collections.singleton(new View.Target("fixture-aggregate-*"))
        );
        ViewMetadata viewMetadata = new ViewMetadata(Collections.singletonMap("fixture-aggregate-view", view));
        MutableWorkloadGroupFragment fragment = new MutableWorkloadGroupFragment(
            MutableWorkloadGroupFragment.ResiliencyMode.MONITOR,
            Collections.singletonMap(ResourceType.MEMORY, 0.25d),
            Collections.emptyMap()
        );
        WorkloadGroup workloadGroup = new WorkloadGroup("fixture-aggregate-workload", "fixture-aggregate-workload-id", fragment, 234567L);
        WorkloadGroupMetadata workloadGroupMetadata = new WorkloadGroupMetadata(
            Collections.singletonMap("fixture-aggregate-workload-id", workloadGroup)
        );
        Metadata metadata = Metadata.builder()
            .putCustom(RepositoriesMetadata.TYPE, repositoriesMetadata)
            .putCustom(WeightedRoutingMetadata.TYPE, weightedRoutingMetadata)
            .putCustom(ViewMetadata.TYPE, viewMetadata)
            .putCustom(WorkloadGroupMetadata.TYPE, workloadGroupMetadata)
            .build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(44L)
            .stateUUID("fixture-state-with-misc-custom-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseLegacyIndexTemplate() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata template = IndexTemplateMetadata.builder("fixture-template")
            .patterns(Collections.singletonList("fixture-*"))
            .order(3)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .version(7)
            .build();
        Metadata metadata = Metadata.builder().put(template).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(20L)
            .stateUUID("fixture-state-with-legacy-index-template")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseLegacyIndexTemplateMappingAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexTemplateMetadata template = IndexTemplateMetadata.builder("fixture-template-with-mapping-alias")
            .patterns(Collections.singletonList("fixture-map-*"))
            .order(4)
            .settings(Settings.builder().put("index.number_of_shards", 1).build())
            .putMapping("_doc", "{\"properties\":{\"title\":{\"type\":\"keyword\"}}}")
            .putAlias(AliasMetadata.builder("fixture-alias").build())
            .version(8)
            .build();
        Metadata metadata = Metadata.builder().put(template).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(21L)
            .stateUUID("fixture-state-with-legacy-index-template-mapping-alias")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        IndexRoutingTable indexRouting = IndexRoutingTable.builder(new Index("fixture-index", "fixture-index-uuid")).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(10L)
            .stateUUID("fixture-state-with-routing")
            .routingTable(RoutingTable.builder().add(indexRouting).build())
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadata() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(11L)
            .stateUUID("fixture-state-with-index-metadata")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataMappingAlias() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-mapping-alias-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-mapping-alias")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .putMapping("{\"properties\":{\"title\":{\"type\":\"keyword\"}}}")
            .putAlias(AliasMetadata.builder("fixture-index-alias"))
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(22L)
            .stateUUID("fixture-state-with-index-metadata-mapping-alias")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataCustomData() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-custom-data-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-custom-data")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .putCustom("fixture-custom", Collections.singletonMap("fixture-custom-key", "fixture-custom-value"))
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(23L)
            .stateUUID("fixture-state-with-index-metadata-custom-data")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataRolloverInfo() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-rollover-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-rollover")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .putRolloverInfo(new RolloverInfo("fixture-rollover-alias", Collections.emptyList(), 123456L))
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(24L)
            .stateUUID("fixture-state-with-index-metadata-rollover-info")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataRolloverCondition() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-rollover-condition-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-rollover-condition")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .putRolloverInfo(
                new RolloverInfo(
                    "fixture-rollover-condition-alias",
                    Collections.<Condition<?>>singletonList(new MaxDocsCondition(42L)),
                    234567L
                )
            )
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(25L)
            .stateUUID("fixture-state-with-index-metadata-rollover-condition")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataRolloverSizeAgeConditions() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-rollover-size-age-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-rollover-size-age")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .putRolloverInfo(
                new RolloverInfo(
                    "fixture-rollover-size-age-alias",
                    Arrays.<Condition<?>>asList(
                        new MaxAgeCondition(TimeValue.timeValueMillis(60000L)),
                        new MaxSizeCondition(new ByteSizeValue(1024L))
                    ),
                    345678L
                )
            )
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(26L)
            .stateUUID("fixture-state-with-index-metadata-rollover-size-age")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseIndexMetadataSplitShards() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-split-shards-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 3)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        SplitShardsMetadata.Builder splitShardsBuilder = new SplitShardsMetadata.Builder(3);
        splitShardsBuilder.splitShard(0, 3);
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index-split-shards")
            .settings(settings)
            .numberOfShards(3)
            .numberOfReplicas(0)
            .splitShardsMetadata(splitShardsBuilder.build())
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(27L)
            .stateUUID("fixture-state-with-index-metadata-split-shards")
            .metadata(metadata)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseShardRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        RoutingTable routingTable = RoutingTable.builder().addAsNew(indexMetadata).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(12L)
            .stateUUID("fixture-state-with-shard-routing")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseUnassignedFailure() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        UnassignedInfo unassignedInfo = new UnassignedInfo(
            UnassignedInfo.Reason.ALLOCATION_FAILED,
            "fixture allocation failed",
            new IllegalStateException("fixture shard failure"),
            1,
            System.nanoTime(),
            123456789L,
            false,
            UnassignedInfo.AllocationStatus.DECIDERS_NO,
            Collections.singleton("fixture-failed-node")
        );
        ShardRouting shard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            unassignedInfo
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(shard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(20L)
            .stateUUID("fixture-state-with-unassigned-failure")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseStartedShardRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting startedShard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "fixture started shard")
        ).initialize("fixture-node-id", null, -1L).moveToStarted();
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(startedShard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(13L)
            .stateUUID("fixture-state-with-started-shard-routing")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseInitializingShardRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting initializingShard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "fixture initializing shard")
        ).initialize("fixture-node-id", null, 12345L);
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(initializingShard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(14L)
            .stateUUID("fixture-state-with-initializing-shard-routing")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseExistingStoreRecoverySource() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting shard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.ExistingStoreRecoverySource.FORCE_STALE_PRIMARY_INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.ALLOCATION_FAILED, "fixture existing store shard")
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(shard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(17L)
            .stateUUID("fixture-state-with-existing-store-recovery-source")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseSnapshotRecoverySource() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        RecoverySource.SnapshotRecoverySource recoverySource = new RecoverySource.SnapshotRecoverySource(
            "fixture-restore-uuid",
            new Snapshot("fixture-repository", new SnapshotId("fixture-snapshot", "fixture-snapshot-uuid")),
            Version.CURRENT,
            new IndexId("fixture-index", "fixture-snapshot-index-id"),
            true,
            false,
            null,
            null,
            123456789L
        );
        ShardRouting shard = ShardRouting.newUnassigned(
            shardId,
            true,
            recoverySource,
            new UnassignedInfo(UnassignedInfo.Reason.NEW_INDEX_RESTORED, "fixture snapshot shard")
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(shard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(18L)
            .stateUUID("fixture-state-with-snapshot-recovery-source")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRemoteStoreRecoverySource() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting shard = ShardRouting.newUnassigned(
            shardId,
            true,
            new RecoverySource.RemoteStoreRecoverySource(
                "fixture-remote-restore-uuid",
                Version.CURRENT,
                new IndexId("fixture-index", "fixture-remote-index-id")
            ),
            new UnassignedInfo(UnassignedInfo.Reason.NEW_INDEX_RESTORED, "fixture remote store shard")
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(shard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(19L)
            .stateUUID("fixture-state-with-remote-store-recovery-source")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseRelocatingShardRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 0)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(0)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting relocatingShard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "fixture relocating shard")
        ).initialize("fixture-node-id", null, -1L).moveToStarted().relocate("fixture-relocating-node-id", 23456L);
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(relocatingShard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(15L)
            .stateUUID("fixture-state-with-relocating-shard-routing")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateResponseReplicaShardRouting() throws IOException {
        ClusterName clusterName = new ClusterName("fixture-cluster");
        Settings settings = Settings.builder()
            .put(IndexMetadata.SETTING_INDEX_UUID, "fixture-index-uuid")
            .put(IndexMetadata.SETTING_VERSION_CREATED, Version.CURRENT)
            .put(IndexMetadata.SETTING_NUMBER_OF_SHARDS, 1)
            .put(IndexMetadata.SETTING_NUMBER_OF_REPLICAS, 1)
            .build();
        IndexMetadata indexMetadata = IndexMetadata.builder("fixture-index")
            .settings(settings)
            .numberOfShards(1)
            .numberOfReplicas(1)
            .build();
        Metadata metadata = Metadata.builder().put(indexMetadata, false).build();
        ShardId shardId = new ShardId(indexMetadata.getIndex(), 0);
        ShardRouting primaryShard = ShardRouting.newUnassigned(
            shardId,
            true,
            RecoverySource.EmptyStoreRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.INDEX_CREATED, "fixture primary shard")
        ).initialize("fixture-node-id", null, -1L).moveToStarted();
        ShardRouting replicaShard = ShardRouting.newUnassigned(
            shardId,
            false,
            RecoverySource.PeerRecoverySource.INSTANCE,
            new UnassignedInfo(UnassignedInfo.Reason.REPLICA_ADDED, "fixture replica shard")
        );
        IndexShardRoutingTable shardRoutingTable = new IndexShardRoutingTable.Builder(shardId).addShard(primaryShard).addShard(replicaShard).build();
        IndexRoutingTable indexRoutingTable = IndexRoutingTable.builder(indexMetadata.getIndex()).addIndexShard(shardRoutingTable).build();
        RoutingTable routingTable = RoutingTable.builder().add(indexRoutingTable).build();
        ClusterState clusterState = ClusterState.builder(clusterName)
            .version(16L)
            .stateUUID("fixture-state-with-replica-shard-routing")
            .metadata(metadata)
            .routingTable(routingTable)
            .build();
        ClusterStateResponse response = new ClusterStateResponse(clusterName, clusterState, false);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            response.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateRequestDefault() throws IOException {
        ClusterStateRequest request = new ClusterStateRequest();
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(Version.CURRENT);
            request.writeTo(out);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeClusterStateTransportRequestDefault(long requestId) throws IOException {
        return serializeRequest(
            ClusterStateAction.NAME,
            new ClusterStateRequest(),
            Version.CURRENT,
            requestId,
            new String[0],
            false
        );
    }

    private static byte[] serializeVersion(Version version) throws IOException {
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.writeVersion(version);
            return BytesReference.toBytes(out.bytes());
        }
    }

    private static byte[] serializeRequest(
        String action,
        TransportRequest request,
        Version version,
        long requestId,
        String[] features,
        boolean isHandshake
    ) throws IOException {
        ThreadContext threadContext = new ThreadContext(Settings.EMPTY);
        try (BytesStreamOutput out = new BytesStreamOutput()) {
            out.setVersion(version);
            out.skip(TcpHeader.headerSize(version));

            long variableHeaderStart = out.position();
            threadContext.writeTo(out);
            out.writeStringArray(features);
            out.writeString(action);
            int variableHeaderSize = Math.toIntExact(out.position() - variableHeaderStart);

            request.writeTo(out);

            BytesReference message = out.bytes();
            out.seek(0);

            byte status = 0;
            status = TransportStatus.setRequest(status);
            if (isHandshake) {
                status = TransportStatus.setHandshake(status);
            }

            int contentSize = message.length() - TcpHeader.headerSize(version);
            TcpHeader.writeHeader(out, requestId, status, version, contentSize, variableHeaderSize);
            return BytesReference.toBytes(message);
        }
    }

    private static void emit(String name, byte[] bytes) {
        System.out.println(name + "=" + BASE64.encodeToString(bytes));
    }

    private static final class FixturePersistentTaskParams implements PersistentTaskParams {
        private static final String NAME = "fixture-persistent-task";
        private static final String MARKER = "fixture-persistent-payload";
        private static final long GENERATION = 7L;

        @Override
        public String getWriteableName() {
            return NAME;
        }

        @Override
        public Version getMinimalSupportedVersion() {
            return Version.CURRENT.minimumCompatibilityVersion();
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            out.writeString(MARKER);
            out.writeLong(GENERATION);
        }

        @Override
        public XContentBuilder toXContent(XContentBuilder builder, Params params) throws IOException {
            return builder.startObject().field("marker", MARKER).field("generation", GENERATION).endObject();
        }
    }

    private static final class FixturePersistentTaskState implements PersistentTaskState {
        private static final String MARKER = "fixture-persistent-state";
        private static final long GENERATION = 11L;

        @Override
        public String getWriteableName() {
            return FixturePersistentTaskParams.NAME;
        }

        @Override
        public void writeTo(StreamOutput out) throws IOException {
            out.writeString(MARKER);
            out.writeLong(GENERATION);
        }

        @Override
        public XContentBuilder toXContent(XContentBuilder builder, Params params) throws IOException {
            return builder.startObject().field("marker", MARKER).field("generation", GENERATION).endObject();
        }
    }
}
