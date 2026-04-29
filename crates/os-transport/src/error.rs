use bytes::Bytes;
use os_stream::{StreamInput, StreamInputError};
use thiserror::Error;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportError {
    pub class_name: String,
    pub message: Option<String>,
    pub cause: Option<Box<TransportError>>,
}

impl TransportError {
    pub fn read(bytes: Bytes) -> Result<Option<Self>, TransportErrorDecodeError> {
        let mut input = StreamInput::new(bytes);
        let error = read_exception(&mut input)?;
        if input.remaining() != 0 {
            return Err(TransportErrorDecodeError::TrailingBytes(input.remaining()));
        }
        Ok(error)
    }

    pub fn summary(&self) -> String {
        let mut summary = self.class_name.clone();
        if let Some(message) = &self.message {
            summary.push_str(": ");
            summary.push_str(message);
        }
        if let Some(cause) = &self.cause {
            summary.push_str("; caused_by=");
            summary.push_str(&cause.summary());
        }
        summary
    }
}

pub fn read_exception(
    input: &mut StreamInput,
) -> Result<Option<TransportError>, TransportErrorDecodeError> {
    if !input.read_bool()? {
        return Ok(None);
    }

    let key = input.read_vint()?;
    let error = match key {
        0 => read_opensearch_exception(input)?,
        4 => read_jvm_exception(input, "java.lang.NullPointerException", false)?,
        5 => read_jvm_exception(input, "java.lang.NumberFormatException", false)?,
        6 => read_jvm_exception(input, "java.lang.IllegalArgumentException", true)?,
        8 => read_jvm_exception(input, "java.io.EOFException", false)?,
        9 => read_jvm_exception(input, "java.lang.SecurityException", true)?,
        10 => read_jvm_exception(input, "java.lang.StringIndexOutOfBoundsException", false)?,
        11 => read_jvm_exception(input, "java.lang.ArrayIndexOutOfBoundsException", false)?,
        12 => read_jvm_exception(input, "java.io.FileNotFoundException", false)?,
        14 => read_jvm_exception(input, "java.lang.IllegalStateException", true)?,
        16 => read_jvm_exception(input, "java.lang.InterruptedException", false)?,
        17 => read_jvm_exception(input, "java.io.IOException", true)?,
        18 => {
            let _is_executor_shutdown = input.read_bool()?;
            read_jvm_exception(
                input,
                "org.opensearch.common.util.concurrent.OpenSearchRejectedExecutionException",
                false,
            )?
        }
        other => read_unknown_transport_exception(input, other)?,
    };

    Ok(Some(error))
}

fn read_jvm_exception(
    input: &mut StreamInput,
    class_name: &str,
    has_cause: bool,
) -> Result<TransportError, TransportErrorDecodeError> {
    let message = input.read_optional_string()?;
    let cause = if has_cause {
        read_exception(input)?.map(Box::new)
    } else {
        None
    };
    skip_stack_trace(input)?;
    Ok(TransportError {
        class_name: class_name.to_string(),
        message,
        cause,
    })
}

fn read_unknown_transport_exception(
    input: &mut StreamInput,
    key: i32,
) -> Result<TransportError, TransportErrorDecodeError> {
    let _remaining_payload = input.read_bytes(input.remaining() as usize)?;

    let error = TransportError {
        class_name: "org.opensearch.transport.UnknownTransportException".to_string(),
        message: Some(format!("unsupported transport exception key {key}")),
        cause: None,
    };

    Ok(error)
}

fn read_opensearch_exception(
    input: &mut StreamInput,
) -> Result<TransportError, TransportErrorDecodeError> {
    let id = input.read_vint()?;
    let class_name = opensearch_exception_class_name(id).to_string();
    let message = input.read_optional_string()?;
    let cause = read_exception(input)?.map(Box::new);
    skip_stack_trace(input)?;
    skip_string_list_map(input)?;
    skip_string_list_map(input)?;

    match id {
        101 => {
            let _action = input.read_optional_string()?;
        }
        103 => {
            skip_optional_transport_address(input)?;
            let _action = input.read_optional_string()?;
        }
        _ => {}
    }

    Ok(TransportError {
        class_name,
        message,
        cause,
    })
}

fn skip_stack_trace(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let frame_count = read_non_negative_len(input)?;
    for _ in 0..frame_count {
        let _declaring_class = input.read_string()?;
        let _file_name = input.read_optional_string()?;
        let _method_name = input.read_string()?;
        let _line_number = input.read_vint()?;
    }

    let suppressed_count = read_non_negative_len(input)?;
    for _ in 0..suppressed_count {
        let _suppressed = read_exception(input)?;
    }
    Ok(())
}

fn skip_string_list_map(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let len = read_non_negative_len(input)?;
    for _ in 0..len {
        let _key = input.read_string()?;
        let values_len = read_non_negative_len(input)?;
        for _ in 0..values_len {
            let _value = input.read_string()?;
        }
    }
    Ok(())
}

