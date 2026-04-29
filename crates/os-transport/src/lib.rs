//! Transport layer scaffolding for OpenSearch-compatible TCP communication.

pub mod action;
pub mod compression;
pub mod error;
pub mod frame;
pub mod handshake;
pub mod internal_transport;
pub mod variable_header;

use bytes::BytesMut;
use os_core::Version;
use os_wire::{TcpHeader, TransportStatus};

pub const PING_FRAME: &[u8; 6] = b"ES\0\0\0\0";

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportMessage {
    pub request_id: i64,
    pub status: TransportStatus,
    pub version: Version,
    pub variable_header: BytesMut,
    pub body: BytesMut,
}

impl TransportMessage {
    pub fn header(&self) -> TcpHeader {
        TcpHeader {
            request_id: self.request_id,
            status: self.status.bits(),
            version: self.version,
            content_size: (self.variable_header.len() + self.body.len()) as i32,
            variable_header_size: self.variable_header.len() as i32,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{TransportMessage, PING_FRAME};
    use bytes::BytesMut;
    use os_core::OPENSEARCH_3_0_0;
    use os_wire::TransportStatus;

    #[test]
    fn ping_frame_matches_opensearch_marker_and_zero_length() {
        assert_eq!(PING_FRAME, b"ES\0\0\0\0");
    }

    #[test]
    fn builds_request_header_from_message() {
        let message = TransportMessage {
            request_id: 7,
            status: TransportStatus::request().with_handshake(),
            version: OPENSEARCH_3_0_0,
            variable_header: BytesMut::from(&b"abc"[..]),
            body: BytesMut::from(&b"body"[..]),
        };

        let header = message.header();

        assert_eq!(header.request_id, 7);
        assert_eq!(header.status, 0b1000);
        assert_eq!(header.content_size, 7);
        assert_eq!(header.variable_header_size, 3);
    }
}
