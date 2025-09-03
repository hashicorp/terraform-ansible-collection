# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import Mock

import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.run import get_run


class TestGetRun:
    """Test cases for get_run function."""

    def test_get_run_raises_terraform_error_on_error_status(self):
        """Test get_run raises TerraformError for error status codes."""
        mock_tf_client = Mock()
        run_id = "run-abc123"

        response = {"status": 404}
        mock_tf_client.get.return_value = response

        run_resp = get_run(mock_tf_client, run_id=run_id)

        assert run_resp == {}

    @pytest.mark.parametrize(
        "response_data,expected_result",
        [
            (
                {"data": {"id": "run-123abc456def789", "type": "runs", "attributes": {"status": "pending", "plan-only": "False"}}, "status": 200},
                {"id": "run-123abc456def789", "type": "runs", "attributes": {"status": "pending", "plan-only": "False"}},
            ),
        ],
    )
    def test_get_run_response(self, response_data, expected_result):
        mock_tf_client = Mock()
        run_id = "run-123abc456def789"

        mock_tf_client.get.return_value = response_data
        result = get_run(mock_tf_client, run_id)
        assert result == expected_result

    def test_get_run_with_complex_data_structure(self):
        """Test get_run with complex nested data structure."""
        mock_tf_client = Mock()
        run_id = "run-123abc456def789"

        expected_response = {
            "data": {
                "id": run_id,
                "type": "runs",
                "attributes": {
                    "actions": {"is-cancelable": False, "is-confirmable": False, "is-discardable": False, "is-force-cancelable": False},
                    "auto-apply": False,
                    "canceled-at": None,
                    "created-at": "2025-07-30T11:35:47.183Z",
                    "has-changes": True,
                    "is-destroy": False,
                    "message": "test",
                    "plan-only": False,
                    "save-plan": False,
                    "source": "tfe-ui",
                    "status": "discarded",
                    "terraform-version": "1.10.5",
                    "updated-at": "2025-07-30T11:39:34.091Z",
                    "permissions": {
                        "can-apply": True,
                        "can-cancel": True,
                        "can-comment": True,
                        "can-discard": True,
                    },
                },
                "relationships": {
                    "workspace": {"data": {"id": "ws-123abc456def", "type": "workspaces"}},
                    "apply": {"data": {"id": "apply-123abc", "type": "applies"}, "links": {"related": "/api/v2/runs/run-123abc/apply"}},
                },
                "links": {"self": "/api/v2/runs/run-123abc456def789"},
            },
            "status": 200,
        }
        mock_tf_client.get.return_value = expected_response

        result = get_run(client=mock_tf_client, run_id=run_id)

        expected_result = expected_response["data"].copy()
        assert result == expected_result
