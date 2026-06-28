#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENSEARCH_ROOT="${OPENSEARCH_ROOT:-/home/ubuntu/OpenSearch}"
KNN_ROOT="${KNN_ROOT:-/home/ubuntu/k-NN}"
OUT_DIR="${OUT_DIR:-${ROOT}/docs/rust-port/generated}"
EXPECTED_OPENSEARCH_COMMIT="${EXPECTED_OPENSEARCH_COMMIT:-f991609d190dfd91c8a09902053a7bbfe0c27b3e}"
EXPECTED_KNN_COMMIT="${EXPECTED_KNN_COMMIT:-86ad5668acddbcf57d62ee0a3db17385aa93fde0}"

require_tool() {
  local tool="$1"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "missing required tool: ${tool}" >&2
    exit 127
  fi
}

repo_commit() {
  git -C "$1" rev-parse HEAD
}

assert_commit() {
  local label="$1"
  local root="$2"
  local expected="$3"
  local actual
  actual="$(repo_commit "${root}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "${label} commit mismatch" >&2
    echo "  root:     ${root}" >&2
    echo "  expected: ${expected}" >&2
    echo "  actual:   ${actual}" >&2
    exit 3
  fi
}

route_status() {
  local source="$1"
  local method="$2"
  local path="$3"

  if [[ "${source}" == "${KNN_ROOT}"/* ]]; then
    case "${source}" in
      *"/RestClearCacheHandler.java"|*"/RestDeleteModelHandler.java"|*"/RestGetModelHandler.java"|*"/RestKNNStatsHandler.java"|*"/RestKNNWarmupHandler.java"|*"/RestSearchModelHandler.java"|*"/RestTrainModelHandler.java")
        echo "implemented"
        return
        ;;
    esac
    echo "planned"
    return
  fi

  if [[ "${source}" == "${OPENSEARCH_ROOT}/plugins/"* ]]; then
    echo "out-of-scope"
    return
  fi

  if [[ "${source}" == *"/modules/opensearch-dashboards/"* && "${path}" == *'/_opensearch_dashboards'*'route.getPath('* ]]; then
    echo "out-of-scope"
    return
  fi

  if [[ "${source}" == *"/RestDeleteIndexAction.java" && "${method}" == "DELETE" && "${path}" == "/" ]]; then
    echo "out-of-scope"
    return
  fi

  case "${method} ${path}" in
    'GET "/" + ENDPOINT'|'POST "/" + ENDPOINT'|'GET "/{index}/" + ENDPOINT'|'POST "/{index}/" + ENDPOINT')
      echo "implemented"
      return
      ;;
    "POST /{index}/_delete_by_query"|"POST /_reindex"|"POST /{index}/_update_by_query"|"POST /_update_by_query/{taskId}/_rethrottle"|"POST /_delete_by_query/{taskId}/_rethrottle"|"POST /_reindex/{taskId}/_rethrottle")
      echo "implemented"
      return
      ;;
    "POST /_filecache/prune")
      echo "implemented"
      return
      ;;
    "GET _wlm/stats"|"GET _wlm/{nodeId}/stats"|"GET _wlm/stats/{workloadGroupId}"|"GET _wlm/{nodeId}/stats/{workloadGroupId}"|"GET _list/wlm_stats"|"GET _list/wlm_stats/{nodeId}/stats"|"GET _list/wlm_stats/stats/{workloadGroupId}"|"GET _list/wlm_stats/{nodeId}/stats/{workloadGroupId}")
      echo "implemented"
      return
      ;;
    "PUT /{index}/_block/{block}"|"POST /_open"|"POST /{index}/_open"|"POST /{index}/ingestion/_pause"|"POST /{index}/ingestion/_resume"|"GET /{index}/ingestion/_state")
      echo "implemented"
      return
      ;;
    "POST /{index}/_shrink/{target}"|"PUT /{index}/_shrink/{target}"|"POST /{index}/_split/{target}"|"PUT /{index}/_split/{target}"|"POST /{index}/_clone/{target}"|"PUT /{index}/_clone/{target}"|"POST /{index}/_scale"|"POST /{index}/_rollover"|"POST /{index}/_rollover/{new_index}"|"GET /_resolve/index/{name}")
      echo "implemented"
      return
      ;;
    "GET /_flush/synced"|"POST /_flush/synced"|"GET /{index}/_flush/synced"|"POST /{index}/_flush/synced"|"POST /_upgrade"|"POST /{index}/_upgrade"|"GET /_upgrade"|"GET /{index}/_upgrade")
      echo "implemented"
      return
      ;;
    "GET /_cat"|"GET /_cat/nodeattrs"|"GET /_cat/repositories"|"GET /_cat/snapshots"|"GET /_cat/snapshots/{repository}")
      echo "implemented"
      return
      ;;
    "POST /_cluster/voting_config_exclusions"|"DELETE /_cluster/voting_config_exclusions")
      echo "implemented"
      return
      ;;
    "DELETE /_cluster/routing/awareness/weights"|"DELETE /_cluster/routing/awareness/{attribute}/weights"|"GET /_cluster/routing/awareness/{attribute}/weights"|"PUT /_cluster/routing/awareness/{attribute}/weights")
      echo "implemented"
      return
      ;;
    'POST "/{index}/_tier/" + targetTier'|"POST /_tier/_cancel/{index}"|"GET /{index}/_tier"|"GET /_tier/all")
      echo "implemented"
      return
      ;;
  esac

  case "${method} ${path}" in
    "GET /_cluster/allocation/explain"|"POST /_cluster/allocation/explain"|"GET /_cluster/pending_tasks"|"GET /_cluster/stats"|"GET /_cluster/stats/nodes/{nodeId}"|"GET /_cluster/stats/{metric}/nodes/{nodeId}"|"GET /_cluster/stats/{metric}/{index_metric}/nodes/{nodeId}"|"GET /_tasks"|"GET /_tasks/{task_id}"|"POST /_tasks/_cancel"|"POST /_tasks/{task_id}/_cancel"|"GET /_remote/info"|"GET /_cat/nodes"|"GET /_cat/pending_tasks"|"GET /_cat/thread_pool"|"GET /_cat/thread_pool/{thread_pool_patterns}")
      echo "implemented"
      return
      ;;
    "GET /_cluster/health/{index}"|"POST /_cluster/reroute"|"PUT /_cluster/decommission/awareness/{awareness_attribute_name}/{awareness_attribute_value}"|"DELETE /_cluster/decommission/awareness"|"GET /_cluster/decommission/awareness/{awareness_attribute_name}/_status")
      echo "implemented"
      return
      ;;
    "GET /_dangling"|"POST /_dangling/{index_uuid}"|"DELETE /_dangling/{index_uuid}")
      echo "implemented"
      return
      ;;
    "GET /_script_context"|"GET /_script_language"|"GET /_scripts/{id}"|"POST /_scripts/{id}"|"PUT /_scripts/{id}"|"POST /_scripts/{id}/{context}"|"PUT /_scripts/{id}/{context}"|"DELETE /_scripts/{id}")
      echo "implemented"
      return
      ;;
    "GET /_remotestore/metadata/{index}"|"GET /_remotestore/metadata/{index}/{shard_id}"|"GET /_remotestore/stats/{index}"|"GET /_remotestore/stats/{index}/{shard_id}"|"POST /_remotestore/_restore")
      echo "implemented"
      return
      ;;
    "GET /_snapshot"|"GET /_snapshot/{repository}"|"POST /_snapshot/{repository}"|"PUT /_snapshot/{repository}"|"DELETE /_snapshot/{repository}"|"POST /_snapshot/{repository}/_verify"|"POST /_snapshot/{repository}/_cleanup")
      echo "implemented"
      return
      ;;
    "POST /_snapshot/{repository}/{snapshot}"|"PUT /_snapshot/{repository}/{snapshot}"|"GET /_snapshot/{repository}/{snapshot}"|"DELETE /_snapshot/{repository}/{snapshot}"|"PUT /_snapshot/{repository}/{snapshot}/_clone/{target_snapshot}"|"POST /_snapshot/{repository}/{snapshot}/_restore")
      echo "implemented"
      return
      ;;
    "GET /_snapshot/_status"|"GET /_snapshot/{repository}/_status"|"GET /_snapshot/{repository}/{snapshot}/_status"|"GET /_snapshot/{repository}/{snapshot}/{index}/_status")
      echo "implemented"
      return
      ;;
    "GET /_analyze"|"POST /_analyze"|"GET /{index}/_analyze"|"POST /{index}/_analyze")
      echo "implemented"
      return
      ;;
    "POST /_cache/clear"|"POST /{index}/_cache/clear"|"POST /_close"|"POST /{index}/_close"|"GET /_flush"|"POST /_flush"|"GET /{index}/_flush"|"POST /{index}/_flush"|"POST /_forcemerge"|"POST /{index}/_forcemerge")
      echo "implemented"
      return
      ;;
    "GET /_shard_stores"|"GET /{index}/_shard_stores"|"GET /_stats"|"GET /_stats/{metric}"|"GET /{index}/_stats"|"GET /{index}/_stats/{metric}")
      echo "implemented"
      return
      ;;
    "PUT /_data_stream/{name}"|"DELETE /_data_stream/{name}"|"GET /_data_stream"|"GET /_data_stream/{name}"|"GET /_data_stream/_stats"|"GET /_data_stream/{name}/_stats")
      echo "implemented"
      return
      ;;
    "GET /_component_template"|"GET /_component_template/{name}"|"HEAD /_component_template/{name}"|"POST /_component_template/{name}"|"PUT /_component_template/{name}"|"DELETE /_component_template/{name}")
      echo "implemented"
      return
      ;;
    "GET /_index_template"|"GET /_index_template/{name}"|"HEAD /_index_template/{name}"|"POST /_index_template/{name}"|"PUT /_index_template/{name}"|"DELETE /_index_template/{name}"|"POST /_index_template/_simulate_index/{name}"|"POST /_index_template/_simulate"|"POST /_index_template/_simulate/{name}")
      echo "implemented"
      return
      ;;
    "GET /_template"|"GET /_template/{name}"|"HEAD /_template/{name}"|"POST /_template/{name}"|"PUT /_template/{name}"|"DELETE /_template/{name}")
      echo "implemented"
      return
      ;;
    "GET /_cat/aliases"|"GET /_cat/aliases/{alias}"|"GET /_cat/allocation"|"GET /_cat/allocation/{nodes}"|"GET /_cat/count"|"GET /_cat/count/{index}"|"GET /_cat/fielddata"|"GET /_cat/fielddata/{fields}"|"GET /_cat/health"|"GET /_cat/indices"|"GET /_cat/indices/{index}")
      echo "implemented"
      return
      ;;
    "GET /_cat/plugins"|"GET /_cat/recovery"|"GET /_cat/recovery/{index}"|"GET /_cat/segments"|"GET /_cat/segments/{index}"|"GET /_cat/shards"|"GET /_cat/shards/{index}"|"GET /_cat/tasks"|"GET /_cat/templates"|"GET /_cat/templates/{name}")
      echo "implemented"
      return
      ;;
  esac

  case "${method} ${path}" in
    "GET /"|"HEAD /")
      echo "implemented"
      ;;
    "GET /_msearch/template"|"POST /_msearch/template"|"GET /{index}/_msearch/template"|"POST /{index}/_msearch/template"|"GET /_render/template"|"POST /_render/template"|"GET /_render/template/{id}"|"POST /_render/template/{id}"|"GET /_search/template"|"POST /_search/template"|"GET /{index}/_search/template"|"POST /{index}/_search/template")
      echo "implemented"
      ;;
    "GET /_ingest/processor/grok"|"GET /_scripts/painless/_context"|"GET /_scripts/painless/_execute"|"POST /_scripts/painless/_execute")
      echo "implemented"
      ;;
    "DELETE /_ingest/pipeline/{id}"|"GET /_ingest/pipeline"|"GET /_ingest/pipeline/{id}"|"PUT /_ingest/pipeline/{id}"|"GET /_ingest/pipeline/{id}/_simulate"|"POST /_ingest/pipeline/{id}/_simulate"|"GET /_ingest/pipeline/_simulate"|"POST /_ingest/pipeline/_simulate")
      echo "implemented"
      ;;
    "GET /_cluster/health"|"PUT /{index}"|"GET /{index}"|"DELETE /{index}")
      echo "implemented"
      ;;
    "POST /_nodes/reload_secure_settings"|"POST /_nodes/{nodeId}/reload_secure_settings"|"GET /_cluster/settings"|"PUT /_cluster/settings"|"GET /_cluster/state"|"GET /_cluster/state/{metric}"|"GET /_cluster/state/{metric}/{indices}"|"GET /_nodes"|"GET /_nodes/{nodeId}"|"GET /_nodes/{nodeId}/{metrics}"|"GET /_nodes/{nodeId}/info/{metrics}"|"GET /_nodes/stats"|"GET /_nodes/{nodeId}/stats"|"GET /_nodes/stats/{metric}"|"GET /_nodes/{nodeId}/stats/{metric}"|"GET /_nodes/stats/{metric}/{index_metric}"|"GET /_nodes/{nodeId}/stats/{metric}/{index_metric}"|"GET /_nodes/usage"|"GET /_nodes/{nodeId}/usage"|"GET /_nodes/usage/{metric}"|"GET /_nodes/{nodeId}/usage/{metric}"|"GET /_nodes/hot_threads"|"GET /_nodes/{nodeId}/hot_threads"|"GET /_segments"|"GET /{index}/_segments"|"GET /_recovery"|"GET /{index}/_recovery"|"GET /_field_caps"|"POST /_field_caps"|"GET /{index}/_field_caps"|"POST /{index}/_field_caps"|"GET /_mapping"|"GET /_mappings"|"GET /{index}/_mapping"|"GET /{index}/_mappings"|"GET /_mapping/field/{fields}"|"GET /{index}/_mapping/field/{fields}"|"POST /{index}/_mapping"|"PUT /{index}/_mapping"|"POST /{index}/_mappings"|"PUT /{index}/_mappings"|"GET /_settings"|"GET /_settings/{name}"|"GET /{index}/_settings"|"GET /{index}/_settings/{name}"|"GET /{index}/_setting/{name}"|"PUT /_settings"|"PUT /{index}/_settings"|"GET /_refresh"|"POST /_refresh"|"GET /{index}/_refresh"|"POST /{index}/_refresh"|"GET /_count"|"POST /_count"|"GET /{index}/_count"|"POST /{index}/_count"|"GET /_validate/query"|"POST /_validate/query"|"GET /{index}/_validate/query"|"POST /{index}/_validate/query"|"POST /_bulk"|"PUT /_bulk"|"POST /{index}/_bulk"|"PUT /{index}/_bulk"|"POST /_bulk/stream"|"PUT /_bulk/stream"|"POST /{index}/_bulk/stream"|"PUT /{index}/_bulk/stream"|"GET /{index}/_doc/{id}"|"HEAD /{index}/_doc/{id}"|"PUT /{index}/_doc/{id}"|"POST /{index}/_doc/{id}"|"POST /{index}/_doc"|"POST /{index}/_create/{id}"|"PUT /{index}/_create/{id}"|"DELETE /{index}/_doc/{id}"|"POST /{index}/_update/{id}"|"GET /{index}/_source/{id}"|"HEAD /{index}/_source/{id}"|"HEAD /{index}"|"GET /_mget"|"POST /_mget"|"GET /{index}/_mget"|"POST /{index}/_mget"|"GET /_mtermvectors"|"POST /_mtermvectors"|"GET /{index}/_mtermvectors"|"POST /{index}/_mtermvectors"|"GET /{index}/_termvectors"|"POST /{index}/_termvectors"|"GET /{index}/_termvectors/{id}"|"POST /{index}/_termvectors/{id}"|"GET /{index}/_explain/{id}"|"POST /{index}/_explain/{id}"|"GET /_search"|"POST /_search"|"GET /{index}/_search"|"POST /{index}/_search"|"GET /_msearch"|"POST /_msearch"|"GET /{index}/_msearch"|"POST /{index}/_msearch"|"GET /_search_shards"|"POST /_search_shards"|"GET /{index}/_search_shards"|"POST /{index}/_search_shards"|"GET /_alias"|"GET /_aliases"|"GET /_alias/{name}"|"HEAD /_alias/{name}"|"GET /{index}/_alias"|"HEAD /{index}/_alias"|"GET /{index}/_alias/{name}"|"HEAD /{index}/_alias/{name}"|"POST /{index}/_alias/{name}"|"PUT /{index}/_alias/{name}"|"POST /_alias/{name}"|"PUT /_alias/{name}"|"POST /{index}/_aliases/{name}"|"PUT /{index}/_aliases/{name}"|"POST /_aliases/{name}"|"PUT /_aliases/{name}"|"PUT /{index}/_alias"|"PUT /{index}/_aliases"|"PUT /_alias"|"POST /_aliases"|"DELETE /{index}/_alias/{name}"|"DELETE /{index}/_aliases/{name}"|"GET /_search/pipeline"|"GET /_search/pipeline/{id}"|"PUT /_search/pipeline/{id}"|"DELETE /_search/pipeline/{id}"|"GET /_search/scroll"|"POST /_search/scroll"|"GET /_search/scroll/{scroll_id}"|"POST /_search/scroll/{scroll_id}"|"DELETE /_search/scroll"|"DELETE /_search/scroll/{scroll_id}"|"POST /{index}/_search/point_in_time"|"DELETE /_search/point_in_time"|"DELETE /_search/point_in_time/_all"|"GET /_search/point_in_time/_all"|"GET /_cat/pit_segments"|"GET /_cat/pit_segments/_all"|"GET /_list"|"GET /_list/indices"|"GET /_list/indices/{index}"|"GET /_list/shards"|"GET /_list/shards/{index}")
      echo "implemented"
      ;;
    *)
      echo "planned"
      ;;
  esac
}

action_status() {
  local source="$1"
  local action="$2"

  if [[ "${source}" == "${KNN_ROOT}"/* ]]; then
    case "${action}" in
      KNNStatsAction.INSTANCE|KNNWarmupAction.INSTANCE|UpdateModelMetadataAction.INSTANCE|TrainingJobRouteDecisionInfoAction.INSTANCE|GetModelAction.INSTANCE|DeleteModelAction.INSTANCE|TrainingJobRouterAction.INSTANCE|TrainingModelAction.INSTANCE|RemoveModelFromCacheAction.INSTANCE|SearchModelAction.INSTANCE|UpdateModelGraveyardAction.INSTANCE|ClearCacheAction.INSTANCE)
        echo "partial"
        ;;
      *)
        echo "planned"
        ;;
    esac
    return
  fi

  case "${action}" in
    ValidateQueryAction.INSTANCE|FlushAction.INSTANCE|ClearIndicesCacheAction.INSTANCE|ForceMergeAction.INSTANCE|UpgradeAction.INSTANCE|UpgradeStatusAction.INSTANCE|SearchAction.INSTANCE|StreamSearchAction.INSTANCE|SearchScrollAction.INSTANCE|MultiSearchAction.INSTANCE|ExplainAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    GetIndexAction.INSTANCE|IndicesExistsAction.INSTANCE|GetIndexTemplatesAction.INSTANCE|GetComponentTemplateAction.INSTANCE|GetComposableIndexTemplateAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    PutIndexTemplateAction.INSTANCE|DeleteIndexTemplateAction.INSTANCE|PutComponentTemplateAction.INSTANCE|DeleteComponentTemplateAction.INSTANCE|PutComposableIndexTemplateAction.INSTANCE|CreateDataStreamAction.INSTANCE|DeleteDataStreamAction.INSTANCE|ResolveIndexAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    DeleteComposableIndexTemplateAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    GetStoredScriptAction.INSTANCE|GetScriptContextAction.INSTANCE|GetScriptLanguageAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    PutSearchPipelineAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    SimulatePipelineAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    PutPipelineAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    DeletePipelineAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    PutStoredScriptAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    DeleteStoredScriptAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    PutMappingAction.INSTANCE|AutoPutMappingAction.INSTANCE|IndicesAliasesAction.INSTANCE|UpdateSettingsAction.INSTANCE|ScaleIndexAction.INSTANCE|AnalyzeAction.INSTANCE|CreateIndexAction.INSTANCE|AutoCreateAction.INSTANCE|DeleteIndexAction.INSTANCE|OpenIndexAction.INSTANCE|CloseIndexAction.INSTANCE|AddIndexBlockAction.INSTANCE)
      echo "implemented"
      return
      ;;
  esac

  case "${action}" in
    MainAction.INSTANCE|NodesInfoAction.INSTANCE|RemoteInfoAction.INSTANCE|NodesStatsAction.INSTANCE|WlmStatsAction.INSTANCE|NodesUsageAction.INSTANCE|NodesHotThreadsAction.INSTANCE|ListTasksAction.INSTANCE|GetTaskAction.INSTANCE|CancelTasksAction.INSTANCE|ClusterStateAction.INSTANCE|GetTermVersionAction.INSTANCE|ClusterHealthAction.INSTANCE|ClusterSearchShardsAction.INSTANCE|PendingClusterTasksAction.INSTANCE|RemoteStoreStatsAction.INSTANCE|GetRepositoriesAction.INSTANCE|IndicesStatsAction.INSTANCE|ClusterStatsAction.INSTANCE|CatShardsAction.INSTANCE|IndicesSegmentsAction.INSTANCE|IndicesShardStoresAction.INSTANCE|GetMappingsAction.INSTANCE|GetFieldMappingsAction.INSTANCE|RefreshAction.INSTANCE|GetAliasesAction.INSTANCE|GetSettingsAction.INSTANCE|IndexAction.INSTANCE|GetAction.INSTANCE|DeleteAction.INSTANCE|UpdateAction.INSTANCE|MultiGetAction.INSTANCE|BulkAction.INSTANCE|ClearScrollAction.INSTANCE|RecoveryAction.INSTANCE|SegmentReplicationStatsAction.INSTANCE|GetDataStreamAction.INSTANCE|DataStreamsStatsAction.INSTANCE|ListViewNamesAction.INSTANCE|ListDanglingIndicesAction.INSTANCE|FindDanglingIndexAction.INSTANCE|CreatePitAction.INSTANCE|DeletePitAction.INSTANCE|PitSegmentsAction.INSTANCE|GetAllPitsAction.INSTANCE|FieldCapabilitiesAction.INSTANCE|GetPipelineAction.INSTANCE|GetSearchPipelineAction.INSTANCE|DeleteSearchPipelineAction.INSTANCE|RemoteStoreMetadataAction.INSTANCE|AddVotingConfigExclusionsAction.INSTANCE|ClearVotingConfigExclusionsAction.INSTANCE|ClusterGetWeightedRoutingAction.INSTANCE|GetDecommissionStateAction.INSTANCE|DeleteDecommissionStateAction.INSTANCE)
      echo "implemented"
      ;;
    ClusterAllocationExplainAction.INSTANCE|ClusterUpdateSettingsAction.INSTANCE|ClusterRerouteAction.INSTANCE|PruneFileCacheAction.INSTANCE|PutRepositoryAction.INSTANCE|DeleteRepositoryAction.INSTANCE|VerifyRepositoryAction.INSTANCE|CleanupRepositoryAction.INSTANCE|GetSnapshotsAction.INSTANCE|DeleteSnapshotAction.INSTANCE|CreateSnapshotAction.INSTANCE|CloneSnapshotAction.INSTANCE|RestoreSnapshotAction.INSTANCE|SnapshotsStatusAction.INSTANCE|ClusterAddWeightedRoutingAction.INSTANCE|ClusterDeleteWeightedRoutingAction.INSTANCE|ResizeAction.INSTANCE|RolloverAction.INSTANCE|GetIndexAction.INSTANCE|IndicesExistsAction.INSTANCE|PutIndexTemplateAction.INSTANCE|GetIndexTemplatesAction.INSTANCE|DeleteIndexTemplateAction.INSTANCE|PutComponentTemplateAction.INSTANCE|GetComponentTemplateAction.INSTANCE|DeleteComponentTemplateAction.INSTANCE|GetComposableIndexTemplateAction.INSTANCE|DeleteComposableIndexTemplateAction.INSTANCE|SimulateIndexTemplateAction.INSTANCE|SimulateTemplateAction.INSTANCE|ValidateQueryAction.INSTANCE|FlushAction.INSTANCE|ForceMergeAction.INSTANCE|UpgradeAction.INSTANCE|UpgradeStatusAction.INSTANCE|UpgradeSettingsAction.INSTANCE|ClearIndicesCacheAction.INSTANCE|TermVectorsAction.INSTANCE|MultiTermVectorsAction.INSTANCE|SearchAction.INSTANCE|StreamSearchAction.INSTANCE|SearchScrollAction.INSTANCE|MultiSearchAction.INSTANCE|ExplainAction.INSTANCE|NodesReloadSecureSettingsAction.INSTANCE|GetStoredScriptAction.INSTANCE|GetScriptContextAction.INSTANCE|GetScriptLanguageAction.INSTANCE|CreateDataStreamAction.INSTANCE|DeleteDataStreamAction.INSTANCE|ResolveIndexAction.INSTANCE|CreateViewAction.INSTANCE|DeleteViewAction.INSTANCE|GetViewAction.INSTANCE|UpdateViewAction.INSTANCE|SearchViewAction.INSTANCE|StartPersistentTaskAction.INSTANCE|UpdatePersistentTaskStatusAction.INSTANCE|CompletionPersistentTaskAction.INSTANCE|RemovePersistentTaskAction.INSTANCE|RetentionLeaseActions.Add.INSTANCE|RetentionLeaseActions.Renew.INSTANCE|RetentionLeaseActions.Remove.INSTANCE|ImportDanglingIndexAction.INSTANCE|DeleteDanglingIndexAction.INSTANCE|RestoreRemoteStoreAction.INSTANCE|ExtensionProxyAction.INSTANCE|DecommissionAction.INSTANCE|PauseIngestionAction.INSTANCE|ResumeIngestionAction.INSTANCE|GetIngestionStateAction.INSTANCE|UpdateIngestionStateAction.INSTANCE|ListTieringStatusAction.INSTANCE|GetTieringStatusAction.INSTANCE)
      echo "partial"
      ;;
    *)
      echo "planned"
      ;;
  esac
}

search_registration_status() {
  local category="$1"
  local text="$2"

  case "${category}" in
    query)
      case "${text}" in
        *MatchQueryBuilder.NAME*|*MatchPhraseQueryBuilder.NAME*|*MatchPhrasePrefixQueryBuilder.NAME*|*MatchBoolPrefixQueryBuilder.NAME*|*MultiMatchQueryBuilder.NAME*|*CombinedFieldsQueryBuilder.NAME*|*QueryStringQueryBuilder.NAME*|*SimpleQueryStringBuilder.NAME*|*MoreLikeThisQueryBuilder.NAME*|*BoolQueryBuilder.NAME*|*BoostingQueryBuilder.NAME*|*ConstantScoreQueryBuilder.NAME*|*DisMaxQueryBuilder.NAME*|*FunctionScoreQueryBuilder.NAME*|*ScriptScoreQueryBuilder.NAME*|*ScriptQueryBuilder.NAME*|*IntervalQueryBuilder.NAME*|*TemplateQueryBuilder.NAME*|*MatchAllQueryBuilder.NAME*|*MatchNoneQueryBuilder.NAME*|*TermQueryBuilder.NAME*|*TermsQueryBuilder.NAME*|*TermsSetQueryBuilder.NAME*|*RangeQueryBuilder.NAME*|*ExistsQueryBuilder.NAME*|*IdsQueryBuilder.NAME*|*PrefixQueryBuilder.NAME*|*WildcardQueryBuilder.NAME*|*RegexpQueryBuilder.NAME*|*FuzzyQueryBuilder.NAME*|*WrapperQueryBuilder.NAME*|*NestedQueryBuilder.NAME*|*GeoDistanceQueryBuilder.NAME*|*GeoBoundingBoxQueryBuilder.NAME*|*GeoPolygonQueryBuilder.NAME*|*GeoShapeQueryBuilder.NAME*|*DistanceFeatureQueryBuilder.NAME*|*RankFeatureQueryBuilder.NAME*|*PinnedQueryBuilder.NAME*|*SpanTermQueryBuilder.NAME*|*SpanGapQueryBuilder.NAME*|*SpanOrQueryBuilder.NAME*|*SpanFirstQueryBuilder.NAME*|*SpanNearQueryBuilder.NAME*|*SpanNotQueryBuilder.NAME*|*SpanContainingQueryBuilder.NAME*|*SpanWithinQueryBuilder.NAME*|*SpanMultiTermQueryBuilder.NAME*|*FieldMaskingSpanQueryBuilder.SPAN_FIELD_MASKING_FIELD*)
          echo "implemented"
          return
          ;;
      esac
      ;;
    aggregation)
      case "${text}" in
        *'TermsAggregationBuilder.NAME'*|*'DateHistogramAggregationBuilder.NAME'*|*'AutoDateHistogramAggregationBuilder.NAME'*|*'HistogramAggregationBuilder.NAME'*|*'VariableWidthHistogramAggregationBuilder.NAME'*|*'RangeAggregationBuilder.NAME'*|*'MinAggregationBuilder.NAME'*|*'MaxAggregationBuilder.NAME'*|*'SumAggregationBuilder.NAME'*|*'AvgAggregationBuilder.NAME'*|*'WeightedAvgAggregationBuilder.NAME'*|*'StatsAggregationBuilder.NAME'*|*'ExtendedStatsAggregationBuilder.NAME'*|*'PercentilesAggregationBuilder.NAME'*|*'PercentileRanksAggregationBuilder.NAME'*|*'MedianAbsoluteDeviationAggregationBuilder.NAME'*|*'CardinalityAggregationBuilder.NAME'*|*'ValueCountAggregationBuilder.NAME'*|*'GlobalAggregationBuilder.NAME'*|*'MissingAggregationBuilder.NAME'*|*'FilterAggregationBuilder.NAME'*|*'FiltersAggregationBuilder.NAME'*|*'AdjacencyMatrixAggregationBuilder.NAME'*|*'NestedAggregationBuilder.NAME'*|*'ReverseNestedAggregationBuilder.NAME'*|*'TopHitsAggregationBuilder.NAME'*|*'CompositeAggregationBuilder.NAME'*|*'SamplerAggregationBuilder.NAME'*|*'DiversifiedAggregationBuilder.NAME'*|*'RareTermsAggregationBuilder.NAME'*|*'SignificantTermsAggregationBuilder.NAME'*|*'SignificantTextAggregationBuilder.NAME'*|*'DateRangeAggregationBuilder.NAME'*|*'IpRangeAggregationBuilder.NAME'*|*'MultiTermsAggregationBuilder.NAME'*|*'GeoDistanceAggregationBuilder.NAME'*|*'GeoCentroidAggregationBuilder.NAME'*|*'ScriptedMetricAggregationBuilder.NAME'*)
          echo "implemented"
          return
          ;;
      esac
      ;;
    pipeline_aggregation)
      case "${text}" in
        *DerivativePipelineAggregationBuilder.NAME*|*MaxBucketPipelineAggregationBuilder.NAME*|*MinBucketPipelineAggregationBuilder.NAME*|*AvgBucketPipelineAggregationBuilder.NAME*|*SumBucketPipelineAggregationBuilder.NAME*|*StatsBucketPipelineAggregationBuilder.NAME*|*ExtendedStatsBucketPipelineAggregationBuilder.NAME*|*PercentilesBucketPipelineAggregationBuilder.NAME*|*MovAvgPipelineAggregationBuilder.NAME*|*CumulativeSumPipelineAggregationBuilder.NAME*|*BucketScriptPipelineAggregationBuilder.NAME*|*BucketSelectorPipelineAggregationBuilder.NAME*|*BucketSortPipelineAggregationBuilder.NAME*|*SerialDiffPipelineAggregationBuilder.NAME*|*MovFnPipelineAggregationBuilder.NAME*)
          echo "implemented"
          return
          ;;
      esac
      ;;
    suggester)
      case "${text}" in
        *TermSuggestionBuilder.SUGGESTION_NAME*|*PhraseSuggestionBuilder.SUGGESTION_NAME*|*CompletionSuggestionBuilder.SUGGESTION_NAME*)
          echo "implemented"
          return
          ;;
      esac
      ;;
    score_function)
      case "${text}" in
        *ScriptScoreFunctionBuilder.NAME*|*GaussDecayFunctionBuilder.NAME*|*LinearDecayFunctionBuilder.NAME*|*ExponentialDecayFunctionBuilder.NAME*|*RandomScoreFunctionBuilder.NAME*|*FieldValueFactorFunctionBuilder.NAME*)
          echo "implemented"
          return
          ;;
      esac
      ;;
    fetch_subphase)
      case "${text}" in
        *ExplainPhase*|*FetchSourcePhase*|*FetchScorePhase*|*HighlightPhase*|*MatchedQueriesPhase*|*FetchDocValuesPhase*|*ScriptFieldsPhase*|*FetchFieldsPhase*|*FetchVersionPhase*|*SeqNoPrimaryTermPhase*)
          echo "implemented"
          return
          ;;
      esac
      ;;
  esac

  echo "planned"
}

extract_search_registrations() {
  local output="$1"
  {
    printf 'status\tcategory\texpression\tsource\tline\n'
    perl -0777 -ne '
      while (/(registerQuery|registerAggregation|registerPipelineAggregation|registerSuggester|registerScoreFunction|registerFetchSubPhase)\s*\(((?:[^()]++|\((?-1)?\))*)\)/sg) {
        my $kind = $1;
        my $args = $2;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        $args =~ s/\s+/ /g;
        $args =~ s/^\s+|\s+$//g;
        print "$kind\t$args\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/search/SearchModule.java" |
      while IFS=$'\t' read -r kind text line; do
        local category status
        case "${kind}" in
          registerQuery) category="query" ;;
          registerAggregation) category="aggregation" ;;
          registerPipelineAggregation) category="pipeline_aggregation" ;;
          registerSuggester) category="suggester" ;;
          registerScoreFunction) category="score_function" ;;
          registerFetchSubPhase) category="fetch_subphase" ;;
          *) category="other" ;;
        esac
        status="$(search_registration_status "${category}" "${text}")"
        printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${category}" "${text}" "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/search/SearchModule.java" "${line}"
      done
  } >"${output}"
}

node_runtime_component_status() {
  local component="$1"

  case "${component}" in
    NetworkService|TransportService|StreamTransportService|SearchTransportService|StreamSearchTransportService)
      echo "partial"
      return
      ;;
    LocalClusterService|ClusterService|BatchedRerouteService|InternalClusterInfoService|ClusterModule)
      echo "partial"
      return
      ;;
    IndicesModule|IndicesService|MetadataCreateIndexService|MetadataCreateDataStreamService|MetadataIndexUpgradeService|SystemIndexMetadataUpgradeService|TemplateUpgradeService|ViewService|MappingTransformerRegistry)
      echo "partial"
      return
      ;;
    SearchModule|SearchService|SearchPhaseController|SearchPipelineService|ResponseCollectorService|SearchBackpressureService)
      echo "partial"
      return
      ;;
    ScriptModule|ScriptService|AnalysisModule|IngestService)
      echo "partial"
      return
      ;;
    SettingsModule|TelemetryModule|UsageService|MonitorService|NodeService|FsHealthService)
      echo "partial"
      return
      ;;
    RepositoriesModule|SnapshotsService|SnapshotShardsService|RestoreService|RemoteStoreRestoreService|InternalSnapshotsInfoService)
      echo "partial"
      return
      ;;
    GatewayModule|MetaStateService|PersistedClusterStateService|PersistedStateRegistry)
      echo "partial"
      return
      ;;
    TaskResourceTrackingService|TaskCancellationMonitoringService|TaskCancellationService|PersistentTasksExecutorRegistry|PersistentTasksClusterService|PersistentTasksService)
      echo "partial"
      return
      ;;
    ActionModule|NamedWriteableRegistry|NamedXContentRegistry|DataFormatRegistry)
      echo "partial"
      return
      ;;
    CacheModule|IndexingPressureService|AdmissionControlService|ResourceUsageCollectorService|HierarchyCircuitBreakerService|NoneCircuitBreakerService)
      echo "partial"
      return
      ;;
  esac

  echo "planned"
}

extract_node_runtime_components() {
  local output="$1"
  {
    printf 'status\tkind\tcomponent\tsource\tline\n'
    perl -0777 -ne '
      while (/new\s+([A-Za-z0-9_]+(?:Module|Service|Gateway|Coordinator|Controller|Registry))\s*\(/sg) {
        my $component = $1;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$component\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/node/Node.java" |
      while IFS=$'\t' read -r component line; do
        local kind status
        case "${component}" in
          *Module) kind="module" ;;
          *Service) kind="service" ;;
          *Gateway) kind="gateway" ;;
          *Coordinator) kind="coordinator" ;;
          *Controller) kind="controller" ;;
          *Registry) kind="registry" ;;
          *) kind="component" ;;
        esac
        status="$(node_runtime_component_status "${component}")"
        printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${kind}" "${component}" "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/node/Node.java" "${line}"
      done
  } >"${output}"
}

build_compatibility_matrix() {
  local output="$1"
  local rest_routes="$2"
  local transport_actions="$3"
  local search_registrations="$4"
  local node_runtime_components="$5"

  {
    printf 'surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n'
    awk -F '\t' 'NR > 1 { printf "rest_route\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${rest_routes}"
    awk -F '\t' 'NR > 1 { printf "transport_action\t%s\taction\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${transport_actions}"
    awk -F '\t' 'NR > 1 { printf "search_registration\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${search_registrations}"
    awk -F '\t' 'NR > 1 { printf "node_runtime\t%s\t%s\t%s\t\t%s\t%s\n", $1, $2, $3, $4, $5 }' "${node_runtime_components}"
  } >"${output}"
}

extract_rest_routes() {
  local output="$1"
  {
    printf 'status\tmethod\tpath_or_expression\tsource\tline\n'
    {
      rg -l 'new Route\(' \
        "${OPENSEARCH_ROOT}/server/src/main/java" \
        "${OPENSEARCH_ROOT}/modules" \
        "${OPENSEARCH_ROOT}/plugins" \
        "${KNN_ROOT}/src/main/java" |
        while IFS= read -r file; do
          perl -0777 -ne '
            while (/new\s+Route\s*\(\s*([^,\n]+?)\s*,\s*((?:String\.format\((?:[^()]|\([^()]*\))*\))|(?:"(?:\\.|[^"])*"(?:\s*\+\s*[^,\n)]+)*)|[^)\n]+?)\s*\)/sg) {
              my $method = $1;
              my $path = $2;
              $method =~ s/^\s+|\s+$//g;
              $path =~ s/^\s+|\s+$//g;
              my $prefix = substr($_, 0, $-[0]);
              my $line = 1 + ($prefix =~ tr/\n//);
              $method =~ s/\t/ /g;
              $path =~ s/\t/ /g;
              print "$method\t$path\t$line\n";
            }
          ' "${file}" |
            while IFS=$'\t' read -r method path_expr line; do
              local path_clean status
              method="$(printf '%s' "${method}" | sed -E 's/.*RestRequest\.Method\.//; s/.*Method\.//; s/[^A-Z_].*$//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
              path_expr="$(printf '%s' "${path_expr}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
              path_clean="${path_expr}"
              if [[ "${path_clean}" =~ ^\".*\"$ ]]; then
                path_clean="${path_clean:1:${#path_clean}-2}"
              fi
              status="$(route_status "${file}" "${method}" "${path_clean}")"
              printf '%s\t%s\t%s\t%s\t%s\n' "${status}" "${method}" "${path_clean}" "${file}" "${line}"
            done
        done
    } | sort -t $'\t' -k4,4 -k5,5n -k2,2 -k3,3
  } >"${output}"
}

extract_transport_actions() {
  local output="$1"
  {
    printf 'status\taction\ttransport_handler\tsource\tline\n'
    perl -0777 -ne '
      while (/actions\.register\(\s*([^,;]+?)\s*,\s*([^,;)]+)(?:,|\))/sg) {
        my $action = $1;
        my $handler = $2;
        $action =~ s/\s+//g;
        $handler =~ s/\s+//g;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$action\t$handler\t$line\n";
      }
    ' "${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/action/ActionModule.java" |
      while IFS=$'\t' read -r action handler line; do
        local source="${OPENSEARCH_ROOT}/server/src/main/java/org/opensearch/action/ActionModule.java"
        printf '%s\t%s\t%s\t%s\t%s\n' "$(action_status "${source}" "${action}")" "${action}" "${handler}" "${source}" "${line}"
      done

    perl -0777 -ne '
      while (/new ActionHandler<>\(\s*([^,;]+?)\s*,\s*([^,)]+)\)/sg) {
        my $action = $1;
        my $handler = $2;
        $action =~ s/\s+//g;
        $handler =~ s/\s+//g;
        my $prefix = substr($_, 0, $-[0]);
        my $line = 1 + ($prefix =~ tr/\n//);
        print "$action\t$handler\t$line\n";
      }
    ' "${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java" |
      while IFS=$'\t' read -r action handler line; do
        local source="${KNN_ROOT}/src/main/java/org/opensearch/knn/plugin/KNNPlugin.java"
        printf '%s\t%s\t%s\t%s\t%s\n' "$(action_status "${source}" "${action}")" "${action}" "${handler}" "${source}" "${line}"
      done
  } >"${output}"
}

require_tool git
require_tool perl
require_tool rg
require_tool sed

assert_commit "OpenSearch" "${OPENSEARCH_ROOT}" "${EXPECTED_OPENSEARCH_COMMIT}"
assert_commit "k-NN" "${KNN_ROOT}" "${EXPECTED_KNN_COMMIT}"

mkdir -p "${OUT_DIR}"
REST_ROUTES_OUT="${OUT_DIR}/source-rest-routes.tsv"
TRANSPORT_ACTIONS_OUT="${OUT_DIR}/source-transport-actions.tsv"
SEARCH_REGISTRATIONS_OUT="${OUT_DIR}/source-search-registrations.tsv"
NODE_RUNTIME_COMPONENTS_OUT="${OUT_DIR}/source-node-runtime-components.tsv"
COMPATIBILITY_MATRIX_OUT="${OUT_DIR}/source-compatibility-matrix.tsv"

extract_rest_routes "${REST_ROUTES_OUT}"
extract_transport_actions "${TRANSPORT_ACTIONS_OUT}"
extract_search_registrations "${SEARCH_REGISTRATIONS_OUT}"
extract_node_runtime_components "${NODE_RUNTIME_COMPONENTS_OUT}"
build_compatibility_matrix \
  "${COMPATIBILITY_MATRIX_OUT}" \
  "${REST_ROUTES_OUT}" \
  "${TRANSPORT_ACTIONS_OUT}" \
  "${SEARCH_REGISTRATIONS_OUT}" \
  "${NODE_RUNTIME_COMPONENTS_OUT}"

echo "generated ${REST_ROUTES_OUT}"
echo "generated ${TRANSPORT_ACTIONS_OUT}"
echo "generated ${SEARCH_REGISTRATIONS_OUT}"
echo "generated ${NODE_RUNTIME_COMPONENTS_OUT}"
echo "generated ${COMPATIBILITY_MATRIX_OUT}"
