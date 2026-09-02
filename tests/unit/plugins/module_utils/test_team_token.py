# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/team_token.py (pytfe adapter)."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.team_token import (
    create_team_token,
    delete_team_token,
    delete_team_token_by_id,
    get_team_token,
    get_team_token_by_id,
)


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetTeamToken:
    def test_success(self):
        adapter = Mock()
        adapter.client.team_tokens.read.return_value = _make_model({"id": "at-abc123", "description": None})
        result = get_team_token(adapter, "team-xyz789")
        assert result == {"id": "at-abc123", "description": None}
        adapter.client.team_tokens.read.assert_called_once_with(team_id="team-xyz789")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.team_tokens.read.side_effect = NotFound("missing")
        assert get_team_token(adapter, "team-xyz789") is None

    def test_unexpected_exception_propagates(self):
        adapter = Mock()
        adapter.client.team_tokens.read.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            get_team_token(adapter, "team-xyz789")


class TestGetTeamTokenById:
    def test_success(self):
        adapter = Mock()
        adapter.client.team_tokens.read_by_id.return_value = _make_model({"id": "at-abc123", "description": "CI"})
        result = get_team_token_by_id(adapter, "at-abc123")
        assert result == {"id": "at-abc123", "description": "CI"}
        adapter.client.team_tokens.read_by_id.assert_called_once_with(token_id="at-abc123")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.team_tokens.read_by_id.side_effect = NotFound("missing")
        assert get_team_token_by_id(adapter, "at-missing") is None

    def test_unexpected_exception_propagates(self):
        adapter = Mock()
        adapter.client.team_tokens.read_by_id.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            get_team_token_by_id(adapter, "at-abc123")


class TestCreateTeamToken:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_create_no_description_no_expiry(self, mock_safe_call):
        """Without description or expired_at, calls create(team_id=...)."""
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "at-abc123", "token": "s3cr3t"})

        result = create_team_token(adapter, "team-xyz789", {})

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.create
        assert kwargs.get("team_id") == "team-xyz789"
        assert "error_context" in kwargs
        assert result == {"id": "at-abc123", "token": "s3cr3t"}

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.TeamTokenCreateOptions")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_named_create_with_description(self, mock_safe_call, mock_opts_cls):
        """With description, builds TeamTokenCreateOptions and calls create_with_options."""
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-desc123", "token": "s3cr3t", "description": "CI"})

        result = create_team_token(adapter, "team-xyz789", {"description": "CI"})

        mock_opts_cls.model_validate.assert_called_once_with({"description": "CI"})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.create_with_options
        assert kwargs.get("team_id") == "team-xyz789"
        assert kwargs.get("options") is opts
        assert "error_context" in kwargs
        assert result["id"] == "at-desc123"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.TeamTokenCreateOptions")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_create_with_expired_at_only_uses_create_with_options(self, mock_safe_call, mock_opts_cls):
        """expired_at without description calls create_with_options so the expiry is transmitted."""
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-exp123", "token": "s3cr3t"})

        create_team_token(adapter, "team-xyz789", {"expired_at": "2027-01-01T00:00:00Z"})

        mock_opts_cls.model_validate.assert_called_once_with({"expired_at": "2027-01-01T00:00:00Z"})
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.create_with_options

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.TeamTokenCreateOptions")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_create_with_description_and_expired_at(self, mock_safe_call, mock_opts_cls):
        """Both description and expired_at use create_with_options (named-token flow)."""
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "at-both123", "token": "s3cr3t"})

        create_team_token(adapter, "team-xyz789", {"description": "CI", "expired_at": "2027-01-01T00:00:00Z"})

        mock_opts_cls.model_validate.assert_called_once_with({"description": "CI", "expired_at": "2027-01-01T00:00:00Z"})
        args, _kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.create_with_options

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_empty_string_description_falls_through_to_create(self, mock_safe_call):
        """description="" is normalised to None, so the plain create() path is used.

        The module normalises falsy descriptions to None before calling the adapter,
        so the adapter should never receive description="".  When it does, it also
        normalises "" to None and calls create() without options.
        """
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "at-abc123", "token": "s3cr3t"})

        create_team_token(adapter, "team-xyz789", {"description": ""})

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.create
        assert kwargs.get("team_id") == "team-xyz789"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_create_unexpected_exception_propagates(self, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            create_team_token(Mock(), "team-xyz789", {})


class TestDeleteTeamToken:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_team_token(adapter, "team-xyz789")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.delete
        assert kwargs.get("team_id") == "team-xyz789"
        assert "error_context" in kwargs

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_delete_unexpected_exception_propagates(self, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            delete_team_token(Mock(), "team-xyz789")


class TestDeleteTeamTokenById:
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_delete_by_id_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_team_token_by_id(adapter, "at-abc123")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.team_tokens.delete_by_id
        assert kwargs.get("token_id") == "at-abc123"
        assert "error_context" in kwargs

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.team_token.safe_api_call")
    def test_delete_by_id_unexpected_exception_propagates(self, mock_safe_call):
        mock_safe_call.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            delete_team_token_by_id(Mock(), "at-abc123")
