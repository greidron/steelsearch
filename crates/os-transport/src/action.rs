use bytes::{Bytes, BytesMut};
use os_core::Version;
use os_engine::{
    BulkWriteItemResponse, BulkWriteOperation, BulkWriteRequest, BulkWriteResponse,
    DeleteDocumentRequest, DocumentMetadata, GetDocumentRequest, GetDocumentResponse,
    IndexDocumentRequest, IndexDocumentResponse, RefreshRequest, RefreshResponse, SearchHit,
    SearchRequest, SearchShardSearchResult, SearchShardTarget, UpdateDocumentRequest,
    WriteOperationKind, WriteResult,
};
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
pub const OPENSEARCH_SEARCH_ACTION_NAME: &str = "indices:data/read/search";
pub const OPENSEARCH_MULTI_SEARCH_ACTION_NAME: &str = "indices:data/read/msearch";
pub const OPENSEARCH_GET_ACTION_NAME: &str = "indices:data/read/get";
pub const OPENSEARCH_MULTI_GET_ACTION_NAME: &str = "indices:data/read/mget";
pub const OPENSEARCH_BULK_ACTION_NAME: &str = "indices:data/write/bulk";
pub const OPENSEARCH_INDEX_ACTION_NAME: &str = "indices:data/write/index";
pub const OPENSEARCH_UPDATE_ACTION_NAME: &str = "indices:data/write/update";
pub const OPENSEARCH_DELETE_ACTION_NAME: &str = "indices:data/write/delete";
pub const OPENSEARCH_REFRESH_ACTION_NAME: &str = "indices:admin/refresh";
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OpenSearchPriorityTransportActionSpec {
    pub action_name: &'static str,
    pub action_type: &'static str,
    pub transport_action: &'static str,
    pub request_wire_type: &'static str,
    pub response_wire_type: &'static str,
    pub adapter_stage: &'static str,
    pub next_step: &'static str,
}

pub const OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS: &[OpenSearchPriorityTransportActionSpec] = &[
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_SEARCH_ACTION_NAME,
        action_type: "SearchAction",
        transport_action: "TransportSearchAction",
        request_wire_type: "SearchRequest",
        response_wire_type: "SearchResponse",
        adapter_stage: "search-read",
        next_step: "register request/response codec and route to the Rust search executor",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_MULTI_SEARCH_ACTION_NAME,
        action_type: "MultiSearchAction",
        transport_action: "TransportMultiSearchAction",
        request_wire_type: "MultiSearchRequest",
        response_wire_type: "MultiSearchResponse",
        adapter_stage: "search-read",
        next_step: "decode batched search requests and aggregate Rust search responses",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_GET_ACTION_NAME,
        action_type: "GetAction",
        transport_action: "TransportGetAction",
        request_wire_type: "GetRequest",
        response_wire_type: "GetResponse",
        adapter_stage: "document-read",
        next_step: "map document get requests onto Rust point lookup semantics",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_MULTI_GET_ACTION_NAME,
        action_type: "MultiGetAction",
        transport_action: "TransportMultiGetAction",
        request_wire_type: "MultiGetRequest",
        response_wire_type: "MultiGetResponse",
        adapter_stage: "document-read",
        next_step: "decode batched document gets and preserve per-item response status",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_BULK_ACTION_NAME,
        action_type: "BulkAction",
        transport_action: "TransportBulkAction",
        request_wire_type: "BulkRequest",
        response_wire_type: "BulkResponse",
        adapter_stage: "write-replication",
        next_step: "decode bulk items and route index/update/delete operations through Rust writes",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_INDEX_ACTION_NAME,
        action_type: "IndexAction",
        transport_action: "TransportIndexAction",
        request_wire_type: "IndexRequest",
        response_wire_type: "IndexResponse",
        adapter_stage: "write-replication",
        next_step: "map single-document index requests onto Rust write semantics",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_UPDATE_ACTION_NAME,
        action_type: "UpdateAction",
        transport_action: "TransportUpdateAction",
        request_wire_type: "UpdateRequest",
        response_wire_type: "UpdateResponse",
        adapter_stage: "write-replication",
        next_step:
            "resolve update scripts/docs into Rust write operations with matching response status",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_DELETE_ACTION_NAME,
        action_type: "DeleteAction",
        transport_action: "TransportDeleteAction",
        request_wire_type: "DeleteRequest",
        response_wire_type: "DeleteResponse",
        adapter_stage: "write-replication",
        next_step: "map single-document delete requests onto Rust tombstone/write semantics",
    },
    OpenSearchPriorityTransportActionSpec {
        action_name: OPENSEARCH_REFRESH_ACTION_NAME,
        action_type: "RefreshAction",
        transport_action: "TransportRefreshAction",
        request_wire_type: "RefreshRequest",
        response_wire_type: "RefreshResponse",
        adapter_stage: "refresh-visibility",
        next_step: "map refresh requests onto Rust visibility barriers and shard status reporting",
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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OpenSearchTransportActionDisposition {
    Implemented,
    Rejected,
    Missing,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchTransportDispatchDecision {
    pub action_name: String,
    pub disposition: OpenSearchTransportActionDisposition,
    pub reason: &'static str,
}

pub fn classify_opensearch_transport_action(
    action_name: &str,
) -> OpenSearchTransportDispatchDecision {
    const PRIORITY_TARGET_REASON: &str =
        "priority transport adapter target; request/response codec and semantic adapter are not registered yet";

    match action_name {
        CLUSTER_STATE_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "cluster-state observer transport adapter is available",
        },
        PENDING_CLUSTER_TASKS_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "pending-tasks observer transport adapter is available",
        },
        CLUSTER_UPDATE_SETTINGS_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Rejected,
            reason: "cluster settings mutation is not admitted through transport",
        },
        OPENSEARCH_GET_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "get transport adapter is available for the default single-document subset",
        },
        OPENSEARCH_MULTI_GET_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "multi-get transport adapter is available for the default document subset",
        },
        OPENSEARCH_BULK_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "bulk transport adapter is available for the bounded index/delete subset",
        },
        OPENSEARCH_INDEX_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "index transport adapter is available for the default single-document subset",
        },
        OPENSEARCH_UPDATE_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "update transport adapter is available for the default doc-update subset",
        },
        OPENSEARCH_DELETE_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "delete transport adapter is available for the default single-document subset",
        },
        OPENSEARCH_REFRESH_ACTION_NAME => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Implemented,
            reason: "refresh transport adapter is available",
        },
        _ if OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS
            .iter()
            .any(|spec| spec.action_name == action_name) =>
        {
            OpenSearchTransportDispatchDecision {
                action_name: action_name.to_string(),
                disposition: OpenSearchTransportActionDisposition::Missing,
                reason: PRIORITY_TARGET_REASON,
            }
        }
        _ => OpenSearchTransportDispatchDecision {
            action_name: action_name.to_string(),
            disposition: OpenSearchTransportActionDisposition::Missing,
            reason: "no OpenSearch transport action adapter is registered",
        },
    }
}

pub fn classify_opensearch_transport_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchTransportDispatchDecision, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    Ok(classify_opensearch_transport_action(&header.action))
}

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

const OPENSEARCH_VERSION_TYPE_INTERNAL: u8 = 0;
const OPENSEARCH_MATCH_ANY_VERSION: i64 = -3;
const OPENSEARCH_UNASSIGNED_SEQ_NO: i64 = -2;
const OPENSEARCH_UNASSIGNED_PRIMARY_TERM: i64 = 0;
const OPENSEARCH_NOT_FOUND_VERSION: i64 = -1;
const OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT: i32 = -2;
const OPENSEARCH_REFRESH_POLICY_NONE: u8 = 0;
const OPENSEARCH_DOC_WRITE_REQUEST_INDEX: u8 = 0;
const OPENSEARCH_DOC_WRITE_REQUEST_DELETE: u8 = 1;
const OPENSEARCH_DOC_WRITE_REQUEST_UPDATE: u8 = 2;
const OPENSEARCH_DOC_WRITE_OP_TYPE_INDEX: u8 = 0;
const OPENSEARCH_DOC_WRITE_OP_TYPE_DELETE: u8 = 3;
const OPENSEARCH_UNSET_AUTO_GENERATED_TIMESTAMP: i64 = -1;
const OPENSEARCH_JSON_MEDIA_TYPE: &str = "application/json";
const OPENSEARCH_DOC_WRITE_RESULT_CREATED: u8 = 0;
const OPENSEARCH_DOC_WRITE_RESULT_UPDATED: u8 = 1;
const OPENSEARCH_DOC_WRITE_RESULT_DELETED: u8 = 2;
const OPENSEARCH_DOC_WRITE_RESULT_NOT_FOUND: u8 = 3;
const OPENSEARCH_DOC_WRITE_RESULT_NOOP: u8 = 4;
const OPENSEARCH_BULK_RESPONSE_INDEX: u8 = 0;
const OPENSEARCH_BULK_RESPONSE_DELETE: u8 = 1;
const OPENSEARCH_BULK_RESPONSE_NONE: u8 = 2;
const OPENSEARCH_BULK_RESPONSE_UPDATE: u8 = 3;
const OPENSEARCH_NO_INGEST_TOOK: i64 = -1;
const OPENSEARCH_UNKNOWN_INDEX_UUID: &str = "_na_";

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchGetRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub internal_shard_id_present: bool,
    pub index: Option<String>,
    pub id: String,
    pub routing: Option<String>,
    pub preference: Option<String>,
    pub refresh: bool,
    pub stored_fields: Option<Vec<String>>,
    pub realtime: bool,
    pub version_type: u8,
    pub version: i64,
    pub fetch_source_context_present: bool,
}

impl OpenSearchGetRequestWire {
    pub fn new(index: String, id: String) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            internal_shard_id_present: false,
            index: Some(index),
            id,
            routing: None,
            preference: None,
            refresh: false,
            stored_fields: None,
            realtime: true,
            version_type: OPENSEARCH_VERSION_TYPE_INTERNAL,
            version: OPENSEARCH_MATCH_ANY_VERSION,
            fetch_source_context_present: false,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        if self.internal_shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request internal shard id",
                reason: "explicit shard ids are not encoded by the get adapter yet",
            });
        }
        output.write_bool(false);
        output.write_optional_string(self.index.as_deref());
        output.write_string(&self.id);
        output.write_optional_string(self.routing.as_deref());
        output.write_optional_string(self.preference.as_deref());
        output.write_bool(self.refresh);
        write_optional_string_array(output, self.stored_fields.as_deref());
        output.write_bool(self.realtime);
        output.write_byte(self.version_type);
        output.write_i64(self.version);
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request fetch source context",
                reason: "fetch source context encoding is not implemented by the get adapter yet",
            });
        }
        output.write_bool(false);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let internal_shard_id_present = input.read_bool()?;
        if internal_shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request internal shard id",
                reason: "explicit shard ids are not decoded by the get adapter yet",
            });
        }
        let request = Self {
            parent_task_node,
            parent_task_id,
            internal_shard_id_present,
            index: input.read_optional_string()?,
            id: input.read_string()?,
            routing: input.read_optional_string()?,
            preference: input.read_optional_string()?,
            refresh: input.read_bool()?,
            stored_fields: read_optional_string_array(&mut input)?,
            realtime: input.read_bool()?,
            version_type: input.read_byte()?,
            version: input.read_i64()?,
            fetch_source_context_present: input.read_bool()?,
        };
        if request.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request fetch source context",
                reason: "fetch source context decoding is not implemented by the get adapter yet",
            });
        }
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    pub fn to_engine_request(&self) -> Result<GetDocumentRequest, TransportActionWireError> {
        if self.internal_shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request internal shard id",
                reason: "explicit shard ids cannot be mapped onto the current get engine request",
            });
        }
        if self.routing.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request routing",
                reason: "routing cannot be mapped onto the current get engine request",
            });
        }
        if self.preference.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request preference",
                reason: "preference cannot be mapped onto the current get engine request",
            });
        }
        if self.refresh {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request refresh",
                reason: "pre-get refresh is not part of the current get adapter subset",
            });
        }
        if self.stored_fields.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request stored fields",
                reason: "stored fields cannot be mapped onto the current get engine request",
            });
        }
        if !self.realtime {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request realtime flag",
                reason: "non-realtime get cannot be mapped onto the current get engine request",
            });
        }
        if self.version_type != OPENSEARCH_VERSION_TYPE_INTERNAL
            || self.version != OPENSEARCH_MATCH_ANY_VERSION
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request versioning",
                reason: "versioned get cannot be mapped onto the current get engine request",
            });
        }
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "get request fetch source context",
                reason:
                    "fetch source filtering cannot be mapped onto the current get engine request",
            });
        }
        Ok(GetDocumentRequest {
            index: self
                .index
                .clone()
                .ok_or(TransportActionWireError::MissingRequiredField { field: "index" })?,
            id: self.id.clone(),
        })
    }
}

