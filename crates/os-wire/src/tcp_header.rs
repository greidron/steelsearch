use bytes::{Buf, BufMut, BytesMut};
use os_core::Version;
use thiserror::Error;

const PREFIX: &[u8; 2] = b"ES";

/// Fixed-size OpenSearch TCP transport header.
///
/// This mirrors `org.opensearch.transport.TcpHeader` for modern OpenSearch
/// versions: marker bytes, message length, request id, status, version id, and
/// variable-header size.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TcpHeader {
    pub request_id: i64,
    pub status: u8,
    pub version: Version,
    pub content_size: i32,
    pub variable_header_size: i32,
}

impl TcpHeader {
    pub const MARKER_BYTES_SIZE: usize = 2;
    pub const MESSAGE_LENGTH_SIZE: usize = 4;
    pub const REQUEST_ID_SIZE: usize = 8;
    pub const STATUS_SIZE: usize = 1;
    pub const VERSION_ID_SIZE: usize = 4;
    pub const VARIABLE_HEADER_SIZE: usize = 4;
    pub const BYTES_REQUIRED_FOR_MESSAGE_SIZE: usize =
        Self::MARKER_BYTES_SIZE + Self::MESSAGE_LENGTH_SIZE;
    pub const VERSION_POSITION: usize = Self::MARKER_BYTES_SIZE
        + Self::MESSAGE_LENGTH_SIZE
        + Self::REQUEST_ID_SIZE
        + Self::STATUS_SIZE;
    pub const VARIABLE_HEADER_SIZE_POSITION: usize = Self::VERSION_POSITION + Self::VERSION_ID_SIZE;
    pub const HEADER_SIZE: usize = Self::VARIABLE_HEADER_SIZE_POSITION + Self::VARIABLE_HEADER_SIZE;

    pub fn encode(&self, dst: &mut BytesMut) {
        dst.put_slice(PREFIX);
        dst.put_i32(
            self.content_size
                + Self::REQUEST_ID_SIZE as i32
                + Self::STATUS_SIZE as i32
                + Self::VERSION_ID_SIZE as i32
                + Self::VARIABLE_HEADER_SIZE as i32,
        );
        dst.put_i64(self.request_id);
        dst.put_u8(self.status);
        dst.put_i32(self.version.id());
        dst.put_i32(self.variable_header_size);
    }

    pub fn decode(src: &[u8]) -> Result<Self, TcpHeaderError> {
        if src.len() < Self::HEADER_SIZE {
            return Err(TcpHeaderError::TooShort {
                actual: src.len(),
                required: Self::HEADER_SIZE,
            });
        }
        if &src[..2] != PREFIX {
            return Err(TcpHeaderError::InvalidPrefix);
        }

        let mut buf = &src[Self::MARKER_BYTES_SIZE..Self::HEADER_SIZE];
        let message_size = buf.get_i32();
        let request_id = buf.get_i64();
        let status = buf.get_u8();
        let version = Version::from_id(buf.get_i32());
        let variable_header_size = buf.get_i32();
        let content_size = message_size
            - Self::REQUEST_ID_SIZE as i32
            - Self::STATUS_SIZE as i32
            - Self::VERSION_ID_SIZE as i32
            - Self::VARIABLE_HEADER_SIZE as i32;

        Ok(Self {
            request_id,
            status,
            version,
            content_size,
            variable_header_size,
        })
    }
}

#[derive(Debug, Error)]
pub enum TcpHeaderError {
    #[error("transport header is too short: got {actual} bytes, need {required}")]
    TooShort { actual: usize, required: usize },
    #[error("transport header does not start with ES marker bytes")]
    InvalidPrefix,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encodes_and_decodes_header() {
        let header = TcpHeader {
            request_id: 42,
            status: 0,
            version: Version::from_id(3000099),
            content_size: 128,
            variable_header_size: 7,
        };

        let mut bytes = BytesMut::new();
        header.encode(&mut bytes);

        assert_eq!(bytes.len(), TcpHeader::HEADER_SIZE);
        assert_eq!(TcpHeader::decode(&bytes).unwrap(), header);
    }
}
