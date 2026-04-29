//! Snapshot and repository state surface for Steelsearch.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotService {
    repositories: BTreeMap<String, RepositoryMetadata>,
    snapshots: BTreeMap<SnapshotKey, SnapshotMetadata>,
    shard_snapshots: BTreeMap<SnapshotShardKey, SnapshotShardMetadata>,
    restores: BTreeMap<String, RestoreMetadata>,
    next_uuid: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryMetadata {
    pub name: String,
    pub repository_type: RepositoryType,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub settings: BTreeMap<String, Value>,
    pub verified: bool,
    pub generation: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RepositoryType {
    Fs,
    Url,
    S3,
    Gcs,
    Azure,
    Custom(String),
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PutRepositoryRequest {
    pub name: String,
    pub repository_type: RepositoryType,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub settings: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RepositoryVerification {
    pub repository: String,
    pub verified: bool,
    pub generation: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct FilesystemRepositoryLayout {
    pub repository: String,
    pub root: PathBuf,
    pub snapshots_dir: PathBuf,
    pub indices_dir: PathBuf,
    pub metadata_file: PathBuf,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CloudRepositoryDescriptor {
    pub repository: String,
    pub provider: RepositoryType,
    pub bucket: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub base_path: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub region: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Serialize, Deserialize)]
pub struct SnapshotKey {
    pub repository: String,
    pub snapshot: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotMetadata {
    pub repository: String,
    pub snapshot: String,
    pub uuid: String,
    pub state: SnapshotState,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub indices: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cloned_from: Option<SnapshotKey>,
    pub shard_stats: SnapshotShardStats,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub failures: Vec<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SnapshotState {
    InProgress,
    Success,
    Failed,
    Deleted,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotShardStats {
    pub total: u32,
    pub successful: u32,
    pub failed: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Serialize, Deserialize)]
pub struct SnapshotShardKey {
    pub repository: String,
    pub snapshot: String,
    pub index: String,
    pub shard_id: u32,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotShardMetadata {
    pub key: SnapshotShardKey,
    pub primary_term: u64,
    pub max_seq_no: u64,
    pub local_checkpoint: u64,
    pub commit_generation: u64,
    pub translog_generation: u64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub segment_files: Vec<SnapshotFileMetadata>,
    pub commit_safe: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotFileMetadata {
    pub name: String,
    pub length: u64,
    pub checksum: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotShardMetadataRequest {
    pub repository: String,
    pub snapshot: String,
    pub index: String,
    pub shard_id: u32,
    pub primary_term: u64,
    pub max_seq_no: u64,
    pub local_checkpoint: u64,
    pub commit_generation: u64,
    pub translog_generation: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SegmentFileCopyRequest {
    pub repository: String,
    pub snapshot: String,
    pub index: String,
    pub shard_id: u32,
    pub source_path: PathBuf,
    pub file_name: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreAllocationRequest {
    pub repository: String,
    pub snapshot: String,
    pub index: String,
    pub shard_count: u32,
    pub candidate_nodes: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreShardAllocation {
    pub index: String,
    pub shard_id: u32,
    pub node_id: String,
    pub primary: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CreateSnapshotRequest {
    pub repository: String,
    pub snapshot: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub indices: Vec<String>,
    #[serde(default)]
    pub wait_for_completion: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DeleteSnapshotRequest {
    pub repository: String,
    pub snapshot: String,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CloneSnapshotRequest {
    pub repository: String,
    pub source_snapshot: String,
    pub target_snapshot: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub indices: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreSnapshotRequest {
    pub repository: String,
    pub snapshot: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub indices: Vec<String>,
    #[serde(default)]
    pub wait_for_completion: bool,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestoreMetadata {
    pub restore_id: String,
    pub repository: String,
    pub snapshot: String,
    pub state: RestoreState,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub indices: Vec<String>,
    pub shard_stats: SnapshotShardStats,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RestoreState {
    InProgress,
    Success,
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct SnapshotStatus {
    pub snapshot: SnapshotMetadata,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub restore: Option<RestoreMetadata>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct CleanupRepositoryResponse {
    pub repository: String,
    pub removed_snapshots: u64,
    pub remaining_snapshots: u64,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum SnapshotError {
    RepositoryAlreadyExists(String),
    RepositoryNotFound(String),
    RepositoryNotVerified(String),
    SnapshotAlreadyExists(SnapshotKey),
    SnapshotNotFound(SnapshotKey),
    RestoreNotFound(String),
    InvalidRequest(String),
    Io(String),
}

impl fmt::Display for SnapshotError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RepositoryAlreadyExists(name) => {
                write!(formatter, "repository [{name}] already exists")
            }
            Self::RepositoryNotFound(name) => write!(formatter, "repository [{name}] not found"),
            Self::RepositoryNotVerified(name) => {
                write!(formatter, "repository [{name}] is not verified")
            }
            Self::SnapshotAlreadyExists(key) => write!(
                formatter,
                "snapshot [{}/{}] already exists",
                key.repository, key.snapshot
            ),
            Self::SnapshotNotFound(key) => write!(
                formatter,
                "snapshot [{}/{}] not found",
                key.repository, key.snapshot
            ),
            Self::RestoreNotFound(id) => write!(formatter, "restore [{id}] not found"),
            Self::InvalidRequest(reason) => write!(formatter, "invalid snapshot request: {reason}"),
            Self::Io(reason) => write!(formatter, "snapshot repository IO error: {reason}"),
        }
    }
}

impl std::error::Error for SnapshotError {}

impl SnapshotService {
    pub fn put_repository(
        &mut self,
        request: PutRepositoryRequest,
    ) -> Result<RepositoryMetadata, SnapshotError> {
        validate_name("repository", &request.name)?;
        if self.repositories.contains_key(&request.name) {
            return Err(SnapshotError::RepositoryAlreadyExists(request.name));
        }

        let repository = RepositoryMetadata {
            name: request.name.clone(),
            repository_type: request.repository_type,
            settings: request.settings,
            verified: false,
            generation: 1,
        };
        self.repositories.insert(request.name, repository.clone());
        Ok(repository)
    }

    pub fn delete_repository(&mut self, name: &str) -> Result<RepositoryMetadata, SnapshotError> {
        self.repositories
            .remove(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))
    }

    pub fn verify_repository(
        &mut self,
        name: &str,
    ) -> Result<RepositoryVerification, SnapshotError> {
        let repository = self
            .repositories
            .get(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))?;
        match repository.repository_type {
            RepositoryType::Fs => {
                build_filesystem_repository_layout(repository)?;
            }
            RepositoryType::S3 | RepositoryType::Gcs | RepositoryType::Azure => {
                build_cloud_repository_descriptor(repository)?;
            }
            RepositoryType::Url | RepositoryType::Custom(_) => {}
        }

        let repository = self
            .repositories
            .get_mut(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))?;
        repository.verified = true;
        repository.generation += 1;
        Ok(RepositoryVerification {
            repository: name.to_string(),
            verified: true,
            generation: repository.generation,
        })
    }

    pub fn prepare_filesystem_repository(
        &self,
        name: &str,
    ) -> Result<FilesystemRepositoryLayout, SnapshotError> {
        let repository = self
            .repositories
            .get(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))?;
        let layout = build_filesystem_repository_layout(repository)?;
        std::fs::create_dir_all(&layout.snapshots_dir)
            .map_err(|error| SnapshotError::Io(error.to_string()))?;
        std::fs::create_dir_all(&layout.indices_dir)
            .map_err(|error| SnapshotError::Io(error.to_string()))?;
        std::fs::write(
            &layout.metadata_file,
            format!("repository={}\n", repository.name),
        )
        .map_err(|error| SnapshotError::Io(error.to_string()))?;
        Ok(layout)
    }

    pub fn cloud_repository_descriptor(
        &self,
        name: &str,
    ) -> Result<CloudRepositoryDescriptor, SnapshotError> {
        let repository = self
            .repositories
            .get(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))?;
        build_cloud_repository_descriptor(repository)
    }

    pub fn create_snapshot(
        &mut self,
        request: CreateSnapshotRequest,
    ) -> Result<SnapshotMetadata, SnapshotError> {
        self.ensure_verified_repository(&request.repository)?;
        validate_name("snapshot", &request.snapshot)?;
        let key = SnapshotKey {
            repository: request.repository.clone(),
            snapshot: request.snapshot.clone(),
        };
        if self.snapshots.contains_key(&key) {
            return Err(SnapshotError::SnapshotAlreadyExists(key));
        }

        let state = if request.wait_for_completion {
            SnapshotState::Success
        } else {
            SnapshotState::InProgress
        };
        let shard_stats =
            completed_or_started_stats(request.indices.len(), request.wait_for_completion);
        let snapshot = SnapshotMetadata {
            repository: request.repository,
            snapshot: request.snapshot,
            uuid: self.next_snapshot_uuid(),
            state,
            indices: request.indices,
            cloned_from: None,
            shard_stats,
            failures: Vec::new(),
        };
        self.snapshots.insert(key, snapshot.clone());
        Ok(snapshot)
    }

    pub fn delete_snapshot(
        &mut self,
        request: DeleteSnapshotRequest,
    ) -> Result<SnapshotMetadata, SnapshotError> {
        let key = SnapshotKey {
            repository: request.repository,
            snapshot: request.snapshot,
        };
        let snapshot = self
            .snapshots
            .get(&key)
            .ok_or_else(|| SnapshotError::SnapshotNotFound(key.clone()))?;
        let mut deleted = snapshot.clone();
        deleted.state = SnapshotState::Deleted;
        self.snapshots.insert(key, deleted.clone());
        Ok(deleted)
    }

    pub fn clone_snapshot(
        &mut self,
        request: CloneSnapshotRequest,
    ) -> Result<SnapshotMetadata, SnapshotError> {
        self.ensure_verified_repository(&request.repository)?;
        validate_name("snapshot", &request.target_snapshot)?;
        let source_key = SnapshotKey {
            repository: request.repository.clone(),
            snapshot: request.source_snapshot.clone(),
        };
        let source = self
            .snapshots
            .get(&source_key)
            .ok_or_else(|| SnapshotError::SnapshotNotFound(source_key.clone()))?
            .clone();
        if source.state != SnapshotState::Success {
            return Err(SnapshotError::InvalidRequest(
                "source snapshot must be successful before clone".to_string(),
            ));
        }

        let target_key = SnapshotKey {
            repository: request.repository.clone(),
            snapshot: request.target_snapshot.clone(),
        };
        if self.snapshots.contains_key(&target_key) {
            return Err(SnapshotError::SnapshotAlreadyExists(target_key));
        }
        let indices = if request.indices.is_empty() {
            source.indices.clone()
        } else {
            request.indices
        };
        let snapshot = SnapshotMetadata {
            repository: request.repository,
            snapshot: request.target_snapshot,
            uuid: self.next_snapshot_uuid(),
            state: SnapshotState::Success,
            shard_stats: completed_or_started_stats(indices.len(), true),
            indices,
            cloned_from: Some(source_key),
            failures: Vec::new(),
        };
        self.snapshots.insert(target_key, snapshot.clone());
        Ok(snapshot)
    }

    pub fn restore_snapshot(
        &mut self,
        request: RestoreSnapshotRequest,
    ) -> Result<RestoreMetadata, SnapshotError> {
        let key = SnapshotKey {
            repository: request.repository.clone(),
            snapshot: request.snapshot.clone(),
        };
        let snapshot = self
            .snapshots
            .get(&key)
            .ok_or_else(|| SnapshotError::SnapshotNotFound(key.clone()))?;
        if snapshot.state != SnapshotState::Success {
            return Err(SnapshotError::InvalidRequest(
                "snapshot must be successful before restore".to_string(),
            ));
        }

        let indices = if request.indices.is_empty() {
            snapshot.indices.clone()
        } else {
            request.indices
        };
        let restore_id = format!("restore-{}", self.next_uuid + 1);
        let restore = RestoreMetadata {
            restore_id: restore_id.clone(),
            repository: request.repository,
            snapshot: request.snapshot,
            state: if request.wait_for_completion {
                RestoreState::Success
            } else {
                RestoreState::InProgress
            },
            shard_stats: completed_or_started_stats(indices.len(), request.wait_for_completion),
            indices,
        };
        self.next_uuid += 1;
        self.restores.insert(restore_id, restore.clone());
        Ok(restore)
    }

    pub fn record_shard_metadata(
        &mut self,
        request: SnapshotShardMetadataRequest,
    ) -> Result<SnapshotShardMetadata, SnapshotError> {
        let snapshot_key = SnapshotKey {
            repository: request.repository.clone(),
            snapshot: request.snapshot.clone(),
        };
        let snapshot = self
            .snapshots
            .get(&snapshot_key)
            .ok_or_else(|| SnapshotError::SnapshotNotFound(snapshot_key.clone()))?;
        if snapshot.state != SnapshotState::Success && snapshot.state != SnapshotState::InProgress {
            return Err(SnapshotError::InvalidRequest(
                "shard metadata requires an active or successful snapshot".to_string(),
            ));
        }
        if request.local_checkpoint < request.max_seq_no {
            return Err(SnapshotError::InvalidRequest(
                "local checkpoint must cover max sequence number before snapshot commit"
                    .to_string(),
            ));
        }
        if request.commit_generation == 0 || request.translog_generation == 0 {
            return Err(SnapshotError::InvalidRequest(
                "commit and translog generations must be greater than zero".to_string(),
            ));
        }

        let key = SnapshotShardKey {
            repository: request.repository,
            snapshot: request.snapshot,
            index: request.index,
            shard_id: request.shard_id,
        };
        let metadata = SnapshotShardMetadata {
            key: key.clone(),
            primary_term: request.primary_term,
            max_seq_no: request.max_seq_no,
            local_checkpoint: request.local_checkpoint,
            commit_generation: request.commit_generation,
            translog_generation: request.translog_generation,
            segment_files: Vec::new(),
            commit_safe: true,
        };
        self.shard_snapshots.insert(key, metadata.clone());
        Ok(metadata)
    }

    pub fn copy_segment_file(
        &mut self,
        request: SegmentFileCopyRequest,
    ) -> Result<SnapshotFileMetadata, SnapshotError> {
        let layout = self.prepare_filesystem_repository(&request.repository)?;
        let key = SnapshotShardKey {
            repository: request.repository,
            snapshot: request.snapshot,
            index: request.index,
            shard_id: request.shard_id,
        };
        if !self.shard_snapshots.contains_key(&key) {
            return Err(SnapshotError::InvalidRequest(
                "segment copy requires recorded shard metadata".to_string(),
            ));
        }
        validate_name("segment file", &request.file_name)?;

        let target_dir = layout
            .snapshots_dir
            .join(&key.snapshot)
            .join(&key.index)
            .join(key.shard_id.to_string());
        std::fs::create_dir_all(&target_dir)
            .map_err(|error| SnapshotError::Io(error.to_string()))?;
        let target_path = target_dir.join(&request.file_name);
        std::fs::copy(&request.source_path, &target_path)
            .map_err(|error| SnapshotError::Io(error.to_string()))?;
        let bytes =
            std::fs::read(&target_path).map_err(|error| SnapshotError::Io(error.to_string()))?;
        let file = SnapshotFileMetadata {
            name: request.file_name,
            length: bytes.len() as u64,
            checksum: checksum_bytes(&bytes),
        };
        self.shard_snapshots
            .get_mut(&key)
            .expect("checked shard metadata existence")
            .segment_files
            .push(file.clone());
        Ok(file)
    }

    pub fn shard_metadata(
        &self,
        key: &SnapshotShardKey,
    ) -> Result<&SnapshotShardMetadata, SnapshotError> {
        self.shard_snapshots.get(key).ok_or_else(|| {
            SnapshotError::InvalidRequest(format!(
                "snapshot shard [{}/{}/{}:{}] not found",
                key.repository, key.snapshot, key.index, key.shard_id
            ))
        })
    }

    pub fn plan_restore_allocation(
        &self,
        request: RestoreAllocationRequest,
    ) -> Result<Vec<RestoreShardAllocation>, SnapshotError> {
        if request.shard_count == 0 {
            return Err(SnapshotError::InvalidRequest(
                "restore allocation requires at least one shard".to_string(),
            ));
        }
        if request.candidate_nodes.is_empty() {
            return Err(SnapshotError::InvalidRequest(
                "restore allocation requires candidate nodes".to_string(),
            ));
        }
        self.snapshot_status(&request.repository, &request.snapshot)?;

        Ok((0..request.shard_count)
            .map(|shard_id| RestoreShardAllocation {
                index: request.index.clone(),
                shard_id,
                node_id: request.candidate_nodes[shard_id as usize % request.candidate_nodes.len()]
                    .clone(),
                primary: true,
            })
            .collect())
    }

    pub fn snapshot_status(
        &self,
        repository: &str,
        snapshot: &str,
    ) -> Result<SnapshotStatus, SnapshotError> {
        let key = SnapshotKey {
            repository: repository.to_string(),
            snapshot: snapshot.to_string(),
        };
        let snapshot_metadata = self
            .snapshots
            .get(&key)
            .ok_or_else(|| SnapshotError::SnapshotNotFound(key.clone()))?
            .clone();
        let restore = self
            .restores
            .values()
            .find(|restore| restore.repository == repository && restore.snapshot == snapshot)
            .cloned();
        Ok(SnapshotStatus {
            snapshot: snapshot_metadata,
            restore,
        })
    }

    pub fn cleanup_repository(
        &mut self,
        repository: &str,
    ) -> Result<CleanupRepositoryResponse, SnapshotError> {
        if !self.repositories.contains_key(repository) {
            return Err(SnapshotError::RepositoryNotFound(repository.to_string()));
        }
        let before = self.snapshots.len() as u64;
        self.snapshots.retain(|_, snapshot| {
            !(snapshot.repository == repository && snapshot.state == SnapshotState::Deleted)
        });
        let after = self.snapshots.len() as u64;
        Ok(CleanupRepositoryResponse {
            repository: repository.to_string(),
            removed_snapshots: before - after,
            remaining_snapshots: self
                .snapshots
                .values()
                .filter(|snapshot| snapshot.repository == repository)
                .count() as u64,
        })
    }

    pub fn get_repository(&self, name: &str) -> Result<&RepositoryMetadata, SnapshotError> {
        self.repositories
            .get(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))
    }

    fn ensure_verified_repository(&self, name: &str) -> Result<(), SnapshotError> {
        let repository = self
            .repositories
            .get(name)
            .ok_or_else(|| SnapshotError::RepositoryNotFound(name.to_string()))?;
        if !repository.verified {
            return Err(SnapshotError::RepositoryNotVerified(name.to_string()));
        }
        Ok(())
    }

    fn next_snapshot_uuid(&mut self) -> String {
        self.next_uuid += 1;
        format!("snapshot-{}", self.next_uuid)
    }
}

fn build_filesystem_repository_layout(
    repository: &RepositoryMetadata,
) -> Result<FilesystemRepositoryLayout, SnapshotError> {
    if repository.repository_type != RepositoryType::Fs {
        return Err(SnapshotError::InvalidRequest(format!(
            "repository [{}] is not a filesystem repository",
            repository.name
        )));
    }
    let location = setting_string(repository, "location")?;
    let root = Path::new(&location).to_path_buf();
    if root.as_os_str().is_empty() {
        return Err(SnapshotError::InvalidRequest(
            "filesystem repository location must not be empty".to_string(),
        ));
    }
    Ok(FilesystemRepositoryLayout {
        repository: repository.name.clone(),
        snapshots_dir: root.join("snapshots"),
        indices_dir: root.join("indices"),
        metadata_file: root.join("repository.metadata"),
        root,
    })
}

fn build_cloud_repository_descriptor(
    repository: &RepositoryMetadata,
) -> Result<CloudRepositoryDescriptor, SnapshotError> {
    if !matches!(
        repository.repository_type,
        RepositoryType::S3 | RepositoryType::Gcs | RepositoryType::Azure
    ) {
        return Err(SnapshotError::InvalidRequest(format!(
            "repository [{}] is not a cloud repository",
            repository.name
        )));
    }
    Ok(CloudRepositoryDescriptor {
        repository: repository.name.clone(),
        provider: repository.repository_type.clone(),
        bucket: setting_string(repository, "bucket")?,
        base_path: optional_setting_string(repository, "base_path"),
        region: optional_setting_string(repository, "region"),
    })
}

fn setting_string(repository: &RepositoryMetadata, key: &str) -> Result<String, SnapshotError> {
    optional_setting_string(repository, key).ok_or_else(|| {
        SnapshotError::InvalidRequest(format!(
            "repository [{}] requires setting [{key}]",
            repository.name
        ))
    })
}

fn optional_setting_string(repository: &RepositoryMetadata, key: &str) -> Option<String> {
    repository
        .settings
        .get(key)
        .and_then(Value::as_str)
        .map(str::to_string)
}

fn validate_name(kind: &str, name: &str) -> Result<(), SnapshotError> {
    if name.trim().is_empty() {
        return Err(SnapshotError::InvalidRequest(format!(
            "{kind} name must not be empty"
        )));
    }
    Ok(())
}

fn completed_or_started_stats(index_count: usize, completed: bool) -> SnapshotShardStats {
    let total = index_count.max(1) as u32;
    SnapshotShardStats {
        total,
        successful: if completed { total } else { 0 },
        failed: 0,
    }
}

fn checksum_bytes(bytes: &[u8]) -> u64 {
    let mut checksum = 0xcbf29ce484222325u64;
    for byte in bytes {
        checksum ^= u64::from(*byte);
        checksum = checksum.wrapping_mul(0x100000001b3);
    }
    checksum
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn repository_metadata_and_verification_lifecycle() {
        let mut service = SnapshotService::default();
        let repository = service
            .put_repository(PutRepositoryRequest {
                name: "repo-1".to_string(),
                repository_type: RepositoryType::Fs,
                settings: BTreeMap::from([("location".to_string(), json!("/snapshots"))]),
            })
            .unwrap();
        assert!(!repository.verified);

        let verification = service.verify_repository("repo-1").unwrap();
        assert!(verification.verified);
        assert_eq!(verification.generation, 2);
        assert!(service.get_repository("repo-1").unwrap().verified);
    }

    #[test]
    fn filesystem_repository_prepares_local_layout() {
        let root = unique_temp_repository_root("steelsearch-fs-repo");
        let mut service = SnapshotService::default();
        service
            .put_repository(PutRepositoryRequest {
                name: "repo-1".to_string(),
                repository_type: RepositoryType::Fs,
                settings: BTreeMap::from([(
                    "location".to_string(),
                    json!(root.to_string_lossy().to_string()),
                )]),
            })
            .unwrap();

        let layout = service.prepare_filesystem_repository("repo-1").unwrap();
        assert_eq!(layout.root, root);
        assert!(layout.snapshots_dir.is_dir());
        assert!(layout.indices_dir.is_dir());
        assert!(layout.metadata_file.is_file());
        service.verify_repository("repo-1").unwrap();

        let _ = std::fs::remove_dir_all(layout.root);
    }

    #[test]
    fn cloud_repository_descriptor_validates_bucket_settings() {
        let mut service = SnapshotService::default();
        service
            .put_repository(PutRepositoryRequest {
                name: "repo-s3".to_string(),
                repository_type: RepositoryType::S3,
                settings: BTreeMap::from([
                    ("bucket".to_string(), json!("steelsearch-snapshots")),
                    ("base_path".to_string(), json!("prod")),
                    ("region".to_string(), json!("us-east-1")),
                ]),
            })
            .unwrap();

        let descriptor = service.cloud_repository_descriptor("repo-s3").unwrap();
        assert_eq!(descriptor.provider, RepositoryType::S3);
        assert_eq!(descriptor.bucket, "steelsearch-snapshots");
        assert_eq!(descriptor.base_path.as_deref(), Some("prod"));
        service.verify_repository("repo-s3").unwrap();
    }

    #[test]
    fn snapshot_create_status_delete_and_cleanup_flow() {
        let mut service = verified_service();
        let snapshot = service
            .create_snapshot(CreateSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                indices: vec!["logs".to_string(), "metrics".to_string()],
                wait_for_completion: true,
            })
            .unwrap();
        assert_eq!(snapshot.state, SnapshotState::Success);
        assert_eq!(snapshot.shard_stats.successful, 2);

        let status = service.snapshot_status("repo-1", "snap-1").unwrap();
        assert_eq!(status.snapshot.uuid, snapshot.uuid);
        assert!(status.restore.is_none());

        let deleted = service
            .delete_snapshot(DeleteSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
            })
            .unwrap();
        assert_eq!(deleted.state, SnapshotState::Deleted);
        let cleanup = service.cleanup_repository("repo-1").unwrap();
        assert_eq!(cleanup.remaining_snapshots, 0);
    }

    #[test]
    fn clone_and_restore_snapshot_flow() {
        let mut service = verified_service();
        service
            .create_snapshot(CreateSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "source".to_string(),
                indices: vec!["logs".to_string()],
                wait_for_completion: true,
            })
            .unwrap();

        let clone = service
            .clone_snapshot(CloneSnapshotRequest {
                repository: "repo-1".to_string(),
                source_snapshot: "source".to_string(),
                target_snapshot: "clone".to_string(),
                indices: Vec::new(),
            })
            .unwrap();
        assert_eq!(clone.state, SnapshotState::Success);
        assert_eq!(clone.cloned_from.unwrap().snapshot, "source");

        let restore = service
            .restore_snapshot(RestoreSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "clone".to_string(),
                indices: Vec::new(),
                wait_for_completion: true,
            })
            .unwrap();
        assert_eq!(restore.state, RestoreState::Success);

        let status = service.snapshot_status("repo-1", "clone").unwrap();
        assert_eq!(status.restore.unwrap().restore_id, restore.restore_id);
    }

    #[test]
    fn snapshot_requires_verified_repository() {
        let mut service = SnapshotService::default();
        service
            .put_repository(PutRepositoryRequest {
                name: "repo-1".to_string(),
                repository_type: RepositoryType::Fs,
                settings: BTreeMap::new(),
            })
            .unwrap();

        let error = service
            .create_snapshot(CreateSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                indices: Vec::new(),
                wait_for_completion: true,
            })
            .unwrap_err();
        assert_eq!(
            error,
            SnapshotError::RepositoryNotVerified("repo-1".to_string())
        );
    }

    #[test]
    fn shard_metadata_segment_copy_and_restore_allocation_flow() {
        let root = unique_temp_repository_root("steelsearch-shard-snapshot");
        let mut service = SnapshotService::default();
        service
            .put_repository(PutRepositoryRequest {
                name: "repo-1".to_string(),
                repository_type: RepositoryType::Fs,
                settings: BTreeMap::from([(
                    "location".to_string(),
                    json!(root.to_string_lossy().to_string()),
                )]),
            })
            .unwrap();
        service.prepare_filesystem_repository("repo-1").unwrap();
        service.verify_repository("repo-1").unwrap();
        service
            .create_snapshot(CreateSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                indices: vec!["logs".to_string()],
                wait_for_completion: true,
            })
            .unwrap();

        let shard = service
            .record_shard_metadata(SnapshotShardMetadataRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                index: "logs".to_string(),
                shard_id: 0,
                primary_term: 3,
                max_seq_no: 42,
                local_checkpoint: 42,
                commit_generation: 7,
                translog_generation: 9,
            })
            .unwrap();
        assert!(shard.commit_safe);

        let source_file = root.join("source-segment.si");
        std::fs::write(&source_file, b"segment-bytes").unwrap();
        let file = service
            .copy_segment_file(SegmentFileCopyRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                index: "logs".to_string(),
                shard_id: 0,
                source_path: source_file,
                file_name: "_0.si".to_string(),
            })
            .unwrap();
        assert_eq!(file.length, "segment-bytes".len() as u64);

        let key = SnapshotShardKey {
            repository: "repo-1".to_string(),
            snapshot: "snap-1".to_string(),
            index: "logs".to_string(),
            shard_id: 0,
        };
        assert_eq!(service.shard_metadata(&key).unwrap().segment_files.len(), 1);

        let allocations = service
            .plan_restore_allocation(RestoreAllocationRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                index: "logs".to_string(),
                shard_count: 3,
                candidate_nodes: vec!["node-a".to_string(), "node-b".to_string()],
            })
            .unwrap();
        assert_eq!(allocations[0].node_id, "node-a");
        assert_eq!(allocations[1].node_id, "node-b");
        assert_eq!(allocations[2].node_id, "node-a");

        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn shard_metadata_rejects_unsafe_checkpoint() {
        let mut service = verified_service();
        service
            .create_snapshot(CreateSnapshotRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                indices: vec!["logs".to_string()],
                wait_for_completion: true,
            })
            .unwrap();

        let error = service
            .record_shard_metadata(SnapshotShardMetadataRequest {
                repository: "repo-1".to_string(),
                snapshot: "snap-1".to_string(),
                index: "logs".to_string(),
                shard_id: 0,
                primary_term: 1,
                max_seq_no: 10,
                local_checkpoint: 9,
                commit_generation: 1,
                translog_generation: 1,
            })
            .unwrap_err();
        assert!(matches!(error, SnapshotError::InvalidRequest(_)));
    }

    fn verified_service() -> SnapshotService {
        let mut service = SnapshotService::default();
        service
            .put_repository(PutRepositoryRequest {
                name: "repo-1".to_string(),
                repository_type: RepositoryType::Fs,
                settings: BTreeMap::from([("location".to_string(), json!("/snapshots"))]),
            })
            .unwrap();
        service.verify_repository("repo-1").unwrap();
        service
    }

    fn unique_temp_repository_root(prefix: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "{}-{}",
            prefix,
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
    }
}
