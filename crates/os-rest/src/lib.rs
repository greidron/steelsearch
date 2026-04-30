//! REST compatibility shell.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::sync::Arc;

pub type RestHandler = Arc<dyn Fn(RestRequest) -> RestResponse + Send + Sync + 'static>;

pub trait IntoRestBody {
    fn into_rest_body(self) -> Vec<u8>;
}

impl IntoRestBody for Vec<u8> {
    fn into_rest_body(self) -> Vec<u8> {
        self
    }
}

impl IntoRestBody for String {
    fn into_rest_body(self) -> Vec<u8> {
        self.into_bytes()
    }
}

impl IntoRestBody for &str {
    fn into_rest_body(self) -> Vec<u8> {
        self.as_bytes().to_vec()
    }
}

impl IntoRestBody for &[u8] {
    fn into_rest_body(self) -> Vec<u8> {
        self.to_vec()
    }
}

impl<const N: usize> IntoRestBody for &[u8; N] {
    fn into_rest_body(self) -> Vec<u8> {
        self.to_vec()
    }
}

impl IntoRestBody for Value {
    fn into_rest_body(self) -> Vec<u8> {
        serde_json::to_vec(&self).expect("json body serialization should succeed")
    }
}

pub const HEADER_ACCEPT: &str = "accept";
pub const HEADER_CONTENT_TYPE: &str = "content-type";
pub const HEADER_OPAQUE_ID: &str = "x-opaque-id";
pub const HEADER_WARNING: &str = "warning";

#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum RestMethod {
    Get,
    Head,
    Put,
    Post,
    Delete,
}

impl RestMethod {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Get => "GET",
            Self::Head => "HEAD",
            Self::Put => "PUT",
            Self::Post => "POST",
            Self::Delete => "DELETE",
        }
    }
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
pub struct RestRoute {
    pub method: RestMethod,
    pub path: String,
}

