# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    create_project,
    delete_project,
    get_project_by_id,
    get_project_tag_bindings,
    list_projects,
    update_project,
    update_project_tag_bindings,
)


class TestGetProjectById:
    """Test cases for get_project_by_id function."""

    @pytest.mark.parametrize("status_code", [401, 403, 422, 500, 502])
    def test_get_project_by_id_raises_terraform_error_on_error_status(self, status_code):
        """Test get_project_by_id raises TerraformError for error status codes."""
        mock_tf_client = Mock()
        project_id = "prj-123abc456def789"

        response = {"status": status_code, "data": {}}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            get_project_by_id(mock_tf_client, project_id)

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            # Successful response with full data
            (
                {
                    "data": {
                        "id": "prj-123abc456def789",
                        "type": "projects",
                        "attributes": {
                            "name": "test-project",
                            "description": "A test project",
                            "created-at": "2025-01-01T00:00:00.000Z",
                        },
                    },
                    "status": 200,
                },
                {
                    "id": "prj-123abc456def789",
                    "type": "projects",
                    "attributes": {
                        "name": "test-project",
                        "description": "A test project",
                        "created-at": "2025-01-01T00:00:00.000Z",
                    },
                    "status": 200,
                },
            ),
            # Empty data section
            ({"data": {}, "status": 200}, {"status": 200}),
            # No data key
            ({"status": 200}, {"status": 200}),
            # Project not found
            ({"status": 404, "data": {}}, {}),
            # Project not found with no data key
            ({"status": 404}, {}),
        ],
    )
    def test_get_project_by_id_responses(self, response_data, expected_result):
        """Test get_project_by_id with various response formats."""
        mock_tf_client = Mock()
        project_id = "prj-123abc456def789"

        mock_tf_client.get.return_value = response_data
        result = get_project_by_id(mock_tf_client, project_id)
        assert result == expected_result

    @pytest.mark.parametrize(
        "project_id",
        [
            "prj-123abc456def789",
            "prj-sample1234567890",
            "prj-production-app123",
            "prj-dev-environment456",
        ],
    )
    def test_get_project_by_id_with_valid_ids(self, project_id):
        """Test get_project_by_id with realistic project IDs."""
        mock_tf_client = Mock()

        expected_response = {
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": {"name": "test-project"},
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_project_by_id(mock_tf_client, project_id)

        expected_result = {
            "id": project_id,
            "type": "projects",
            "attributes": {"name": "test-project"},
            "status": 200,
        }
        assert result == expected_result
        mock_tf_client.get.assert_called_with(f"/projects/{project_id}")

    def test_get_project_by_id_with_complex_data_structure(self):
        """Test get_project_by_id with complex nested data structure."""
        mock_tf_client = Mock()
        project_id = "prj-complex123"

        complex_response = {
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": {
                    "name": "complex-project",
                    "description": "A complex project with many attributes",
                    "created-at": "2025-01-01T00:00:00.000Z",
                    "permissions": {
                        "can-read": True,
                        "can-update": True,
                        "can-destroy": False,
                        "can-create-workspace": True,
                        "can-move-workspace": True,
                        "can-move-stack": False,
                        "can-deploy-no-code-modules": True,
                        "can-read-teams": True,
                        "can-manage-tags": True,
                        "can-manage-teams": False,
                        "can-manage-in-hcp": False,
                        "can-manage-ephemeral-workspace-for-projects": True,
                        "can-manage-varsets": True,
                    },
                    "workspace-count": 5,
                    "team-count": 2,
                    "stack-count": 1,
                    "auto-destroy-activity-duration": None,
                    "default-execution-mode": "remote",
                    "setting-overwrites": {
                        "default-execution-mode": False,
                        "default-agent-pool": False,
                    },
                },
                "relationships": {
                    "organization": {
                        "data": {"id": "test-org", "type": "organizations"},
                        "links": {"related": "/api/v2/organizations/test-org"},
                    },
                    "default-agent-pool": {"data": None},
                },
                "links": {"self": f"/api/v2/projects/{project_id}"},
            },
            "status": 200,
        }

        mock_tf_client.get.return_value = complex_response
        result = get_project_by_id(mock_tf_client, project_id)

        expected_result = complex_response["data"].copy()
        expected_result["status"] = 200

        assert result == expected_result
        mock_tf_client.get.assert_called_with(f"/projects/{project_id}")

    def test_get_project_by_id_404_returns_empty_dict(self):
        """Test get_project_by_id returns empty dict for 404 status."""
        mock_tf_client = Mock()
        project_id = "prj-nonexistent"

        response = {"status": 404, "data": {}}
        mock_tf_client.get.return_value = response

        result = get_project_by_id(mock_tf_client, project_id)
        assert result == {}
        mock_tf_client.get.assert_called_with(f"/projects/{project_id}")

    def test_get_project_by_id_404_with_error_message(self):
        """Test get_project_by_id handles 404 with error message gracefully."""
        mock_tf_client = Mock()
        project_id = "prj-nonexistent"

        response = {
            "status": 404,
            "data": {},
            "errors": [{"status": "404", "title": "Not Found", "detail": "Project not found"}],
        }
        mock_tf_client.get.return_value = response

        result = get_project_by_id(mock_tf_client, project_id)
        assert result == {}
        mock_tf_client.get.assert_called_with(f"/projects/{project_id}")

    def test_get_project_by_id_success_adds_status_field(self):
        """Test get_project_by_id adds status field to successful response."""
        mock_tf_client = Mock()
        project_id = "prj-123abc456def789"

        response = {
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": {"name": "test-project"},
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = response

        result = get_project_by_id(mock_tf_client, project_id)

        # Verify status field is added to the data
        assert "status" in result
        assert result["status"] == 200

    def test_get_project_by_id_handles_missing_data_key(self):
        """Test get_project_by_id handles response without data key."""
        mock_tf_client = Mock()
        project_id = "prj-123abc456def789"

        response = {"status": 200}
        mock_tf_client.get.return_value = response

        result = get_project_by_id(mock_tf_client, project_id)
        assert result == {"status": 200}

    def test_get_project_by_id_client_method_call(self):
        """Test get_project_by_id calls client.get with correct endpoint."""
        mock_tf_client = Mock()
        project_id = "prj-test123"

        response = {"data": {}, "status": 200}
        mock_tf_client.get.return_value = response

        get_project_by_id(mock_tf_client, project_id)

        # Verify the correct API endpoint is called
        mock_tf_client.get.assert_called_once_with(f"/projects/{project_id}")

    @pytest.mark.parametrize(
        "error_status,error_response",
        [
            (
                401,
                {
                    "status": 401,
                    "data": {},
                    "errors": [{"status": "401", "title": "Unauthorized", "detail": "Invalid credentials"}],
                },
            ),
            (
                403,
                {
                    "status": 403,
                    "data": {},
                    "errors": [{"status": "403", "title": "Forbidden", "detail": "Insufficient permissions"}],
                },
            ),
            (
                422,
                {
                    "status": 422,
                    "data": {},
                    "errors": [{"status": "422", "title": "Unprocessable Entity", "detail": "Invalid project ID format"}],
                },
            ),
            (
                500,
                {
                    "status": 500,
                    "data": {},
                    "errors": [{"status": "500", "title": "Internal Server Error", "detail": "Server error occurred"}],
                },
            ),
        ],
    )
    def test_get_project_by_id_error_handling(self, error_status, error_response):
        """Test get_project_by_id properly handles various error responses."""
        mock_tf_client = Mock()
        project_id = "prj-123abc456def789"

        mock_tf_client.get.return_value = error_response

        with pytest.raises(TerraformError) as exc_info:
            get_project_by_id(mock_tf_client, project_id)

        # Verify the TerraformError contains the response
        assert exc_info.value.args[0] == error_response

    def test_get_project_by_id_preserves_original_data_structure(self):
        """Test get_project_by_id preserves the original data structure from API response."""
        mock_tf_client = Mock()
        project_id = "prj-preserve123"

        original_data = {
            "id": project_id,
            "type": "projects",
            "attributes": {
                "name": "preserve-test",
                "nested": {"deep": {"value": "preserved"}},
                "list": [1, 2, 3],
                "boolean": True,
                "null_value": None,
            },
        }

        response = {"data": original_data, "status": 200}
        mock_tf_client.get.return_value = response

        result = get_project_by_id(mock_tf_client, project_id)

        # Verify all original data is preserved
        for key, value in original_data.items():
            assert result[key] == value

        # Verify status was added
        assert result["status"] == 200


class TestCreateProject:
    """Test cases for create_project function."""

    def test_create_project_success(self):
        """Test successful project creation."""
        mock_tf_client = Mock()
        organization = "test-org"
        project_data = {
            "data": {
                "type": "projects",
                "attributes": {"name": "new-project", "description": "A new test project"},
            }
        }

        response = {
            "status": 201,
            "data": {
                "id": "prj-new123",
                "type": "projects",
                "attributes": {"name": "new-project", "description": "A new test project"},
            },
        }
        mock_tf_client.post.return_value = response

        result = create_project(mock_tf_client, organization, project_data)

        assert result == response["data"]
        mock_tf_client.post.assert_called_once_with(f"/organizations/{organization}/projects", data=project_data)

    def test_create_project_raises_error_on_non_201_status(self):
        """Test create_project raises TerraformError for non-201 status."""
        mock_tf_client = Mock()
        organization = "test-org"
        project_data = {"data": {"type": "projects", "attributes": {"name": "new-project"}}}

        response = {"status": 422, "errors": [{"detail": "Validation error"}]}
        mock_tf_client.post.return_value = response

        with pytest.raises(TerraformError):
            create_project(mock_tf_client, organization, project_data)

    @pytest.mark.parametrize("error_status", [400, 401, 403, 404, 422, 500])
    def test_create_project_error_statuses(self, error_status):
        """Test create_project with various error status codes."""
        mock_tf_client = Mock()
        organization = "test-org"
        project_data = {"data": {}}

        response = {"status": error_status}
        mock_tf_client.post.return_value = response

        with pytest.raises(TerraformError):
            create_project(mock_tf_client, organization, project_data)

    def test_create_project_with_complete_data(self):
        """Test creating project with all attributes."""
        mock_tf_client = Mock()
        organization = "complete-org"
        project_data = {
            "data": {
                "type": "projects",
                "attributes": {
                    "name": "complete-project",
                    "description": "Complete project with all fields",
                    "auto-destroy-activity-duration": "14d",
                    "default-execution-mode": "remote",
                },
                "relationships": {
                    "tag-bindings": {
                        "data": [
                            {"key": "environment", "value": "production"},
                            {"key": "team", "value": "infra"},
                        ]
                    }
                },
            }
        }

        response = {
            "status": 201,
            "data": {
                "id": "prj-complete789",
                "type": "projects",
                "attributes": project_data["data"]["attributes"],
            },
        }
        mock_tf_client.post.return_value = response

        result = create_project(mock_tf_client, organization, project_data)

        assert result["id"] == "prj-complete789"
        assert result["attributes"]["name"] == "complete-project"


class TestUpdateProject:
    """Test cases for update_project function."""

    def test_update_project_success(self):
        """Test successful project update."""
        mock_tf_client = Mock()
        project_id = "prj-update123"
        update_data = {
            "data": {
                "type": "projects",
                "attributes": {"description": "Updated description"},
            }
        }

        response = {
            "status": 200,
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": {"name": "existing-project", "description": "Updated description"},
            },
        }
        mock_tf_client.patch.return_value = response

        result = update_project(mock_tf_client, project_id, update_data)

        assert result == response["data"]
        mock_tf_client.patch.assert_called_once_with(f"/projects/{project_id}", data=update_data)

    def test_update_project_raises_error_on_non_200_status(self):
        """Test update_project raises TerraformError for non-200 status."""
        mock_tf_client = Mock()
        project_id = "prj-fail123"
        update_data = {"data": {}}

        response = {"status": 404, "errors": [{"detail": "Project not found"}]}
        mock_tf_client.patch.return_value = response

        with pytest.raises(TerraformError):
            update_project(mock_tf_client, project_id, update_data)

    @pytest.mark.parametrize("error_status", [401, 403, 404, 422, 500])
    def test_update_project_error_statuses(self, error_status):
        """Test update_project with various error status codes."""
        mock_tf_client = Mock()
        project_id = "prj-error123"
        update_data = {"data": {}}

        response = {"status": error_status}
        mock_tf_client.patch.return_value = response

        with pytest.raises(TerraformError):
            update_project(mock_tf_client, project_id, update_data)

    def test_update_project_multiple_attributes(self):
        """Test updating multiple project attributes."""
        mock_tf_client = Mock()
        project_id = "prj-multi123"
        update_data = {
            "data": {
                "type": "projects",
                "attributes": {
                    "name": "renamed-project",
                    "description": "New description",
                    "auto-destroy-activity-duration": "30d",
                },
            }
        }

        response = {
            "status": 200,
            "data": {
                "id": project_id,
                "type": "projects",
                "attributes": update_data["data"]["attributes"],
            },
        }
        mock_tf_client.patch.return_value = response

        result = update_project(mock_tf_client, project_id, update_data)

        assert result["attributes"]["name"] == "renamed-project"
        assert result["attributes"]["description"] == "New description"
        assert result["attributes"]["auto-destroy-activity-duration"] == "30d"


