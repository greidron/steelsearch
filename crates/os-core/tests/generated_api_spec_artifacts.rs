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
    let rest_tsv_path = "/home/ubuntu/steelsearch/docs/rust-port/generated/source-rest-routes.tsv";

    let openapi_text =
        fs::read_to_string(openapi_path).expect("generated openapi json should exist");
    let openapi: Value =
        serde_json::from_str(&openapi_text).expect("generated openapi json should parse");

    assert_eq!(openapi["openapi"], "3.0.3");
    assert_eq!(
        openapi["info"]["title"],
        "Steelsearch OpenSearch-Compatible API"
    );

    let paths = openapi["paths"]
        .as_object()
        .expect("openapi paths should be an object");
    assert!(paths.len() >= 200);
    assert!(paths.contains_key("/"));
    assert!(paths.contains_key("/_cluster/health"));
    assert!(paths.contains_key("/_search"));

    let cluster_health_get = &paths["/_cluster/health"]["get"];
    assert_eq!(cluster_health_get["x-steelsearch-family"], "root-cluster-node");
    assert!(cluster_health_get["x-evidence-profile"].is_string());
    assert!(cluster_health_get["x-evidence-entrypoint"].is_string());

    let route_matrix =
        fs::read_to_string(route_matrix_path).expect("generated route evidence matrix should exist");
    assert!(route_matrix.contains("# Generated Route Evidence Matrix"));
    assert!(route_matrix.contains(
        "| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |"
    ));
    assert!(route_matrix.contains("`/_cluster/health`"));
    assert!(route_matrix.contains("`/_search`"));

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
