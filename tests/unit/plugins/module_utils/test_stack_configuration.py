# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/stack_configuration.py (pytfe adapter)."""

from unittest.mock import Mock, patch

from pytfe.errors import NotFound
from pytfe.models.stack_configuration import StackConfigurationSource

from ansible_collections.hashicorp.terraform.plugins.module_utils.stack_configuration import (
    create_stack_configuration,
    get_stack_configuration,
)

MU_PATH = "ansible_collections.hashicorp.terraform.plugins.module_utils.stack_configuration"


def _make_model(payload):
    """Create a mock SDK model object whose model_dump returns payload."""
    m = Mock()
    m.model_dump.return_value = payload
    return m


class TestGetStackConfiguration:
    def test_success(self):
        adapter = Mock()
        adapter.client.stack_configurations.read.return_value = _make_model({"id": "stc-abc123", "status": "completed"})
        result = get_stack_configuration(adapter, "stc-abc123")
        assert result == {"id": "stc-abc123", "status": "completed"}
        adapter.client.stack_configurations.read.assert_called_once_with(stack_configuration_id="stc-abc123")

    def test_not_found_returns_none(self):
        adapter = Mock()
        adapter.client.stack_configurations.read.side_effect = NotFound("missing")
        result = get_stack_configuration(adapter, "stc-missing")
        assert result is None


class TestCreateStackConfiguration:
    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.StackConfigurationCreateOptions")
    def test_create_with_options_uses_sdk_model(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "stc-1", "status": "pending"})

        data = {"speculative_enabled": True, "destroy_all": False}
        result = create_stack_configuration(adapter, "st-xyz789", data)

        mock_opts_cls.model_validate.assert_called_once_with({"speculative_enabled": True, "destroy_all": False})
        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.stack_configurations.create
        assert args[1] == "st-xyz789"
        assert args[2] is opts
        assert args[3] == StackConfigurationSource.MANUAL
        assert "error_context" in kwargs
        assert result == {"id": "stc-1", "status": "pending"}

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.StackConfigurationCreateOptions")
    def test_create_with_fetch_source(self, mock_opts_cls, mock_safe_call):
        """source='fetch' is popped before model_validate; remaining data is empty → opts=None."""
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "stc-2", "status": "pending"})

        data = {"source": "fetch"}
        create_stack_configuration(adapter, "st-xyz789", data)

        # After popping 'source', data is empty → model_validate is NOT called; opts=None
        mock_opts_cls.model_validate.assert_not_called()
        args, kwargs = mock_safe_call.call_args
        assert args[1] == "st-xyz789"
        assert args[2] is None
        assert args[3] == StackConfigurationSource.FETCH

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.StackConfigurationCreateOptions")
    def test_create_with_reuse_source(self, mock_opts_cls, mock_safe_call):
        """source='reuse' is popped before model_validate; remaining data is empty → opts=None."""
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "stc-3"})

        data = {"source": "reuse"}
        create_stack_configuration(adapter, "st-xyz789", data)

        # After popping 'source', data is empty → model_validate is NOT called; opts=None
        mock_opts_cls.model_validate.assert_not_called()
        args, kwargs = mock_safe_call.call_args
        assert args[2] is None
        assert args[3] == StackConfigurationSource.REUSE

    @patch(f"{MU_PATH}.safe_api_call")
    def test_create_no_options_sends_none(self, mock_safe_call):
        adapter = Mock()
        mock_safe_call.return_value = _make_model({"id": "stc-4"})

        create_stack_configuration(adapter, "st-xyz789", {})

        args, kwargs = mock_safe_call.call_args
        assert args[0] is adapter.client.stack_configurations.create
        assert args[1] == "st-xyz789"
        assert args[2] is None
        assert args[3] == StackConfigurationSource.MANUAL
        assert "error_context" in kwargs

    @patch(f"{MU_PATH}.safe_api_call")
    @patch(f"{MU_PATH}.StackConfigurationCreateOptions")
    def test_create_with_selected_deployments(self, mock_opts_cls, mock_safe_call):
        adapter = Mock()
        opts = Mock()
        mock_opts_cls.model_validate.return_value = opts
        mock_safe_call.return_value = _make_model({"id": "stc-5"})

        data = {"selected_deployments": ["dep-a", "dep-b"]}
        create_stack_configuration(adapter, "st-xyz789", data)

        mock_opts_cls.model_validate.assert_called_once_with({"selected_deployments": ["dep-a", "dep-b"]})
