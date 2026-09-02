# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Policy set version adapter for pytfe SDK integration.

Wraps ``client.policy_set_versions``. Like ``configuration_versions``, this is
a create-then-upload, immutable-once-uploaded resource (no update, no delete
endpoint at all - not even archive). Unlike ``configuration_versions.upload_tar_gzip``
(which expects an already-packed ``.tar.gz``), ``policy_set_versions.upload``
packs a raw local directory itself via ``pytfe.utils.pack_contents`` - callers
just point it at a directory of policy files.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response, safe_api_call


def create_policy_set_version(adapter: TerraformClient, policy_set_id: str) -> Dict[str, Any]:
    """Trigger a new policy set version. Takes no attributes."""
    response = safe_api_call(
        adapter.client.policy_set_versions.create,
        policy_set_id,
        error_context=f"Failed to create a policy set version for policy set {policy_set_id}",
    )
    return format_response(response)


def upload_policy_set_version(adapter: TerraformClient, policy_set_version_id: str, policy_files_path: str) -> None:
    """Pack and upload a local directory of policy files to a policy set version.

    Re-reads the raw (unformatted) version object first, since ``upload()``
    needs its ``links.upload`` URL, not just the ID.
    """
    raw_version = adapter.client.policy_set_versions.read(policy_set_version_id)
    safe_api_call(
        adapter.client.policy_set_versions.upload,
        raw_version,
        policy_files_path,
        error_context=f"Failed to upload policy files to policy set version {policy_set_version_id}",
    )


def get_policy_set_version(adapter: TerraformClient, policy_set_version_id: str) -> Optional[Dict[str, Any]]:
    """Read a single policy set version by its ID. Returns None if not found."""
    try:
        return format_response(adapter.client.policy_set_versions.read(policy_set_version_id))
    except NotFound:
        return None
