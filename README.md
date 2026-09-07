# SteelSearch

SteelSearch is an experimental Rust implementation of an OpenSearch-compatible node.

The project starts from protocol and behavior compatibility rather than a direct
line-by-line Java port. The near-term target is to interoperate with Java
OpenSearch at the transport and cluster-state boundary, while developing a
Rust-native storage and search engine behind a stable engine abstraction.

See `docs/rust-port/` for the working architecture and milestone plan.

All new releases must follow the [release notes and performance policy](docs/releases/README.md),
including scenario-level comparisons against the previous release and OpenSearch.
