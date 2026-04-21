use bytes::Bytes;
use os_stream::{StreamInput, StreamInputError, StreamOutput};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ThreadHeaders {
    pub request: BTreeMap<String, String>,
    pub response: BTreeMap<String, BTreeSet<String>>,
}

impl ThreadHeaders {
    pub fn read(input: &mut StreamInput) -> Result<Self, StreamInputError> {
        Ok(Self {
            request: input.read_string_map()?,
            response: input.read_string_set_map()?,
        })
    }

    pub fn write(&self, output: &mut StreamOutput) {
        output.write_string_map(&self.request);
        output.write_string_set_map(&self.response);
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RequestVariableHeader {
    pub thread_headers: ThreadHeaders,
    pub features: Vec<String>,
    pub action: String,
}

impl RequestVariableHeader {
    pub fn new(action: impl Into<String>) -> Self {
        Self {
            thread_headers: ThreadHeaders::default(),
            features: Vec::new(),
            action: action.into(),
        }
    }

    pub fn read(bytes: Bytes) -> Result<Self, StreamInputError> {
        let mut input = StreamInput::new(bytes);
        Ok(Self {
            thread_headers: ThreadHeaders::read(&mut input)?,
            features: input.read_string_array()?,
            action: input.read_string()?,
        })
    }

    pub fn write(&self, output: &mut StreamOutput) {
        self.thread_headers.write(output);
        output.write_string_array(&self.features);
        output.write_string(&self.action);
    }

    pub fn to_bytes(&self) -> Bytes {
        let mut output = StreamOutput::new();
        self.write(&mut output);
        output.freeze()
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ResponseVariableHeader {
    pub thread_headers: ThreadHeaders,
}

impl ResponseVariableHeader {
    pub fn read(bytes: Bytes) -> Result<Self, StreamInputError> {
        let mut input = StreamInput::new(bytes);
        Ok(Self {
            thread_headers: ThreadHeaders::read(&mut input)?,
        })
    }

    pub fn write(&self, output: &mut StreamOutput) {
        self.thread_headers.write(output);
    }

    pub fn to_bytes(&self) -> Bytes {
        let mut output = StreamOutput::new();
        self.write(&mut output);
        output.freeze()
    }
}

#[cfg(test)]
mod tests {
    use super::RequestVariableHeader;

    #[test]
    fn request_variable_header_roundtrips() {
        let mut header = RequestVariableHeader::new("internal:transport/handshake");
        header.features = vec!["feature-a".to_string(), "feature-b".to_string()];

        let decoded = RequestVariableHeader::read(header.to_bytes()).unwrap();

        assert_eq!(decoded, header);
    }
}
