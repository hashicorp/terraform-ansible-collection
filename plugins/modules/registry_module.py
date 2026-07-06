#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
DOCUMENTATION = r"""
---
module: registry_module
version_added: "2.2.0"
short_description: Manage Terraform Cloud/Enterprise private registry modules.
author: "Nimisha Shrivastava (@nimisha-shrivastava)"
description:
  - Manages private registry modules on Terraform Cloud and Terraform Enterprise.
  - Registry modules allow you to publish and share Terraform modules within your organization.
  - Supports creating modules with or without VCS connection, creating versions, and managing module lifecycle.
  - Identify a module by C(organization), C(name), and C(provider).
  - The C(present) state creates the module if it does not exist, or updates it when configuration drifts.
  - The C(absent) state deletes the module, provider, or specific version based on provided parameters.
  - Compatible with both Terraform Cloud and Terraform Enterprise.
extends_documentation_fragment: hashicorp.terraform.common
options:
  organization:
    description:
      - The name of the organization that owns the registry module.
      - Required for all operations.
    type: str
    required: true
  name:
    description:
      - The name of the registry module.
      - Required for create and update operations.
    type: str
  provider:
    description:
      - The provider name for the registry module (e.g., C(aws), C(azurerm), C(google)).
      - Required when identifying a specific provider variant of a module.
    type: str
  registry_name:
    description:
      - The registry name (C(private) or C(public)).
      - Defaults to C(private).
    type: str
    choices: ["private", "public"]
    default: "private"
  namespace:
    description:
      - The namespace for the registry module.
      - For private modules, this defaults to the organization name.
      - Required for public modules.
    type: str
  no_code:
    description:
      - Whether this is a no-code module.
      - No-code modules can be provisioned without writing Terraform configuration.
    type: bool
  vcs_repo:
    description:
      - VCS repository configuration for the module.
      - Required when creating a module with VCS connection.
    type: dict
    suboptions:
      identifier:
        description:
          - The repository identifier (e.g., C(org/repo) for GitHub).
        type: str
        required: true
      oauth_token_id:
        description:
          - The OAuth token ID for VCS authentication.
        type: str
      display_identifier:
        description:
          - The display identifier for the repository.
        type: str
      branch:
        description:
          - The branch to use for the module.
        type: str
      tags:
        description:
          - Whether to use tags for versioning.
        type: bool
      organization_name:
        description:
          - The organization name (required when using branch).
        type: str
  test_config:
    description:
      - Test configuration for the module.
    type: dict
    suboptions:
      tests_enabled:
        description:
          - Whether tests are enabled for this module.
        type: bool
  version:
    description:
      - The version string for creating a new module version.
      - Required when O(operation=create_version).
      - Must follow semantic versioning (e.g., C(1.0.0)).
    type: str
  archive:
    description:
      - Path to a tar.gz archive file to upload after creating a version.
      - Only used with O(operation=create_version).
      - The archive should contain the Terraform module files.
    type: path
  operation:
    description:
      - The operation to perform on the registry module.
      - C(create) creates a module without VCS.
      - C(create_with_vcs) creates a module with VCS connection.
      - C(create_version) creates a new version for an existing module.
      - C(update) updates module properties.
      - C(delete) removes the module (use with O(delete_scope)).
    type: str
    choices: ["create", "create_with_vcs", "create_version", "update", "delete"]
  delete_scope:
    description:
      - Scope of deletion when O(operation=delete).
      - C(module) deletes the entire module (all providers and versions).
      - C(provider) deletes a specific provider and all its versions.
      - C(version) deletes a specific version.
    type: str
    choices: ["module", "provider", "version"]
  state:
    description:
      - Desired state of the registry module.
      - C(present) creates or updates the module.
      - C(absent) deletes the module based on O(delete_scope).
    type: str
    choices: ["present", "absent"]
    default: "present"
"""

EXAMPLES = r"""
- name: Create a private registry module without VCS
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    operation: "create"
    state: present
  register: module

- name: Create a registry module with VCS connection
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    namespace: "my-org"
    operation: "create_with_vcs"
    vcs_repo:
      identifier: "my-org/terraform-aws-vpc"
      oauth_token_id: "ot-abc123"
      display_identifier: "my-org/terraform-aws-vpc"
    state: present
  register: module_vcs

- name: Create a new version for a registry module
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.0"
    operation: "create_version"
    state: present
  register: version

- name: Create a version and upload archive
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.1"
    archive: "/path/to/module.tar.gz"
    operation: "create_version"
    state: present
  register: version_with_upload

- name: Update registry module properties
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    no_code: true
    operation: "update"
    state: present

- name: Delete a specific version
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.0"
    operation: "delete"
    delete_scope: "version"
    state: absent

- name: Delete a specific provider
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    operation: "delete"
    delete_scope: "provider"
    state: absent

- name: Delete entire module (all providers)
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    operation: "delete"
    delete_scope: "module"
    state: absent
"""

