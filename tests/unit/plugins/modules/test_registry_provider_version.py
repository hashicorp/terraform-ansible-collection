# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/registry_provider_version.py."""

from unittest.mock import Mock, patch

import pytest

MOD_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version"


@pytest.fixture
def mock_adapter():
    return Mock()


PARAMS_PRESENT = {
    "organization_name": "my-org",
    "namespace": "my-org",
    "name": "aws",
    "version": "1.0.0",
    "key_id": "ABCD1234",
    "protocols": ["5.0"],
    "state": "present",
}

PARAMS_ABSENT = {
    "organization_name": "my-org",
    "namespace": "my-org",
    "name": "aws",
    "version": "1.0.0",
    "key_id": None,
    "protocols": None,
    "state": "absent",
}

EXISTING_VERSION = {
    "id": "provver-1",
    "version": "1.0.0",
    "key_id": "ABCD1234",
    "protocols": ["5.0"],
    "shasums_uploaded": False,
    "shasums_sig_uploaded": False,
}


class TestBuildProviderId:
    def test_builds_correct_provider_id(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import _build_provider_id

        params = {
            "organization_name": "my-org",
            "namespace": "my-org",
            "name": "aws",
        }
        result = _build_provider_id(params)

        assert result["organization_name"] == "my-org"
        assert result["registry_name"] == "private"
        assert result["namespace"] == "my-org"
        assert result["name"] == "aws"

    def test_registry_name_always_private(self):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import _build_provider_id

        params = {"organization_name": "org", "namespace": "ns", "name": "provider"}
        result = _build_provider_id(params)

        assert result["registry_name"] == "private"


class TestFetchRegistryProviderVersion:
    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_fetch_success(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import _fetch_registry_provider_version

        mock_get.return_value = EXISTING_VERSION
        params = {
            "organization_name": "my-org",
            "namespace": "my-org",
            "name": "aws",
            "version": "1.0.0",
        }

        result = _fetch_registry_provider_version(mock_adapter, params)

        assert result == EXISTING_VERSION
        mock_get.assert_called_once()

    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_fetch_returns_none_when_missing_params(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import _fetch_registry_provider_version

        params = {"organization_name": "my-org", "namespace": "my-org", "name": "aws"}  # missing version
        result = _fetch_registry_provider_version(mock_adapter, params)

        assert result is None
        mock_get.assert_not_called()

    @patch(f"{MOD_PATH}.get_registry_provider_version")
    def test_fetch_returns_none_when_not_found(self, mock_get, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import _fetch_registry_provider_version

        mock_get.return_value = None
        params = {
            "organization_name": "my-org",
            "namespace": "my-org",
            "name": "aws",
            "version": "9.9.9",
        }

        result = _fetch_registry_provider_version(mock_adapter, params)

        assert result is None


class TestStatePresent:
    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.create_registry_provider_version")
    def test_version_created_when_missing(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = None
        mock_create.return_value = EXISTING_VERSION

        result = state_present(mock_adapter, PARAMS_PRESENT, check_mode=False)

        assert result["changed"] is True
        assert result["id"] == "provver-1"
        assert result["version"] == "1.0.0"
        mock_create.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.create_registry_provider_version")
    def test_version_idempotent_when_exists(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = EXISTING_VERSION

        result = state_present(mock_adapter, PARAMS_PRESENT, check_mode=False)

        assert result["changed"] is False
        assert result["id"] == "provver-1"
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.create_registry_provider_version")
    def test_check_mode_does_not_create(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = None

        result = state_present(mock_adapter, PARAMS_PRESENT, check_mode=True)

        assert result["changed"] is True
        assert "would be created" in result["msg"]
        assert "check mode" in result["msg"]
        mock_create.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    def test_missing_key_id_raises(self, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = None
        params = dict(PARAMS_PRESENT, key_id=None)

        with pytest.raises(ValueError, match="'key_id' is required"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    def test_missing_protocols_raises(self, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = None
        params = dict(PARAMS_PRESENT, protocols=None)

        with pytest.raises(ValueError, match="'protocols' is required"):
            state_present(mock_adapter, params, check_mode=False)

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.create_registry_provider_version")
    def test_create_called_with_correct_data(self, mock_create, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_present

        mock_fetch.return_value = None
        mock_create.return_value = EXISTING_VERSION

        state_present(mock_adapter, PARAMS_PRESENT, check_mode=False)

        _first_arg, call_args = mock_create.call_args[0][1], mock_create.call_args[0][2]
        passed_data = mock_create.call_args[0][2]
        assert passed_data["version"] == "1.0.0"
        assert passed_data["key_id"] == "ABCD1234"
        assert passed_data["protocols"] == ["5.0"]


class TestStateAbsent:
    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.delete_registry_provider_version")
    def test_delete_when_exists(self, mock_delete, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_absent

        mock_fetch.return_value = EXISTING_VERSION

        result = state_absent(mock_adapter, PARAMS_ABSENT, check_mode=False)

        assert result["changed"] is True
        assert "deleted successfully" in result["msg"]
        mock_delete.assert_called_once()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.delete_registry_provider_version")
    def test_no_op_when_already_absent(self, mock_delete, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_absent

        mock_fetch.return_value = None

        result = state_absent(mock_adapter, PARAMS_ABSENT, check_mode=False)

        assert result["changed"] is False
        assert "already absent" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.delete_registry_provider_version")
    def test_check_mode_does_not_delete(self, mock_delete, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_absent

        mock_fetch.return_value = EXISTING_VERSION

        result = state_absent(mock_adapter, PARAMS_ABSENT, check_mode=True)

        assert result["changed"] is True
        assert "would be deleted" in result["msg"]
        assert "check mode" in result["msg"]
        mock_delete.assert_not_called()

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.delete_registry_provider_version")
    def test_msg_includes_version(self, mock_delete, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_absent

        mock_fetch.return_value = EXISTING_VERSION

        result = state_absent(mock_adapter, PARAMS_ABSENT, check_mode=False)

        assert "1.0.0" in result["msg"]

    @patch(f"{MOD_PATH}._fetch_registry_provider_version")
    @patch(f"{MOD_PATH}.delete_registry_provider_version")
    def test_delete_called_with_correct_version(self, mock_delete, mock_fetch, mock_adapter):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import state_absent

        mock_fetch.return_value = EXISTING_VERSION
        params = dict(PARAMS_ABSENT, version="2.3.4")

        state_absent(mock_adapter, params, check_mode=False)

        call_args = mock_delete.call_args[0]
        assert call_args[2] == "2.3.4"


class TestMainModule:
    def _mock_module(self, params, check_mode=False):
        mock_module = Mock()
        mock_module.params = params
        mock_module.check_mode = check_mode

        mock_adapter = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_adapter)
        mock_context.__exit__ = Mock(return_value=False)
        mock_module.client.return_value = mock_context
        return mock_module, mock_adapter

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.state_present")
    def test_main_state_present(self, mock_state_present, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import main

        mock_module, mock_adapter = self._mock_module(PARAMS_PRESENT)
        mock_module_class.return_value = mock_module
        mock_state_present.return_value = {"changed": True, **EXISTING_VERSION}

        main()

        # main() injects check_mode into params; just assert it was called once with the adapter
        assert mock_state_present.call_count == 1
        call_args = mock_state_present.call_args[0]
        assert call_args[0] is mock_adapter
        assert call_args[2] is False  # check_mode=False
        mock_module.exit_json.assert_called_once()

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.state_absent")
    def test_main_state_absent(self, mock_state_absent, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import main

        mock_module, mock_adapter = self._mock_module(PARAMS_ABSENT)
        mock_module_class.return_value = mock_module
        mock_state_absent.return_value = {"changed": True, "msg": "deleted"}

        main()

        # main() injects check_mode into params; just assert it was called once with the adapter
        assert mock_state_absent.call_count == 1
        call_args = mock_state_absent.call_args[0]
        assert call_args[0] is mock_adapter
        assert call_args[2] is False  # check_mode=False
        mock_module.exit_json.assert_called_once()

    @patch(f"{MOD_PATH}.AnsibleTerraformModule")
    @patch(f"{MOD_PATH}.state_present")
    def test_main_exception_calls_fail_json(self, mock_state_present, mock_module_class):
        from ansible_collections.hashicorp.terraform.plugins.modules.registry_provider_version import main

        mock_module, _adapter = self._mock_module(PARAMS_PRESENT)
        mock_module_class.return_value = mock_module
        mock_state_present.side_effect = Exception("API failure")

        main()

        mock_module.fail_json.assert_called_once()
        assert "API failure" in mock_module.fail_json.call_args[1]["msg"]
