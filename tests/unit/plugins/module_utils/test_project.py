# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for refactored project module_utils functions.
These tests mock the pytfe SDK calls instead of HTTP responses.
"""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    create_project,
    delete_project,
    get_project_by_id,
    get_project_by_name,
    get_project_tag_bindings,
    list_projects,
    update_project,
    update_project_tag_bindings,
)


class TestGetProjectById:
    """Test cases for get_project_by_id function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    def test_get_project_by_id_success(self, mock_format_response):
        """Test get_project_by_id returns formatted project data."""
        mock_adapter = Mock()
        mock_project = Mock()
        mock_format_response.return_value = {"id": "prj-123", "name": "test-project"}
        mock_adapter.client.projects.read.return_value = mock_project

        result = get_project_by_id(mock_adapter, "prj-123")

        assert result["id"] == "prj-123"
        assert result["name"] == "test-project"
        mock_adapter.client.projects.read.assert_called_once_with("prj-123")
        mock_format_response.assert_called_once_with(mock_project)

    def test_get_project_by_id_not_found(self):
        """Test get_project_by_id returns empty dict when project is not found."""
        mock_adapter = Mock()
        mock_adapter.client.projects.read.side_effect = NotFound("Project not found")

        result = get_project_by_id(mock_adapter, "prj-missing")

        assert result == {}
        mock_adapter.client.projects.read.assert_called_once_with("prj-missing")


class TestGetProjectByName:
    """Test cases for get_project_by_name function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.list_projects")
    def test_get_project_by_name_success(self, mock_list_projects, mock_format_response):
        """Test get_project_by_name returns formatted first matching project."""
        mock_adapter = Mock()
        mock_project = Mock()
        mock_list_projects.return_value = iter([mock_project])
        mock_format_response.return_value = {"id": "prj-123", "name": "demo-project"}

        result = get_project_by_name(mock_adapter, "demo-org", "demo-project")

        assert result == {"id": "prj-123", "name": "demo-project"}
        mock_list_projects.assert_called_once()
        mock_format_response.assert_called_once_with(mock_project)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.list_projects")
    def test_get_project_by_name_not_found(self, mock_list_projects):
        """Test get_project_by_name returns empty dict when no project matches."""
        mock_adapter = Mock()
        mock_list_projects.return_value = iter([])

        result = get_project_by_name(mock_adapter, "demo-org", "missing")

        assert result == {}


class TestCreateProject:
    """Test cases for create_project function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    def test_create_project_success(self, mock_format_response, mock_safe_api_call):
        """Test create_project with successful creation."""
        mock_adapter = Mock()
        mock_project = Mock()
        mock_safe_api_call.return_value = mock_project
        mock_format_response.return_value = {"id": "prj-new", "name": "new-project"}

        result = create_project(mock_adapter, "demo-org", {"name": "new-project"})

        assert result["id"] == "prj-new"
        assert result["name"] == "new-project"
        mock_safe_api_call.assert_called_once()
        mock_format_response.assert_called_once_with(mock_project)


class TestUpdateProject:
    """Test cases for update_project function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.safe_api_call")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    def test_update_project_success(self, mock_format_response, mock_safe_api_call):
        """Test update_project with successful update."""
        mock_adapter = Mock()
        mock_project = Mock()
        mock_safe_api_call.return_value = mock_project
        mock_format_response.return_value = {"id": "prj-123", "description": "Updated"}

        result = update_project(mock_adapter, "prj-123", {"name": "demo-project", "description": "Updated"})

        assert result["id"] == "prj-123"
        assert result["description"] == "Updated"
        mock_safe_api_call.assert_called_once()
        mock_format_response.assert_called_once_with(mock_project)


class TestDeleteProject:
    """Test cases for delete_project function with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.safe_api_call")
    def test_delete_project_success(self, mock_safe_api_call):
        """Test delete_project calls safe_api_call correctly."""
        mock_adapter = Mock()

        delete_project(mock_adapter, "prj-123")

        mock_safe_api_call.assert_called_once()


class TestTagBindings:
    """Test cases for project tag binding functions with pytfe SDK."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    def test_get_project_tag_bindings_list_response(self, mock_format_response):
        """Test get_project_tag_bindings formats list responses."""
        mock_adapter = Mock()
        tag_1 = Mock()
        tag_2 = Mock()
        mock_adapter.client.projects.list_tag_bindings.return_value = [tag_1, tag_2]
        mock_format_response.side_effect = [
            {"key": "env", "value": "dev"},
            {"key": "team", "value": "platform"},
        ]

        result = get_project_tag_bindings(mock_adapter, "prj-123")

        assert result == [
            {"key": "env", "value": "dev"},
            {"key": "team", "value": "platform"},
        ]
        mock_adapter.client.projects.list_tag_bindings.assert_called_once_with("prj-123")

    def test_get_project_tag_bindings_not_found(self):
        """Test get_project_tag_bindings returns empty dict on NotFound."""
        mock_adapter = Mock()
        mock_adapter.client.projects.list_tag_bindings.side_effect = NotFound("Project not found")

        result = get_project_tag_bindings(mock_adapter, "prj-missing")

        assert result == {}

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.project.format_response")
    def test_update_project_tag_bindings_success(self, mock_format_response):
        """Test update_project_tag_bindings formats returned tag bindings."""
        mock_adapter = Mock()
        tag_1 = Mock()
        tag_2 = Mock()
        mock_adapter.client.projects.add_tag_bindings.return_value = [tag_1, tag_2]
        mock_format_response.side_effect = [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "infra"},
        ]

        options = Mock()
        result = update_project_tag_bindings(mock_adapter, "prj-123", options)

        assert result == [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "infra"},
        ]
        mock_adapter.client.projects.add_tag_bindings.assert_called_once_with("prj-123", options)


class TestListProjects:
    """Test cases for list_projects function with pytfe SDK."""

    def test_list_projects_success(self):
        """Test list_projects returns SDK iterator response."""
        mock_adapter = Mock()
        project_1 = Mock(id="prj-1")
        project_2 = Mock(id="prj-2")
        mock_adapter.client.projects.list.return_value = iter([project_1, project_2])

        result = list_projects(mock_adapter, "demo-org")

        assert list(result) == [project_1, project_2]
        mock_adapter.client.projects.list.assert_called_once_with("demo-org", options=None)

    def test_list_projects_not_found(self):
        """Test list_projects returns empty dict when org has no projects."""
        mock_adapter = Mock()
        mock_adapter.client.projects.list.side_effect = NotFound("Organization not found")

        result = list_projects(mock_adapter, "missing-org")

        assert result == {}
