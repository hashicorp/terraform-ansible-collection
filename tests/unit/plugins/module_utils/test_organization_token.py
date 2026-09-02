# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/organization_token.py."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.organization_token import (
    create_organization_token,
    delete_organization_token,
    delete_organization_token_with_type,
    get_organization_token,
    get_organization_token_with_type,
)

ADAPTER_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.organization_token"


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


# get_organization_token  (default read path)


class TestGetOrganizationToken:
    def test_success(self):
        adapter = Mock()
        adapter.client.organization_tokens.read.return_value = _make_model({"id": "at-abc123", "created_at": "2024-01-01T00:00:00+00:00"})
        result = get_organization_token(adapter, "my-org")
        assert result == {"id": "at-abc123", "created_at": "2024-01-01T00:00:00+00:00"}
        adapter.client.organization_tokens.read.assert_called_once_with("my-org")
        # Must NOT call read_with_options
        adapter.client.organization_tokens.read_with_options.assert_not_called()

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.organization_tokens.read.side_effect = NotFound("missing")
        assert get_organization_token(adapter, "my-org") is None

    def test_unexpected_exception_propagates(self):
        adapter = Mock()
        adapter.client.organization_tokens.read.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            get_organization_token(adapter, "my-org")


# get_organization_token_with_type  (audit-trails read path)


class TestGetOrganizationTokenWithType:
    def test_success_calls_read_with_options(self):
        adapter = Mock()
        adapter.client.organization_tokens.read_with_options.return_value = _make_model({"id": "at-audit123", "created_at": "2024-01-01T00:00:00+00:00"})
        result = get_organization_token_with_type(adapter, "my-org", "audit-trails")
        assert result == {"id": "at-audit123", "created_at": "2024-01-01T00:00:00+00:00"}
        # Must NOT call the default read()
        adapter.client.organization_tokens.read.assert_not_called()
        # Must call read_with_options with the correct options object
        adapter.client.organization_tokens.read_with_options.assert_called_once()
        call_args = adapter.client.organization_tokens.read_with_options.call_args
        assert call_args[0][0] == "my-org"
        options = call_args[0][1]
        assert options.token_type.value == "audit-trails"

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.organization_tokens.read_with_options.side_effect = NotFound("no audit token")
        assert get_organization_token_with_type(adapter, "my-org", "audit-trails") is None

    def test_unexpected_exception_propagates(self):
        adapter = Mock()
        adapter.client.organization_tokens.read_with_options.side_effect = RuntimeError("api down")
        with pytest.raises(RuntimeError, match="api down"):
            get_organization_token_with_type(adapter, "my-org", "audit-trails")


# create_organization_token


class TestCreateOrganizationToken:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.OrganizationTokenCreateOptions")
    def test_create_default_token(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-new123", "created_at": "2024-01-01T00:00:00+00:00", "token": "secret-value"})

        result = create_organization_token(adapter, "my-org", {})

        mock_opts_cls.model_validate.assert_called_once_with({})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.organization_tokens.create_with_options
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "at-new123", "created_at": "2024-01-01T00:00:00+00:00", "token": "secret-value"}

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.OrganizationTokenCreateOptions")
    def test_create_with_expiry(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-exp123", "created_at": "2024-01-01T00:00:00+00:00", "expired_at": "2027-01-01T00:00:00+00:00"})

        result = create_organization_token(adapter, "my-org", {"expired_at": "2027-01-01T00:00:00Z"})

        mock_opts_cls.model_validate.assert_called_once_with({"expired_at": "2027-01-01T00:00:00Z"})
        assert result["expired_at"] == "2027-01-01T00:00:00+00:00"

    def test_create_audit_trails_option_mapping(self):
        """Verify the real pytfe model accepts token_type='audit-trails' string and produces
        a valid OrganizationTokenCreateOptions with TokenType.AUDIT_TRAILS set.
        This test is NOT mocked so it exercises the real model_validate path."""
        from pytfe.models.organization_token import OrganizationTokenCreateOptions, TokenType

        opts = OrganizationTokenCreateOptions.model_validate({"token_type": "audit-trails"})
        assert opts.token_type == TokenType.AUDIT_TRAILS
        assert opts.token_type.value == "audit-trails"

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.OrganizationTokenCreateOptions")
    def test_create_propagates_error(self, _opts, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            create_organization_token(Mock(), "my-org", {})


# delete_organization_token  (default delete path)


class TestDeleteOrganizationToken:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_organization_token(adapter, "my-org")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.organization_tokens.delete
        assert args[1] == "my-org"
        assert "error_context" in kwargs
        # Must NOT call delete_with_options
        adapter.client.organization_tokens.delete_with_options.assert_not_called()

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    def test_delete_propagates_error(self, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("delete failed")
        with pytest.raises(RuntimeError, match="delete failed"):
            delete_organization_token(Mock(), "my-org")


# delete_organization_token_with_type  (audit-trails delete path)


class TestDeleteOrganizationTokenWithType:
    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.OrganizationTokenDeleteOptions")
    def test_delete_calls_delete_with_options(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts

        delete_organization_token_with_type(adapter, "my-org", "audit-trails")

        mock_opts_cls.model_validate.assert_called_once_with({"token_type": "audit-trails"})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.organization_tokens.delete_with_options
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        # Must NOT call the default delete()
        adapter.client.organization_tokens.delete.assert_not_called()

    def test_delete_audit_trails_option_mapping(self):
        """Verify the real pytfe model accepts token_type='audit-trails' and produces
        a valid OrganizationTokenDeleteOptions. Not mocked."""
        from pytfe.models.organization_token import OrganizationTokenDeleteOptions, TokenType

        opts = OrganizationTokenDeleteOptions.model_validate({"token_type": "audit-trails"})
        assert opts.token_type == TokenType.AUDIT_TRAILS

    @patch(f"{ADAPTER_PATH}.safe_api_call")
    @patch(f"{ADAPTER_PATH}.OrganizationTokenDeleteOptions")
    def test_delete_propagates_error(self, _opts, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("delete with options failed")
        with pytest.raises(RuntimeError, match="delete with options failed"):
            delete_organization_token_with_type(Mock(), "my-org", "audit-trails")
