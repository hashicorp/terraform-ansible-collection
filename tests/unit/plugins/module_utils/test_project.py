# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.project import (
    get_project_by_id,
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
