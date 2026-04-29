//! Source-owned refresh policy subset and visibility timing rules for Phase A write-path work.

pub const DEFAULT_REFRESH_POLICY: &str = "false";
pub const WAIT_FOR_REFRESH_POLICY: &str = "wait_for";
pub const SUPPORTED_REFRESH_POLICIES: [&str; 2] =
    [DEFAULT_REFRESH_POLICY, WAIT_FOR_REFRESH_POLICY];
pub const UNSUPPORTED_REFRESH_POLICY_BUCKET: &str = "unsupported refresh policy";

pub fn normalize_refresh_policy(raw: Option<&str>) -> Result<&'static str, &'static str> {
    match raw.unwrap_or(DEFAULT_REFRESH_POLICY) {
        DEFAULT_REFRESH_POLICY => Ok(DEFAULT_REFRESH_POLICY),
        WAIT_FOR_REFRESH_POLICY => Ok(WAIT_FOR_REFRESH_POLICY),
        _ => Err(UNSUPPORTED_REFRESH_POLICY_BUCKET),
    }
}

pub fn requires_explicit_post_refresh(policy: &str) -> bool {
    policy == DEFAULT_REFRESH_POLICY
}

pub fn grants_request_scoped_visibility(policy: &str) -> bool {
    policy == WAIT_FOR_REFRESH_POLICY
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn refresh_policy_defaults_to_false_and_keeps_wait_for_subset() {
        assert_eq!(normalize_refresh_policy(None), Ok("false"));
        assert_eq!(normalize_refresh_policy(Some("false")), Ok("false"));
        assert_eq!(normalize_refresh_policy(Some("wait_for")), Ok("wait_for"));
    }

    #[test]
    fn refresh_policy_rejects_out_of_subset_values() {
        assert_eq!(
            normalize_refresh_policy(Some("true")),
            Err("unsupported refresh policy")
        );
        assert_eq!(
            normalize_refresh_policy(Some("immediate")),
            Err("unsupported refresh policy")
        );
    }

    #[test]
    fn refresh_policy_visibility_rules_distinguish_false_from_wait_for() {
        assert!(requires_explicit_post_refresh("false"));
        assert!(!requires_explicit_post_refresh("wait_for"));
        assert!(grants_request_scoped_visibility("wait_for"));
        assert!(!grants_request_scoped_visibility("false"));
    }
}
