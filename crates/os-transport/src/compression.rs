use bytes::BytesMut;
use flate2::read::DeflateDecoder;
use std::io::Read;
use thiserror::Error;

pub const DEFLATE_HEADER: &[u8; 4] = b"DFL\0";

pub fn is_deflate_compressed(bytes: &[u8]) -> bool {
    bytes.starts_with(DEFLATE_HEADER)
}

pub fn decompress_deflate_body(bytes: &[u8]) -> Result<BytesMut, CompressionError> {
    if !is_deflate_compressed(bytes) {
        return Err(CompressionError::MissingDeflateHeader);
    }

    let mut decoder = DeflateDecoder::new(&bytes[DEFLATE_HEADER.len()..]);
    let mut output = Vec::new();
    decoder.read_to_end(&mut output)?;
    Ok(BytesMut::from(&output[..]))
}

#[derive(Debug, Error)]
pub enum CompressionError {
    #[error("compressed transport body is missing DFL\\0 header")]
    MissingDeflateHeader,
    #[error("failed to inflate DEFLATE transport body")]
    Inflate(#[from] std::io::Error),
}

#[cfg(test)]
mod tests {
    use super::{decompress_deflate_body, is_deflate_compressed, DEFLATE_HEADER};
    use flate2::write::DeflateEncoder;
    use flate2::Compression;
    use std::io::Write;

    #[test]
    fn detects_deflate_header() {
        assert!(is_deflate_compressed(b"DFL\0payload"));
        assert!(!is_deflate_compressed(b"payload"));
    }

    #[test]
    fn decompresses_raw_deflate_body_after_opensearch_header() {
        let mut encoder = DeflateEncoder::new(Vec::new(), Compression::fast());
        encoder.write_all(b"hello transport").unwrap();
        let compressed = encoder.finish().unwrap();

        let mut body = Vec::new();
        body.extend_from_slice(DEFLATE_HEADER);
        body.extend_from_slice(&compressed);

        assert_eq!(
            &decompress_deflate_body(&body).unwrap()[..],
            b"hello transport"
        );
    }
}
