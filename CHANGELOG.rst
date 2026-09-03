============================================
Hashicorp Terraform Collection Release Notes
============================================

.. contents:: Topics

v2.2.1
======

Bugfixes
--------

- notification_configuration - Do not report perpetual drift for the write-only webhook token on an existing notification.
- policy_set and variable_sets - Normalize pytfe's Python-safe aliases for the global field so global=false remains idempotent.
- promote_run - Wait for post-apply completion, honor Terraform's is_confirmable capability, and support planned_and_saved runs.
- run - Poll for completion states appropriate to auto-apply, speculative, saved-plan, apply, discard, and cancel operations instead of accepting an unrelated intermediate state.

Documentation Changes
---------------------

- docs - Added five foundational and twelve advanced end-to-end cookbooks covering provisioning and configuration, application onboarding, governed drift, event-driven automation, ephemeral environments, immutable promotion, private agents, fleet upgrades, dynamic credentials, decommissioning, disaster recovery, compliance controls, private providers, Terraform Actions, HYOK rotation, and Stack observability. Added GitHub-readable navigation and aligned the getting-started dependency and installation guidance with Automation Hub and Git/source distribution.
- docs - Corrected examples after validating them against collection behavior.

v2.2.0
======

Minor Changes
-------------

- Add the read-only ``stack_diagnostic_info`` module to retrieve a stack diagnostic by ID through the PyTFE ``stack_diagnostics.read()`` SDK call.
- Added ``aws_oidc_configuration``, ``azure_oidc_configuration``, ``gcp_oidc_configuration``, and ``vault_oidc_configuration`` modules (each with an ``_info`` companion) to manage the HCP Terraform-side OIDC configuration record HYOK uses to authenticate to a customer KMS - most commonly as the ``oidc_configuration_id`` dependency of ``hyok_configuration``. None of the four create or manage cloud-side IAM/service-principal/workload-identity resources, only the HCP Terraform configuration record. Since the underlying API has no ``list`` endpoint and the record has no ``name`` field, ``state=present`` is only idempotent when ``oidc_configuration_id`` is supplied (read+diff+update); without it, every run creates a new record - documented explicitly in each module rather than silently duplicating.
- Added ``hyok_configuration`` and ``hyok_configuration_info`` modules to manage HCP Terraform HYOK (Hold Your Own Key) configurations, letting an organization encrypt workspace state/plan data with a customer-controlled KMS key. Since the underlying API has no update endpoint, ``hyok_configuration`` fails on ``state=present`` if the supplied options drift from an existing configuration rather than silently ignoring the drift or replacing the configuration - delete and recreate to change attributes. ``state=absent`` automatically revokes the configuration (polling for completion) before deleting, since the API rejects deleting a non-revoked configuration; set ``wait=false`` to only trigger the revoke. An optional ``test=true`` invokes and, by default, waits on the async key-access test action, failing the task on a ``test_failed`` result.
- Added a family of policy management modules: ``policy``/``policy_info`` (standalone Sentinel/OPA/tf-policy policies, with genuine content drift detection via the API's round-trippable upload/download), ``policy_set``/``policy_set_info`` (policy sets, including inline diff-and-sync of all five relationship types - policies, workspaces, workspace_exclusions, projects, project_exclusions - against a policy set's current membership), ``policy_set_version``/``policy_set_version_info`` (create-then-upload a new version for non-VCS-backed policy sets, mirroring ``configuration_version``'s shape), ``policy_set_parameter``/``policy_set_parameter_info`` (key/value parameters on a policy set, with the same sensitive-value write-only handling as the ``variable`` module), ``policy_evaluation_info`` and ``policy_set_outcome_info`` (read-only OPA policy evaluation results), and ``policy_check``/``policy_check_info`` (the legacy Sentinel policy-checks surface, extending the existing ``policy_check`` module_utils helper used by ``promote_run`` and the ``tf_policy_checks`` lookup - ``policy_check`` adds an idempotent override action). ``kind`` is immutable after creation on both ``policy`` and ``policy_set``; supplying a different value against an existing resource fails with a clear message rather than silently ignoring the drift.
- Adds a new module hashicorp.terraform.registry_provider for creating and deleting Terraform Cloud/Enterprise registry providers.
- Adds a new module hashicorp.terraform.registry_provider_info for fetching information about a Terraform Cloud/Enterprise registry provider.
- Adds new modules hashicorp.terraform.registry_provider_version and hashicorp.terraform.registry_provider_version_info for managing private registry provider versions on Terraform Cloud and Terraform Enterprise.
- Adds the new module hashicorp.terraform.stack_configuration for creating Terraform Cloud/Enterprise stack configuration snapshots.
- Adds the new module hashicorp.terraform.stack_configuration_info for retrieving information about a Terraform Cloud/Enterprise stack configuration.
- Adds the new module hashicorp.terraform.stack_deployment_group_info for retrieving information about Terraform Cloud/Enterprise stack deployment groups by ID or name.
- Adds the new module hashicorp.terraform.stack_deployment_run_info for retrieving information about Terraform Cloud/Enterprise stack deployment runs by ID.
- Adds the new module hashicorp.terraform.stack_deployment_step_info for retrieving information about Terraform Cloud/Enterprise stack deployment steps by ID.
- agent - new module to delete Terraform Cloud/Enterprise agents by ID.
- agent_info - new info module to retrieve information about a Terraform Cloud/Enterprise agent by ID.
- agent_token - new module to manage Terraform Cloud/Enterprise agent pool authentication tokens.
- agent_token_info - new module to retrieve information about Terraform Cloud/Enterprise agent pool authentication tokens.
- explorer - new module to create, update, and delete Terraform Cloud/Enterprise Explorer saved views with full idempotency and check-mode support.
- explorer_info - new read-only module to execute ad-hoc Explorer queries or read a saved view definition and its result rows.
- no_code_module - new module to manage Terraform Cloud/Enterprise no-code provisioning modules.
- no_code_module_info - new module to retrieve information about Terraform Cloud/Enterprise no-code provisioning modules.
- organization_token - New module ``hashicorp.terraform.organization_token`` to manage organization-scoped authentication tokens on Terraform Cloud and Terraform Enterprise. Supports creating and deleting the default organization token or the HCP Terraform Audit Trails token (``token_type=audit-trails``). Accepts an optional ``expired_at`` expiry timestamp. Fully idempotent on ``state=present`` with full ``check_mode`` support.
- plan_analyze module - New read-only module ``hashicorp.terraform.plan_analyze`` that parses a Terraform plan JSON document (fetched via a ``run_id`` / ``plan_id``, or supplied inline as ``plan_json``) and returns machine-friendly drift and change facts: ``has_drift`` / ``drift_count``, ``has_changes`` / ``change_count``, the changed and computed (unknown) attribute paths per resource, and a descriptive ``safe`` / ``risky`` / ``blocked`` / ``unknown`` classification with user-overridable, glob-based ``safe_attributes`` / ``risky_attributes`` / ``blocked_attributes`` rules (precedence ``blocked > risky > safe > unknown``). Rules default to empty (fail-closed) and are matched against a canonical ``<module_path>.<type>.<name>.<attribute.path>`` target, so they can be scoped by resource type/module rather than bare attribute names. Complements ``view_plan`` (human-readable diff) by exposing a programmatic drift-detection surface. Targets Terraform 1.x plan JSON; an unrecognized ``format_version`` warns and proceeds best-effort rather than failing the task.
- plan_guard filter / plan_safe test - New pure, offline plugins ``hashicorp.terraform.plan_guard`` (filter) and ``hashicorp.terraform.plan_safe`` (test) that evaluate a ``plan_analyze`` result against user-defined ``allow`` / ``deny`` rules and return an auditable ``safe_to_refresh`` decision for gating a refresh-only apply that absorbs approved drift into Terraform state. Unlike a module, both are usable inline (for example directly in ``when:``) since they perform no I/O and never fork a Python interpreter. Rules use the same canonical attribute-matching grammar as ``plan_analyze`` classification; ``deny`` always wins over ``allow``, ``strict`` mode (default) is fail-closed, and a resource ``plan_analyze`` already classified ``blocked`` is escalated unconditionally. Not a replacement for TFE-native Sentinel/OPA policy checks.
- public_registry_module_info - new module to retrieve information about modules from the public Terraform Registry (registry.terraform.io).
- registry_module - new module to manage Terraform Cloud/Enterprise private registry modules (https://github.com/hashicorp/terraform-ansible-collection/pull/168).
- registry_module_info - new module to retrieve information about Terraform Cloud/Enterprise private registry modules (https://github.com/hashicorp/terraform-ansible-collection/pull/168).
- registry_provider_platform - new module to manage Terraform Cloud/Enterprise registry provider platforms.
- registry_provider_platform_info - new module to retrieve information about Terraform Cloud/Enterprise registry provider platforms.
- reserved_tag_keys - New module to create, update, and delete Terraform Cloud/Enterprise reserved tag keys.
- run_task module - New module ``hashicorp.terraform.run_task`` to create, update, and delete organization-scoped run tasks on Terraform Cloud and Terraform Enterprise. Supports identifying a run task by ``run_task_id`` or by ``(organization, name)``, configuring the invocation ``url``, ``description``, ``enabled`` flag, optional ``hmac_key`` (write-only), ``agent_pool_id``, and a ``global_configuration`` block (``enabled`` / ``stages`` / ``enforcement_level``). Idempotent on ``present`` with ``check_mode`` support.
- run_task_info module - New module ``hashicorp.terraform.run_task_info`` to retrieve run task details by ``run_task_id``, by ``(organization, name)``, or list every run task in an organization.
- stack - New module to create, update, and delete Terraform Cloud/Enterprise stacks (https://github.com/hashicorp/terraform-ansible-collection/pull/163).
- stack_info - New module to retrieve information about Terraform Cloud/Enterprise stacks (https://github.com/hashicorp/terraform-ansible-collection/pull/163).
- stack_state_info - New read-only module to retrieve information about a Terraform Cloud/Enterprise stack state by its unique ID.
- task_result_info module - New module ``hashicorp.terraform.task_result_info`` to read a single run task result by ``task_result_id`` on Terraform Cloud and Terraform Enterprise.
- task_stage_info module - New module ``hashicorp.terraform.task_stage_info`` to read a single run task stage by ``task_stage_id`` (optionally sideloading related resources via ``include``) or list every task stage for a run by ``run_id``, on Terraform Cloud and Terraform Enterprise.
- team_token - New module to create and delete Terraform Cloud and Terraform Enterprise team tokens, with idempotent team-token management.
- team_token_info - New module to retrieve read-only information about Terraform Cloud and Terraform Enterprise team tokens by team ID or token ID.
- tf_policy_evaluation - New module to override a Terraform policy (tf-policy) evaluation that is awaiting override.
- tf_policy_evaluation_info - New module to read Terraform policy (tf-policy) evaluations and set outcomes for a run.
- tfc_inv inventory - Add an optional ``hostvars`` option with ``include`` and ``exclude`` lists to shape which top-level source attributes are emitted as Ansible host variables. ``include`` limits emitted host vars to the listed keys, ``exclude`` removes listed keys, and ``exclude`` wins when a key appears in both; unknown keys are ignored. Shaping affects only the emitted host vars - ``compose``, ``hostnames``, ``keyed_groups``, ``groups``, and the filter options continue to resolve against the full sanitized data, and the plugin-injected ``ansible_host`` / ``value`` / ``tfc_workspace_id`` / ``tfc_workspace_name`` variables are always emitted. When ``hostvars`` is omitted, behavior is unchanged.
- workspace_run_task module - New module ``hashicorp.terraform.workspace_run_task`` to associate an existing organization run task with a workspace, update its enforcement level and run stages, or remove the association, on Terraform Cloud and Terraform Enterprise. The workspace is identified by ``workspace_id`` or ``(organization, workspace)``, and the run task by ``run_task_id`` or ``run_task_name``; an existing association can also be targeted by ``workspace_run_task_id``. Idempotent on ``present`` with ``check_mode`` support.
- workspace_run_task_info module - New module ``hashicorp.terraform.workspace_run_task_info`` to retrieve a workspace run task association by ``workspace_run_task_id`` or by run task, or list every run task associated with a workspace.

New Plugins
-----------

Filter
~~~~~~

- plan_guard - Evaluate a plan\_analyze result against allow/deny drift rules

Test
~~~~

- plan_safe - Test whether a plan\_analyze result is safe to refresh under allow/deny drift rules

New Modules
-----------

- agent - Manage Terraform Cloud/Enterprise agents (delete).
- agent_info - Retrieve information about a Terraform Cloud/Enterprise agent.
- agent_token - Manage Terraform Cloud/Enterprise agent pool tokens.
- agent_token_info - Retrieve information about a Terraform Cloud/Enterprise agent token.
- aws_oidc_configuration - Manage HCP Terraform AWS OIDC configurations for HYOK.
- aws_oidc_configuration_info - Retrieve information about an HCP Terraform AWS OIDC configuration.
- azure_oidc_configuration - Manage HCP Terraform Azure OIDC configurations for HYOK.
- azure_oidc_configuration_info - Retrieve information about an HCP Terraform Azure OIDC configuration.
- explorer - Manage Terraform Cloud/Enterprise Explorer saved views.
- explorer_info - Query the Terraform Cloud/Enterprise Explorer API (read\-only).
- gcp_oidc_configuration - Manage HCP Terraform GCP OIDC configurations for HYOK.
- gcp_oidc_configuration_info - Retrieve information about an HCP Terraform GCP OIDC configuration.
- hyok_configuration - Manage HCP Terraform HYOK (Hold Your Own Key) configurations.
- hyok_configuration_info - Retrieve information about HCP Terraform HYOK (Hold Your Own Key) configurations.
- no_code_module - Manage Terraform Cloud/Enterprise no\-code modules.
- no_code_module_info - Retrieve information about a Terraform Cloud/Enterprise no\-code module.
- organization_token - Manage Terraform Cloud/Enterprise organization tokens.
- plan_analyze - Analyze a Terraform plan for drift and change classification
- policy - Manage Terraform Cloud/Enterprise policies (Sentinel, OPA, or tf\-policy).
- policy_check - Override a soft\-mandatory Terraform Cloud/Enterprise policy check.
- policy_check_info - Retrieve Sentinel policy check outcomes for a Terraform Cloud/Enterprise run.
- policy_evaluation_info - List OPA policy evaluations for a Terraform Cloud/Enterprise task stage.
- policy_info - Retrieve information about a Terraform Cloud/Enterprise policy.
- policy_set - Manage Terraform Cloud/Enterprise policy sets and their memberships.
- policy_set_info - Retrieve information about a Terraform Cloud/Enterprise policy set.
- policy_set_outcome_info - Retrieve OPA policy set outcomes for a Terraform Cloud/Enterprise policy evaluation.
- policy_set_parameter - Manage parameters on a Terraform Cloud/Enterprise policy set.
- policy_set_parameter_info - Retrieve information about Terraform Cloud/Enterprise policy set parameters.
- policy_set_version - Create and upload a Terraform Cloud/Enterprise policy set version.
- policy_set_version_info - Retrieve information about a Terraform Cloud/Enterprise policy set version.
- public_registry_module_info - Retrieve information about a module from the public Terraform Registry.
- registry_module - Manage Terraform Cloud/Enterprise private registry modules.
- registry_module_info - Retrieve information about a Terraform Cloud/Enterprise private registry module.
- registry_provider - Manage Terraform Cloud/Enterprise registry providers.
- registry_provider_info - Retrieve information about a Terraform Cloud/Enterprise registry provider.
- registry_provider_platform - Manage Terraform Cloud/Enterprise registry provider platforms.
- registry_provider_platform_info - Retrieve information about a Terraform Cloud/Enterprise registry provider platform.
- registry_provider_version - Manage Terraform Cloud/Enterprise private registry provider versions.
- registry_provider_version_info - Retrieve information about a Terraform Cloud/Enterprise private registry provider version.
- reserved_tag_keys - Manage Terraform Cloud/Enterprise reserved tag keys (create, update, delete).
- run_task - Manage Terraform Cloud/Enterprise run tasks (create, update, delete).
- run_task_info - Retrieve information about Terraform Cloud/Enterprise run tasks.
- stack - Manage Terraform Cloud/Enterprise stacks (create, update, delete).
- stack_configuration - Create a Terraform stack configuration snapshot.
- stack_configuration_info - Retrieve information about a Terraform stack configuration.
- stack_deployment_group_info - Retrieve information about a Terraform Cloud/Enterprise stack deployment group.
- stack_deployment_run_info - Retrieve information about a Terraform Cloud/Enterprise stack deployment run.
- stack_deployment_step_info - Retrieve information about a Terraform Cloud/Enterprise stack deployment step.
- stack_diagnostic_info - Retrieve information about a Terraform Cloud/Enterprise stack diagnostic.
- stack_info - Retrieve information about Terraform Cloud/Enterprise stacks.
- stack_state_info - Retrieve information about a Terraform Cloud/Enterprise stack state.
- task_result_info - Retrieve information about a Terraform Cloud/Enterprise task result.
- task_stage_info - Retrieve information about Terraform Cloud/Enterprise task stages.
- team_token - Manage Terraform Cloud and Terraform Enterprise team tokens.
- team_token_info - Retrieve information about a Terraform Cloud and Terraform Enterprise team token.
- tf_policy_evaluation - Override a Terraform policy (tf\-policy) evaluation.
- tf_policy_evaluation_info - Read Terraform policy (tf\-policy) evaluations and set outcomes for a run.
- vault_oidc_configuration - Manage HCP Terraform Vault OIDC configurations for HYOK.
- vault_oidc_configuration_info - Retrieve information about an HCP Terraform Vault OIDC configuration.
- workspace_run_task - Associate and manage run tasks on a Terraform Cloud/Enterprise workspace.
- workspace_run_task_info - Retrieve information about run tasks associated with a workspace.

v2.1.0
======

Release Summary
---------------

This release adds team and access-management modules (teams, team info, team-project access, and team-workspace access), user information, and organization-tag association. The ``variable`` module can now manage variables inside a variable set via C(variable_set_id). It also extends the dynamic inventory plugin with Ansible-standard caching and multi-workspace scanning, adds Terraform refresh-only and action-only runs, and supports parent relationships when creating variable sets.

Minor Changes
-------------

- Added ``meta/execution-environment.yml`` so that Ansible Builder automatically installs the collection's controller-side Python dependency (``pytfe>=1.2.0``) when the collection is included in an execution environment.
- authentication - The ``tfe_token`` option is no longer marked ``required`` on modules and lookups. When omitted, it falls back to the ``TFE_TOKEN`` environment variable, so tasks can authenticate purely from the environment (for example via ``module_defaults``) without ansible-lint reporting a missing required argument.
- docs - Added a set of scenario guides to the collection docsite under ``docs/docsite/rst/`` (getting started, authentication, workspaces and projects, runs and configuration versions, variables and variable sets, teams and access, workspace bootstrap, dynamic inventory, lookup plugins, execution environments, troubleshooting, and compatibility), along with the ``docs/docsite/extra-docs.yml`` and ``docs/docsite/config.yml`` docsite configuration.
- inventory - Added an opt-in ``cache_validate_current_state_version`` option (default ``false``). When enabled, each run resolves the workspace's current Terraform state version ID and reuses cached data only when the IDs match, otherwise the cache is overwritten with fresh data. This trades the offline-friendliness of the default mode for apply-aware freshness; if the validation API call fails, the plugin raises rather than serve stale cache.
- inventory - Default cache hits skip all upstream API calls — workspace resolution, state download, and outputs fetch are all bypassed, so subsequent ``ansible-inventory`` invocations within the ``cache_timeout`` window are fast and offline-capable. Use ``--flush-cache`` to force a refresh after a Terraform apply if you do not want to wait for the timeout.
- inventory - Every host produced in multi-workspace mode is stamped with auto-injected ``tfc_workspace_id`` and ``tfc_workspace_name`` variables so playbooks can route by origin. These names are exempt from ``hostvars_prefix`` / ``hostvars_suffix`` renaming.
- inventory - In multi-workspace mode with ``cache_validate_current_state_version: true``, a workspace whose ``state_versions.read_current()`` call fails is excluded from inventory with a warning rather than failing the whole sync. This is a more lenient contract than single-workspace mode (which raises), justified by the "fan-out" nature of filter mode where one workspace being unreachable should not block the rest.
- inventory - Multi-workspace mode reuses the existing per-workspace cache blob shape unchanged (so a workspace cached in single-workspace mode by ID is bit-for-bit reusable in filter mode) and adds a separate B(selector cache) keyed by ``(source, organization, workspace_filters)`` that eliminates the workspace list API call on warm runs. With both layers warm, multi-workspace inventory is fully offline-capable within ``cache_timeout`` — the same contract as single-workspace mode.
- inventory - New ``enable_parallel_processing`` option (default ``false``) and ``concurrency`` option (default ``5``, hard cap ``10``) drive concurrent per-workspace fetches via a thread pool. Each worker constructs its own pytfe client; Ansible inventory mutation always happens on the main thread.
- inventory - The ``hashicorp.terraform.tfc_inv`` dynamic inventory plugin now stamps a component tag onto the HCP Terraform/Enterprise ``User-Agent`` so usage telemetry can distinguish dynamic-inventory traffic. The base ``terraform-ansible-collection/<version>`` token is preserved verbatim (aggregate usage queries are unaffected) and an RFC 7231 comment is appended, for example ``(inventory:tfc_inv; source=statefile; mode=single)``, identifying the plugin, the data source (``statefile`` or ``outputs``), and single vs multi-workspace mode.
- inventory - The ``hashicorp.terraform.tfc_inv`` dynamic inventory plugin now supports Ansible-standard caching via the ``Cacheable`` mixin and the ``inventory_cache`` documentation fragment. All five standard options are exposed (``cache``, ``cache_plugin``, ``cache_connection``, ``cache_prefix``, ``cache_timeout``), matching the ``aws_ec2`` / ``azure_rm`` / ``kubernetes.core.k8s`` convention.
- inventory - The ``hashicorp.terraform.tfc_inv`` dynamic inventory plugin now supports B(multi-workspace mode). Setting the new ``workspace_filters`` option (mutually exclusive with ``workspace`` / ``workspace_id``) enumerates every matching workspace via the HCP Terraform Workspaces list API and merges inventory across them. Supported filter keys map onto pytfe's ``WorkspaceListOptions``: ``project_id``, ``name_search``, ``tags``, ``exclude_tags``, ``wildcard_name``, ``current_run_status``, ``sort``, ``page_size``. Project name resolution is not supported; pass the project ID directly (``prj-...``).
- inventory statefile source - Sensitive Terraform attributes (paths flagged in the state's ``sensitive_attributes``) are stripped from the state body before it is written to the Ansible cache. Persistent cache files (e.g. under ``~/.ansible/cache/``) therefore never contain values Terraform marked sensitive.
- modules - Added ``hashicorp.terraform.agent_pool`` and ``hashicorp.terraform.agent_pool_info`` for managing and inspecting Terraform Cloud/Enterprise agent pools. Agent pools group Terraform Cloud Agents so that C(execution_mode=agent) workspaces and projects can run on private, self-hosted infrastructure. The ``agent_pool`` module supports organization scoping and per-workspace/per-project allow and exclude lists; ``agent_pool_info`` can read a pool by ID, look one up by name, or list all pools in an organization.
- modules - Added ``hashicorp.terraform.team``, ``hashicorp.terraform.team_info``, ``hashicorp.terraform.team_project_access``, ``hashicorp.terraform.team_workspace_access``, ``hashicorp.terraform.user_info``, and ``hashicorp.terraform.organization_tags`` for managing teams, team access to projects and workspaces, user information, and organization-tag/workspace associations. The ``team_info`` module can retrieve a single team by ID, list all teams in an organization, or look one up by name.
- run - Added invoke_action_addrs option to trigger Terraform Actions runs, allowing invocation of ephemeral provider operations (e.g., AWS Lambda) at specified action addresses without creating, changing, or destroying managed resources. Produces a run with operation type action_only.
- run - Added refresh_only option to trigger a Terraform refresh-only run that syncs state to match real infrastructure without making any changes. Compatible with auto_apply; mutually exclusive with is_destroy, plan_only, and save_plan (https://github.com/hashicorp/terraform-ansible-collection/issues/133).
- tf_org_tags lookup - New lookup plugin ``hashicorp.terraform.tf_org_tags`` that returns all organization tags as a list of dicts (``id``, ``name``, ``instance_count``).  Supports an optional ``query`` parameter for partial-name filtering (maps to ``?q=`` on the API) and an optional ``filter_exclude_taggable_id`` parameter that excludes tags already associated with a given workspace (maps to ``?filter[exclude][taggable][id]=``), making it easy to discover which tags are available to add to a specific workspace.
- variable - Added the ``variable_set_id`` option so the ``variable`` module can manage variables inside a variable set in addition to workspace variables. This mirrors the ``tfe_variable`` resource in the Terraform ``tfe`` provider, which is scoped by either ``workspace_id`` or ``variable_set_id``.
- variable_sets - The ``variable_sets`` module now supports setting a parent relationship on creation via the new ``parent_project_id`` and ``parent_organization_name`` options.

Bugfixes
--------

- ``hashicorp.terraform.run`` with ``state: present`` and a ``run_message`` value now correctly propagates the message to HCP Terraform.
- project - Fixed idempotent runs returning only ``changed=false`` with no resource data; the module now returns the full project attributes (including ``id``, ``name``, ``description``, etc.) even when no changes are made.
- workspace - Fixed idempotent runs returning only ``changed=false`` with no resource data; the module now returns the full workspace attributes (including ``id``, ``name``, ``execution_mode``, etc.) even when no changes are made.
- workspace_info - Corrected the module's ``RETURN`` documentation and examples, which still described the old JSON:API response shape (``workspace.attributes.*``). The module returns the workspace fields flattened at the top level (for example ``workspace.name``, ``workspace.execution_mode``), so the previous examples would fail at runtime with ``'dict object' has no attribute 'attributes'``.

New Plugins
-----------

Lookup
~~~~~~

- tf_org_tags - List organization tags in Terraform Cloud/Enterprise

New Modules
-----------

- agent_pool - Manage Terraform Cloud/Enterprise agent pools (create, update, delete).
- agent_pool_info - Retrieve information about Terraform Cloud/Enterprise agent pools.
- organization_tags - Manage Terraform Cloud/Enterprise organization tags (create, associate workspaces, delete).
- team - Manage teams in Terraform Cloud/Enterprise.
- team_info - Retrieve information about a team in Terraform Cloud/Enterprise.
- team_project_access - Manage team access grants on a Terraform Cloud/Enterprise project.
- team_workspace_access - Manage team access grants on a Terraform Cloud/Enterprise workspace.
- user_info - Retrieve information about a user in Terraform Cloud/Enterprise.

v2.0.0
======

Release Summary
---------------

Version 2.0.0 migrates the collection to the official pytfe SDK, updates the public authentication surface to ``tfe_*`` options, expands Terraform Cloud/Enterprise workspace management coverage, and adds a dynamic inventory plugin for statefile and outputs based inventory.

Major Changes
-------------

- client - Added a shared pytfe-backed ``TerraformClient`` lifecycle wrapper for modules, lookups, action plugins, and inventory plugins. The wrapper centralizes token/address handling, timeout, retry, TLS verification, CA bundle, proxy, and collection ``User-Agent`` suffix configuration.
- module_utils - Removed the collection's custom request/session and local response-model layer in favor of the first-class pytfe SDK and pytfe's response models.

Minor Changes
-------------

- actions - Added ``hashicorp.terraform.promote_run`` to gate and optionally apply a run based on Sentinel policy-check outcomes, and ``hashicorp.terraform.workspace_bootstrap`` to converge workspace settings, variables, variable-set attachments, run triggers, and notification configurations in one idempotent task.
- inventory - Added the ``hashicorp.terraform.tfc_inv`` dynamic inventory plugin for HCP Terraform and Terraform Enterprise. The plugin supports ``source=outputs`` and ``source=statefile``, targets a single workspace by ``workspace_id`` or by ``organization`` plus ``workspace``, uses the pytfe SDK, supports constructed inventory features, and does not require the Terraform CLI or direct backend credentials.
- inventory outputs source - Added ``source=outputs`` to build hosts from current state version outputs. The source supports ``hosts_from`` mappings using Terraform type expressions for primitives, objects, lists, sets, maps, tuples, and dynamic values, including automatic ``ansible_host`` assignment for primitive shapes when ``compose`` is empty.
- inventory outputs source - Object-shaped outputs spread user fields at the top level of host variables; primitive-shaped outputs expose the scalar as ``value``; map-shaped outputs use the map key as the inventory hostname. ``hostvars_prefix`` and ``hostvars_suffix`` can namespace user fields while leaving plugin-injected ``ansible_host`` and ``value`` unchanged.
- inventory outputs source - Sensitive outputs are fetched with ``display_sensitive=False`` and are masked by the shared output helper unless the API omits the value.
- inventory statefile source - Added ``source=statefile`` to build hosts from the latest Terraform state version. The source supports Terraform state v4, managed resources, optional child-module traversal with ``search_child_modules``, built-in mappings for common AWS, AzureRM, and Google compute resources, custom ``provider_mapping`` entries, attribute and tag-based hostname preferences, include/exclude filters, and keyed groups.
- inventory statefile source - Terraform resource attributes marked in ``sensitive_attributes`` are stripped before host variables are emitted. Sensitive values are dropped rather than masked, and stripped values are not available to hostname resolution, filters, compose, groups, or keyed groups.
- lookups - Added ``hashicorp.terraform.tf_policy_checks``, ``hashicorp.terraform.tf_run_events``, and ``hashicorp.terraform.tf_variable_set_vars`` for policy-check gating, run timeline inspection, and variable-set variable retrieval. Sensitive variable-set values are masked by default.
- module_utils - Added pytfe-backed helpers for notification configurations, organizations, run events, run triggers, SSH keys, workspace variables, variable-set variables, and variable sets.
- modules - Added ``hashicorp.terraform.notification_configuration``, ``hashicorp.terraform.organizations``, ``hashicorp.terraform.run_trigger``, ``hashicorp.terraform.ssh_keys``, ``hashicorp.terraform.variable``, and ``hashicorp.terraform.variable_sets``.
- modules - The previously released modules (``configuration_version``, ``configuration_version_info``, ``output``, ``project``, ``project_info``, ``run``, ``run_info``, ``view_plan``, ``workspace``, ``workspace_info``) have been re-implemented on the pytfe SDK. Public module parameters are unchanged apart from the shared authentication surface migration noted in breaking_changes.

Breaking Changes / Porting Guide
--------------------------------

- authentication - The canonical authentication and transport options are now ``tfe_token``, ``tfe_address``, ``tfe_timeout``, ``tfe_verify_tls``, ``tfe_max_retries``, ``tfe_ca_bundle``, and ``tfe_proxies``. The ``tf_token`` option remains as an alias for ``tfe_token`` for compatibility, but old transport names such as ``tf_hostname``, ``tf_validate_certs``, ``tf_timeout``, and ``tf_max_retries`` are not supported by the pytfe-backed client. The primary environment variables also move to ``TFE_TOKEN`` and ``TFE_ADDRESS``.
- client - The collection now uses a shared pytfe-backed client wrapper (``plugins/module_utils/client.py``) instead of the removed ``plugins/module_utils/common.py`` request helpers. Custom plugins or automation that imported the internal ``common`` module must migrate to ``AnsibleTerraformModule`` and ``TerraformClient`` from ``plugins/module_utils/client.py``.

Bugfixes
--------

- modules - Preserved task invocation parameters in module results so module code does not override the invocation data reported by Ansible.
- run - Increased the default run polling timeout to 120 seconds to avoid premature timeout failures on normal Terraform Cloud/Enterprise runs.

New Plugins
-----------

Inventory
~~~~~~~~~

- inventory - Unified dynamic inventory plugin for HCP Terraform / Terraform Enterprise.
- tfc_inv - Unified dynamic inventory plugin for HCP Terraform / Terraform Enterprise.

Lookup
~~~~~~

- tf_policy_checks - Retrieve Sentinel policy check outcomes for a run
- tf_run_events - Retrieve the timeline of events for a Terraform Cloud/Enterprise run
- tf_variable_set_vars - Retrieve variables owned by a Terraform Cloud/Enterprise variable set

New Modules
-----------

- notification_configuration - Manage Terraform Cloud/Enterprise workspace notification configurations (create, update, delete).
- organizations - Manage Terraform Cloud/Enterprise organizations (create, update, delete).
- promote_run - Gate and apply a Terraform Cloud/Enterprise run based on policy outcomes.
- run_trigger - Manage Terraform Cloud/Enterprise run triggers (create, delete).
- ssh_keys - Manage Terraform Cloud/Enterprise organization SSH keys (create, update, delete).
- variable - Manage Terraform Cloud/Enterprise workspace variables (create, update, delete).
- variable_sets - Manage Terraform Cloud/Enterprise variable sets (create, update, delete, attach).
- workspace_bootstrap - Converge a Terraform Cloud/Enterprise workspace baseline in a single task.

v1.2.0
======

Minor Changes
-------------

- Adds a new module hashicorp.terraform.output for retrieving state version outputs information from TFE/C.
- Adds a new module hashicorp.terraform.project for project management on TFE/C.

Bugfixes
--------

- Increased the default poll_timeout for the run module to 120s. The previous default of 25s was low and caused issues in tasks.

New Plugins
-----------

Lookup
~~~~~~

- tf_output - Retrieve Terraform Cloud/Enterprise output values

New Modules
-----------

- output - Retrieve Terraform Cloud/Enterprise state version outputs
- project - Manage Terraform Cloud/Enterprise projects (create, update, delete).
- project_info - Gather information about a project in Terraform Enterprise/Cloud.

v1.1.0
======

Minor Changes
-------------

- Adds a new module hashicorp.terraform.configuration_version_info to fetch information about a configuration version in TFE/C.
- Adds a new module hashicorp.terraform.run_info to fetch information about a run in TFE/C.
- Adds a new module hashicorp.terraform.view_plan for retrieving plan information from TFE/C.
- Adds a new module hashicorp.terraform.workspace for workspace management on TFE/C.
- Adds a new module hashicorp.terraform.workspace_info to fetch information about a workspace in TFE/C.

Bugfixes
--------

- Ensures module invocation parameters in the task execution result aren't overridden by module code logic.

New Modules
-----------

- configuration_version_info - Retrieve information about configuration versions in Terraform Enterprise/Cloud.
- run_info - Retrieve information about a run in Terraform Enterprise/Cloud.
- view_plan - View Terraform Cloud/Enterprise plan information
- workspace - Manage workspaces in Terraform Enterprise/Cloud.
- workspace_info - Gather information about a workspace in Terraform Enterprise/Cloud.

v1.0.0
======

Release Summary
---------------

This marks the first release of the hashicorp.terraform collection.

Minor Changes
-------------

- Adds a new module hashicorp.terraform.configuration_version for configuration-version management on TFE/C.
- Adds a new module hashicorp.terraform.run for run management on TFE/C.

New Modules
-----------

- configuration_version - Manage configuration versions in Terraform Enterprise/Cloud.
- run - Manage Terraform Cloud/Enterprise runs (create, apply, cancel, discard).
