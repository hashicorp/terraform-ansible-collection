# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest


class TestWorkspaceInfoModule:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {"workspace_id": "ws-arg-spec", "workspace": None, "organization": None}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient",
            return_value=Mock(),
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id",
            side_effect=Exception("test"),
        ):
            with pytest.raises(AssertionError):
                main()

        call_args = mock_ansible_module.call_args[1]

        assert call_args["argument_spec"] == {
            "workspace_id": {"type": "str"},
            "workspace": {"type": "str"},
            "organization": {"type": "str"},
        }
        assert call_args["supports_check_mode"] is True
        assert call_args["mutually_exclusive"] == [
            ["workspace_id", "workspace"],
            ["workspace_id", "organization"],
        ]
        assert call_args["required_one_of"] == [["workspace_id", "workspace"]]
        assert call_args["required_together"] == [["workspace", "organization"]]

    @pytest.mark.parametrize(
        "workspace_data",
        [
            {
                "id": "ws-123abc456def789",
                "name": "test-workspace",
                "terraform_version": "1.10.5",
                "execution_mode": "remote",
                "auto_apply": False,
                "locked": False,
                "resource_count": 0,
                "organization": "test-org",
                "status": 200,
            },
            {
                "id": "ws-complex123",
                "name": "complex-workspace",
                "description": "Complex workspace",
                "terraform_version": "1.9.0",
                "execution_mode": "remote",
                "auto_apply": True,
                "allow_destroy_plan": True,
                "file_triggers_enabled": True,
                "queue_all_runs": False,
                "organization": "org-456",
                "tag_names": ["env:dev", "team:platform"],
                "status": 200,
            },
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_workspace_retrieval_by_id_success(
        self,
        mock_get_workspace_by_id,
        mock_terraform_client,
        mock_ansible_module,
        enhanced_dummy_module,
        workspace_data,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-123abc456def789"
        expected_workspace = dict(workspace_data)
        expected_workspace.pop("status", None)

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {
            "workspace_id": workspace_id,
            "workspace": None,
            "organization": None,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_workspace_by_id.return_value = dict(workspace_data)

        with pytest.raises(SystemExit):
            main()

        mock_terraform_client.assert_called_once_with(
            tfe_token="token",
            tfe_address="https://app.terraform.io",
        )
        mock_get_workspace_by_id.assert_called_once_with(adapter, workspace_id)
        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["warnings"] == []
        assert mock_module.exit_args["workspace"] == expected_workspace
        assert "status" not in mock_module.exit_args["workspace"]
        adapter.cleanup.assert_called_once_with()

    @pytest.mark.parametrize(
        "workspace_data",
        [
            {
                "id": "ws-123abc456def789",
                "name": "test-workspace",
                "organization": "test-org",
                "execution_mode": "remote",
                "status": 200,
            },
            {
                "id": "ws-minimal",
                "name": "minimal-workspace",
                "organization": "test-org",
                "status": 200,
            },
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_workspace_retrieval_by_name_success(
        self,
        mock_get_workspace,
        mock_terraform_client,
        mock_ansible_module,
        enhanced_dummy_module,
        workspace_data,
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        organization = "test-org"
        workspace_name = "test-workspace"
        expected_workspace = dict(workspace_data)
        expected_workspace.pop("status", None)

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {
            "workspace": workspace_name,
            "organization": organization,
            "workspace_id": None,
        }

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_workspace.return_value = dict(workspace_data)

        with pytest.raises(SystemExit):
            main()

        mock_get_workspace.assert_called_once_with(adapter, organization, workspace_name)
        assert mock_module.exit_args["workspace"] == expected_workspace
        assert mock_module.exit_args["changed"] is False
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_workspace_not_found_by_id(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-nonexistent"

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id, "workspace": None, "organization": None}

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_workspace_by_id.return_value = {}

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == f"Workspace '{workspace_id}' was not found."
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace")
    def test_workspace_not_found_by_name(self, mock_get_workspace, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        organization = "test-org"
        workspace_name = "nonexistent-workspace"

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {"workspace": workspace_name, "organization": organization, "workspace_id": None}

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_workspace.return_value = {}

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == f"The workspace {workspace_name} in {organization} organization was not found."
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.workspace_info.get_workspace_by_id")
    def test_check_mode_behavior(self, mock_get_workspace_by_id, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.workspace_info import main

        workspace_id = "ws-123abc456def789"
        workspace_data = {
            "id": workspace_id,
            "name": "test-workspace",
            "execution_mode": "remote",
            "status": 200,
        }

        mock_module = enhanced_dummy_module
        mock_module.check_mode = True
        mock_module.params = {"workspace_id": workspace_id, "workspace": None, "organization": None}

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_workspace_by_id.return_value = workspace_data

        with pytest.raises(SystemExit):
            main()

        mock_get_workspace_by_id.assert_called_once_with(adapter, workspace_id)
        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["workspace"]["id"] == workspace_id
        assert mock_module.exit_args["workspace"]["name"] == "test-workspace"
        assert "status" not in mock_module.exit_args["workspace"]
        adapter.cleanup.assert_called_once_with()
