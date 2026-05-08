use serde::{Deserialize, Serialize};
use std::net::{SocketAddr, TcpListener};

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestServerConfig {
    pub bind_host: String,
    pub port: u16,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SecurityBoundaryPolicy {}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReleaseReadinessChecklist {}

pub fn validate_production_mode_request(
    _policy: &SecurityBoundaryPolicy,
    _checklist: ReleaseReadinessChecklist,
) -> Result<(), Box<dyn std::error::Error>> {
    Err(
        "production mode is blocked until tls must be implemented and enforced, authentication must be implemented and enforced, authorization must be implemented and enforced, audit_logging must be implemented and enforced, tenant_isolation must be implemented and enforced, secure_settings must be implemented and enforced, benchmark coverage is missing, load test coverage is missing, chaos test coverage is missing, packaging is not verified, rolling upgrade coverage is missing".into(),
    )
}

pub fn bind_rest_http_listener(address: SocketAddr) -> std::io::Result<TcpListener> {
    TcpListener::bind(address)
}
