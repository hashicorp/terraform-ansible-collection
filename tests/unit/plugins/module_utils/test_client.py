# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.client import (
    _ARGSPEC_TO_SDK,
    AUTH_ARGSPEC,
    AUTH_KEYS,
    AnsibleTerraformModule,
    TerraformClient,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformTokenNotFoundError,
)


class TestAnsibleTerraformModule:
    """Test AnsibleTerraformModule wrapper class."""

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_module_initialization_merges_argspecs(self, mock_ansible_module):
        """Test that module initialization merges AUTH_ARGSPEC with custom argspec."""
        custom_argspec = {
            "workspace": {"type": "str", "required": True},
            "organization": {"type": "str", "required": True},
        }

        AnsibleTerraformModule(argument_spec=custom_argspec)

        mock_ansible_module.assert_called_once()
        call_kwargs = mock_ansible_module.call_args[1]
        merged_spec = call_kwargs["argument_spec"]

        # Every AUTH_ARGSPEC key flows into the merged spec
        for key in AUTH_KEYS:
            assert key in merged_spec
        assert "workspace" in merged_spec
        assert "organization" in merged_spec

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_module_initialization_with_additional_kwargs(self, mock_ansible_module):
        """Test module initialization passes additional kwargs to AnsibleModule."""
        AnsibleTerraformModule(
            argument_spec={"workspace": {"type": "str"}},
            supports_check_mode=True,
            required_together=[["workspace", "organization"]],
        )

        call_kwargs = mock_ansible_module.call_args[1]
        assert call_kwargs["supports_check_mode"] is True
        assert call_kwargs["required_together"] == [["workspace", "organization"]]

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_attribute_delegation(self, mock_ansible_module):
        """Test that attributes are delegated to underlying AnsibleModule."""
        mock_instance = Mock()
        mock_instance.params = {"workspace": "test"}
        mock_instance.check_mode = False
        mock_ansible_module.return_value = mock_instance

        module = AnsibleTerraformModule(argument_spec={})

        assert module.params == {"workspace": "test"}
        assert module.check_mode is False

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_method_delegation(self, mock_ansible_module):
        """Test that methods are delegated to underlying AnsibleModule."""
        mock_instance = Mock()
        mock_ansible_module.return_value = mock_instance

        module = AnsibleTerraformModule(argument_spec={})

        module.exit_json(changed=True)
        module.fail_json(msg="error")
        module.warn("warning")

        mock_instance.exit_json.assert_called_once_with(changed=True)
        mock_instance.fail_json.assert_called_once_with(msg="error")
        mock_instance.warn.assert_called_once_with("warning")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.client.AnsibleModule")
    def test_client_method_returns_terraform_client(self, mock_ansible_module):
        """module.client() should build a TerraformClient bound to module.params."""
        mock_instance = Mock()
        mock_instance.params = {
            "tfe_token": "token-xyz",
            "tfe_address": "https://tfe.example.com",
            "tfe_timeout": 60.0,
            "workspace": "ws-1",
        }
        mock_ansible_module.return_value = mock_instance

        module = AnsibleTerraformModule(argument_spec={"workspace": {"type": "str"}})
        adapter = module.client()

        assert isinstance(adapter, TerraformClient)
        assert adapter._sdk_kwargs == {
            "token": "token-xyz",
            "address": "https://tfe.example.com",
            "timeout": 60.0,
        }


class TestAuthSchemaContract:
    """Guards on the AUTH_ARGSPEC → SDK wiring that each new module relies on."""

    def test_auth_keys_derived_from_argspec(self):
        """AUTH_KEYS must be derived from AUTH_ARGSPEC so additions stay in sync."""
        assert AUTH_KEYS == tuple(AUTH_ARGSPEC.keys())

    def test_every_auth_key_has_sdk_mapping(self):
        """Every exposed argspec key must map to a pytfe.TFEConfig field."""
        missing = [k for k in AUTH_KEYS if k not in _ARGSPEC_TO_SDK]
        assert missing == [], f"AUTH_KEYS without _ARGSPEC_TO_SDK entry: {missing}"

    def test_argspec_to_sdk_has_no_unknown_keys(self):
        """_ARGSPEC_TO_SDK must not reference keys outside AUTH_ARGSPEC."""
        extra = [k for k in _ARGSPEC_TO_SDK if k not in AUTH_ARGSPEC]
        assert extra == [], f"_ARGSPEC_TO_SDK has keys not in AUTH_ARGSPEC: {extra}"


