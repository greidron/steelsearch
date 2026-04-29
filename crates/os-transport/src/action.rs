use bytes::{Bytes, BytesMut};
use os_core::Version;
use os_engine::{SearchRequest, SearchShardSearchResult, SearchShardTarget};
use os_stream::input::{StreamInput, StreamInputError};
use os_stream::output::StreamOutput;
use os_wire::TransportStatus;
use serde::{de::DeserializeOwned, Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use thiserror::Error;

use crate::frame::encode_message;
use crate::variable_header::{RequestVariableHeader, ResponseVariableHeader};
use crate::TransportMessage;

pub const CLUSTER_STATE_ACTION_NAME: &str = "cluster:monitor/state";
pub const CLUSTER_UPDATE_SETTINGS_ACTION_NAME: &str = "cluster:admin/settings/update";
pub const PENDING_CLUSTER_TASKS_ACTION_NAME: &str = "cluster:monitor/task";
pub const STEELSEARCH_SHARD_SEARCH_ACTION_NAME: &str = "steelsearch:internal/search/shard";
pub const STEELSEARCH_RECOVERY_START_ACTION_NAME: &str = "steelsearch:internal/recovery/start";
pub const STEELSEARCH_RECOVERY_CHUNK_ACTION_NAME: &str = "steelsearch:internal/recovery/chunk";
pub const STEELSEARCH_RECOVERY_TRANSLOG_ACTION_NAME: &str =
    "steelsearch:internal/recovery/translog";
pub const STEELSEARCH_RECOVERY_FINALIZE_ACTION_NAME: &str =
    "steelsearch:internal/recovery/finalize";
pub const STEELSEARCH_RECOVERY_CANCEL_ACTION_NAME: &str = "steelsearch:internal/recovery/cancel";
pub const STEELSEARCH_REPLICA_OPERATION_ACTION_NAME: &str =
    "steelsearch:internal/replication/replica_operation";

const TIME_UNIT_SECONDS: u8 = 3;
const TIME_UNIT_MINUTES: u8 = 4;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceTransportActionSpec {
    pub action_name: &'static str,
    pub action_type: &'static str,
    pub transport_action: &'static str,
    pub request_wire_type: &'static str,
    pub response_wire_type: &'static str,
}

pub const SOURCE_DERIVED_CLUSTER_ACTIONS: &[SourceTransportActionSpec] = &[
    SourceTransportActionSpec {
        action_name: CLUSTER_STATE_ACTION_NAME,
        action_type: "ClusterStateAction",
        transport_action: "TransportClusterStateAction",
        request_wire_type: "ClusterStateRequest",
        response_wire_type: "ClusterStateResponse",
    },
    SourceTransportActionSpec {
        action_name: CLUSTER_UPDATE_SETTINGS_ACTION_NAME,
        action_type: "ClusterUpdateSettingsAction",
        transport_action: "TransportClusterUpdateSettingsAction",
        request_wire_type: "ClusterUpdateSettingsRequest",
        response_wire_type: "ClusterUpdateSettingsResponse",
    },
    SourceTransportActionSpec {
        action_name: PENDING_CLUSTER_TASKS_ACTION_NAME,
        action_type: "PendingClusterTasksAction",
        transport_action: "TransportPendingClusterTasksAction",
        request_wire_type: "PendingClusterTasksRequest",
        response_wire_type: "PendingClusterTasksResponse",
    },
];

pub const STEELSEARCH_SEARCH_ACTIONS: &[SourceTransportActionSpec] = &[SourceTransportActionSpec {
    action_name: STEELSEARCH_SHARD_SEARCH_ACTION_NAME,
    action_type: "SteelsearchShardSearchAction",
    transport_action: "SteelsearchTransportShardSearchAction",
    request_wire_type: "SteelsearchShardSearchRequest",
    response_wire_type: "SteelsearchShardSearchResponse",
}];

pub const STEELSEARCH_RECOVERY_ACTIONS: &[SourceTransportActionSpec] = &[
    SourceTransportActionSpec {
        action_name: STEELSEARCH_RECOVERY_START_ACTION_NAME,
        action_type: "SteelsearchRecoveryStartAction",
        transport_action: "SteelsearchTransportRecoveryStartAction",
        request_wire_type: "SteelsearchRecoveryStartRequest",
        response_wire_type: "SteelsearchRecoveryResponse",
    },
    SourceTransportActionSpec {
        action_name: STEELSEARCH_RECOVERY_CHUNK_ACTION_NAME,
        action_type: "SteelsearchRecoveryChunkAction",
        transport_action: "SteelsearchTransportRecoveryChunkAction",
        request_wire_type: "SteelsearchRecoveryChunkRequest",
        response_wire_type: "SteelsearchRecoveryResponse",
    },
    SourceTransportActionSpec {
        action_name: STEELSEARCH_RECOVERY_TRANSLOG_ACTION_NAME,
        action_type: "SteelsearchRecoveryTranslogAction",
        transport_action: "SteelsearchTransportRecoveryTranslogAction",
        request_wire_type: "SteelsearchRecoveryTranslogRequest",
        response_wire_type: "SteelsearchRecoveryResponse",
    },
    SourceTransportActionSpec {
        action_name: STEELSEARCH_RECOVERY_FINALIZE_ACTION_NAME,
        action_type: "SteelsearchRecoveryFinalizeAction",
        transport_action: "SteelsearchTransportRecoveryFinalizeAction",
        request_wire_type: "SteelsearchRecoveryFinalizeRequest",
        response_wire_type: "SteelsearchRecoveryResponse",
    },
    SourceTransportActionSpec {
        action_name: STEELSEARCH_RECOVERY_CANCEL_ACTION_NAME,
        action_type: "SteelsearchRecoveryCancelAction",
        transport_action: "SteelsearchTransportRecoveryCancelAction",
        request_wire_type: "SteelsearchRecoveryCancelRequest",
        response_wire_type: "SteelsearchRecoveryResponse",
    },
];

pub const STEELSEARCH_REPLICATION_ACTIONS: &[SourceTransportActionSpec] =
    &[SourceTransportActionSpec {
        action_name: STEELSEARCH_REPLICA_OPERATION_ACTION_NAME,
        action_type: "SteelsearchReplicaOperationAction",
        transport_action: "SteelsearchTransportReplicaOperationAction",
        request_wire_type: "SteelsearchReplicaOperationRequest",
        response_wire_type: "SteelsearchReplicaOperationResponse",
    }];

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TimeValueWire {
    pub duration: i64,
    pub time_unit_ordinal: u8,
}

impl TimeValueWire {
    pub const fn seconds(duration: i64) -> Self {
        Self {
            duration,
            time_unit_ordinal: TIME_UNIT_SECONDS,
        }
    }

    pub const fn minutes(duration: i64) -> Self {
        Self {
            duration,
            time_unit_ordinal: TIME_UNIT_MINUTES,
        }
    }

    fn write(&self, output: &mut StreamOutput) {
        output.write_zlong(self.duration);
        output.write_byte(self.time_unit_ordinal);
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        Ok(Self {
            duration: read_zlong(input)?,
            time_unit_ordinal: input.read_byte()?,
        })
    }
}

impl Default for TimeValueWire {
    fn default() -> Self {
        Self::seconds(30)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClusterStateRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub cluster_manager_timeout: TimeValueWire,
    pub local: bool,
    pub routing_table: bool,
    pub nodes: bool,
    pub metadata: bool,
    pub blocks: bool,
    pub customs: bool,
    pub indices: Vec<String>,
    pub indices_options: String,
    pub wait_for_timeout: TimeValueWire,
    pub wait_for_metadata_version: Option<i64>,
}

impl Default for ClusterStateRequestWire {
    fn default() -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            cluster_manager_timeout: TimeValueWire::seconds(30),
            local: false,
            routing_table: true,
            nodes: true,
            metadata: true,
            blocks: true,
            customs: true,
            indices: Vec::new(),
            indices_options: "lenient_expand_open".to_string(),
            wait_for_timeout: TimeValueWire::minutes(1),
            wait_for_metadata_version: None,
        }
    }
}

