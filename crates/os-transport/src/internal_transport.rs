use bytes::BytesMut;
use os_core::Version;
use thiserror::Error;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;

use crate::action::{
    build_steelsearch_replica_operation_request_message,
    build_steelsearch_replica_operation_response_message,
    build_steelsearch_shard_search_request_message,
    build_steelsearch_shard_search_response_message,
    read_steelsearch_replica_operation_request_message,
    read_steelsearch_replica_operation_response_message,
    read_steelsearch_shard_search_request_message, read_steelsearch_shard_search_response_message,
    SteelsearchReplicaOperationRequestWire, SteelsearchReplicaOperationResponseWire,
    SteelsearchShardSearchRequestWire, SteelsearchShardSearchResponseWire,
    TransportActionWireError,
};
use crate::frame::{decode_frame, DecodedFrame, FrameError};

pub async fn send_steelsearch_shard_search_request(
    address: std::net::SocketAddr,
    request_id: i64,
    version: Version,
    request: &SteelsearchShardSearchRequestWire,
) -> Result<SteelsearchShardSearchResponseWire, InternalTransportError> {
    let mut stream = TcpStream::connect(address).await?;
    let frame = build_steelsearch_shard_search_request_message(request_id, version, request)?;
    stream.write_all(&frame).await?;
    stream.flush().await?;

    let message = read_next_message(&mut stream).await?;
    if message.request_id != request_id {
        return Err(InternalTransportError::UnexpectedRequestId {
            expected: request_id,
            actual: message.request_id,
        });
    }
    Ok(read_steelsearch_shard_search_response_message(&message)?)
}

pub async fn handle_steelsearch_shard_search_connection(
    mut stream: TcpStream,
    version: Version,
    handler: impl FnOnce(
        SteelsearchShardSearchRequestWire,
    ) -> Result<SteelsearchShardSearchResponseWire, InternalTransportError>,
) -> Result<(), InternalTransportError> {
    let request_message = read_next_message(&mut stream).await?;
    let request_id = request_message.request_id;
    let request = read_steelsearch_shard_search_request_message(&request_message)?;
    let response = handler(request)?;
    let frame = build_steelsearch_shard_search_response_message(request_id, version, &response)?;
    stream.write_all(&frame).await?;
    stream.flush().await?;
    Ok(())
}

pub async fn send_steelsearch_replica_operation_request(
    address: std::net::SocketAddr,
    request_id: i64,
    version: Version,
    request: &SteelsearchReplicaOperationRequestWire,
) -> Result<SteelsearchReplicaOperationResponseWire, InternalTransportError> {
    let mut stream = TcpStream::connect(address).await?;
    let frame = build_steelsearch_replica_operation_request_message(request_id, version, request)?;
    stream.write_all(&frame).await?;
    stream.flush().await?;

    let message = read_next_message(&mut stream).await?;
    if message.request_id != request_id {
        return Err(InternalTransportError::UnexpectedRequestId {
            expected: request_id,
            actual: message.request_id,
        });
    }
    Ok(read_steelsearch_replica_operation_response_message(
        &message,
    )?)
}

pub async fn handle_steelsearch_replica_operation_connection(
    mut stream: TcpStream,
    version: Version,
    handler: impl FnOnce(
        SteelsearchReplicaOperationRequestWire,
    ) -> Result<SteelsearchReplicaOperationResponseWire, InternalTransportError>,
) -> Result<(), InternalTransportError> {
    let request_message = read_next_message(&mut stream).await?;
    let request_id = request_message.request_id;
    let request = read_steelsearch_replica_operation_request_message(&request_message)?;
    let response = handler(request)?;
    let frame =
        build_steelsearch_replica_operation_response_message(request_id, version, &response)?;
    stream.write_all(&frame).await?;
    stream.flush().await?;
    Ok(())
}

pub fn validate_replica_operation_request_progress(
    request: &SteelsearchReplicaOperationRequestWire,
    current_primary_term: u64,
    local_checkpoint: i64,
) -> Result<(), ReplicaReplicationValidationError> {
    if request.primary_term < current_primary_term {
        return Err(ReplicaReplicationValidationError::StalePrimaryTerm {
            local: current_primary_term,
            remote: request.primary_term,
        });
    }
    if request.primary_term == current_primary_term && request.seq_no <= local_checkpoint {
        return Err(ReplicaReplicationValidationError::StaleSeqNo {
            checkpoint: local_checkpoint,
            remote: request.seq_no,
        });
    }
    Ok(())
}

