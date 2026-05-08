# Java primary <-> Rust replica actual run runbook

## 목적

`java-primary-rust-replica` profile의 실제 mixed-cluster 실행 증거를 수집한다.

이 runbook은 다음 두 경로를 대상으로 한다.

- success path:
  - single-doc CRUD
  - `_bulk`
  - refresh 후 readback
  - recovery/restart 이후 readback
- negative path:
  - `decode_mismatch`
  - `apply_mismatch`
  - `checkpoint_mismatch`

## 전제 조건

- 같은 cluster에 Java/OpenSearch node와 Rust/Steelsearch node가 모두 참여하고 있어야 한다.
- coordinator HTTP endpoint 하나로 cluster 전체에 접근 가능해야 한다.
- shard 배치는 아래를 만족해야 한다.
  - primary shard node = Java node
  - replica shard node = Rust node
- 실행자는 다음 값을 알고 있어야 한다.
  - `CLUSTER_URL`
  - `JAVA_NODE`
  - `RUST_NODE`

## success path 실행

기본 실행 순서:

```bash
bash tools/run-java-mixed-cluster-binary-harness.sh \
  --profile java-primary-rust-replica \
  --report-dir target/java-mixed-cluster-binary \
  --prepare-cmd "python3 tools/run_java_primary_rust_replica_actual.py --cluster-url ${CLUSTER_URL} --index mixed-java-success-000001 --java-node ${JAVA_NODE} --rust-node ${RUST_NODE} --state-dir target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state prepare" \
  --write-cmd "python3 tools/run_java_primary_rust_replica_actual.py --cluster-url ${CLUSTER_URL} --index mixed-java-success-000001 --java-node ${JAVA_NODE} --rust-node ${RUST_NODE} --state-dir target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state write" \
  --read-cmd "python3 tools/run_java_primary_rust_replica_actual.py --cluster-url ${CLUSTER_URL} --index mixed-java-success-000001 --java-node ${JAVA_NODE} --rust-node ${RUST_NODE} --state-dir target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state read" \
  --recover-cmd ":" \
  --restart-cmd ":" \
  --check-cmd "python3 tools/run_java_primary_rust_replica_actual.py --cluster-url ${CLUSTER_URL} --index mixed-java-success-000001 --java-node ${JAVA_NODE} --rust-node ${RUST_NODE} --state-dir target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state check"
```

## negative path 실행

negative path는 recipe wrapper를 사용한다.

### decode mismatch

```bash
bash tools/run_java_primary_rust_replica_negative_recipe.sh \
  --cluster-url "${CLUSTER_URL}" \
  --java-node "${JAVA_NODE}" \
  --rust-node "${RUST_NODE}" \
  --fault-class decode_mismatch \
  --report-dir target/java-primary-rust-negative
```

### apply mismatch

```bash
bash tools/run_java_primary_rust_replica_negative_recipe.sh \
  --cluster-url "${CLUSTER_URL}" \
  --java-node "${JAVA_NODE}" \
  --rust-node "${RUST_NODE}" \
  --fault-class apply_mismatch \
  --report-dir target/java-primary-rust-negative
```

### checkpoint mismatch

```bash
bash tools/run_java_primary_rust_replica_negative_recipe.sh \
  --cluster-url "${CLUSTER_URL}" \
  --java-node "${JAVA_NODE}" \
  --rust-node "${RUST_NODE}" \
  --fault-class checkpoint_mismatch \
  --report-dir target/java-primary-rust-negative
```

## 필수 artifact

success path에서 최소 다음 artifact가 있어야 한다.

- `target/java-mixed-cluster-binary/java-primary-rust-replica/report.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/prepare.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/write.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/read.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/phase-artifacts/check.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/check-stats.json`
- `target/java-mixed-cluster-binary/java-primary-rust-replica/runtime-state/read-search.json`

negative path에서 최소 다음 artifact가 있어야 한다.

- `target/java-primary-rust-negative/java-primary-rust-replica/report.json`
- `target/java-primary-rust-negative/java-primary-rust-replica/phase-artifacts/check.json`

## 성공 판정

- success path
  - `artifact_source = actual-phase-artifacts`
  - `divergence_classification = none`
  - `placement_observed.java_primary = true`
  - `placement_observed.rust_replica = true`
- negative path
  - requested `fault_class`와 `divergence_classification`가 일치해야 한다.

## 실패 시 우선 확인 항목

- primary/replica 배치가 원하는 node에 올라갔는지
- `read-search.json`에 expected doc id 3개가 모두 있는지
- `check-stats.json`의 `seq_no` block이 shard level로 채워졌는지
- `phase-artifacts/check.json`의 `observed_failure_classes`가 requested fault와 일치하는지
