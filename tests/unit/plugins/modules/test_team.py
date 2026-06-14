# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the team module."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.team import (
    extract_comparable_attributes,
    manage_membership,
    normalize_team_response,
    state_absent,
    state_create,
    state_update,
)


class TestTeamHelpers:
    """Test helper functions for team module."""

    def test_normalize_team_response(self):
        """Test normalization of team response data."""
        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
            "sso_team_id": "sso-123",
            "allow_member_token_management": True,
            "user_count": 5,
            "is_unified": False,
            "organization_access": {"manage_workspaces": True},
            "permissions": {"can_destroy": True},
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "platform-team"
        assert result["visibility"] == "secret"
        assert result["organization_access"] == {"manage_workspaces": True}

    def test_extract_comparable_attributes(self):
        """Test extraction of comparable attributes for idempotency checking."""
        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
            "sso_team_id": "sso-123",
            "allow_member_token_management": True,
            "organization_access": {"manage_workspaces": True},
        }

        result = extract_comparable_attributes(team_data)

        assert result["name"] == "platform-team"
        assert result["visibility"] == "secret"
        assert result["sso_team_id"] == "sso-123"
        assert result["allow_member_token_management"] is True
        assert "id" not in result


class TestTeamStateCreate:
    """Test team creation state function."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_create_team_success(self, mock_adapter):
        """Test successful team creation."""
        params = {
            "organization": "my-org",
            "name": "platform-team",
            "visibility": "secret",
            "allow_member_token_management": True,
        }

        mock_team_response = {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
            "allow_member_token_management": True,
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.create_team"
        ) as mock_create:
            mock_create.return_value = mock_team_response

            result = state_create(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert result["id"] == "team-123"
            assert "created successfully" in result["msg"]

    def test_create_team_missing_organization(self, mock_adapter):
        """Test team creation without organization."""
        params = {
            "name": "platform-team",
        }

        with pytest.raises(ValueError, match="organization is required"):
            state_create(mock_adapter, params, check_mode=False)

    def test_create_team_missing_name(self, mock_adapter):
        """Test team creation without name."""
        params = {
            "organization": "my-org",
        }

        with pytest.raises(ValueError, match="name is required"):
            state_create(mock_adapter, params, check_mode=False)

    def test_create_team_check_mode(self, mock_adapter):
        """Test team creation in check mode."""
        params = {
            "organization": "my-org",
            "name": "platform-team",
            "visibility": "organization",
        }

        result = state_create(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]
        assert result["name"] == "platform-team"


class TestTeamStateUpdate:
    """Test team update state function."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @pytest.fixture
    def current_team(self):
        return {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
            "sso_team_id": None,
            "allow_member_token_management": False,
        }

    def test_update_team_with_changes(self, mock_adapter, current_team):
        """Test successful team update with changes."""
        params = {
            "team_id": "team-123",
            "name": "platform-team-updated",
            "allow_member_token_management": True,
        }

        mock_updated_team = {
            "id": "team-123",
            "name": "platform-team-updated",
            "visibility": "secret",
            "allow_member_token_management": True,
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.update_team"
        ) as mock_update:
            mock_update.return_value = mock_updated_team

            result = state_update(mock_adapter, params, current_team, check_mode=False)

            assert result["changed"] is True
            assert result["name"] == "platform-team-updated"
            assert "updated successfully" in result["msg"]

    def test_update_team_no_changes(self, mock_adapter, current_team):
        """Test team update with no changes."""
        params = {
            "team_id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
        }

        result = state_update(mock_adapter, params, current_team, check_mode=False)

        assert result["changed"] is False
        assert "already has the desired state" in result["msg"]

    def test_update_team_not_found(self, mock_adapter):
        """Test updating non-existent team."""
        params = {
            "team_id": "team-999",
        }

        with pytest.raises(ValueError, match="was not found"):
            state_update(mock_adapter, params, None, check_mode=False)

    def test_update_team_check_mode(self, mock_adapter, current_team):
        """Test team update in check mode."""
        params = {
            "team_id": "team-123",
            "name": "platform-team-updated",
        }

        result = state_update(mock_adapter, params, current_team, check_mode=True)

        assert result["changed"] is True
        assert "would be updated" in result["msg"]


