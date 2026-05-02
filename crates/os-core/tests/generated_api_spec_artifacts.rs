use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;

fn literal_openapi_path(path: &str) -> bool {
    path.starts_with('/')
        && !path.contains('"')
        && !path.contains(' ')
        && !path.contains('+')
        && !path.contains('(')
        && !path.contains(')')
}

#[test]
fn generated_openapi_and_route_evidence_artifacts_are_release_auditable() {
    let openapi_path = "/home/ubuntu/steelsearch/docs/api-spec/generated/openapi.json";
    let route_matrix_path =
        "/home/ubuntu/steelsearch/docs/api-spec/generated/route-evidence-matrix.md";
    let runtime_ledger_path =
        "/home/ubuntu/steelsearch/docs/api-spec/generated/runtime-route-ledger.json";
    let stateful_probe_report_path =
        "/home/ubuntu/steelsearch/docs/api-spec/generated/runtime-stateful-route-probe-report.json";
    let rest_tsv_path = "/home/ubuntu/steelsearch/docs/rust-port/generated/source-rest-routes.tsv";

    let openapi_text =
        fs::read_to_string(openapi_path).expect("generated openapi json should exist");
    let openapi: Value =
        serde_json::from_str(&openapi_text).expect("generated openapi json should parse");

    assert_eq!(openapi["openapi"], "3.0.3");
    assert_eq!(openapi["info"]["title"], "Steelsearch API");

    let paths = openapi["paths"]
        .as_object()
        .expect("openapi paths should be an object");
    assert!(paths.len() >= 200);
    assert!(paths.contains_key("/"));
    assert!(paths.contains_key("/_cluster/health"));
    assert!(paths.contains_key("/_search"));
    assert_eq!(
        paths["/"]
            .as_object()
            .expect("root path item should be an object")
            .keys()
            .cloned()
            .collect::<BTreeSet<_>>(),
        BTreeSet::from(["get".to_string(), "head".to_string()])
    );

    let cluster_health_get = &paths["/_cluster/health"]["get"];
    assert_eq!(cluster_health_get["x-steelsearch-family"], "root-cluster-node");
    assert_eq!(cluster_health_get["x-steelsearch-status"], "implemented-read");
    assert!(cluster_health_get["x-evidence-profile"].is_string());
    assert!(cluster_health_get["x-evidence-entrypoint"].is_string());
    assert_eq!(cluster_health_get["operationId"], "get__cluster_health");
    assert_eq!(
        cluster_health_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/OpenSearchSuccessEnvelope"
    );
    assert!(cluster_health_get["responses"]["200"]["content"]["text/plain"].is_null());

    let search_get = &paths["/_search"]["get"];
    let search_params = search_get["parameters"]
        .as_array()
        .expect("search parameters should be array");
    assert!(search_params.iter().any(|param| param["name"] == "from"));
    assert!(search_params.iter().any(|param| param["name"] == "size"));
    assert!(search_params
        .iter()
        .any(|param| param["name"] == "track_total_hits"));

    let bulk_post = &paths["/_bulk"]["post"];
    assert_eq!(
        bulk_post["requestBody"]["content"]["application/x-ndjson"]["schema"]["$ref"],
        "#/components/schemas/BulkNdjsonRequest"
    );
    let indexed_bulk_post = &paths["/{index}/_bulk"]["post"];
    assert_eq!(indexed_bulk_post["x-steelsearch-status"], "implemented-stateful");

    let cluster_settings_put = &paths["/_cluster/settings"]["put"];
    assert_eq!(cluster_settings_put["x-steelsearch-status"], "implemented-stateful");

    let tasks_cancel_post = &paths["/_tasks/_cancel"]["post"];
    assert_eq!(tasks_cancel_post["x-steelsearch-status"], "implemented-stateful");

    let knn_train_post = &paths["/_plugins/_knn/models/_train"]["post"];
    assert_eq!(knn_train_post["x-steelsearch-status"], "implemented-stateful");

    let cat_count_get = &paths["/_cat/count"]["get"];
    assert_eq!(
        cat_count_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/CatCountResponse"
    );
    assert_eq!(
        cat_count_get["responses"]["200"]["content"]["text/plain"]["schema"]["type"],
        "string"
    );

    let cat_indices_get = &paths["/_cat/indices"]["get"];
    assert_eq!(
        cat_indices_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/CatIndicesResponse"
    );

    let cat_root_get = &paths["/_cat"]["get"];
    assert!(cat_root_get["responses"]["200"]["content"]["application/json"].is_null());
    assert_eq!(
        cat_root_get["responses"]["200"]["content"]["text/plain"]["schema"]["type"],
        "string"
    );

    let cat_health_get = &paths["/_cat/health"]["get"];
    assert_eq!(cat_health_get["x-steelsearch-status"], "implemented-read");
    assert_eq!(
        cat_health_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/CatHealthResponse"
    );

    let cat_aliases_get = &paths["/_cat/aliases"]["get"];
    assert_eq!(cat_aliases_get["x-steelsearch-status"], "implemented-read");

    let cat_nodes_get = &paths["/_cat/nodes"]["get"];
    assert_eq!(
        cat_nodes_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/CatNodesResponse"
    );

    let cat_shards_get = &paths["/_cat/shards"]["get"];
    assert_eq!(
        cat_shards_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
        "#/components/schemas/CatShardsResponse"
    );

    let hot_threads_get = &paths["/_nodes/hot_threads"]["get"];
    assert!(hot_threads_get["responses"]["200"]["content"]["application/json"].is_null());
    assert_eq!(
        hot_threads_get["responses"]["200"]["content"]["text/plain"]["schema"]["type"],
        "string"
    );

    let tags = openapi["tags"].as_array().expect("openapi tags should be array");
    assert!(tags.iter().any(|tag| tag["name"] == "root-cluster-node"));
    assert!(tags.iter().any(|tag| tag["name"] == "search"));

    let schemas = openapi["components"]["schemas"]
        .as_object()
        .expect("openapi components schemas should be object");
    assert!(schemas["CatHealthRow"]["properties"]["active_shards_percent"].is_object());
    assert!(schemas["CatNodeRow"]["properties"]["heap.current"].is_object());
    assert!(schemas["CatShardRow"]["properties"]["unassigned.reason"].is_object());
    assert!(schemas["CatSegmentRow"]["properties"]["size.memory"].is_object());
    assert!(schemas["CatRecoveryRow"]["properties"]["bytes_recovered"].is_object());
    assert!(schemas["CatTaskRow"]["properties"]["running_time_ns"].is_object());
    assert!(schemas["CatTemplateRow"]["properties"]["priority"].is_object());
    assert!(schemas["CatThreadPoolRow"]["properties"]["queue_size"].is_object());

    let route_matrix =
        fs::read_to_string(route_matrix_path).expect("generated route evidence matrix should exist");
    assert!(route_matrix.contains("# Generated Route Evidence Matrix"));
    assert!(route_matrix.contains(
        "| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |"
    ));
    assert!(route_matrix.contains("`/_cluster/health`"));
    assert!(route_matrix.contains("`/_search`"));
    assert!(route_matrix.contains("| root-cluster-node | implemented-read | GET | `/_cluster/health` |"));
    assert!(route_matrix.contains("| root-cluster-node | implemented-read | GET | `/_cat/aliases` |"));
    assert!(route_matrix.contains("| root-cluster-node | implemented-stateful | PUT | `/_cluster/settings` |"));
    assert!(route_matrix.contains("| root-cluster-node | implemented-stateful | POST | `/_tasks/_cancel` |"));

    let runtime_ledger_text =
        fs::read_to_string(runtime_ledger_path).expect("runtime route ledger should exist");
    let runtime_ledger: Value =
        serde_json::from_str(&runtime_ledger_text).expect("runtime route ledger should parse");
    assert_eq!(runtime_ledger["summary"]["implemented-read"], 203);
    assert!(runtime_ledger["routes"]
        .as_array()
        .expect("runtime ledger routes should be array")
        .iter()
        .any(|route| route["path"] == "/_cat/aliases" && route["runtime_status"] == "implemented-read"));

    let stateful_probe_text =
        fs::read_to_string(stateful_probe_report_path).expect("stateful route probe report should exist");
    let stateful_probe: Value =
        serde_json::from_str(&stateful_probe_text).expect("stateful route probe report should parse");
    assert_eq!(stateful_probe["summary"]["passed"], 266);
    assert_eq!(
        stateful_probe["semantic_coverage_required"],
        serde_json::json!(["happy-path", "error-path", "idempotency-or-selector"])
    );
    assert!(stateful_probe["semantic_coverage_summary"]["complete"].as_u64().unwrap_or(0) > 0);
    assert!(stateful_probe["semantic_coverage_summary"]["incomplete"].as_u64().unwrap_or(0) > 0);
    assert!(stateful_probe["semantic_coverage_routes"]
        .as_array()
        .expect("semantic coverage routes should be array")
        .iter()
        .any(|route| {
            route["inventory_path"] == "/{index}/_delete_by_query"
                && route["complete"] == true
        }));
    assert!(stateful_probe["semantic_coverage_routes"]
        .as_array()
        .expect("semantic coverage routes should be array")
        .iter()
        .any(|route| {
            route["inventory_path"] == "/{index}/_search"
                && route["complete"] == true
        }));
    assert!(stateful_probe["semantic_coverage_missing"]
        .as_array()
        .expect("semantic coverage missing should be array")
        .iter()
        .any(|route| route["inventory_path"] == "/_tasks/_cancel"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_field_caps" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_field_caps" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_tier/_cancel/{index}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_tier/{targetTier}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_plugins/_knn/models/_search" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_plugins/_knn/clear_cache/{index}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_plugins/_knn/models/{model_id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_plugins/_knn/models/{model_id}/_train" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_ingest/pipeline/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_ingest/pipeline/_simulate" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_ingest/pipeline/{id}/_simulate" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_scripts/painless/_execute" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_rank_eval" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_rank_eval" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_forcemerge" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_forcemerge" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_index_template/_simulate" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_index_template/_simulate/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_index_template/_simulate_index/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_index_template/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/pipeline/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/point_in_time/_all" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/scroll" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/scroll/{scroll_id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_msearch/template" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_render/template" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_render/template/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/template" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_msearch/template" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_search/template" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_count" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "count_root_term_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_count" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "count_target_term_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "validate_query_root_invalid_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "validate_query_target_invalid_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "validate_query_root_empty_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "validate_query_target_empty_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_template_named_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_template_target_named_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_template_missing_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "render_template_named_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_validate/query" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_validate/query" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_root_term_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search/point_in_time" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_search/point_in_time" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_msearch" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "msearch_root_multi_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_explain/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "explain_target_unmatched_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "explain_target_missing_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "msearch_target_multi_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_target_term_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_target_missing_field_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_target_wildcard_match_all_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_target_wildcard_term_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_msearch" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_open" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_open" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_template/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_alias" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_alias/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_aliases" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_aliases/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "alias_named_wildcard_put" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "index_alias_collection_wildcard_put" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "index_alias_named_duplicate_put" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "settings_global_flat_get" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "settings_target_flat_get" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_block/{block}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_clone/{target}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_scale" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_shrink/{target}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_split/{target}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_rollover" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_rollover/{new_index}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/ingestion/_pause" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/ingestion/_resume" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_upgrade" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_analyze" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_analyze" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_flush" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_flush/synced" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_flush" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_flush/synced" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_upgrade" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/ingestion/_state" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_mget" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_mget" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_mtermvectors" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_mtermvectors" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_refresh" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_refresh" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_termvectors" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_termvectors/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_bulk" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "bulk_root_semantic_mixed_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_bulk/stream" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_bulk" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "bulk_target_semantic_mixed_put" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_bulk/stream" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_delete_by_query/{taskId}/_rethrottle" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "delete_by_query_rethrottle_known_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_reindex/{taskId}/_rethrottle" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "reindex_rethrottle_known_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_reindex" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "reindex_missing_dest_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "reindex_wildcard_source_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "reindex_overwrite_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_create/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "create_doc_refresh_put" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_doc" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_doc/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_delete_by_query" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "delete_by_query_unmatched_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "delete_by_query_repeated_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_update/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "single_doc_update_missing_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "single_doc_update_noop_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "single_doc_update_script_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_update_by_query/{taskId}/_rethrottle" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "update_by_query_rethrottle_known_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_update_by_query" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "update_by_query_unmatched_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "update_by_query_noop_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/allocation/explain" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/decommission/awareness/{awareness_attribute_name}/{awareness_attribute_value}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/reroute" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/routing/awareness/weights" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/routing/awareness/{attribute}/weights" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/voting_config_exclusions" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_nodes/reload_secure_settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_nodes/{nodeId}/reload_secure_settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_mapping" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_mappings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "mapping_target_merge_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "mapping_target_redefine_type_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_alias" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_alias/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_aliases" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_aliases/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cache/clear" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_cache/clear" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_close" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_close" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_component_template/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "component_template_named_overwrite_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "index_template_named_overwrite_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "legacy_template_named_overwrite_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_data_stream/{name}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "data_stream_stats_get"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_scroll_named_get"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_scroll_root_get_query"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_scroll_root_delete_array"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "search_point_in_time_root_delete_array"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "close_root_repeat_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "open_root_repeat_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "tier_cancel_repeat_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "flush_selector_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "refresh_selector_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "cache_clear_selector_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "forcemerge_selector_post"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_tasks/{task_id}/_cancel" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["name"] == "tasks_cancel_by_id_non_cancellable_post" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_dangling/{index_uuid}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_filecache/prune" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_remotestore/_restore" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}/_cleanup" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}/_verify" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}/{snapshot}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_search_shards" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/{index}/_search_shards" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_scripts/{id}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_scripts/{id}/{context}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}/{snapshot}/_clone/{target_snapshot}" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_snapshot/{repository}/{snapshot}/_restore" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| {
            (case["inventory_path"] == "/_plugins/_knn/models/_train"
                || case["path"] == "/_plugins/_knn/models/_train")
                && case["runtime_status"] == "stateful-route-present"
        }));

    let mut literal_routes = BTreeSet::new();
    let rest_tsv = fs::read_to_string(rest_tsv_path).expect("source rest route tsv should exist");
    for line in rest_tsv.lines().skip(1) {
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() < 6 {
            continue;
        }
        let method = cols[0].to_ascii_lowercase();
        let path = cols[1];
        if matches!(method.as_str(), "get" | "put" | "post" | "delete" | "head")
            && literal_openapi_path(path)
        {
            literal_routes.insert((method, path.to_string()));
        }
    }

    for (method, path) in literal_routes {
        let operation = paths
            .get(&path)
            .and_then(|value| value.get(&method))
            .unwrap_or_else(|| panic!("generated openapi missing {method} {path}"));
        assert!(operation["x-evidence-profile"].is_string());
    }
}
