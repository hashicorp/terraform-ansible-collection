# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/agent_token.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.modules.agent_token import (
    _fetch_agent_token,
    state_absent,
    state_present,
)

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.agent_token"


@pytest.fixture
def mock_adapter():
    return Mock()


class TestFetchAgentToken:
    @patch(f"{MOD_PATH}.get_agent_token")
    def test_by_id(self, mock_get, mock_adapter):
        mock_get.return_value = {"id": "at-1", "description": "ci-runner"}
        params = {"agent_token_id": "at-1"}

        result = _fetch_agent_token(mock_adapter, params)

        assert result == {"id": "at-1", "description": "ci-runner"}
        mock_get.assert_called_once_with(mock_adapter, "at-1")

    @patch(f"{MOD_PATH}.get_agent_token")
    def test_returns_none_when_no_id_given(self, mock_get, mock_adapter):
        params = {}

        result = _fetch_agent_token(mock_adapter, params)

        assert result is None
        mock_get.assert_not_called()


class TestStatePresent:
    @patch(f"{MOD_PATH}._fetch_agent_token")
    @patch(f"{MOD_PATH}.create_agent_token")
    def test_create_when_missing(self, mock_create, mock_fetch, mock_adapter):
        mock_fetch.return_value = None
        mock_create.return_value = {
            "id": "at-1",
            "description": "ci-runner",
            "token": "t.secret",
        }
        params = {"agent_pool_id": "apool-1", "description": "ci-runner"}

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "at-1"
        assert result["token"] == "t.secret"
        mock_create.assert_called_once_with(mock_adapter, "apool-1", {"description": "ci-runner"})

    @patch(f"{MOD_PATH}._fetch_agent_token")
    @patch(f"{MOD_PATH}.create_agent_token")
    def test_idempotent_when_token_exists(self, mock_create, mock_fetch, mock_adapter):
        existing = {"id": "at-1", "description": "ci-runner"}
        mock_fetch.return_value = existing
        params = {"agent_token_id": "at-1"}

        result = state_present(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "at-1"
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_agent_token")
    @patch(f"{MOD_PATH}.create_agent_token")
    def test_check_mode_skips_creation(self, mock_create, mock_fetch, mock_adapter):
        mock_fetch.return_value = None
        params = {"agent_pool_id": "apool-1", "description": "ci-runner"}

        result = state_present(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "check mode" in result["msg"]
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_agent_token")
    def test_missing_agent_pool_id_raises(self, mock_fetch, mock_adapter):
        mock_fetch.return_value = None
        params = {"description": "ci-runner"}

        with pytest.raises(ValueError, match="agent_pool_id"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}._fetch_agent_token")
    def test_missing_description_raises(self, mock_fetch, mock_adapter):
        mock_fetch.return_value = None
        params = {"agent_pool_id": "apool-1"}

        with pytest.raises(ValueError, match="description"):
            state_present(mock_adapter, params, check_mode=False)


class TestStateAbsent:
    @patch(f"{MOD_PATH}.get_agent_token")
    @patch(f"{MOD_PATH}.delete_agent_token")
    def test_delete_existing_token(self, mock_delete, mock_get, mock_adapter):
        mock_get.return_value = {"id": "at-1", "description": "ci-runner"}
        params = {"agent_token_id": "at-1"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete.assert_called_once_with(mock_adapter, "at-1")

    @patch(f"{MOD_PATH}.get_agent_token")
    @patch(f"{MOD_PATH}.delete_agent_token")
    def test_idempotent_when_already_absent(self, mock_delete, mock_get, mock_adapter):
        mock_get.return_value = None
        params = {"agent_token_id": "at-missing"}

        result = state_absent(mock_adapter, params, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}.get_agent_token")
    @patch(f"{MOD_PATH}.delete_agent_token")
    def test_check_mode_skips_deletion(self, mock_delete, mock_get, mock_adapter):
        mock_get.return_value = {"id": "at-1", "description": "ci-runner"}
        params = {"agent_token_id": "at-1"}

        result = state_absent(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "check mode" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}.get_agent_token")
    @patch(f"{MOD_PATH}.delete_agent_token")
    def test_delete_propagates_api_error(self, mock_delete, mock_get, mock_adapter):
        mock_get.return_value = {"id": "at-1", "description": "ci-runner"}
        mock_delete.side_effect = TerraformError("Failed to delete agent token at-1")
        params = {"agent_token_id": "at-1"}

        with pytest.raises(TerraformError, match="Failed to delete agent token"):
            state_absent(mock_adapter, params, check_mode=False)


class TestStatePresentApiError:
    @patch(f"{MOD_PATH}._fetch_agent_token")
    @patch(f"{MOD_PATH}.create_agent_token")
    def test_create_propagates_api_error(self, mock_create, mock_fetch, mock_adapter):
        mock_fetch.return_value = None
        mock_create.side_effect = TerraformError("Failed to create agent token in pool apool-1")
        params = {"agent_pool_id": "apool-1", "description": "ci-runner"}

        with pytest.raises(TerraformError, match="Failed to create agent token"):
            state_present(mock_adapter, params, check_mode=False)
