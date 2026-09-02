# HashiCorp Terraform Collection Guides

These guides show how to integrate Ansible with HCP Terraform and Terraform
Enterprise. They complement the plugin reference available through Automation
Hub and `ansible-doc`.

## Getting Started

- [Getting started](guide_getting_started.rst): Install the collection and run
  your first task.
- [Authentication](guide_authentication.rst): Configure API tokens, Terraform
  Enterprise endpoints, TLS, proxies, timeouts, and retries.

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