impl ClusterStateRequestWire {
    pub fn write(&self, output: &mut StreamOutput) {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        self.cluster_manager_timeout.write(output);
        output.write_bool(self.local);
        output.write_bool(self.routing_table);
        output.write_bool(self.nodes);
        output.write_bool(self.metadata);
        output.write_bool(self.blocks);
        output.write_bool(self.customs);
        output.write_string_array(&self.indices);
        output.write_string(&self.indices_options);
        self.wait_for_timeout.write(output);
        write_optional_i64(output, self.wait_for_metadata_version);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let request = Self {
            parent_task_node,
            parent_task_id,
            cluster_manager_timeout: TimeValueWire::read(&mut input)?,
            local: input.read_bool()?,
            routing_table: input.read_bool()?,
            nodes: input.read_bool()?,
            metadata: input.read_bool()?,
            blocks: input.read_bool()?,
            customs: input.read_bool()?,
            indices: input.read_string_array()?,
            indices_options: input.read_string()?,
            wait_for_timeout: TimeValueWire::read(&mut input)?,
            wait_for_metadata_version: read_optional_i64(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct ClusterStateResponseWire {
    pub cluster_name: String,
    pub cluster_uuid: String,
    pub state_uuid: String,
    pub version: i64,
    pub sections: BTreeMap<String, Value>,
}

impl ClusterStateResponseWire {
    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_string(&self.cluster_name);
        output.write_string(&self.cluster_uuid);
        output.write_string(&self.state_uuid);
        output.write_i64(self.version);
        write_json_section_map(output, &self.sections)?;
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self {
            cluster_name: input.read_string()?,
            cluster_uuid: input.read_string()?,
            state_uuid: input.read_string()?,
            version: input.read_i64()?,
            sections: read_json_section_map(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClusterUpdateSettingsRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub cluster_manager_timeout: TimeValueWire,
    pub ack_timeout: TimeValueWire,
    pub transient_settings: BTreeMap<String, String>,
    pub persistent_settings: BTreeMap<String, String>,
}

impl Default for ClusterUpdateSettingsRequestWire {
    fn default() -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            cluster_manager_timeout: TimeValueWire::seconds(30),
            ack_timeout: TimeValueWire::seconds(30),
            transient_settings: BTreeMap::new(),
            persistent_settings: BTreeMap::new(),
        }
    }
}

impl ClusterUpdateSettingsRequestWire {
    pub fn write(&self, output: &mut StreamOutput) {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        self.cluster_manager_timeout.write(output);
        self.ack_timeout.write(output);
        output.write_string_map(&self.transient_settings);
        output.write_string_map(&self.persistent_settings);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let request = Self {
            parent_task_node,
            parent_task_id,
            cluster_manager_timeout: TimeValueWire::read(&mut input)?,
            ack_timeout: TimeValueWire::read(&mut input)?,
            transient_settings: input.read_string_map()?,
            persistent_settings: input.read_string_map()?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AcknowledgedResponseWire {
    pub acknowledged: bool,
}

impl AcknowledgedResponseWire {
    pub fn write(&self, output: &mut StreamOutput) {
        output.write_bool(self.acknowledged);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self {
            acknowledged: input.read_bool()?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PendingClusterTasksRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub cluster_manager_timeout: TimeValueWire,
    pub local: bool,
}

impl Default for PendingClusterTasksRequestWire {
    fn default() -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            cluster_manager_timeout: TimeValueWire::seconds(30),
            local: false,
        }
    }
}

impl PendingClusterTasksRequestWire {
    pub fn write(&self, output: &mut StreamOutput) {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        self.cluster_manager_timeout.write(output);
        output.write_bool(self.local);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let request = Self {
            parent_task_node,
            parent_task_id,
            cluster_manager_timeout: TimeValueWire::read(&mut input)?,
            local: input.read_bool()?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PendingClusterTaskWire {
    pub insert_order: i64,
    pub priority: String,
    pub source: String,
    pub executing: bool,
    pub time_in_queue_millis: i64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PendingClusterTasksResponseWire {
    pub tasks: Vec<PendingClusterTaskWire>,
}

impl PendingClusterTasksResponseWire {
    pub fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.tasks.len() as i32);
        for task in &self.tasks {
            output.write_i64(task.insert_order);
            output.write_string(&task.priority);
            output.write_string(&task.source);
            output.write_bool(task.executing);
            output.write_i64(task.time_in_queue_millis);
        }
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let task_count = read_len(&mut input)?;
        let mut tasks = Vec::with_capacity(task_count);
        for _ in 0..task_count {
            tasks.push(PendingClusterTaskWire {
                insert_order: input.read_i64()?,
                priority: input.read_string()?,
                source: input.read_string()?,
                executing: input.read_bool()?,
                time_in_queue_millis: input.read_i64()?,
            });
        }
        require_no_trailing_bytes(&input)?;
        Ok(Self { tasks })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct SteelsearchShardSearchRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub target: SearchShardTarget,
    pub request: SearchRequest,
}

impl SteelsearchShardSearchRequestWire {
    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        write_json_value(output, &self.target)?;
        write_json_value(output, &self.request)?;
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let request = Self {
            parent_task_node,
            parent_task_id,
            target: read_json_value(&mut input)?,
            request: read_json_value(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct SteelsearchShardSearchResponseWire {
    pub result: SearchShardSearchResult,
}

impl SteelsearchShardSearchResponseWire {
    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_json_value(output, &self.result)
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self {
            result: read_json_value(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }
}

pub fn build_steelsearch_shard_search_request_message(
    request_id: i64,
    version: Version,
    request: &SteelsearchShardSearchRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(STEELSEARCH_SHARD_SEARCH_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_steelsearch_shard_search_request_message(
    message: &TransportMessage,
) -> Result<SteelsearchShardSearchRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != STEELSEARCH_SHARD_SEARCH_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: STEELSEARCH_SHARD_SEARCH_ACTION_NAME,
            actual: header.action,
        });
    }
    SteelsearchShardSearchRequestWire::read(message.body.clone().freeze())
}

pub fn build_steelsearch_shard_search_response_message(
    request_id: i64,
    version: Version,
    response: &SteelsearchShardSearchResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    response.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_steelsearch_shard_search_response_message(
    message: &TransportMessage,
) -> Result<SteelsearchShardSearchResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    SteelsearchShardSearchResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct SteelsearchRecoveryStartRequestWire {
    pub recovery_id: String,
    pub index: String,
    pub shard_id: u32,
    pub source_node: String,
    pub target_node: String,
    pub primary_term: i64,
    pub starting_seq_no: i64,
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct SteelsearchRecoveryChunkRequestWire {
    pub recovery_id: String,
    pub index: String,
    pub shard_id: u32,
    pub file_name: String,
    pub offset: u64,
    pub data: Vec<u8>,
    pub last_chunk: bool,
    pub checksum: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchRecoveryOperationWire {
    pub seq_no: i64,
    pub primary_term: i64,
    pub version: i64,
    pub op_type: String,
    pub id: String,
    pub source: Option<Value>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
pub struct SteelsearchRecoveryTranslogRequestWire {
    pub recovery_id: String,
    pub index: String,
    pub shard_id: u32,
    pub operations: Vec<SteelsearchRecoveryOperationWire>,
    pub max_seq_no: i64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchRecoveryFinalizeRequestWire {
    pub recovery_id: String,
    pub index: String,
    pub shard_id: u32,
    pub allocation_id: String,
    pub global_checkpoint: i64,
    pub max_seq_no: i64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchRecoveryCancelRequestWire {
    pub recovery_id: String,
    pub index: String,
    pub shard_id: u32,
    pub reason: String,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchRecoveryResponseWire {
    pub recovery_id: String,
    pub accepted: bool,
    pub phase: String,
    pub message: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchRetentionLeaseWire {
    pub id: String,
    pub retaining_sequence_number: i64,
    pub source: String,
    pub timestamp_millis: u64,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SteelsearchReplicaOperationKindWire {
    Index,
    Delete,
    Noop,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchReplicaOperationWire {
    pub op_type: SteelsearchReplicaOperationKindWire,
    pub id: String,
    pub source: Option<Value>,
    pub noop_reason: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchReplicaOperationRequestWire {
    pub index: String,
    pub shard_id: u32,
    pub target_node: String,
    pub primary_node: String,
    pub allocation_id: String,
    pub seq_no: i64,
    pub primary_term: u64,
    pub version: u64,
    pub global_checkpoint: i64,
    pub local_checkpoint: i64,
    pub retention_leases: Vec<SteelsearchRetentionLeaseWire>,
    pub operation: SteelsearchReplicaOperationWire,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SteelsearchReplicaOperationResponseWire {
    pub index: String,
    pub shard_id: u32,
    pub target_node: String,
    pub seq_no: i64,
    pub primary_term: u64,
    pub version: u64,
    pub global_checkpoint: i64,
    pub applied: bool,
    pub result: String,
    pub failure: Option<String>,
}

macro_rules! steelsearch_recovery_message_functions {
    (
        $build_request:ident,
        $read_request:ident,
        $action_name:ident,
        $request_ty:ty
    ) => {
        pub fn $build_request(
            request_id: i64,
            version: Version,
            request: &$request_ty,
        ) -> Result<BytesMut, TransportActionWireError> {
            build_steelsearch_json_request_message(request_id, version, $action_name, request)
        }

        pub fn $read_request(
            message: &TransportMessage,
        ) -> Result<$request_ty, TransportActionWireError> {
            read_steelsearch_json_request_message(message, $action_name)
        }
    };
}

steelsearch_recovery_message_functions!(
    build_steelsearch_recovery_start_request_message,
    read_steelsearch_recovery_start_request_message,
    STEELSEARCH_RECOVERY_START_ACTION_NAME,
    SteelsearchRecoveryStartRequestWire
);
steelsearch_recovery_message_functions!(
    build_steelsearch_recovery_chunk_request_message,
    read_steelsearch_recovery_chunk_request_message,
    STEELSEARCH_RECOVERY_CHUNK_ACTION_NAME,
    SteelsearchRecoveryChunkRequestWire
);
steelsearch_recovery_message_functions!(
    build_steelsearch_recovery_translog_request_message,
    read_steelsearch_recovery_translog_request_message,
    STEELSEARCH_RECOVERY_TRANSLOG_ACTION_NAME,
    SteelsearchRecoveryTranslogRequestWire
);
steelsearch_recovery_message_functions!(
    build_steelsearch_recovery_finalize_request_message,
    read_steelsearch_recovery_finalize_request_message,
    STEELSEARCH_RECOVERY_FINALIZE_ACTION_NAME,
    SteelsearchRecoveryFinalizeRequestWire
);
steelsearch_recovery_message_functions!(
    build_steelsearch_recovery_cancel_request_message,
    read_steelsearch_recovery_cancel_request_message,
    STEELSEARCH_RECOVERY_CANCEL_ACTION_NAME,
    SteelsearchRecoveryCancelRequestWire
);

pub fn build_steelsearch_recovery_response_message(
    request_id: i64,
    version: Version,
    response: &SteelsearchRecoveryResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    build_steelsearch_json_response_message(request_id, version, response)
}

pub fn read_steelsearch_recovery_response_message(
    message: &TransportMessage,
) -> Result<SteelsearchRecoveryResponseWire, TransportActionWireError> {
    read_steelsearch_json_response_message(message)
}

pub fn build_steelsearch_replica_operation_request_message(
    request_id: i64,
    version: Version,
    request: &SteelsearchReplicaOperationRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    build_steelsearch_json_request_message(
        request_id,
        version,
        STEELSEARCH_REPLICA_OPERATION_ACTION_NAME,
        request,
    )
}

pub fn read_steelsearch_replica_operation_request_message(
    message: &TransportMessage,
) -> Result<SteelsearchReplicaOperationRequestWire, TransportActionWireError> {
    read_steelsearch_json_request_message(message, STEELSEARCH_REPLICA_OPERATION_ACTION_NAME)
}

pub fn build_steelsearch_replica_operation_response_message(
    request_id: i64,
    version: Version,
    response: &SteelsearchReplicaOperationResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    build_steelsearch_json_response_message(request_id, version, response)
}

pub fn read_steelsearch_replica_operation_response_message(
    message: &TransportMessage,
) -> Result<SteelsearchReplicaOperationResponseWire, TransportActionWireError> {
    read_steelsearch_json_response_message(message)
}

fn build_steelsearch_json_request_message<T: Serialize>(
    request_id: i64,
    version: Version,
    action_name: &'static str,
    request: &T,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    write_json_value(&mut body, request)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(&RequestVariableHeader::new(action_name).to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

fn read_steelsearch_json_request_message<T: DeserializeOwned>(
    message: &TransportMessage,
    expected_action: &'static str,
) -> Result<T, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != expected_action {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: expected_action,
            actual: header.action,
        });
    }
    let mut input = StreamInput::new(message.body.clone().freeze());
    let request = read_json_value(&mut input)?;
    require_no_trailing_bytes(&input)?;
    Ok(request)
}

fn build_steelsearch_json_response_message<T: Serialize>(
    request_id: i64,
    version: Version,
    response: &T,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    write_json_value(&mut body, response)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

fn read_steelsearch_json_response_message<T: DeserializeOwned>(
    message: &TransportMessage,
) -> Result<T, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    let mut input = StreamInput::new(message.body.clone().freeze());
    let response = read_json_value(&mut input)?;
    require_no_trailing_bytes(&input)?;
    Ok(response)
}

#[derive(Debug, Error)]
pub enum TransportActionWireError {
    #[error("stream decode failed")]
    Stream(#[from] StreamInputError),
    #[error("json section encode failed")]
    JsonEncode(#[source] serde_json::Error),
    #[error("json section decode failed")]
    JsonDecode(#[source] serde_json::Error),
    #[error("trailing bytes after action body: {0}")]
    TrailingBytes(usize),
    #[error("unexpected transport action: expected {expected}, got {actual}")]
    UnexpectedAction {
        expected: &'static str,
        actual: String,
    },
    #[error("unexpected transport message status: expected {expected}, got bits {actual}")]
    UnexpectedMessageStatus { expected: &'static str, actual: u8 },
}

fn write_json_value<T: Serialize>(
    output: &mut StreamOutput,
    value: &T,
) -> Result<(), TransportActionWireError> {
    let encoded = serde_json::to_vec(value).map_err(TransportActionWireError::JsonEncode)?;
    output.write_bytes_reference(&encoded);
    Ok(())
}

fn read_json_value<T: DeserializeOwned>(
    input: &mut StreamInput,
) -> Result<T, TransportActionWireError> {
    let value = input.read_bytes_reference()?;
    serde_json::from_slice(&value).map_err(TransportActionWireError::JsonDecode)
}

fn write_parent_task_id(output: &mut StreamOutput, node: &str, id: Option<i64>) {
    output.write_string(node);
    if !node.is_empty() {
        output.write_i64(id.unwrap_or(-1));
    }
}

fn read_parent_task_id(
    input: &mut StreamInput,
) -> Result<(String, Option<i64>), TransportActionWireError> {
    let node = input.read_string()?;
    let id = if node.is_empty() {
        None
    } else {
        Some(input.read_i64()?)
    };
    Ok((node, id))
}

fn write_optional_i64(output: &mut StreamOutput, value: Option<i64>) {
    if let Some(value) = value {
        output.write_bool(true);
        output.write_i64(value);
    } else {
        output.write_bool(false);
    }
}

fn read_optional_i64(input: &mut StreamInput) -> Result<Option<i64>, TransportActionWireError> {
    if input.read_bool()? {
        Ok(Some(input.read_i64()?))
    } else {
        Ok(None)
    }
}

fn write_json_section_map(
    output: &mut StreamOutput,
    sections: &BTreeMap<String, Value>,
) -> Result<(), TransportActionWireError> {
    output.write_vint(sections.len() as i32);
    for (key, value) in sections {
        output.write_string(key);
        let encoded = serde_json::to_vec(value).map_err(TransportActionWireError::JsonEncode)?;
        output.write_bytes_reference(&encoded);
    }
    Ok(())
}

fn read_json_section_map(
    input: &mut StreamInput,
) -> Result<BTreeMap<String, Value>, TransportActionWireError> {
    let len = read_len(input)?;
    let mut sections = BTreeMap::new();
    for _ in 0..len {
        let key = input.read_string()?;
        let value = input.read_bytes_reference()?;
        let value = serde_json::from_slice(&value).map_err(TransportActionWireError::JsonDecode)?;
        sections.insert(key, value);
    }
    Ok(sections)
}

fn read_len(input: &mut StreamInput) -> Result<usize, TransportActionWireError> {
    let len = input.read_vint()?;
    if len < 0 {
        return Err(StreamInputError::NegativeLength(len).into());
    }
    Ok(len as usize)
}

fn read_zlong(input: &mut StreamInput) -> Result<i64, StreamInputError> {
    let value = input.read_vlong()? as u64;
    Ok(((value >> 1) as i64) ^ (-((value & 1) as i64)))
}

fn require_no_trailing_bytes(input: &StreamInput) -> Result<(), TransportActionWireError> {
    let remaining = input.remaining();
    if remaining == 0 {
        Ok(())
    } else {
        Err(TransportActionWireError::TrailingBytes(remaining))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::frame::{decode_frame, DecodedFrame};
    use os_core::OPENSEARCH_3_7_0_TRANSPORT;
    use os_engine::{
        DocumentMetadata, SearchFetchSubphase, SearchFetchSubphaseResult, SearchHit, SearchPhase,
        SearchPhaseResult, SearchResponse, SortSpec,
    };
    use serde_json::json;

    #[test]
    fn source_derived_cluster_actions_have_opensearch_names_and_wire_types() {
        assert_eq!(
            SOURCE_DERIVED_CLUSTER_ACTIONS,
            &[
                SourceTransportActionSpec {
                    action_name: "cluster:monitor/state",
                    action_type: "ClusterStateAction",
                    transport_action: "TransportClusterStateAction",
                    request_wire_type: "ClusterStateRequest",
                    response_wire_type: "ClusterStateResponse",
                },
                SourceTransportActionSpec {
                    action_name: "cluster:admin/settings/update",
                    action_type: "ClusterUpdateSettingsAction",
                    transport_action: "TransportClusterUpdateSettingsAction",
                    request_wire_type: "ClusterUpdateSettingsRequest",
                    response_wire_type: "ClusterUpdateSettingsResponse",
                },
                SourceTransportActionSpec {
                    action_name: "cluster:monitor/task",
                    action_type: "PendingClusterTasksAction",
                    transport_action: "TransportPendingClusterTasksAction",
                    request_wire_type: "PendingClusterTasksRequest",
                    response_wire_type: "PendingClusterTasksResponse",
                },
            ]
        );
    }

    #[test]
    fn steelsearch_search_actions_have_internal_wire_types() {
        assert_eq!(
            STEELSEARCH_SEARCH_ACTIONS,
            &[SourceTransportActionSpec {
                action_name: "steelsearch:internal/search/shard",
                action_type: "SteelsearchShardSearchAction",
                transport_action: "SteelsearchTransportShardSearchAction",
                request_wire_type: "SteelsearchShardSearchRequest",
                response_wire_type: "SteelsearchShardSearchResponse",
            }]
        );
    }

    #[test]
    fn steelsearch_recovery_actions_have_internal_wire_types() {
        assert_eq!(STEELSEARCH_RECOVERY_ACTIONS.len(), 5);
        assert_eq!(
            STEELSEARCH_RECOVERY_ACTIONS[0],
            SourceTransportActionSpec {
                action_name: "steelsearch:internal/recovery/start",
                action_type: "SteelsearchRecoveryStartAction",
                transport_action: "SteelsearchTransportRecoveryStartAction",
                request_wire_type: "SteelsearchRecoveryStartRequest",
                response_wire_type: "SteelsearchRecoveryResponse",
            }
        );
        assert_eq!(
            STEELSEARCH_RECOVERY_ACTIONS[4].action_name,
            "steelsearch:internal/recovery/cancel"
        );
    }

    #[test]
    fn steelsearch_replication_action_has_internal_wire_types() {
        assert_eq!(
            STEELSEARCH_REPLICATION_ACTIONS,
            &[SourceTransportActionSpec {
                action_name: "steelsearch:internal/replication/replica_operation",
                action_type: "SteelsearchReplicaOperationAction",
                transport_action: "SteelsearchTransportReplicaOperationAction",
                request_wire_type: "SteelsearchReplicaOperationRequest",
                response_wire_type: "SteelsearchReplicaOperationResponse",
            }]
        );
    }

    #[test]
    fn steelsearch_shard_search_wire_round_trips() {
        let target = SearchShardTarget {
            index: "logs-000001".to_string(),
            shard: 0,
            node: "node-a".to_string(),
        };
        let request = SteelsearchShardSearchRequestWire {
            parent_task_node: "coordinator".to_string(),
            parent_task_id: Some(17),
            target: target.clone(),
            request: SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: json!({ "match_all": {} }),
                aggregations: json!({}),
                sort: Vec::<SortSpec>::new(),
                from: 0,
                size: 10,
            },
        };
        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        assert_eq!(
            SteelsearchShardSearchRequestWire::read(output.freeze()).unwrap(),
            request
        );

        let result = SearchShardSearchResult::success(
            target,
            SearchResponse::new(
                1,
                vec![SearchHit {
                    index: "logs-000001".to_string(),
                    metadata: DocumentMetadata {
                        id: "1".to_string(),
                        version: 1,
                        seq_no: 0,
                        primary_term: 1,
                    },
                    score: 1.0,
                    source: json!({ "message": "hello" }),
                }],
                json!({}),
            )
            .with_phase_results(vec![SearchPhaseResult::completed(
                SearchPhase::Query,
                "query shard",
            )])
            .with_fetch_subphases(vec![SearchFetchSubphaseResult::completed(
                SearchFetchSubphase::Source,
                "load source",
            )]),
        );
        let response = SteelsearchShardSearchResponseWire { result };
        let mut output = StreamOutput::new();
        response.write(&mut output).unwrap();
        assert_eq!(
            SteelsearchShardSearchResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }

    #[test]
    fn steelsearch_shard_search_transport_messages_bind_action_frames() {
        let target = SearchShardTarget {
            index: "logs-000001".to_string(),
            shard: 0,
            node: "node-a".to_string(),
        };
        let request = SteelsearchShardSearchRequestWire {
            parent_task_node: "coordinator".to_string(),
            parent_task_id: Some(17),
            target: target.clone(),
            request: SearchRequest {
                indices: vec!["logs-000001".to_string()],
                query: json!({ "match_all": {} }),
                aggregations: json!({}),
                sort: Vec::<SortSpec>::new(),
                from: 0,
                size: 10,
            },
        };
        let mut frame = build_steelsearch_shard_search_request_message(
            99,
            OPENSEARCH_3_7_0_TRANSPORT,
            &request,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected shard search request message");
        };

        assert_eq!(message.request_id, 99);
        assert!(message.status.is_request());
        assert_eq!(
            read_steelsearch_shard_search_request_message(&message).unwrap(),
            request
        );

        let response = SteelsearchShardSearchResponseWire {
            result: SearchShardSearchResult::failure(target, "remote failed", 503),
        };
        let mut frame = build_steelsearch_shard_search_response_message(
            99,
            OPENSEARCH_3_7_0_TRANSPORT,
            &response,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected shard search response message");
        };

        assert_eq!(message.request_id, 99);
        assert!(message.status.is_response());
        assert_eq!(
            read_steelsearch_shard_search_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn steelsearch_recovery_wire_requests_round_trip_json_payloads() {
        let start = SteelsearchRecoveryStartRequestWire {
            recovery_id: "recovery-1".to_string(),
            index: "logs-000001".to_string(),
            shard_id: 0,
            source_node: "node-a".to_string(),
            target_node: "node-b".to_string(),
            primary_term: 3,
            starting_seq_no: 42,
            metadata: BTreeMap::from([("store_uuid".to_string(), json!("store-a"))]),
        };
        let chunk = SteelsearchRecoveryChunkRequestWire {
            recovery_id: "recovery-1".to_string(),
            index: "logs-000001".to_string(),
            shard_id: 0,
            file_name: "segment_1".to_string(),
            offset: 128,
            data: vec![1, 2, 3, 4],
            last_chunk: true,
            checksum: Some("crc32:abcd".to_string()),
        };
        let translog = SteelsearchRecoveryTranslogRequestWire {
            recovery_id: "recovery-1".to_string(),
            index: "logs-000001".to_string(),
            shard_id: 0,
            operations: vec![SteelsearchRecoveryOperationWire {
                seq_no: 43,
                primary_term: 3,
                version: 7,
                op_type: "index".to_string(),
                id: "1".to_string(),
                source: Some(json!({ "message": "replicate me" })),
            }],
            max_seq_no: 43,
        };
        let finalize = SteelsearchRecoveryFinalizeRequestWire {
            recovery_id: "recovery-1".to_string(),
            index: "logs-000001".to_string(),
            shard_id: 0,
            allocation_id: "alloc-b".to_string(),
            global_checkpoint: 43,
            max_seq_no: 43,
        };
        let cancel = SteelsearchRecoveryCancelRequestWire {
            recovery_id: "recovery-1".to_string(),
            index: "logs-000001".to_string(),
            shard_id: 0,
            reason: "target left".to_string(),
        };

        assert_recovery_request_round_trip(
            build_steelsearch_recovery_start_request_message,
            read_steelsearch_recovery_start_request_message,
            start,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_chunk_request_message,
            read_steelsearch_recovery_chunk_request_message,
            chunk,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_translog_request_message,
            read_steelsearch_recovery_translog_request_message,
            translog,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_finalize_request_message,
            read_steelsearch_recovery_finalize_request_message,
            finalize,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_cancel_request_message,
            read_steelsearch_recovery_cancel_request_message,
            cancel,
        );
    }

    fn assert_recovery_request_round_trip<T>(
        build: fn(i64, Version, &T) -> Result<BytesMut, TransportActionWireError>,
        read: fn(&TransportMessage) -> Result<T, TransportActionWireError>,
        request: T,
    ) where
        T: std::fmt::Debug + PartialEq,
    {
        let mut frame = build(77, OPENSEARCH_3_7_0_TRANSPORT, &request).unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected recovery request message");
        };
        assert_eq!(message.request_id, 77);
        assert!(message.status.is_request());
        assert_eq!(read(&message).unwrap(), request);
    }

    #[test]
    fn steelsearch_recovery_response_binds_response_frame() {
        let response = SteelsearchRecoveryResponseWire {
            recovery_id: "recovery-1".to_string(),
            accepted: true,
            phase: "finalized".to_string(),
            message: None,
        };
        let mut frame =
            build_steelsearch_recovery_response_message(88, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected recovery response message");
        };

        assert_eq!(message.request_id, 88);
        assert!(message.status.is_response());
        assert_eq!(
            read_steelsearch_recovery_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn steelsearch_replica_operation_request_binds_primary_assigned_metadata() {
        let request = SteelsearchReplicaOperationRequestWire {
            index: "logs-000001".to_string(),
            shard_id: 0,
            target_node: "node-b".to_string(),
            primary_node: "node-a".to_string(),
            allocation_id: "alloc-b".to_string(),
            seq_no: 43,
            primary_term: 3,
            version: 7,
            global_checkpoint: 42,
            local_checkpoint: 42,
            retention_leases: vec![SteelsearchRetentionLeaseWire {
                id: "node-b".to_string(),
                retaining_sequence_number: 40,
                source: "replica".to_string(),
                timestamp_millis: 1_700_000_000_000,
            }],
            operation: SteelsearchReplicaOperationWire {
                op_type: SteelsearchReplicaOperationKindWire::Index,
                id: "1".to_string(),
                source: Some(json!({ "message": "replicate me" })),
                noop_reason: None,
            },
        };

        let mut frame = build_steelsearch_replica_operation_request_message(
            90,
            OPENSEARCH_3_7_0_TRANSPORT,
            &request,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected replica operation request message");
        };

        assert_eq!(message.request_id, 90);
        assert!(message.status.is_request());
        assert_eq!(
            read_steelsearch_replica_operation_request_message(&message).unwrap(),
            request
        );
    }

    #[test]
    fn steelsearch_replica_delete_operation_round_trips_without_source() {
        let request = SteelsearchReplicaOperationRequestWire {
            index: "logs-000001".to_string(),
            shard_id: 0,
            target_node: "node-b".to_string(),
            primary_node: "node-a".to_string(),
            allocation_id: "alloc-b".to_string(),
            seq_no: 44,
            primary_term: 3,
            version: 8,
            global_checkpoint: 43,
            local_checkpoint: 43,
            retention_leases: Vec::new(),
            operation: SteelsearchReplicaOperationWire {
                op_type: SteelsearchReplicaOperationKindWire::Delete,
                id: "1".to_string(),
                source: None,
                noop_reason: None,
            },
        };

        let mut frame = build_steelsearch_replica_operation_request_message(
            91,
            OPENSEARCH_3_7_0_TRANSPORT,
            &request,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected replica delete operation request message");
        };

        assert_eq!(
            read_steelsearch_replica_operation_request_message(&message).unwrap(),
            request
        );
    }

    #[test]
    fn steelsearch_replica_operation_response_binds_replication_metadata() {
        let response = SteelsearchReplicaOperationResponseWire {
            index: "logs-000001".to_string(),
            shard_id: 0,
            target_node: "node-b".to_string(),
            seq_no: 43,
            primary_term: 3,
            version: 7,
            global_checkpoint: 43,
            applied: true,
            result: "updated".to_string(),
            failure: None,
        };
        let mut frame = build_steelsearch_replica_operation_response_message(
            92,
            OPENSEARCH_3_7_0_TRANSPORT,
            &response,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected replica operation response message");
        };

        assert_eq!(message.request_id, 92);
        assert!(message.status.is_response());
        assert_eq!(
            read_steelsearch_replica_operation_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn cluster_state_request_wire_round_trips() {
        let request = ClusterStateRequestWire {
            local: true,
            metadata: false,
            indices: vec!["logs-*".to_string()],
            wait_for_metadata_version: Some(42),
            ..ClusterStateRequestWire::default()
        };
        let mut output = StreamOutput::new();
        request.write(&mut output);

        assert_eq!(
            ClusterStateRequestWire::read(output.freeze()).unwrap(),
            request
        );
    }

    #[test]
    fn cluster_state_response_wire_round_trips_json_sections() {
        let response = ClusterStateResponseWire {
            cluster_name: "steelsearch".to_string(),
            cluster_uuid: "uuid-1".to_string(),
            state_uuid: "state-1".to_string(),
            version: 7,
            sections: BTreeMap::from([
                ("nodes".to_string(), json!({"node-a": {"name": "node-a"}})),
                ("metadata".to_string(), json!({"indices": {}})),
            ]),
        };
        let mut output = StreamOutput::new();
        response.write(&mut output).unwrap();

        assert_eq!(
            ClusterStateResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }

    #[test]
    fn update_settings_request_and_ack_response_wire_round_trip() {
        let request = ClusterUpdateSettingsRequestWire {
            transient_settings: BTreeMap::from([(
                "cluster.routing.allocation.enable".to_string(),
                "all".to_string(),
            )]),
            persistent_settings: BTreeMap::from([(
                "cluster.max_shards_per_node".to_string(),
                "1000".to_string(),
            )]),
            ..ClusterUpdateSettingsRequestWire::default()
        };
        let mut output = StreamOutput::new();
        request.write(&mut output);
        assert_eq!(
            ClusterUpdateSettingsRequestWire::read(output.freeze()).unwrap(),
            request
        );

        let response = AcknowledgedResponseWire { acknowledged: true };
        let mut output = StreamOutput::new();
        response.write(&mut output);
        assert_eq!(
            AcknowledgedResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }

    #[test]
    fn pending_cluster_tasks_wire_round_trips() {
        let request = PendingClusterTasksRequestWire {
            local: true,
            ..PendingClusterTasksRequestWire::default()
        };
        let mut output = StreamOutput::new();
        request.write(&mut output);
        assert_eq!(
            PendingClusterTasksRequestWire::read(output.freeze()).unwrap(),
            request
        );

        let response = PendingClusterTasksResponseWire {
            tasks: vec![PendingClusterTaskWire {
                insert_order: 1,
                priority: "URGENT".to_string(),
                source: "create-index [logs]".to_string(),
                executing: false,
                time_in_queue_millis: 15,
            }],
        };
        let mut output = StreamOutput::new();
        response.write(&mut output);
        assert_eq!(
            PendingClusterTasksResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }
}
