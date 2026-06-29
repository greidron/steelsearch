use bytes::Bytes;
use os_stream::{StreamInput, StreamInputError, StreamOutput};
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

pub fn write_illegal_argument_exception(output: &mut StreamOutput, message: Option<&str>) {
    output.write_bool(true);
    output.write_vint(6);
    output.write_optional_string(message);
    output.write_bool(false);
    write_empty_stack_trace(output);
}

pub fn write_rejected_execution_exception(output: &mut StreamOutput, message: Option<&str>) {
    output.write_bool(true);
    output.write_vint(18);
    output.write_bool(false);
    output.write_optional_string(message);
    write_empty_stack_trace(output);
}

pub fn write_search_context_missing_exception(
    output: &mut StreamOutput,
    message: Option<&str>,
    session_id: &str,
    context_id: i64,
) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(24);
    output.write_optional_string(message);
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    write_empty_string_list_map(output);
    output.write_i64(context_id);
    output.write_string(session_id);
}

pub fn write_search_phase_execution_exception_for_missing_context(
    output: &mut StreamOutput,
    phase_name: &str,
    message: &str,
    missing_context_message: &str,
    session_id: &str,
    context_id: i64,
) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(100);
    output.write_optional_string(Some(message));
    write_nested_search_context_missing_exception(
        output,
        Some(missing_context_message),
        session_id,
        context_id,
    );
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    write_empty_string_list_map(output);
    output.write_optional_string(Some(phase_name));
    output.write_vint(1);
    output.write_bool(false);
    output.write_string(missing_context_message);
    output.write_string("NOT_FOUND");
    write_nested_search_context_missing_exception(
        output,
        Some(missing_context_message),
        session_id,
        context_id,
    );
}

fn write_nested_search_context_missing_exception(
    output: &mut StreamOutput,
    message: Option<&str>,
    session_id: &str,
    context_id: i64,
) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(24);
    output.write_optional_string(message);
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    write_empty_string_list_map(output);
    output.write_i64(context_id);
    output.write_string(session_id);
}

pub fn write_index_not_found_exception(output: &mut StreamOutput, index: &str) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(16);
    output.write_optional_string(Some(&format!("no such index [{index}]")));
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    output.write_vint(2);
    output.write_string("opensearch.index");
    output.write_vint(1);
    output.write_string(index);
    output.write_string("opensearch.index_uuid");
    output.write_vint(1);
    output.write_string("_na_");
}

pub fn write_invalid_index_name_exception(output: &mut StreamOutput, index: &str, desc: &str) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(32);
    output.write_optional_string(Some(&format!("Invalid index name [{index}], {desc}")));
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    output.write_vint(2);
    output.write_string("opensearch.index");
    output.write_vint(1);
    output.write_string(index);
    output.write_string("opensearch.index_uuid");
    output.write_vint(1);
    output.write_string("_na_");
}

