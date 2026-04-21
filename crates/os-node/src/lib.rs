//! Node lifecycle scaffolding.

use os_core::Version;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NodeInfo {
    pub name: String,
    pub version: Version,
}
