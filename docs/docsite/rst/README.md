# HashiCorp Terraform Collection Guides

These guides show how to integrate Ansible with HCP Terraform and Terraform
Enterprise. They complement the plugin reference available through Automation
Hub and `ansible-doc`.

## Getting Started

- [Getting started](guide_getting_started.rst): Install the collection and run
  your first task.
- [Authentication](guide_authentication.rst): Configure API tokens, Terraform
  Enterprise endpoints, TLS, proxies, timeouts, and retries.

## End-to-End Cookbooks

- [Provision with Terraform, configure with Ansible](cookbook_provision_and_configure.rst):
  Apply Terraform, turn outputs into inventory, and configure the resulting hosts.
- [Application onboarding factory](cookbook_application_onboarding.rst): Build an
  idempotent project and workspace landing zone from an application definition.
- [Governed drift reconciliation](cookbook_governed_drift.rst): Detect drift,
  evaluate allow and deny rules, approve safe state reconciliation, and discard
  unsafe drift.
- [Event-driven post-apply automation](cookbook_event_driven_post_apply.rst):
  Route Terraform run notifications through EDA to configuration and failure
  workflows.
- [Ephemeral preview environments](cookbook_ephemeral_environment.rst): Create,
  configure, test, destroy, and delete a temporary environment in one lifecycle.

## Advanced Platform Cookbooks

- [Promote one known-good configuration](cookbook_promote_known_good_configuration.rst):
  Reuse one immutable configuration version across development, staging, and production.
- [Replace an agent pool blue-green](cookbook_agent_pool_blue_green.rst): Build and
  verify replacement private execution capacity before draining the old pool.
- [Run a fleet Terraform upgrade campaign](cookbook_fleet_upgrade_campaign.rst): Use
  Explorer, speculative runs, bounded batches, and automatic canary rollback.
- [Respond to drift through an EDA workflow](cookbook_event_driven_drift_response.rst):
  Route health-assessment events into analysis, approval, and an exact-run decision.
- [Migrate a workspace to dynamic credentials](cookbook_dynamic_credentials_migration.rst):
  Replace static cloud keys with workload identity and a reversible canary plan.
- [Decommission infrastructure safely](cookbook_governed_decommission.rst): Drain and
  back up applications before reviewing, applying, and recording a destroy run.
- [Rehearse disaster recovery end to end](cookbook_disaster_recovery_rehearsal.rst):
  Rebuild isolated infrastructure, restore data, validate recovery, and clean up.
- [Roll out compliance controls safely](cookbook_compliance_control_rollout.rst): Canary
  policies and run tasks in advisory mode before mandatory enforcement.
- [Publish a signed private provider](cookbook_private_provider_release.rst): Publish
  checksums, signatures, and multi-platform provider binaries to a private registry.
- [Govern day-two operations with Actions](cookbook_terraform_actions.rst): Preview,
  approve, invoke, and validate provider-defined Terraform Actions.
- [Rotate an HCP Terraform HYOK key](cookbook_hyok_key_rotation.rst): Test a new
  customer-managed key and retire the old configuration under separate approval.
- [Onboard and observe an HCP Terraform Stack](cookbook_stacks_observability.rst): Create
  a VCS-backed Stack and collect deployment, state, step, and diagnostic evidence.

## Scenario Guides

- [Workspaces and projects](guide_workspaces_projects.rst): Create, update,
  inspect, and remove core Terraform organizational resources.
- [Runs and configuration versions](guide_runs.rst): Upload configurations,
  queue runs, inspect plans, and gate applies.
- [Drift-safe Day 2 operations](guide_plan_analyze.rst): Detect and analyze
  drift with `plan_analyze`, `plan_guard`, and `plan_safe`.
- [Enforcing tf-policy compliance](guide_tf_policy.rst): Evaluate native
  Terraform policy outcomes and control workflow progression.
- [Variables and variable sets](guide_variables.rst): Manage workspace and
  variable-set values declaratively.
- [Teams and access](guide_teams_and_access.rst): Manage teams and workspace or
  project access grants.
- [Workspace bootstrap](guide_workspace_bootstrap.rst): Provision a workspace
  and its supporting resources in one idempotent workflow.
- [Private registry modules](guide_registry_modules.rst): Publish and manage
  modules in a private Terraform registry.

## Dynamic Inventory

- [Dynamic inventory](guide_dynamic_inventory.rst): Build Ansible inventory
  from Terraform state or workspace outputs.

## Lookup Plugins

- [Lookup plugins](guide_lookups.rst): Read Terraform outputs, state,
  variables, and workspace information inside playbooks and templates.

## Operating the Collection

- [Execution environments](guide_execution_environments.rst): Package the
  collection and its dependencies into an execution environment.
- [Troubleshooting](guide_troubleshooting.rst): Diagnose common installation,
  authentication, API, and runtime problems.
- [Compatibility and support](guide_compatibility.rst): Review supported
  versions, platforms, and support channels.

[Return to the collection README](../../../README.md).
