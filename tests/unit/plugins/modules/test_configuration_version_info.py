from unittest.mock import Mock, patch

import pytest

from tests.unit.constants import create_configuration_version_response


class TestConfigurationVersionInfo:

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_workspace_by_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_workspace_not_found_by_id(self, mock_ansible_module, mock_terraform_client, mock_get_workspace_by_id, mock_get_config):
        from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": "ws-nonexistent"}
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_workspace_by_id.return_value = None

        main()

        mock_module.fail_json.assert_called_once_with(msg="Workspace 'ws-nonexistent' was not found.")
        mock_module.exit_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_workspace")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_workspace_not_found_by_name(self, mock_ansible_module, mock_terraform_client, mock_get_workspace, mock_get_config):
        from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace": "ws", "organization": "org"}
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_workspace.return_value = None

        main()

        mock_module.fail_json.assert_called_once_with(msg="The workspace ws in org organization was not found.")
        mock_module.exit_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_workspace_by_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_configuration_version_not_found(self, mock_ansible_module, mock_terraform_client, mock_get_workspace_by_id, mock_get_config):
        from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main

        workspace_id = "ws-1234"
        config_version_id = "cv-1234"

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id}
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_workspace_by_id.return_value = {"data": {"relationships": {"current-configuration-version": {"data": {"id": config_version_id}}}}}
        mock_get_config.return_value = None

        main()

        mock_module.fail_json.assert_called_once_with(msg=f"Configuration version '{config_version_id}' was not found.")
        mock_module.exit_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_workspace_by_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_success_with_workspace_id(self, mock_ansible_module, mock_terraform_client, mock_get_workspace_by_id, mock_get_config):
        from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main

        workspace_id = "ws-1234"
        config_version_id = "cv-5678"
        config_data = {"data": {"id": config_version_id, "type": "configuration-versions", "attributes": {"status": "uploaded"}}}

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace_id": workspace_id}
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_workspace_by_id.return_value = {"data": {"relationships": {"current-configuration-version": {"data": {"id": config_version_id}}}}}
        mock_get_config.return_value = config_data

        main()

        mock_module.exit_json.assert_called_once()
        args = mock_module.exit_json.call_args[1]
        assert args["configuration"] == config_data["data"]
        assert args["changed"] is False
        mock_module.fail_json.assert_not_called()

    @pytest.mark.parametrize(
        "workspace, organization, config_data, expected_config_id",
        [
            ("ws-abc", "org-1", create_configuration_version_response(cv_id="cv-123", status="uploaded"), "cv-123"),
            ("ws-def", "org-2", create_configuration_version_response(cv_id="cv-456", status="uploaded"), "cv-456"),
            ("ws-xyz", "org-3", create_configuration_version_response(cv_id="cv-789", status="uploaded"), "cv-789"),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_workspace")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_success_with_workspace_and_org(
        self, mock_ansible_module, mock_terraform_client, mock_get_workspace, mock_get_config, workspace, organization, config_data, expected_config_id
    ):
        from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main

        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"workspace": workspace, "organization": organization}
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = Mock()
        mock_get_workspace.return_value = {"data": {"relationships": {"current-configuration-version": {"data": {"id": expected_config_id}}}}}
        mock_get_config.return_value = config_data

        main()

        mock_module.exit_json.assert_called_once()
        args = mock_module.exit_json.call_args[1]
        assert args["configuration"] == config_data["data"]
        assert args["changed"] is False
        mock_module.fail_json.assert_not_called()
