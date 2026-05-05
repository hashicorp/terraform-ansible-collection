============================================
Hashicorp Terraform Collection Release Notes
============================================

.. contents:: Topics

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
