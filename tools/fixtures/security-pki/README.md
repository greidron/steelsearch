# Security PKI Fixture Layout

This directory fixes the repo-local layout for self-signed test PKI material
used by the secure standalone and secure multi-node harnesses.

Purpose:

- keep certificate/key locations stable across local and CI runs;
- separate CA, server, and client material by role;
- let later bootstrap tasks wire concrete filenames without inventing new
  paths.

Directory contract:

- `ca/`
  - self-signed test certificate authority material
  - expected later filenames:
    - `ca.crt`
    - `ca.key`
- `server/single-node-secure/`
  - single-node HTTP/transport test server certificates
  - expected later filenames:
    - `http.crt`
    - `http.key`
    - `transport.crt`
    - `transport.key`
- `server/multi-node-secure/`
  - multi-node server certificate root
  - later tasks may add node-specific subdirectories such as `node-1/`,
    `node-2/`, `node-3/`
- `client/admin/`
  - privileged admin client test credentials
- `client/reader/`
  - least-privilege read-only client test credentials
- `client/writer/`
  - bounded write-role client test credentials

Boundary:

- no real private material is committed here in the current phase;
- placeholder files only establish path ownership;
- later tasks will decide generation flow, filename exactness, and whether the
  credentials are ephemeral or checked in for CI-only use.
