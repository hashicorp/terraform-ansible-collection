# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/organizations.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.organizations import (
    _build_desired_state,
    _filter_current_state,
    main,
    state_absent,
    state_present,
)


class TestHelpers:
    def test_build_desired_state_strips_plumbing(self):
        params = {
            "name": "demo-org",
            "email": "ops@example.com",
            "cost_estimation_enabled": True,
            "tfe_token": "secret",
            "tf_token": "legacy",
            "state": "present",
            "check_mode": False,
            "saml_enabled": None,
        }

        result = _build_desired_state(params)

        assert result == {
            "name": "demo-org",
            "email": "ops@example.com",
            "cost_estimation_enabled": True,
        }

    def test_filter_current_state_projects_onto_wanted_keys(self):
        have = {"email": "a@b.c", "cost_estimation_enabled": True, "created_at": "2026-01-01T00:00:00Z"}
        want = {"email": "new@b.c"}

        assert _filter_current_state(have, want) == {"email": "a@b.c"}


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_create_when_missing(self, adapter):
        params = {"name": "demo", "email": "ops@example.com", "state": "present", "check_mode": False}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=None) as mock_get, patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.create_organization",
            return_value={"id": "demo", "name": "demo", "email": "ops@example.com"},
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)

        mock_get.assert_called_once_with(adapter, "demo")
        mock_create.assert_called_once_with(adapter, {"name": "demo", "email": "ops@example.com"})
        assert result["changed"] is True
        assert result["id"] == "demo"

    def test_create_without_email_raises(self, adapter):
        params = {"name": "demo", "email": None, "state": "present", "check_mode": False}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=None):
            with pytest.raises(ValueError, match="email"):
                state_present(adapter, params, check_mode=False)

    def test_create_check_mode(self, adapter):
        params = {"name": "demo", "email": "ops@example.com", "state": "present", "check_mode": True}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=None), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.create_organization"
        ) as mock_create:
            result = state_present(adapter, params, check_mode=True)

        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_idempotent_no_diff(self, adapter):
        current = {
            "id": "demo",
            "name": "demo",
            "email": "ops@example.com",
            "cost_estimation_enabled": True,
        }
        params = {
            "name": "demo",
            "email": "ops@example.com",
            "cost_estimation_enabled": True,
            "state": "present",
            "check_mode": False,
        }
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=current), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.update_organization"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "demo"

    def test_update_on_drift(self, adapter):
        current = {
            "id": "demo",
            "name": "demo",
            "email": "old@example.com",
            "cost_estimation_enabled": False,
        }
        params = {
            "name": "demo",
            "email": "new@example.com",
            "cost_estimation_enabled": True,
            "state": "present",
            "check_mode": False,
        }
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=current), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.update_organization",
            return_value={"id": "demo", "email": "new@example.com", "cost_estimation_enabled": True},
        ) as mock_update:
            result = state_present(adapter, params, check_mode=False)

        mock_update.assert_called_once_with(
            adapter,
            "demo",
            {"email": "new@example.com", "cost_estimation_enabled": True},
        )
        assert result["changed"] is True

    def test_update_check_mode(self, adapter):
        current = {"id": "demo", "name": "demo", "email": "old@example.com"}
        params = {"name": "demo", "email": "new@example.com", "state": "present", "check_mode": True}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=current), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.update_organization"
        ) as mock_update:
            result = state_present(adapter, params, check_mode=True)

        mock_update.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def test_delete_existing(self, adapter):
        params = {"name": "demo", "state": "absent", "check_mode": False}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value={"id": "demo"}), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.delete_organization"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_called_once_with(adapter, "demo")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_absent_is_noop(self, adapter):
        params = {"name": "ghost", "state": "absent", "check_mode": False}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value=None), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.delete_organization"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=False)

        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_check_mode(self, adapter):
        params = {"name": "demo", "state": "absent", "check_mode": True}
        with patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.get_organization", return_value={"id": "demo"}), patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.delete_organization"
        ) as mock_delete:
            result = state_absent(adapter, params, check_mode=True)

        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]


class TestMain:
    @patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "demo", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.state_present",
            side_effect=Exception("stop"),
        ):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]

        assert argument_spec["name"] == {"type": "str", "required": True, "aliases": ["organization"]}
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["default_execution_mode"]["choices"] == ["remote", "local", "agent"]
        assert argument_spec["collaborator_auth_policy"]["choices"] == ["password", "two_factor_mandatory"]
        assert call_kwargs["supports_check_mode"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.AnsibleTerraformModule")
    def test_main_present_invokes_state_present(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "demo", "email": "ops@example.com", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.state_present",
            return_value={"changed": True, "id": "demo"},
        ) as mock_present:
            with pytest.raises(SystemExit):
                main()

        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True
        assert mock_module.exit_args["id"] == "demo"

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.AnsibleTerraformModule")
    def test_main_absent_invokes_state_absent(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "demo", "state": "absent"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.state_absent",
            return_value={"changed": True, "msg": "Organization demo has been deleted successfully"},
        ) as mock_absent:
            with pytest.raises(SystemExit):
                main()

        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.modules.organizations.AnsibleTerraformModule")
    def test_main_propagates_errors_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {"name": "demo", "state": "present"}
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            "ansible_collections.hashicorp.terraform.plugins.modules.organizations.state_present",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(AssertionError):
                main()

        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]
