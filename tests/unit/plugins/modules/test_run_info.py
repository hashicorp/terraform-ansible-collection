import sys
import types
from unittest.mock import Mock, patch

import pytest
from ansible.module_utils import _text
from ansible.module_utils.common.text.converters import to_text as converters_to_text

if "pytfe" not in sys.modules:
    pytfe = types.ModuleType("pytfe")

    class _DummyPytfeObject:
        def __init__(self, *args, **kwargs):
            pass

        @classmethod
        def model_validate(cls, data):
            return data

    pytfe.TFEClient = _DummyPytfeObject
    pytfe.TFEConfig = _DummyPytfeObject

    pytfe_errors = types.ModuleType("pytfe.errors")

    class NotFound(Exception):
        pass

    class AuthError(Exception):
        pass

    class ServerError(Exception):
        pass

    class TFEError(Exception):
        pass

    pytfe_errors.AuthError = AuthError
    pytfe_errors.NotFound = NotFound
    pytfe_errors.ServerError = ServerError
    pytfe_errors.TFEError = TFEError

    pytfe_models = types.ModuleType("pytfe.models")
    for _name in [
        "ConfigurationVersion",
        "ExecutionMode",
        "RunApplyOptions",
        "RunCancelOptions",
        "RunCreateOptions",
        "RunDiscardOptions",
        "RunVariable",
        "TagBindings",
        "WorkspaceCreateOptions",
        "WorkspaceUpdateOptions",
        "Workspace",
    ]:
        setattr(pytfe_models, _name, _DummyPytfeObject)

    def _models_getattr(_name):
        return _DummyPytfeObject

    pytfe_models.__getattr__ = _models_getattr

    sys.modules["pytfe"] = pytfe
    sys.modules["pytfe.errors"] = pytfe_errors
    sys.modules["pytfe.models"] = pytfe_models

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError

if not hasattr(_text, "to_text"):
    _text.to_text = converters_to_text


def create_run_response(run_id: str, status: str) -> dict:
    return {
        "data": {
            "id": run_id,
            "type": "runs",
            "attributes": {
                "status": status,
            },
        }
    }


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
        mock_get_run.assert_called_once_with(mock_client, "run-gXm1C5TmRo4CX")
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
        mock_get_run.assert_called_once_with(mock_client, run_id)
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

        mock_get_run.assert_called_once_with(mock_client, run_id)

        mock_module.exit_json.assert_called_once()
        call_args = mock_module.exit_json.call_args[1]
        assert call_args["run"] == expected_result
        assert call_args["changed"] is False
