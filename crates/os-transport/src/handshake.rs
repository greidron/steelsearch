use bytes::{Bytes, BytesMut};
use os_core::Version;
use os_stream::{StreamInput, StreamInputError, StreamOutput};
use os_wire::TransportStatus;
use std::collections::{BTreeMap, BTreeSet};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use thiserror::Error;

use crate::frame::encode_message;
use crate::variable_header::RequestVariableHeader;
use crate::TransportMessage;

pub const TCP_HANDSHAKE_ACTION: &str = "internal:tcp/handshake";
pub const TRANSPORT_HANDSHAKE_ACTION: &str = "internal:transport/handshake";

/// Builds an uncompressed low-level TCP handshake request.
///
/// Java OpenSearch sends this during connection establishment using
/// `TransportHandshaker.HANDSHAKE_ACTION_NAME`. The request body is a
/// `TransportRequest` parent task id followed by a bytes reference containing
/// the sender's version id.
pub fn build_tcp_handshake_request(
    request_id: i64,
    header_version: Version,
    payload_version: Version,
) -> BytesMut {
    let variable_header = RequestVariableHeader::new(TCP_HANDSHAKE_ACTION).to_bytes();
    let mut body = StreamOutput::new();
    write_empty_transport_request(&mut body);
    write_version_bytes_reference(&mut body, payload_version);

    let message = TransportMessage {
        request_id,
        status: TransportStatus::request().with_handshake(),
        version: header_version,
        variable_header: BytesMut::from(&variable_header[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };

    encode_message(&message)
}

/// Builds an uncompressed high-level transport handshake request.
///
/// The high-level request body is just an empty `TransportRequest`; the response
/// carries discovery node, cluster name, and version.
pub fn build_transport_handshake_request(request_id: i64, version: Version) -> BytesMut {
    let variable_header = RequestVariableHeader::new(TRANSPORT_HANDSHAKE_ACTION).to_bytes();
    let mut body = StreamOutput::new();
    write_empty_transport_request(&mut body);

    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(&variable_header[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };

    encode_message(&message)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportHandshakeResponse {
    pub discovery_node: Option<DiscoveryNode>,
    pub cluster_name: String,
    pub version: Version,
}

impl TransportHandshakeResponse {
    pub fn read(bytes: Bytes, stream_version: Version) -> Result<Self, HandshakeDecodeError> {
        let mut input = StreamInput::new(bytes);
        let discovery_node = if input.read_bool()? {
            Some(DiscoveryNode::read(&mut input, stream_version)?)
        } else {
            None
        };
        let cluster_name = input.read_string()?;
        let version = Version::from_id(input.read_vint()?);
        if input.remaining() != 0 {
            return Err(HandshakeDecodeError::TrailingBytes(input.remaining()));
        }
        Ok(Self {
            discovery_node,
            cluster_name,
            version,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscoveryNode {
    pub name: String,
    pub id: String,
    pub ephemeral_id: String,
    pub host_name: String,
    pub host_address: String,
    pub address: TransportAddress,
    pub stream_address: Option<TransportAddress>,
    pub attributes: BTreeMap<String, String>,
    pub roles: BTreeSet<DiscoveryNodeRole>,
    pub version: Version,
}

impl DiscoveryNode {
    fn read(
        input: &mut StreamInput,
        stream_version: Version,
    ) -> Result<Self, HandshakeDecodeError> {
        let name = input.read_string()?;
        let id = input.read_string()?;
        let ephemeral_id = input.read_string()?;
        let host_name = input.read_string()?;
        let host_address = input.read_string()?;
        let address = TransportAddress::read(input)?;
        let stream_address = if stream_version.id() >= 137_237_827 {
            if input.read_bool()? {
                Some(TransportAddress::read(input)?)
            } else {
                None
            }
        } else {
            None
        };
        let attributes = input.read_string_map()?;

        let role_count = input.read_vint()?;
        if role_count < 0 {
            return Err(HandshakeDecodeError::NegativeRoleCount(role_count));
        }
        let mut roles = BTreeSet::new();
        for _ in 0..role_count {
            roles.insert(DiscoveryNodeRole {
                name: input.read_string()?,
                abbreviation: input.read_string()?,
                can_contain_data: input.read_bool()?,
            });
        }
        let version = Version::from_id(input.read_vint()?);

        Ok(Self {
            name,
            id,
            ephemeral_id,
            host_name,
            host_address,
            address,
            stream_address,
            attributes,
            roles,
            version,
        })
    }
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct DiscoveryNodeRole {
    pub name: String,
    pub abbreviation: String,
    pub can_contain_data: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportAddress {
    pub ip: IpAddr,
    pub host: String,
    pub port: i32,
}

impl TransportAddress {
    fn read(input: &mut StreamInput) -> Result<Self, HandshakeDecodeError> {
        let len = input.read_byte()? as usize;
        let raw = input.read_bytes(len)?;
        let ip = match len {
            4 => IpAddr::V4(Ipv4Addr::new(raw[0], raw[1], raw[2], raw[3])),
            16 => {
                let mut octets = [0u8; 16];
                octets.copy_from_slice(&raw);
                IpAddr::V6(Ipv6Addr::from(octets))
            }
            other => return Err(HandshakeDecodeError::InvalidIpLength(other)),
        };
        let host = input.read_string()?;
        let port = input.read_i32()?;
        Ok(Self { ip, host, port })
    }
}

fn write_empty_transport_request(output: &mut StreamOutput) {
    // TaskId.EMPTY_TASK_ID serializes as an empty node id and no numeric task id.
    output.write_string("");
}

#[derive(Debug, Error)]
pub enum HandshakeDecodeError {
    #[error(transparent)]
    Stream(#[from] StreamInputError),
    #[error("invalid transport address IP byte length: {0}")]
    InvalidIpLength(usize),
    #[error("negative discovery node role count: {0}")]
    NegativeRoleCount(i32),
    #[error("transport handshake response body has {0} trailing bytes")]
    TrailingBytes(usize),
}

fn write_version_bytes_reference(output: &mut StreamOutput, version: Version) {
    let mut version_bytes = StreamOutput::new();
    version_bytes.write_vint(version.id());
    output.write_bytes_reference(&version_bytes.freeze());
}

#[cfg(test)]
mod tests {
    use super::{
        build_tcp_handshake_request, build_transport_handshake_request, TCP_HANDSHAKE_ACTION,
        TRANSPORT_HANDSHAKE_ACTION,
    };
    use crate::frame::{decode_frame, DecodedFrame};
    use crate::variable_header::RequestVariableHeader;
    use os_core::Version;
    use os_stream::{StreamInput, StreamOutput};

    #[test]
    fn builds_tcp_handshake_request() {
        let mut frame =
            build_tcp_handshake_request(1, Version::from_id(3000099), Version::from_id(3000099));
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected message frame");
        };
        let variable_header =
            RequestVariableHeader::read(message.variable_header.freeze()).unwrap();
        assert_eq!(variable_header.action, TCP_HANDSHAKE_ACTION);

        let mut body = StreamInput::new(message.body.freeze());
        assert_eq!(body.read_string().unwrap(), "");
        let mut version_bytes = StreamInput::new(body.read_bytes_reference().unwrap());
        assert_eq!(version_bytes.read_vint().unwrap(), 3000099);
    }

    #[test]
    fn builds_transport_handshake_request() {
        let mut frame = build_transport_handshake_request(2, Version::from_id(3000099));
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected message frame");
        };
        let variable_header =
            RequestVariableHeader::read(message.variable_header.freeze()).unwrap();
        assert_eq!(variable_header.action, TRANSPORT_HANDSHAKE_ACTION);

        let mut body = StreamInput::new(message.body.freeze());
        assert_eq!(body.read_string().unwrap(), "");
        assert_eq!(body.remaining(), 0);
    }

    #[test]
    fn handshake_request_starts_with_es_marker() {
        let frame = build_tcp_handshake_request(1, Version::from_id(1), Version::from_id(1));
        assert_eq!(&frame[..2], b"ES");
    }

    #[test]
    fn decodes_transport_handshake_response_body() {
        let version = Version::from_id(137287827);
        let mut body = StreamOutput::new();
        body.write_bool(true);
        body.write_string("node-a");
        body.write_string("node-id");
        body.write_string("ephemeral-id");
        body.write_string("127.0.0.1");
        body.write_string("127.0.0.1");
        body.write_byte(4);
        for byte in [127, 0, 0, 1] {
            body.write_byte(byte);
        }
        body.write_string("127.0.0.1");
        body.write_i32(9300);
        body.write_bool(false);
        body.write_vint(1);
        body.write_string("testattr");
        body.write_string("test");
        body.write_vint(1);
        body.write_string("data");
        body.write_string("d");
        body.write_bool(true);
        body.write_vint(version.id());
        body.write_string("cluster-a");
        body.write_vint(version.id());

        let response = super::TransportHandshakeResponse::read(body.freeze(), version).unwrap();

        assert_eq!(response.cluster_name, "cluster-a");
        assert_eq!(response.version, version);
        let node = response.discovery_node.unwrap();
        assert_eq!(node.name, "node-a");
        assert_eq!(node.address.host, "127.0.0.1");
        assert_eq!(node.address.port, 9300);
        assert_eq!(node.attributes.get("testattr").unwrap(), "test");
        assert!(node.roles.iter().any(|role| role.name == "data"));
    }
}
