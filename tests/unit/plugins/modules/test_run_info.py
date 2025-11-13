from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from tests.unit.constants import create_run_response


class TestRunInfo:

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_run_not_found(self, mock_get_run, mock_ansible_module, mock_terraform_client):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        # Create fake module object
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"run_id": "run-gXm1C5TmRo4CX"}
        mock_client = Mock()

        # Configure mocks
        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_run.side_effect = TerraformError({"status": 404, "data": {"errors": [{"status": "404", "title": "not found"}]}})

        # Run the module
        main()
        # Assert behavior
        mock_get_run.assert_called_once_with(client=mock_client, run_id="run-gXm1C5TmRo4CX")
        mock_module.fail_json.assert_called_once_with(msg=str({"status": 404, "data": {"errors": [{"status": "404", "title": "not found"}]}}))
        mock_module.exit_json.assert_not_called()

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_run_not_found_by_id(self, mock_get_run, mock_ansible_module, mock_terraform_client):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        # Create fake module object
        run_id = "non-existent"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"run_id": run_id}
        mock_client = Mock()

        # Configure mocks
        mock_terraform_client.return_value = mock_client
        mock_ansible_module.return_value = mock_module
        mock_get_run.return_value = {}

        # Run the module
        main()
        # Assert behavior
        mock_get_run.assert_called_once_with(client=mock_client, run_id=run_id)
        mock_module.fail_json.assert_called_once_with(msg=f"The run with ID '{run_id}' was not found.")

    @pytest.mark.parametrize(
        "run_info_data,expected_result",
        [
            (
                create_run_response(run_id="run-12ab345cde78", status="succeeded")["data"],
                create_run_response(run_id="run-12ab345cde78", status="succeeded")["data"],
            ),
        ],
    )
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.AnsibleTerraformModule")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.TerraformClient")
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.run_info.get_run")
    def test_run_found(self, mock_get_run, mock_terraform_client, mock_ansible_module, run_info_data, expected_result):
        from ansible_collections.hashicorp.terraform.plugins.modules.run_info import main

        run_id = "run-12ab345cde78"
        mock_module = Mock()
        mock_module.check_mode = False
        mock_module.params = {"run_id": run_id}
        mock_client = Mock()

        mock_ansible_module.return_value = mock_module
        mock_terraform_client.return_value = mock_client
        mock_get_run.return_value = run_info_data

        main()

        mock_get_run.assert_called_once_with(client=mock_client, run_id=run_id)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["run"] == expected_result
        assert call_args["changed"] is False