class TestTerraformClientInitialization:
    """Test TerraformClient initialization and precheck behavior."""

    def test_client_initialization_with_token(self):
        client = TerraformClient(token="test-token")
        assert client._sdk_kwargs == {"token": "test-token"}

    def test_client_initialization_without_token_raises_error(self):
        with pytest.raises(TerraformTokenNotFoundError) as excinfo:
            TerraformClient()
        assert "Authentication token is required" in str(excinfo.value)

    def test_client_initialization_with_empty_token_raises_error(self):
        with pytest.raises(TerraformTokenNotFoundError):
            TerraformClient(token="")


class TestFromMapping:
    """Test the allowlist translation from argspec mapping -> SDK kwargs."""

    def test_translates_argspec_keys_to_sdk_keys(self):
        client = TerraformClient.from_mapping(
            {
                "tfe_token": "t",
                "tfe_address": "https://tfe.example.com",
                "tfe_timeout": 10.0,
                "tfe_verify_tls": False,
            }
        )
        assert client._sdk_kwargs == {
            "token": "t",
            "address": "https://tfe.example.com",
            "timeout": 10.0,
            "verify_tls": False,
        }

    def test_ignores_non_auth_keys(self):
        """Allowlist: keys outside AUTH_KEYS never reach TFEConfig."""
        client = TerraformClient.from_mapping(
            {
                "tfe_token": "t",
                "workspace_id": "ws-123",
                "state": "present",
                "force": True,
            }
        )
        assert client._sdk_kwargs == {"token": "t"}

    def test_drops_none_values_so_sdk_defaults_apply(self):
        """None values must not be forwarded — they'd override pytfe's defaults."""
        client = TerraformClient.from_mapping({"tfe_token": "t", "tfe_proxies": None, "tfe_ca_bundle": None})
        assert client._sdk_kwargs == {"token": "t"}

    def test_raises_when_token_missing(self):
        with pytest.raises(TerraformTokenNotFoundError):
            TerraformClient.from_mapping({"tfe_address": "https://x"})


class TestFromModule:
    """Test the AnsibleTerraformModule entrypoint."""

    def test_from_module_reads_params(self):
        fake_module = Mock()
        fake_module.params = {
            "tfe_token": "t",
            "tfe_address": "https://tfe",
            "tfe_max_retries": 7,
            "workspace": "ignored",
        }
        client = TerraformClient.from_module(fake_module)
        assert client._sdk_kwargs == {
            "token": "t",
            "address": "https://tfe",
            "max_retries": 7,
        }


class TestContextManager:
    """Test the __enter__/__exit__ lifecycle."""

    def test_enter_returns_self(self):
        client = TerraformClient(token="t")
        with client as ctx:
            assert ctx is client

    def test_exit_calls_cleanup(self):
        client = TerraformClient(token="t")
        with patch.object(client, "cleanup") as mock_cleanup:
            with client:
                pass
            mock_cleanup.assert_called_once()

    def test_exit_cleanup_runs_on_exception(self):
        client = TerraformClient(token="t")
        with patch.object(client, "cleanup") as mock_cleanup:
            with pytest.raises(RuntimeError):
                with client:
                    raise RuntimeError("boom")
            mock_cleanup.assert_called_once()


class TestTerraformClientLazyLoading:
    """Test TerraformClient lazy loading of config and client."""

    def test_config_lazy_loading(self):
        client = TerraformClient(token="test-token")
        assert client._config is None

        cfg = client.config
        assert cfg is not None
        assert client._config is not None

    def test_config_forwards_all_sdk_kwargs(self):
        """TFEConfig must receive every kwarg the adapter was built with."""
        client = TerraformClient(
            token="t",
            address="https://tfe.example.com",
            timeout=45.0,
            verify_tls=False,
            max_retries=2,
        )
        cfg = client.config
        assert cfg.token == "t"
        assert cfg.address == "https://tfe.example.com"
        assert cfg.timeout == 45.0
        assert cfg.verify_tls is False
        assert cfg.max_retries == 2


class TestTerraformClientCleanup:
    """Test TerraformClient cleanup method."""

    def test_cleanup_handles_no_client(self):
        client = TerraformClient(token="test-token")
        client.cleanup()
        assert client._client is None
        assert client._config is None

    def test_cleanup_is_idempotent(self):
        client = TerraformClient(token="test-token")
        client.cleanup()
        client.cleanup()  # must not raise
