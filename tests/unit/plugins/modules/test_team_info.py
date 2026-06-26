# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the team_info module."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.module_utils.team import (
    normalize_team_response,
)
from ansible_collections.hashicorp.terraform.plugins.modules.team_info import main


def _mock_module(params, check_mode=False):
    mock_module = Mock()
    mock_module.params = params
    mock_module.check_mode = check_mode

    mock_adapter = Mock()
    mock_context = Mock()
    mock_context.__enter__ = Mock(return_value=mock_adapter)
    mock_context.__exit__ = Mock(return_value=False)
    mock_module.client.return_value = mock_context
    return mock_module, mock_adapter


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


class TestTeamInfoModule:
    """Test team_info module execution paths."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.get_team")
    def test_get_team_by_id_success(self, mock_get_team, mock_module_class):
        mock_module, mock_adapter = _mock_module(
            {
                "team_id": "team-123",
                "organization": None,
                "name": None,
            }
        )
        mock_module_class.return_value = mock_module
        mock_get_team.return_value = {"id": "team-123", "name": "platform-team"}

        main()

        mock_get_team.assert_called_once_with(mock_adapter, "team-123")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["team"]["id"] == "team-123"
        assert "teams" not in result

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.get_team_by_name")
    def test_get_team_by_organization_and_name_success(self, mock_get_team_by_name, mock_module_class):
        mock_module, mock_adapter = _mock_module(
            {
                "team_id": None,
                "organization": "my-org",
                "name": "platform-team",
            }
        )
        mock_module_class.return_value = mock_module
        mock_get_team_by_name.return_value = {"id": "team-123", "name": "platform-team"}

        main()

        mock_get_team_by_name.assert_called_once_with(mock_adapter, "my-org", "platform-team")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["team"]["id"] == "team-123"
        assert result["teams"] == [result["team"]]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.list_teams")
    def test_list_teams_by_organization_success(self, mock_list_teams, mock_module_class):
        mock_module, mock_adapter = _mock_module(
            {
                "team_id": None,
                "organization": "my-org",
                "name": None,
            }
        )
        mock_module_class.return_value = mock_module
        mock_list_teams.return_value = [
            {"id": "team-123", "name": "platform-team"},
            {"id": "team-456", "name": "ops-team"},
        ]

        main()

        mock_list_teams.assert_called_once_with(mock_adapter, "my-org")
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert "team" not in result
        assert [team["id"] for team in result["teams"]] == ["team-123", "team-456"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.team_info.get_team_by_name")
    def test_get_team_by_organization_and_name_not_found(self, mock_get_team_by_name, mock_module_class):
        mock_module, mock_adapter = _mock_module(
            {
                "team_id": None,
                "organization": "my-org",
                "name": "missing-team",
            }
        )
        mock_module_class.return_value = mock_module
        mock_get_team_by_name.return_value = None

        main()

        mock_get_team_by_name.assert_called_once_with(mock_adapter, "my-org", "missing-team")
        mock_module.fail_json.assert_called_once()
        assert "missing-team" in mock_module.fail_json.call_args[1]["msg"]
