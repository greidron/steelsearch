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
