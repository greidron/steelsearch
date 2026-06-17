use serde::{Deserialize, Serialize};
use std::net::{SocketAddr, TcpListener};

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestServerConfig {
    pub bind_host: String,
    pub port: u16,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SecurityBoundaryPolicy {
    pub tls: SecurityBoundaryState,
    pub authentication: SecurityBoundaryState,
    pub authorization: SecurityBoundaryState,
    pub audit_logging: SecurityBoundaryState,
    pub tenant_isolation: SecurityBoundaryState,
    pub secure_settings: SecurityBoundaryState,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct ReleaseReadinessChecklist {
    pub benchmark_coverage: bool,
    pub load_test_coverage: bool,
    pub chaos_test_coverage: bool,
    pub packaging_verified: bool,
    pub rolling_upgrade_coverage: bool,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub enum SecurityBoundaryState {
    #[default]
    Required,
    Enforced,
}

impl SecurityBoundaryPolicy {
    pub fn steelsearch_native_required() -> Self {
        Self::default()
    }

    pub fn enforced() -> Self {
        Self {
            tls: SecurityBoundaryState::Enforced,
            authentication: SecurityBoundaryState::Enforced,
            authorization: SecurityBoundaryState::Enforced,
            audit_logging: SecurityBoundaryState::Enforced,
            tenant_isolation: SecurityBoundaryState::Enforced,
            secure_settings: SecurityBoundaryState::Enforced,
        }
    }

    fn blockers(&self) -> Vec<&'static str> {
        let boundaries = [
            (self.tls, "tls must be implemented and enforced"),
            (
                self.authentication,
                "authentication must be implemented and enforced",
            ),
            (
                self.authorization,
                "authorization must be implemented and enforced",
            ),
            (
                self.audit_logging,
                "audit_logging must be implemented and enforced",
            ),
            (
                self.tenant_isolation,
                "tenant_isolation must be implemented and enforced",
            ),
            (
                self.secure_settings,
                "secure_settings must be implemented and enforced",
            ),
        ];
        boundaries
            .into_iter()
            .filter_map(|(state, blocker)| {
                (state != SecurityBoundaryState::Enforced).then_some(blocker)
            })
            .collect()
    }
}

impl ReleaseReadinessChecklist {
    pub fn complete() -> Self {
        Self {
            benchmark_coverage: true,
            load_test_coverage: true,
            chaos_test_coverage: true,
            packaging_verified: true,
            rolling_upgrade_coverage: true,
        }
    }

    fn blockers(&self) -> Vec<&'static str> {
        let checks = [
            (self.benchmark_coverage, "benchmark coverage is missing"),
            (self.load_test_coverage, "load test coverage is missing"),
            (self.chaos_test_coverage, "chaos test coverage is missing"),
            (self.packaging_verified, "packaging is not verified"),
            (
                self.rolling_upgrade_coverage,
                "rolling upgrade coverage is missing",
            ),
        ];
        checks
            .into_iter()
            .filter_map(|(ready, blocker)| (!ready).then_some(blocker))
            .collect()
    }
}

pub fn validate_production_mode_request(
    policy: &SecurityBoundaryPolicy,
    checklist: ReleaseReadinessChecklist,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut blockers = policy.blockers();
    blockers.extend(checklist.blockers());
    if blockers.is_empty() {
        return Ok(());
    }
    Err(format!("production mode is blocked until {}", blockers.join(", ")).into())
}

pub fn bind_rest_http_listener(address: SocketAddr) -> std::io::Result<TcpListener> {
    TcpListener::bind(address)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn production_mode_request_reports_each_missing_security_and_release_gate() {
        let error = validate_production_mode_request(
            &SecurityBoundaryPolicy::steelsearch_native_required(),
            ReleaseReadinessChecklist::default(),
        )
        .unwrap_err()
        .to_string();

        assert!(error.contains("production mode is blocked"));
        assert!(error.contains("tls must be implemented and enforced"));
        assert!(error.contains("authentication must be implemented and enforced"));
        assert!(error.contains("authorization must be implemented and enforced"));
        assert!(error.contains("audit_logging must be implemented and enforced"));
        assert!(error.contains("tenant_isolation must be implemented and enforced"));
        assert!(error.contains("secure_settings must be implemented and enforced"));
        assert!(error.contains("benchmark coverage is missing"));
        assert!(error.contains("load test coverage is missing"));
        assert!(error.contains("chaos test coverage is missing"));
        assert!(error.contains("packaging is not verified"));
        assert!(error.contains("rolling upgrade coverage is missing"));
    }

    #[test]
    fn production_mode_request_allows_startup_only_when_all_gates_are_complete() {
        validate_production_mode_request(
            &SecurityBoundaryPolicy::enforced(),
            ReleaseReadinessChecklist::complete(),
        )
        .expect("all enforced security boundaries and release checks should pass");
    }

    #[test]
    fn production_mode_request_keeps_release_and_security_blockers_distinct() {
        let policy = SecurityBoundaryPolicy {
            tls: SecurityBoundaryState::Enforced,
            authentication: SecurityBoundaryState::Enforced,
            ..SecurityBoundaryPolicy::steelsearch_native_required()
        };
        let checklist = ReleaseReadinessChecklist {
            benchmark_coverage: true,
            ..ReleaseReadinessChecklist::default()
        };

        let error = validate_production_mode_request(&policy, checklist)
            .unwrap_err()
            .to_string();

        assert!(!error.contains("tls must be implemented and enforced"));
        assert!(!error.contains("authentication must be implemented and enforced"));
        assert!(error.contains("authorization must be implemented and enforced"));
        assert!(!error.contains("benchmark coverage is missing"));
        assert!(error.contains("load test coverage is missing"));
    }
}
