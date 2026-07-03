use bytes::Bytes;
use os_stream::{StreamInput, StreamInputError, StreamOutput};
use thiserror::Error;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportError {
    pub class_name: String,
    pub message: Option<String>,
    pub cause: Option<Box<TransportError>>,
    pub search_context_id: Option<TransportErrorSearchContextId>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TransportErrorSearchContextId {
    pub session_id: String,
    pub id: i64,
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

pub fn write_illegal_state_exception(output: &mut StreamOutput, message: Option<&str>) {
    output.write_bool(true);
    output.write_vint(14);
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

pub fn write_incompatible_cluster_state_version_exception(
    output: &mut StreamOutput,
    message: Option<&str>,
) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(75);
    output.write_optional_string(message);
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    write_empty_string_list_map(output);
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

pub fn write_resource_not_found_exception(output: &mut StreamOutput, message: Option<&str>) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(19);
    output.write_optional_string(message);
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    write_empty_string_list_map(output);
}

pub fn write_shard_not_found_exception(
    output: &mut StreamOutput,
    index: &str,
    index_uuid: &str,
    shard_id: i32,
) {
    output.write_bool(true);
    output.write_vint(0);
    output.write_vint(11);
    output.write_optional_string(Some("no such shard"));
    output.write_bool(false);
    write_empty_stack_trace(output);
    write_empty_string_list_map(output);
    output.write_vint(3);
    output.write_string("opensearch.index");
    output.write_vint(1);
    output.write_string(index);
    output.write_string("opensearch.index_uuid");
    output.write_vint(1);
    output.write_string(index_uuid);
    output.write_string("opensearch.shard");
    output.write_vint(1);
    output.write_string(&shard_id.to_string());
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
        search_context_id: None,
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
        search_context_id: None,
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

    let mut search_context_id = None;
    match id {
        101 => {
            let _action = input.read_optional_string()?;
        }
        40 | 72 => {
            let _line_number = input.read_i32()?;
            let _column_number = input.read_i32()?;
        }
        12 => {
            skip_action_transport_exception_fields(input)?;
            skip_optional_discovery_node(input)?;
        }
        20 | 83 => {
            skip_action_transport_exception_fields(input)?;
        }
        30 => {
            let _repository_name = input.read_optional_string()?;
            let _snapshot_name = input.read_optional_string()?;
        }
        36 => {
            skip_optional_search_shard_target(input)?;
        }
        42 => {
            let _number_of_files = input.read_i32()?;
            skip_byte_size_value(input)?;
        }
        49 => {
            skip_cluster_blocks(input)?;
        }
        57 | 82 | 88 => {
            let _name = input.read_optional_string()?;
        }
        62 => {
            let _name = input.read_string()?;
            let _status = input.read_byte()?;
        }
        71 => {
            let _node_id = input.read_optional_string()?;
        }
        76 => {
            let _phase = input.read_i32()?;
        }
        78 => {
            let _timestamp = input.read_optional_string()?;
        }
        79 => {
            let _type = input.read_string()?;
            let _id = input.read_string()?;
        }
        17 | 97 | 155 => {
            let _current_state = input.read_byte()?;
        }
        149 => {
            let _max_buckets = input.read_i32()?;
        }
        163 => {
            let _attribute_name = input.read_string()?;
            let _attribute_value = input.read_string()?;
        }
        177 => {
            let _error_code = input.read_byte()?;
        }
        133 => {
            let _byte_limit = input.read_i64()?;
            let _bytes_wanted = input.read_i64()?;
            let _durability = input.read_vint()?;
        }
        143 => {
            let _script_stack = input.read_string_array()?;
            let _script = input.read_string()?;
            let _lang = input.read_string()?;
            skip_optional_script_position(input)?;
        }
        145 => {
            let _status = input.read_byte()?;
        }
        171 => {
            let _name = input.read_string()?;
            let _type = input.read_string()?;
            let _status = input.read_i32()?;
        }
        175 => {
            let _response_limit = input.read_vint()?;
            let _limit_entity = input.read_vint()?;
        }
        103 => {
            skip_optional_transport_address(input)?;
            let _action = input.read_optional_string()?;
        }
        24 => {
            let context_id = input.read_i64()?;
            let session_id = input.read_string()?;
            search_context_id = Some(TransportErrorSearchContextId {
                session_id,
                id: context_id,
            });
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
        search_context_id,
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

fn skip_action_transport_exception_fields(
    input: &mut StreamInput,
) -> Result<(), TransportErrorDecodeError> {
    skip_optional_transport_address(input)?;
    let _action = input.read_optional_string()?;
    Ok(())
}

fn skip_optional_discovery_node(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    if input.read_bool()? {
        skip_discovery_node(input)?;
    }
    Ok(())
}

fn skip_discovery_node(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let _name = input.read_string()?;
    let _id = input.read_string()?;
    let _ephemeral_id = input.read_string()?;
    let _host_name = input.read_string()?;
    let _host_address = input.read_string()?;
    skip_transport_address(input)?;
    if input.read_bool()? {
        skip_transport_address(input)?;
    }
    let _attributes = input.read_string_map()?;
    let role_count = read_non_negative_len(input)?;
    for _ in 0..role_count {
        let _name = input.read_string()?;
        let _abbreviation = input.read_string()?;
        let _can_contain_data = input.read_bool()?;
    }
    let _version = input.read_vint()?;
    Ok(())
}

fn skip_optional_script_position(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    if input.read_bool()? {
        let _offset = input.read_i32()?;
        let _start = input.read_i32()?;
        let _end = input.read_i32()?;
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
        skip_optional_text(input)?;
        skip_shard_id(input)?;
        let _cluster_alias = input.read_optional_string()?;
    }
    Ok(())
}

fn skip_optional_text(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    if input.read_bool()? {
        let _text = input.read_string()?;
    }
    Ok(())
}

fn skip_shard_id(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let _index_name = input.read_string()?;
    let _index_uuid = input.read_string()?;
    let _shard_id = input.read_vint()?;
    Ok(())
}

fn skip_byte_size_value(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let _size = input.read_zlong()?;
    let _unit = input.read_vint()?;
    Ok(())
}

fn skip_transport_address(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let len = input.read_byte()? as usize;
    match len {
        4 | 16 => {
            let _ip = input.read_bytes(len)?;
        }
        other => return Err(TransportErrorDecodeError::InvalidIpLength(other)),
    }
    let _host = input.read_string()?;
    let _port = input.read_i32()?;
    Ok(())
}

fn skip_cluster_blocks(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let len = read_non_negative_len(input)?;
    for _ in 0..len {
        let _id = input.read_vint()?;
        let _uuid = input.read_optional_string()?;
        let _description = input.read_string()?;
        skip_enum_set(input)?;
        let _retryable = input.read_bool()?;
        let _disable_state_persistence = input.read_bool()?;
        let _status = input.read_string()?;
        let _allow_release_resources = input.read_bool()?;
    }
    Ok(())
}

fn skip_enum_set(input: &mut StreamInput) -> Result<(), TransportErrorDecodeError> {
    let len = read_non_negative_len(input)?;
    for _ in 0..len {
        let _ordinal = input.read_vint()?;
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
        0 => "org.opensearch.core.index.snapshots.IndexShardSnapshotFailedException",
        1 => "org.opensearch.search.dfs.DfsPhaseExecutionException",
        2 => "org.opensearch.common.util.CancellableThreads.ExecutionCancelledException",
        3 => "org.opensearch.discovery.ClusterManagerNotDiscoveredException",
        4 => "org.opensearch.OpenSearchSecurityException",
        5 => "org.opensearch.index.snapshots.IndexShardRestoreException",
        6 => "org.opensearch.indices.IndexClosedException",
        7 => "org.opensearch.http.BindHttpException",
        8 => "org.opensearch.action.search.ReduceSearchPhaseException",
        9 => "org.opensearch.node.NodeClosedException",
        10 => "org.opensearch.index.engine.SnapshotFailedEngineException",
        11 => "org.opensearch.index.shard.ShardNotFoundException",
        12 => "org.opensearch.transport.ConnectTransportException",
        13 => "org.opensearch.transport.NotSerializableTransportException",
        14 => "org.opensearch.transport.ResponseHandlerFailureTransportException",
        15 => "org.opensearch.indices.IndexCreationException",
        16 => "org.opensearch.index.IndexNotFoundException",
        17 => "org.opensearch.cluster.routing.IllegalShardRoutingStateException",
        18 => "org.opensearch.action.support.broadcast.BroadcastShardOperationFailedException",
        19 => "org.opensearch.ResourceNotFoundException",
        20 => "org.opensearch.transport.ActionTransportException",
        21 => "org.opensearch.OpenSearchGenerationException",
        23 => "org.opensearch.index.shard.IndexShardStartedException",
        24 => "org.opensearch.search.SearchContextMissingException",
        25 => "org.opensearch.script.GeneralScriptException",
        27 => "org.opensearch.snapshots.SnapshotCreationException",
        29 => "org.opensearch.index.engine.DocumentMissingException",
        30 => "org.opensearch.snapshots.SnapshotException",
        31 => "org.opensearch.indices.InvalidAliasNameException",
        32 => "org.opensearch.indices.InvalidIndexNameException",
        33 => "org.opensearch.indices.IndexPrimaryShardNotAllocatedException",
        34 => "org.opensearch.transport.TransportException",
        35 => "org.opensearch.OpenSearchParseException",
        36 => "org.opensearch.search.SearchException",
        37 => "org.opensearch.index.mapper.MapperException",
        38 => "org.opensearch.indices.InvalidTypeNameException",
        39 => "org.opensearch.snapshots.SnapshotRestoreException",
        40 => "org.opensearch.core.common.ParsingException",
        41 => "org.opensearch.index.shard.IndexShardClosedException",
        42 => "org.opensearch.indices.recovery.RecoverFilesRecoveryException",
        43 => "org.opensearch.index.translog.TruncatedTranslogException",
        44 => "org.opensearch.indices.recovery.RecoveryFailedException",
        45 => "org.opensearch.index.shard.IndexShardRelocatedException",
        46 => "org.opensearch.transport.NodeShouldNotConnectException",
        48 => "org.opensearch.index.translog.TranslogCorruptedException",
        49 => "org.opensearch.cluster.block.ClusterBlockException",
        50 => "org.opensearch.search.fetch.FetchPhaseExecutionException",
        52 => "org.opensearch.index.engine.VersionConflictEngineException",
        53 => "org.opensearch.index.engine.EngineException",
        55 => "org.opensearch.action.NoSuchNodeException",
        56 => "org.opensearch.common.settings.SettingsException",
        57 => "org.opensearch.indices.IndexTemplateMissingException",
        58 => "org.opensearch.transport.SendRequestTransportException",
        62 => "org.opensearch.core.common.io.stream.NotSerializableExceptionWrapper",
        63 => "org.opensearch.indices.AliasFilterParsingException",
        65 => "org.opensearch.gateway.GatewayException",
        66 => "org.opensearch.index.shard.IndexShardNotRecoveringException",
        67 => "org.opensearch.http.HttpException",
        68 => "org.opensearch.OpenSearchException",
        69 => "org.opensearch.snapshots.SnapshotMissingException",
        70 => "org.opensearch.action.PrimaryMissingActionException",
        71 => "org.opensearch.action.FailedNodeException",
        72 => "org.opensearch.search.SearchParseException",
        73 => "org.opensearch.snapshots.ConcurrentSnapshotExecutionException",
        74 => "org.opensearch.common.blobstore.BlobStoreException",
        75 => "org.opensearch.cluster.IncompatibleClusterStateVersionException",
        76 => "org.opensearch.index.engine.RecoveryEngineException",
        77 => "org.opensearch.common.util.concurrent.UncategorizedExecutionException",
        78 => "org.opensearch.action.TimestampParsingException",
        79 => "org.opensearch.action.RoutingMissingException",
        81 => "org.opensearch.index.snapshots.IndexShardRestoreFailedException",
        82 => "org.opensearch.repositories.RepositoryException",
        83 => "org.opensearch.transport.ReceiveTimeoutTransportException",
        84 => "org.opensearch.transport.NodeDisconnectedException",
        86 => "org.opensearch.search.aggregations.AggregationExecutionException",
        88 => "org.opensearch.indices.InvalidIndexTemplateException",
        90 => "org.opensearch.index.engine.RefreshFailedEngineException",
        91 => "org.opensearch.search.aggregations.AggregationInitializationException",
        92 => "org.opensearch.indices.recovery.DelayRecoveryException",
        94 => "org.opensearch.transport.client.transport.NoNodeAvailableException",
        96 => "org.opensearch.snapshots.InvalidSnapshotNameException",
        97 => "org.opensearch.index.shard.IllegalIndexShardStateException",
        98 => "org.opensearch.core.index.snapshots.IndexShardSnapshotException",
        99 => "org.opensearch.index.shard.IndexShardNotStartedException",
        100 => "org.opensearch.action.search.SearchPhaseExecutionException",
        101 => "org.opensearch.transport.ActionNotFoundTransportException",
        102 => "org.opensearch.transport.TransportSerializationException",
        103 => "org.opensearch.transport.RemoteTransportException",
        104 => "org.opensearch.index.engine.EngineCreationFailureException",
        105 => "org.opensearch.cluster.routing.RoutingException",
        106 => "org.opensearch.index.shard.IndexShardRecoveryException",
        107 => "org.opensearch.repositories.RepositoryMissingException",
        109 => "org.opensearch.index.engine.DocumentSourceMissingException",
        111 => "org.opensearch.common.settings.NoClassSettingsException",
        112 => "org.opensearch.transport.BindTransportException",
        113 => "org.opensearch.rest.action.admin.indices.AliasesNotFoundException",
        114 => "org.opensearch.index.shard.IndexShardRecoveringException",
        115 => "org.opensearch.index.translog.TranslogException",
        116 => "org.opensearch.cluster.metadata.ProcessClusterEventTimeoutException",
        117 => "org.opensearch.action.support.replication.ReplicationOperation.RetryOnPrimaryException",
        118 => "org.opensearch.OpenSearchTimeoutException",
        119 => "org.opensearch.search.query.QueryPhaseExecutionException",
        120 => "org.opensearch.repositories.RepositoryVerificationException",
        121 => "org.opensearch.search.aggregations.InvalidAggregationPathException",
        123 => "org.opensearch.ResourceAlreadyExistsException",
        125 => "org.opensearch.transport.TcpTransport.HttpRequestOnTransportException",
        126 => "org.opensearch.index.mapper.MapperParsingException",
        128 => "org.opensearch.search.builder.SearchSourceBuilderException",
        130 => "org.opensearch.action.NoShardAvailableActionException",
        131 => "org.opensearch.action.UnavailableShardsException",
        132 => "org.opensearch.index.engine.FlushFailedEngineException",
        133 => "org.opensearch.core.common.breaker.CircuitBreakingException",
        134 => "org.opensearch.transport.NodeNotConnectedException",
        135 => "org.opensearch.index.mapper.StrictDynamicMappingException",
        136 => "org.opensearch.action.support.replication.TransportReplicationAction.RetryOnReplicaException",
        137 => "org.opensearch.indices.TypeMissingException",
        140 => "org.opensearch.cluster.coordination.FailedToCommitClusterStateException",
        141 => "org.opensearch.index.query.QueryShardException",
        142 => "org.opensearch.cluster.action.shard.ShardStateAction.NoLongerPrimaryShardException",
        143 => "org.opensearch.script.ScriptException",
        144 => "org.opensearch.cluster.NotClusterManagerException",
        145 => "org.opensearch.OpenSearchStatusException",
        146 => "org.opensearch.core.tasks.TaskCancelledException",
        147 => "org.opensearch.env.ShardLockObtainFailedException",
        149 => "org.opensearch.search.aggregations.MultiBucketConsumerService.TooManyBucketsException",
        150 => "org.opensearch.cluster.coordination.CoordinationStateRejectedException",
        151 => "org.opensearch.snapshots.SnapshotInProgressException",
        152 => "org.opensearch.transport.NoSuchRemoteClusterException",
        153 => "org.opensearch.index.seqno.RetentionLeaseAlreadyExistsException",
        154 => "org.opensearch.index.seqno.RetentionLeaseNotFoundException",
        155 => "org.opensearch.index.shard.ShardNotInPrimaryModeException",
        156 => "org.opensearch.index.seqno.RetentionLeaseInvalidRetainingSeqNoException",
        157 => "org.opensearch.ingest.IngestProcessorException",
        158 => "org.opensearch.indices.recovery.PeerRecoveryNotFound",
        159 => "org.opensearch.cluster.coordination.NodeHealthCheckFailureException",
        160 => "org.opensearch.transport.NoSeedNodeLeftException",
        161 => "org.opensearch.indices.replication.common.ReplicationFailedException",
        162 => "org.opensearch.index.shard.PrimaryShardClosedException",
        163 => "org.opensearch.cluster.decommission.DecommissioningFailedException",
        164 => "org.opensearch.cluster.decommission.NodeDecommissionedException",
        165 => "org.opensearch.cluster.service.ClusterManagerThrottlingException",
        166 => "org.opensearch.snapshots.SnapshotInUseDeletionException",
        167 => "org.opensearch.cluster.routing.UnsupportedWeightedRoutingStateException",
        168 => "org.opensearch.cluster.routing.PreferenceBasedSearchNotAllowedException",
        169 => "org.opensearch.cluster.routing.NodeWeighedAwayException",
        170 => "org.opensearch.search.pipeline.SearchPipelineProcessingException",
        171 => "org.opensearch.crypto.CryptoRegistryException",
        172 => "org.opensearch.action.admin.indices.view.ViewNotFoundException",
        173 => "org.opensearch.action.admin.indices.view.ViewAlreadyExistsException",
        174 => "org.opensearch.indices.InvalidIndexContextException",
        175 => "org.opensearch.common.breaker.ResponseLimitBreachedException",
        176 => "org.opensearch.index.engine.IngestionEngineException",
        177 => "org.opensearch.transport.stream.StreamException",
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
        assert!(error.search_context_id.is_none());
    }

    #[test]
    fn writes_jvm_illegal_argument_exception_message() {
        let mut output = StreamOutput::new();
        super::write_illegal_argument_exception(&mut output, Some("bad request"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(error.class_name, "java.lang.IllegalArgumentException");
        assert_eq!(error.message.as_deref(), Some("bad request"));
        assert!(error.cause.is_none());
        assert!(error.search_context_id.is_none());
    }

    #[test]
    fn writes_jvm_illegal_state_exception_message() {
        let mut output = StreamOutput::new();
        super::write_illegal_state_exception(&mut output, Some("bad state"));

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(error.class_name, "java.lang.IllegalStateException");
        assert_eq!(error.message.as_deref(), Some("bad state"));
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
    fn writes_opensearch_resource_not_found_exception_message() {
        let mut output = StreamOutput::new();
        super::write_resource_not_found_exception(
            &mut output,
            Some("the task with id persistent-task-1 doesn't exist"),
        );

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(error.class_name, "org.opensearch.ResourceNotFoundException");
        assert_eq!(
            error.message.as_deref(),
            Some("the task with id persistent-task-1 doesn't exist")
        );
        assert!(error.cause.is_none());
        assert!(error.search_context_id.is_none());
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
        assert_eq!(
            error.search_context_id,
            Some(super::TransportErrorSearchContextId {
                session_id: "session-a".to_string(),
                id: 42,
            })
        );
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
        assert_eq!(
            cause.search_context_id,
            Some(super::TransportErrorSearchContextId {
                session_id: "scroll-session".to_string(),
                id: 77,
            })
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
    fn writes_opensearch_shard_not_found_exception_message() {
        let mut output = StreamOutput::new();
        super::write_shard_not_found_exception(&mut output, "logs", "uuid-logs", 2);

        let error = TransportError::read(output.freeze()).unwrap().unwrap();

        assert_eq!(
            error.class_name,
            "org.opensearch.index.shard.ShardNotFoundException"
        );
        assert_eq!(error.message.as_deref(), Some("no such shard"));
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

    #[test]
    fn maps_source_derived_super_only_opensearch_exception_ids() {
        for (id, class_name) in [
            (
                3,
                "org.opensearch.discovery.ClusterManagerNotDiscoveredException",
            ),
            (
                2,
                "org.opensearch.common.util.CancellableThreads.ExecutionCancelledException",
            ),
            (4, "org.opensearch.OpenSearchSecurityException"),
            (
                13,
                "org.opensearch.transport.NotSerializableTransportException",
            ),
            (56, "org.opensearch.common.settings.SettingsException"),
            (84, "org.opensearch.transport.NodeDisconnectedException"),
            (
                107,
                "org.opensearch.repositories.RepositoryMissingException",
            ),
            (
                117,
                "org.opensearch.action.support.replication.ReplicationOperation.RetryOnPrimaryException",
            ),
            (
                125,
                "org.opensearch.transport.TcpTransport.HttpRequestOnTransportException",
            ),
            (134, "org.opensearch.transport.NodeNotConnectedException"),
            (
                136,
                "org.opensearch.action.support.replication.TransportReplicationAction.RetryOnReplicaException",
            ),
            (
                142,
                "org.opensearch.cluster.action.shard.ShardStateAction.NoLongerPrimaryShardException",
            ),
            (
                140,
                "org.opensearch.cluster.coordination.FailedToCommitClusterStateException",
            ),
            (146, "org.opensearch.core.tasks.TaskCancelledException"),
            (
                153,
                "org.opensearch.index.seqno.RetentionLeaseAlreadyExistsException",
            ),
            (
                154,
                "org.opensearch.index.seqno.RetentionLeaseNotFoundException",
            ),
            (157, "org.opensearch.ingest.IngestProcessorException"),
            (
                172,
                "org.opensearch.action.admin.indices.view.ViewNotFoundException",
            ),
            (
                173,
                "org.opensearch.action.admin.indices.view.ViewAlreadyExistsException",
            ),
            (
                170,
                "org.opensearch.search.pipeline.SearchPipelineProcessingException",
            ),
        ] {
            let mut output = StreamOutput::new();
            write_base_opensearch_exception(&mut output, id, Some("source-derived failure"));

            let error = TransportError::read(output.freeze()).unwrap().unwrap();

            assert_eq!(error.class_name, class_name, "id {id}");
            assert_eq!(error.message.as_deref(), Some("source-derived failure"));
            assert!(error.cause.is_none(), "id {id}");
            assert!(error.search_context_id.is_none(), "id {id}");
        }
    }

    #[test]
    fn skips_source_derived_simple_extension_fields() {
        for case in [
            SimpleExtensionCase::new(40, "org.opensearch.core.common.ParsingException")
                .with_i32(12)
                .with_i32(34),
            SimpleExtensionCase::new(12, "org.opensearch.transport.ConnectTransportException")
                .with_optional_transport_address(false)
                .with_optional_string(Some("internal:transport/handshake"))
                .with_optional_discovery_node(false),
            SimpleExtensionCase::new(12, "org.opensearch.transport.ConnectTransportException")
                .with_optional_transport_address(false)
                .with_optional_string(Some("internal:transport/handshake"))
                .with_optional_discovery_node(true),
            SimpleExtensionCase::new(20, "org.opensearch.transport.ActionTransportException")
                .with_optional_transport_address(true)
                .with_optional_string(Some("indices:data/read/search")),
            SimpleExtensionCase::new(30, "org.opensearch.snapshots.SnapshotException")
                .with_optional_string(Some("repo-a"))
                .with_optional_string(Some("snapshot-1")),
            SimpleExtensionCase::new(36, "org.opensearch.search.SearchException")
                .with_optional_search_shard_target(true),
            SimpleExtensionCase::new(
                42,
                "org.opensearch.indices.recovery.RecoverFilesRecoveryException",
            )
            .with_i32(3)
            .with_byte_size_value(4096, 0),
            SimpleExtensionCase::new(49, "org.opensearch.cluster.block.ClusterBlockException")
                .with_cluster_block(),
            SimpleExtensionCase::new(57, "org.opensearch.indices.IndexTemplateMissingException")
                .with_optional_string(Some("missing-template")),
            SimpleExtensionCase::new(
                62,
                "org.opensearch.core.common.io.stream.NotSerializableExceptionWrapper",
            )
            .with_string("runtime_exception")
            .with_byte(0),
            SimpleExtensionCase::new(71, "org.opensearch.action.FailedNodeException")
                .with_optional_string(Some("node-a")),
            SimpleExtensionCase::new(72, "org.opensearch.search.SearchParseException")
                .with_i32(3)
                .with_i32(9),
            SimpleExtensionCase::new(76, "org.opensearch.index.engine.RecoveryEngineException")
                .with_i32(2),
            SimpleExtensionCase::new(78, "org.opensearch.action.TimestampParsingException")
                .with_optional_string(Some("2026-07-03T00:00:00Z")),
            SimpleExtensionCase::new(79, "org.opensearch.action.RoutingMissingException")
                .with_string("_doc")
                .with_string("doc-1"),
            SimpleExtensionCase::new(82, "org.opensearch.repositories.RepositoryException")
                .with_optional_string(Some("repo-a")),
            SimpleExtensionCase::new(
                83,
                "org.opensearch.transport.ReceiveTimeoutTransportException",
            )
            .with_optional_transport_address(false)
            .with_optional_string(Some("cluster:monitor/nodes/info")),
            SimpleExtensionCase::new(88, "org.opensearch.indices.InvalidIndexTemplateException")
                .with_optional_string(Some("template-a")),
            SimpleExtensionCase::new(
                97,
                "org.opensearch.index.shard.IllegalIndexShardStateException",
            )
            .with_byte(1),
            SimpleExtensionCase::new(
                17,
                "org.opensearch.cluster.routing.IllegalShardRoutingStateException",
            )
            .with_byte(2),
            SimpleExtensionCase::new(
                133,
                "org.opensearch.core.common.breaker.CircuitBreakingException",
            )
            .with_i64(1024)
            .with_i64(2048)
            .with_vint(1),
            SimpleExtensionCase::new(143, "org.opensearch.script.ScriptException")
                .with_string_array(&["ctx._source.count += params.inc"])
                .with_string("inline")
                .with_string("painless")
                .with_optional_script_position(true),
            SimpleExtensionCase::new(145, "org.opensearch.OpenSearchStatusException").with_byte(3),
            SimpleExtensionCase::new(
                149,
                "org.opensearch.search.aggregations.MultiBucketConsumerService.TooManyBucketsException",
            )
            .with_i32(10000),
            SimpleExtensionCase::new(
                155,
                "org.opensearch.index.shard.ShardNotInPrimaryModeException",
            )
            .with_byte(1),
            SimpleExtensionCase::new(
                163,
                "org.opensearch.cluster.decommission.DecommissioningFailedException",
            )
            .with_string("zone")
            .with_string("us-east-1a"),
            SimpleExtensionCase::new(171, "org.opensearch.crypto.CryptoRegistryException")
                .with_string("crypto-a")
                .with_string("kms")
                .with_i32(500),
            SimpleExtensionCase::new(
                175,
                "org.opensearch.common.breaker.ResponseLimitBreachedException",
            )
            .with_vint(1000)
            .with_vint(2),
            SimpleExtensionCase::new(177, "org.opensearch.transport.stream.StreamException")
                .with_byte(3),
        ] {
            let mut output = StreamOutput::new();
            write_base_opensearch_exception(&mut output, case.id, Some("extended failure"));
            for field in &case.fields {
                field.write_to(&mut output);
            }

            let error = TransportError::read(output.freeze()).unwrap().unwrap();

            assert_eq!(error.class_name, case.class_name, "id {}", case.id);
            assert_eq!(error.message.as_deref(), Some("extended failure"));
        }
    }

    fn write_empty_stack_trace(output: &mut StreamOutput) {
        output.write_vint(0);
        output.write_vint(0);
    }

    fn write_base_opensearch_exception(output: &mut StreamOutput, id: i32, message: Option<&str>) {
        output.write_bool(true);
        output.write_vint(0);
        output.write_vint(id);
        output.write_optional_string(message);
        output.write_bool(false);
        write_empty_stack_trace(output);
        output.write_vint(0);
        output.write_vint(0);
    }

    struct SimpleExtensionCase {
        id: i32,
        class_name: &'static str,
        fields: Vec<SimpleExtensionField>,
    }

    impl SimpleExtensionCase {
        fn new(id: i32, class_name: &'static str) -> Self {
            Self {
                id,
                class_name,
                fields: Vec::new(),
            }
        }

        fn with_i32(mut self, value: i32) -> Self {
            self.fields.push(SimpleExtensionField::I32(value));
            self
        }

        fn with_i64(mut self, value: i64) -> Self {
            self.fields.push(SimpleExtensionField::I64(value));
            self
        }

        fn with_vint(mut self, value: i32) -> Self {
            self.fields.push(SimpleExtensionField::VInt(value));
            self
        }

        fn with_byte(mut self, value: u8) -> Self {
            self.fields.push(SimpleExtensionField::Byte(value));
            self
        }

        fn with_string(mut self, value: &'static str) -> Self {
            self.fields.push(SimpleExtensionField::String(value));
            self
        }

        fn with_optional_string(mut self, value: Option<&'static str>) -> Self {
            self.fields
                .push(SimpleExtensionField::OptionalString(value));
            self
        }

        fn with_optional_transport_address(mut self, present: bool) -> Self {
            self.fields
                .push(SimpleExtensionField::OptionalTransportAddress(present));
            self
        }

        fn with_optional_discovery_node(mut self, present: bool) -> Self {
            self.fields
                .push(SimpleExtensionField::OptionalDiscoveryNode(present));
            self
        }

        fn with_optional_search_shard_target(mut self, present: bool) -> Self {
            self.fields
                .push(SimpleExtensionField::OptionalSearchShardTarget(present));
            self
        }

        fn with_optional_script_position(mut self, present: bool) -> Self {
            self.fields
                .push(SimpleExtensionField::OptionalScriptPosition(present));
            self
        }

        fn with_string_array(mut self, values: &[&'static str]) -> Self {
            self.fields
                .push(SimpleExtensionField::StringArray(values.to_vec()));
            self
        }

        fn with_byte_size_value(mut self, size: i64, unit: i32) -> Self {
            self.fields
                .push(SimpleExtensionField::ByteSizeValue { size, unit });
            self
        }

        fn with_cluster_block(mut self) -> Self {
            self.fields.push(SimpleExtensionField::ClusterBlock);
            self
        }
    }

    enum SimpleExtensionField {
        Byte(u8),
        ByteSizeValue { size: i64, unit: i32 },
        ClusterBlock,
        I32(i32),
        I64(i64),
        OptionalDiscoveryNode(bool),
        OptionalSearchShardTarget(bool),
        OptionalScriptPosition(bool),
        OptionalString(Option<&'static str>),
        OptionalTransportAddress(bool),
        String(&'static str),
        StringArray(Vec<&'static str>),
        VInt(i32),
    }

    impl SimpleExtensionField {
        fn write_to(&self, output: &mut StreamOutput) {
            match self {
                Self::Byte(value) => output.write_byte(*value),
                Self::ByteSizeValue { size, unit } => {
                    output.write_zlong(*size);
                    output.write_vint(*unit);
                }
                Self::ClusterBlock => {
                    output.write_vint(1);
                    output.write_vint(1);
                    output.write_optional_string(Some("block-uuid"));
                    output.write_string("metadata writes are blocked");
                    output.write_vint(2);
                    output.write_vint(0);
                    output.write_vint(1);
                    output.write_bool(false);
                    output.write_bool(false);
                    output.write_string("FORBIDDEN");
                    output.write_bool(false);
                }
                Self::I32(value) => output.write_i32(*value),
                Self::I64(value) => output.write_i64(*value),
                Self::OptionalDiscoveryNode(present) => {
                    output.write_bool(*present);
                    if *present {
                        output.write_string("node-a");
                        output.write_string("node-a-id");
                        output.write_string("node-a-ephemeral");
                        output.write_string("node-a.example.test");
                        output.write_string("127.0.0.1");
                        output.write_byte(4);
                        output.write_raw_bytes(&[127, 0, 0, 1]);
                        output.write_string("127.0.0.1");
                        output.write_i32(9300);
                        output.write_bool(false);
                        output.write_vint(1);
                        output.write_string("rack");
                        output.write_string("r1");
                        output.write_vint(1);
                        output.write_string("cluster_manager");
                        output.write_string("m");
                        output.write_bool(false);
                        output.write_vint(2170099);
                    }
                }
                Self::OptionalSearchShardTarget(present) => {
                    output.write_bool(*present);
                    if *present {
                        output.write_bool(true);
                        output.write_string("node-a");
                        output.write_string("logs");
                        output.write_string("uuid-logs");
                        output.write_vint(0);
                        output.write_optional_string(Some("remote-a"));
                    }
                }
                Self::OptionalScriptPosition(present) => {
                    output.write_bool(*present);
                    if *present {
                        output.write_i32(7);
                        output.write_i32(3);
                        output.write_i32(11);
                    }
                }
                Self::OptionalString(value) => output.write_optional_string(*value),
                Self::OptionalTransportAddress(present) => {
                    output.write_bool(*present);
                    if *present {
                        output.write_byte(4);
                        output.write_raw_bytes(&[127, 0, 0, 1]);
                        output.write_string("127.0.0.1");
                        output.write_i32(9300);
                    }
                }
                Self::String(value) => output.write_string(value),
                Self::StringArray(values) => {
                    let values: Vec<String> =
                        values.iter().map(|value| value.to_string()).collect();
                    output.write_string_array(&values);
                }
                Self::VInt(value) => output.write_vint(*value),
            }
        }
    }
}
