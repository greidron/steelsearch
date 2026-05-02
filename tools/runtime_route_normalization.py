from __future__ import annotations

UNPROBEABLE_MARKERS = (' + ', 'String.format(', 'KNNPlugin.', 'ENDPOINT', 'URL_PATH', '(dynamic)')

PATH_NORMALIZATION = {
    '/ + ENDPOINT': '/_rank_eval',
    '/{index}/ + ENDPOINT': '/{index}/_rank_eval',
    '"/" + ENDPOINT': '/_rank_eval',
    '"/{index}/" + ENDPOINT': '/{index}/_rank_eval',
    'String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, CLEAR_CACHE, INDEX)': '/_plugins/_knn/clear_cache/{index}',
    'String.format(Locale.ROOT, "%s/%s/{%s}", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)': '/_plugins/_knn/models/{model_id}',
    'String.format(Locale.ROOT, "%s/%s/{%s}/_train", KNNPlugin.KNN_BASE_URI, MODELS, MODEL_ID)': '/_plugins/_knn/models/{model_id}/_train',
    'String.format(Locale.ROOT, "%s/%s/_train", KNNPlugin.KNN_BASE_URI, MODELS)': '/_plugins/_knn/models/_train',
    'String.format(Locale.ROOT, "%s/%s/%s", KNNPlugin.KNN_BASE_URI, MODELS, SEARCH)': '/_plugins/_knn/models/_search',
    'KNNPlugin.KNN_BASE_URI + "/stats/"': '/_plugins/_knn/stats',
    'KNNPlugin.KNN_BASE_URI + "/stats/{stat}"': '/_plugins/_knn/stats/{stat}',
    'KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/"': '/_plugins/_knn/{nodeId}/stats',
    'KNNPlugin.KNN_BASE_URI + "/{nodeId}/stats/{stat}"': '/_plugins/_knn/{nodeId}/stats/{stat}',
    'KNNPlugin.KNN_BASE_URI + URL_PATH': '/_plugins/_knn/warmup',
    '_wlm/workload_group/': '/_wlm/workload_group',
    '_wlm/workload_group/{name}': '/_wlm/workload_group/{name}',
    '_wlm/stats': '/_wlm/stats',
    '_wlm/{nodeId}/stats': '/_wlm/{nodeId}/stats',
    '_wlm/stats/{workloadGroupId}': '/_wlm/stats/{workloadGroupId}',
    '_wlm/{nodeId}/stats/{workloadGroupId}': '/_wlm/{nodeId}/stats/{workloadGroupId}',
    '_list/wlm_stats': '/_list/wlm_stats',
    '_list/wlm_stats/{nodeId}/stats': '/_list/wlm_stats/{nodeId}/stats',
    '_list/wlm_stats/stats/{workloadGroupId}': '/_list/wlm_stats/stats/{workloadGroupId}',
    '_list/wlm_stats/{nodeId}/stats/{workloadGroupId}': '/_list/wlm_stats/{nodeId}/stats/{workloadGroupId}',
    '/{index}/_tier/ + targetTier': '/{index}/_tier/{targetTier}',
}


def normalize_path(path: str) -> str:
    normalized = PATH_NORMALIZATION.get(path, path)
    normalized = normalized.rstrip('/') or '/'
    if not normalized.startswith('/'):
        normalized = '/' + normalized
    return normalized


def is_concrete_path(path: str) -> bool:
    return not any(marker in path for marker in UNPROBEABLE_MARKERS)
