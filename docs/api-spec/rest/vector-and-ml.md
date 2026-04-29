# Vector And ML REST Spec

This document covers k-NN and ML Commons-shaped REST surfaces.

## Semantic Summary

OpenSearch vector and ML features are partly core-like and partly plugin-like.
For Steelsearch they represent first-class extension surfaces rather than minor
search options.

## Current Steelsearch Position

- `knn_vector` mapping and `knn` query support exist for a supported subset.
- Selected `/_plugins/_knn/*` and `/_plugins/_ml/*` routes exist.
- Full plugin transport/runtime parity, authorization, and production isolation
  are still incomplete.

## Key Route Families

### k-NN

- vector field mappings
- `knn` query
- `/_plugins/_knn/stats`
- warmup / clear cache
- model get/delete/search/train

### ML Commons

- model groups
- register / deploy / undeploy
- predict / rerank / search
- task-oriented model lifecycle routes

## Replacement Gap

Useful for development replacement, not yet enough for production parity.
