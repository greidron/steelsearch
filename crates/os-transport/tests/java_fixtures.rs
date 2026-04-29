use base64::engine::general_purpose::STANDARD;
use base64::Engine;
use bytes::{Bytes, BytesMut};
use flate2::write::DeflateEncoder;
use flate2::Compression;
use os_core::Version;
use os_stream::StreamInput;
use os_transport::compression::DEFLATE_HEADER;
use os_transport::TransportMessage;
use os_transport::frame::{decode_frame, DecodedFrame};
use os_transport::handshake::{
    build_tcp_handshake_request, build_transport_handshake_request, TCP_HANDSHAKE_ACTION,
    TRANSPORT_HANDSHAKE_ACTION,
};
use os_transport::variable_header::RequestVariableHeader;
use os_wire::{TcpHeader, TransportStatus};
use std::collections::BTreeMap;
use std::io::Write;

fn fixtures() -> BTreeMap<&'static str, Vec<u8>> {
    include_str!("../../../fixtures/java/opensearch-wire-fixtures.txt")
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| {
            let (name, value) = line.split_once('=').unwrap();
            (name, STANDARD.decode(value).unwrap())
        })
        .collect()
}

#[test]
fn java_string_fixture_matches_stream_output_contract() {
    let fixtures = fixtures();
    let mut input = StreamInput::new(Bytes::from(
        fixtures.get("string_steelsearch_search").unwrap().clone(),
    ));
    assert_eq!(input.read_string().unwrap(), "steelsearch 검색");
    assert_eq!(input.remaining(), 0);

    let mut input = StreamInput::new(Bytes::from(
        fixtures.get("string_array_features").unwrap().clone(),
    ));
    assert_eq!(
        input.read_string_array().unwrap(),
        vec!["feature-a".to_string(), "feature-b".to_string()]
    );
    assert_eq!(input.remaining(), 0);
}

#[test]
fn java_variable_header_fixture_decodes_with_rust_codec() {
    let fixtures = fixtures();
    let header = RequestVariableHeader::read(Bytes::from(
        fixtures.get("variable_header_request").unwrap().clone(),
    ))
    .unwrap();

    assert!(header.thread_headers.request.is_empty());
    assert!(header.thread_headers.response.is_empty());
    assert_eq!(
        header.features,
        vec!["feature-a".to_string(), "feature-b".to_string()]
    );
    assert_eq!(header.action, TRANSPORT_HANDSHAKE_ACTION);
}

#[test]
fn java_tcp_handshake_fixture_matches_rust_builder() {
    let fixtures = fixtures();
    let java_bytes = fixtures.get("tcp_handshake_request").unwrap().clone();

    let header = TcpHeader::decode(&java_bytes[..TcpHeader::HEADER_SIZE]).unwrap();
    let mut body = StreamInput::new(Bytes::from(
        java_bytes[TcpHeader::HEADER_SIZE + header.variable_header_size as usize..].to_vec(),
    ));
    assert_eq!(body.read_string().unwrap(), "");
    let mut version_bytes = StreamInput::new(body.read_bytes_reference().unwrap());
    let payload_version = Version::from_id(version_bytes.read_vint().unwrap());

    let rust_bytes =
        build_tcp_handshake_request(header.request_id, header.version, payload_version);

    assert_eq!(&rust_bytes[..], &java_bytes[..]);
}

#[test]
fn java_transport_handshake_fixture_matches_rust_builder() {
    let fixtures = fixtures();
    let java_bytes = fixtures.get("transport_handshake_request").unwrap().clone();

    let header = TcpHeader::decode(&java_bytes[..TcpHeader::HEADER_SIZE]).unwrap();
    let rust_bytes = build_transport_handshake_request(header.request_id, header.version);

    assert_eq!(&rust_bytes[..], &java_bytes[..]);
}

#[test]
fn java_transport_handshake_compressed_frame_decodes_with_rust_frame_codec() {
    let fixtures = fixtures();
    let java_bytes = fixtures.get("transport_handshake_request").unwrap().clone();

    let header = TcpHeader::decode(&java_bytes[..TcpHeader::HEADER_SIZE]).unwrap();
    let var_end = TcpHeader::HEADER_SIZE + header.variable_header_size as usize;
    let body = &java_bytes[var_end..];

    let mut encoder = DeflateEncoder::new(Vec::new(), Compression::fast());
    encoder.write_all(body).unwrap();
    let compressed_payload = encoder.finish().unwrap();
    let mut compressed_body = Vec::with_capacity(DEFLATE_HEADER.len() + compressed_payload.len());
    compressed_body.extend_from_slice(DEFLATE_HEADER);
    compressed_body.extend_from_slice(&compressed_payload);

    let message = TransportMessage {
        request_id: header.request_id,
        status: TransportStatus::request().with_compress(),
        version: header.version,
        variable_header: BytesMut::from(&java_bytes[TcpHeader::HEADER_SIZE..var_end]),
        body: BytesMut::from(&compressed_body[..]),
    };
    let mut frame = os_transport::frame::encode_message(&message);

    let DecodedFrame::Message(decoded) = decode_frame(&mut frame).unwrap().unwrap() else {
        panic!("expected message frame");
    };

    assert_eq!(decoded.request_id, header.request_id);
    assert!(decoded.status.is_compressed());
    assert!(decoded.status.is_request());
    assert_eq!(decoded.variable_header, message.variable_header);
    assert_eq!(&decoded.body[..], body);
}

#[test]
fn java_handshake_frames_decode_with_rust_frame_codec() {
    let fixtures = fixtures();

    for (name, expected_action) in [
        ("tcp_handshake_request", TCP_HANDSHAKE_ACTION),
        ("transport_handshake_request", TRANSPORT_HANDSHAKE_ACTION),
    ] {
        let mut frame = BytesMut::from(fixtures.get(name).unwrap().as_slice());
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected message frame");
        };
        let variable_header =
            RequestVariableHeader::read(message.variable_header.freeze()).unwrap();
        assert_eq!(variable_header.action, expected_action);
        assert!(frame.is_empty());
    }
}
