//! REST compatibility shell.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestRoute {
    pub method: String,
    pub path: String,
}
