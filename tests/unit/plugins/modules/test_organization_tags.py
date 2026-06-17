# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/organization_tags.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.organization_tags import (
    _add_tag_to_workspaces_by_name,
    _add_workspaces_to_tag_by_id,
    _resolve_tag,
    delete_organization_tags,
    get_organization_tag_by_name,
    list_organization_tags,
    main,
    state_absent,
    state_present,
)

MODULE = "ansible_collections.hashicorp.terraform.plugins.modules.organization_tags"


def _mock_list_response(items):
    """Return a mock transport response for a paginated list (single page)."""
    r = Mock()
    r.json.return_value = {"data": items}
    return r


class TestSdkHelpers:
    def test_list_success(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = _mock_list_response(
            [
                {"id": "tag-1", "attributes": {"name": "prod"}},
                {"id": "tag-2", "attributes": {"name": "dev"}},
            ]
        )
        result = list_organization_tags(adapter, "my-org")
        assert result == [{"id": "tag-1", "name": "prod"}, {"id": "tag-2", "name": "dev"}]
        adapter.client._transport.request.assert_called_with("GET", "/api/v2/organizations/my-org/tags", params={"page[number]": 1, "page[size]": 100})

    def test_list_not_found_returns_empty(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client._transport.request.side_effect = NotFound("none")
        assert list_organization_tags(adapter, "my-org") == []

    def test_get_by_name_match(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = _mock_list_response(
            [{"id": "tag-1", "attributes": {"name": "prod"}}, {"id": "tag-2", "attributes": {"name": "dev"}}]
        )
        assert get_organization_tag_by_name(adapter, "my-org", "dev") == {"id": "tag-2", "name": "dev"}

    def test_get_by_name_no_match(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = _mock_list_response([])
        assert get_organization_tag_by_name(adapter, "my-org", "ghost") is None

    def test_get_by_name_is_case_insensitive(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = _mock_list_response([{"id": "tag-1", "attributes": {"name": "prod"}}])
        # TFC stores lowercase; a mixed-case query should still resolve.
        assert get_organization_tag_by_name(adapter, "my-org", "PROD") == {"id": "tag-1", "name": "prod"}

    def test_delete(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = Mock()
        delete_organization_tags(adapter, "my-org", ["tag-1", "tag-2"])
        adapter.client._transport.request.assert_called_once_with(
            "DELETE",
            "/api/v2/organizations/my-org/tags",
            json_body={"data": [{"type": "tags", "id": "tag-1"}, {"type": "tags", "id": "tag-2"}]},
        )

    def test_delete_empty_is_noop(self):
        adapter = Mock()
        delete_organization_tags(adapter, "my-org", [])
        adapter.client._transport.request.assert_not_called()

    def test_add_workspaces_by_id(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = Mock()
        _add_workspaces_to_tag_by_id(adapter, "tag-1", ["ws-a", "ws-b"])
        adapter.client._transport.request.assert_called_once_with(
            "POST",
            "/api/v2/tags/tag-1/relationships/workspaces",
            json_body={"data": [{"type": "workspaces", "id": "ws-a"}, {"type": "workspaces", "id": "ws-b"}]},
        )

    def test_add_workspaces_by_id_empty_is_noop(self):
        adapter = Mock()
        _add_workspaces_to_tag_by_id(adapter, "tag-1", [])
        adapter.client._transport.request.assert_not_called()

    def test_add_tag_by_name_calls_workspace_endpoint_per_workspace(self):
        adapter = Mock()
        adapter.client._transport.request.return_value = Mock()
        _add_tag_to_workspaces_by_name(adapter, "prod", ["ws-a", "ws-b"])
        calls = adapter.client._transport.request.call_args_list
        assert len(calls) == 2
        assert calls[0].args == ("POST", "/api/v2/workspaces/ws-a/relationships/tags")
        assert calls[0].kwargs["json_body"] == {"data": [{"type": "tags", "attributes": {"name": "prod"}}]}
        assert calls[1].args == ("POST", "/api/v2/workspaces/ws-b/relationships/tags")

    def test_add_tag_by_name_empty_is_noop(self):
        adapter = Mock()
        _add_tag_to_workspaces_by_name(adapter, "prod", [])
        adapter.client._transport.request.assert_not_called()


class TestResolveTag:
    def test_by_id(self):
        adapter = Mock()
        with patch(f"{MODULE}.list_organization_tags", return_value=[{"id": "tag-1", "name": "a"}, {"id": "tag-2", "name": "b"}]):
            assert _resolve_tag(adapter, {"organization": "org", "tag_id": "tag-2"}) == {"id": "tag-2", "name": "b"}

    def test_by_id_missing(self):
        adapter = Mock()
        with patch(f"{MODULE}.list_organization_tags", return_value=[{"id": "tag-1", "name": "a"}]):
            assert _resolve_tag(adapter, {"organization": "org", "tag_id": "tag-x"}) is None

    def test_by_name(self):
        adapter = Mock()
        with patch(f"{MODULE}.get_organization_tag_by_name", return_value={"id": "tag-9", "name": "prod"}) as mock_get:
            assert _resolve_tag(adapter, {"organization": "org", "name": "prod"}) == {"id": "tag-9", "name": "prod"}
            mock_get.assert_called_once_with(adapter, "org", "prod")

    def test_no_identifier(self):
        adapter = Mock()
        assert _resolve_tag(adapter, {"organization": "org"}) is None


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_requires_workspace_ids(self, adapter):
        params = {"organization": "org", "name": "prod", "workspace_ids": None}
        with pytest.raises(ValueError, match="workspace_ids"):
            state_present(adapter, params, check_mode=False)

    def test_associate_by_name_resolves_id(self, adapter):
        params = {"organization": "org", "name": "prod", "tag_id": None, "workspace_ids": ["ws-b", "ws-a"]}
        with patch(f"{MODULE}._resolve_tag", return_value={"id": "tag-9", "name": "prod"}), patch(f"{MODULE}._add_workspaces_to_tag_by_id") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_called_once_with(adapter, "tag-9", ["ws-a", "ws-b"])
        assert result["changed"] is True
        assert result["workspace_ids"] == ["ws-a", "ws-b"]
        assert result["id"] == "tag-9"
        assert result["name"] == "prod"

    def test_associate_by_tag_id_when_tag_not_listed(self, adapter):
        params = {"organization": "org", "name": None, "tag_id": "tag-5", "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}._resolve_tag", return_value=None), patch(f"{MODULE}._add_workspaces_to_tag_by_id") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_called_once_with(adapter, "tag-5", ["ws-a"])
        assert result["id"] == "tag-5"

    def test_associate_by_name_tag_not_found_uses_workspace_api(self, adapter):
        params = {"organization": "org", "name": "new-tag", "tag_id": None, "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}._resolve_tag", return_value=None), patch(f"{MODULE}._add_tag_to_workspaces_by_name") as mock_add:
            result = state_present(adapter, params, check_mode=False)

        mock_add.assert_called_once_with(adapter, "new-tag", ["ws-a"])
        assert result["name"] == "new-tag"
        assert result["workspace_ids"] == ["ws-a"]

    def test_missing_identifier_raises(self, adapter):
        params = {"organization": "org", "name": None, "tag_id": None, "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}._resolve_tag", return_value=None):
            with pytest.raises(ValueError, match="name.*tag_id|tag_id"):
                state_present(adapter, params, check_mode=False)

    def test_check_mode_does_not_mutate(self, adapter):
        params = {"organization": "org", "name": "prod", "tag_id": None, "workspace_ids": ["ws-a"]}
        with patch(f"{MODULE}._resolve_tag", return_value={"id": "tag-9", "name": "prod"}), patch(f"{MODULE}._add_workspaces_to_tag_by_id") as mock_add:
            result = state_present(adapter, params, check_mode=True)

        mock_add.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_by_name(self, adapter):
        params = {"organization": "org", "name": "prod", "tag_id": None, "ids": None}
        with patch(f"{MODULE}._resolve_tag", return_value={"id": "tag-9", "name": "prod"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_called_once_with(adapter, "org", ["tag-9"])
        assert result["changed"] is True
        assert result["ids"] == ["tag-9"]

    def test_delete_by_ids_filters_to_existing(self, adapter):
        params = {"organization": "org", "name": None, "tag_id": None, "ids": ["tag-1", "tag-x"]}
        with patch(f"{MODULE}.list_organization_tags", return_value=[{"id": "tag-1"}, {"id": "tag-2"}]), patch(
            f"{MODULE}.delete_organization_tags"
        ) as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_called_once_with(adapter, "org", ["tag-1"])
        assert result["ids"] == ["tag-1"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"organization": "org", "name": "ghost", "tag_id": None, "ids": None}
        with patch(f"{MODULE}._resolve_tag", return_value=None), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=False)

        mock_del.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"organization": "org", "name": "prod", "tag_id": None, "ids": None}
        with patch(f"{MODULE}._resolve_tag", return_value={"id": "tag-9"}), patch(f"{MODULE}.delete_organization_tags") as mock_del:
            result = state_absent(adapter, params, check_mode=True)

        mock_del.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "state": "present", "name": "prod", "workspace_ids": ["ws-a"]}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True}):
            with pytest.raises(SystemExit):
                main()

        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]
        assert call_args["argument_spec"]["organization"] == {"type": "str", "required": True}
        assert call_args["argument_spec"]["state"]["choices"] == ["present", "absent"]
        assert call_args["mutually_exclusive"] == [("name", "tag_id", "ids")]
        assert call_args["supports_check_mode"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "state": "present", "name": "prod", "workspace_ids": ["ws-a"]}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", return_value={"changed": True, "workspace_ids": ["ws-a"]}) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "state": "absent", "ids": ["tag-1"]}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_absent", return_value={"changed": True, "ids": ["tag-1"]}) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE}.AnsibleTerraformModule")
    def test_failure_calls_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"organization": "org", "state": "present", "name": "prod", "workspace_ids": None}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE}.state_present", side_effect=ValueError("boom")):
            with pytest.raises(AssertionError, match="boom"):
                main()

        assert mock_module.failed is True
