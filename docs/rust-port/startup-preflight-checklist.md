# Startup Preflight Checklist

This document defines the minimum preflight checks that secure and non-secure
standalone runtime startup must perform before the node is considered safe to
join or serve traffic.

It is a checklist for later refusal tests, not a claim that every item below is
already implemented.

## Scope

Profiles covered:

- `standalone`
- `secure standalone`
- future multi-node bootstrap work, where the same checks must hold before a
  node joins cluster coordination

## Checklist

| Area | Check | Expected behavior on failure | Operator-visible evidence |
| --- | --- | --- | --- |
| Data path | data path exists | fail closed before startup | non-zero exit, stderr/log marker naming the missing path |
| Data path | data path writable | fail closed before startup | non-zero exit, stderr/log marker naming permission denial |
| Data path | exclusive lock obtainable | fail closed before startup | non-zero exit, stderr/log marker naming lock conflict |
| Node identity | duplicate node id / node metadata conflict | fail closed before startup | non-zero exit, stderr/log marker naming conflicting node identity |
| Config parse | malformed config file or env override | fail closed before startup | non-zero exit, parse-focused stderr/log marker |
| Config semantics | incompatible setting combination | fail closed before startup | non-zero exit, rejected-setting stderr/log marker |
| Network bind | HTTP port already in use | fail closed before startup | non-zero exit, bind/listen stderr/log marker |
| Network bind | transport port already in use | fail closed before startup | non-zero exit, bind/listen stderr/log marker |
| Network bind | malformed bind/publish address | fail closed before startup | non-zero exit, address-parse stderr/log marker |
| Security bootstrap | TLS/authn required material missing in secure profile | fail closed before startup | non-zero exit, stderr/log marker naming missing cert/key/credential input |
| Bootstrap mode | unsupported bootstrap/profile mode | fail closed before startup | non-zero exit, stderr/log marker naming unsupported mode |
| Runtime invariants | unsupported cluster/runtime setting presented at startup | fail closed before startup | non-zero exit, stderr/log marker naming unsupported setting |

## Test Decomposition Rules

Each checklist row should later become one or more runtime-backed cases with:

1. explicit setup condition;
2. expected exit code class;
3. expected stderr/log marker;
4. explicit statement that no partial startup or traffic-serving state was
   reached.

## Immediate Follow-up Cases

The next runtime/bootstrap tasks should derive cases from this checklist in the
following order:

1. data path absent / readonly / lock conflict;
2. duplicate node-id or persisted metadata conflict;
3. invalid config parse and incompatible setting combinations;
4. port-in-use and malformed bind address;
5. secure-profile missing TLS/authn material.

Current repo-local case fixture:

- [startup-preflight-failures.json](/home/ubuntu/steelsearch/tools/fixtures/startup-preflight-failures.json)

## Startup Ordering And Lifecycle Evidence

Preflight refusal checks are not sufficient on their own. Startup also needs an
ordering transcript so later runtime-backed tests can prove the node did not:

- bind transport before persisted state was loaded;
- bind HTTP before metadata apply completed;
- declare readiness after an ordering failure.

Current repo-local ordering artifacts:

- [startup-ordering-transcript.json](/home/ubuntu/steelsearch/tools/fixtures/startup-ordering-transcript.json)
- [check-startup-ordering-transcript.py](/home/ubuntu/steelsearch/tools/check-startup-ordering-transcript.py)

The canonical ordering contract for the transcript is:

1. gateway manifest load or `shared-runtime-state` load;
2. metadata apply;
3. service start;
4. transport bind;
5. HTTP bind.

The transcript must also fail closed when it detects:

- HTTP bind before metadata apply;
- transport bind before `shared-runtime-state` load;
- ready-state markers before bind completion;
- success markers after a startup-ordering failure.

## Current Refusal Evidence Matrix

| Case | Exit class | Expected stderr markers | Expected log markers |
| --- | --- | --- | --- |
| `data_path_missing` | `non-zero` | `data path`, `missing` | `startup preflight`, `data path` |
| `data_path_readonly` | `non-zero` | `data path`, `permission` | `startup preflight`, `readonly` |
| `data_path_locked` | `non-zero` | `lock`, `data path` | `startup preflight`, `lock conflict` |
| `duplicate_node_id` | `non-zero` | `node id`, `conflict` | `startup preflight`, `duplicate node` |
| `invalid_config_parse` | `non-zero` | `config`, `parse` | `startup preflight`, `config parse` |
| `incompatible_setting_combination` | `non-zero` | `setting`, `incompatible` | `startup preflight`, `rejected setting` |
| `http_port_in_use` | `non-zero` | `bind`, `port` | `startup preflight`, `http bind` |
| `malformed_bind_address` | `non-zero` | `address`, `bind` | `startup preflight`, `address parse` |
| `unsupported_cluster_setting` | `non-zero` | `unsupported`, `setting` | `startup preflight`, `unsupported setting` |
