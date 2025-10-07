============================================
Hashicorp Terraform Collection Release Notes
============================================

.. contents:: Topics

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
