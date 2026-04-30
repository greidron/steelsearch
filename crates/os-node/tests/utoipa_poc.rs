use utoipa::{OpenApi, ToSchema};

#[derive(ToSchema)]
struct RootInfoResponse {
    name: String,
    cluster_name: String,
}

#[derive(ToSchema)]
struct ClusterHealthResponse {
    status: String,
    number_of_nodes: u32,
}

#[utoipa::path(
    get,
    path = "/",
    responses(
        (status = 200, description = "Root node identity", body = RootInfoResponse)
    )
)]
fn root_info_doc() {}

#[utoipa::path(
    get,
    path = "/_cluster/health",
    responses(
        (status = 200, description = "Cluster health", body = ClusterHealthResponse)
    )
)]
fn cluster_health_doc() {}

#[derive(OpenApi)]
#[openapi(
    paths(root_info_doc, cluster_health_doc),
    components(schemas(RootInfoResponse, ClusterHealthResponse)),
    tags(
        (name = "root-cluster-node", description = "Minimal utoipa proof of concept")
    )
)]
struct UtoipaPhasePoc;

#[test]
fn utoipa_can_generate_a_small_openapi_document_for_current_route_families() {
    let doc = UtoipaPhasePoc::openapi();
    let json = serde_json::to_value(&doc).expect("utoipa openapi doc should serialize");

    assert_eq!(json["openapi"], "3.0.3");
    assert!(json["paths"]["/"]["get"].is_object());
    assert!(json["paths"]["/_cluster/health"]["get"].is_object());
    assert!(json["components"]["schemas"]["RootInfoResponse"].is_object());
    assert!(json["components"]["schemas"]["ClusterHealthResponse"].is_object());
}
