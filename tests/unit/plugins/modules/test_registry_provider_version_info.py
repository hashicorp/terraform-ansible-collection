# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/registry_provider_version_info.py."""

from unittest.mock import Mock, patch

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info"

PARAMS = {
    "organization_name": "my-org",
    "namespace": "my-org",
    "name": "aws",
    "version": "1.0.0",
}

PROVIDER_VERSION_DATA = {
    "id": "provver-1",
    "version": "1.0.0",
    "key_id": "ABCD1234",
    "protocols": ["5.0"],
    "shasums_uploaded": False,
    "shasums_sig_uploaded": False,
    "created_at": "2025-01-01T00:00:00.000Z",
    "updated_at": "2025-01-01T00:00:00.000Z",
}


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


class TestRegistryProviderVersionInfoModule:
    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_read_success(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, mock_adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.return_value = PROVIDER_VERSION_DATA

        main()

        mock_get.assert_called_once_with(
            mock_adapter,
            {
                "organization_name": "my-org",
                "registry_name": "private",
                "namespace": "my-org",
                "name": "aws",
            },
            "1.0.0",
        )
        mock_module.exit_json.assert_called_once()
        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
        assert result["registry_provider_version"]["id"] == "provver-1"
        assert result["registry_provider_version"]["version"] == "1.0.0"

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_not_found_calls_fail_json(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, _adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.return_value = None

        main()

        mock_module.fail_json.assert_called_once()
        err_msg = mock_module.fail_json.call_args[1]["msg"]
        assert "1.0.0" in err_msg
        assert "aws" in err_msg
        assert "my-org" in err_msg

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_sdk_exception_calls_fail_json(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, _adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.side_effect = Exception("Connection timeout")

        main()

        mock_module.fail_json.assert_called_once()
        assert "Connection timeout" in mock_module.fail_json.call_args[1]["msg"]

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_result_contains_full_version_data(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, _adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.return_value = PROVIDER_VERSION_DATA

        main()

        result = mock_module.exit_json.call_args[1]
        pv = result["registry_provider_version"]
        assert pv["key_id"] == "ABCD1234"
        assert pv["protocols"] == ["5.0"]
        assert pv["shasums_uploaded"] is False
        assert pv["shasums_sig_uploaded"] is False

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_provider_id_built_with_private_registry(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, _adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.return_value = PROVIDER_VERSION_DATA

        main()

        call_provider_id = mock_get.call_args[0][1]
        assert call_provider_id["registry_name"] == "private"

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_changed_is_always_false(self, mock_get, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version_info import main

        mock_module, _adapter = _mock_module(PARAMS)
        mock_module_class.return_value = mock_module
        mock_get.return_value = PROVIDER_VERSION_DATA

        main()

        result = mock_module.exit_json.call_args[1]
        assert result["changed"] is False
