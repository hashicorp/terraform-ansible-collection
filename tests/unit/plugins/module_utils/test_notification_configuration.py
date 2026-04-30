# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/notification_configuration.py (pytfe adapter)."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.notification_configuration import (
    _build_create_options,
    _build_update_options,
    _notification_to_dict,
    create_notification_configuration,
    delete_notification_configuration,
    get_notification_configuration,
    get_notification_configuration_by_name,
    list_notification_configurations,
    update_notification_configuration,
)

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.notification_configuration"


def _fake_notification(**overrides):
    """Build a stand-in for pytfe's (non-pydantic) NotificationConfiguration."""
    nc = Mock(spec=[])  # spec=[] disables auto-attributes; only fields set below exist
    attrs = {
        "id": "nc-abc",
        "name": "ops",
        "destination_type": "generic",
        "enabled": True,
        "url": "https://hooks.example.com/x",
        "token": None,
        "triggers": [],
        "email_addresses": [],
        "created_at": None,
        "updated_at": None,
    }
    attrs.update(overrides)
    for k, v in attrs.items():
        setattr(nc, k, v)
    return nc


class TestNotificationToDict:
    """`_notification_to_dict` replaces `format_response` for the non-pydantic response."""

    def test_basic_fields(self):
        nc = _fake_notification(
            id="nc-1",
            name="ops",
            destination_type="generic",
            enabled=True,
            url="https://hooks.example.com/x",
        )
        result = _notification_to_dict(nc)
        assert result["id"] == "nc-1"
        assert result["name"] == "ops"
        assert result["destination_type"] == "generic"
        assert result["enabled"] is True
        assert result["url"] == "https://hooks.example.com/x"

    def test_triggers_are_unwrapped_from_enum(self):
        """Triggers come back from pytfe as enum members; wire format is the string value."""
        trigger = Mock()
        trigger.value = "run:needs_attention"
        nc = _fake_notification(triggers=[trigger])
        assert _notification_to_dict(nc)["triggers"] == ["run:needs_attention"]

    def test_triggers_pass_through_raw_strings(self):
        """Unknown triggers that stayed as strings must not crash."""
        nc = _fake_notification(triggers=["run:unknown-future-trigger"])
        assert _notification_to_dict(nc)["triggers"] == ["run:unknown-future-trigger"]

    def test_datetimes_are_isoformat(self):
        ts = datetime(2025, 7, 3, 8, 10, 20, tzinfo=timezone.utc)
        nc = _fake_notification(created_at=ts, updated_at=ts)
        result = _notification_to_dict(nc)
        assert result["created_at"] == ts.isoformat()
        assert result["updated_at"] == ts.isoformat()

    def test_empty_string_url_and_token_become_none(self):
        """pytfe initializes url/token to '' when absent; surface None to keep diffs clean."""
        nc = _fake_notification(url="", token="")
        result = _notification_to_dict(nc)
        assert result["url"] is None
        assert result["token"] is None


class TestBuildCreateOptions:
    """Options are constructed by direct instantiation to support both plain-class and pydantic pytfe."""

    @patch(f"{MODULE_PATH}.NotificationConfigurationCreateOptions")
    @patch(f"{MODULE_PATH}.NotificationDestinationType")
    @patch(f"{MODULE_PATH}.NotificationTriggerType")
    def test_translates_user_dict(self, mock_trigger, mock_dest, mock_opts):
        mock_dest.return_value = "dest-enum"
        mock_trigger.side_effect = lambda v: f"trigger[{v}]"

        _build_create_options(
            {
                "name": "ops",
                "destination_type": "generic",
                "enabled": True,
                "url": "https://x",
                "triggers": ["run:needs_attention", "run:errored"],
            }
        )

        mock_dest.assert_called_once_with("generic")
        assert mock_trigger.call_args_list[0].args == ("run:needs_attention",)
        assert mock_trigger.call_args_list[1].args == ("run:errored",)
        kwargs = mock_opts.call_args.kwargs
        assert kwargs["name"] == "ops"
        assert kwargs["destination_type"] == "dest-enum"
        assert kwargs["enabled"] is True
        assert kwargs["url"] == "https://x"
        assert kwargs["triggers"] == ["trigger[run:needs_attention]", "trigger[run:errored]"]
        assert kwargs["email_addresses"] == []


