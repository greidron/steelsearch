# Security Redaction Baseline

This document defines the minimum redaction contract for secure standalone
runtime logs, error envelopes, config dumps, and compatibility harness output.
It is the source of truth for later grep-based smoke checks.

## Redaction Targets

The following values must never appear verbatim in logs, debug output, config
render dumps, or HTTP error bodies:

- basic-auth usernames and passwords from the secure harness env contract
- `Authorization` header values
- bearer tokens, API keys, session tokens, or refresh tokens
- private key material
- PEM payload bodies for CA, server, or client keys
- keystore/truststore passphrases
- raw cookie values used for authenticated sessions

## Allowed Versus Forbidden Output

| Surface | Allowed | Forbidden |
| --- | --- | --- |
| HTTP `401/403` error body | error type, generic reason, realm hint | raw credential values, header payloads, token strings |
| startup/bootstrap logs | file paths, enabled/disabled security flags, cert file locations | private key contents, passphrases, inline cert/key payloads |
| config dump / debug print | redacted placeholders, path references, boolean flags | resolved passwords, token env values, raw auth headers |
| audit/authn failure logs | username identifier if policy allows, route, status code, failure category | password, bearer token, basic-auth blob, cookie/session secret |
| compat harness stdout/report | credential env variable names, profile names, fixture paths | resolved secret values from env |

## Canonical Redaction Form

When a secret-bearing field must appear structurally, it should render in one
of these forms:

- `<redacted>`
- `***`
- field omitted entirely

The exact spelling may differ by subsystem, but the later smoke tests will only
accept output that does not leak the original secret.

## Grep-Based Smoke Expectations

Later smoke checks should fail if any of the following are found in captured
logs or rendered config/debug output:

- `Authorization: Basic `
- `Authorization: Bearer `
- `SECURITY_ADMIN_PASSWORD=`
- `SECURITY_READER_PASSWORD=`
- `SECURITY_WRITER_PASSWORD=`
- `BEGIN PRIVATE KEY`
- `BEGIN EC PRIVATE KEY`
- `BEGIN RSA PRIVATE KEY`
- raw token fixture values introduced by future authn tests

Current repo-local smoke entrypoint:

- `tools/check-security-redaction-smoke.sh <file-or-dir>...`

## Notes

- Username visibility is a policy decision; password/token visibility is not.
- File paths to cert/key material are allowed because operators need them for
  debugging bootstrap issues. File contents are not.
- If a future subsystem requires a narrower or stricter redaction policy, add
  it here before widening the smoke test harness.