impl From<GetDocumentRequest> for OpenSearchGetRequestWire {
    fn from(request: GetDocumentRequest) -> Self {
        Self::new(request.index, request.id)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchGetResponseWire {
    pub index: String,
    pub id: String,
    pub seq_no: i64,
    pub primary_term: i64,
    pub version: i64,
    pub found: bool,
    pub source: Option<Value>,
}

impl OpenSearchGetResponseWire {
    pub fn found(index: String, metadata: DocumentMetadata, source: Value) -> Self {
        Self {
            index,
            id: metadata.id,
            seq_no: metadata.seq_no,
            primary_term: metadata.primary_term as i64,
            version: metadata.version as i64,
            found: true,
            source: Some(source),
        }
    }

    pub fn not_found(index: String, id: String) -> Self {
        Self {
            index,
            id,
            seq_no: OPENSEARCH_UNASSIGNED_SEQ_NO,
            primary_term: OPENSEARCH_UNASSIGNED_PRIMARY_TERM,
            version: OPENSEARCH_NOT_FOUND_VERSION,
            found: false,
            source: None,
        }
    }

    pub fn from_engine_response(
        index: String,
        id: String,
        response: Option<GetDocumentResponse>,
    ) -> Self {
        match response {
            Some(response) => {
                OpenSearchGetResponseWire::found(response.index, response.metadata, response.source)
            }
            None => OpenSearchGetResponseWire::not_found(index, id),
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_string(&self.index);
        output.write_string(&self.id);
        output.write_zlong(self.seq_no);
        output.write_vlong(self.primary_term);
        output.write_i64(self.version);
        output.write_bool(self.found);
        if self.found {
            let source = self
                .source
                .as_ref()
                .ok_or(TransportActionWireError::MissingRequiredField { field: "source" })?;
            write_json_bytes_reference(output, source)?;
            output.write_vint(0);
            output.write_vint(0);
        }
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self::read_from_input(&mut input)?;
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }

    fn read_from_input(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let index = input.read_string()?;
        let id = input.read_string()?;
        let seq_no = read_zlong(input)?;
        let primary_term = input.read_vlong()?;
        let version = input.read_i64()?;
        let found = input.read_bool()?;
        let source = if found {
            let source = read_json_bytes_reference(input)?;
            let document_field_count = input.read_vint()?;
            if document_field_count != 0 {
                return Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "get response document fields",
                    reason: "document fields are not decoded by the get adapter yet",
                });
            }
            let meta_field_count = input.read_vint()?;
            if meta_field_count != 0 {
                return Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "get response metadata fields",
                    reason: "metadata fields are not decoded by the get adapter yet",
                });
            }
            Some(source)
        } else {
            None
        };
        Ok(Self {
            index,
            id,
            seq_no,
            primary_term,
            version,
            found,
            source,
        })
    }

    pub fn into_engine_response(self) -> Option<GetDocumentResponse> {
        if !self.found {
            return None;
        }
        Some(GetDocumentResponse {
            index: self.index,
            metadata: DocumentMetadata {
                id: self.id,
                version: self.version as u64,
                seq_no: self.seq_no,
                primary_term: self.primary_term as u64,
            },
            source: self.source.unwrap_or(Value::Null),
            found: true,
        })
    }
}

pub fn build_opensearch_get_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchGetRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_GET_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_get_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchGetRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_GET_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_GET_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchGetRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_get_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchGetResponseWire,
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

pub fn read_opensearch_get_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchGetResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchGetResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchMultiGetItemRequestWire {
    pub index: String,
    pub id: String,
    pub routing: Option<String>,
    pub stored_fields: Option<Vec<String>>,
    pub version: i64,
    pub version_type: u8,
    pub fetch_source_context_present: bool,
}

impl OpenSearchMultiGetItemRequestWire {
    pub fn new(index: String, id: String) -> Self {
        Self {
            index,
            id,
            routing: None,
            stored_fields: None,
            version: OPENSEARCH_MATCH_ANY_VERSION,
            version_type: OPENSEARCH_VERSION_TYPE_INTERNAL,
            fetch_source_context_present: false,
        }
    }

    fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_string(&self.index);
        output.write_string(&self.id);
        output.write_optional_string(self.routing.as_deref());
        write_optional_string_array(output, self.stored_fields.as_deref());
        output.write_i64(self.version);
        output.write_byte(self.version_type);
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item fetch source context",
                reason:
                    "fetch source context encoding is not implemented by the multi-get adapter yet",
            });
        }
        output.write_bool(false);
        Ok(())
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let item = Self {
            index: input.read_string()?,
            id: input.read_string()?,
            routing: input.read_optional_string()?,
            stored_fields: read_optional_string_array(input)?,
            version: input.read_i64()?,
            version_type: input.read_byte()?,
            fetch_source_context_present: input.read_bool()?,
        };
        if item.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item fetch source context",
                reason:
                    "fetch source context decoding is not implemented by the multi-get adapter yet",
            });
        }
        Ok(item)
    }

    pub fn to_engine_request(&self) -> Result<GetDocumentRequest, TransportActionWireError> {
        if self.routing.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item routing",
                reason: "routing cannot be mapped onto the current get engine request",
            });
        }
        if self.stored_fields.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item stored fields",
                reason: "stored fields cannot be mapped onto the current get engine request",
            });
        }
        if self.version_type != OPENSEARCH_VERSION_TYPE_INTERNAL
            || self.version != OPENSEARCH_MATCH_ANY_VERSION
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item versioning",
                reason: "versioned reads cannot be mapped onto the current get engine request",
            });
        }
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request item fetch source context",
                reason:
                    "fetch source filtering cannot be mapped onto the current get engine request",
            });
        }
        Ok(GetDocumentRequest {
            index: self.index.clone(),
            id: self.id.clone(),
        })
    }
}

impl From<GetDocumentRequest> for OpenSearchMultiGetItemRequestWire {
    fn from(request: GetDocumentRequest) -> Self {
        Self::new(request.index, request.id)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchMultiGetRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub preference: Option<String>,
    pub refresh: bool,
    pub realtime: bool,
    pub items: Vec<OpenSearchMultiGetItemRequestWire>,
}

impl OpenSearchMultiGetRequestWire {
    pub fn new(items: Vec<OpenSearchMultiGetItemRequestWire>) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            preference: None,
            refresh: false,
            realtime: true,
            items,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        output.write_optional_string(self.preference.as_deref());
        output.write_bool(self.refresh);
        output.write_bool(self.realtime);
        output.write_vint(self.items.len() as i32);
        for item in &self.items {
            item.write(output)?;
        }
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let preference = input.read_optional_string()?;
        let refresh = input.read_bool()?;
        let realtime = input.read_bool()?;
        let item_count = read_len(&mut input)?;
        let mut items = Vec::with_capacity(item_count);
        let request = Self {
            parent_task_node,
            parent_task_id,
            preference,
            refresh,
            realtime,
            items: {
                for _ in 0..item_count {
                    items.push(OpenSearchMultiGetItemRequestWire::read(&mut input)?);
                }
                items
            },
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    pub fn to_engine_requests(&self) -> Result<Vec<GetDocumentRequest>, TransportActionWireError> {
        if self.preference.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request preference",
                reason: "preference cannot be mapped onto the current get engine request",
            });
        }
        if self.refresh {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request refresh",
                reason: "pre-get refresh is not part of the current multi-get adapter subset",
            });
        }
        if !self.realtime {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get request realtime flag",
                reason:
                    "non-realtime multi-get cannot be mapped onto the current get engine request",
            });
        }
        self.items
            .iter()
            .map(OpenSearchMultiGetItemRequestWire::to_engine_request)
            .collect()
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchMultiGetItemResponseWire {
    pub response: OpenSearchGetResponseWire,
}

impl OpenSearchMultiGetItemResponseWire {
    fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_bool(false);
        self.response.write(output)
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        if input.read_bool()? {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "multi-get failure item",
                reason: "failure items are not decoded by the multi-get adapter yet",
            });
        }
        Ok(Self {
            response: OpenSearchGetResponseWire::read_from_input(input)?,
        })
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchMultiGetResponseWire {
    pub items: Vec<OpenSearchMultiGetItemResponseWire>,
}

impl OpenSearchMultiGetResponseWire {
    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_vint(self.items.len() as i32);
        for item in &self.items {
            item.write(output)?;
        }
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let item_count = read_len(&mut input)?;
        let mut items = Vec::with_capacity(item_count);
        for _ in 0..item_count {
            items.push(OpenSearchMultiGetItemResponseWire::read(&mut input)?);
        }
        require_no_trailing_bytes(&input)?;
        Ok(Self { items })
    }
}

pub fn build_opensearch_multi_get_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchMultiGetRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_MULTI_GET_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_multi_get_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchMultiGetRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_MULTI_GET_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_MULTI_GET_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchMultiGetRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_multi_get_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchMultiGetResponseWire,
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

pub fn read_opensearch_multi_get_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchMultiGetResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchMultiGetResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchIndexRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub shard_id_present: bool,
    pub wait_for_active_shards: i32,
    pub timeout: TimeValueWire,
    pub index: String,
    pub routed_based_on_cluster_version: i64,
    pub refresh_policy: u8,
    pub id: Option<String>,
    pub routing: Option<String>,
    pub source: Value,
    pub extra_field_values_present: bool,
    pub op_type: u8,
    pub version: i64,
    pub version_type: u8,
    pub pipeline: Option<String>,
    pub final_pipeline: Option<String>,
    pub system_ingest_pipeline: Option<String>,
    pub pipeline_resolved: bool,
    pub retry: bool,
    pub auto_generated_timestamp: i64,
    pub content_type: Option<String>,
    pub if_seq_no: i64,
    pub if_primary_term: i64,
    pub require_alias: bool,
}

impl OpenSearchIndexRequestWire {
    pub fn new(index: String, id: String, source: Value) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            shard_id_present: false,
            wait_for_active_shards: OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT,
            timeout: TimeValueWire::minutes(1),
            index,
            routed_based_on_cluster_version: 0,
            refresh_policy: OPENSEARCH_REFRESH_POLICY_NONE,
            id: Some(id),
            routing: None,
            source,
            extra_field_values_present: false,
            op_type: OPENSEARCH_DOC_WRITE_OP_TYPE_INDEX,
            version: OPENSEARCH_MATCH_ANY_VERSION,
            version_type: OPENSEARCH_VERSION_TYPE_INTERNAL,
            pipeline: None,
            final_pipeline: None,
            system_ingest_pipeline: None,
            pipeline_resolved: false,
            retry: false,
            auto_generated_timestamp: OPENSEARCH_UNSET_AUTO_GENERATED_TIMESTAMP,
            content_type: Some(OPENSEARCH_JSON_MEDIA_TYPE.into()),
            if_seq_no: OPENSEARCH_UNASSIGNED_SEQ_NO,
            if_primary_term: OPENSEARCH_UNASSIGNED_PRIMARY_TERM,
            require_alias: false,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request shard id",
                reason: "explicit shard ids are not encoded by the index adapter yet",
            });
        }
        output.write_bool(false);
        output.write_i32(self.wait_for_active_shards);
        self.timeout.write(output);
        output.write_string(&self.index);
        output.write_vlong(self.routed_based_on_cluster_version);
        output.write_byte(self.refresh_policy);
        output.write_optional_string(self.id.as_deref());
        output.write_optional_string(self.routing.as_deref());
        write_json_bytes_reference(output, &self.source)?;
        if self.extra_field_values_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request extra field values",
                reason: "extra field values are not encoded by the index adapter yet",
            });
        }
        output.write_bool(false);
        output.write_byte(self.op_type);
        output.write_i64(self.version);
        output.write_byte(self.version_type);
        output.write_optional_string(self.pipeline.as_deref());
        output.write_optional_string(self.final_pipeline.as_deref());
        output.write_optional_string(self.system_ingest_pipeline.as_deref());
        output.write_bool(self.pipeline_resolved);
        output.write_bool(self.retry);
        output.write_i64(self.auto_generated_timestamp);
        if let Some(content_type) = self.content_type.as_deref() {
            output.write_bool(true);
            output.write_string(content_type);
        } else {
            output.write_bool(false);
        }
        output.write_zlong(self.if_seq_no);
        output.write_vlong(self.if_primary_term);
        output.write_bool(self.require_alias);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let request = Self::read_from_input(&mut input)?;
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    fn read_from_input(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let (parent_task_node, parent_task_id) = read_parent_task_id(input)?;
        let shard_id_present = input.read_bool()?;
        if shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request shard id",
                reason: "explicit shard ids are not decoded by the index adapter yet",
            });
        }
        let extra_field_values_present;
        let content_type_present;
        let request = Self {
            parent_task_node,
            parent_task_id,
            shard_id_present,
            wait_for_active_shards: input.read_i32()?,
            timeout: TimeValueWire::read(input)?,
            index: input.read_string()?,
            routed_based_on_cluster_version: input.read_vlong()?,
            refresh_policy: input.read_byte()?,
            id: input.read_optional_string()?,
            routing: input.read_optional_string()?,
            source: read_json_bytes_reference(input)?,
            extra_field_values_present: {
                extra_field_values_present = input.read_bool()?;
                if extra_field_values_present {
                    return Err(TransportActionWireError::UnsupportedWireShape {
                        shape: "index request extra field values",
                        reason: "extra field values are not decoded by the index adapter yet",
                    });
                }
                extra_field_values_present
            },
            op_type: input.read_byte()?,
            version: input.read_i64()?,
            version_type: input.read_byte()?,
            pipeline: input.read_optional_string()?,
            final_pipeline: input.read_optional_string()?,
            system_ingest_pipeline: input.read_optional_string()?,
            pipeline_resolved: input.read_bool()?,
            retry: input.read_bool()?,
            auto_generated_timestamp: input.read_i64()?,
            content_type: {
                content_type_present = input.read_bool()?;
                if content_type_present {
                    Some(input.read_string()?)
                } else {
                    None
                }
            },
            if_seq_no: read_zlong(input)?,
            if_primary_term: input.read_vlong()?,
            require_alias: input.read_bool()?,
        };
        Ok(request)
    }

    pub fn to_engine_request(&self) -> Result<IndexDocumentRequest, TransportActionWireError> {
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request shard id",
                reason: "explicit shard ids cannot be mapped onto the current index engine request",
            });
        }
        if self.wait_for_active_shards != OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request active shard count",
                reason:
                    "custom active-shard waits cannot be mapped onto the current index engine request",
            });
        }
        if self.timeout != TimeValueWire::minutes(1) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request timeout",
                reason:
                    "custom replication timeout cannot be mapped onto the current index engine request",
            });
        }
        if self.routed_based_on_cluster_version != 0 {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request routed cluster version",
                reason:
                    "routed cluster version cannot be mapped onto the current index engine request",
            });
        }
        if self.refresh_policy != OPENSEARCH_REFRESH_POLICY_NONE {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request refresh policy",
                reason:
                    "index refresh policy cannot be mapped onto the current index engine request",
            });
        }
        if self.routing.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request routing",
                reason: "routing cannot be mapped onto the current index engine request",
            });
        }
        if self.extra_field_values_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request extra field values",
                reason: "extra field values cannot be mapped onto the current index engine request",
            });
        }
        if self.op_type != OPENSEARCH_DOC_WRITE_OP_TYPE_INDEX {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request op type",
                reason: "create op type cannot be mapped onto the current index engine request",
            });
        }
        if self.version_type != OPENSEARCH_VERSION_TYPE_INTERNAL
            || self.version != OPENSEARCH_MATCH_ANY_VERSION
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request versioning",
                reason: "versioned index cannot be mapped onto the current index engine request",
            });
        }
        if self.pipeline.is_some()
            || self.final_pipeline.is_some()
            || self.system_ingest_pipeline.is_some()
            || self.pipeline_resolved
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request pipeline",
                reason: "ingest pipelines cannot be mapped onto the current index engine request",
            });
        }
        if self.retry {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request retry flag",
                reason: "retry state cannot be mapped onto the current index engine request",
            });
        }
        if self.auto_generated_timestamp != OPENSEARCH_UNSET_AUTO_GENERATED_TIMESTAMP {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request auto generated timestamp",
                reason: "auto-generated ids cannot be mapped onto the current index engine request",
            });
        }
        if self.content_type.as_deref() != Some(OPENSEARCH_JSON_MEDIA_TYPE) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request content type",
                reason: "only JSON index sources are mapped onto the current index engine request",
            });
        }
        if self.if_seq_no != OPENSEARCH_UNASSIGNED_SEQ_NO
            || self.if_primary_term != OPENSEARCH_UNASSIGNED_PRIMARY_TERM
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request optimistic concurrency",
                reason:
                    "optimistic-concurrency index cannot be mapped onto the current index engine request",
            });
        }
        if self.require_alias {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index request require alias",
                reason:
                    "require-alias writes cannot be mapped onto the current index engine request",
            });
        }
        Ok(IndexDocumentRequest {
            index: self.index.clone(),
            id: self
                .id
                .clone()
                .ok_or(TransportActionWireError::MissingRequiredField { field: "id" })?,
            source: self.source.clone(),
        })
    }
}

