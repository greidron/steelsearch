//! Validated routing layout shared by document placement and search shard selection.

#[derive(Clone, Copy, Debug, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(try_from = "StoredRouting")]
pub struct IndexRouting {
    primary_shards: u32,
    routing_shards: u32,
    partition_size: u32,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredRouting {
    primary_shards: u32,
    routing_shards: u32,
    partition_size: u32,
}

impl TryFrom<StoredRouting> for IndexRouting {
    type Error = RoutingError;

    fn try_from(value: StoredRouting) -> Result<Self, Self::Error> {
        Self::new(
            value.primary_shards,
            Some(value.routing_shards),
            value.partition_size,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, thiserror::Error)]
pub enum RoutingError {
    #[error("primary shard count must be positive and representable as a signed 32-bit integer")]
    InvalidPrimaryShards,
    #[error("routing shard count must be positive and representable as a signed 32-bit integer")]
    InvalidRoutingShards,
    #[error("routing shard count must be at least the primary shard count")]
    RoutingShardsTooSmall,
    #[error("primary shard count must be a factor of routing shard count")]
    RoutingShardsNotMultiple,
    #[error("partition size must be positive and, unless one, less than routing shard count")]
    InvalidPartitionSize,
}

impl IndexRouting {
    pub fn new(
        primary_shards: u32,
        routing_shards: Option<u32>,
        partition_size: u32,
    ) -> Result<Self, RoutingError> {
        if primary_shards == 0 || primary_shards > i32::MAX as u32 {
            return Err(RoutingError::InvalidPrimaryShards);
        }
        let routing_shards = match routing_shards {
            Some(value) => value,
            None => {
                // MetadataCreateIndexService guarantees at least one future split.
                let ceil_log2 = u32::BITS - (primary_shards - 1).leading_zeros();
                let splits = 10_u32.saturating_sub(ceil_log2).max(1);
                primary_shards
                    .checked_mul(1 << splits)
                    .ok_or(RoutingError::InvalidRoutingShards)?
            }
        };
        if routing_shards == 0 || routing_shards > i32::MAX as u32 {
            return Err(RoutingError::InvalidRoutingShards);
        }
        if routing_shards < primary_shards {
            return Err(RoutingError::RoutingShardsTooSmall);
        }
        if routing_shards % primary_shards != 0 {
            return Err(RoutingError::RoutingShardsNotMultiple);
        }
        if partition_size == 0 || (partition_size != 1 && partition_size >= routing_shards) {
            return Err(RoutingError::InvalidPartitionSize);
        }
        Ok(Self {
            primary_shards,
            routing_shards,
            partition_size,
        })
    }

    pub fn primary_shards(self) -> u32 {
        self.primary_shards
    }
    pub fn routing_shards(self) -> u32 {
        self.routing_shards
    }
    pub fn partition_size(self) -> u32 {
        self.partition_size
    }

    /// Hashes are OpenSearch Murmur3 hashes of UTF-16LE routing and document ID.
    pub fn document_shard(self, routing_hash: i32, id_hash: i32) -> u32 {
        let offset = id_hash.rem_euclid(self.partition_size as i32) as u32;
        self.shard_with_offset(routing_hash, offset)
    }

    /// Multiple offsets can map to one shard; callers should collect into their shard set.
    pub fn search_shards(self, routing_hash: i32) -> impl Iterator<Item = u32> {
        (0..self.partition_size).map(move |offset| self.shard_with_offset(routing_hash, offset))
    }