pub fn validate_replica_operation_response(
    response: &SteelsearchReplicaOperationResponseWire,
) -> Result<(), ReplicaReplicationValidationError> {
    if !response.applied || response.failure.is_some() {
        return Err(ReplicaReplicationValidationError::PartialReplication {
            result: response.result.clone(),
            failure: response.failure.clone(),
        });
    }
    Ok(())
}

async fn read_next_message(
    stream: &mut TcpStream,
) -> Result<crate::TransportMessage, InternalTransportError> {
    let mut buffer = BytesMut::new();
    loop {
        if let Some(frame) = decode_frame(&mut buffer)? {
            return match frame {
                DecodedFrame::Message(message) => Ok(message),
                DecodedFrame::Ping => Err(InternalTransportError::UnexpectedPing),
            };
        }

        let read = stream.read_buf(&mut buffer).await?;
        if read == 0 {
            return Err(InternalTransportError::ConnectionClosed);
        }
    }
}

#[derive(Debug, Error)]
pub enum InternalTransportError {
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    Frame(#[from] FrameError),
    #[error(transparent)]
    Action(#[from] TransportActionWireError),
    #[error("unexpected ping frame while waiting for action message")]
    UnexpectedPing,
    #[error("connection closed before a complete action message arrived")]
    ConnectionClosed,
    #[error("unexpected response request id: expected {expected}, got {actual}")]
    UnexpectedRequestId { expected: i64, actual: i64 },
    #[error("handler failed: {0}")]
    Handler(String),
}

#[derive(Debug, Error, Eq, PartialEq)]
pub enum ReplicaReplicationValidationError {
    #[error("stale primary term: local {local}, remote {remote}")]
    StalePrimaryTerm { local: u64, remote: u64 },
    #[error("stale seq_no: local checkpoint {checkpoint}, remote {remote}")]
    StaleSeqNo { checkpoint: i64, remote: i64 },
    #[error("partial replication response: result {result}, failure {failure:?}")]
    PartialReplication {
        result: String,
        failure: Option<String>,
    },
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::action::{
        SteelsearchReplicaOperationKindWire, SteelsearchReplicaOperationWire,
        SteelsearchRetentionLeaseWire,
    };
    use os_core::OPENSEARCH_3_7_0_TRANSPORT;
    use os_engine::{
        DocumentMetadata, SearchHit, SearchRequest, SearchResponse, SearchShardSearchResult,
        SearchShardTarget,
    };
    use serde::Deserialize;
    use serde_json::json;
    use tokio::net::TcpListener;

    #[derive(Debug, Deserialize)]
    struct MixedClusterWriteReplicationFailClosedFixture {
        cases: Vec<MixedClusterWriteReplicationFailClosedCase>,
    }

    #[derive(Debug, Deserialize)]
    struct MixedClusterWriteReplicationFailClosedCase {
        name: String,
        kind: String,
        current_primary_term: Option<u64>,
        local_checkpoint: Option<i64>,
        request: Option<SteelsearchReplicaOperationRequestWire>,
        request_json: Option<serde_json::Value>,
        response: Option<SteelsearchReplicaOperationResponseWire>,
        expected_error: String,
    }

    #[tokio::test]
    async fn shard_search_client_and_server_round_trip_over_tcp() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            handle_steelsearch_shard_search_connection(
                stream,
                OPENSEARCH_3_7_0_TRANSPORT,
                |request| {
                    Ok(SteelsearchShardSearchResponseWire {
                        result: SearchShardSearchResult::success(
                            request.target,
                            SearchResponse::new(
                                1,
                                vec![SearchHit {
                                    index: "logs-000001".to_string(),
                                    metadata: DocumentMetadata {
                                        id: "remote-1".to_string(),
                                        version: 1,
                                        seq_no: 0,
                                        primary_term: 1,
                                    },
                                    score: 1.0,
                                    source: json!({ "message": "remote" }),
                                }],
                                json!({}),
                            ),
                        ),
                    })
                },
            )
            .await
            .unwrap();
        });

