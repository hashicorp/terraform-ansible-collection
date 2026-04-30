from unittest.mock import patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info import main


class TestConfigurationVersionInfo:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_success_with_configuration_version_id(self, mock_ansible_module, mock_get_config, enhanced_dummy_module):
        configuration_version_id = "cv-1234"
        configuration_data = {
            "id": configuration_version_id,
            "status": "uploaded",
            "auto_queue_runs": True,
            "source": "tfe-api",
            "speculative": False,
        }

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "configuration_version_id": configuration_version_id,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_ansible_module.return_value = mock_module

        mock_get_config.return_value = configuration_data

        with pytest.raises(SystemExit):
            main()

        mock_get_config.assert_called_once_with(mock_module.adapter, configuration_version_id)
        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["warnings"] == []
        assert mock_module.exit_args["configuration"] == configuration_data
        assert mock_module.failed is False

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_configuration_version_not_found(self, mock_ansible_module, mock_get_config, enhanced_dummy_module):
        configuration_version_id = "cv-missing"

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "configuration_version_id": configuration_version_id,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_ansible_module.return_value = mock_module

        mock_get_config.return_value = {}

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == f"Configuration version '{configuration_version_id}' was not found."

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_get_config_exception(self, mock_ansible_module, mock_get_config, enhanced_dummy_module):
        configuration_version_id = "cv-1234"

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "configuration_version_id": configuration_version_id,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_ansible_module.return_value = mock_module

        mock_get_config.side_effect = RuntimeError("boom")

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == "boom"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.get_config")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.configuration_version_info.AnsibleTerraformModule")
    def test_client_creation_error_uses_fail_json(self, mock_ansible_module, mock_get_config, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "configuration_version_id": "cv-1234",
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }
        mock_module.client = lambda: (i for i in ()).throw(RuntimeError("client-init-failed"))
        mock_ansible_module.return_value = mock_module

        with pytest.raises(AssertionError):
            main()

        mock_get_config.assert_not_called()
        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == "client-init-failed"