impl From<IndexDocumentRequest> for OpenSearchIndexRequestWire {
    fn from(request: IndexDocumentRequest) -> Self {
        Self::new(request.index, request.id, request.source)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchIndexResponseWire {
    pub shard_total: i32,
    pub shard_successful: i32,
    pub index: String,
    pub index_uuid: String,
    pub shard_id: i32,
    pub id: String,
    pub version: i64,
    pub seq_no: i64,
    pub primary_term: i64,
    pub forced_refresh: bool,
    pub result: u8,
}

impl OpenSearchIndexResponseWire {
    pub fn created(index: String, metadata: DocumentMetadata) -> Self {
        Self::from_metadata(index, metadata, OPENSEARCH_DOC_WRITE_RESULT_CREATED)
    }

    pub fn updated(index: String, metadata: DocumentMetadata) -> Self {
        Self::from_metadata(index, metadata, OPENSEARCH_DOC_WRITE_RESULT_UPDATED)
    }

    fn from_metadata(index: String, metadata: DocumentMetadata, result: u8) -> Self {
        Self {
            shard_total: 1,
            shard_successful: 1,
            index,
            index_uuid: OPENSEARCH_UNKNOWN_INDEX_UUID.into(),
            shard_id: 0,
            id: metadata.id,
            version: metadata.version as i64,
            seq_no: metadata.seq_no,
            primary_term: metadata.primary_term as i64,
            forced_refresh: false,
            result,
        }
    }

    pub fn from_engine_response(
        response: IndexDocumentResponse,
    ) -> Result<Self, TransportActionWireError> {
        match response.result {
            WriteResult::Created => Ok(Self::created(response.index, response.metadata)),
            WriteResult::Updated => Ok(Self::updated(response.index, response.metadata)),
            WriteResult::Deleted => Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index response write result",
                reason: "deleted engine responses cannot be encoded as IndexResponse",
            }),
        }
    }

    pub fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.shard_total);
        output.write_vint(self.shard_successful);
        output.write_vint(0);
        output.write_string(&self.index);
        output.write_string(&self.index_uuid);
        output.write_vint(self.shard_id);
        output.write_string(&self.id);
        output.write_zlong(self.version);
        output.write_zlong(self.seq_no);
        output.write_vlong(self.primary_term);
        output.write_bool(self.forced_refresh);
        output.write_byte(self.result);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self::read_from_input(&mut input)?;
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }

    fn read_from_input(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let response = Self {
            shard_total: input.read_vint()?,
            shard_successful: input.read_vint()?,
            index: {
                let shard_failure_count = input.read_vint()?;
                if shard_failure_count != 0 {
                    return Err(TransportActionWireError::UnsupportedWireShape {
                        shape: "index response shard failures",
                        reason: "non-empty failure arrays are not decoded by the index adapter yet",
                    });
                }
                input.read_string()?
            },
            index_uuid: input.read_string()?,
            shard_id: input.read_vint()?,
            id: input.read_string()?,
            version: read_zlong(input)?,
            seq_no: read_zlong(input)?,
            primary_term: input.read_vlong()?,
            forced_refresh: input.read_bool()?,
            result: input.read_byte()?,
        };
        if response.result != OPENSEARCH_DOC_WRITE_RESULT_CREATED
            && response.result != OPENSEARCH_DOC_WRITE_RESULT_UPDATED
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "index response result",
                reason: "only created and updated index results are decoded by the index adapter",
            });
        }
        Ok(response)
    }
}

pub fn build_opensearch_index_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchIndexRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_INDEX_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_index_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchIndexRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_INDEX_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_INDEX_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchIndexRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_index_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchIndexResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    response.write(&mut body);
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_index_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchIndexResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchIndexResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchUpdateRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub index: String,
    pub shard_id_present: bool,
    pub timeout: TimeValueWire,
    pub concrete_index: Option<String>,
    pub wait_for_active_shards: i32,
    pub id: String,
    pub routing: Option<String>,
    pub script_present: bool,
    pub retry_on_conflict: i32,
    pub refresh_policy: u8,
    pub doc: Option<OpenSearchIndexRequestWire>,
    pub fetch_source_context_present: bool,
    pub upsert: Option<OpenSearchIndexRequestWire>,
    pub doc_as_upsert: bool,
    pub if_seq_no: i64,
    pub if_primary_term: i64,
    pub detect_noop: bool,
    pub scripted_upsert: bool,
    pub require_alias: bool,
}

impl OpenSearchUpdateRequestWire {
    pub fn new(index: String, id: String, doc: Value) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            index: index.clone(),
            shard_id_present: false,
            timeout: TimeValueWire::minutes(1),
            concrete_index: None,
            wait_for_active_shards: OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT,
            id: id.clone(),
            routing: None,
            script_present: false,
            retry_on_conflict: 0,
            refresh_policy: OPENSEARCH_REFRESH_POLICY_NONE,
            doc: Some(OpenSearchIndexRequestWire::new(index, id, doc)),
            fetch_source_context_present: false,
            upsert: None,
            doc_as_upsert: false,
            if_seq_no: OPENSEARCH_UNASSIGNED_SEQ_NO,
            if_primary_term: OPENSEARCH_UNASSIGNED_PRIMARY_TERM,
            detect_noop: true,
            scripted_upsert: false,
            require_alias: false,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        output.write_string(&self.index);
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request shard id",
                reason: "explicit shard ids are not encoded by the update adapter yet",
            });
        }
        output.write_bool(false);
        self.timeout.write(output);
        output.write_optional_string(self.concrete_index.as_deref());
        output.write_i32(self.wait_for_active_shards);
        output.write_string(&self.id);
        output.write_optional_string(self.routing.as_deref());
        if self.script_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request script",
                reason: "scripted updates are not encoded by the update adapter yet",
            });
        }
        output.write_bool(false);
        output.write_vint(self.retry_on_conflict);
        output.write_byte(self.refresh_policy);
        if let Some(doc) = &self.doc {
            output.write_bool(true);
            doc.write(output)?;
        } else {
            output.write_bool(false);
        }
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request fetch source context",
                reason: "fetch source context is not encoded by the update adapter yet",
            });
        }
        output.write_bool(false);
        if let Some(upsert) = &self.upsert {
            output.write_bool(true);
            upsert.write(output)?;
        } else {
            output.write_bool(false);
        }
        output.write_bool(self.doc_as_upsert);
        output.write_zlong(self.if_seq_no);
        output.write_vlong(self.if_primary_term);
        output.write_bool(self.detect_noop);
        output.write_bool(self.scripted_upsert);
        output.write_bool(self.require_alias);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let index = input.read_string()?;
        let shard_id_present = input.read_bool()?;
        if shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request shard id",
                reason: "explicit shard ids are not decoded by the update adapter yet",
            });
        }
        let timeout = TimeValueWire::read(&mut input)?;
        let concrete_index = input.read_optional_string()?;
        let wait_for_active_shards = input.read_i32()?;
        let id = input.read_string()?;
        let routing = input.read_optional_string()?;
        let script_present = input.read_bool()?;
        if script_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request script",
                reason: "scripted updates are not decoded by the update adapter yet",
            });
        }
        let retry_on_conflict = input.read_vint()?;
        let refresh_policy = input.read_byte()?;
        let doc = if input.read_bool()? {
            Some(OpenSearchIndexRequestWire::read_from_input(&mut input)?)
        } else {
            None
        };
        let fetch_source_context_present = input.read_bool()?;
        if fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request fetch source context",
                reason: "fetch source context is not decoded by the update adapter yet",
            });
        }
        let upsert = if input.read_bool()? {
            Some(OpenSearchIndexRequestWire::read_from_input(&mut input)?)
        } else {
            None
        };
        let request = Self {
            parent_task_node,
            parent_task_id,
            index,
            shard_id_present,
            timeout,
            concrete_index,
            wait_for_active_shards,
            id,
            routing,
            script_present,
            retry_on_conflict,
            refresh_policy,
            doc,
            fetch_source_context_present,
            upsert,
            doc_as_upsert: input.read_bool()?,
            if_seq_no: read_zlong(&mut input)?,
            if_primary_term: input.read_vlong()?,
            detect_noop: input.read_bool()?,
            scripted_upsert: input.read_bool()?,
            require_alias: input.read_bool()?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    pub fn to_engine_request(&self) -> Result<UpdateDocumentRequest, TransportActionWireError> {
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request shard id",
                reason:
                    "explicit shard ids cannot be mapped onto the current update engine request",
            });
        }
        if self.timeout != TimeValueWire::minutes(1) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request timeout",
                reason: "custom timeout cannot be mapped onto the current update engine request",
            });
        }
        if self.concrete_index.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request concrete index",
                reason: "concrete index override cannot be mapped onto the current update engine request",
            });
        }
        if self.wait_for_active_shards != OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request active shard count",
                reason:
                    "custom active-shard waits cannot be mapped onto the current update engine request",
            });
        }
        if self.routing.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request routing",
                reason: "routing cannot be mapped onto the current update engine request",
            });
        }
        if self.script_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request script",
                reason: "scripted updates cannot be mapped onto the current update engine request",
            });
        }
        if self.retry_on_conflict != 0 {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request retry on conflict",
                reason: "retry-on-conflict cannot be mapped onto the current update engine request",
            });
        }
        if self.refresh_policy != OPENSEARCH_REFRESH_POLICY_NONE {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request refresh policy",
                reason:
                    "update refresh policy cannot be mapped onto the current update engine request",
            });
        }
        if self.fetch_source_context_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request fetch source context",
                reason: "fetch source cannot be mapped onto the current update engine request",
            });
        }
        if self.upsert.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request upsert",
                reason: "explicit upsert cannot be mapped onto the current update engine request",
            });
        }
        if self.if_seq_no != OPENSEARCH_UNASSIGNED_SEQ_NO
            || self.if_primary_term != OPENSEARCH_UNASSIGNED_PRIMARY_TERM
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request optimistic concurrency",
                reason:
                    "optimistic-concurrency update cannot be mapped onto the current update engine request",
            });
        }
        if !self.detect_noop {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request detect noop",
                reason: "detect_noop=false cannot be mapped onto the current update engine request",
            });
        }
        if self.scripted_upsert {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request scripted upsert",
                reason: "scripted upsert cannot be mapped onto the current update engine request",
            });
        }
        if self.require_alias {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request require alias",
                reason:
                    "require-alias updates cannot be mapped onto the current update engine request",
            });
        }
        let doc = self
            .doc
            .as_ref()
            .ok_or(TransportActionWireError::MissingRequiredField { field: "doc" })?;
        let doc_request = doc.to_engine_request()?;
        if doc_request.index != self.index || doc_request.id != self.id {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update request doc identity",
                reason: "nested update doc identity must match the update request identity",
            });
        }
        Ok(UpdateDocumentRequest {
            index: self.index.clone(),
            id: self.id.clone(),
            doc: doc_request.source,
            doc_as_upsert: self.doc_as_upsert,
        })
    }
}

