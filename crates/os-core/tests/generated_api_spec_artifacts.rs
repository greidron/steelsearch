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
    assert_eq!(runtime_ledger["summary"]["implemented-read"], 111);
    assert!(runtime_ledger["routes"]
        .as_array()
        .expect("runtime ledger routes should be array")
        .iter()
        .any(|route| route["path"] == "/_cat/aliases" && route["runtime_status"] == "implemented-read"));

    let stateful_probe_text =
        fs::read_to_string(stateful_probe_report_path).expect("stateful route probe report should exist");
    let stateful_probe: Value =
        serde_json::from_str(&stateful_probe_text).expect("stateful route probe report should parse");
    assert_eq!(stateful_probe["summary"]["passed"], 7);
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "/_cluster/settings" && case["runtime_status"] == "stateful-route-present"));
    assert!(stateful_probe["cases"]
        .as_array()
        .expect("stateful probe cases should be array")
        .iter()
        .any(|case| case["inventory_path"] == "String.format(Locale.ROOT, \"%s/%s/_train\", KNNPlugin.KNN_BASE_URI, MODELS)" && case["runtime_status"] == "stateful-route-present"));

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