fn skip_optional_transport_address(
    input: &mut StreamInput,
) -> Result<(), TransportErrorDecodeError> {
    if input.read_bool()? {
        let len = input.read_byte()? as usize;
        match len {
            4 | 16 => {
                let _ip = input.read_bytes(len)?;
            }
            other => return Err(TransportErrorDecodeError::InvalidIpLength(other)),
        }
        let _host = input.read_string()?;
        let _port = input.read_i32()?;
    }
    Ok(())
}

fn read_non_negative_len(input: &mut StreamInput) -> Result<usize, TransportErrorDecodeError> {
    let len = input.read_vint()?;
    if len < 0 {
        return Err(TransportErrorDecodeError::NegativeLength(len));
    }
    Ok(len as usize)
}

fn opensearch_exception_class_name(id: i32) -> &'static str {
    match id {
        101 => "org.opensearch.transport.ActionNotFoundTransportException",
        102 => "org.opensearch.transport.TransportSerializationException",
        103 => "org.opensearch.transport.RemoteTransportException",
        _ => "org.opensearch.OpenSearchException",
    }
}

#[derive(Debug, Error)]
pub enum TransportErrorDecodeError {
    #[error(transparent)]
    Stream(#[from] StreamInputError),
    #[error("unsupported serialized exception key: {0}")]
    UnsupportedExceptionKey(i32),
    #[error("negative serialized collection length: {0}")]
    NegativeLength(i32),
    #[error("invalid transport address IP byte length: {0}")]
    InvalidIpLength(usize),
    #[error("transport error body has {0} trailing bytes")]
    TrailingBytes(usize),
}

#[cfg(test)]
mod tests {
    use super::TransportError;
    use os_stream::StreamOutput;

    #[test]
    fn decodes_jvm_exception_message() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(14);
        output.write_optional_string(Some("boom"));
        output.write_bool(false);
        write_empty_stack_trace(&mut output);

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(error.class_name, "java.lang.IllegalStateException");
        assert_eq!(error.message.as_deref(), Some("boom"));
        assert!(error.cause.is_none());
    }

    #[test]
    fn decodes_remote_transport_exception_with_cause() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(0);
        output.write_vint(103);
        output.write_optional_string(Some("[node][127.0.0.1:9300][missing:action]"));
        output.write_bool(true);
        output.write_vint(14);
        output.write_optional_string(Some("missing handler"));
        output.write_bool(false);
        write_empty_stack_trace(&mut output);
        write_empty_stack_trace(&mut output);
        output.write_vint(0);
        output.write_vint(0);
        output.write_bool(false);
        output.write_optional_string(Some("missing:action"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.transport.RemoteTransportException"
        );
        assert_eq!(
            error.cause.as_ref().unwrap().class_name,
            "java.lang.IllegalStateException"
        );
        assert!(error.summary().contains("missing handler"));
    }

    #[test]
    fn maps_unknown_exception_key_to_unknown_transport_exception() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(999);
        output.write_optional_string(Some("unsupported payload"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.transport.UnknownTransportException"
        );
        assert!(
            error
                .message
                .as_deref()
                .expect("should include fallback message")
                .contains("unsupported transport exception key 999")
        );
        assert_eq!(error.cause, None);
    }

    #[test]
    fn maps_unknown_exception_key_with_nonnormal_payload_to_unknown_transport_exception() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(999);
        output.write_vint(17);
        output.write_vint(42);

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.transport.UnknownTransportException"
        );
        assert_eq!(
            error.message.as_deref(),
            Some("unsupported transport exception key 999")
        );
    }

    #[test]
    fn maps_action_not_found_exception_id_to_transport_exception_class() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(0);
        output.write_vint(101);
        output.write_optional_string(Some("missing action"));
        output.write_bool(false);
        write_empty_stack_trace(&mut output);
        output.write_vint(0);
        output.write_vint(0);
        output.write_optional_string(Some("internal:transport/foobar"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.transport.ActionNotFoundTransportException"
        );
        assert_eq!(error.message.as_deref(), Some("missing action"));
    }

    #[test]
    fn maps_transport_serialization_exception_id_to_transport_exception_class() {
        let mut output = StreamOutput::new();
        output.write_bool(true);
        output.write_vint(0);
        output.write_vint(102);
        output.write_optional_string(Some("failed to serialize request"));
        output.write_bool(false);
        write_empty_stack_trace(&mut output);
        output.write_vint(0);
        output.write_vint(0);

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.transport.TransportSerializationException"
        );
        assert_eq!(
            error.message.as_deref(),
            Some("failed to serialize request")
        );
    }

    fn write_empty_stack_trace(output: &mut StreamOutput) {
        output.write_vint(0);
        output.write_vint(0);
    }
}