impl From<UpdateDocumentRequest> for OpenSearchUpdateRequestWire {
    fn from(request: UpdateDocumentRequest) -> Self {
        let mut wire = Self::new(request.index, request.id, request.doc);
        wire.doc_as_upsert = request.doc_as_upsert;
        wire
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchUpdateResponseWire {
    pub shard_total: i32,
    pub shard_successful: i32,
    pub index: String,
    pub index_uuid: String,
    pub shard_id: i32,
    pub id: String,
    pub version: i64,
    pub seq_no: i64,
    pub primary_term: i64,
    pub forced_refresh: bool,
    pub result: u8,
    pub get_result_present: bool,
}

impl OpenSearchUpdateResponseWire {
    pub fn updated(index: String, metadata: DocumentMetadata) -> Self {
        Self::from_metadata(index, metadata, OPENSEARCH_DOC_WRITE_RESULT_UPDATED)
    }

    pub fn created(index: String, metadata: DocumentMetadata) -> Self {
        Self::from_metadata(index, metadata, OPENSEARCH_DOC_WRITE_RESULT_CREATED)
    }

    fn from_metadata(index: String, metadata: DocumentMetadata, result: u8) -> Self {
        Self {
            shard_total: 1,
            shard_successful: 1,
            index,
            index_uuid: OPENSEARCH_UNKNOWN_INDEX_UUID.into(),
            shard_id: 0,
            id: metadata.id,
            version: metadata.version as i64,
            seq_no: metadata.seq_no,
            primary_term: metadata.primary_term as i64,
            forced_refresh: false,
            result,
            get_result_present: false,
        }
    }

    pub fn from_engine_response(
        response: IndexDocumentResponse,
    ) -> Result<Self, TransportActionWireError> {
        match response.result {
            WriteResult::Created => Ok(Self::created(response.index, response.metadata)),
            WriteResult::Updated => Ok(Self::updated(response.index, response.metadata)),
            WriteResult::Deleted => Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update response write result",
                reason: "deleted engine responses cannot be encoded as UpdateResponse",
            }),
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        output.write_vint(self.shard_total);
        output.write_vint(self.shard_successful);
        output.write_vint(0);
        output.write_string(&self.index);
        output.write_string(&self.index_uuid);
        output.write_vint(self.shard_id);
        output.write_string(&self.id);
        output.write_zlong(self.version);
        output.write_zlong(self.seq_no);
        output.write_vlong(self.primary_term);
        output.write_bool(self.forced_refresh);
        output.write_byte(self.result);
        if self.get_result_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update response get result",
                reason: "embedded get results are not encoded by the update adapter yet",
            });
        }
        output.write_bool(false);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self {
            shard_total: input.read_vint()?,
            shard_successful: input.read_vint()?,
            index: {
                let shard_failure_count = input.read_vint()?;
                if shard_failure_count != 0 {
                    return Err(TransportActionWireError::UnsupportedWireShape {
                        shape: "update response shard failures",
                        reason:
                            "non-empty failure arrays are not decoded by the update adapter yet",
                    });
                }
                input.read_string()?
            },
            index_uuid: input.read_string()?,
            shard_id: input.read_vint()?,
            id: input.read_string()?,
            version: read_zlong(&mut input)?,
            seq_no: read_zlong(&mut input)?,
            primary_term: input.read_vlong()?,
            forced_refresh: input.read_bool()?,
            result: input.read_byte()?,
            get_result_present: input.read_bool()?,
        };
        if response.result != OPENSEARCH_DOC_WRITE_RESULT_CREATED
            && response.result != OPENSEARCH_DOC_WRITE_RESULT_UPDATED
            && response.result != OPENSEARCH_DOC_WRITE_RESULT_NOOP
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update response result",
                reason: "only created, updated, and noop update results are decoded by the update adapter",
            });
        }
        if response.get_result_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "update response get result",
                reason: "embedded get results are not decoded by the update adapter yet",
            });
        }
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }
}

pub fn build_opensearch_update_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchUpdateRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_UPDATE_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_update_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchUpdateRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_UPDATE_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_UPDATE_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchUpdateRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_update_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchUpdateResponseWire,
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

pub fn read_opensearch_update_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchUpdateResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchUpdateResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchDeleteRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub shard_id_present: bool,
    pub wait_for_active_shards: i32,
    pub timeout: TimeValueWire,
    pub index: String,
    pub routed_based_on_cluster_version: i64,
    pub refresh_policy: u8,
    pub id: String,
    pub routing: Option<String>,
    pub version: i64,
    pub version_type: u8,
    pub if_seq_no: i64,
    pub if_primary_term: i64,
}

impl OpenSearchDeleteRequestWire {
    pub fn new(index: String, id: String) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            shard_id_present: false,
            wait_for_active_shards: OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT,
            timeout: TimeValueWire::minutes(1),
            index,
            routed_based_on_cluster_version: 0,
            refresh_policy: OPENSEARCH_REFRESH_POLICY_NONE,
            id,
            routing: None,
            version: OPENSEARCH_MATCH_ANY_VERSION,
            version_type: OPENSEARCH_VERSION_TYPE_INTERNAL,
            if_seq_no: OPENSEARCH_UNASSIGNED_SEQ_NO,
            if_primary_term: OPENSEARCH_UNASSIGNED_PRIMARY_TERM,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request shard id",
                reason: "explicit shard ids are not encoded by the delete adapter yet",
            });
        }
        output.write_bool(false);
        output.write_i32(self.wait_for_active_shards);
        self.timeout.write(output);
        output.write_string(&self.index);
        output.write_vlong(self.routed_based_on_cluster_version);
        output.write_byte(self.refresh_policy);
        output.write_string(&self.id);
        output.write_optional_string(self.routing.as_deref());
        output.write_i64(self.version);
        output.write_byte(self.version_type);
        output.write_zlong(self.if_seq_no);
        output.write_vlong(self.if_primary_term);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let request = Self::read_from_input(&mut input)?;
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    fn read_from_input(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let (parent_task_node, parent_task_id) = read_parent_task_id(input)?;
        let shard_id_present = input.read_bool()?;
        if shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request shard id",
                reason: "explicit shard ids are not decoded by the delete adapter yet",
            });
        }
        let request = Self {
            parent_task_node,
            parent_task_id,
            shard_id_present,
            wait_for_active_shards: input.read_i32()?,
            timeout: TimeValueWire::read(input)?,
            index: input.read_string()?,
            routed_based_on_cluster_version: input.read_vlong()?,
            refresh_policy: input.read_byte()?,
            id: input.read_string()?,
            routing: input.read_optional_string()?,
            version: input.read_i64()?,
            version_type: input.read_byte()?,
            if_seq_no: read_zlong(input)?,
            if_primary_term: input.read_vlong()?,
        };
        Ok(request)
    }

    pub fn to_engine_request(&self) -> Result<DeleteDocumentRequest, TransportActionWireError> {
        if self.shard_id_present {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request shard id",
                reason:
                    "explicit shard ids cannot be mapped onto the current delete engine request",
            });
        }
        if self.wait_for_active_shards != OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request active shard count",
                reason: "custom active-shard waits cannot be mapped onto the current delete engine request",
            });
        }
        if self.timeout != TimeValueWire::minutes(1) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request timeout",
                reason: "custom replication timeout cannot be mapped onto the current delete engine request",
            });
        }
        if self.routed_based_on_cluster_version != 0 {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request routed cluster version",
                reason:
                    "routed cluster version cannot be mapped onto the current delete engine request",
            });
        }
        if self.refresh_policy != OPENSEARCH_REFRESH_POLICY_NONE {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request refresh policy",
                reason:
                    "delete refresh policy cannot be mapped onto the current delete engine request",
            });
        }
        if self.routing.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request routing",
                reason: "routing cannot be mapped onto the current delete engine request",
            });
        }
        if self.version_type != OPENSEARCH_VERSION_TYPE_INTERNAL
            || self.version != OPENSEARCH_MATCH_ANY_VERSION
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request versioning",
                reason: "versioned delete cannot be mapped onto the current delete engine request",
            });
        }
        if self.if_seq_no != OPENSEARCH_UNASSIGNED_SEQ_NO
            || self.if_primary_term != OPENSEARCH_UNASSIGNED_PRIMARY_TERM
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete request optimistic concurrency",
                reason: "optimistic-concurrency delete cannot be mapped onto the current delete engine request",
            });
        }
        Ok(DeleteDocumentRequest {
            index: self.index.clone(),
            id: self.id.clone(),
        })
    }
}

impl From<DeleteDocumentRequest> for OpenSearchDeleteRequestWire {
    fn from(request: DeleteDocumentRequest) -> Self {
        Self::new(request.index, request.id)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchDeleteResponseWire {
    pub shard_total: i32,
    pub shard_successful: i32,
    pub index: String,
    pub index_uuid: String,
    pub shard_id: i32,
    pub id: String,
    pub version: i64,
    pub seq_no: i64,
    pub primary_term: i64,
    pub forced_refresh: bool,
    pub result: u8,
}

impl OpenSearchDeleteResponseWire {
    pub fn deleted(index: String, metadata: DocumentMetadata) -> Self {
        Self {
            shard_total: 1,
            shard_successful: 1,
            index,
            index_uuid: OPENSEARCH_UNKNOWN_INDEX_UUID.into(),
            shard_id: 0,
            id: metadata.id,
            version: metadata.version as i64,
            seq_no: metadata.seq_no,
            primary_term: metadata.primary_term as i64,
            forced_refresh: false,
            result: OPENSEARCH_DOC_WRITE_RESULT_DELETED,
        }
    }

    pub fn not_found(index: String, id: String) -> Self {
        Self {
            shard_total: 1,
            shard_successful: 1,
            index,
            index_uuid: OPENSEARCH_UNKNOWN_INDEX_UUID.into(),
            shard_id: 0,
            id,
            version: OPENSEARCH_NOT_FOUND_VERSION,
            seq_no: OPENSEARCH_UNASSIGNED_SEQ_NO,
            primary_term: OPENSEARCH_UNASSIGNED_PRIMARY_TERM,
            forced_refresh: false,
            result: OPENSEARCH_DOC_WRITE_RESULT_NOT_FOUND,
        }
    }

    pub fn from_engine_response(
        response: IndexDocumentResponse,
    ) -> Result<Self, TransportActionWireError> {
        if response.result != WriteResult::Deleted {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete response write result",
                reason: "only deleted engine responses can be encoded as DeleteResponse",
            });
        }
        Ok(Self::deleted(response.index, response.metadata))
    }

    pub fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.shard_total);
        output.write_vint(self.shard_successful);
        output.write_vint(0);
        output.write_string(&self.index);
        output.write_string(&self.index_uuid);
        output.write_vint(self.shard_id);
        output.write_string(&self.id);
        output.write_zlong(self.version);
        output.write_zlong(self.seq_no);
        output.write_vlong(self.primary_term);
        output.write_bool(self.forced_refresh);
        output.write_byte(self.result);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self::read_from_input(&mut input)?;
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }

    fn read_from_input(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let response = Self {
            shard_total: input.read_vint()?,
            shard_successful: input.read_vint()?,
            index: {
                let shard_failure_count = input.read_vint()?;
                if shard_failure_count != 0 {
                    return Err(TransportActionWireError::UnsupportedWireShape {
                        shape: "delete response shard failures",
                        reason:
                            "non-empty failure arrays are not decoded by the delete adapter yet",
                    });
                }
                input.read_string()?
            },
            index_uuid: input.read_string()?,
            shard_id: input.read_vint()?,
            id: input.read_string()?,
            version: read_zlong(input)?,
            seq_no: read_zlong(input)?,
            primary_term: input.read_vlong()?,
            forced_refresh: input.read_bool()?,
            result: input.read_byte()?,
        };
        if response.result != OPENSEARCH_DOC_WRITE_RESULT_DELETED
            && response.result != OPENSEARCH_DOC_WRITE_RESULT_NOT_FOUND
        {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "delete response result",
                reason:
                    "only deleted and not-found delete results are decoded by the delete adapter",
            });
        }
        Ok(response)
    }
}

