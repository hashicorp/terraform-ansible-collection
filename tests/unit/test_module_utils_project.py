import json
from unittest.mock import patch

import pytest

import importlib.util
import types
import os
import sys

# Load module under a synthetic top-level package to avoid Ansible's collection
# import hooks while preserving relative imports inside the plugins package.
REPO_ROOT = "/Users/kshitijapurushottamchoudhari/Projects/hahsicorp.terraform/hashicorp.terraform"

def _make_pkg(name, path):
    m = types.ModuleType(name)
    m.__path__ = [path]
    sys.modules[name] = m

# Create a fake package hierarchy 'fakepkg.hashicorp.terraform.plugins.module_utils'
_make_pkg("fakepkg", REPO_ROOT)
_make_pkg("fakepkg.hashicorp", os.path.join(REPO_ROOT))
_make_pkg("fakepkg.hashicorp.terraform", os.path.join(REPO_ROOT))
_make_pkg("fakepkg.hashicorp.terraform.plugins", os.path.join(REPO_ROOT, "plugins"))
_make_pkg("fakepkg.hashicorp.terraform.plugins.module_utils", os.path.join(REPO_ROOT, "plugins", "module_utils"))

# Load the project module file into the synthetic package namespace so relative
# imports like 'from .client import ...' resolve to the files under plugins/module_utils.
proj_path = os.path.join(REPO_ROOT, "plugins", "module_utils", "project.py")
spec = importlib.util.spec_from_file_location(
    "fakepkg.hashicorp.terraform.plugins.module_utils.project", proj_path
)
project_utils = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = project_utils
spec.loader.exec_module(project_utils)


class MockProjects:
    def __init__(self, create_ret=None, add_tags_ret=None):
        self._create_ret = create_ret
        self._add_tags_ret = add_tags_ret

    def create(self, organization, options, **kwargs):
        # Accept extra kwargs forwarded by safe_api_call (e.g., error_context)
        return self._create_ret

    def add_tag_bindings(self, project_id, options):
        return self._add_tags_ret

    def list_tag_bindings(self, project_id):
        return []

    def delete_tag_bindings(self, project_id):
        return None


class MockClient:
    def __init__(self, create_ret=None, add_tags_ret=None):
        self.address = "https://app.terraform.io"
        self.token = "token"
        self.client = type("C", (), {"projects": MockProjects(create_ret, add_tags_ret)})()

    def safe_api_call(self, func, *args, **kwargs):
        # simply call the underlying mock function
        return func(*args, **kwargs)


def test_get_project_full_not_found():
    client = MockClient()
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 404
        res = project_utils._get_project_full(client, "prj-no")
        assert res == {}


def test_create_project_calls_patch_and_get():
    # create returns an object/dict with id
    create_ret = {"id": "prj-1"}
    client = MockClient(create_ret=create_ret)
    with patch("requests.patch") as mock_patch, \
         patch("requests.get") as mock_get:

        mock_patch.return_value.status_code = 200
        mock_patch.return_value.json.return_value = {"data": {"id": "prj-1", "attributes": {"name": "proj"}}}

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": {"id": "prj-1", "attributes": {"name": "proj"}}}

        res = project_utils.create_project(
            client,
            organization="org",
            name="proj",
            description="d",
            execution_mode="remote",
        )

        # Ensure final data is returned and includes id
        assert isinstance(res, dict)
        assert "data" in res
        assert res["data"]["id"] == "prj-1"


def test_wrap_response_maps_fields():
    # Provide a dict that mimics pytfe output
    data = {
        "id": "prj-xyz",
        "name": "myproject",
        "default_execution_mode": "remote",
        "auto_destroy_activity_duration": "30d",
        "default_agent_pool_id": "ap-123",
        "setting_overwrites": {"auto_apply": True},
    }

    wrapped = project_utils._wrap_response(data)
    assert wrapped["id"] == "prj-xyz"
    assert wrapped["attributes"]["name"] == "myproject"
    assert wrapped["attributes"]["default-execution-mode"] == "remote"
    assert wrapped["attributes"]["auto-destroy-activity-duration"] == "30d"
    assert wrapped["relationships"]["default-agent-pool"]["data"]["id"] == "ap-123"
