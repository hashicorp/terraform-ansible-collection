try:
    import requests
    import re
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None
    re = None

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import (
    TerraformClient,
    ArchivistClient,
)


def create_config(client: TerraformClient, workspace_id: str, payload: dict):
    try:
        return client.post(f"/workspaces/{workspace_id}/configuration-versions", data=payload)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def archive_config(client: TerraformClient, config_version_id: str):
    try:
        return client.post(f"/configuration-versions/{config_version_id}/actions/archive")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def upload_config(client: ArchivistClient, upload_url: str, configuration_files_path: str):

    try:
        with open(configuration_files_path, "rb") as f:
            if re.match(r"^https?://", client.base_url) and "/object" in upload_url:
                return client.put(f"{upload_url}", f)
            return client.put(f"/object/{upload_url}", f)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


def get_config(client: TerraformClient, config_version_id: str):
    try:
        return client.get(f"/configuration-versions/{config_version_id}")
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
