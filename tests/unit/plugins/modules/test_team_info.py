# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the team_info module."""

from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
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
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "platform-team"
        assert result["visibility"] == "secret"
        assert result["user_count"] == 5
        assert result["sso_team_id"] == "sso-123"
        assert result["allow_member_token_management"] is True
        assert result["is_unified"] is False
        assert result["organization_access"]["manage_workspaces"] is True
        assert result["permissions"]["can_destroy"] is True

    def test_normalize_team_response_minimal_fields(self):
        """Test normalization with minimal fields."""
        team_data = {
            "id": "team-123",
            "name": "minimal-team",
        }

        result = normalize_team_response(team_data)

        assert result["id"] == "team-123"
        assert result["name"] == "minimal-team"
        assert result["visibility"] is None
        assert result["sso_team_id"] is None
        assert "organization_access" not in result
        assert "permissions" not in result


class TestTeamInfoNormalization:
    """Test team_info response normalization."""

    def test_normalize_multiple_team_objects(self):
        """Test normalization of multiple team objects."""
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