class TestDeleteProject:
    """Test cases for delete_project function."""

    def test_delete_project_success(self):
        """Test successful project deletion."""
        mock_tf_client = Mock()
        project_id = "prj-delete123"

        response = {"status": 204, "data": None}
        mock_tf_client.delete.return_value = response

        result = delete_project(mock_tf_client, project_id)

        assert result is None
        mock_tf_client.delete.assert_called_once_with(f"/projects/{project_id}")

    def test_delete_project_raises_error_on_non_204_status(self):
        """Test delete_project raises TerraformError for non-204 status."""
        mock_tf_client = Mock()
        project_id = "prj-fail123"

        response = {"status": 404, "errors": [{"detail": "Project not found"}]}
        mock_tf_client.delete.return_value = response

        with pytest.raises(TerraformError):
            delete_project(mock_tf_client, project_id)

    @pytest.mark.parametrize("error_status", [401, 403, 404, 409, 422, 500])
    def test_delete_project_error_statuses(self, error_status):
        """Test delete_project with various error status codes."""
        mock_tf_client = Mock()
        project_id = "prj-error123"

        response = {"status": error_status}
        mock_tf_client.delete.return_value = response

        with pytest.raises(TerraformError):
            delete_project(mock_tf_client, project_id)

    def test_delete_project_with_error_details(self):
        """Test delete_project with detailed error response."""
        mock_tf_client = Mock()
        project_id = "prj-conflict123"

        response = {
            "status": 409,
            "errors": [{"status": "409", "title": "Conflict", "detail": "Project has active workspaces"}],
        }
        mock_tf_client.delete.return_value = response

        with pytest.raises(TerraformError):
            delete_project(mock_tf_client, project_id)

        mock_tf_client.delete.assert_called_once_with(f"/projects/{project_id}")