class TestBuildUpdateOptions:
    """Update options forward only user-supplied keys (PATCH semantics)."""

    @patch(f"{MODULE_PATH}.NotificationConfigurationUpdateOptions")
    def test_empty_dict_passes_no_kwargs(self, mock_opts):
        _build_update_options({})
        assert mock_opts.call_args.kwargs == {}

    @patch(f"{MODULE_PATH}.NotificationConfigurationUpdateOptions")
    @patch(f"{MODULE_PATH}.NotificationTriggerType")
    def test_forwards_only_present_keys(self, mock_trigger, mock_opts):
        mock_trigger.side_effect = lambda v: f"t[{v}]"
        _build_update_options({"enabled": False, "triggers": ["run:errored"]})
        kwargs = mock_opts.call_args.kwargs
        assert kwargs == {"enabled": False, "triggers": ["t[run:errored]"]}


class TestListNotifications:
    def test_list_serializes_each(self):
        adapter = Mock()
        adapter.client.notification_configurations.list.return_value = iter([_fake_notification(id="nc-1", name="a"), _fake_notification(id="nc-2", name="b")])
        result = list_notification_configurations(adapter, "ws-x")
        assert [r["id"] for r in result] == ["nc-1", "nc-2"]
        adapter.client.notification_configurations.list.assert_called_once_with("ws-x")

    def test_not_found_returns_empty(self):
        adapter = Mock()
        adapter.client.notification_configurations.list.side_effect = NotFound("nope")
        assert list_notification_configurations(adapter, "ws-x") == []


class TestGetNotification:
    def test_read_serializes(self):
        adapter = Mock()
        adapter.client.notification_configurations.read.return_value = _fake_notification(id="nc-1")
        result = get_notification_configuration(adapter, "nc-1")
        assert result["id"] == "nc-1"
        adapter.client.notification_configurations.read.assert_called_once_with("nc-1")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.notification_configurations.read.side_effect = NotFound("missing")
        assert get_notification_configuration(adapter, "nc-missing") is None

    def test_by_name_matches(self):
        adapter = Mock()
        adapter.client.notification_configurations.list.return_value = iter([_fake_notification(id="nc-1", name="a"), _fake_notification(id="nc-2", name="b")])
        result = get_notification_configuration_by_name(adapter, "ws-x", "b")
        assert result["id"] == "nc-2"

    def test_by_name_no_match(self):
        adapter = Mock()
        adapter.client.notification_configurations.list.return_value = iter([_fake_notification(name="a")])
        assert get_notification_configuration_by_name(adapter, "ws-x", "missing") is None


class TestCreateUpdateDelete:
    @patch(f"{MODULE_PATH}.safe_api_call")
    @patch(f"{MODULE_PATH}._build_create_options")
    def test_create_passes_options_to_sdk(self, mock_build, mock_safe):
        opts = Mock(name="create-opts")
        mock_build.return_value = opts
        mock_safe.return_value = _fake_notification(id="nc-new", name="ops")

        adapter = Mock()
        data = {"name": "ops", "destination_type": "generic", "url": "https://x"}
        result = create_notification_configuration(adapter, "ws-x", data)

        mock_build.assert_called_once_with(data)
        args, kwargs = mock_safe.call_args
        assert args[0] is adapter.client.notification_configurations.create
        assert args[1] == "ws-x"
        assert args[2] is opts
        assert "error_context" in kwargs
        assert result["id"] == "nc-new"

    @patch(f"{MODULE_PATH}.safe_api_call")
    @patch(f"{MODULE_PATH}._build_update_options")
    def test_update_passes_options_to_sdk(self, mock_build, mock_safe):
        opts = Mock(name="update-opts")
        mock_build.return_value = opts
        mock_safe.return_value = _fake_notification(id="nc-1", enabled=False)

        adapter = Mock()
        data = {"enabled": False}
        result = update_notification_configuration(adapter, "nc-1", data)

        mock_build.assert_called_once_with(data)
        args = mock_safe.call_args.args
        assert args[0] is adapter.client.notification_configurations.update
        assert args[1] == "nc-1"
        assert args[2] is opts
        assert result["enabled"] is False

    @patch(f"{MODULE_PATH}.safe_api_call")
    def test_delete_calls_sdk(self, mock_safe):
        adapter = Mock()
        delete_notification_configuration(adapter, "nc-1")
        args, kwargs = mock_safe.call_args
        assert args[0] is adapter.client.notification_configurations.delete
        assert args[1] == "nc-1"
        assert "error_context" in kwargs


class TestErrorPropagation:
    @patch(f"{MODULE_PATH}.safe_api_call", side_effect=RuntimeError("boom"))
    @patch(f"{MODULE_PATH}._build_create_options")
    def test_create_propagates(self, _build, _safe):
        with pytest.raises(RuntimeError, match="boom"):
            create_notification_configuration(Mock(), "ws-x", {"name": "ops"})
