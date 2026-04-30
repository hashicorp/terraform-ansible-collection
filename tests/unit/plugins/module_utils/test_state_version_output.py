# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock, patch

import pytest
from pytfe.errors import NotFound

from ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output import (
    _format_output_data,
    get_output_by_name,
    get_specific_output,
    get_workspace_outputs,
    resolve_workspace_id,
)


class TestFormatOutputData:
    """Tests for _format_output_data helper."""

    def test_format_non_sensitive_output(self):
        raw_output = {
            "id": "wsout-123",
            "name": "environment",
            "value": "test",
            "sensitive": False,
            "type": "string",
            "detailed-type": "string",
        }

        result = _format_output_data(raw_output)

        assert result == {
            "id": "wsout-123",
            "name": "environment",
            "value": "test",
            "sensitive": False,
            "type": "string",
            "detailed_type": "string",
        }

    def test_format_sensitive_null_masks_value(self):
        raw_output = {
            "id": "wsout-456",
            "name": "sensitive_token",
            "value": None,
            "sensitive": True,
            "type": "string",
            "detailed-type": "string",
        }

        result = _format_output_data(raw_output)

        assert result["value"] == "<sensitive>"
        assert result["sensitive"] is True


class TestResolveWorkspaceId:
    """Tests for resolve_workspace_id."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    def test_resolve_with_direct_workspace_id(self, mock_adapter):
        assert resolve_workspace_id(mock_adapter, workspace_id="ws-direct") == "ws-direct"

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_with_workspace_and_org(self, mock_get_workspace, mock_adapter):
        mock_get_workspace.return_value = {"id": "ws-resolved"}

        result = resolve_workspace_id(mock_adapter, workspace="demo-workspace", organization="demo-org")

        assert result == "ws-resolved"
        mock_get_workspace.assert_called_once_with(mock_adapter, "demo-org", "demo-workspace")

    def test_resolve_missing_parameters(self, mock_adapter):
        with pytest.raises(ValueError, match="Either workspace_id or both workspace and organization must be provided"):
            resolve_workspace_id(mock_adapter)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_workspace_not_found(self, mock_get_workspace, mock_adapter):
        mock_get_workspace.return_value = {}

        with pytest.raises(ValueError, match="was not found"):
            resolve_workspace_id(mock_adapter, workspace="missing", organization="demo-org")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace")
    def test_resolve_workspace_missing_id(self, mock_get_workspace, mock_adapter):
        mock_get_workspace.return_value = {"name": "demo-workspace"}

        with pytest.raises(ValueError, match="Invalid workspace data"):
            resolve_workspace_id(mock_adapter, workspace="demo-workspace", organization="demo-org")


class TestGetSpecificOutput:
    """Tests for get_specific_output."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.format_response")
    def test_get_specific_output_non_sensitive(self, mock_format_response, mock_adapter):
        mock_response = Mock()
        mock_adapter.client.state_version_outputs.read.return_value = mock_response
        mock_format_response.return_value = {
            "id": "wsout-1",
            "name": "environment",
            "value": "test",
            "sensitive": False,
            "type": "string",
            "detailed-type": "string",
        }

        result = get_specific_output(mock_adapter, "wsout-1")

        assert result["id"] == "wsout-1"
        assert result["value"] == "test"
        assert result["sensitive"] is False
        mock_adapter.client.state_version_outputs.read.assert_called_once_with("wsout-1")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.format_response")
    def test_get_specific_output_sensitive_masked(self, mock_format_response, mock_adapter):
        mock_adapter.client.state_version_outputs.read.return_value = Mock()
        mock_format_response.return_value = {
            "id": "wsout-2",
            "name": "sensitive_token",
            "value": "secret-value",
            "sensitive": True,
            "type": "string",
            "detailed-type": "string",
        }

        result = get_specific_output(mock_adapter, "wsout-2", display_sensitive=False)

        assert result["value"] == "<sensitive>"
        assert result["sensitive"] is True

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.format_response")
    def test_get_specific_output_sensitive_displayed(self, mock_format_response, mock_adapter):
        mock_adapter.client.state_version_outputs.read.return_value = Mock()
        mock_format_response.return_value = {
            "id": "wsout-3",
            "name": "sensitive_token",
            "value": "secret-value",
            "sensitive": True,
            "type": "string",
            "detailed-type": "string",
        }

        result = get_specific_output(mock_adapter, "wsout-3", display_sensitive=True)

        assert result["value"] == "secret-value"

    def test_get_specific_output_not_found(self, mock_adapter):
        mock_adapter.client.state_version_outputs.read.side_effect = NotFound("not found")

        with pytest.raises(ValueError, match="was not found"):
            get_specific_output(mock_adapter, "wsout-missing")


