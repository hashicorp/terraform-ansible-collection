# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the team module."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    get_team_by_name,
    list_teams,
    normalize_team_response,
)
from ansible_collections.hashicorp.terraform.plugins.modules.team import (
    extract_comparable_attributes,
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.team.create_team") as mock_create:
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.team.create_team") as mock_create:
            mock_create.side_effect = ValueError("'organization' is required")

            with pytest.raises(ValueError, match="'organization' is required"):
                state_create(mock_adapter, params, check_mode=False)

    def test_create_team_missing_name(self, mock_adapter):
        """Test team creation without name."""
        params = {
            "organization": "my-org",
        }

        with pytest.raises(Exception, match="validation error for TeamCreateOptions|Field required"):
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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.team.update_team") as mock_update:
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

    def test_update_team_name_too_long(self, mock_adapter, current_team):
        """Test updating team with name exceeding 90 characters."""
        params = {
            "team_id": "team-123",
            "name": "a" * 91,
        }

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.team.update_team") as mock_update:
            mock_update.side_effect = ValueError("String should have at most 90 characters")

            with pytest.raises(ValueError, match="at most 90 characters"):
                state_update(mock_adapter, params, current_team, check_mode=False)


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

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.team.delete_team") as mock_delete:
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


class TestGetTeamByName:
    """Test get_team_by_name utility function."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_get_team_by_name_found(self, mock_adapter):
        """Test that the first result is returned when the server-side filter matches."""
        mock_team = Mock()
        mock_team.model_dump.return_value = {"id": "team-123", "name": "platform-team"}
        mock_adapter.client.teams.list.return_value = iter([mock_team])

        result = get_team_by_name(mock_adapter, "my-org", "platform-team")

        assert result is not None
        assert result["id"] == "team-123"
        assert result["name"] == "platform-team"
        mock_adapter.client.teams.list.assert_called_once()

    def test_get_team_by_name_not_found(self, mock_adapter):
        """Test that None is returned when the server-side filter returns no results."""
        mock_adapter.client.teams.list.return_value = iter([])

        result = get_team_by_name(mock_adapter, "my-org", "platform-team")

        assert result is None

    def test_get_team_by_name_empty_org(self, mock_adapter):
        """Test that None is returned when the org has no teams."""
        mock_adapter.client.teams.list.return_value = iter([])

        result = get_team_by_name(mock_adapter, "my-org", "platform-team")

        assert result is None


class TestListTeams:
    """Test list_teams utility function."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_list_teams_returns_formatted_results(self, mock_adapter):
        mock_team = Mock()
        mock_team.model_dump.return_value = {"id": "team-123", "name": "platform-team"}
        mock_adapter.client.teams.list.return_value = iter([mock_team])

        result = list_teams(mock_adapter, "my-org")

        assert result == [{"id": "team-123", "name": "platform-team"}]
        mock_adapter.client.teams.list.assert_called_once_with("my-org", options=None)
