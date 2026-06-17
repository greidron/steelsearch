use serde::{Deserialize, Serialize};
use std::net::{SocketAddr, TcpListener};

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AuthenticationUsersFile {
    #[serde(default)]
    pub users: Vec<AuthenticationUser>,
    #[serde(default)]
    pub service_accounts: Vec<AuthenticationServiceAccount>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AuthenticationUser {
    pub username: String,
    #[serde(default)]
    pub password_hash: Option<String>,
    #[serde(default)]
    pub password: Option<String>,
    pub roles: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AuthenticationServiceAccount {
    pub name: String,
    #[serde(default)]
    pub token_hash: Option<String>,
    #[serde(default)]
    pub token: Option<String>,
    pub roles: Vec<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct RestServerConfig {
    pub bind_host: String,
    pub port: u16,
}

#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct SecurityBoundaryPolicy {
    pub http_tls: SecurityBoundaryState,
    pub transport_tls: SecurityBoundaryState,
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
            http_tls: SecurityBoundaryState::Enforced,
            transport_tls: SecurityBoundaryState::Enforced,
            authentication: SecurityBoundaryState::Enforced,
            authorization: SecurityBoundaryState::Enforced,
            audit_logging: SecurityBoundaryState::Enforced,
            tenant_isolation: SecurityBoundaryState::Enforced,
            secure_settings: SecurityBoundaryState::Enforced,
        }
    }

    fn blockers(&self) -> Vec<&'static str> {
        let boundaries = [
            (self.http_tls, "http_tls must be implemented and enforced"),
            (
                self.transport_tls,
                "transport_tls must be implemented and enforced",
            ),
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

pub fn parse_authentication_users_json(
    raw: &str,
) -> Result<AuthenticationUsersFile, Box<dyn std::error::Error>> {
    if raw.trim().is_empty() {
        return Err("must contain at least one authentication subject".into());
    }
    let parsed: AuthenticationUsersFile =
        serde_json::from_str(raw).map_err(|error| format!("must be valid JSON: {error}"))?;
    validate_authentication_users_file(&parsed)?;
    Ok(parsed)
}

pub fn validate_authentication_users_file(
    users_file: &AuthenticationUsersFile,
) -> Result<(), Box<dyn std::error::Error>> {
    if users_file.users.is_empty() && users_file.service_accounts.is_empty() {
        return Err("must contain at least one authentication subject".into());
    }
    for (index, user) in users_file.users.iter().enumerate() {
        if user.username.trim().is_empty() {
            return Err(format!("user[{index}].username must be a non-empty string").into());
        }
        let has_password_hash = user
            .password_hash
            .as_deref()
            .map(str::trim)
            .is_some_and(|value| !value.is_empty());
        let has_password = user
            .password
            .as_deref()
            .map(str::trim)
            .is_some_and(|value| !value.is_empty());
        if !has_password_hash && !has_password {
            return Err(format!("user[{index}] must include password_hash or password").into());
        }
        if user.roles.is_empty() || user.roles.iter().any(|role| role.trim().is_empty()) {
            return Err(format!("user[{index}].roles must be a non-empty string array").into());
        }
    }
    for (index, service_account) in users_file.service_accounts.iter().enumerate() {
        if service_account.name.trim().is_empty() {
            return Err(
                format!("service_accounts[{index}].name must be a non-empty string").into(),
            );
        }
        let has_token_hash = service_account
            .token_hash
            .as_deref()
            .map(str::trim)
            .is_some_and(|value| !value.is_empty());
        let has_token = service_account
            .token
            .as_deref()
            .map(str::trim)
            .is_some_and(|value| !value.is_empty());
        if !has_token_hash && !has_token {
            return Err(
                format!("service_accounts[{index}] must include token_hash or token").into(),
            );
        }
        if service_account.roles.is_empty()
            || service_account.roles.iter().any(|role| role.trim().is_empty())
        {
            return Err(
                format!("service_accounts[{index}].roles must be a non-empty string array")
                    .into(),
            );
        }
    }
    Ok(())
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
        assert!(error.contains("http_tls must be implemented and enforced"));
        assert!(error.contains("transport_tls must be implemented and enforced"));
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
            http_tls: SecurityBoundaryState::Enforced,
            transport_tls: SecurityBoundaryState::Enforced,
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

        assert!(!error.contains("http_tls must be implemented and enforced"));
        assert!(!error.contains("transport_tls must be implemented and enforced"));
        assert!(!error.contains("authentication must be implemented and enforced"));
        assert!(error.contains("authorization must be implemented and enforced"));
        assert!(!error.contains("benchmark coverage is missing"));
        assert!(error.contains("load test coverage is missing"));
    }

    #[test]
    fn production_mode_request_tracks_http_and_transport_tls_independently() {
        let policy = SecurityBoundaryPolicy {
            http_tls: SecurityBoundaryState::Enforced,
            ..SecurityBoundaryPolicy::steelsearch_native_required()
        };

        let error = validate_production_mode_request(&policy, ReleaseReadinessChecklist::complete())
            .unwrap_err()
            .to_string();

        assert!(!error.contains("http_tls must be implemented and enforced"));
        assert!(error.contains("transport_tls must be implemented and enforced"));
        assert!(error.contains("authentication must be implemented and enforced"));
        assert!(!error.contains("benchmark coverage is missing"));
    }

    #[test]
    fn authentication_users_file_parser_accepts_subjects_with_roles() {
        let parsed = parse_authentication_users_json(
            r#"{"users":[{"username":"admin","password_hash":"hash","roles":["admin"]}],"service_accounts":[{"name":"svc-indexer","token_hash":"service-hash","roles":["writer"]}]}"#,
        )
        .unwrap();

        assert_eq!(parsed.users[0].username, "admin");
        assert_eq!(parsed.users[0].password_hash.as_deref(), Some("hash"));
        assert_eq!(parsed.users[0].roles, vec!["admin".to_string()]);
        assert_eq!(parsed.service_accounts[0].name, "svc-indexer");
        assert_eq!(
            parsed.service_accounts[0].token_hash.as_deref(),
            Some("service-hash")
        );
        assert_eq!(
            parsed.service_accounts[0].roles,
            vec!["writer".to_string()]
        );
    }

    #[test]
    fn authentication_users_file_parser_rejects_empty_and_malformed_inputs() {
        assert_eq!(
            parse_authentication_users_json("").unwrap_err().to_string(),
            "must contain at least one authentication subject"
        );
        assert!(parse_authentication_users_json("not-json")
            .unwrap_err()
            .to_string()
            .contains("must be valid JSON"));
        assert_eq!(
            parse_authentication_users_json(r#"{"users":[]}"#)
                .unwrap_err()
                .to_string(),
            "must contain at least one authentication subject"
        );
    }

    #[test]
    fn authentication_users_file_parser_rejects_invalid_subject_entries() {
        assert_eq!(
            parse_authentication_users_json(
                r#"{"users":[{"username":"","password_hash":"hash","roles":["admin"]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "user[0].username must be a non-empty string"
        );
        assert_eq!(
            parse_authentication_users_json(
                r#"{"users":[{"username":"admin","roles":["admin"]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "user[0] must include password_hash or password"
        );
        assert_eq!(
            parse_authentication_users_json(
                r#"{"users":[{"username":"admin","password_hash":"hash","roles":[]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "user[0].roles must be a non-empty string array"
        );
        assert_eq!(
            parse_authentication_users_json(
                r#"{"service_accounts":[{"name":"","token_hash":"hash","roles":["writer"]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "service_accounts[0].name must be a non-empty string"
        );
        assert_eq!(
            parse_authentication_users_json(
                r#"{"service_accounts":[{"name":"svc-indexer","roles":["writer"]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "service_accounts[0] must include token_hash or token"
        );
        assert_eq!(
            parse_authentication_users_json(
                r#"{"service_accounts":[{"name":"svc-indexer","token_hash":"hash","roles":[]}]}"#,
            )
            .unwrap_err()
            .to_string(),
            "service_accounts[0].roles must be a non-empty string array"
        );
    }
}