pub fn build_opensearch_delete_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchDeleteRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_DELETE_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_delete_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchDeleteRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_DELETE_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_DELETE_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchDeleteRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_delete_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchDeleteResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    response.write(&mut body);
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_delete_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchDeleteResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchDeleteResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, PartialEq)]
pub enum OpenSearchBulkRequestItemWire {
    Index(OpenSearchIndexRequestWire),
    Delete(OpenSearchDeleteRequestWire),
}

impl OpenSearchBulkRequestItemWire {
    fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        match self {
            Self::Index(request) => {
                output.write_byte(OPENSEARCH_DOC_WRITE_REQUEST_INDEX);
                request.write(output)
            }
            Self::Delete(request) => {
                output.write_byte(OPENSEARCH_DOC_WRITE_REQUEST_DELETE);
                request.write(output)
            }
        }
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        match input.read_byte()? {
            OPENSEARCH_DOC_WRITE_REQUEST_INDEX => Ok(Self::Index(
                OpenSearchIndexRequestWire::read_from_input(input)?,
            )),
            OPENSEARCH_DOC_WRITE_REQUEST_DELETE => Ok(Self::Delete(
                OpenSearchDeleteRequestWire::read_from_input(input)?,
            )),
            OPENSEARCH_DOC_WRITE_REQUEST_UPDATE => {
                Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "bulk request update item",
                    reason: "update items are not decoded by the bulk adapter yet",
                })
            }
            _ => Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk request item type",
                reason: "bulk item request type is outside the OpenSearch source-derived range",
            }),
        }
    }

    fn to_engine_operation(&self) -> Result<BulkWriteOperation, TransportActionWireError> {
        match self {
            Self::Index(request) => Ok(BulkWriteOperation::Index(request.to_engine_request()?)),
            Self::Delete(request) => Ok(BulkWriteOperation::Delete(request.to_engine_request()?)),
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct OpenSearchBulkRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub wait_for_active_shards: i32,
    pub items: Vec<OpenSearchBulkRequestItemWire>,
    pub refresh_policy: u8,
    pub timeout: TimeValueWire,
}

impl OpenSearchBulkRequestWire {
    pub fn new(items: Vec<OpenSearchBulkRequestItemWire>) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            wait_for_active_shards: OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT,
            items,
            refresh_policy: OPENSEARCH_REFRESH_POLICY_NONE,
            timeout: TimeValueWire::minutes(1),
        }
    }

    pub fn write(&self, output: &mut StreamOutput) -> Result<(), TransportActionWireError> {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        output.write_i32(self.wait_for_active_shards);
        output.write_vint(self.items.len() as i32);
        for item in &self.items {
            item.write(output)?;
        }
        output.write_byte(self.refresh_policy);
        self.timeout.write(output);
        Ok(())
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let item_count;
        let request = Self {
            parent_task_node,
            parent_task_id,
            wait_for_active_shards: input.read_i32()?,
            items: {
                item_count = read_len(&mut input)?;
                let mut items = Vec::with_capacity(item_count);
                for _ in 0..item_count {
                    items.push(OpenSearchBulkRequestItemWire::read(&mut input)?);
                }
                items
            },
            refresh_policy: input.read_byte()?,
            timeout: TimeValueWire::read(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    pub fn to_engine_request(&self) -> Result<BulkWriteRequest, TransportActionWireError> {
        if self.wait_for_active_shards != OPENSEARCH_ACTIVE_SHARD_COUNT_DEFAULT {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk request active shard count",
                reason:
                    "custom active-shard waits cannot be mapped onto the current bulk engine request",
            });
        }
        if self.refresh_policy != OPENSEARCH_REFRESH_POLICY_NONE {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk request refresh policy",
                reason: "bulk refresh policy cannot be mapped onto the current bulk engine request",
            });
        }
        if self.timeout != TimeValueWire::minutes(1) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk request timeout",
                reason:
                    "custom replication timeout cannot be mapped onto the current bulk engine request",
            });
        }
        let operations = self
            .items
            .iter()
            .map(OpenSearchBulkRequestItemWire::to_engine_operation)
            .collect::<Result<Vec<_>, _>>()?;
        Ok(BulkWriteRequest { operations })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum OpenSearchBulkItemResponseBodyWire {
    Index(OpenSearchIndexResponseWire),
    Delete(OpenSearchDeleteResponseWire),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchBulkItemResponseWire {
    pub item_id: i32,
    pub op_type: u8,
    pub response: OpenSearchBulkItemResponseBodyWire,
}

impl OpenSearchBulkItemResponseWire {
    pub fn index(item_id: i32, response: OpenSearchIndexResponseWire) -> Self {
        Self {
            item_id,
            op_type: OPENSEARCH_DOC_WRITE_OP_TYPE_INDEX,
            response: OpenSearchBulkItemResponseBodyWire::Index(response),
        }
    }

    pub fn delete(item_id: i32, response: OpenSearchDeleteResponseWire) -> Self {
        Self {
            item_id,
            op_type: OPENSEARCH_DOC_WRITE_OP_TYPE_DELETE,
            response: OpenSearchBulkItemResponseBodyWire::Delete(response),
        }
    }

    fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.item_id);
        output.write_byte(self.op_type);
        match &self.response {
            OpenSearchBulkItemResponseBodyWire::Index(response) => {
                output.write_byte(OPENSEARCH_BULK_RESPONSE_INDEX);
                response.write(output);
            }
            OpenSearchBulkItemResponseBodyWire::Delete(response) => {
                output.write_byte(OPENSEARCH_BULK_RESPONSE_DELETE);
                response.write(output);
            }
        }
        output.write_bool(false);
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let item_id = input.read_vint()?;
        let op_type = input.read_byte()?;
        let response = match input.read_byte()? {
            OPENSEARCH_BULK_RESPONSE_INDEX => OpenSearchBulkItemResponseBodyWire::Index(
                OpenSearchIndexResponseWire::read_from_input(input)?,
            ),
            OPENSEARCH_BULK_RESPONSE_DELETE => OpenSearchBulkItemResponseBodyWire::Delete(
                OpenSearchDeleteResponseWire::read_from_input(input)?,
            ),
            OPENSEARCH_BULK_RESPONSE_NONE => {
                return Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "bulk response empty item",
                    reason: "empty bulk item responses are not decoded by the bulk adapter yet",
                });
            }
            OPENSEARCH_BULK_RESPONSE_UPDATE => {
                return Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "bulk response update item",
                    reason: "update bulk item responses are not decoded by the bulk adapter yet",
                });
            }
            _ => {
                return Err(TransportActionWireError::UnsupportedWireShape {
                    shape: "bulk response item type",
                    reason:
                        "bulk item response type is outside the OpenSearch source-derived range",
                });
            }
        };
        if input.read_bool()? {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk response failure item",
                reason: "failure bulk item responses are not decoded by the bulk adapter yet",
            });
        }
        Ok(Self {
            item_id,
            op_type,
            response,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchBulkResponseWire {
    pub items: Vec<OpenSearchBulkItemResponseWire>,
    pub took_millis: i64,
    pub ingest_took_millis: i64,
}

impl OpenSearchBulkResponseWire {
    pub fn success(items: Vec<OpenSearchBulkItemResponseWire>) -> Self {
        Self {
            items,
            took_millis: 0,
            ingest_took_millis: OPENSEARCH_NO_INGEST_TOOK,
        }
    }

    pub fn from_engine_response(
        response: BulkWriteResponse,
    ) -> Result<Self, TransportActionWireError> {
        let mut items = Vec::with_capacity(response.items.len());
        for (item_id, item) in response.items.into_iter().enumerate() {
            items.push(OpenSearchBulkItemResponseWire::from_engine_item(
                item_id as i32,
                item,
            )?);
        }
        Ok(Self::success(items))
    }

    pub fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.items.len() as i32);
        for item in &self.items {
            item.write(output);
        }
        output.write_vlong(self.took_millis);
        output.write_zlong(self.ingest_took_millis);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let item_count = read_len(&mut input)?;
        let mut items = Vec::with_capacity(item_count);
        for _ in 0..item_count {
            items.push(OpenSearchBulkItemResponseWire::read(&mut input)?);
        }
        let response = Self {
            items,
            took_millis: input.read_vlong()?,
            ingest_took_millis: read_zlong(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }
}

impl OpenSearchBulkItemResponseWire {
    fn from_engine_item(
        item_id: i32,
        item: BulkWriteItemResponse,
    ) -> Result<Self, TransportActionWireError> {
        if item.error_type.is_some() {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk response failure item",
                reason: "failure bulk item responses are not encoded by the bulk adapter yet",
            });
        }
        let metadata = item
            .metadata
            .ok_or(TransportActionWireError::MissingRequiredField { field: "metadata" })?;
        let response = IndexDocumentResponse {
            index: item.index,
            metadata,
            coordination: item.coordination.unwrap_or_default(),
            result: item
                .result
                .ok_or(TransportActionWireError::MissingRequiredField { field: "result" })?,
        };
        match item.operation {
            WriteOperationKind::Index => Ok(Self::index(
                item_id,
                OpenSearchIndexResponseWire::from_engine_response(response)?,
            )),
            WriteOperationKind::Delete => Ok(Self::delete(
                item_id,
                OpenSearchDeleteResponseWire::from_engine_response(response)?,
            )),
            WriteOperationKind::Create
            | WriteOperationKind::Update
            | WriteOperationKind::Replay => Err(TransportActionWireError::UnsupportedWireShape {
                shape: "bulk response operation kind",
                reason:
                    "only index and delete bulk item responses are encoded by the bulk adapter yet",
            }),
        }
    }
}

pub fn build_opensearch_bulk_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchBulkRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body)?;
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_BULK_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_bulk_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchBulkRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_BULK_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_BULK_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchBulkRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_bulk_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchBulkResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    response.write(&mut body);
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_bulk_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchBulkResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchBulkResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchRefreshRequestWire {
    pub parent_task_node: String,
    pub parent_task_id: Option<i64>,
    pub indices: Vec<String>,
    pub indices_options: OpenSearchIndicesOptionsWire,
}

impl OpenSearchRefreshRequestWire {
    pub fn new(indices: Vec<String>) -> Self {
        Self {
            parent_task_node: String::new(),
            parent_task_id: None,
            indices,
            indices_options: OpenSearchIndicesOptionsWire::strict_expand_open_forbid_closed(),
        }
    }

    pub fn write(&self, output: &mut StreamOutput) {
        write_parent_task_id(output, &self.parent_task_node, self.parent_task_id);
        output.write_string_array(&self.indices);
        self.indices_options.write(output);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let (parent_task_node, parent_task_id) = read_parent_task_id(&mut input)?;
        let request = Self {
            parent_task_node,
            parent_task_id,
            indices: input.read_string_array()?,
            indices_options: OpenSearchIndicesOptionsWire::read(&mut input)?,
        };
        require_no_trailing_bytes(&input)?;
        Ok(request)
    }

    pub fn to_engine_request(&self) -> RefreshRequest {
        RefreshRequest {
            indices: self.indices.clone(),
        }
    }
}

impl From<RefreshRequest> for OpenSearchRefreshRequestWire {
    fn from(request: RefreshRequest) -> Self {
        Self::new(request.indices)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OpenSearchRefreshResponseWire {
    pub total_shards: i32,
    pub successful_shards: i32,
    pub failed_shards: i32,
}

impl OpenSearchRefreshResponseWire {
    pub fn success(total_shards: i32) -> Self {
        Self {
            total_shards,
            successful_shards: total_shards,
            failed_shards: 0,
        }
    }

    pub fn write(&self, output: &mut StreamOutput) {
        output.write_vint(self.total_shards);
        output.write_vint(self.successful_shards);
        output.write_vint(self.failed_shards);
        output.write_vint(0);
    }

    pub fn read(bytes: Bytes) -> Result<Self, TransportActionWireError> {
        let mut input = StreamInput::new(bytes);
        let response = Self {
            total_shards: input.read_vint()?,
            successful_shards: input.read_vint()?,
            failed_shards: input.read_vint()?,
        };
        let failure_count = input.read_vint()?;
        if failure_count != 0 {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape: "refresh response shard failures",
                reason: "non-empty failure arrays are not decoded by the refresh adapter yet",
            });
        }
        require_no_trailing_bytes(&input)?;
        Ok(response)
    }

    pub fn to_engine_response(&self) -> RefreshResponse {
        RefreshResponse {
            refreshed: self.failed_shards == 0,
        }
    }
}

impl From<RefreshResponse> for OpenSearchRefreshResponseWire {
    fn from(response: RefreshResponse) -> Self {
        if response.refreshed {
            Self::success(1)
        } else {
            Self {
                total_shards: 1,
                successful_shards: 0,
                failed_shards: 1,
            }
        }
    }
}

pub fn build_opensearch_refresh_request_message(
    request_id: i64,
    version: Version,
    request: &OpenSearchRefreshRequestWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    request.write(&mut body);
    let message = TransportMessage {
        request_id,
        status: TransportStatus::request(),
        version,
        variable_header: BytesMut::from(
            &RequestVariableHeader::new(OPENSEARCH_REFRESH_ACTION_NAME).to_bytes()[..],
        ),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_refresh_request_message(
    message: &TransportMessage,
) -> Result<OpenSearchRefreshRequestWire, TransportActionWireError> {
    if !message.status.is_request() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "request",
            actual: message.status.bits(),
        });
    }
    let header = RequestVariableHeader::read(message.variable_header.clone().freeze())?;
    if header.action != OPENSEARCH_REFRESH_ACTION_NAME {
        return Err(TransportActionWireError::UnexpectedAction {
            expected: OPENSEARCH_REFRESH_ACTION_NAME,
            actual: header.action,
        });
    }
    OpenSearchRefreshRequestWire::read(message.body.clone().freeze())
}

