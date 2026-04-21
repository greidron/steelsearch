//! Minimal StreamInput/StreamOutput-compatible primitives.

pub mod input;
pub mod output;

pub use input::{StreamInput, StreamInputError};
pub use output::StreamOutput;
