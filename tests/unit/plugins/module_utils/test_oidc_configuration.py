# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/oidc_configuration.py (pytfe adapter)."""

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.oidc_configuration import (
    PROVIDERS,
    _ProviderSpec,
    build_desired_state,
    create_oidc_configuration,
    delete_oidc_configuration,
    get_oidc_configuration,
    state_absent,
    state_present,
    update_oidc_configuration,
)

MOD = "ansible_collections.hashicorp.terraform.plugins.module_utils.oidc_configuration"

_CLIENT_ATTR = {
    "aws": "aws_oidc_configurations",
    "azure": "azure_oidc_configurations",
    "gcp": "gcp_oidc_configurations",
    "vault": "vault_oidc_configurations",
}


def _make_model(payload):
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestProvidersTable:
    def test_all_four_providers_registered(self):
        assert set(PROVIDERS.keys()) == {"aws", "azure", "gcp", "vault"}

    @pytest.mark.parametrize("provider", ["aws", "azure", "gcp", "vault"])
    def test_client_attr_matches_pytfe(self, provider):
        assert PROVIDERS[provider].client_attr == _CLIENT_ATTR[provider]


class TestGetOIDCConfiguration:
    @pytest.mark.parametrize("provider", ["aws", "azure", "gcp", "vault"])
    def test_success(self, provider):
        adapter = Mock()
        client_attr = _CLIENT_ATTR[provider]
        getattr(adapter.client, client_attr).read.return_value = _make_model({"id": "oidc-1"})
        assert get_oidc_configuration(adapter, provider, "oidc-1") == {"id": "oidc-1"}
        getattr(adapter.client, client_attr).read.assert_called_once_with("oidc-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.aws_oidc_configurations.read.side_effect = NotFound("missing")
        assert get_oidc_configuration(adapter, "aws", "oidc-missing") is None


class TestCreateOIDCConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_create_uses_provider_options_cls(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc"})
        mock_opts_cls = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        fake_spec = _ProviderSpec("aws_oidc_configurations", mock_opts_cls, Mock())

        with patch.dict(f"{MOD}.PROVIDERS", {"aws": fake_spec}):
            result = create_oidc_configuration(adapter, "aws", "my-org", {"role_arn": "arn:aws:iam::123:role/tfc"})

        mock_opts_cls.model_validate.assert_called_once_with({"role_arn": "arn:aws:iam::123:role/tfc"})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.aws_oidc_configurations.create
        assert args[1] == "my-org"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc"}


class TestUpdateOIDCConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_update_uses_provider_options_cls(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "oidc-1", "role_name": "tfc-new"})
        mock_opts_cls = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        fake_spec = _ProviderSpec("vault_oidc_configurations", Mock(), mock_opts_cls)

        with patch.dict(f"{MOD}.PROVIDERS", {"vault": fake_spec}):
            result = update_oidc_configuration(adapter, "vault", "oidc-1", {"role_name": "tfc-new"})

        mock_opts_cls.model_validate.assert_called_once_with({"role_name": "tfc-new"})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.vault_oidc_configurations.update
        assert args[1] == "oidc-1"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result == {"id": "oidc-1", "role_name": "tfc-new"}


class TestDeleteOIDCConfiguration:
    @patch(f"{MOD}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe_call):
        adapter = Mock()
        delete_oidc_configuration(adapter, "gcp", "oidc-1")
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.gcp_oidc_configurations.delete
        assert args[1] == "oidc-1"
        assert "error_context" in kwargs


class TestBuildDesiredState:
    def test_strips_plumbing(self):
        params = {
            "role_arn": "arn:aws:iam::123:role/tfc",
            "oidc_configuration_id": None,
            "organization": "my-org",
            "state": "present",
            "check_mode": False,
            "tfe_token": "secret",
        }
        assert build_desired_state(params) == {"role_arn": "arn:aws:iam::123:role/tfc"}


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_no_id(self, adapter):
        params = {"organization": "my-org", "role_arn": "arn:aws:iam::123:role/tfc", "state": "present", "check_mode": False}
        with patch(f"{MOD}.create_oidc_configuration", return_value={"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc"}) as mock_create:
            result = state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

        mock_create.assert_called_once_with(adapter, "aws", "my-org", {"role_arn": "arn:aws:iam::123:role/tfc"})
        assert result["changed"] is True
        assert result["id"] == "oidc-1"

    def test_create_check_mode(self, adapter):
        params = {"organization": "my-org", "role_arn": "arn:aws:iam::123:role/tfc", "state": "present", "check_mode": True}
        with patch(f"{MOD}.create_oidc_configuration") as mock_create:
            result = state_present(adapter, "aws", ("role_arn",), params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_create_without_organization_raises(self, adapter):
        params = {"organization": None, "role_arn": "arn:aws:iam::123:role/tfc", "state": "present", "check_mode": False}
        with pytest.raises(ValueError, match="organization"):
            state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

    def test_create_missing_required_raises(self, adapter):
        params = {"organization": "my-org", "role_arn": None, "state": "present", "check_mode": False}
        with pytest.raises(ValueError, match="role_arn"):
            state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

    def test_update_missing_id_raises_not_found(self, adapter):
        params = {"oidc_configuration_id": "oidc-ghost", "role_arn": "x", "state": "present", "check_mode": False}
        with patch(f"{MOD}.get_oidc_configuration", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

    def test_idempotent_no_diff(self, adapter):
        current = {"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc"}
        params = {"oidc_configuration_id": "oidc-1", "role_arn": "arn:aws:iam::123:role/tfc", "state": "present", "check_mode": False}
        with patch(f"{MOD}.get_oidc_configuration", return_value=current), patch(f"{MOD}.update_oidc_configuration") as mock_update:
            result = state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "oidc-1"

    def test_update_on_drift(self, adapter):
        current = {"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/OLD"}
        params = {"oidc_configuration_id": "oidc-1", "role_arn": "arn:aws:iam::123:role/NEW", "state": "present", "check_mode": False}
        with patch(f"{MOD}.get_oidc_configuration", return_value=current), patch(
            f"{MOD}.update_oidc_configuration", return_value={"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/NEW"}
        ) as mock_update:
            result = state_present(adapter, "aws", ("role_arn",), params, check_mode=False)

        mock_update.assert_called_once_with(adapter, "aws", "oidc-1", {"role_arn": "arn:aws:iam::123:role/NEW"})
        assert result["changed"] is True

    def test_update_check_mode(self, adapter):
        current = {"id": "oidc-1", "role_arn": "arn:aws:iam::123:role/OLD"}
        params = {"oidc_configuration_id": "oidc-1", "role_arn": "arn:aws:iam::123:role/NEW", "state": "present", "check_mode": True}
        with patch(f"{MOD}.get_oidc_configuration", return_value=current), patch(f"{MOD}.update_oidc_configuration") as mock_update:
            result = state_present(adapter, "aws", ("role_arn",), params, check_mode=True)

        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_missing_id_raises(self, adapter):
        params = {"oidc_configuration_id": None, "state": "absent", "check_mode": False}
        with pytest.raises(ValueError, match="oidc_configuration_id"):
            state_absent(adapter, "aws", params, check_mode=False)

    def test_delete_existing(self, adapter):
        current = {"id": "oidc-1"}
        params = {"oidc_configuration_id": "oidc-1", "state": "absent", "check_mode": False}
        with patch(f"{MOD}.get_oidc_configuration", return_value=current), patch(f"{MOD}.delete_oidc_configuration") as mock_delete:
            result = state_absent(adapter, "aws", params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "aws", "oidc-1")
        assert result["changed"] is True

    def test_delete_absent_is_noop(self, adapter):
        params = {"oidc_configuration_id": "oidc-ghost", "state": "absent", "check_mode": False}
        with patch(f"{MOD}.get_oidc_configuration", return_value=None):
            result = state_absent(adapter, "aws", params, check_mode=False)

        assert result["changed"] is False

    def test_delete_check_mode(self, adapter):
        current = {"id": "oidc-1"}
        params = {"oidc_configuration_id": "oidc-1", "state": "absent", "check_mode": True}
        with patch(f"{MOD}.get_oidc_configuration", return_value=current), patch(f"{MOD}.delete_oidc_configuration") as mock_delete:
            result = state_absent(adapter, "aws", params, check_mode=True)

        mock_delete.assert_not_called()
        assert result["changed"] is True
