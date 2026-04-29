# Steelsearch Production Security Baseline

This document defines the production security baseline for a standalone
Steelsearch cluster.

The current implementation is fail-closed. Production mode must not start until
every boundary below is implemented, enforced, tested, and accepted through the
readiness gate.

## Required Boundaries

Production security readiness requires all of these boundaries to be enforced:

- HTTP TLS;
- Steelsearch-native transport TLS;
- authentication;
- authorization;
- service accounts;
- role permissions;
- index permissions;
- audit logging;
- tenant isolation;
- secure settings;
- model connector secret handling;
- OpenSearch Security plugin API parity or an explicit fail-closed replacement
  decision.

`SecurityBoundaryPolicy::steelsearch_native_required()` is the default. It
marks every boundary as required and reports production blockers until the
boundary is moved to `Enforced`. `SecurityBoundaryPolicy::enforced()` exists
only for tests and future wiring after the actual enforcement code is present.

## Fail-Closed Rules

The daemon must fail closed in these cases:

- production mode is requested while any security boundary is not enforced;
- TLS or authentication is explicitly disabled outside development mode;
- secure settings or model connector secrets would be serialized into cluster
  metadata, REST responses, logs, snapshots, or migration manifests;
- OpenSearch Security plugin APIs are requested before a compatibility surface
  exists;
- authorization decisions cannot prove a subject has the required cluster,
  index, model, snapshot, or admin permission;
- audit logging cannot record an allowed or denied sensitive operation.

The readiness endpoint must expose these failures under the `security`
category, and production startup validation must include the same blockers.

## Access-Control Scope

The minimum authorization model must include:

- users and service accounts as authenticated subjects;
- roles with cluster permissions;
- roles with index permissions scoped by concrete index, alias, data stream, or
  pattern;
- explicit permissions for index admin, document CRUD, search, bulk, cluster
  admin, snapshots, k-NN operational routes, and ML Commons/model routes;
- tenant or namespace decisions for model metadata and future multi-tenant
  resources;
- deny-by-default behavior for unknown permissions, unknown resources, missing
  credentials, and malformed credentials.

Field-level and document-level security are not allowed to be silently ignored.
If they are not implemented, requests that require them must be rejected with an
OpenSearch-shaped security error.

## Secret Handling

Secrets are never ordinary cluster metadata.

Production secret handling must keep these values out of plaintext metadata,
logs, snapshots, readiness reports, and migration manifests:

- model connector credentials;
- repository credentials;
- TLS private keys;
- service account tokens;
- user password hashes or password-equivalent material;
- external provider tokens.

Secure settings must be loaded through a dedicated secret source with explicit
reload and redaction behavior. Redaction itself is part of the production gate.

## OpenSearch Security API Scope

OpenSearch Security plugin API parity is not currently implemented. Until it is
implemented, it remains a production blocker.

Supported future options are:

- implement compatible APIs under the OpenSearch Security plugin route shape;
- implement a Steelsearch-native security API and reject OpenSearch Security
  plugin APIs with documented, OpenSearch-shaped errors;
- support a migration-only translator for security metadata while keeping
  unsupported APIs fail-closed.

The selected option must be visible in `SecurityBoundaryPolicy` and the
readiness endpoint. Unsupported security APIs must not degrade to 404-only
ambiguity in production mode.

## Test Requirements

Production security is not complete until tests cover:

- valid and invalid HTTP TLS certificates;
- valid and invalid transport TLS certificates;
- expired certificates and hostname mismatch;
- insecure mode rejection when production mode is requested;
- successful authentication for users and service accounts;
- missing, malformed, expired, and revoked credentials;
- role and index permission allow/deny decisions;
- document CRUD, search, bulk, index admin, cluster admin, snapshot, k-NN, and
  ML Commons authorization checks;
- tenant isolation for model and namespace-scoped metadata;
- privilege escalation attempts;
- secret redaction in REST responses, logs, snapshots, and readiness reports;
- audit log entries for allowed and denied sensitive operations;
- production readiness and startup failures when any boundary is stubbed.

Existing production mode and readiness tests already assert that the daemon
blocks production until all security boundaries are enforced. They are baseline
tests, not proof that enforcement has been implemented.

## Operator Evidence

Before production cutover, attach this security evidence to the release record:

- readiness output with the security category ready;
- TLS certificate chain and rotation evidence;
- authn/authz test report;
- audit log sampling report;
- secret redaction test report;
- OpenSearch Security API compatibility or fail-closed decision record;
- list of accepted residual security risks.
