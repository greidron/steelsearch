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

- Core `_search` routes are live and release-gated by the strict search and
  search-execution profiles.
- Query DSL, aggregation, response-shaping, scroll, PIT, and search execution
  controls documented in the main spec are implemented on the standalone
  surface.
- Remaining non-claims are later-phase semantics or Steelsearch-only
  extensions, not a development placeholder route.

## Key Route Families

### Core search

- `GET /_search`
- `POST /_search`
- `GET /{index}/_search`
- `POST /{index}/_search`

### Advanced search families still narrower than full OpenSearch

- search templates
- search templates
- broader mixed-cluster shard-phase semantics
- request-body `runtime_mappings` as OpenSearch parity

## Replacement Gap

Search is one of the stronger standalone replacement areas in Steelsearch
today. Remaining gaps are deeper OpenSearch semantics rather than missing route
family activation.
