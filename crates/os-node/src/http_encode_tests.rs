use super::{encode_rest_response, rest_response_to_actix_response, EncodedRestResponse};
use actix_web::body::to_bytes;
use actix_web::http::StatusCode;
use os_rest::RestResponse;
use serde_json::{json, Value};
use std::collections::BTreeMap;

fn response(
    status: u16,
    headers: BTreeMap<String, String>,
    body: Value,
    raw_body: Option<Vec<u8>>,
) -> RestResponse {
    RestResponse {
        status,
        headers,
        body,
        raw_body,
    }
}

fn assert_send_static<T: Send + 'static>(_: &T) {}

#[test]
fn encoded_response_is_send_and_static_for_web_block() {
    let encoded = encode_rest_response(RestResponse::empty(204));

    assert_send_static(&encoded);
}

#[test]
fn encodes_json_status_headers_and_nested_numeric_values_exactly() {
    let mut headers = BTreeMap::new();
    headers.insert("content-type".to_string(), "application/json".to_string());
    headers.insert("x-request-id".to_string(), "request-42".to_string());
    let encoded = encode_rest_response(response(
        201,
        headers,
        json!({
            "nested": [
                {"maximum": u64::MAX},
                [1.25, true, null]
            ],
            "name": "document"
        }),
        None,
    ));

    assert_eq!(encoded.status, 201);
    assert_eq!(
        encoded.headers,
        BTreeMap::from([
            ("content-type".to_string(), "application/json".to_string()),
            ("x-request-id".to_string(), "request-42".to_string()),
        ])
    );
    assert_eq!(
        encoded.body,
        br#"{"name":"document","nested":[{"maximum":18446744073709551615},[1.25,true,null]]}"#
    );
}

#[test]
fn encodes_plain_text_for_content_type_prefix_including_charset() {
    let mut headers = BTreeMap::new();
    headers.insert(
        "content-type".to_string(),
        "text/plain; charset=utf-8".to_string(),
    );
    let encoded = encode_rest_response(response(
        200,
        headers,
        Value::String("plain text\n".to_string()),
        None,
    ));

    assert_eq!(encoded.body, b"plain text\n");
}

#[test]
fn encodes_non_string_plain_text_body_as_empty() {
    let mut headers = BTreeMap::new();
    headers.insert("content-type".to_string(), "text/plain".to_string());
    let encoded = encode_rest_response(response(200, headers, json!({"message": "nope"}), None));

    assert!(encoded.body.is_empty());
}

#[test]
fn encodes_null_and_empty_responses_as_empty_bodies() {
    let null_encoded = encode_rest_response(RestResponse::json(200, Value::Null));
    let empty_encoded = encode_rest_response(RestResponse::empty(204));

    assert!(null_encoded.body.is_empty());
    assert!(empty_encoded.body.is_empty());
}

#[test]
fn raw_body_wins_over_json_without_cloning_the_buffer() {
    let raw_body = b"raw payload".to_vec();
    let raw_pointer = raw_body.as_ptr();
    let encoded = encode_rest_response(response(
        202,
        BTreeMap::from([("content-type".to_string(), "application/json".to_string())]),
        json!({"ignored": true}),
        Some(raw_body),
    ));

    assert_eq!(encoded.body, b"raw payload");
    assert_eq!(encoded.body.as_ptr(), raw_pointer);
}

#[test]
fn empty_raw_body_wins_over_non_empty_json() {
    let encoded = encode_rest_response(response(
        202,
        BTreeMap::new(),
        json!({"ignored": true}),
        Some(Vec::new()),
    ));

    assert!(encoded.body.is_empty());
}

#[test]
fn actix_conversion_uses_internal_server_error_for_invalid_status_and_preserves_headers() {
    actix_web::rt::System::new().block_on(async {
        let mut headers = BTreeMap::new();
        headers.insert("content-type".to_string(), "application/json".to_string());
        headers.insert("x-request-id".to_string(), "request-42".to_string());
        let response = rest_response_to_actix_response(EncodedRestResponse {
            status: 99,
            headers,
            body: br#"{"error":"invalid status"}"#.to_vec(),
        });

        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(
            response.headers().get("content-type").unwrap(),
            "application/json"
        );
        assert_eq!(
            response.headers().get("x-request-id").unwrap(),
            "request-42"
        );
        assert_eq!(
            to_bytes(response.into_body()).await.unwrap().as_ref(),
            br#"{"error":"invalid status"}"#
        );
    });
}
