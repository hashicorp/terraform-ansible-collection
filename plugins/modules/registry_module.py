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
  - The C(present) state reconciles the resource declaratively - the action is inferred
    from the fields provided - O(version) publishes/ensures a module version, O(vcs_repo)
    creates a VCS-connected module, otherwise a no-VCS module is ensured and O(no_code)
    drift is reconciled.
  - The C(absent) state deletes the module, provider, or specific version based on O(delete_scope).
    C(provider) and C(name) are required for all delete scopes.
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
      - Required to manage a module, publish a version, or delete (except for VCS creates that derive it).
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
      - The version string of a module version to manage.
      - When set with O(state=present), the module ensures that version exists (publishing it if missing).
      - When set with O(state=absent) and O(delete_scope=version), that version is deleted.
      - Must follow semantic versioning (e.g., C(1.0.0)).
      - Mutually exclusive with O(vcs_repo).
    type: str
  archive:
    description:
      - Path to a tar.gz archive file to upload when publishing a new version.
      - Only used with O(state=present) when O(version) is provided and the version does not yet exist.
      - The archive should contain the Terraform module files.
    type: path
  delete_scope:
    description:
      - Scope of deletion when O(state=absent).
      - Required when O(state=absent).
      - C(module) deletes the entire module (all providers and versions).
      - C(provider) deletes a specific provider and all its versions.
      - C(version) deletes a specific version (requires O(version)).
    type: str
    choices: ["module", "provider", "version"]
  state:
    description:
      - Desired state of the registry module.
      - C(present) reconciles the resource - the action is inferred from the fields
        provided - O(version) manages a module version, O(vcs_repo) manages a
        VCS-connected module, otherwise a no-VCS module is ensured and O(no_code)
        drift is reconciled.
      - C(absent) deletes the module, provider, or version selected by O(delete_scope).
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
    state: present
  register: module

- name: Create a registry module with VCS connection
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    namespace: "my-org"
    vcs_repo:
      identifier: "my-org/terraform-aws-vpc"
      oauth_token_id: "ot-abc123"
      display_identifier: "my-org/terraform-aws-vpc"
    state: present
  register: module_vcs

- name: Publish a new version for a registry module
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.0"
    state: present
  register: version

- name: Publish a version and upload its archive
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.1"
    archive: "/path/to/module.tar.gz"
    state: present
  register: version_with_upload

- name: Update registry module properties
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    no_code: true
    state: present

- name: Delete a specific version
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    version: "1.0.0"
    delete_scope: "version"
    state: absent

- name: Delete a specific provider
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
    provider: "aws"
    delete_scope: "provider"
    state: absent

- name: Delete entire module (all providers)
  hashicorp.terraform.registry_module:
    organization: "my-org"
    name: "vpc"
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
  returned: when a module is created or updated
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
  returned: when a module version is managed
  type: str
  sample: "1.0.0"
links:
  description: Links related to the resource (includes upload URL for versions).
  returned: when a module version is managed
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

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import AnsibleTerraformModule, TerraformClient
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
    """Reconcile the desired state of a registry module, version, or VCS module.

    The action is inferred from the provided fields:
      - ``version`` set   -> ensure that module version exists (optionally upload an archive).
      - ``vcs_repo`` set  -> ensure a VCS-connected module exists.
      - otherwise         -> ensure a no-VCS module exists and reconcile ``no_code`` drift.
    """
    if params.get("version"):
        return _ensure_version(adapter, params, check_mode)
    if params.get("vcs_repo"):
        return _ensure_vcs_module(adapter, params, check_mode)
    return _ensure_module(adapter, params, check_mode)


def _ensure_module(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool) -> Dict[str, Any]:
    """Ensure a no-VCS registry module exists; reconcile ``no_code`` drift."""
    if not params.get("name") or not params.get("provider"):
        raise ValueError("'name' and 'provider' are required to manage a registry module")

    current = _fetch_registry_module(adapter, params)
    if current is None:
        if check_mode:
            return {
                "changed": True,
                "msg": f"Registry module {params.get('name')} would be created. Skipped creation due to check mode.",
                "name": params.get("name"),
            }
        created = create_registry_module(
            adapter,
            params["organization"],
            {
                "name": params["name"],
                "provider": params["provider"],
                "registry_name": params.get("registry_name", "private"),
                "namespace": params.get("namespace"),
                "no_code": params.get("no_code"),
            },
        )
        return {"changed": True, **created}

    if _has_drift(params, current):
        if check_mode:
            return {
                "changed": True,
                "msg": f"Registry module {current.get('id')} would be updated. Skipped update due to check mode.",
            }
        module_id = _build_module_id(params)
        updated = update_registry_module(adapter, module_id, {"no_code": params.get("no_code")})
        return {"changed": True, **updated}

    return {"changed": False, **current}


