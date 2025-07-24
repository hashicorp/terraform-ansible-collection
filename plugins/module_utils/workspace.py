# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient


def get_workspace(client: TerraformClient, organization: str, workspace_name: str):
    try:
        return client.get(f"/organizations/{organization}/workspaces/{workspace_name}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