class TestGetProjectTagBindings:
    """Test cases for get_project_tag_bindings function."""

    def test_get_project_tag_bindings_success(self):
        """Test successful retrieval of tag bindings."""
        mock_tf_client = Mock()
        project_id = "prj-tags123"

        response = {
            "status": 200,
            "data": [
                {"id": "tb-1", "type": "tag-bindings", "attributes": {"key": "env", "value": "prod"}},
                {"id": "tb-2", "type": "tag-bindings", "attributes": {"key": "team", "value": "ops"}},
            ],
        }
        mock_tf_client.get.return_value = response

        result = get_project_tag_bindings(mock_tf_client, project_id)

        assert result == response["data"]
        assert len(result) == 2
        mock_tf_client.get.assert_called_once_with(f"/projects/{project_id}/tag-bindings")

    def test_get_project_tag_bindings_not_found(self):
        """Test get_project_tag_bindings returns empty dict for 404."""
        mock_tf_client = Mock()
        project_id = "prj-notfound123"

        response = {"status": 404}
        mock_tf_client.get.return_value = response

        result = get_project_tag_bindings(mock_tf_client, project_id)

        assert result == {}

    def test_get_project_tag_bindings_empty_list(self):
        """Test get_project_tag_bindings with empty tag list."""
        mock_tf_client = Mock()
        project_id = "prj-notags123"

        response = {"status": 200, "data": []}
        mock_tf_client.get.return_value = response

        result = get_project_tag_bindings(mock_tf_client, project_id)

        assert result == []

    @pytest.mark.parametrize("error_status", [401, 403, 422, 500])
    def test_get_project_tag_bindings_error_statuses(self, error_status):
        """Test get_project_tag_bindings with error status codes."""
        mock_tf_client = Mock()
        project_id = "prj-error123"

        response = {"status": error_status}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            get_project_tag_bindings(mock_tf_client, project_id)

    def test_get_project_tag_bindings_multiple_tags(self):
        """Test getting multiple tag bindings."""
        mock_tf_client = Mock()
        project_id = "prj-multitags123"

        response = {
            "status": 200,
            "data": [
                {"attributes": {"key": "environment", "value": "production"}},
                {"attributes": {"key": "team", "value": "infrastructure"}},
                {"attributes": {"key": "cost-center", "value": "engineering"}},
                {"attributes": {"key": "owner", "value": "devops"}},
            ],
        }
        mock_tf_client.get.return_value = response

        result = get_project_tag_bindings(mock_tf_client, project_id)

        assert len(result) == 4
        assert result[0]["attributes"]["key"] == "environment"


