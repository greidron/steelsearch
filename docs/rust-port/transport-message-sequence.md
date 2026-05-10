# OpenSearch Transport Message Sequence

This document fixes the required OpenSearch transport-layer message order for
Steelsearch interoperability work. The transport is a custom binary protocol
over TCP, not HTTP, REST, or gRPC.

## Source Baseline

The contract below is derived from the OpenSearch Java transport source:

- `TcpTransport`: validates the first six bytes, requires marker `ES`, rejects
  HTTP/TLS-looking traffic on the transport port, and treats message length `-1`
  as ping.
- `TcpHeader`: writes the fixed transport envelope.
- `TransportHandshaker`: owns low-level `internal:tcp/handshake`.
- `TransportService`: owns high-level `internal:transport/handshake`.
- `InboundDecoder`: parses fixed header, variable header, compatibility gates,
  and request/response dispatch metadata.

## Transport Endpoint

OpenSearch node-to-node transport runs on TCP. The common default port is
`9300/tcp`, but deployments may configure a different `transport.port`.

The HTTP REST port, commonly `9200/tcp`, is not valid for this protocol.
OpenSearch explicitly detects HTTP request/response prefixes on the transport
port and rejects them.

## Frame Envelope

Every non-ping transport message starts with this fixed envelope:

```text
2 bytes   marker: "ES"
4 bytes   message length, excluding marker and length fields
8 bytes   request id
1 byte    status
4 bytes   version id
4 bytes   variable header size
N bytes   variable header
M bytes   request or response body
```

`TcpHeader.writeHeader()` computes message length as:

```text
content_size + request_id_size + status_size + version_id_size + variable_header_size_field_size
```

That means the length includes the fixed fields after the length integer and the
variable header/body, but excludes the leading `ES` marker and the length field
itself.

## Status Byte

The OpenSearch status byte carries the dispatch class:

```text
bit 0  request/response; unset=request, set=response
bit 1  error response
bit 2  compressed body
bit 3  handshake
```

Handshake frames must set the handshake bit. Response frames must preserve the
request id from the corresponding request and set the response bit.

## Variable Header

Requests carry:

```text
thread context request headers
thread context response headers
string array: features
string: action name
```

Responses carry:

```text
thread context response headers
```

Therefore action names such as `internal:tcp/handshake` and
`internal:transport/handshake` exist in the request variable header, not in the
fixed header.

## Ping / Keepalive

Ping is a special six-byte frame:

```text
45 53 ff ff ff ff
 E  S  -1
```

It has no request id, status, version, variable header, or body. The current
Steelsearch Rust constant still uses `ES + 0`; that is an implementation delta
to fix before claiming keepalive parity.

## Required Message Order: OpenSearch Initiates Connection To Steelsearch

This is the critical mixed-node path when a Java OpenSearch node discovers a
Steelsearch transport address.

```text
1. Java opens TCP connection to Steelsearch transport port.
2. Java sends request action internal:tcp/handshake.
3. Steelsearch decodes the frame and exhausts the HandshakeRequest body.
4. Steelsearch sends a response on the same TCP connection:
   same request id,
   response bit set,
   handshake bit set,
   body = remote Version.
5. Steelsearch keeps the channel open.
6. Java decodes the low-level response and checks version compatibility.
7. Java sends high-level action internal:transport/handshake on a connected
   transport channel.
8. Steelsearch responds with:
   optional DiscoveryNode,
   ClusterName,
   Version.
9. Java validates cluster name and version compatibility.
10. Java promotes the connection into node-level transport connection state.
11. Java may send discovery/coordination actions over the connected profile.
```

Step 5 matters. A valid handshake response followed by an immediate local close
can still fail connection establishment because Java attaches close listeners to
the channel and maps close-before-settle to connection failure.

## Required Message Order: Steelsearch Initiates Connection To OpenSearch

When Steelsearch acts as the outbound client, the same contract applies with
roles reversed:

```text
1. Steelsearch opens TCP connection to Java OpenSearch transport port.
2. Steelsearch sends internal:tcp/handshake with the minimum compatible version
   in the request body.
3. Java responds with internal:tcp/handshake response body = Java node Version.
4. Steelsearch validates version compatibility.
5. Steelsearch sends internal:transport/handshake.
6. Java responds with DiscoveryNode, ClusterName, and Version.
7. Steelsearch validates identity and cluster compatibility.
8. Only then may Steelsearch send higher-level transport actions.
```

## Low-Level Handshake Contract

Action:

```text
internal:tcp/handshake
```

Java request body:

```text
TransportRequest base fields
BytesReference containing Version
```

Java response body:

```text
TransportResponse base fields
Version
```

The low-level handshake does not carry node identity. It only proves that the
peer can parse the transport envelope and speaks a compatible version.

## High-Level Handshake Contract

Action:

```text
internal:transport/handshake
```

Java request body:

```text
TransportRequest base fields
```

Java response body:

```text
optional DiscoveryNode
ClusterName
Version
```

This is the identity handshake. Java rejects the connection if the returned
cluster name does not match the local cluster predicate or if the returned
version is incompatible with the local node version.

## Expected Post-Handshake Action Families

After both handshakes succeed, there is no single globally fixed action order.
OpenSearch may open several channels per node and dispatch actions based on the
connection profile and coordination state. In mixed membership traces, the
important action families are:

```text
internal:discovery/request_peers
internal:cluster/request_pre_vote
internal:cluster/coordination/start_join
internal:cluster/coordination/join
internal:cluster/coordination/join/validate
internal:coordination/fault_detection/follower_check
internal:cluster/coordination/publish_state
internal:cluster/coordination/commit_state
```

These actions are not substitutes for either handshake. They are only valid
after the connection has passed the transport handshake sequence and entered
node-level connection management.

## Current Mixed-Node Interpretation

The current investigation should be read against this sequence:

```text
Java -> Steelsearch: internal:tcp/handshake request
Steelsearch -> Java: internal:tcp/handshake response
Java native/JDK read observes response bytes
Java Netty/transport response dispatch markers are not reached in the failing run
```

This means the direct symptom is after Steelsearch writes the low-level response
and before Java completes response dispatch. It does not by itself prove that the
wire response is semantically valid; it narrows the next useful check to
byte-for-byte frame shape, channel lifecycle, and Java read-to-Netty dispatch
boundary.

## Compatibility Checklist

Steelsearch must satisfy all of these before claiming OpenSearch transport
interoperability:

- Use TCP transport port, not HTTP port.
- Emit `ES` marker and correct message length semantics.
- Use ping frame `ES ff ff ff ff`.
- Preserve request id in responses.
- Set response and handshake status bits correctly.
- Encode variable headers exactly as Java expects for request vs response.
- Distinguish `internal:tcp/handshake` from `internal:transport/handshake`.
- Keep handshake channels open long enough for Java connection settlement.
- Support multiple simultaneous transport channels per node profile.
- Fail closed on unsupported version, malformed frame, unknown required action,
  or undecodable identity payload.

## Immediate Follow-Up Items

- Fix Steelsearch `PING_FRAME` from `ES + 0` to `ES + -1`.
- Capture a Java-Java reference pair for both handshake actions and compare
  Steelsearch response bytes field-by-field.
- Keep separating low-level response validity from channel-retention and
  Java-side dispatch timing; they are different failure classes.
