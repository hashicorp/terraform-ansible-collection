# Copyright IBM Corp. 2025, 2026

# -*- coding: utf-8 -*-

from unittest.mock import patch

import pytest


class TestProjectInfoModule:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {"project_id": "prj-arg-spec"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id",
            side_effect=Exception("test"),
        ):
            with pytest.raises(AssertionError):
                main()

        mock_ansible_module.assert_called_once()
        call_args = mock_ansible_module.call_args[1]

        assert call_args["argument_spec"] == {
            "project_id": {"type": "str", "required": True},
        }
        assert call_args["supports_check_mode"] is True

    @pytest.mark.parametrize(
        "project_data",
        [
            {
                "id": "prj-123abc456def789",
                "name": "test-project",
                "description": "SDK-style basic project",
                "organization": "org-test123",
                "workspace_count": 0,
                "team_count": 0,
                "stack_count": 0,
                "status": 200,
            },
            {
                "id": "prj-complex123",
                "name": "complex-project",
                "description": "A complex project",
                "organization": "test-org",
                "created_at": "2025-01-01T00:00:00.000Z",
                "permissions": {
                    "can-read": True,
                    "can-update": True,
                    "can-destroy": False,
                },
                "workspace_count": 5,
                "team_count": 2,
                "stack_count": 1,
                "auto_destroy_activity_duration": None,
                "default_execution_mode": "remote",
                "setting_overwrites": {
                    "default_execution_mode": False,
                    "default_agent_pool": False,
                },
                "status": 200,
            },
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_retrieval_success(
        self,
        mock_get_project_by_id,
        mock_ansible_module,
        enhanced_dummy_module,
        project_data,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-123abc456def789"
        expected_project = dict(project_data)
        expected_project.pop("status", None)

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {
            "project_id": project_id,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }

        mock_ansible_module.return_value = mock_module
        mock_get_project_by_id.return_value = dict(project_data)

        with pytest.raises(SystemExit):
            main()

        mock_get_project_by_id.assert_called_once_with(mock_module.adapter, project_id)
        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["warnings"] == []
        assert mock_module.exit_args["project"] == expected_project
        assert "status" not in mock_module.exit_args["project"]
        assert mock_module.failed is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_project_not_found(self, mock_get_project_by_id, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-nonexistent"

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {"project_id": project_id}

        mock_ansible_module.return_value = mock_module
        mock_get_project_by_id.return_value = {}

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == f"Project '{project_id}' was not found."

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_flat_project_payload_supported(self, mock_get_project_by_id, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-flat"
        project_payload = {
            "id": project_id,
            "name": "flat-project",
            "description": "Flat payload from SDK formatter",
            "status": 200,
        }

        mock_module = enhanced_dummy_module
        mock_module.check_mode = True
        mock_module.params = {"project_id": project_id}

        mock_ansible_module.return_value = mock_module
        mock_get_project_by_id.return_value = dict(project_payload)

        with pytest.raises(SystemExit):
            main()

        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["project"]["id"] == project_id
        assert mock_module.exit_args["project"]["name"] == "flat-project"
        assert "status" not in mock_module.exit_args["project"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.project_info.get_project_by_id")
    def test_client_parameters_passed_correctly(
        self,
        mock_get_project_by_id,
        mock_ansible_module,
        enhanced_dummy_module,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.project_info import main

        project_id = "prj-params123"

        mock_module = enhanced_dummy_module
        mock_module.check_mode = True
        mock_module.params = {
            "project_id": project_id,
            "tfe_token": "test-token",
            "tfe_address": "app.terraform.io",
        }

        mock_ansible_module.return_value = mock_module
        mock_get_project_by_id.return_value = {
            "id": project_id,
            "name": "test",
            "organization": "org-test123",
        }

        with pytest.raises(SystemExit):
            main()
