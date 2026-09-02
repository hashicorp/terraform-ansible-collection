# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from typing import Any, Dict, Optional

try:
    from pytfe.errors import NotFound
except ImportError:

    class NotFound(Exception):  # type: ignore[no-redef]
        pass


from ansible_collections.hashicorp.terraform.plugins.module_utils.client import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import format_response


def get_public_registry_module_latest(adapter: TerraformClient, namespace: str, name: str, provider: str) -> Optional[Dict[str, Any]]:
    """Read the latest published version of a public registry module.

    Returns None if the module is not found.
    """
    try:
        module = adapter.client.registry.latest_for_provider(namespace, name, provider)
        return format_response(module)
    except NotFound:
        return None


def get_public_registry_module(adapter: TerraformClient, namespace: str, name: str, provider: str, version: str) -> Optional[Dict[str, Any]]:
    """Read a specific version of a public registry module.

    Returns None if the module or version is not found.
    """
    try:
        module = adapter.client.registry.get_module(namespace, name, provider, version)
        return format_response(module)
    except NotFound:
        return None
