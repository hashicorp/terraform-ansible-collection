# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest
from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tf_variable_set_vars import LookupModule

MOD = "ansible_collections.hashicorp.terraform.plugins.lookup.tf_variable_set_vars"


@pytest.fixture
def lookup_plugin():
    return LookupModule()


@pytest.fixture
def patched_client():
    with patch(f"{MOD}.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


class TestTfeVariableSetVarsLookup:

    @patch(f"{MOD}.list_variable_set_variables")
    def test_lookup_by_id_masks_sensitive(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = [
            {"id": "var-1", "key": "db_host", "value": "db.example.com", "sensitive": False, "category": "terraform", "hcl": False},
            {"id": "var-2", "key": "db_pass", "value": "super-secret", "sensitive": True, "category": "env", "hcl": False},
        ]
        result = lookup_plugin.run([], None, variable_set_id="varset-abc")
        assert result[0]["value"] == "db.example.com"
        assert result[1]["value"] == "<sensitive>"

    @patch(f"{MOD}.list_variable_set_variables")
    def test_lookup_by_id_reveals_with_flag(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = [
            {"id": "var-2", "key": "db_pass", "value": "super-secret", "sensitive": True, "category": "env", "hcl": False},
        ]
        result = lookup_plugin.run([], None, variable_set_id="varset-abc", display_sensitive=True)
        assert result[0]["value"] == "super-secret"

    @patch(f"{MOD}.get_variable_set_by_name")
    @patch(f"{MOD}.list_variable_set_variables")
    def test_lookup_by_name_and_org(self, mock_list, mock_by_name, patched_client, lookup_plugin):
        mock_by_name.return_value = {"id": "varset-xyz", "name": "platform"}
        mock_list.return_value = []
        result = lookup_plugin.run([], None, name="platform", organization="acme")
        assert result == []
        mock_by_name.assert_called_once()

    @patch(f"{MOD}.get_variable_set_by_name")
    def test_lookup_name_not_found(self, mock_by_name, patched_client, lookup_plugin):
        mock_by_name.return_value = None
        with pytest.raises(AnsibleError, match="not found"):
            lookup_plugin.run([], None, name="missing", organization="acme")

    def test_mutually_exclusive(self, patched_client, lookup_plugin):
        with pytest.raises(AnsibleError, match="mutually exclusive"):
            lookup_plugin.run([], None, variable_set_id="varset-a", name="x", organization="y")

    def test_missing_required(self, patched_client, lookup_plugin):
        with pytest.raises(AnsibleError, match="must be provided"):
            lookup_plugin.run([], None)

    @patch(f"{MOD}.list_variable_set_variables")
    def test_api_error_wrapped(self, mock_list, patched_client, lookup_plugin):
        mock_list.side_effect = RuntimeError("boom")
        with pytest.raises(AnsibleError, match="tf_variable_set_vars lookup failed"):
            lookup_plugin.run([], None, variable_set_id="varset-abc")