def _ensure_vcs_module(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool) -> Dict[str, Any]:
    """Ensure a VCS-connected registry module exists."""
    vcs_repo = params.get("vcs_repo") or {}
    if not vcs_repo.get("identifier"):
        raise ValueError("'vcs_repo.identifier' is required to create a VCS-connected module")

    # Pre-check existence when name/provider are known (idempotency). When they are
    # omitted, TFE derives them from the repo and we cannot pre-check.
    if params.get("name") and params.get("provider"):
        current = _fetch_registry_module(adapter, params)
        if current is not None:
            return {"changed": False, **current}

    if check_mode:
        return {
            "changed": True,
            "msg": "VCS-connected registry module would be created. Skipped creation due to check mode.",
        }

    create_data: Dict[str, Any] = {"vcs_repo": params["vcs_repo"]}
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


def _ensure_version(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool) -> Dict[str, Any]:
    """Ensure a module version exists; optionally upload an archive."""
    if not params.get("name") or not params.get("provider"):
        raise ValueError("'name' and 'provider' are required to manage a module version")

    module_id = _build_module_id(params)
    existing_version = get_registry_module_version(adapter, module_id, params["version"])
    if existing_version is not None:
        result = {"changed": False, **existing_version}
        # Version already exists; an archive upload cannot be replayed idempotently.
        if params.get("archive"):
            result["msg"] = f"Version {params['version']} already exists. Archive upload skipped."
        return result

    if check_mode:
        return {
            "changed": True,
            "msg": f"Version {params['version']} would be created. Skipped creation due to check mode.",
            "version": params["version"],
        }

    version = create_registry_module_version(adapter, module_id, {"version": params["version"]})

    # Upload archive if provided
    if params.get("archive"):
        upload_url = version.get("links", {}).get("upload")
        if not upload_url:
            raise ValueError("Version created but no upload URL available")

        import os

        archive_path = params["archive"]
        if not os.path.exists(archive_path):
            raise ValueError(f"Archive file not found: {archive_path}")

        with open(archive_path, "rb") as f:
            archive_content = f.read()

        upload_registry_module_version(adapter, upload_url, archive_content)
        version["msg"] = f"Version {params['version']} created and archive uploaded successfully"

    return {"changed": True, **version}


def state_absent(adapter: TerraformClient, params: Dict[str, Any], check_mode: bool = False) -> Dict[str, Any]:
    """Delete the registry module, provider, or version based on delete_scope."""
    delete_scope = params.get("delete_scope")
    module_id = _build_module_id(params)

    if delete_scope == "version":
        if not params.get("version"):
            raise ValueError("'version' is required when delete_scope is 'version'")
        if not params.get("name") or not params.get("provider"):
            raise ValueError("'name' and 'provider' are required when delete_scope is 'version'")

        # Check if the version exists (idempotent absent)
        existing_version = get_registry_module_version(adapter, module_id, params["version"])
        if existing_version is None:
            return {"changed": False, "msg": "Registry module version is already absent."}

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

    elif delete_scope == "module":
        if not params.get("name") or not params.get("provider"):
            raise ValueError("'name' and 'provider' are required when delete_scope is 'module'")

        # Check if the module exists (idempotent absent)
        current = _fetch_registry_module(adapter, params)
        if current is None:
            return {"changed": False, "msg": "Registry module is already absent."}

        if check_mode:
            return {
                "changed": True,
                "msg": f"Module {params['name']} would be deleted. Skipped deletion due to check mode.",
            }
        delete_registry_module_by_name(adapter, module_id)
        return {"changed": True, "msg": f"Module {params['name']} has been deleted successfully"}

    else:
        raise ValueError(f"Invalid delete_scope: {delete_scope!r}. Must be one of: module, provider, version")


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
            "delete_scope": {"type": "str", "choices": ["module", "provider", "version"]},
            "state": {"type": "str", "default": "present", "choices": ["present", "absent"]},
        },
        required_if=[("state", "absent", ["delete_scope"])],
        mutually_exclusive=[("vcs_repo", "version")],
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