class TestGetWorkspaceOutputs:
    """Tests for get_workspace_outputs."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.format_response")
    def test_get_workspace_outputs_multiple(self, mock_format_response, mock_adapter):
        out_1 = Mock()
        out_2 = Mock()
        mock_adapter.client.state_version_outputs.read_current.return_value = [out_1, out_2]
        mock_format_response.side_effect = [
            {
                "id": "wsout-1",
                "name": "environment",
                "value": "test",
                "sensitive": False,
                "type": "string",
                "detailed-type": "string",
            },
            {
                "id": "wsout-2",
                "name": "sensitive_token",
                "value": None,
                "sensitive": True,
                "type": "string",
                "detailed-type": "string",
            },
        ]

        result = get_workspace_outputs(mock_adapter, "ws-123")

        assert len(result) == 2
        assert result[0]["name"] == "environment"
        assert result[1]["value"] == "<sensitive>"
        mock_adapter.client.state_version_outputs.read_current.assert_called_once_with("ws-123")

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_specific_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.format_response")
    def test_get_workspace_outputs_display_sensitive(self, mock_format_response, mock_get_specific_output, mock_adapter):
        out_1 = Mock()
        out_2 = Mock()
        mock_adapter.client.state_version_outputs.read_current.return_value = [out_1, out_2]
        mock_format_response.side_effect = [
            {
                "id": "wsout-sensitive",
                "name": "sensitive_token",
                "value": None,
                "sensitive": True,
                "type": "string",
                "detailed-type": "string",
            },
            {
                "id": "wsout-plain",
                "name": "environment",
                "value": "test",
                "sensitive": False,
                "type": "string",
                "detailed-type": "string",
            },
        ]
        mock_get_specific_output.return_value = {
            "id": "wsout-sensitive",
            "name": "sensitive_token",
            "value": "real-secret",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }

        result = get_workspace_outputs(mock_adapter, "ws-123", display_sensitive=True)

        assert result[0]["value"] == "real-secret"
        assert result[1]["value"] == "test"
        mock_get_specific_output.assert_called_once_with(mock_adapter, "wsout-sensitive", display_sensitive=True)

    def test_get_workspace_outputs_empty(self, mock_adapter):
        mock_adapter.client.state_version_outputs.read_current.return_value = []

        assert get_workspace_outputs(mock_adapter, "ws-empty") == []

    def test_get_workspace_outputs_not_found(self, mock_adapter):
        mock_adapter.client.state_version_outputs.read_current.side_effect = NotFound("not found")

        with pytest.raises(ValueError, match="Workspace with ID 'ws-missing' was not found"):
            get_workspace_outputs(mock_adapter, "ws-missing")


class TestGetOutputByName:
    """Tests for get_output_by_name."""

    @pytest.fixture
    def mock_adapter(self):
        return Mock()

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace_outputs")
    def test_get_output_by_name_found(self, mock_get_workspace_outputs, mock_adapter):
        mock_get_workspace_outputs.return_value = [
            {
                "id": "wsout-1",
                "name": "environment",
                "value": "test",
                "sensitive": False,
                "type": "string",
                "detailed_type": "string",
            },
        ]

        result = get_output_by_name(mock_adapter, "ws-123", "environment")

        assert result["value"] == "test"
        mock_get_workspace_outputs.assert_called_once_with(mock_adapter, "ws-123", display_sensitive=False)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_specific_output")
    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace_outputs")
    def test_get_output_by_name_sensitive_display(self, mock_get_workspace_outputs, mock_get_specific_output, mock_adapter):
        mock_get_workspace_outputs.return_value = [
            {
                "id": "wsout-2",
                "name": "sensitive_token",
                "value": "<sensitive>",
                "sensitive": True,
                "type": "string",
                "detailed_type": "string",
            },
        ]
        mock_get_specific_output.return_value = {
            "id": "wsout-2",
            "name": "sensitive_token",
            "value": "real-secret",
            "sensitive": True,
            "type": "string",
            "detailed_type": "string",
        }

        result = get_output_by_name(mock_adapter, "ws-123", "sensitive_token", display_sensitive=True)

        assert result["value"] == "real-secret"
        mock_get_specific_output.assert_called_once_with(mock_adapter, "wsout-2", display_sensitive=True)

    @patch("ansible_collections.hashicorp.terraform.plugins.module_utils.state_version_output.get_workspace_outputs")
    def test_get_output_by_name_not_found(self, mock_get_workspace_outputs, mock_adapter):
        mock_get_workspace_outputs.return_value = [{"name": "other_output", "id": "wsout-9"}]

        with pytest.raises(ValueError, match="Output with name 'environment' not found"):
            get_output_by_name(mock_adapter, "ws-123", "environment")
