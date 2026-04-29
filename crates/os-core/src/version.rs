use serde::{Deserialize, Serialize};
use std::fmt;

/// OpenSearch wire version identifier.
///
/// Java OpenSearch serializes the version as an integer in transport headers and
/// uses it to gate request and cluster-state serialization.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash, Serialize, Deserialize)]
pub struct Version {
    id: i32,
}

pub const OPENSEARCH_2_7_0: Version = Version::from_id(2_070_099);
pub const OPENSEARCH_2_9_0: Version = Version::from_id(2_090_099);
pub const OPENSEARCH_2_10_0: Version = Version::from_id(2_100_099);
pub const OPENSEARCH_2_17_0: Version = Version::from_id(2_170_099);
pub const OPENSEARCH_2_18_0: Version = Version::from_id(2_180_099);
pub const OPENSEARCH_3_0_0: Version = Version::from_id(3_000_099);
pub const OPENSEARCH_3_6_0: Version = Version::from_id(3_060_099);
pub const OPENSEARCH_3_7_0: Version = Version::from_id(3_070_099);

/// Transport version from the Java OpenSearch 3.7.0-SNAPSHOT fixtures.
pub const OPENSEARCH_3_7_0_TRANSPORT: Version = Version::from_id(137_287_827);

/// Minimum transport compatibility version emitted by the 3.7.0-SNAPSHOT
/// fixture's TCP handshake header.
pub const OPENSEARCH_3_7_0_MIN_COMPAT_TRANSPORT: Version = Version::from_id(136_407_827);

/// Transport stream version where discovery nodes include a stream address.
pub const OPENSEARCH_DISCOVERY_NODE_STREAM_ADDRESS: Version = Version::from_id(137_237_827);

impl Version {
    pub const fn from_id(id: i32) -> Self {
        Self { id }
    }

    pub const fn id(self) -> i32 {
        self.id
    }

    pub const fn on_or_after(self, other: Self) -> bool {
        self.id >= other.id
    }
}

impl fmt::Display for Version {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.id)
    }
}