RETURN = r"""
changed:
  description: Whether the module made a change.
  returned: always
  type: bool
  sample: true
id:
  description: The registry module identifier.
  returned: when state is present and operation is not create_version
  type: str
  sample: "mod-abc123"
name:
  description: The registry module name.
  returned: when state is present
  type: str
  sample: "vpc"
provider:
  description: The provider name.
  returned: when state is present
  type: str
  sample: "aws"
registry_name:
  description: The registry name (private or public).
  returned: when state is present
  type: str
  sample: "private"
namespace:
  description: The namespace for the module.
  returned: when state is present
  type: str
  sample: "my-org"
status:
  description: The module status.
  returned: when state is present
  type: str
  sample: "pending"
version:
  description: The version string.
  returned: when operation is create_version
  type: str
  sample: "1.0.0"
links:
  description: Links related to the resource (includes upload URL for versions).
  returned: when operation is create_version
  type: dict
  sample: {"upload": "https://archivist.terraform.io/v1/object/..."}
msg:
  description: Informational message, primarily for delete, no-op, and check mode operations.
  returned: when relevant
  type: str
  sample: "Registry module vpc has been deleted successfully"
"""

from copy import deepcopy
from typing import Any, Dict, Optional

from ansible.module_utils._text import to_text

from ansible_collections.hashicorp.terraform.plugins.module_utils.registry_module import (
    create_registry_module,
    create_registry_module_version,
    create_registry_module_with_vcs,
    delete_registry_module_by_name,
    delete_registry_module_provider,
    delete_registry_module_version,
    get_registry_module,
    get_registry_module_version,
    update_registry_module,
    upload_registry_module_version,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient


def _build_module_id(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build a module ID dict from params."""
    return {
        "organization": params.get("organization"),
        "name": params.get("name"),
        "provider": params.get("provider"),
        "namespace": params.get("namespace"),
        "registry_name": params.get("registry_name", "private"),
    }


def _fetch_registry_module(adapter: TerraformClient, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve the target registry module using direct read API."""
    organization = params.get("organization")
    name = params.get("name")
    provider = params.get("provider")
    
    if organization and name and provider:
        module_id = _build_module_id(params)
        return get_registry_module(adapter, module_id)
    return None


def _has_drift(params: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if any user-specified field differs from the current module."""
    if params.get("no_code") is not None and params["no_code"] != current.get("no_code"):
        return True
    return False


def state_present(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Create or update a registry module to match the desired state."""
    operation = params.get("operation", "create")
    
    if operation == "create":
        # Check if module already exists
        current = _fetch_registry_module(adapter, params)
        if current is not None:
            return {"changed": False, **current}
        
        if check_mode:
            return {
                "changed": True,
                "msg": f"Registry module {params.get('name')} would be created. Skipped creation due to check mode.",
                "name": params.get("name"),
            }
        
        created = create_registry_module(adapter, params["organization"], {
            "name": params["name"],
            "provider": params["provider"],
            "registry_name": params.get("registry_name", "private"),
            "namespace": params.get("namespace"),
            "no_code": params.get("no_code"),
        })
        return {"changed": True, **created}
    
    elif operation == "create_with_vcs":
        if not params.get("vcs_repo"):
            raise ValueError("'vcs_repo' is required when operation is 'create_with_vcs'")
        
        # Check if module already exists
        if params.get("name") and params.get("provider"):
            current = _fetch_registry_module(adapter, params)
            if current is not None:
                return {"changed": False, **current}
        
        if check_mode:
            return {
                "changed": True,
                "msg": "Registry module with VCS would be created. Skipped creation due to check mode.",
            }
        
        # Build full options for create_with_vcs
        create_data = {
            "vcs_repo": params["vcs_repo"],
        }
        # Add optional fields if provided
        if params.get("name"):
            create_data["name"] = params["name"]
        if params.get("provider"):
            create_data["provider"] = params["provider"]
        if params.get("registry_name"):
            create_data["registry_name"] = params["registry_name"]
        if params.get("namespace"):
            create_data["namespace"] = params["namespace"]
        if params.get("no_code") is not None:
            create_data["no_code"] = params["no_code"]
        if params.get("test_config"):
            create_data["test_config"] = params["test_config"]
        
        created = create_registry_module_with_vcs(adapter, create_data)
        return {"changed": True, **created}
    
    elif operation == "create_version":
        if not params.get("version"):
            raise ValueError("'version' is required when operation is 'create_version'")
        if not params.get("name") or not params.get("provider"):
            raise ValueError("'name' and 'provider' are required when operation is 'create_version'")
        
        # Check if version already exists
        module_id = _build_module_id(params)
        existing_version = get_registry_module_version(adapter, module_id, params["version"])
        if existing_version is not None:
            result = {"changed": False, **existing_version}
            # If archive is provided but version exists, note that upload was skipped
            if params.get("archive"):
                result["msg"] = f"Version {params['version']} already exists. Archive upload skipped."
            return result
        
        if check_mode:
            return {
                "changed": True,
                "msg": f"Version {params['version']} would be created. Skipped creation due to check mode.",
                "version": params["version"],
            }
        
        version = create_registry_module_version(adapter, module_id, {
            "version": params["version"],
        })
        
        # Upload archive if provided
        if params.get("archive"):
            upload_url = version.get("links", {}).get("upload")
            if not upload_url:
                raise ValueError("Version created but no upload URL available")
            
            # Read archive file
            import os
            archive_path = params["archive"]
            if not os.path.exists(archive_path):
                raise ValueError(f"Archive file not found: {archive_path}")
            
            with open(archive_path, "rb") as f:
                archive_content = f.read()
            
            upload_registry_module_version(adapter, upload_url, archive_content)
            version["msg"] = f"Version {params['version']} created and archive uploaded successfully"
        
        return {"changed": True, **version}
    
    elif operation == "update":
        current = _fetch_registry_module(adapter, params)
        if current is None:
            raise ValueError(f"Registry module {params.get('name')}/{params.get('provider')} not found")
        
        if _has_drift(params, current):
            if check_mode:
                return {
                    "changed": True,
                    "msg": f"Registry module {current.get('id')} would be updated. Skipped update due to check mode.",
                }
            module_id = _build_module_id(params)
            updated = update_registry_module(adapter, module_id, {
                "no_code": params.get("no_code"),
            })
            return {"changed": True, **updated}
        
        return {"changed": False, **current}
    
    else:
        raise ValueError(f"Unknown operation: {operation}")


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the registry module, provider, or version based on delete_scope."""
    delete_scope = params.get("delete_scope", "module")
    module_id = _build_module_id(params)
    
    if delete_scope == "version":
        if not params.get("version"):
            raise ValueError("'version' is required when delete_scope is 'version'")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Version {params['version']} would be deleted. Skipped deletion due to check mode.",
            }
        delete_registry_module_version(adapter, module_id, params["version"])
        return {"changed": True, "msg": f"Version {params['version']} has been deleted successfully"}
    
    elif delete_scope == "provider":
        if not params.get("provider"):
            raise ValueError("'provider' is required when delete_scope is 'provider'")
        
        # Check if provider exists
        current = _fetch_registry_module(adapter, params)
        if current is None:
            return {"changed": False, "msg": "Registry module provider is already absent."}
        
        if check_mode:
            return {
                "changed": True,
                "msg": f"Provider {params['provider']} would be deleted. Skipped deletion due to check mode.",
            }
        delete_registry_module_provider(adapter, module_id)
        return {"changed": True, "msg": f"Provider {params['provider']} has been deleted successfully"}
    
    else:  # delete_scope == "module"
        if not params.get("name"):
            raise ValueError("'name' is required when delete_scope is 'module'")
        if check_mode:
            return {
                "changed": True,
                "msg": f"Module {params['name']} would be deleted. Skipped deletion due to check mode.",
            }
        delete_registry_module_by_name(adapter, module_id)
        return {"changed": True, "msg": f"Module {params['name']} has been deleted successfully"}


def main() -> None:
    module = AnsibleTerraformModule(
        argument_spec={
            "organization": {"type": "str", "required": True},
            "name": {"type": "str"},
            "provider": {"type": "str"},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
            "namespace": {"type": "str"},
            "no_code": {"type": "bool"},
            "vcs_repo": {
                "type": "dict",
                "options": {
                    "identifier": {"type": "str", "required": True},
                    "oauth_token_id": {"type": "str"},
                    "display_identifier": {"type": "str"},
                    "branch": {"type": "str"},
                    "tags": {"type": "bool"},
                    "organization_name": {"type": "str"},
                },
            },
            "test_config": {
                "type": "dict",
                "options": {
                    "tests_enabled": {"type": "bool"},
                },
            },
            "version": {"type": "str"},
            "archive": {"type": "path"},
            "operation": {
                "type": "str",
                "choices": ["create", "create_with_vcs", "create_version", "update", "delete"],
            },
            "delete_scope": {"type": "str", "choices": ["module", "provider", "version"]},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        supports_check_mode=True,
    )

    warnings: list = []
    result: Dict[str, Any] = {"changed": False, "warnings": warnings}
    action_result: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = deepcopy(module.params)
    params["check_mode"] = module.check_mode

    try:
        with module.client() as adapter:
            match params["state"]:
                case "present":
                    action_result = state_present(adapter, params, params["check_mode"])
                case "absent":
                    action_result = state_absent(adapter, params, params["check_mode"])

            if action_result:
                result.update(action_result)
            module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=to_text(e))


if __name__ == "__main__":
    main()

# Made with Bob