        let response = send_steelsearch_shard_search_request(
            address,
            42,
            OPENSEARCH_3_7_0_TRANSPORT,
            &SteelsearchShardSearchRequestWire {
                parent_task_node: "coordinator".to_string(),
                parent_task_id: None,
                target: SearchShardTarget {
                    index: "logs-000001".to_string(),
                    shard: 0,
                    node: "node-a".to_string(),
                },
                request: SearchRequest {
                    indices: vec!["logs-000001".to_string()],
                    query: json!({ "match_all": {} }),
                    aggregations: json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                },
            },
        )
        .await
        .unwrap();

        server.await.unwrap();
        assert_eq!(
            response.result.response.unwrap().hits[0].metadata.id,
            "remote-1"
        );
    }

    #[tokio::test]
    async fn replica_operation_client_and_server_round_trip_over_tcp() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            handle_steelsearch_replica_operation_connection(
                stream,
                OPENSEARCH_3_7_0_TRANSPORT,
                |request| {
                    assert_eq!(request.index, "logs-000001");
                    assert_eq!(request.shard_id, 0);
                    assert_eq!(request.target_node, "node-b");
                    assert_eq!(request.primary_node, "node-a");
                    assert_eq!(request.seq_no, 43);
                    assert_eq!(request.primary_term, 3);
                    assert_eq!(request.version, 7);
                    assert_eq!(request.global_checkpoint, 42);
                    assert_eq!(request.retention_leases.len(), 1);
                    assert_eq!(
                        request.operation.op_type,
                        SteelsearchReplicaOperationKindWire::Index
                    );
                    Ok(SteelsearchReplicaOperationResponseWire {
                        index: request.index,
                        shard_id: request.shard_id,
                        target_node: request.target_node,
                        seq_no: request.seq_no,
                        primary_term: request.primary_term,
                        version: request.version,
                        global_checkpoint: 43,
                        applied: true,
                        result: "updated".to_string(),
                        failure: None,
                    })
                },
            )
            .await
            .unwrap();
        });

        let response = send_steelsearch_replica_operation_request(
            address,
            43,
            OPENSEARCH_3_7_0_TRANSPORT,
            &SteelsearchReplicaOperationRequestWire {
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
                    source: Some(json!({ "message": "remote replica" })),
                    noop_reason: None,
                },
            },
        )
        .await
        .unwrap();

        server.await.unwrap();
        assert!(response.applied);
        assert_eq!(response.seq_no, 43);
        assert_eq!(response.global_checkpoint, 43);
    }

    #[tokio::test]
    async fn replica_operation_tcp_round_trip_preserves_replication_progress_metadata() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            handle_steelsearch_replica_operation_connection(
                stream,
                OPENSEARCH_3_7_0_TRANSPORT,
                |request| {
                    assert_eq!(request.seq_no, 128);
                    assert_eq!(request.primary_term, 9);
                    assert_eq!(request.global_checkpoint, 120);
                    assert_eq!(request.local_checkpoint, 123);
                    assert_eq!(request.retention_leases.len(), 2);
                    assert_eq!(request.retention_leases[0].id, "node-b");
                    assert_eq!(
                        request.retention_leases[0].retaining_sequence_number,
                        118
                    );
                    assert_eq!(request.retention_leases[1].id, "ccr");
                    assert_eq!(
                        request.retention_leases[1].retaining_sequence_number,
                        111
                    );
                    Ok(SteelsearchReplicaOperationResponseWire {
                        index: request.index,
                        shard_id: request.shard_id,
                        target_node: request.target_node,
                        seq_no: request.seq_no,
                        primary_term: request.primary_term,
                        version: request.version,
                        global_checkpoint: request.global_checkpoint,
                        applied: true,
                        result: "noop".to_string(),
                        failure: None,
                    })
                },
            )
            .await
            .unwrap();
        });

        let response = send_steelsearch_replica_operation_request(
            address,
            44,
            OPENSEARCH_3_7_0_TRANSPORT,
            &SteelsearchReplicaOperationRequestWire {
                index: "logs-000001".to_string(),
                shard_id: 0,
                target_node: "node-b".to_string(),
                primary_node: "node-a".to_string(),
                allocation_id: "alloc-b".to_string(),
                seq_no: 128,
                primary_term: 9,
                version: 21,
                global_checkpoint: 120,
                local_checkpoint: 123,
                retention_leases: vec![
                    SteelsearchRetentionLeaseWire {
                        id: "node-b".to_string(),
                        retaining_sequence_number: 118,
                        source: "peer_recovery".to_string(),
                        timestamp_millis: 1_700_000_000_100,
                    },
                    SteelsearchRetentionLeaseWire {
                        id: "ccr".to_string(),
                        retaining_sequence_number: 111,
                        source: "replication".to_string(),
                        timestamp_millis: 1_700_000_000_200,
                    },
                ],
                operation: SteelsearchReplicaOperationWire {
                    op_type: SteelsearchReplicaOperationKindWire::Noop,
                    id: "1".to_string(),
                    source: None,
                    noop_reason: Some("already applied on primary".to_string()),
                },
            },
        )
        .await
        .unwrap();

        server.await.unwrap();
        assert!(response.applied);
        assert_eq!(response.seq_no, 128);
        assert_eq!(response.primary_term, 9);
        assert_eq!(response.version, 21);
        assert_eq!(response.global_checkpoint, 120);
        assert_eq!(response.result, "noop");
    }

    #[test]
    fn mixed_cluster_write_replication_fail_closed_fixture_matches_validation_behavior() {
        let fixture: MixedClusterWriteReplicationFailClosedFixture = serde_json::from_str(
            include_str!("../../../tools/fixtures/mixed-cluster-write-replication-fail-closed.json"),
        )
        .expect("mixed-cluster write replication fail-closed fixture should deserialize");

        for case in fixture.cases {
            match case.kind.as_str() {
                "stale_primary_term" | "stale_seq_no" => {
                    let error = validate_replica_operation_request_progress(
                        case.request
                            .as_ref()
                            .expect("request case should include request"),
                        case.current_primary_term
                            .expect("request case should include current primary term"),
                        case.local_checkpoint
                            .expect("request case should include local checkpoint"),
                    )
                    .expect_err("stale request case should fail closed");
                    match (case.expected_error.as_str(), error) {
                        (
                            "stale_primary_term",
                            ReplicaReplicationValidationError::StalePrimaryTerm { .. },
                        ) => {}
                        ("stale_seq_no", ReplicaReplicationValidationError::StaleSeqNo { .. }) => {
                        }
                        (expected, actual) => {
                            panic!("unexpected request validation outcome: expected {expected}, got {actual:?}")
                        }
                    }
                }
                "partial_replication" => {
                    let error = validate_replica_operation_response(
                        case.response
                            .as_ref()
                            .expect("response case should include response"),
                    )
                    .expect_err("partial replication case should fail closed");
                    match (case.expected_error.as_str(), error) {
                        (
                            "partial_replication",
                            ReplicaReplicationValidationError::PartialReplication { .. },
                        ) => {}
                        (expected, actual) => {
                            panic!("unexpected response validation outcome: expected {expected}, got {actual:?}")
                        }
                    }
                }
                "unsupported_write_action" => {
                    let error = serde_json::from_value::<SteelsearchReplicaOperationRequestWire>(
                        case.request_json
                            .expect("unsupported action case should include raw request json"),
                    )
                    .expect_err("unsupported write action should fail decode");
                    assert!(
                        error.to_string().contains("unknown variant")
                            || error.to_string().contains("expected"),
                        "unexpected unsupported action decode error: {error}"
                    );
                    assert_eq!(case.expected_error, "unsupported_write_action");
                }
                other => panic!("unexpected fixture case kind: {other}"),
            }
            assert!(!case.name.is_empty());
        }
    }

    #[tokio::test]
    async fn shard_search_request_to_unavailable_node_returns_io_error() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        drop(listener);

        let error = send_steelsearch_shard_search_request(
            address,
            44,
            OPENSEARCH_3_7_0_TRANSPORT,
            &SteelsearchShardSearchRequestWire {
                parent_task_node: "coordinator".to_string(),
                parent_task_id: None,
                target: SearchShardTarget {
                    index: "logs-000001".to_string(),
                    shard: 0,
                    node: "node-a".to_string(),
                },
                request: SearchRequest {
                    indices: vec!["logs-000001".to_string()],
                    query: json!({ "match_all": {} }),
                    aggregations: json!({}),
                    sort: Vec::new(),
                    from: 0,
                    size: 10,
                },
            },
        )
        .await
        .unwrap_err();

        assert!(matches!(error, InternalTransportError::Io(_)));
    }
}
