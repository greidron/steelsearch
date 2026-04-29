# Search REST Spec

This document covers search-facing REST APIs.

## Semantic Summary

Search parity requires more than a route existing. OpenSearch search semantics
span:

- Query DSL families;
- shard targeting and wildcard/alias resolution;
- search phases and fetch subphases;
- search response shaping;
- aggregation trees;
- PIT, scroll, search templates, suggesters, and advanced controls.

## Current Steelsearch Position

- Core `_search` routes exist.
- A selected Query DSL, aggregation, sort, pagination, alias/wildcard, and
  vector-search subset is implemented.
- Many advanced search features are still absent or explicitly fail-closed.

## Key Route Families

### Core search

- `GET /_search`
- `POST /_search`
- `GET /{index}/_search`
- `POST /{index}/_search`

### Advanced search families still missing or partial

- search templates
- PIT
- scroll
- suggest
- highlight
- rescore
- collapse
- explain
- profile
- stored fields / docvalue fields / runtime fields

## Replacement Gap

Search is one of the stronger parts of Steelsearch today, but it is still a
subset implementation relative to OpenSearch.
