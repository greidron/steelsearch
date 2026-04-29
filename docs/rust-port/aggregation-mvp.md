# Aggregation MVP

The first aggregation subset is `terms`.

## Supported Shape

Steelsearch should initially accept the OpenSearch request shape below:

```json
{
  "aggs": {
    "by_service": {
      "terms": {
        "field": "service",
        "size": 10
      }
    }
  }
}
```

`aggregations` is accepted as an alias for `aggs`.

## Field Scope

The MVP evaluates terms buckets from scalar `_source` values only:

- strings, including `keyword` fields
- booleans
- integer and floating point numbers

Arrays, objects, missing fields, scripts, runtime fields, sub-aggregations,
ordering options, include/exclude filters, and shard-size behavior are deferred.

## Response Shape

The response should preserve the OpenSearch bucket shape:

```json
{
  "aggregations": {
    "by_service": {
      "buckets": [
        {
          "key": "api",
          "doc_count": 3
        }
      ]
    }
  }
}
```

Buckets are sorted by `doc_count` descending, then key ascending for stable MVP
behavior. `size` defaults to 10.

## Execution Semantics

Aggregation collection runs after the query filter and before `from`/`size`
pagination, matching the normal OpenSearch expectation that aggregations see
the full query result set rather than only the returned hits page.
