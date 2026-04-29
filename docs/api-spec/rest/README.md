# REST API Spec

This directory contains human-written REST API specifications grouped by
OpenSearch-facing meaning rather than by source file.

Each document should answer:

- what the API family means in OpenSearch;
- what Steelsearch currently implements;
- what remains missing for parity.

## Documents

- [root-cluster-node.md](./root-cluster-node.md)
- [index-and-metadata.md](./index-and-metadata.md)
- [document-and-bulk.md](./document-and-bulk.md)
- [search.md](./search.md)
- [vector-and-ml.md](./vector-and-ml.md)
- [snapshot-migration-interop.md](./snapshot-migration-interop.md)

## Generated References

For exhaustive route and action inventories generated from the source-derived
TSV files, see:

- [Generated REST Route Reference](../generated/rest-routes.md)
- [Generated Transport Action Reference](../generated/transport-actions.md)