class TestUpdateProjectTagBindings:
    """Test cases for update_project_tag_bindings function."""

    def test_update_project_tag_bindings_success(self):
        """Test successful update of tag bindings."""
        mock_tf_client = Mock()
        project_id = "prj-updatetags123"
        tag_data = {
            "data": [
                {"type": "tag-bindings", "attributes": {"key": "env", "value": "staging"}},
            ]
        }

        response = {
            "status": 200,
            "data": [
                {"id": "tb-1", "type": "tag-bindings", "attributes": {"key": "env", "value": "staging"}},
            ],
        }
        mock_tf_client.patch.return_value = response

        result = update_project_tag_bindings(mock_tf_client, project_id, tag_data)

        assert result == response["data"]
        mock_tf_client.patch.assert_called_once_with(f"/projects/{project_id}/tag-bindings", data=tag_data)

    def test_update_project_tag_bindings_raises_error_on_non_200_status(self):
        """Test update_project_tag_bindings raises TerraformError for non-200 status."""
        mock_tf_client = Mock()
        project_id = "prj-fail123"
        tag_data = {"data": []}

        response = {"status": 422, "errors": [{"detail": "Invalid tag format"}]}
        mock_tf_client.patch.return_value = response

        with pytest.raises(TerraformError):
            update_project_tag_bindings(mock_tf_client, project_id, tag_data)

    @pytest.mark.parametrize("error_status", [401, 403, 404, 422, 500])
    def test_update_project_tag_bindings_error_statuses(self, error_status):
        """Test update_project_tag_bindings with various error status codes."""
        mock_tf_client = Mock()
        project_id = "prj-error123"
        tag_data = {"data": []}

        response = {"status": error_status}
        mock_tf_client.patch.return_value = response

        with pytest.raises(TerraformError):
            update_project_tag_bindings(mock_tf_client, project_id, tag_data)

    def test_update_project_tag_bindings_multiple_tags(self):
        """Test updating multiple tag bindings at once."""
        mock_tf_client = Mock()
        project_id = "prj-multitags123"
        tag_data = {
            "data": [
                {"attributes": {"key": "environment", "value": "production"}},
                {"attributes": {"key": "team", "value": "platform"}},
                {"attributes": {"key": "version", "value": "2.0"}},
            ]
        }

        response = {
            "status": 200,
            "data": tag_data["data"],
        }
        mock_tf_client.patch.return_value = response

        result = update_project_tag_bindings(mock_tf_client, project_id, tag_data)

        assert len(result) == 3
        assert result[1]["attributes"]["value"] == "platform"


