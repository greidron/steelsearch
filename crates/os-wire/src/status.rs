/// Status bits used in OpenSearch transport messages.
///
/// Mirrors `org.opensearch.transport.TransportStatus`.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct TransportStatus(u8);

impl TransportStatus {
    const REQRES: u8 = 1 << 0;
    const ERROR: u8 = 1 << 1;
    const COMPRESS: u8 = 1 << 2;
    const HANDSHAKE: u8 = 1 << 3;

    pub const fn from_bits(bits: u8) -> Self {
        Self(bits)
    }

    pub const fn bits(self) -> u8 {
        self.0
    }

    pub const fn request() -> Self {
        Self(0)
    }

    pub const fn response() -> Self {
        Self(Self::REQRES)
    }

    pub const fn is_request(self) -> bool {
        self.0 & Self::REQRES == 0
    }

    pub const fn is_response(self) -> bool {
        !self.is_request()
    }

    pub const fn is_error(self) -> bool {
        self.0 & Self::ERROR != 0
    }

    pub const fn is_compressed(self) -> bool {
        self.0 & Self::COMPRESS != 0
    }

    pub const fn is_handshake(self) -> bool {
        self.0 & Self::HANDSHAKE != 0
    }

    pub const fn with_error(self) -> Self {
        Self(self.0 | Self::ERROR)
    }

    pub const fn with_compress(self) -> Self {
        Self(self.0 | Self::COMPRESS)
    }

    pub const fn with_handshake(self) -> Self {
        Self(self.0 | Self::HANDSHAKE)
    }
}

impl From<TransportStatus> for u8 {
    fn from(status: TransportStatus) -> Self {
        status.bits()
    }
}

#[cfg(test)]
mod tests {
    use super::TransportStatus;

    #[test]
    fn mirrors_opensearch_status_bits() {
        let request = TransportStatus::request();
        assert!(request.is_request());
        assert_eq!(request.bits(), 0);

        let response = TransportStatus::response()
            .with_error()
            .with_compress()
            .with_handshake();
        assert!(response.is_response());
        assert!(response.is_error());
        assert!(response.is_compressed());
        assert!(response.is_handshake());
        assert_eq!(response.bits(), 0b1111);
    }
}
