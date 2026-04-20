# -*- coding: utf-8 -*-

from unittest.mock import Mock, patch

import pytest


class TestRunInfoModule:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    def test_module_argument_specification(self, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        mock_module = enhanced_dummy_module
        mock_module.params = {"run_id": "run-arg-spec"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient",
            return_value=Mock(),
        ), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run",
            side_effect=Exception("test"),
        ):
            with pytest.raises(AssertionError):
                main()

        call_args = mock_ansible_module.call_args[1]
        assert call_args["argument_spec"] == {
            "run_id": {"type": "str", "required": True},
        }
        assert call_args["supports_check_mode"] is True

    @pytest.mark.parametrize(
        "run_id,run_info_data",
        [
            (
                "run-12ab345cde78",
                {
                    "id": "run-12ab345cde78",
                    "status": "planned_and_finished",
                    "message": "Triggered via API",
                    "plan_only": True,
                    "source": "tfe-api",
                    "variables": [],
                    "workspace": {"id": "ws-123"},
                    "status_timestamps": {"planned_and_finished_at": "2026-04-20T07:47:33Z"},
                },
            ),
            (
                "run-minimal-001",
                {
                    "id": "run-minimal-001",
                    "status": "planned",
                    "message": "minimal-run",
                    "plan_only": False,
                    "variables": [],
                },
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_run_found(self, mock_get_run, mock_terraform_client, mock_ansible_module, enhanced_dummy_module, run_id, run_info_data):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        expected_run = dict(run_info_data)

        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {
            "run_id": run_id,
            "tfe_token": "token",
            "tfe_address": "https://app.terraform.io",
        }

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_run.return_value = dict(run_info_data)

        with pytest.raises(SystemExit):
            main()

        mock_terraform_client.assert_called_once_with(
            tfe_token="token",
            tfe_address="https://app.terraform.io",
        )
        mock_get_run.assert_called_once_with(adapter, run_id)
        assert mock_module.exit_args["changed"] is False
        assert mock_module.exit_args["warnings"] == []
        assert mock_module.exit_args["run"] == expected_run
        assert mock_module.exit_args["run"]["id"] == run_id
        assert mock_module.exit_args["run"]["status"] == run_info_data["status"]
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_run_not_found_by_id(self, mock_get_run, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        run_id = "non-existent"
        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {"run_id": run_id}

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_run.return_value = {}

        with pytest.raises(AssertionError):
            main()

        mock_get_run.assert_called_once_with(adapter, run_id)
        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == f"The run with ID '{run_id}' was not found."
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_get_run_exception(self, mock_get_run, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        run_id = "run-boom"
        mock_module = enhanced_dummy_module
        mock_module.check_mode = False
        mock_module.params = {"run_id": run_id}

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_run.side_effect = RuntimeError("boom")

        with pytest.raises(AssertionError):
            main()

        assert mock_module.failed is True
        assert mock_module.fail_args["msg"] == "boom"
        adapter.cleanup.assert_called_once_with()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_client_parameters_passed_correctly(self, mock_get_run, mock_terraform_client, mock_ansible_module, enhanced_dummy_module):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        run_id = "run-params123"

        mock_module = enhanced_dummy_module
        mock_module.check_mode = True
        mock_module.params = {
            "run_id": run_id,
            "tfe_token": "test-token",
            "tfe_address": "app.terraform.io",
        }

        adapter = Mock()
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = adapter
        mock_get_run.return_value = {
            "id": run_id,
            "status": "planned",
            "message": "Triggered via API",
        }

        with pytest.raises(SystemExit):
            main()

        mock_terraform_client.assert_called_once_with(
            tfe_token="test-token",
            tfe_address="app.terraform.io",
        )
        adapter.cleanup.assert_called_once_with()
