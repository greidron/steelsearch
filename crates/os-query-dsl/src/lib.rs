//! OpenSearch query DSL model placeholders.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Query {
    MatchAll,
    Term {
        field: String,
        value: serde_json::Value,
    },
}
