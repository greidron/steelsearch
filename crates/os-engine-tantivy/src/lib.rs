//! Tantivy-backed engine placeholder.

use anyhow::Result;
use os_engine::IndexEngine;
use serde_json::Value;

#[derive(Debug, Default)]
pub struct TantivyEngine;

impl IndexEngine for TantivyEngine {
    fn create_index(&self, _name: &str) -> Result<()> {
        Ok(())
    }

    fn index_document(&self, _index: &str, _id: &str, _source: Value) -> Result<()> {
        Ok(())
    }

    fn get_document(&self, _index: &str, _id: &str) -> Result<Option<Value>> {
        Ok(None)
    }
}