pub fn write_index_closed_exception(output: &mut StreamOutput, index: &str) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(6);
    output.write_optional_string(Some("closed"));
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    output.write_vint(2);
    output.write_string("opensearch.index");
    output.write_vint(1);
    output.write_string(index);
    output.write_string("opensearch.index_uuid");
    output.write_vint(1);
    output.write_string("_na_");
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
        24 => {
            let _context_id = input.read_i64()?;
            let _session_id = input.read_string()?;
        }
        100 => {
            let _phase_name = input.read_optional_string()?;
            skip_shard_search_failures(input)?;
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

fn write_empty_stack_trace(output: &mut StreamOutput) {
    output.write_vint(0);
    output.write_vint(0);
}

fn write_empty_string_list_map(output: &mut StreamOutput) {
    output.write_vint(0);
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

fn skip_shard_search_failures(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let len = read_non_negative_len(input)?;
    for _ in 0..len {
        skip_optional_search_shard_target(input)?;
        let _reason = input.read_string()?;
        let _status = input.read_string()?;
        let _cause = read_exception(input)?;
    }
    Ok(())
}

fn skip_optional_search_shard_target(
    input: &mut StreamInput,
) -> Result<(), TransportErrorDecodeError> {
    if input.read_bool()? {
        return Err(TransportErrorDecodeError::UnsupportedSearchShardTarget);
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
        6 => "org.opensearch.indices.IndexClosedException",
        16 => "org.opensearch.index.IndexNotFoundException",
        24 => "org.opensearch.search.SearchContextMissingException",
        32 => "org.opensearch.indices.InvalidIndexNameException",
        19 => "org.opensearch.ResourceNotFoundException",
        68 => "org.opensearch.OpenSearchException",
        71 => "org.opensearch.action.FailedNodeException",
        100 => "org.opensearch.action.search.SearchPhaseExecutionException",
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
    #[error("serialized search shard target payload is not supported")]
    UnsupportedSearchShardTarget,
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
    fn writes_jvm_illegal_argument_exception_message() {
        let mut output = StreamOutput::new();
        super::write_illegal_argument_exception(&mut output, Some("bad request"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(error.class_name, "java.lang.IllegalArgumentException");
        assert_eq!(error.message.as_deref(), Some("bad request"));
        assert!(error.cause.is_none());
    }

    #[test]
    fn writes_opensearch_rejected_execution_exception_message() {
        let mut output = StreamOutput::new();
        super::write_rejected_execution_exception(&mut output, Some("too many contexts"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.common.util.concurrent.OpenSearchRejectedExecutionException"
        );
        assert_eq!(error.message.as_deref(), Some("too many contexts"));
        assert!(error.cause.is_none());
    }

    #[test]
    fn writes_opensearch_search_context_missing_exception_message() {
        let mut output = StreamOutput::new();
        super::write_search_context_missing_exception(
            &mut output,
            Some("No search context found for id [42]"),
            "session-a",
            42,
        );

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.search.SearchContextMissingException"
        );
        assert_eq!(
            error.message.as_deref(),
            Some("No search context found for id [42]")
        );
        assert!(error.cause.is_none());
    }

    #[test]
    fn writes_search_phase_execution_exception_for_missing_context() {
        let mut output = StreamOutput::new();
        super::write_search_phase_execution_exception_for_missing_context(
            &mut output,
            "query",
            "all shards failed",
            "No search context found for id [77]",
            "scroll-session",
            77,
        );

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.action.search.SearchPhaseExecutionException"
        );
        assert_eq!(error.message.as_deref(), Some("all shards failed"));
        let cause = error.cause.as_ref().expect("search phase cause");
        assert_eq!(
            cause.class_name,
            "org.opensearch.search.SearchContextMissingException"
        );
        assert_eq!(
            cause.message.as_deref(),
            Some("No search context found for id [77]")
        );
    }

    #[test]
    fn writes_opensearch_index_not_found_exception_message() {
        let mut output = StreamOutput::new();
        super::write_index_not_found_exception(&mut output, "logs-missing");

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.index.IndexNotFoundException"
        );
        assert_eq!(
            error.message.as_deref(),
            Some("no such index [logs-missing]")
        );
        assert!(error.cause.is_none());
    }

    #[test]
    fn writes_opensearch_invalid_index_name_exception_message() {
        let mut output = StreamOutput::new();
        super::write_invalid_index_name_exception(&mut output, "_bad", "must not start with '_'.");

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.indices.InvalidIndexNameException"
        );
        assert_eq!(
            error.message.as_deref(),
            Some("Invalid index name [_bad], must not start with '_'.")
        );
        assert!(error.cause.is_none());
    }

    #[test]
    fn writes_opensearch_index_closed_exception_message() {
        let mut output = StreamOutput::new();
        super::write_index_closed_exception(&mut output, "logs-closed");

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.indices.IndexClosedException"
        );
        assert_eq!(error.message.as_deref(), Some("closed"));
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
        assert!(error
            .message
            .as_deref()
            .expect("should include fallback message")
            .contains("unsupported transport exception key 999"));
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
