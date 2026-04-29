use bytes::{Buf, BytesMut};
use os_core::Version;
use os_wire::{TcpHeader, TcpHeaderError, TransportStatus};
use thiserror::Error;

use crate::compression::{decompress_deflate_body, CompressionError};
use crate::{TransportMessage, PING_FRAME};

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DecodedFrame {
    Ping,
    Message(TransportMessage),
}

pub fn encode_message(message: &TransportMessage) -> BytesMut {
    let mut bytes = BytesMut::with_capacity(
        TcpHeader::HEADER_SIZE + message.variable_header.len() + message.body.len(),
    );
    message.header().encode(&mut bytes);
    bytes.extend_from_slice(&message.variable_header);
    bytes.extend_from_slice(&message.body);
    bytes
}

pub fn decode_frame(src: &mut BytesMut) -> Result<Option<DecodedFrame>, FrameError> {
    if src.len() < TcpHeader::BYTES_REQUIRED_FOR_MESSAGE_SIZE {
        return Ok(None);
    }

    if &src[..2] != b"ES" {
        return Err(FrameError::InvalidPrefix);
    }

    let message_size = (&src[2..6]).get_i32();
    if message_size == 0 {
        src.advance(PING_FRAME.len());
        return Ok(Some(DecodedFrame::Ping));
    }
    if message_size < 0 {
        return Err(FrameError::NegativeMessageSize(message_size));
    }

    let frame_len = TcpHeader::BYTES_REQUIRED_FOR_MESSAGE_SIZE + message_size as usize;
    if src.len() < frame_len {
        return Ok(None);
    }

    let frame = src.split_to(frame_len);
    let header = TcpHeader::decode(&frame[..TcpHeader::HEADER_SIZE])?;
    if header.variable_header_size < 0 || header.content_size < header.variable_header_size {
        return Err(FrameError::InvalidHeaderSizes {
            content_size: header.content_size,
            variable_header_size: header.variable_header_size,
        });
    }

    let variable_start = TcpHeader::HEADER_SIZE;
    let variable_end = variable_start + header.variable_header_size as usize;
    let body_end = variable_start + header.content_size as usize;

    let status = TransportStatus::from_bits(header.status);
    let body = if status.is_compressed() {
        decompress_deflate_body(&frame[variable_end..body_end])?
    } else {
        BytesMut::from(&frame[variable_end..body_end])
    };

    Ok(Some(DecodedFrame::Message(TransportMessage {
        request_id: header.request_id,
        status,
        version: Version::from_id(header.version.id()),
        variable_header: BytesMut::from(&frame[variable_start..variable_end]),
        body,
    })))
}

#[derive(Debug, Error)]
pub enum FrameError {
    #[error("transport frame does not start with ES marker bytes")]
    InvalidPrefix,
    #[error("negative transport message size: {0}")]
    NegativeMessageSize(i32),
    #[error("invalid transport header sizes: content={content_size}, variable_header={variable_header_size}")]
    InvalidHeaderSizes {
        content_size: i32,
        variable_header_size: i32,
    },
    #[error(transparent)]
    Header(#[from] TcpHeaderError),
    #[error(transparent)]
    Compression(#[from] CompressionError),
}

#[cfg(test)]
mod tests {
    use super::{decode_frame, encode_message, DecodedFrame};
    use crate::compression::DEFLATE_HEADER;
    use crate::{TransportMessage, PING_FRAME};
    use bytes::BytesMut;
    use flate2::write::DeflateEncoder;
    use flate2::Compression;
    use os_core::OPENSEARCH_3_0_0;
    use os_wire::TransportStatus;
    use std::io::Write;

    #[test]
    fn decodes_ping_frame() {
        let mut bytes = BytesMut::from(&PING_FRAME[..]);
        assert_eq!(decode_frame(&mut bytes).unwrap(), Some(DecodedFrame::Ping));
        assert!(bytes.is_empty());
    }

    #[test]
    fn returns_none_for_partial_frame() {
        let mut bytes = BytesMut::from(&b"ES\0"[..]);
        assert_eq!(decode_frame(&mut bytes).unwrap(), None);
        assert_eq!(&bytes[..], b"ES\0");
    }

    #[test]
    fn message_frame_roundtrips() {
        let message = TransportMessage {
            request_id: 123,
            status: TransportStatus::request().with_handshake(),
            version: OPENSEARCH_3_0_0,
            variable_header: BytesMut::from(&b"headers"[..]),
            body: BytesMut::from(&b"payload"[..]),
        };
        let mut bytes = encode_message(&message);

        assert_eq!(
            decode_frame(&mut bytes).unwrap(),
            Some(DecodedFrame::Message(message))
        );
        assert!(bytes.is_empty());
    }

    #[test]
    fn decodes_compressed_message_body() {
        let mut encoder = DeflateEncoder::new(Vec::new(), Compression::fast());
        encoder.write_all(b"payload").unwrap();
        let compressed = encoder.finish().unwrap();

        let mut compressed_body = BytesMut::new();
        compressed_body.extend_from_slice(DEFLATE_HEADER);
        compressed_body.extend_from_slice(&compressed);

        let message = TransportMessage {
            request_id: 123,
            status: TransportStatus::response().with_compress(),
            version: OPENSEARCH_3_0_0,
            variable_header: BytesMut::from(&b"headers"[..]),
            body: compressed_body,
        };
        let mut bytes = encode_message(&message);

        let DecodedFrame::Message(decoded) = decode_frame(&mut bytes).unwrap().unwrap() else {
            panic!("expected message frame");
        };

        assert!(decoded.status.is_compressed());
        assert_eq!(&decoded.variable_header[..], b"headers");
        assert_eq!(&decoded.body[..], b"payload");
        assert!(bytes.is_empty());
    }
}
