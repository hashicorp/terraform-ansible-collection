# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/lookup/tf_org_tags.py."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tf_org_tags import LookupModule

LOOKUP = "ansible_collections.hashicorp.terraform.plugins.lookup.tf_org_tags"

_TAG_LIST = [
    {"id": "tag-1", "name": "env:prod", "instance_count": 3},
    {"id": "tag-2", "name": "env:dev", "instance_count": 1},
]


@pytest.fixture
def lookup_plugin():
    return LookupModule()


@pytest.fixture
def patched_client():
    with patch(f"{LOOKUP}.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


class TestTfOrgTagsLookup:

    @patch(f"{LOOKUP}.list_organization_tags", return_value=_TAG_LIST)
    def test_returns_all_tags(self, mock_list, patched_client, lookup_plugin):
        """run() returns a single-element list whose sole item is the tag list."""
        result = lookup_plugin.run([], None, organization="my-org", tfe_token="tok")
        assert result == [_TAG_LIST]
        mock_list.assert_called_once()
        call_org, call_query, call_filter = mock_list.call_args.args[1:]
        assert call_org == "my-org"
        assert call_query is None
        assert call_filter is None

    @patch(f"{LOOKUP}.list_organization_tags", return_value=[_TAG_LIST[0]])
    def test_query_forwarded_to_helper(self, mock_list, patched_client, lookup_plugin):
        """The query kwarg is passed through to list_organization_tags."""
        result = lookup_plugin.run([], None, organization="my-org", query="env:prod", tfe_token="tok")
        assert result == [[_TAG_LIST[0]]]
        call_org, call_query, call_filter = mock_list.call_args.args[1:]
        assert call_org == "my-org"
        assert call_query == "env:prod"
        assert call_filter is None

    @patch(f"{LOOKUP}.list_organization_tags", return_value=[_TAG_LIST[1]])
    def test_filter_exclude_taggable_id_forwarded(self, mock_list, patched_client, lookup_plugin):
        """filter_exclude_taggable_id kwarg is passed through to list_organization_tags."""
        result = lookup_plugin.run([], None, organization="my-org", filter_exclude_taggable_id="ws-abc", tfe_token="tok")
        assert result == [[_TAG_LIST[1]]]
        call_org, call_query, call_filter = mock_list.call_args.args[1:]
        assert call_org == "my-org"
        assert call_query is None
        assert call_filter == "ws-abc"

    @patch(f"{LOOKUP}.list_organization_tags", return_value=[_TAG_LIST[0]])
    def test_query_and_filter_combined(self, mock_list, patched_client, lookup_plugin):
        """Both query and filter_exclude_taggable_id can be supplied together."""
        lookup_plugin.run([], None, organization="my-org", query="env:prod", filter_exclude_taggable_id="ws-xyz", tfe_token="tok")
        call_query, call_filter = mock_list.call_args.args[2:4]
        assert call_query == "env:prod"
        assert call_filter == "ws-xyz"

    @patch(f"{LOOKUP}.list_organization_tags", return_value=[])
    def test_returns_empty_list_when_no_tags(self, mock_list, patched_client, lookup_plugin):
        """An organization with no tags returns an empty inner list, not an error."""
        result = lookup_plugin.run([], None, organization="empty-org", tfe_token="tok")
        assert result == [[]]

    def test_missing_organization_raises(self, patched_client, lookup_plugin):
        """Omitting 'organization' raises AnsibleError immediately."""
        with pytest.raises(AnsibleError, match="'organization' is required"):
            lookup_plugin.run([], None, tfe_token="tok")

    def test_empty_organization_raises(self, patched_client, lookup_plugin):
        """Passing an empty string for 'organization' raises AnsibleError."""
        with pytest.raises(AnsibleError, match="'organization' is required"):
            lookup_plugin.run([], None, organization="", tfe_token="tok")

    @patch(f"{LOOKUP}.list_organization_tags", side_effect=RuntimeError("api boom"))
    def test_api_error_wrapped_as_ansible_error(self, mock_list, patched_client, lookup_plugin):
        """Exceptions from list_organization_tags are wrapped in AnsibleError."""
        with pytest.raises(AnsibleError, match="tf_org_tags lookup failed.*api boom"):
            lookup_plugin.run([], None, organization="my-org", tfe_token="tok")

    @patch(f"{LOOKUP}.list_organization_tags", return_value=_TAG_LIST)
    def test_kwargs_forwarded_to_client(self, mock_list, patched_client, lookup_plugin):
        """All kwargs (including auth params) are forwarded to TerraformClient.from_mapping."""
        mock_class = patched_client[1]
        kwargs = {"organization": "my-org", "tfe_token": "tok-123", "tfe_address": "https://tfe.example.com"}
        lookup_plugin.run([], None, **kwargs)
        mock_class.from_mapping.assert_called_once_with(kwargs)