class TestListProjects:
    """Test cases for list_projects function."""

    def test_list_projects_success(self):
        """Test successful listing of projects."""
        mock_tf_client = Mock()
        organization = "test-org"

        response = {
            "status": 200,
            "data": [
                {"id": "prj-1", "type": "projects", "attributes": {"name": "project-1"}},
                {"id": "prj-2", "type": "projects", "attributes": {"name": "project-2"}},
            ],
        }
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization)

        assert result == response["data"]
        assert len(result) == 2
        mock_tf_client.get.assert_called_once_with(f"/organizations/{organization}/projects", query_params=None)

    def test_list_projects_with_query_params(self):
        """Test listing projects with query parameters."""
        mock_tf_client = Mock()
        organization = "test-org"
        query_params = {"filter[name]": "test", "page[number]": "1", "page[size]": "20"}

        response = {
            "status": 200,
            "data": [{"id": "prj-filtered", "attributes": {"name": "test-project"}}],
        }
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization, query_params=query_params)

        assert result == response["data"]
        mock_tf_client.get.assert_called_once_with(f"/organizations/{organization}/projects", query_params=query_params)

    def test_list_projects_empty_list(self):
        """Test listing projects with empty result."""
        mock_tf_client = Mock()
        organization = "empty-org"

        response = {"status": 200, "data": []}
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization)

        assert result == []

    def test_list_projects_not_found(self):
        """Test list_projects returns empty dict for 404."""
        mock_tf_client = Mock()
        organization = "nonexistent-org"

        response = {"status": 404}
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization)

        assert result == {}

    @pytest.mark.parametrize("error_status", [401, 403, 422, 500])
    def test_list_projects_error_statuses(self, error_status):
        """Test list_projects with error status codes."""
        mock_tf_client = Mock()
        organization = "error-org"

        response = {"status": error_status}
        mock_tf_client.get.return_value = response

        with pytest.raises(TerraformError):
            list_projects(mock_tf_client, organization)

    def test_list_projects_with_pagination(self):
        """Test listing projects with pagination metadata."""
        mock_tf_client = Mock()
        organization = "paginated-org"
        query_params = {"page[number]": "1", "page[size]": "10"}

        response = {
            "status": 200,
            "data": [{"id": f"prj-{i}", "attributes": {"name": f"project-{i}"}} for i in range(10)],
            "meta": {"pagination": {"current-page": 1, "total-pages": 5, "total-count": 50}},
        }
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization, query_params=query_params)

        assert len(result) == 10

    def test_list_projects_large_result_set(self):
        """Test listing many projects."""
        mock_tf_client = Mock()
        organization = "large-org"

        response = {
            "status": 200,
            "data": [{"id": f"prj-{i}", "attributes": {"name": f"project-{i}"}} for i in range(100)],
        }
        mock_tf_client.get.return_value = response

        result = list_projects(mock_tf_client, organization)

        assert len(result) == 100
        assert result[0]["id"] == "prj-0"
        assert result[99]["id"] == "prj-99"
