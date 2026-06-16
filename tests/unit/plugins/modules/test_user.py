# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for user module_utils based on pytfe test patterns."""

import copy
from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.user import (
    get_current_user,
    get_user,
    update_current_user,
)


class TestUserModuleUtils:
    """Test suite for user module_utils operations."""

    @pytest.fixture
    def mock_adapter(self):
        """Mock TerraformClient adapter."""
        adapter = Mock()
        adapter.client = Mock()
        adapter.client.users = Mock()
        return adapter

    @pytest.fixture
    def sample_user_response(self):
        """Sample user response matching pytfe format."""
        return {
            "id": "user-MA4GL63FmYRpSFxa",
            "username": "admin",
            "email": "admin@example.com",
            "is_service_account": False,
            "auth_method": "hcp_sso",
            "avatar_url": "https://example.com/avatar.png",
            "v2_only": True,
            "permissions": {
                "can_create_organizations": False,
                "can_change_email": True,
                "can_change_username": True,
                "can_manage_user_tokens": False,
                "can_view_2fa_settings": False,
                "can_manage_hcp_account": False,
            },
        }

    def test_get_user_success(self, mock_adapter, sample_user_response):
        """Test reading a specific user by ID."""
        user_id = "user-MA4GL63FmYRpSFxa"

        # Mock the user object
        mock_user = Mock()
        mock_user.model_dump.return_value = sample_user_response
        mock_adapter.client.users.read.return_value = mock_user

        result = get_user(mock_adapter, user_id)

        mock_adapter.client.users.read.assert_called_once_with(user_id)
        assert result == sample_user_response
        assert result["id"] == user_id
        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["is_service_account"] is False
        assert result["auth_method"] == "hcp_sso"
        assert result["avatar_url"] == "https://example.com/avatar.png"
        assert result["v2_only"] is True
        assert result["permissions"]["can_create_organizations"] is False
        assert result["permissions"]["can_change_email"] is True
        assert result["permissions"]["can_change_username"] is True

    def test_get_user_invalid_id(self, mock_adapter):
        """Test reading a user with an invalid user ID."""
        with pytest.raises(ValueError, match="invalid user id"):
            get_user(mock_adapter, "")

    def test_get_user_not_found(self, mock_adapter):
        """Test reading a user that doesn't exist."""
        from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import NotFound

        user_id = "user-invalid-id"
        mock_adapter.client.users.read.side_effect = NotFound("User not found")

        result = get_user(mock_adapter, user_id)

        assert result is None
        mock_adapter.client.users.read.assert_called_once_with(user_id)

    def test_get_user_with_null_unconfirmed_email(self, mock_adapter, sample_user_response):
        """Test reading a user when unconfirmed_email is null."""
        modified_response = copy.deepcopy(sample_user_response)
        modified_response["unconfirmed_email"] = None

        mock_user = Mock()
        mock_user.model_dump.return_value = modified_response
        mock_adapter.client.users.read.return_value = mock_user

        result = get_user(mock_adapter, "user-MA4GL63FmYRpSFxa")

        assert result["unconfirmed_email"] is None

    def test_get_user_two_factor_parsing(self, mock_adapter, sample_user_response):
        """Test reading a user with two-factor data."""
        modified_response = copy.deepcopy(sample_user_response)
        modified_response["two_factor"] = {
            "enabled": True,
            "verified": False,
        }

        mock_user = Mock()
        mock_user.model_dump.return_value = modified_response
        mock_adapter.client.users.read.return_value = mock_user

        result = get_user(mock_adapter, "user-MA4GL63FmYRpSFxa")

        assert result["two_factor"] is not None
        assert result["two_factor"]["enabled"] is True
        assert result["two_factor"]["verified"] is False

    def test_get_user_nullable_bools(self, mock_adapter, sample_user_response):
        """Test reading a user when pointer-style boolean fields are null."""
        modified_response = copy.deepcopy(sample_user_response)
        modified_response["is_site_admin"] = None
        modified_response["is_admin"] = None
        modified_response["is_sso_login"] = None

        mock_user = Mock()
        mock_user.model_dump.return_value = modified_response
        mock_adapter.client.users.read.return_value = mock_user

        result = get_user(mock_adapter, "user-MA4GL63FmYRpSFxa")

        assert result["is_site_admin"] is None
        assert result["is_admin"] is None
        assert result["is_sso_login"] is None

    def test_get_current_user(self, mock_adapter, sample_user_response):
        """Test reading the currently authenticated user."""
        mock_user = Mock()
        mock_user.model_dump.return_value = sample_user_response
        mock_adapter.client.users.read_current.return_value = mock_user

        result = get_current_user(mock_adapter)

        mock_adapter.client.users.read_current.assert_called_once()
        assert result == sample_user_response
        assert result["id"] == "user-MA4GL63FmYRpSFxa"
        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"

    def test_update_current_user(self, mock_adapter, sample_user_response):
        """Test updating the currently authenticated user."""
        update_data = {
            "username": "new-admin",
            "email": "new-admin@example.com",
        }

        updated_response = copy.deepcopy(sample_user_response)
        updated_response["username"] = "new-admin"
        updated_response["email"] = "new-admin@example.com"

        mock_user = Mock()
        mock_user.model_dump.return_value = updated_response
        mock_adapter.client.users.update_current.return_value = mock_user

        result = update_current_user(mock_adapter, update_data)

        mock_adapter.client.users.update_current.assert_called_once()
        assert result["username"] == "new-admin"
        assert result["email"] == "new-admin@example.com"

    def test_get_current_user_exception(self, mock_adapter):
        """Test exception handling when getting current user fails."""
        from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError

        # Mock the API call to raise an exception
        mock_adapter.client.users.read_current.side_effect = Exception("API Error")

        # Verify that TerraformError is raised and contains the original error message
        with pytest.raises(TerraformError) as exc_info:
            get_current_user(mock_adapter)

        assert "API Error" in str(exc_info.value)
