# OpenSearch Snapshot Import Policy

This document defines the boundary between Steelsearch-native snapshots and
OpenSearch snapshot import.

## Decision

Direct OpenSearch snapshot import is not a replacement gate for the first
standalone Steelsearch cluster.

Steelsearch snapshots are a native backup and restore format for
Steelsearch-owned shard stores. OpenSearch snapshots are a migration input only
when an explicit translation path exists. A Java OpenSearch snapshot repository
must not be treated as directly restorable into the Rust-native Tantivy store.

The supported replacement gate is:

- create, delete, cleanup, verify, status, and restore Steelsearch-native
  snapshots;
- migrate existing OpenSearch data through scroll/PIT export plus `_bulk`
  import, with mappings/settings/templates/aliases translated explicitly;
- fail closed for direct OpenSearch snapshot constructs that Steelsearch cannot
  validate or convert.

## Native Snapshot Boundary

Steelsearch-native snapshots cover data that was written by Steelsearch and
stored in the Steelsearch shard format.

Native snapshot restore may assume:

- Steelsearch metadata manifests;
- Steelsearch mapping and schema hashes;
- Steelsearch shard manifests;
- Tantivy segment files and Steelsearch operation-history metadata;
- Steelsearch repository metadata and verification state.

Native restore must validate:

- snapshot metadata format version;
- cluster UUID and index metadata compatibility;
- shard manifest checksum and length;
- mapping/schema hash compatibility;
- replayed or stale deletion and cleanup markers.

If any of those validations fail, restore must return an OpenSearch-shaped
error and leave the live cluster metadata unchanged.

## Migration-Only OpenSearch Translation

OpenSearch snapshot input may be supported only as an offline or migration-only
translation flow. That flow is separate from native restore.

Allowed migration shape:

1. Read OpenSearch metadata and identify indices, aliases, templates, data
   streams, mappings, settings, and repository layout.
2. Reject unsupported metadata before moving any data.
3. Export documents through OpenSearch APIs when possible: scroll, PIT, sliced
   search, or reindex-from-remote style reads.
4. Translate supported mappings/settings into Steelsearch-compatible mappings
   and settings.
5. Import through Steelsearch `_bulk` with checkpoints, retries, idempotency
   guards, and post-import validation.
6. Validate document counts, sampled documents, vector dimensions, aliases,
   templates, and search compatibility before cutover.

Optional offline translation can be considered later, but it still must produce
Steelsearch-native manifests and shard data. It must not bypass the native
restore validation path.

## Unsupported Direct-Import Constructs

Direct import from an OpenSearch snapshot repository is unsupported when it
requires any of the following:

- opening Lucene shard segment files as Steelsearch/Tantivy segments;
- accepting OpenSearch translog files as Steelsearch operation history;
- trusting OpenSearch commit metadata, history UUIDs, retention leases, or
  sequence-number state without conversion;
- restoring remote-store segment or translog metadata directly;
- restoring searchable snapshots directly;
- restoring snapshot-based shrink, split, clone, or local-shards state without
  Steelsearch-native reconstruction;
- restoring repository plugin metadata for S3, GCS, Azure, HDFS, or custom
  repositories without a Steelsearch repository implementation;
- restoring custom metadata, security metadata, ingest/search pipelines,
  scripts, model metadata, k-NN native engine metadata, or plugin-owned state
  without a typed compatibility rule;
- translating analyzer, tokenizer, normalizer, similarity, runtime-field,
  nested, parent/child, geo, or vector behavior without explicit validation;
- replaying snapshot deletion, cleanup, or partial-finalization state as if it
  were a completed Steelsearch snapshot.

Any such construct must be rejected before import or routed through an explicit
migration translator with its own compatibility evidence.

## Why Direct Import Is Not A Replacement Gate

OpenSearch snapshots are coupled to Lucene store files, OpenSearch commit and
translog metadata, repository plugin behavior, and cluster metadata owned by
OpenSearch and its plugins. Steelsearch's first replacement target uses a
Rust-native store and Steelsearch-native metadata. Matching the REST snapshot
API shape is not the same as being able to safely restore OpenSearch snapshot
bytes.

Making direct OpenSearch snapshot import a first replacement gate would require
one of these larger projects:

- a Lucene-compatible store layer;
- a JVM bridge that can open and validate OpenSearch/Lucene shard data;
- an offline converter that rewrites OpenSearch snapshots into
  Steelsearch-native snapshots;
- a dual-format repository and metadata compatibility layer for core and plugin
  state.

Those projects are useful future compatibility tracks, but they are not required
for a standalone Steelsearch cluster that accepts migration through APIs and
then owns its data natively.

## Acceptance Criteria

Native snapshot compatibility is sufficient for the standalone replacement
milestone when:

- Steelsearch can create and restore its own snapshots after restart;
- interrupted create, restore, delete, and cleanup operations fail closed;
- corrupt manifests, missing shard files, checksum mismatches, stale metadata,
  and incompatible mappings are rejected;
- migration tooling can move OpenSearch data into Steelsearch with resumable
  checkpoints and validation.

Direct OpenSearch snapshot import can be reopened only after a dedicated design
chooses a Lucene/JVM bridge, offline converter, or compatible store layer and
adds tests proving the chosen path can reject unsupported repository and plugin
state.