impl RestRoute {
    pub fn new(method: RestMethod, path: impl Into<String>) -> Self {
        Self {
            method,
            path: path.into(),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestRequest {
    pub method: RestMethod,
    pub path: String,
    pub path_params: BTreeMap<String, String>,
    pub query_params: BTreeMap<String, String>,
    pub headers: BTreeMap<String, String>,
    pub body: Vec<u8>,
}

impl RestRequest {
    pub fn new(method: RestMethod, path: impl Into<String>) -> Self {
        Self {
            method,
            path: path.into(),
            path_params: BTreeMap::new(),
            query_params: BTreeMap::new(),
            headers: BTreeMap::new(),
            body: Vec::new(),
        }
    }

    pub fn with_body(mut self, body: impl IntoRestBody) -> Self {
        self.body = body.into_rest_body();
        self
    }

    pub fn with_json_body(mut self, body: impl Serialize) -> Self {
        self.body = serde_json::to_vec(&body).expect("json body serialization should succeed");
        self.headers.insert(
            HEADER_CONTENT_TYPE.to_string(),
            "application/json".to_string(),
        );
        self
    }

    pub fn with_header(mut self, name: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers
            .insert(normalize_header_name(&name.into()), value.into());
        self
    }

    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .get(&normalize_header_name(name))
            .map(String::as_str)
    }

    pub fn require_json_content_type(&self) -> Result<(), RestResponse> {
        if self.body.is_empty() {
            return Ok(());
        }
        match self.header(HEADER_CONTENT_TYPE) {
            Some(value) if is_json_media_type(value) => Ok(()),
            Some(value) => Err(RestResponse::opensearch_error_kind(
                RestErrorKind::UnsupportedMediaType,
                format!("unsupported content-type [{value}]"),
            )),
            None => Err(RestResponse::opensearch_error_kind(
                RestErrorKind::ContentTypeRequired,
                "request body is required to have a content-type header",
            )),
        }
    }

    pub fn require_json_accept(&self) -> Result<(), RestResponse> {
        match self.header(HEADER_ACCEPT) {
            Some(value) if accepts_json(value) => Ok(()),
            Some(value) => Err(RestResponse::opensearch_error_kind(
                RestErrorKind::NotAcceptable,
                format!("unsupported accept header [{value}]"),
            )),
            None => Ok(()),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestResponse {
    pub status: u16,
    pub headers: BTreeMap<String, String>,
    pub body: Value,
    #[serde(skip)]
    pub raw_body: Option<Vec<u8>>,
}

impl RestResponse {
    pub fn json(status: u16, body: Value) -> Self {
        let mut headers = BTreeMap::new();
        headers.insert(
            HEADER_CONTENT_TYPE.to_string(),
            "application/json".to_string(),
        );
        Self {
            status,
            headers,
            body,
            raw_body: None,
        }
    }

    pub fn text(status: u16, body: impl Into<String>) -> Self {
        let mut headers = BTreeMap::new();
        headers.insert(HEADER_CONTENT_TYPE.to_string(), "text/plain".to_string());
        Self {
            status,
            headers,
            body: Value::String(body.into()),
            raw_body: None,
        }
    }

    pub fn raw(status: u16, body: impl IntoRestBody, content_type: impl Into<String>) -> Self {
        let mut headers = BTreeMap::new();
        headers.insert(HEADER_CONTENT_TYPE.to_string(), content_type.into());
        Self {
            status,
            headers,
            body: Value::Null,
            raw_body: Some(body.into_rest_body()),
        }
    }

    pub fn empty(status: u16) -> Self {
        Self {
            status,
            headers: BTreeMap::new(),
            body: Value::Null,
            raw_body: None,
        }
    }

    pub fn opensearch_error(
        status: u16,
        error_type: impl Into<String>,
        reason: impl Into<String>,
    ) -> Self {
        let error_type = error_type.into();
        let reason = reason.into();
        Self::json(
            status,
            serde_json::json!({
                "error": {
                    "root_cause": [
                        {
                            "type": &error_type,
                            "reason": &reason
                        }
                    ],
                    "type": &error_type,
                    "reason": &reason
                },
                "status": status
            }),
        )
    }

    pub fn opensearch_error_kind(kind: RestErrorKind, reason: impl Into<String>) -> Self {
        Self::opensearch_error(kind.status_code(), kind.error_type(), reason)
    }

    pub fn with_header(mut self, name: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers
            .insert(normalize_header_name(&name.into()), value.into());
        self
    }

    pub fn with_opaque_id_from(mut self, request: &RestRequest) -> Self {
        if let Some(value) = request.header(HEADER_OPAQUE_ID) {
            self.headers
                .insert(HEADER_OPAQUE_ID.to_string(), value.to_string());
        }
        self
    }

    pub fn with_deprecation_warning(self, message: impl AsRef<str>) -> Self {
        self.with_header(HEADER_WARNING, deprecation_warning(message.as_ref()))
    }

    pub fn not_found_for(method: RestMethod, path: &str) -> Self {
        Self::opensearch_error_kind(
            RestErrorKind::NoHandlerFound,
            format!(
                "no handler found for uri [{}] and method [{}]",
                path,
                method.as_str()
            ),
        )
    }

    pub fn not_found() -> Self {
        Self::opensearch_error_kind(
            RestErrorKind::NoHandlerFound,
            "no handler found for request",
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RestErrorKind {
    Parse,
    IllegalArgument,
    ResourceAlreadyExists,
    IndexNotFound,
    NoHandlerFound,
    ContentTypeRequired,
    UnsupportedMediaType,
    NotAcceptable,
    TaskCancelled,
    Timeout,
    TransportSerialization,
    Internal,
}

impl RestErrorKind {
    pub fn status_code(self) -> u16 {
        match self {
            Self::Parse | Self::IllegalArgument | Self::ContentTypeRequired => 400,
            Self::IndexNotFound | Self::NoHandlerFound => 404,
            Self::ResourceAlreadyExists => 400,
            Self::UnsupportedMediaType => 415,
            Self::NotAcceptable => 406,
            Self::TaskCancelled | Self::Timeout | Self::Internal => 500,
            Self::TransportSerialization => 502,
        }
    }

    pub fn error_type(self) -> &'static str {
        match self {
            Self::Parse => "parse_exception",
            Self::IllegalArgument => "illegal_argument_exception",
            Self::ResourceAlreadyExists => "resource_already_exists_exception",
            Self::IndexNotFound => "index_not_found_exception",
            Self::NoHandlerFound => "no_handler_found_exception",
            Self::ContentTypeRequired => "content_type_missing_exception",
            Self::UnsupportedMediaType => "media_type_header_exception",
            Self::NotAcceptable => "not_acceptable_exception",
            Self::TaskCancelled => "task_cancelled_exception",
            Self::Timeout => "timeout_exception",
            Self::TransportSerialization => "transport_serialization_exception",
            Self::Internal => "internal_server_error",
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RestTaskCancellation {
    pub task_id: String,
    pub reason: String,
}

impl RestTaskCancellation {
    pub fn response(&self) -> RestResponse {
        RestResponse::opensearch_error_kind(
            RestErrorKind::TaskCancelled,
            format!("task [{}] was cancelled: {}", self.task_id, self.reason),
        )
    }
}

pub fn deprecation_warning(message: &str) -> String {
    format!("299 OpenSearch-3.0.0 \"{}\"", message.replace('"', "\\\""))
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RouteMatch {
    pub route: RestRoute,
    pub path_params: BTreeMap<String, String>,
}

#[derive(Clone)]
struct RouteEntry {
    route: RestRoute,
    segments: Vec<RouteSegment>,
    handler: RestHandler,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum RouteSegment {
    Literal(String),
    Param(String),
}

#[derive(Clone, Default)]
pub struct RestRouter {
    routes: Vec<RouteEntry>,
}

impl RestRouter {
    pub fn new() -> Self {
        Self { routes: Vec::new() }
    }

    pub fn register(
        &mut self,
        method: RestMethod,
        path: impl Into<String>,
        handler: impl Fn(RestRequest) -> RestResponse + Send + Sync + 'static,
    ) -> RestRoute {
        let route = RestRoute::new(method, path);
        let segments = parse_route_segments(&route.path);
        self.routes.push(RouteEntry {
            route: route.clone(),
            segments,
            handler: Arc::new(handler),
        });
        route
    }

    pub fn route_count(&self) -> usize {
        self.routes.len()
    }

    pub fn routes(&self) -> Vec<RestRoute> {
        self.routes
            .iter()
            .map(|entry| entry.route.clone())
            .collect()
    }

    pub fn recognize(&self, method: RestMethod, path: &str) -> Option<RouteMatch> {
        let path_segments = split_path(path);
        self.routes
            .iter()
            .filter(|entry| entry.route.method == method)
            .find_map(|entry| {
                match_segments(&entry.segments, &path_segments).map(|path_params| RouteMatch {
                    route: entry.route.clone(),
                    path_params,
                })
            })
    }

    pub fn handle(&self, mut request: RestRequest) -> RestResponse {
        let Some(entry) = self.find_entry(request.method, &request.path) else {
            return RestResponse::not_found_for(request.method, &request.path)
                .with_opaque_id_from(&request);
        };
        let path_segments = split_path(&request.path);
        request.path_params = match_segments(&entry.segments, &path_segments).unwrap_or_default();
        let opaque_request = request.clone();
        (entry.handler)(request).with_opaque_id_from(&opaque_request)
    }

    fn find_entry(&self, method: RestMethod, path: &str) -> Option<&RouteEntry> {
        let path_segments = split_path(path);
        self.routes
            .iter()
            .filter(|entry| entry.route.method == method)
            .find(|entry| match_segments(&entry.segments, &path_segments).is_some())
    }
}

fn parse_route_segments(path: &str) -> Vec<RouteSegment> {
    split_path(path)
        .into_iter()
        .map(|segment| {
            if let Some(param) = segment
                .strip_prefix('{')
                .and_then(|value| value.strip_suffix('}'))
            {
                RouteSegment::Param(param.to_string())
            } else {
                RouteSegment::Literal(segment)
            }
        })
        .collect()
}

fn split_path(path: &str) -> Vec<String> {
    path.trim_matches('/')
        .split('/')
        .filter(|segment| !segment.is_empty())
        .map(ToString::to_string)
        .collect()
}

fn match_segments(
    route_segments: &[RouteSegment],
    path_segments: &[String],
) -> Option<BTreeMap<String, String>> {
    if route_segments.len() != path_segments.len() {
        return None;
    }

    let mut path_params = BTreeMap::new();
    for (route_segment, path_segment) in route_segments.iter().zip(path_segments) {
        match route_segment {
            RouteSegment::Literal(value) if value == path_segment => {}
            RouteSegment::Param(name) => {
                path_params.insert(name.clone(), path_segment.clone());
            }
            RouteSegment::Literal(_) => return None,
        }
    }
    Some(path_params)
}

fn normalize_header_name(name: &str) -> String {
    name.to_ascii_lowercase()
}

fn is_json_media_type(value: &str) -> bool {
    value
        .split(';')
        .next()
        .map(str::trim)
        .map(|media_type| {
            media_type.eq_ignore_ascii_case("application/json")
                || media_type.eq_ignore_ascii_case("application/vnd.opensearch+json")
        })
        .unwrap_or(false)
}

fn accepts_json(value: &str) -> bool {
    value.split(',').any(|part| {
        let media_type = part.split(';').next().map(str::trim).unwrap_or_default();
        media_type == "*/*"
            || media_type.eq_ignore_ascii_case("application/*")
            || is_json_media_type(media_type)
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ok_handler(request: RestRequest) -> RestResponse {
        RestResponse::json(
            200,
            serde_json::json!({
                "index": request.path_params.get("index").cloned()
            }),
        )
    }

    #[test]
    fn registers_and_recognizes_parameterized_routes() {
        let mut router = RestRouter::new();
        let route = router.register(RestMethod::Get, "/{index}", ok_handler);

        assert_eq!(route, RestRoute::new(RestMethod::Get, "/{index}"));
        assert_eq!(router.route_count(), 1);

        let matched = router.recognize(RestMethod::Get, "/steelsearch").unwrap();
        assert_eq!(matched.route, route);
        assert_eq!(
            matched.path_params.get("index").map(String::as_str),
            Some("steelsearch")
        );
    }

    #[test]
    fn dispatches_to_registered_handler_with_path_params() {
        let mut router = RestRouter::new();
        router.register(RestMethod::Get, "/{index}", ok_handler);

        let response = router.handle(RestRequest::new(RestMethod::Get, "/steelsearch"));

        assert_eq!(response.status, 200);
        assert_eq!(response.body["index"], "steelsearch");
    }

    #[test]
    fn returns_not_found_for_unmatched_routes() {
        let router = RestRouter::new();

        let response = router.handle(RestRequest::new(RestMethod::Get, "/missing"));

        assert_eq!(response.status, 404);
        assert_eq!(response.body["status"], 404);
        assert_eq!(response.body["error"]["type"], "no_handler_found_exception");
        assert_eq!(
            response.body["error"]["root_cause"][0]["reason"],
            "no handler found for uri [/missing] and method [GET]"
        );
    }

    #[test]
    fn builds_opensearch_shaped_error_response() {
        let response =
            RestResponse::opensearch_error(400, "parse_exception", "failed to parse request");

        assert_eq!(response.status, 400);
        assert_eq!(
            response.headers.get("content-type").map(String::as_str),
            Some("application/json")
        );
        assert_eq!(response.body["status"], 400);
        assert_eq!(response.body["error"]["type"], "parse_exception");
        assert_eq!(response.body["error"]["reason"], "failed to parse request");
        assert_eq!(
            response.body["error"]["root_cause"][0]["type"],
            "parse_exception"
        );
    }

    #[test]
    fn builds_empty_response_without_json_header() {
        let response = RestResponse::empty(200);

        assert_eq!(response.status, 200);
        assert!(response.headers.is_empty());
        assert_eq!(response.body, Value::Null);
    }

    #[test]
    fn preserves_opensearch_error_type_and_status_mapping() {
        let response = RestResponse::opensearch_error_kind(
            RestErrorKind::UnsupportedMediaType,
            "unsupported content-type [text/plain]",
        );

        assert_eq!(response.status, 415);
        assert_eq!(response.body["status"], 415);
        assert_eq!(
            response.body["error"]["type"],
            "media_type_header_exception"
        );
    }

    #[test]
    fn validates_json_content_type_and_accept_headers() {
        let accepted = RestRequest::new(RestMethod::Post, "/_search")
            .with_header("Content-Type", "application/json; charset=UTF-8")
            .with_header("Accept", "application/vnd.opensearch+json")
            .with_body("{}");

        assert!(accepted.require_json_content_type().is_ok());
        assert!(accepted.require_json_accept().is_ok());

        let rejected = RestRequest::new(RestMethod::Post, "/_search")
            .with_header("Content-Type", "text/plain")
            .with_body("{}");
        let response = rejected.require_json_content_type().unwrap_err();
        assert_eq!(response.status, 415);
        assert_eq!(
            response.body["error"]["type"],
            "media_type_header_exception"
        );

        let not_acceptable =
            RestRequest::new(RestMethod::Get, "/_search").with_header("Accept", "text/plain");
        let response = not_acceptable.require_json_accept().unwrap_err();
        assert_eq!(response.status, 406);
        assert_eq!(response.body["error"]["type"], "not_acceptable_exception");
    }

    #[test]
    fn propagates_opaque_id_and_deprecation_warning_headers() {
        let request =
            RestRequest::new(RestMethod::Get, "/").with_header("X-Opaque-Id", "request-123");

        let response = RestResponse::json(200, serde_json::json!({ "ok": true }))
            .with_opaque_id_from(&request)
            .with_deprecation_warning("old \"thing\"");

        assert_eq!(
            response.headers.get(HEADER_OPAQUE_ID).map(String::as_str),
            Some("request-123")
        );
        assert_eq!(
            response.headers.get(HEADER_WARNING).map(String::as_str),
            Some("299 OpenSearch-3.0.0 \"old \\\"thing\\\"\"")
        );
    }

    #[test]
    fn accepts_json_header_allows_wildcards_and_multiple_values() {
        let wildcard =
            RestRequest::new(RestMethod::Get, "/_search").with_header("Accept", "*/*");
        assert!(wildcard.require_json_accept().is_ok());

        let mixed = RestRequest::new(RestMethod::Get, "/_search")
            .with_header("Accept", "text/plain, application/*;q=0.9");
        assert!(mixed.require_json_accept().is_ok());
    }

    #[test]
    fn with_opaque_id_from_is_noop_when_request_has_no_header() {
        let request = RestRequest::new(RestMethod::Get, "/");
        let response =
            RestResponse::json(200, serde_json::json!({ "ok": true })).with_opaque_id_from(&request);
        assert!(response.headers.get(HEADER_OPAQUE_ID).is_none());
    }

    #[test]
    fn task_cancellation_uses_opensearch_error_shape() {
        let cancellation = RestTaskCancellation {
            task_id: "node-a:42".to_string(),
            reason: "timeout".to_string(),
        };

        let response = cancellation.response();

        assert_eq!(response.status, 500);
        assert_eq!(response.body["error"]["type"], "task_cancelled_exception");
        assert_eq!(
            response.body["error"]["reason"],
            "task [node-a:42] was cancelled: timeout"
        );
    }
}
