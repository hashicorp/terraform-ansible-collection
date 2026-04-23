# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/organizations.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.organizations import (
    create_organization,
    delete_organization,
    get_organization,
    get_organization_capacity,
    get_organization_entitlements,
    list_organizations,
    update_organization,
)


def _make_model(payload):
    """Return a Mock that behaves like a pydantic model with model_dump()."""
    model = Mock()
    model.model_dump.return_value = payload
    return model


class TestGetOrganization:
    def test_success(self):
        adapter = Mock()
        adapter.client.organizations.read.return_value = _make_model({"id": "demo-org", "name": "demo-org"})

        result = get_organization(adapter, "demo-org")

        assert result == {"id": "demo-org", "name": "demo-org"}
        adapter.client.organizations.read.assert_called_once_with("demo-org")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.organizations.read.side_effect = NotFound("missing")

        assert get_organization(adapter, "ghost-org") is None


class TestListOrganizations:
    def test_success(self):
        adapter = Mock()
        adapter.client.organizations.list.return_value = iter(
            [
                _make_model({"id": "a", "name": "a"}),
                _make_model({"id": "b", "name": "b"}),
            ]
        )

        result = list_organizations(adapter)

        assert result == [{"id": "a", "name": "a"}, {"id": "b", "name": "b"}]

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.organizations.list.side_effect = NotFound("none")

        assert list_organizations(adapter) == []


class TestCreateOrganization:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.organizations.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.organizations.OrganizationCreateOptions")
    def test_create_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "new-org", "name": "new-org"})

        data = {"name": "new-org", "email": "ops@example.com"}
        result = create_organization(adapter, data)

        mock_options_cls.model_validate.assert_called_once_with(data)
        mock_safe_call.assert_called_once()
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.organizations.create
        assert args[1] is options
        assert "error_context" in kwargs
        assert result == {"id": "new-org", "name": "new-org"}


class TestUpdateOrganization:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.organizations.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.organizations.OrganizationUpdateOptions")
    def test_update_uses_sdk_options(self, mock_options_cls, mock_safe_call):
        adapter = Mock()
        options = Mock()
        mock_options_cls.model_validate.return_value = options
        mock_safe_call.return_value = _make_model({"id": "demo", "email": "new@example.com"})

        result = update_organization(adapter, "demo", {"email": "new@example.com"})

        mock_options_cls.model_validate.assert_called_once_with({"email": "new@example.com"})
        args, _ = mock_safe_call.call_args
        assert args[0] is adapter.client.organizations.update
        assert args[1] == "demo"
        assert args[2] is options
        assert result == {"id": "demo", "email": "new@example.com"}


class TestDeleteOrganization:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.organizations.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_organization(adapter, "demo")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.organizations.delete
        assert args[1] == "demo"
        assert "error_context" in kwargs


class TestReadExtras:
    def test_capacity_success(self):
        adapter = Mock()
        adapter.client.organizations.read_capacity.return_value = _make_model({"organization": "demo", "pending": 1, "running": 2})

        result = get_organization_capacity(adapter, "demo")

        assert result == {"organization": "demo", "pending": 1, "running": 2}

    def test_capacity_not_found(self):
        adapter = Mock()
        adapter.client.organizations.read_capacity.side_effect = NotFound("x")
        assert get_organization_capacity(adapter, "demo") is None

    def test_entitlements_success(self):
        adapter = Mock()
        adapter.client.organizations.read_entitlements.return_value = _make_model({"id": "demo", "operations": True})

        result = get_organization_entitlements(adapter, "demo")

        assert result == {"id": "demo", "operations": True}

    def test_entitlements_not_found(self):
        adapter = Mock()
        adapter.client.organizations.read_entitlements.side_effect = NotFound("x")
        assert get_organization_entitlements(adapter, "demo") is None
