import requests

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient


def get_workspace(client: TerraformClient, organization: str, workspace_name: str):
    try:
        return client.get(f"/organizations/{organization}/workspaces/{workspace_name}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
