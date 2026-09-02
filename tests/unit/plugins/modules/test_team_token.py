# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/team_token.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.team_token import (
    main,
    state_absent,
    state_present,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.team_token"

# Synthetic token data — never real values.
_TOKEN_DATA = {"id": "at-abc123", "token": "synth-secret", "description": None, "created_at": "2026-05-01T10:00:00Z"}


class TestStatePresent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    # ── Team-token (no description) flow ─────────────────────────────────────

    def test_team_token_create_when_absent(self, adapter):
        """Token absent → create → changed=True, token value returned."""
        params = {"team_id": "team-xyz789", "description": None, "expired_at": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.create_team_token", return_value=_TOKEN_DATA) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_called_once_with(adapter, "team-xyz789", {})
        assert result["changed"] is True
        assert result["id"] == "at-abc123"
        assert result["token"] == "synth-secret"

    def test_team_token_idempotent_when_present(self, adapter):
        """Token already exists → no create → changed=False."""
        existing = {"id": "at-abc123", "description": None, "created_at": "2026-05-01T10:00:00Z"}
        params = {"team_id": "team-xyz789", "description": None, "expired_at": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=existing), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "at-abc123"

    def test_team_token_check_mode_when_absent(self, adapter):
        """Check mode + absent: no creation, changed=True, msg contains 'check mode'."""
        params = {"team_id": "team-xyz789", "description": None, "expired_at": None, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_team_token_check_mode_when_present(self, adapter):
        """Check mode + existing: no mutation, changed=False."""
        existing = {"id": "at-abc123", "description": None}
        params = {"team_id": "team-xyz789", "description": None, "expired_at": None, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=existing), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is False
        assert result["id"] == "at-abc123"

    def test_missing_team_id_raises(self, adapter):
        """state=present without team_id raises ValueError."""
        params = {"team_id": None, "description": None, "expired_at": None, "check_mode": False}
        with pytest.raises(ValueError, match="team_id"):
            state_present(adapter, params, check_mode=False)

    # ── expired_at-only flow ──────────────────────────────────────────────────

    def test_expired_at_only_reads_before_creating(self, adapter):
        """expired_at without description uses the team-token flow (read before create).

        Without a description, this stays in the team-token flow — it must NOT
        be treated as a named-token flow.
        """
        params = {"team_id": "team-xyz789", "description": None, "expired_at": "2027-12-31T00:00:00Z", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None) as mock_read, patch(
            f"{MODULE_PATH}.create_team_token", return_value={"id": "at-exp123", "token": "synth-s"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_read.assert_called_once_with(adapter, "team-xyz789")
        mock_create.assert_called_once_with(adapter, "team-xyz789", {"expired_at": "2027-12-31T00:00:00Z"})
        assert result["changed"] is True

    def test_expired_at_only_idempotent_when_present(self, adapter):
        """expired_at without description: existing token → no regeneration → changed=False."""
        existing = {"id": "at-abc123", "description": None}
        params = {"team_id": "team-xyz789", "description": None, "expired_at": "2027-12-31T00:00:00Z", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=existing), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_create.assert_not_called()
        assert result["changed"] is False

    def test_expired_at_only_check_mode_when_absent(self, adapter):
        """expired_at-only, check mode, absent: changed=True, no mutation."""
        params = {"team_id": "team-xyz789", "description": None, "expired_at": "2027-12-31T00:00:00Z", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_expired_at_only_check_mode_when_present(self, adapter):
        """expired_at-only, check mode, existing: changed=False, no mutation."""
        existing = {"id": "at-abc123", "description": None}
        params = {"team_id": "team-xyz789", "description": None, "expired_at": "2027-12-31T00:00:00Z", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=existing), patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is False

    # ── Named-token (description) flow ───────────────────────────────────────

    def test_named_token_always_creates(self, adapter):
        """With description, create is called every time.

        Named-token lookup/listing is outside this module's scope, so the named
        flow is intentionally not idempotent. get_team_token must NOT be called.
        """
        params = {"team_id": "team-xyz789", "description": "CI token", "expired_at": None, "check_mode": False}
        named_token = {"id": "at-desc123", "token": "synth-secret", "description": "CI token"}
        with patch(f"{MODULE_PATH}.get_team_token") as mock_read, patch(f"{MODULE_PATH}.create_team_token", return_value=named_token) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_read.assert_not_called()
        mock_create.assert_called_once_with(adapter, "team-xyz789", {"description": "CI token"})
        assert result["changed"] is True
        assert result["id"] == "at-desc123"

    def test_named_token_with_expired_at(self, adapter):
        """description + expired_at: both are passed to create_team_token."""
        params = {
            "team_id": "team-xyz789",
            "description": "CI token",
            "expired_at": "2027-12-31T00:00:00Z",
            "check_mode": False,
        }
        named_token = {"id": "at-desc123", "token": "synth-secret"}
        with patch(f"{MODULE_PATH}.get_team_token") as mock_read, patch(f"{MODULE_PATH}.create_team_token", return_value=named_token) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_read.assert_not_called()
        mock_create.assert_called_once_with(adapter, "team-xyz789", {"description": "CI token", "expired_at": "2027-12-31T00:00:00Z"})
        assert result["changed"] is True

    def test_named_token_check_mode(self, adapter):
        """Check mode with description: no creation, changed=True."""
        params = {"team_id": "team-xyz789", "description": "CI token", "expired_at": None, "check_mode": True}
        with patch(f"{MODULE_PATH}.create_team_token") as mock_create:
            result = state_present(adapter, params, check_mode=True)
        mock_create.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_empty_string_description_uses_team_token_flow(self, adapter):
        """description="" is normalised to None — same team-token read-before-create path as None."""
        params = {"team_id": "team-xyz789", "description": "", "expired_at": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None) as mock_read, patch(
            f"{MODULE_PATH}.create_team_token", return_value={"id": "at-abc123", "token": "synth-s"}
        ) as mock_create:
            result = state_present(adapter, params, check_mode=False)
        mock_read.assert_called_once_with(adapter, "team-xyz789")
        mock_create.assert_called_once_with(adapter, "team-xyz789", {})
        assert result["changed"] is True

    def test_sdk_error_propagates(self, adapter):
        params = {"team_id": "team-xyz789", "description": None, "expired_at": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.create_team_token", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                state_present(adapter, params, check_mode=False)


class TestStateAbsent:
    @pytest.fixture
    def adapter(self):
        return Mock()

    # ── Delete by team_id ─────────────────────────────────────────────────────

    def test_team_token_delete_when_present(self, adapter):
        """Token exists → delete → changed=True."""
        params = {"team_id": "team-xyz789", "token_id": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value={"id": "at-abc123"}), patch(f"{MODULE_PATH}.delete_team_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "team-xyz789")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_team_token_delete_already_absent(self, adapter):
        """Token does not exist → no delete → changed=False."""
        params = {"team_id": "team-xyz789", "token_id": None, "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.delete_team_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_team_token_delete_check_mode_when_present(self, adapter):
        """Check mode + existing: no delete, changed=True."""
        params = {"team_id": "team-xyz789", "token_id": None, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value={"id": "at-abc123"}), patch(f"{MODULE_PATH}.delete_team_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_team_token_delete_check_mode_when_absent(self, adapter):
        """Check mode + absent: no delete, changed=False."""
        params = {"team_id": "team-xyz789", "token_id": None, "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token", return_value=None), patch(f"{MODULE_PATH}.delete_team_token") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    # ── By token_id delete (read-before-delete) ───────────────────────────────

    def test_delete_by_token_id_when_present(self, adapter):
        """Existing token → read → delete_by_id → changed=True."""
        params = {"team_id": None, "token_id": "at-abc123", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token_by_id", return_value={"id": "at-abc123"}), patch(f"{MODULE_PATH}.delete_team_token_by_id") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_called_once_with(adapter, "at-abc123")
        assert result["changed"] is True
        assert "deleted" in result["msg"]

    def test_delete_by_token_id_not_found(self, adapter):
        """Token not found by read → no delete → changed=False (idempotent)."""
        params = {"team_id": None, "token_id": "at-missing", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token_by_id", return_value=None), patch(f"{MODULE_PATH}.delete_team_token_by_id") as mock_delete:
            result = state_absent(adapter, params, check_mode=False)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_by_token_id_check_mode_when_present(self, adapter):
        """Check mode + existing token: no delete, changed=True."""
        params = {"team_id": None, "token_id": "at-abc123", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token_by_id", return_value={"id": "at-abc123"}), patch(f"{MODULE_PATH}.delete_team_token_by_id") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is True
        assert "check mode" in result["msg"]

    def test_delete_by_token_id_check_mode_when_absent(self, adapter):
        """Check mode + absent token: no delete, changed=False."""
        params = {"team_id": None, "token_id": "at-missing", "check_mode": True}
        with patch(f"{MODULE_PATH}.get_team_token_by_id", return_value=None), patch(f"{MODULE_PATH}.delete_team_token_by_id") as mock_delete:
            result = state_absent(adapter, params, check_mode=True)
        mock_delete.assert_not_called()
        assert result["changed"] is False
        assert "absent" in result["msg"]

    def test_delete_by_token_id_unexpected_exception_propagates(self, adapter):
        """Unexpected exception from delete_by_id propagates (is not treated as NotFound)."""
        params = {"team_id": None, "token_id": "at-abc123", "check_mode": False}
        with patch(f"{MODULE_PATH}.get_team_token_by_id", return_value={"id": "at-abc123"}), patch(
            f"{MODULE_PATH}.delete_team_token_by_id", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError, match="boom"):
                state_absent(adapter, params, check_mode=False)

    def test_no_identifier_raises(self, adapter):
        """Neither team_id nor token_id → ValueError."""
        params = {"team_id": None, "token_id": None, "check_mode": False}
        with pytest.raises(ValueError, match="team_id"):
            state_absent(adapter, params, check_mode=False)


class TestMain:
    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_argument_spec(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": None,
            "expired_at": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=Exception("stop")):
            with pytest.raises(AssertionError):
                main()

        call_kwargs = mock_ansible_module.call_args[1]
        argument_spec = call_kwargs["argument_spec"]
        assert argument_spec["state"]["choices"] == ["present", "absent"]
        assert argument_spec["team_id"]["type"] == "str"
        assert argument_spec["token_id"]["type"] == "str"
        assert call_kwargs["supports_check_mode"] is True
        assert ("team_id", "token_id") in call_kwargs["mutually_exclusive"]
        # required_if: state=present requires team_id
        assert ("state", "present", ("team_id",)) in call_kwargs["required_if"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_present_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": None,
            "expired_at": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", return_value={"changed": True, "id": "at-abc123"}) as mock_present:
            with pytest.raises(SystemExit):
                main()
        mock_present.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_dispatch(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": None,
            "expired_at": None,
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(
            f"{MODULE_PATH}.state_absent",
            return_value={"changed": True, "msg": "Team token at-abc123 has been deleted successfully"},
        ) as mock_absent:
            with pytest.raises(SystemExit):
                main()
        mock_absent.assert_called_once()
        assert mock_module.exit_args["changed"] is True

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_error_via_fail_json(self, mock_ansible_module, enhanced_dummy_module):
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": None,
            "expired_at": None,
            "state": "present",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with patch(f"{MODULE_PATH}.state_present", side_effect=RuntimeError("boom")):
            with pytest.raises(AssertionError):
                main()
        assert mock_module.failed is True
        assert "boom" in mock_module.fail_args["msg"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_rejects_description(self, mock_ansible_module, enhanced_dummy_module):
        """state=absent with description raises fail_json before dispatching."""
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": "bad",
            "expired_at": None,
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with pytest.raises(AssertionError):
            main()
        assert mock_module.failed is True
        assert "description" in mock_module.fail_args["msg"]
        assert "state=absent" in mock_module.fail_args["msg"]

    @patch(f"{MODULE_PATH}.AnsibleTerraformModule")
    def test_main_absent_rejects_expired_at(self, mock_ansible_module, enhanced_dummy_module):
        """state=absent with expired_at raises fail_json before dispatching."""
        mock_module = enhanced_dummy_module
        mock_module.params = {
            "team_id": "team-xyz789",
            "token_id": None,
            "description": None,
            "expired_at": "2027-12-31T00:00:00Z",
            "state": "absent",
        }
        mock_module.check_mode = False
        mock_ansible_module.return_value = mock_module

        with pytest.raises(AssertionError):
            main()
        assert mock_module.failed is True
        assert "expired_at" in mock_module.fail_args["msg"]
        assert "state=absent" in mock_module.fail_args["msg"]