    fn shard_with_offset(self, routing_hash: i32, offset: u32) -> u32 {
        let hash = routing_hash.wrapping_add(offset as i32);
        hash.rem_euclid(self.routing_shards as i32) as u32
            / (self.routing_shards / self.primary_shards)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    #[test]
    fn persisted_layout_is_validated_on_read() {
        let layout = IndexRouting::new(3, Some(12), 2).unwrap();
        let bytes = serde_json::to_vec(&layout).unwrap();
        assert_eq!(
            serde_json::from_slice::<IndexRouting>(&bytes).unwrap(),
            layout
        );
        for body in [
            serde_json::json!({"primary_shards": 3, "routing_shards": 4, "partition_size": 1}),
            serde_json::json!({"primary_shards": 3, "routing_shards": 12, "partition_size": 0}),
            serde_json::json!({"primary_shards": 3, "routing_shards": 12}),
            serde_json::json!({"primary_shards": 3, "routing_shards": 12, "partition_size": 1, "unknown": 2}),
        ] {
            assert!(serde_json::from_value::<IndexRouting>(body).is_err());
        }
    }

    #[test]
    fn default_layout_matches_reference_split_policy() {
        for (primary, routing) in [
            (1, 1024),
            (3, 768),
            (5, 640),
            (512, 1024),
            (1024, 2048),
            (1025, 2050),
        ] {
            let layout = IndexRouting::new(primary, None, 1).unwrap();
            assert_eq!(layout.primary_shards(), primary);
            assert_eq!(layout.routing_shards(), routing);
            assert_eq!(layout.partition_size(), 1);
        }
    }

    #[test]
    fn explicit_primary_count_preserves_unscaled_layout() {
        let layout = IndexRouting::new(3, Some(3), 1).unwrap();
        for hash in [i32::MIN, -1025, -1, 0, 1, 1025, i32::MAX] {
            assert_eq!(layout.document_shard(hash, 123), hash.rem_euclid(3) as u32);
        }
    }

    #[test]
    fn scaled_routing_uses_floor_mod_before_division() {
        let layout = IndexRouting::new(3, Some(12), 1).unwrap();
        for (hash, expected) in [
            (-13, 2),
            (-12, 0),
            (-1, 2),
            (0, 0),
            (3, 0),
            (4, 1),
            (7, 1),
            (8, 2),
            (11, 2),
            (12, 0),
        ] {
            assert_eq!(layout.document_shard(hash, 0), expected);
            assert_eq!(
                layout.search_shards(hash).collect::<Vec<_>>(),
                vec![expected]
            );
        }
    }

    #[test]
    fn partition_search_contains_every_document_shard_and_wraps_like_java() {
        for partition in [1, 2, 3, 11] {
            let layout = IndexRouting::new(3, Some(12), partition).unwrap();
            for routing in [i32::MIN, -13, -1, 0, 3, 11, i32::MAX] {
                let shards = layout.search_shards(routing).collect::<BTreeSet<_>>();
                assert!(shards.iter().all(|id| *id < 3));
                for id in -20_i32..20 {
                    assert!(shards.contains(&layout.document_shard(routing, id)));
                }
            }
        }
        let layout = IndexRouting::new(3, Some(12), 2).unwrap();
        assert_eq!(layout.document_shard(i32::MAX, 1), 1);
        assert_eq!(
            layout.search_shards(3).collect::<BTreeSet<_>>(),
            BTreeSet::from([0, 1])
        );
    }

    #[test]
    fn invalid_layouts_fail_before_any_placement() {
        for (primary, routing, partition, expected) in [
            (0, None, 1, RoutingError::InvalidPrimaryShards),
            (3, Some(0), 1, RoutingError::InvalidRoutingShards),
            (3, Some(2), 1, RoutingError::RoutingShardsTooSmall),
            (3, Some(4), 1, RoutingError::RoutingShardsNotMultiple),
            (3, Some(12), 0, RoutingError::InvalidPartitionSize),
            (3, Some(12), 12, RoutingError::InvalidPartitionSize),
            (3, Some(12), 13, RoutingError::InvalidPartitionSize),
            (i32::MAX as u32, None, 1, RoutingError::InvalidRoutingShards),
            (3, Some(u32::MAX), 1, RoutingError::InvalidRoutingShards),
        ] {
            assert_eq!(
                IndexRouting::new(primary, routing, partition),
                Err(expected)
            );
        }
        assert!(IndexRouting::new(3, Some(12), 3).is_ok());
        assert!(IndexRouting::new(1, Some(1), 1).is_ok());
    }
}
