# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the team_info module."""

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.team_info import (
    normalize_team_response,
)


class TestTeamInfoHelpers:
    """Test helper functions for team_info module."""

    def test_normalize_team_response_with_all_fields(self):
        """Test normalization of team response with all fields."""
        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "visibility": "secret",
            "sso_team_id": "sso-123",
            "allow_member_token_management": True,
            "user_count": 5,
            "is_unified": False,
            "organization_access": {
                "manage_workspaces": True,
                "read_workspaces": True,
            },
            "permissions": {
                "can_destroy": True,
                "can_update_membership": True,
            },
            "users": [
                {"id": "user-1", "username": "john"},
                {"id": "user-2", "username": "jane"},
            ],
            "organization_memberships": [
                {"id": "ou-1", "email": "john@example.com"},
            ],
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "platform-team"
        assert result["visibility"] == "secret"
        assert result["user_count"] == 5
        assert len(result["users"]) == 2
        assert len(result["organization_memberships"]) == 1

    def test_normalize_team_response_minimal_fields(self):
        """Test normalization with minimal fields."""
        team_data = {
            "id": "team-123",
            "name": "minimal-team",
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "minimal-team"
        assert "users" not in result
        assert "organization_memberships" not in result


class TestTeamInfoModuleIntegration:
    """Test team_info module integration tests."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_list_teams_response_format(self):
        """Test response format for listing teams."""
        teams_data = [
            {
                "id": "team-123",
                "name": "platform-team",
                "visibility": "secret",
                "user_count": 3,
            },
            {
                "id": "team-456",
                "name": "admin-team",
                "visibility": "organization",
                "user_count": 2,
            },
        ]

        results = [normalize_team_response(team) for team in teams_data]

        assert len(results) == 2
        assert results[0]["id"] == "team-123"
        assert results[1]["id"] == "team-456"
        assert results[0]["visibility"] == "secret"
        assert results[1]["visibility"] == "organization"

    def test_team_with_organization_access(self):
        """Test team response with organization access."""
        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "organization_access": {
                "manage_workspaces": True,
                "manage_projects": True,
                "read_workspaces": True,
            },
        }

        result = normalize_team_response(team_data)

        assert result["organization_access"]["manage_workspaces"] is True
        assert result["organization_access"]["manage_projects"] is True
        assert result["organization_access"]["read_workspaces"] is True

    def test_team_with_permissions(self):
        """Test team response with permissions."""
        team_data = {
            "id": "team-123",
            "name": "platform-team",
            "permissions": {
                "can_destroy": True,
                "can_update_membership": False,
            },
        }

        result = normalize_team_response(team_data)

        assert result["permissions"]["can_destroy"] is True
        assert result["permissions"]["can_update_membership"] is False
