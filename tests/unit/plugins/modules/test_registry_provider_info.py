# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import patch

import pytest

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_info"


class TestRegistryProviderInfoModule:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "my-org",
            "namespace": "my-org",
            "name": "aws",
            "registry_name": "private",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.get_registry_provider", side_effect=Exception("fail")):
            with pytest.raises(AssertionError):
                main()

        call_args = mock_ansible_module.call_args[1]
        assert call_args["argument_spec"] == {
            "organization": {"type": "str", "required": True},
            "namespace": {"type": "str", "required": True},
            "name": {"type": "str", "required": True},
            "registry_name": {"type": "str", "default": "private", "choices": ["private", "public"]},
        }
        assert call_args["supports_check_mode"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_registry_provider")
    def test_registry_provider_retrieval(self, mock_get, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "my-org",
            "namespace": "my-org",
            "name": "aws",
            "registry_name": "private",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_get.return_value = {"id": "regprov-1", "name": "aws"}

        with pytest.raises(SystemExit):
            main()

        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["registry_provider"] == {"id": "regprov-1", "name": "aws"}

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    @patch(f"{MODULE_PATH}.get_registry_provider")
    def test_registry_provider_not_found(self, mock_get, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {
            "organization": "my-org",
            "namespace": "my-org",
            "name": "aws",
            "registry_name": "private",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module
        mock_get.return_value = None

        with pytest.raises(AssertionError):
            main()

        assert "not found" in mock_module.fail_args["msg"]
