//! Engine abstraction for Lucene-compatible and Rust-native backends.

use anyhow::Result;
use serde_json::Value;

pub trait IndexEngine: Send + Sync {
    fn create_index(&self, name: &str) -> Result<()>;
    fn index_document(&self, index: &str, id: &str, source: Value) -> Result<()>;
    fn get_document(&self, index: &str, id: &str) -> Result<Option<Value>>;
}
