# -*- coding: utf-8 -*-

from unittest.mock import Mock, patch
import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from tests.unit.constants import create_project_response


class TestProjectInfoModule:
    """Test cases for the project_info module."""

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        mock_module = Mock()
        mock_module.params = {}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient",
            side_effect=Exception("test"),
        ):
            main()

        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]

        expected_argument_spec = {
            "project_id": {"type": "str", "required": True},
        }

        assert call_args["argument_spec"] == expected_argument_spec
        assert call_args["supports_check_mode"] is True

    @pytest.mark.parametrize(
        "project_data,expected_result",
        [
            (
                {
                    **create_project_response(
                        project_id="prj-123abc456def789",
                        name="test-project"
                    )["data"],
                    "status": 200,
                },
                create_project_response(
                    project_id="prj-123abc456def789",
                    name="test-project"
                )["data"],
            ),
            (
                {
                    **create_project_response(
                        project_id="prj-complex123",
                        name="complex-project",
                        description="A complex project",
                        organization_id="test-org",
                        **{
                            "created-at": "2025-01-01T00:00:00.000Z",
                            "permissions": {
                                "can-read": True,
                                "can-update": True,
                                "can-destroy": False,
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
                    )["data"],
                    "status": 200,
                },
                create_project_response(
                    project_id="prj-complex123",
                    name="complex-project",
                    description="A complex project",
                    organization_id="test-org",
                    **{
                        "created-at": "2025-01-01T00:00:00.000Z",
                        "permissions": {
                            "can-read": True,
                            "can-update": True,
                            "can-destroy": False,
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
                )["data"],
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_retrieval_success(
        self,
        mock_get_project_by_id,
        mock_terraform_client,
        mock_ansible_module,
        project_data,
        expected_result,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123abc456def789"

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}

        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]

        # Validate flattened output
        for key, value in expected_result.items():
            assert call_args[key] == value

        assert call_args["changed"] is False
        assert call_args["warnings"] == []

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_not_found(
        self, mock_get_project_by_id, mock_terraform_client, mock_ansible_module
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-nonexistent"

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_project_by_id.return_value = {}

        main()

        mock_module.fail_json.assert_called_once_with(
            msg=f"Project '{project_id}' was not found."
        )

    @pytest.mark.parametrize(
        "exception,expected_message",
        [
            (TerraformError("API Error: Unauthorized"), "API Error: Unauthorized"),
            (Exception("Generic error"), "Generic error"),
            (ValueError("Invalid project ID format"), "Invalid project ID format"),
            (ConnectionError("Network connection failed"), "Network connection failed"),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    def test_exception_handling(
        self,
        mock_terraform_client,
        mock_ansible_module,
        exception,
        expected_message,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"project_id": "prj-123"}

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.side_effect = exception

        main()

        mock_module.fail_json.assert_called_once_with(msg=expected_message)

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_check_mode_behavior(
        self,
        mock_get_project_by_id,
        mock_terraform_client,
        mock_ansible_module,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123"

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {"project_id": project_id}

        mock_client = Mock()

        project_data = {
            **create_project_response(project_id=project_id, name="test")["data"],
            "status": 200,
        }

        expected_result = create_project_response(
            project_id=project_id, name="test"
        )["data"]

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_project_by_id.return_value = project_data

        main()

        mock_get_project_by_id.assert_called_once_with(mock_client, project_id)

        call_args = mock_module.exit_json.call_args[1]

        for key, value in expected_result.items():
            assert call_args[key] == value

        assert call_args["changed"] is False
        assert call_args["warnings"] == []

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_client_parameters_passed_correctly(
        self,
        mock_get_project_by_id,
        mock_terraform_client,
        mock_ansible_module,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-params123"

        mock_module = Mock()
        mock_module.check_mode = True
        mock_module.params = {
            "project_id": project_id,
            "tfe_token": "test-token",
            "tfe_address": "app.terraform.io",
        }

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_project_by_id.return_value = create_project_response(
            project_id=project_id, name="test"
        )["data"]

        main()

        mock_terraform_client.assert_called_once_with(
            tfe_token="test-token",
            tfe_address="app.terraform.io",
        )