# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: BUSL-1.1
# =============================================================================
# mandatory_overridable_scen_8 — resource_policy with enforcement_level =
# "mandatory_overridable". Fixture: scen8_compliant log group (Allow) and
# scen8_violating log group (overridable Deny — the run should offer the
# override path).
# Source: hashicorp/policy-library-for-tfpolicy,
# tfpolicy-feature-regression/policies/mandatory_overridable_scen_8.policy.hcl
# =============================================================================

resource_policy "aws_cloudwatch_log_group" "overridable_name_prefix_scen_8" {
  enforcement_level = "mandatory_overridable"
  enforce {
    condition     = core::length(core::regexall("^/beta/", core::try(attrs.name, ""))) > 0
    info_message  = "Log group '${core::try(attrs.name, "?")}' carries the required /beta/ prefix"
    error_message = "Log group name must start with '/beta/'; found '${core::try(attrs.name, "<missing>")}'. This deny is mandatory_overridable and can be overridden."
  }
}