pub fn build_opensearch_refresh_response_message(
    request_id: i64,
    version: Version,
    response: &OpenSearchRefreshResponseWire,
) -> Result<BytesMut, TransportActionWireError> {
    let mut body = StreamOutput::new();
    response.write(&mut body);
    let message = TransportMessage {
        request_id,
        status: TransportStatus::response(),
        version,
        variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
        body: BytesMut::from(&body.freeze()[..]),
    };
    Ok(encode_message(&message))
}

pub fn read_opensearch_refresh_response_message(
    message: &TransportMessage,
) -> Result<OpenSearchRefreshResponseWire, TransportActionWireError> {
    if !message.status.is_response() {
        return Err(TransportActionWireError::UnexpectedMessageStatus {
            expected: "response",
            actual: message.status.bits(),
        });
    }
    let _header = ResponseVariableHeader::read(message.variable_header.clone().freeze())?;
    OpenSearchRefreshResponseWire::read(message.body.clone().freeze())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OpenSearchIndicesOptionsWire {
    pub ignore_unavailable: bool,
    pub ignore_aliases: bool,
    pub allow_no_indices: bool,
    pub forbid_aliases_to_multiple_indices: bool,
    pub forbid_closed_indices: bool,
    pub ignore_throttled: bool,
    pub expand_open: bool,
    pub expand_closed: bool,
    pub expand_hidden: bool,
}

impl OpenSearchIndicesOptionsWire {
    pub const fn strict_expand_open_forbid_closed() -> Self {
        Self {
            ignore_unavailable: false,
            ignore_aliases: false,
            allow_no_indices: true,
            forbid_aliases_to_multiple_indices: false,
            forbid_closed_indices: true,
            ignore_throttled: false,
            expand_open: true,
            expand_closed: false,
            expand_hidden: false,
        }
    }

    fn write(&self, output: &mut StreamOutput) {
        write_enum_set(output, &self.option_ordinals());
        write_enum_set(output, &self.wildcard_state_ordinals());
    }

    fn read(input: &mut StreamInput) -> Result<Self, TransportActionWireError> {
        let options = read_enum_set(input, 6, "indices options")?;
        let wildcard_states = read_enum_set(input, 3, "indices wildcard states")?;
        Ok(Self {
            ignore_unavailable: options.contains(&0),
            ignore_aliases: options.contains(&1),
            allow_no_indices: options.contains(&2),
            forbid_aliases_to_multiple_indices: options.contains(&3),
            forbid_closed_indices: options.contains(&4),
            ignore_throttled: options.contains(&5),
            expand_open: wildcard_states.contains(&0),
            expand_closed: wildcard_states.contains(&1),
            expand_hidden: wildcard_states.contains(&2),
        })
    }

    fn option_ordinals(&self) -> Vec<u8> {
        let mut values = Vec::new();
        if self.ignore_unavailable {
            values.push(0);
        }
        if self.ignore_aliases {
            values.push(1);
        }
        if self.allow_no_indices {
            values.push(2);
        }
        if self.forbid_aliases_to_multiple_indices {
            values.push(3);
        }
        if self.forbid_closed_indices {
            values.push(4);
        }
        if self.ignore_throttled {
            values.push(5);
        }
        values
    }

    fn wildcard_state_ordinals(&self) -> Vec<u8> {
        let mut values = Vec::new();
        if self.expand_open {
            values.push(0);
        }
        if self.expand_closed {
            values.push(1);
        }
        if self.expand_hidden {
            values.push(2);
        }
        values
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

    pub fn first_hit(&self) -> Option<&SearchHit> {
        self.result.first_hit()
    }

    pub fn last_hit(&self) -> Option<&SearchHit> {
        self.result.last_hit()
    }

    pub fn hit_at(&self, index: usize) -> Option<&SearchHit> {
        self.result.hit_at(index)
    }

    pub fn hits(&self) -> Option<&[SearchHit]> {
        self.result.hits()
    }

    pub fn iter_hits(&self) -> Option<std::slice::Iter<'_, SearchHit>> {
        self.result.iter_hits()
    }

    pub fn into_hits(self) -> Option<Vec<SearchHit>> {
        self.result.into_hits()
    }

    pub fn into_iter_hits(self) -> Option<std::vec::IntoIter<SearchHit>> {
        self.result.into_iter_hits()
    }

    pub fn hit_count(&self) -> usize {
        self.result.hit_count()
    }

    pub fn has_hits(&self) -> bool {
        self.result.has_hits()
    }

    pub fn is_empty(&self) -> bool {
        self.result.is_empty()
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
    #[error("missing required transport wire field {field}")]
    MissingRequiredField { field: &'static str },
    #[error("unexpected transport message status: expected {expected}, got bits {actual}")]
    UnexpectedMessageStatus { expected: &'static str, actual: u8 },
    #[error("unsupported transport wire shape {shape}: {reason}")]
    UnsupportedWireShape {
        shape: &'static str,
        reason: &'static str,
    },
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

fn write_optional_string_array(output: &mut StreamOutput, values: Option<&[String]>) {
    if let Some(values) = values {
        output.write_bool(true);
        output.write_string_array(values);
    } else {
        output.write_bool(false);
    }
}

fn read_optional_string_array(
    input: &mut StreamInput,
) -> Result<Option<Vec<String>>, TransportActionWireError> {
    if input.read_bool()? {
        Ok(Some(input.read_string_array()?))
    } else {
        Ok(None)
    }
}

fn write_enum_set(output: &mut StreamOutput, ordinals: &[u8]) {
    output.write_vint(ordinals.len() as i32);
    for ordinal in ordinals {
        output.write_vint(i32::from(*ordinal));
    }
}

fn read_enum_set(
    input: &mut StreamInput,
    variant_count: u8,
    shape: &'static str,
) -> Result<Vec<u8>, TransportActionWireError> {
    let len = read_len(input)?;
    let mut ordinals = Vec::with_capacity(len);
    for _ in 0..len {
        let ordinal = input.read_vint()?;
        if ordinal < 0 || ordinal >= i32::from(variant_count) {
            return Err(TransportActionWireError::UnsupportedWireShape {
                shape,
                reason: "enum ordinal is outside the OpenSearch source-derived range",
            });
        }
        let ordinal = ordinal as u8;
        if !ordinals.contains(&ordinal) {
            ordinals.push(ordinal);
        }
    }
    Ok(ordinals)
}

fn write_json_bytes_reference(
    output: &mut StreamOutput,
    value: &Value,
) -> Result<(), TransportActionWireError> {
    let encoded = serde_json::to_vec(value).map_err(TransportActionWireError::JsonEncode)?;
    output.write_bytes_reference(&encoded);
    Ok(())
}

fn read_json_bytes_reference(input: &mut StreamInput) -> Result<Value, TransportActionWireError> {
    let value = input.read_bytes_reference()?;
    serde_json::from_slice(&value).map_err(TransportActionWireError::JsonDecode)
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
        SearchPhaseResult, SearchResponse, SortSpec, WriteCoordinationMetadata,
    };
    use serde::Deserialize;
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
    fn opensearch_priority_transport_actions_have_source_names_and_stages() {
        assert_eq!(
            OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS,
            &[
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/read/search",
                    action_type: "SearchAction",
                    transport_action: "TransportSearchAction",
                    request_wire_type: "SearchRequest",
                    response_wire_type: "SearchResponse",
                    adapter_stage: "search-read",
                    next_step: "register request/response codec and route to the Rust search executor",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/read/msearch",
                    action_type: "MultiSearchAction",
                    transport_action: "TransportMultiSearchAction",
                    request_wire_type: "MultiSearchRequest",
                    response_wire_type: "MultiSearchResponse",
                    adapter_stage: "search-read",
                    next_step: "decode batched search requests and aggregate Rust search responses",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/read/get",
                    action_type: "GetAction",
                    transport_action: "TransportGetAction",
                    request_wire_type: "GetRequest",
                    response_wire_type: "GetResponse",
                    adapter_stage: "document-read",
                    next_step: "map document get requests onto Rust point lookup semantics",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/read/mget",
                    action_type: "MultiGetAction",
                    transport_action: "TransportMultiGetAction",
                    request_wire_type: "MultiGetRequest",
                    response_wire_type: "MultiGetResponse",
                    adapter_stage: "document-read",
                    next_step: "decode batched document gets and preserve per-item response status",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/write/bulk",
                    action_type: "BulkAction",
                    transport_action: "TransportBulkAction",
                    request_wire_type: "BulkRequest",
                    response_wire_type: "BulkResponse",
                    adapter_stage: "write-replication",
                    next_step: "decode bulk items and route index/update/delete operations through Rust writes",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/write/index",
                    action_type: "IndexAction",
                    transport_action: "TransportIndexAction",
                    request_wire_type: "IndexRequest",
                    response_wire_type: "IndexResponse",
                    adapter_stage: "write-replication",
                    next_step: "map single-document index requests onto Rust write semantics",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/write/update",
                    action_type: "UpdateAction",
                    transport_action: "TransportUpdateAction",
                    request_wire_type: "UpdateRequest",
                    response_wire_type: "UpdateResponse",
                    adapter_stage: "write-replication",
                    next_step: "resolve update scripts/docs into Rust write operations with matching response status",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:data/write/delete",
                    action_type: "DeleteAction",
                    transport_action: "TransportDeleteAction",
                    request_wire_type: "DeleteRequest",
                    response_wire_type: "DeleteResponse",
                    adapter_stage: "write-replication",
                    next_step: "map single-document delete requests onto Rust tombstone/write semantics",
                },
                OpenSearchPriorityTransportActionSpec {
                    action_name: "indices:admin/refresh",
                    action_type: "RefreshAction",
                    transport_action: "TransportRefreshAction",
                    request_wire_type: "RefreshRequest",
                    response_wire_type: "RefreshResponse",
                    adapter_stage: "refresh-visibility",
                    next_step: "map refresh requests onto Rust visibility barriers and shard status reporting",
                },
            ]
        );
    }

    #[test]
    fn opensearch_transport_action_dispatch_classifies_current_adapters() {
        assert_eq!(
            classify_opensearch_transport_action(CLUSTER_STATE_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(PENDING_CLUSTER_TASKS_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(CLUSTER_UPDATE_SETTINGS_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Rejected
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_SEARCH_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Missing
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_GET_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_MULTI_GET_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_BULK_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_INDEX_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_UPDATE_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_DELETE_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            classify_opensearch_transport_action(OPENSEARCH_REFRESH_ACTION_NAME).disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
    }

    #[test]
    fn opensearch_transport_action_dispatch_marks_priority_targets_explicitly() {
        for spec in OPENSEARCH_PRIORITY_TRANSPORT_ACTIONS {
            let decision = classify_opensearch_transport_action(spec.action_name);
            if spec.action_name == OPENSEARCH_GET_ACTION_NAME
                || spec.action_name == OPENSEARCH_MULTI_GET_ACTION_NAME
                || spec.action_name == OPENSEARCH_BULK_ACTION_NAME
                || spec.action_name == OPENSEARCH_INDEX_ACTION_NAME
                || spec.action_name == OPENSEARCH_UPDATE_ACTION_NAME
                || spec.action_name == OPENSEARCH_DELETE_ACTION_NAME
                || spec.action_name == OPENSEARCH_REFRESH_ACTION_NAME
            {
                assert_eq!(
                    decision.disposition,
                    OpenSearchTransportActionDisposition::Implemented,
                    "{}",
                    spec.action_name
                );
                continue;
            }

            assert_eq!(
                decision.disposition,
                OpenSearchTransportActionDisposition::Missing,
                "{}",
                spec.action_name
            );
            assert!(
                decision
                    .reason
                    .starts_with("priority transport adapter target"),
                "{}",
                spec.action_name
            );
        }

        let unknown = classify_opensearch_transport_action("indices:data/read/unknown");
        assert_eq!(
            unknown.disposition,
            OpenSearchTransportActionDisposition::Missing
        );
        assert_eq!(
            unknown.reason,
            "no OpenSearch transport action adapter is registered"
        );
    }

    #[test]
    fn opensearch_get_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchGetRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            ..OpenSearchGetRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchGetRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request().unwrap(),
            GetDocumentRequest {
                index: "logs-000001".into(),
                id: "doc-1".into(),
            }
        );
    }

    #[test]
    fn opensearch_get_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchGetRequestWire {
            routing: Some("tenant-a".into()),
            ..OpenSearchGetRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "get request routing");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_get_response_wire_round_trips_found_and_missing_documents() {
        let found = OpenSearchGetResponseWire::found(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 3,
                seq_no: 7,
                primary_term: 2,
            },
            json!({ "message": "hello", "tenant": "tenant-a" }),
        );

        let mut output = StreamOutput::new();
        found.write(&mut output).unwrap();
        let decoded = OpenSearchGetResponseWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, found);
        assert_eq!(
            decoded.into_engine_response().unwrap(),
            GetDocumentResponse {
                index: "logs-000001".into(),
                metadata: DocumentMetadata {
                    id: "doc-1".into(),
                    version: 3,
                    seq_no: 7,
                    primary_term: 2,
                },
                source: json!({ "message": "hello", "tenant": "tenant-a" }),
                found: true,
            }
        );

        let missing = OpenSearchGetResponseWire::not_found("logs-000001".into(), "doc-404".into());
        let mut output = StreamOutput::new();
        missing.write(&mut output).unwrap();
        assert_eq!(
            OpenSearchGetResponseWire::read(output.freeze())
                .unwrap()
                .into_engine_response(),
            None
        );
    }

    #[test]
    fn opensearch_get_transport_messages_bind_action_frames() {
        let request = OpenSearchGetRequestWire::new("logs-000001".into(), "doc-1".into());
        let mut frame =
            build_opensearch_get_request_message(21, OPENSEARCH_3_7_0_TRANSPORT, &request).unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 21);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_get_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchGetResponseWire::found(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 1,
                seq_no: 0,
                primary_term: 1,
            },
            json!({ "message": "hello" }),
        );
        let mut frame =
            build_opensearch_get_response_message(21, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 21);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_get_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_multi_get_request_wire_round_trips_and_maps_to_engine_requests() {
        let request = OpenSearchMultiGetRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            items: vec![
                OpenSearchMultiGetItemRequestWire::new("logs-000001".into(), "doc-1".into()),
                OpenSearchMultiGetItemRequestWire::new("metrics-000001".into(), "doc-2".into()),
            ],
            ..OpenSearchMultiGetRequestWire::new(Vec::new())
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchMultiGetRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_requests().unwrap(),
            vec![
                GetDocumentRequest {
                    index: "logs-000001".into(),
                    id: "doc-1".into(),
                },
                GetDocumentRequest {
                    index: "metrics-000001".into(),
                    id: "doc-2".into(),
                },
            ]
        );
    }

    #[test]
    fn opensearch_multi_get_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchMultiGetRequestWire {
            preference: Some("_primary".into()),
            items: vec![OpenSearchMultiGetItemRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
            )],
            ..OpenSearchMultiGetRequestWire::new(Vec::new())
        };

        match request.to_engine_requests().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "multi-get request preference");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchMultiGetRequestWire::new(vec![OpenSearchMultiGetItemRequestWire {
            routing: Some("tenant-a".into()),
            ..OpenSearchMultiGetItemRequestWire::new("logs-000001".into(), "doc-1".into())
        }]);

        match request.to_engine_requests().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "multi-get request item routing");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_multi_get_response_wire_round_trips_successful_items() {
        let response = OpenSearchMultiGetResponseWire {
            items: vec![
                OpenSearchMultiGetItemResponseWire {
                    response: OpenSearchGetResponseWire::found(
                        "logs-000001".into(),
                        DocumentMetadata {
                            id: "doc-1".into(),
                            version: 3,
                            seq_no: 7,
                            primary_term: 2,
                        },
                        json!({ "message": "hello" }),
                    ),
                },
                OpenSearchMultiGetItemResponseWire {
                    response: OpenSearchGetResponseWire::not_found(
                        "logs-000001".into(),
                        "doc-404".into(),
                    ),
                },
            ],
        };

        let mut output = StreamOutput::new();
        response.write(&mut output).unwrap();
        assert_eq!(
            OpenSearchMultiGetResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_multi_get_transport_messages_bind_action_frames() {
        let request = OpenSearchMultiGetRequestWire::new(vec![
            OpenSearchMultiGetItemRequestWire::new("logs-000001".into(), "doc-1".into()),
            OpenSearchMultiGetItemRequestWire::new("logs-000001".into(), "doc-2".into()),
        ]);
        let mut frame =
            build_opensearch_multi_get_request_message(22, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 22);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_multi_get_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchMultiGetResponseWire {
            items: vec![OpenSearchMultiGetItemResponseWire {
                response: OpenSearchGetResponseWire::found(
                    "logs-000001".into(),
                    DocumentMetadata {
                        id: "doc-1".into(),
                        version: 1,
                        seq_no: 0,
                        primary_term: 1,
                    },
                    json!({ "message": "hello" }),
                ),
            }],
        };
        let mut frame =
            build_opensearch_multi_get_response_message(22, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 22);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_multi_get_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_index_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchIndexRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            ..OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "hello", "tenant": "tenant-a" }),
            )
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchIndexRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request().unwrap(),
            IndexDocumentRequest {
                index: "logs-000001".into(),
                id: "doc-1".into(),
                source: json!({ "message": "hello", "tenant": "tenant-a" }),
            }
        );
    }

    #[test]
    fn opensearch_index_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchIndexRequestWire {
            routing: Some("tenant-a".into()),
            ..OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "hello" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "index request routing");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchIndexRequestWire {
            op_type: 1,
            ..OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "hello" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "index request op type");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchIndexRequestWire {
            pipeline: Some("logs-pipeline".into()),
            ..OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "hello" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "index request pipeline");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchIndexRequestWire {
            id: None,
            ..OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "hello" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::MissingRequiredField { field } => {
                assert_eq!(field, "id");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_index_response_wire_round_trips_created_and_updated_documents() {
        let created = OpenSearchIndexResponseWire::created(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 1,
                seq_no: 7,
                primary_term: 2,
            },
        );

        let mut output = StreamOutput::new();
        created.write(&mut output);
        assert_eq!(
            OpenSearchIndexResponseWire::read(output.freeze()).unwrap(),
            created
        );

        let updated = OpenSearchIndexResponseWire::updated(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 2,
                seq_no: 8,
                primary_term: 2,
            },
        );
        let mut output = StreamOutput::new();
        updated.write(&mut output);
        assert_eq!(
            OpenSearchIndexResponseWire::read(output.freeze()).unwrap(),
            updated
        );
    }

    #[test]
    fn opensearch_index_response_maps_from_engine_created_and_updated_responses() {
        let created = IndexDocumentResponse {
            index: "logs-000001".into(),
            metadata: DocumentMetadata {
                id: "doc-1".into(),
                version: 1,
                seq_no: 7,
                primary_term: 2,
            },
            coordination: WriteCoordinationMetadata::default(),
            result: WriteResult::Created,
        };

        assert_eq!(
            OpenSearchIndexResponseWire::from_engine_response(created).unwrap(),
            OpenSearchIndexResponseWire::created(
                "logs-000001".into(),
                DocumentMetadata {
                    id: "doc-1".into(),
                    version: 1,
                    seq_no: 7,
                    primary_term: 2,
                },
            )
        );

        let updated = IndexDocumentResponse {
            index: "logs-000001".into(),
            metadata: DocumentMetadata {
                id: "doc-1".into(),
                version: 2,
                seq_no: 8,
                primary_term: 2,
            },
            coordination: WriteCoordinationMetadata::default(),
            result: WriteResult::Updated,
        };

        assert_eq!(
            OpenSearchIndexResponseWire::from_engine_response(updated).unwrap(),
            OpenSearchIndexResponseWire::updated(
                "logs-000001".into(),
                DocumentMetadata {
                    id: "doc-1".into(),
                    version: 2,
                    seq_no: 8,
                    primary_term: 2,
                },
            )
        );
    }

    #[test]
    fn opensearch_index_transport_messages_bind_action_frames() {
        let request = OpenSearchIndexRequestWire::new(
            "logs-000001".into(),
            "doc-1".into(),
            json!({ "message": "hello" }),
        );
        let mut frame =
            build_opensearch_index_request_message(24, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 24);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_index_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchIndexResponseWire::created(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 1,
                seq_no: 0,
                primary_term: 1,
            },
        );
        let mut frame =
            build_opensearch_index_response_message(24, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 24);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_index_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_update_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchUpdateRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            ..OpenSearchUpdateRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "patched" }),
            )
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchUpdateRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request().unwrap(),
            UpdateDocumentRequest {
                index: "logs-000001".into(),
                id: "doc-1".into(),
                doc: json!({ "message": "patched" }),
                doc_as_upsert: false,
            }
        );
    }

    #[test]
    fn opensearch_update_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchUpdateRequestWire {
            routing: Some("tenant-a".into()),
            ..OpenSearchUpdateRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "patched" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "update request routing");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchUpdateRequestWire {
            retry_on_conflict: 1,
            ..OpenSearchUpdateRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "patched" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "update request retry on conflict");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchUpdateRequestWire {
            upsert: Some(OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "upsert" }),
            )),
            ..OpenSearchUpdateRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "patched" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "update request upsert");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchUpdateRequestWire {
            doc: None,
            ..OpenSearchUpdateRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "patched" }),
            )
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::MissingRequiredField { field } => {
                assert_eq!(field, "doc");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_update_response_wire_round_trips_updated_and_created_documents() {
        let updated = OpenSearchUpdateResponseWire::updated(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 2,
                seq_no: 8,
                primary_term: 2,
            },
        );

        let mut output = StreamOutput::new();
        updated.write(&mut output).unwrap();
        assert_eq!(
            OpenSearchUpdateResponseWire::read(output.freeze()).unwrap(),
            updated
        );

        let created = OpenSearchUpdateResponseWire::created(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-2".into(),
                version: 1,
                seq_no: 9,
                primary_term: 2,
            },
        );
        let mut output = StreamOutput::new();
        created.write(&mut output).unwrap();
        assert_eq!(
            OpenSearchUpdateResponseWire::read(output.freeze()).unwrap(),
            created
        );
    }

    #[test]
    fn opensearch_update_response_maps_from_engine_updated_response() {
        let response = IndexDocumentResponse {
            index: "logs-000001".into(),
            metadata: DocumentMetadata {
                id: "doc-1".into(),
                version: 2,
                seq_no: 8,
                primary_term: 2,
            },
            coordination: WriteCoordinationMetadata::default(),
            result: WriteResult::Updated,
        };

        assert_eq!(
            OpenSearchUpdateResponseWire::from_engine_response(response).unwrap(),
            OpenSearchUpdateResponseWire::updated(
                "logs-000001".into(),
                DocumentMetadata {
                    id: "doc-1".into(),
                    version: 2,
                    seq_no: 8,
                    primary_term: 2,
                },
            )
        );
    }

    #[test]
    fn opensearch_update_transport_messages_bind_action_frames() {
        let request = OpenSearchUpdateRequestWire::new(
            "logs-000001".into(),
            "doc-1".into(),
            json!({ "message": "patched" }),
        );
        let mut frame =
            build_opensearch_update_request_message(26, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 26);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_update_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchUpdateResponseWire::updated(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 2,
                seq_no: 1,
                primary_term: 1,
            },
        );
        let mut frame =
            build_opensearch_update_response_message(26, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 26);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_update_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_delete_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchDeleteRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            ..OpenSearchDeleteRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchDeleteRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request().unwrap(),
            DeleteDocumentRequest {
                index: "logs-000001".into(),
                id: "doc-1".into(),
            }
        );
    }

    #[test]
    fn opensearch_delete_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchDeleteRequestWire {
            routing: Some("tenant-a".into()),
            ..OpenSearchDeleteRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "delete request routing");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchDeleteRequestWire {
            refresh_policy: 1,
            ..OpenSearchDeleteRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "delete request refresh policy");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchDeleteRequestWire {
            if_seq_no: 7,
            if_primary_term: 2,
            ..OpenSearchDeleteRequestWire::new("logs-000001".into(), "doc-1".into())
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "delete request optimistic concurrency");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_delete_response_wire_round_trips_deleted_and_missing_documents() {
        let deleted = OpenSearchDeleteResponseWire::deleted(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 3,
                seq_no: 7,
                primary_term: 2,
            },
        );

        let mut output = StreamOutput::new();
        deleted.write(&mut output);
        assert_eq!(
            OpenSearchDeleteResponseWire::read(output.freeze()).unwrap(),
            deleted
        );

        let missing =
            OpenSearchDeleteResponseWire::not_found("logs-000001".into(), "doc-404".into());
        let mut output = StreamOutput::new();
        missing.write(&mut output);
        assert_eq!(
            OpenSearchDeleteResponseWire::read(output.freeze()).unwrap(),
            missing
        );
    }

    #[test]
    fn opensearch_delete_response_maps_from_engine_deleted_response() {
        let response = IndexDocumentResponse {
            index: "logs-000001".into(),
            metadata: DocumentMetadata {
                id: "doc-1".into(),
                version: 3,
                seq_no: 7,
                primary_term: 2,
            },
            coordination: WriteCoordinationMetadata::default(),
            result: WriteResult::Deleted,
        };

        assert_eq!(
            OpenSearchDeleteResponseWire::from_engine_response(response).unwrap(),
            OpenSearchDeleteResponseWire::deleted(
                "logs-000001".into(),
                DocumentMetadata {
                    id: "doc-1".into(),
                    version: 3,
                    seq_no: 7,
                    primary_term: 2,
                },
            )
        );
    }

    #[test]
    fn opensearch_delete_transport_messages_bind_action_frames() {
        let request = OpenSearchDeleteRequestWire::new("logs-000001".into(), "doc-1".into());
        let mut frame =
            build_opensearch_delete_request_message(23, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 23);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_delete_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchDeleteResponseWire::deleted(
            "logs-000001".into(),
            DocumentMetadata {
                id: "doc-1".into(),
                version: 1,
                seq_no: 0,
                primary_term: 1,
            },
        );
        let mut frame =
            build_opensearch_delete_response_message(23, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 23);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_delete_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_bulk_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchBulkRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            items: vec![
                OpenSearchBulkRequestItemWire::Index(OpenSearchIndexRequestWire::new(
                    "logs-000001".into(),
                    "doc-1".into(),
                    json!({ "message": "created" }),
                )),
                OpenSearchBulkRequestItemWire::Delete(OpenSearchDeleteRequestWire::new(
                    "logs-000001".into(),
                    "doc-2".into(),
                )),
            ],
            ..OpenSearchBulkRequestWire::new(Vec::new())
        };

        let mut output = StreamOutput::new();
        request.write(&mut output).unwrap();
        let decoded = OpenSearchBulkRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request().unwrap(),
            BulkWriteRequest {
                operations: vec![
                    BulkWriteOperation::Index(IndexDocumentRequest {
                        index: "logs-000001".into(),
                        id: "doc-1".into(),
                        source: json!({ "message": "created" }),
                    }),
                    BulkWriteOperation::Delete(DeleteDocumentRequest {
                        index: "logs-000001".into(),
                        id: "doc-2".into(),
                    }),
                ],
            }
        );
    }

    #[test]
    fn opensearch_bulk_request_rejects_unsupported_engine_mapping_options() {
        let request = OpenSearchBulkRequestWire {
            refresh_policy: 1,
            items: vec![OpenSearchBulkRequestItemWire::Index(
                OpenSearchIndexRequestWire::new(
                    "logs-000001".into(),
                    "doc-1".into(),
                    json!({ "message": "created" }),
                ),
            )],
            ..OpenSearchBulkRequestWire::new(Vec::new())
        };

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "bulk request refresh policy");
            }
            other => panic!("unexpected error {other:?}"),
        }

        let request = OpenSearchBulkRequestWire::new(vec![OpenSearchBulkRequestItemWire::Index(
            OpenSearchIndexRequestWire {
                routing: Some("tenant-a".into()),
                ..OpenSearchIndexRequestWire::new(
                    "logs-000001".into(),
                    "doc-1".into(),
                    json!({ "message": "created" }),
                )
            },
        )]);

        match request.to_engine_request().unwrap_err() {
            TransportActionWireError::UnsupportedWireShape { shape, .. } => {
                assert_eq!(shape, "index request routing");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }

    #[test]
    fn opensearch_bulk_response_wire_round_trips_successful_items() {
        let response = OpenSearchBulkResponseWire::success(vec![
            OpenSearchBulkItemResponseWire::index(
                0,
                OpenSearchIndexResponseWire::created(
                    "logs-000001".into(),
                    DocumentMetadata {
                        id: "doc-1".into(),
                        version: 1,
                        seq_no: 7,
                        primary_term: 2,
                    },
                ),
            ),
            OpenSearchBulkItemResponseWire::delete(
                1,
                OpenSearchDeleteResponseWire::deleted(
                    "logs-000001".into(),
                    DocumentMetadata {
                        id: "doc-2".into(),
                        version: 2,
                        seq_no: 8,
                        primary_term: 2,
                    },
                ),
            ),
        ]);

        let mut output = StreamOutput::new();
        response.write(&mut output);
        assert_eq!(
            OpenSearchBulkResponseWire::read(output.freeze()).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_bulk_response_maps_from_engine_response() {
        let response = BulkWriteResponse {
            errors: false,
            items: vec![
                BulkWriteItemResponse {
                    operation: WriteOperationKind::Index,
                    index: "logs-000001".into(),
                    id: "doc-1".into(),
                    status: 201,
                    result: Some(WriteResult::Created),
                    metadata: Some(DocumentMetadata {
                        id: "doc-1".into(),
                        version: 1,
                        seq_no: 7,
                        primary_term: 2,
                    }),
                    coordination: Some(WriteCoordinationMetadata::default()),
                    error_type: None,
                    reason: None,
                },
                BulkWriteItemResponse {
                    operation: WriteOperationKind::Delete,
                    index: "logs-000001".into(),
                    id: "doc-2".into(),
                    status: 200,
                    result: Some(WriteResult::Deleted),
                    metadata: Some(DocumentMetadata {
                        id: "doc-2".into(),
                        version: 2,
                        seq_no: 8,
                        primary_term: 2,
                    }),
                    coordination: Some(WriteCoordinationMetadata::default()),
                    error_type: None,
                    reason: None,
                },
            ],
        };

        assert_eq!(
            OpenSearchBulkResponseWire::from_engine_response(response).unwrap(),
            OpenSearchBulkResponseWire::success(vec![
                OpenSearchBulkItemResponseWire::index(
                    0,
                    OpenSearchIndexResponseWire::created(
                        "logs-000001".into(),
                        DocumentMetadata {
                            id: "doc-1".into(),
                            version: 1,
                            seq_no: 7,
                            primary_term: 2,
                        },
                    ),
                ),
                OpenSearchBulkItemResponseWire::delete(
                    1,
                    OpenSearchDeleteResponseWire::deleted(
                        "logs-000001".into(),
                        DocumentMetadata {
                            id: "doc-2".into(),
                            version: 2,
                            seq_no: 8,
                            primary_term: 2,
                        },
                    ),
                ),
            ])
        );
    }

    #[test]
    fn opensearch_bulk_transport_messages_bind_action_frames() {
        let request = OpenSearchBulkRequestWire::new(vec![
            OpenSearchBulkRequestItemWire::Index(OpenSearchIndexRequestWire::new(
                "logs-000001".into(),
                "doc-1".into(),
                json!({ "message": "created" }),
            )),
            OpenSearchBulkRequestItemWire::Delete(OpenSearchDeleteRequestWire::new(
                "logs-000001".into(),
                "doc-2".into(),
            )),
        ]);
        let mut frame =
            build_opensearch_bulk_request_message(25, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 25);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_bulk_request_message(&message).unwrap(),
            request
        );

        let response =
            OpenSearchBulkResponseWire::success(vec![OpenSearchBulkItemResponseWire::index(
                0,
                OpenSearchIndexResponseWire::created(
                    "logs-000001".into(),
                    DocumentMetadata {
                        id: "doc-1".into(),
                        version: 1,
                        seq_no: 0,
                        primary_term: 1,
                    },
                ),
            )]);
        let mut frame =
            build_opensearch_bulk_response_message(25, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 25);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_bulk_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_refresh_request_wire_round_trips_and_maps_to_engine_request() {
        let request = OpenSearchRefreshRequestWire {
            parent_task_node: "node-a".into(),
            parent_task_id: Some(42),
            indices: vec!["logs-000001".into(), "metrics-000001".into()],
            indices_options: OpenSearchIndicesOptionsWire::strict_expand_open_forbid_closed(),
        };

        let mut output = StreamOutput::new();
        request.write(&mut output);
        let decoded = OpenSearchRefreshRequestWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, request);
        assert_eq!(
            decoded.to_engine_request(),
            RefreshRequest {
                indices: vec!["logs-000001".into(), "metrics-000001".into()],
            }
        );
    }

    #[test]
    fn opensearch_refresh_response_wire_round_trips_and_maps_to_engine_response() {
        let response = OpenSearchRefreshResponseWire {
            total_shards: 3,
            successful_shards: 3,
            failed_shards: 0,
        };

        let mut output = StreamOutput::new();
        response.write(&mut output);
        let decoded = OpenSearchRefreshResponseWire::read(output.freeze()).unwrap();

        assert_eq!(decoded, response);
        assert_eq!(
            decoded.to_engine_response(),
            RefreshResponse { refreshed: true }
        );
    }

    #[test]
    fn opensearch_refresh_transport_messages_bind_action_frames() {
        let request = OpenSearchRefreshRequestWire::new(vec!["logs-000001".into()]);
        let mut frame =
            build_opensearch_refresh_request_message(19, OPENSEARCH_3_7_0_TRANSPORT, &request)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 19);
        assert!(message.status.is_request());
        assert_eq!(
            classify_opensearch_transport_request_message(&message)
                .unwrap()
                .disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
        assert_eq!(
            read_opensearch_refresh_request_message(&message).unwrap(),
            request
        );

        let response = OpenSearchRefreshResponseWire::success(1);
        let mut frame =
            build_opensearch_refresh_response_message(19, OPENSEARCH_3_7_0_TRANSPORT, &response)
                .unwrap();
        let message = match decode_frame(&mut frame).unwrap().unwrap() {
            DecodedFrame::Message(message) => message,
            DecodedFrame::Ping => panic!("expected message frame"),
        };

        assert_eq!(message.request_id, 19);
        assert!(message.status.is_response());
        assert_eq!(
            read_opensearch_refresh_response_message(&message).unwrap(),
            response
        );
    }

    #[test]
    fn opensearch_transport_request_dispatch_reads_action_from_header() {
        let message = TransportMessage {
            request_id: 7,
            status: TransportStatus::request(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            variable_header: BytesMut::from(
                &RequestVariableHeader::new(CLUSTER_STATE_ACTION_NAME).to_bytes()[..],
            ),
            body: BytesMut::new(),
        };

        let decision = classify_opensearch_transport_request_message(&message).unwrap();

        assert_eq!(decision.action_name, CLUSTER_STATE_ACTION_NAME);
        assert_eq!(
            decision.disposition,
            OpenSearchTransportActionDisposition::Implemented
        );
    }

    #[test]
    fn opensearch_transport_request_dispatch_rejects_response_messages() {
        let message = TransportMessage {
            request_id: 7,
            status: TransportStatus::response(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            variable_header: BytesMut::from(&ResponseVariableHeader::default().to_bytes()[..]),
            body: BytesMut::new(),
        };

        match classify_opensearch_transport_request_message(&message).unwrap_err() {
            TransportActionWireError::UnexpectedMessageStatus { expected, actual } => {
                assert_eq!(expected, "request");
                assert_eq!(actual, TransportStatus::response().bits());
            }
            other => panic!("unexpected error {other:?}"),
        }
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
                stored_fields: None,
                source_fields: None,
                source_filter: None,
                source_includes: None,
                source_include: None,
                source_excludes: None,
                source_exclude: None,
                highlight: None,
                explain: false,
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
                    fields: None,
                    highlight: None,
                    explanation: None,
                    sort: None,
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
                stored_fields: None,
                source_fields: None,
                source_filter: None,
                source_includes: None,
                source_include: None,
                source_excludes: None,
                source_exclude: None,
                highlight: None,
                explain: false,
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

    #[derive(Debug, Deserialize)]
    struct MixedClusterRecoveryWireFixture {
        recovery_wire_fixture: MixedClusterRecoveryWirePayload,
    }

    #[derive(Debug, Deserialize)]
    struct MixedClusterRecoveryWirePayload {
        start_request: SteelsearchRecoveryStartRequestWire,
        chunk_request: SteelsearchRecoveryChunkRequestWire,
        translog_request: SteelsearchRecoveryTranslogRequestWire,
        finalize_request: SteelsearchRecoveryFinalizeRequestWire,
        response: SteelsearchRecoveryResponseWire,
    }

    #[test]
    fn mixed_cluster_recovery_wire_fixture_round_trips_all_claimed_shapes() {
        let fixture: MixedClusterRecoveryWireFixture = serde_json::from_str(include_str!(
            "../../../tools/fixtures/mixed-cluster-recovery-wire.json"
        ))
        .expect("mixed-cluster recovery wire fixture should deserialize");

        assert_recovery_request_round_trip(
            build_steelsearch_recovery_start_request_message,
            read_steelsearch_recovery_start_request_message,
            fixture.recovery_wire_fixture.start_request,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_chunk_request_message,
            read_steelsearch_recovery_chunk_request_message,
            fixture.recovery_wire_fixture.chunk_request,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_translog_request_message,
            read_steelsearch_recovery_translog_request_message,
            fixture.recovery_wire_fixture.translog_request,
        );
        assert_recovery_request_round_trip(
            build_steelsearch_recovery_finalize_request_message,
            read_steelsearch_recovery_finalize_request_message,
            fixture.recovery_wire_fixture.finalize_request,
        );

        let mut frame = build_steelsearch_recovery_response_message(
            88,
            OPENSEARCH_3_7_0_TRANSPORT,
            &fixture.recovery_wire_fixture.response,
        )
        .unwrap();
        let DecodedFrame::Message(message) = decode_frame(&mut frame).unwrap().unwrap() else {
            panic!("expected recovery response message");
        };
        assert_eq!(
            read_steelsearch_recovery_response_message(&message).unwrap(),
            fixture.recovery_wire_fixture.response
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

    #[test]
    fn shard_search_request_rejects_unknown_transport_action() {
        let message = TransportMessage {
            request_id: 99,
            status: TransportStatus::request(),
            version: OPENSEARCH_3_7_0_TRANSPORT,
            variable_header: BytesMut::from(
                &RequestVariableHeader::new("cluster:monitor/health").to_bytes()[..],
            ),
            body: BytesMut::new(),
        };

        match read_steelsearch_shard_search_request_message(&message).unwrap_err() {
            TransportActionWireError::UnexpectedAction { expected, actual } => {
                assert_eq!(expected, STEELSEARCH_SHARD_SEARCH_ACTION_NAME);
                assert_eq!(actual, "cluster:monitor/health");
            }
            other => panic!("unexpected error {other:?}"),
        }
    }
}
