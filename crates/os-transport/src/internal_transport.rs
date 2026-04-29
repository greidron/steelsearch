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
    use serde_json::json;
    use tokio::net::TcpListener;

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
}
