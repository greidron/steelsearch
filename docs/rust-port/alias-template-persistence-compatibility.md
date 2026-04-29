# Alias and Template Persistence Compatibility

This note defines the live comparison fixture for alias and template registry
persistence. The canonical fixture is
`tools/fixtures/alias-template-persistence-compat.json`.

## Scope

The fixture covers the stable REST fields that Steelsearch now preserves across
development metadata reloads and snapshot restore:

- component template identity, template settings, mappings, aliases, version,
  and `_meta`;
- composable index template identity, `index_patterns`, `composed_of`,
  priority, version, template settings, aliases, and `_meta`;
- alias metadata applied by direct index creation;
- template-applied settings and aliases visible from `GET /{index}`;
- snapshot restore rehydrating the template registry and restored index
  metadata.

The fixture intentionally excludes OpenSearch internals that are not stable
across versions, such as cluster-state UUIDs, task IDs, shard allocation
details, and repository filesystem paths.

## Steelsearch Transcript

Run against a development node that was started with a development metadata
store and snapshot support:

```bash
BASE_URL="${STEELSEARCH_URL:-http://127.0.0.1:9200}"

curl -fsS -XPUT "$BASE_URL/_component_template/steelsearch-live-component" \
  -H 'content-type: application/json' \
  -d '{"version":7,"template":{"settings":{"index":{"number_of_shards":1}},"mappings":{"properties":{"component_field":{"type":"keyword"}}},"aliases":{"steelsearch-live-alias":{}}},"_meta":{"fixture":"alias-template-persistence-compat"}}'

curl -fsS -XPUT "$BASE_URL/_index_template/steelsearch-live-template" \
  -H 'content-type: application/json' \
  -d '{"index_patterns":["steelsearch-template-*"],"composed_of":["steelsearch-live-component"],"priority":501,"version":11,"template":{"settings":{"index":{"number_of_replicas":0}},"aliases":{"steelsearch-template-alias":{}}},"_meta":{"fixture":"alias-template-persistence-compat"}}'

curl -fsS -XPUT "$BASE_URL/steelsearch-template-000001" \
  -H 'content-type: application/json' \
  -d '{"aliases":{"steelsearch-write":{"is_write_index":true}}}'

curl -fsS "$BASE_URL/_component_template/steelsearch-live-component"
curl -fsS "$BASE_URL/_index_template/steelsearch-live-template"
curl -fsS "$BASE_URL/steelsearch-template-000001"
```

Expected stable fields:

```text
component_template[0].name=steelsearch-live-component
component_template[0].component_template.version=7
index_template[0].name=steelsearch-live-template
index_template[0].index_template.index_patterns=["steelsearch-template-*"]
index_template[0].index_template.composed_of=["steelsearch-live-component"]
steelsearch-template-000001.aliases.steelsearch-live-alias={}
steelsearch-template-000001.aliases.steelsearch-template-alias={}
steelsearch-template-000001.aliases.steelsearch-write.is_write_index=true
steelsearch-template-000001.settings.index.number_of_shards=1
steelsearch-template-000001.settings.index.number_of_replicas=0
```

Restart parity check:

```bash
# Stop and restart the same Steelsearch node using the same development
# metadata path, then rerun:
curl -fsS "$BASE_URL/_component_template/steelsearch-live-component"
curl -fsS "$BASE_URL/_index_template/steelsearch-live-template"
curl -fsS "$BASE_URL/steelsearch-template-000001"
```

The stable fields above must be unchanged.

Snapshot restore parity check:

```bash
curl -fsS -XPUT "$BASE_URL/_snapshot/steelsearch-persistence-repo/steelsearch-template-snapshot"
curl -fsS -XDELETE "$BASE_URL/_index_template/steelsearch-live-template"
curl -fsS -XDELETE "$BASE_URL/steelsearch-template-000001"
curl -fsS -XPOST "$BASE_URL/_snapshot/steelsearch-persistence-repo/steelsearch-template-snapshot/_restore"
curl -fsS "$BASE_URL/_index_template/steelsearch-live-template"
curl -fsS "$BASE_URL/steelsearch-template-000001"
```

After restore, the stable index template and index fields must match the
pre-snapshot values.

## OpenSearch Transcript

OpenSearch requires a registered filesystem repository before the snapshot
steps. The repository location must be allowed by `path.repo`.

```bash
OS_URL="${OPENSEARCH_URL:-http://127.0.0.1:9200}"
SNAPSHOT_LOCATION="${OPENSEARCH_SNAPSHOT_LOCATION:-/tmp/steelsearch-persistence-repo}"

curl -fsS -XPUT "$OS_URL/_snapshot/steelsearch-persistence-repo" \
  -H 'content-type: application/json' \
  -d "{\"type\":\"fs\",\"settings\":{\"location\":\"$SNAPSHOT_LOCATION\"}}"
```

Then run the same fixture requests from
`tools/fixtures/alias-template-persistence-compat.json`. Compare only the
stable fields listed above. OpenSearch may return additional fields, defaulted
settings, or different acknowledgement timing fields; those are intentionally
outside this fixture.

## Validation Status

Steelsearch unit coverage:

```bash
cargo test -p os-node development_metadata_store_persists_template_registries
cargo test -p os-node development_snapshot_restore_restores_template_registries
```

Live OpenSearch comparison remains opt-in because it requires an external
OpenSearch node with `path.repo` configured. The fixture is intended to be wired
into `tools/run-opensearch-compare.sh` when that environment is present.