class TestTeamStateAbsent:
    """Test team deletion state function."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @pytest.fixture
    def current_team(self):
        return {
            "id": "team-123",
            "name": "platform-team",
        }

    def test_delete_team_success(self, mock_adapter, current_team):
        """Test successful team deletion."""
        params = {
            "team_id": "team-123",
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.delete_team"
        ) as mock_delete:
            result = state_absent(mock_adapter, params, current_team, check_mode=False)

            assert result["changed"] is True
            assert "deleted successfully" in result["msg"]
            mock_delete.assert_called_once_with(mock_adapter, "team-123")

    def test_delete_team_not_found(self, mock_adapter):
        """Test deleting non-existent team."""
        params = {
            "team_id": "team-999",
        }

        result = state_absent(mock_adapter, params, None, check_mode=False)

        assert result["changed"] is False
        assert "was not found" in result["msg"]

    def test_delete_team_check_mode(self, mock_adapter, current_team):
        """Test team deletion in check mode."""
        params = {
            "team_id": "team-123",
        }

        result = state_absent(mock_adapter, params, current_team, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]


class TestTeamMembership:
    """Test team membership management functions."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_add_users_to_team(self, mock_adapter):
        """Test adding users to team."""
        params = {
            "team_id": "team-123",
            "add_users": ["user1", "user2"],
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.add_users_to_team"
        ) as mock_add:
            result = manage_membership(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert "Added users" in result["msg"]
            mock_add.assert_called_once_with(
                mock_adapter, "team-123", ["user1", "user2"]
            )

    def test_remove_users_from_team(self, mock_adapter):
        """Test removing users from team."""
        params = {
            "team_id": "team-123",
            "remove_users": ["user1"],
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.remove_users_from_team"
        ) as mock_remove:
            result = manage_membership(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert "Removed users" in result["msg"]
            mock_remove.assert_called_once_with(mock_adapter, "team-123", ["user1"])

    def test_add_organization_memberships(self, mock_adapter):
        """Test adding organization memberships to team."""
        params = {
            "team_id": "team-123",
            "add_organization_memberships": ["ou-123", "ou-456"],
        }

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.team.add_organization_memberships_to_team"
        ) as mock_add:
            result = manage_membership(mock_adapter, params, check_mode=False)

            assert result["changed"] is True
            assert "Added organization memberships" in result["msg"]
            mock_add.assert_called_once()

    def test_no_membership_changes(self, mock_adapter):
        """Test when no membership changes requested."""
        params = {
            "team_id": "team-123",
        }

        result = manage_membership(mock_adapter, params, check_mode=False)

        assert result["changed"] is False

    def test_membership_check_mode(self, mock_adapter):
        """Test membership management in check mode."""
        params = {
            "team_id": "team-123",
            "add_users": ["user1"],
            "remove_organization_memberships": ["ou-123"],
        }

        result = manage_membership(mock_adapter, params, check_mode=True)

        assert result["changed"] is True
        assert "Would add users" in result["msg"]
        assert "Would remove organization memberships" in result["msg"]
        assert "check mode" in result["msg"]


class TestTeamInfoModule:
    """Test team_info module integration."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_get_specific_team(self, mock_adapter):
        """Test retrieving specific team."""
        from ansible_collections.hashicorp.terraform.plugins.modules.team_info import (
            normalize_team_response,
        )

        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "platform-team"

    def test_list_teams_response(self, mock_adapter):
        """Test list teams response normalization."""
        from ansible_collections.hashicorp.terraform.plugins.modules.team_info import (
            normalize_team_response,
        )

        teams = [
            {
                "id": "team-123",
                "name": "platform-team",
                "visibility": "secret",
            },
            {
                "id": "team-456",
                "name": "admin-team",
                "visibility": "organization",
            },
        ]

        result = [normalize_team_response(team) for team in teams]

        assert len(result) == 2
        assert result[0]["name"] == "platform-team"
        assert result[1]["name"] == "admin-team"
