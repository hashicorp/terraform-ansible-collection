# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/user_info.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.user_info import main


class TestUserInfo:
    """Test suite for user_info module operations."""

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data response."""
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

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_user")
    def test_get_user_by_id_success(self, mock_get_user, mock_module_class, sample_user_data):
        """Test retrieving user by ID successfully."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": "user-MA4GL63FmYRpSFxa",
            "current": False,
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_user
        mock_get_user.return_value = sample_user_data

        # Execute
        main()

        # Verify
        mock_get_user.assert_called_once_with(mock_adapter, "user-MA4GL63FmYRpSFxa")
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert call_args["user"] == sample_user_data

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_user")
    def test_get_user_by_id_not_found(self, mock_get_user, mock_module_class):
        """Test retrieving user by ID when user doesn't exist."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": "user-invalid-id",
            "current": False,
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_user to return None (not found)
        mock_get_user.return_value = None

        # Execute
        main()

        # Verify
        mock_get_user.assert_called_once_with(mock_adapter, "user-invalid-id")
        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "not found" in call_args["msg"].lower()
        assert "user-invalid-id" in call_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_current_user")
    def test_get_current_user_success(self, mock_get_current_user, mock_module_class, sample_user_data):
        """Test retrieving current authenticated user successfully."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": None,
            "current": True,
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_current_user
        mock_get_current_user.return_value = sample_user_data

        # Execute
        main()

        # Verify
        mock_get_current_user.assert_called_once_with(mock_adapter)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert call_args["user"] == sample_user_data

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_user")
    def test_check_mode_with_user_id(self, mock_get_user, mock_module_class, sample_user_data):
        """Test check mode with user ID."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": "user-MA4GL63FmYRpSFxa",
            "current": False,
        }
        mock_module.check_mode = True
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_user
        mock_get_user.return_value = sample_user_data

        # Execute
        main()

        # Verify - check mode should still retrieve the user
        mock_get_user.assert_called_once_with(mock_adapter, "user-MA4GL63FmYRpSFxa")
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert call_args["user"] == sample_user_data

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_current_user")
    def test_check_mode_with_current(self, mock_get_current_user, mock_module_class, sample_user_data):
        """Test check mode with current user."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": None,
            "current": True,
        }
        mock_module.check_mode = True
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_current_user
        mock_get_current_user.return_value = sample_user_data

        # Execute
        main()

        # Verify - check mode should still retrieve the current user
        mock_get_current_user.assert_called_once_with(mock_adapter)
        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["changed"] is False
        assert call_args["user"] == sample_user_data

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.user_info.get_user")
    def test_exception_handling(self, mock_get_user, mock_module_class):
        """Test exception handling."""
        # Setup mock module
        mock_module = Mock()
        mock_module.params = {
            "user_id": "user-MA4GL63FmYRpSFxa",
            "current": False,
        }
        mock_module.check_mode = False
        mock_module_class.return_value = mock_module

        # Setup mock adapter with context manager
        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context

        # Setup mock get_user to raise an exception
        mock_get_user.side_effect = Exception("API Error")

        # Execute
        main()

        # Verify
        mock_module.fail_json.assert_called_once()
        call_args = mock_module.fail_json.call_args[1]
        assert "API Error" in call_args["msg"]
