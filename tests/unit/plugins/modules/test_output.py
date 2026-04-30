# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.output import main


class TestOutputModule:
    """Unit tests for output module main function."""

    @pytest.fixture
    def base_params(self):
        return {
            "state_version_output_id": None,
            "workspace_id": None,
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
            "tfe_token": "test-token",
            "tfe_address": "https://app.terraform.io",
        }

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_get_specific_output_by_id(self, mock_module_class, mock_get_specific, enhanced_dummy_module, base_params):
        params = dict(base_params)
        params.update({"state_version_output_id": "wsout-123"})

        module = enhanced_dummy_module
        module.params = params
        mock_module_class.return_value = module

        mock_get_specific.return_value = {
            "id": "wsout-123",
            "name": "server_id",
            "value": "i-1234567890",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }

        with pytest.raises(SystemExit):
            main()

        mock_get_specific.assert_called_once_with(module.adapter, "wsout-123", display_sensitive=False)
        assert module.exit_args["changed"] is False
        assert module.exit_args["output"]["id"] == "wsout-123"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_output_by_name")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_get_output_by_name(self, mock_module_class, mock_resolve_workspace, mock_get_by_name, enhanced_dummy_module, base_params):
        params = dict(base_params)
        params.update(
            {
                "workspace": "demo-workspace",
                "organization": "demo-org",
                "name": "database_url",
                "display_sensitive": True,
            }
        )

        module = enhanced_dummy_module
        module.params = params
        mock_module_class.return_value = module

        mock_resolve_workspace.return_value = "ws-123"
        mock_get_by_name.return_value = {
            "id": "wsout-55",
            "name": "database_url",
            "value": "postgres://user:pass@host/db",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }

        with pytest.raises(SystemExit):
            main()

        mock_resolve_workspace.assert_called_once_with(module.adapter, None, "demo-workspace", "demo-org")
        mock_get_by_name.assert_called_once_with(module.adapter, "ws-123", "database_url", display_sensitive=True)
        assert module.exit_args["output"]["name"] == "database_url"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_get_all_outputs(self, mock_module_class, mock_resolve_workspace, mock_get_workspace_outputs, enhanced_dummy_module, base_params):
        params = dict(base_params)
        params.update({"workspace_id": "ws-456"})

        module = enhanced_dummy_module
        module.params = params
        mock_module_class.return_value = module

        mock_resolve_workspace.return_value = "ws-456"
        mock_get_workspace_outputs.return_value = [
            {"id": "wsout-1", "name": "region", "value": "us-east-1", "sensitive": False, "type": "string", "detailed_type": "string"},
            {"id": "wsout-2", "name": "token", "value": "<sensitive>", "sensitive": True, "type": "string", "detailed_type": "string"},
        ]

        with pytest.raises(SystemExit):
            main()

        mock_resolve_workspace.assert_called_once_with(module.adapter, "ws-456", None, None)
        mock_get_workspace_outputs.assert_called_once_with(module.adapter, "ws-456", display_sensitive=False)
        assert module.exit_args["count"] == 2
        assert len(module.exit_args["outputs"]) == 2

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_workspace_outputs")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.resolve_workspace_id")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_get_all_outputs_empty(self, mock_module_class, mock_resolve_workspace, mock_get_workspace_outputs, enhanced_dummy_module, base_params):
        params = dict(base_params)
        params.update({"workspace_id": "ws-empty"})

        module = enhanced_dummy_module
        module.params = params
        mock_module_class.return_value = module

        mock_resolve_workspace.return_value = "ws-empty"
        mock_get_workspace_outputs.return_value = []

        with pytest.raises(SystemExit):
            main()

        assert module.exit_args["outputs"] == []
        assert module.exit_args["count"] == 0
        assert module.exit_args["msg"] == "No outputs found for workspace."

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_helper_error_uses_fail_json_and_cleanup(self, mock_module_class, mock_get_specific, enhanced_dummy_module, base_params):
        params = dict(base_params)
        params.update({"state_version_output_id": "wsout-missing"})

        module = enhanced_dummy_module
        module.params = params
        mock_module_class.return_value = module

        mock_get_specific.side_effect = ValueError("State version output with ID 'wsout-missing' was not found.")

        with pytest.raises(AssertionError):
            main()

        assert module.failed is True
        assert "wsout-missing" in module.fail_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_client_creation_error_uses_fail_json(self, mock_module_class, enhanced_dummy_module, base_params):
        module = enhanced_dummy_module
        module.params = dict(base_params)
        module.params.update({"state_version_output_id": "wsout-1"})
        module.client = lambda: (i for i in ()).throw(RuntimeError("client init failed"))
        mock_module_class.return_value = module

        with pytest.raises(AssertionError):
            main()

        assert module.failed is True
        assert "client init failed" in module.fail_args["msg"]

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.output.AnsibleTerraformModule")
    def test_main_argument_spec_shape(self, mock_module_class, enhanced_dummy_module):
        module = enhanced_dummy_module
        module.params = {
            "state_version_output_id": "wsout-1",
            "workspace_id": None,
            "workspace": None,
            "organization": None,
            "name": None,
            "display_sensitive": False,
            "tfe_token": "x",
            "tfe_address": "https://app.terraform.io",
        }
        mock_module_class.return_value = module

        with patch("ansible_collections.hashicorp.terraform.plugins.modules.output.get_specific_output") as mock_get_specific:
            mock_get_specific.return_value = {"id": "wsout-1"}

            with pytest.raises(SystemExit):
                main()

        kwargs = mock_module_class.call_args.kwargs
        assert "argument_spec" in kwargs
        assert kwargs["required_together"] == [["workspace", "organization"]]
        assert kwargs["required_one_of"] == [["state_version_output_id", "workspace_id", "workspace"]]
