# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/policy_set_version.py."""

from unittest.mock import Mock, patch

import pytest

from ansible_collections.hashicorp.terraform.plugins.modules.policy_set_version import create_and_upload

MOD = "ansible_collections.hashicorp.terraform.plugins.modules.policy_set_version"


@pytest.fixture(autouse=True)
def no_sleep():
    with patch(f"{MOD}.time.sleep"):
        yield


class TestCreateAndUpload:
    @pytest.fixture
    def adapter(self):
        return Mock()

    def _params(self, **overrides):
        params = {"policy_set_id": "polset-1", "policy_files_path": "./policies", "poll_interval": 1, "poll_timeout": 5}
        params.update(overrides)
        return params

    def test_success_reaches_ready(self, adapter):
        created = {"id": "polsetver-1", "status": "pending"}
        polled = {"id": "polsetver-1", "status": "ready"}
        with patch(f"{MOD}.create_policy_set_version", return_value=created), patch(f"{MOD}.upload_policy_set_version") as mock_upload, patch(
            f"{MOD}.get_policy_set_version", return_value=polled
        ):
            result = create_and_upload(adapter, self._params())

        mock_upload.assert_called_once_with(adapter, "polsetver-1", "./policies")
        assert result["changed"] is True
        assert result["status"] == "ready"
        assert "msg" not in result

    def test_errored_status_still_reports_changed(self, adapter):
        created = {"id": "polsetver-1", "status": "pending"}
        polled = {"id": "polsetver-1", "status": "errored", "error": "bad policy"}
        with patch(f"{MOD}.create_policy_set_version", return_value=created), patch(f"{MOD}.upload_policy_set_version"), patch(
            f"{MOD}.get_policy_set_version", return_value=polled
        ):
            result = create_and_upload(adapter, self._params())

        assert result["changed"] is True
        assert result["status"] == "errored"

    def test_poll_timeout_reports_msg_not_failure(self, adapter):
        created = {"id": "polsetver-1", "status": "pending"}
        stuck = {"id": "polsetver-1", "status": "pending"}
        with patch(f"{MOD}.create_policy_set_version", return_value=created), patch(f"{MOD}.upload_policy_set_version"), patch(
            f"{MOD}.get_policy_set_version", return_value=stuck
        ):
            result = create_and_upload(adapter, self._params(poll_timeout=0))

        assert result["changed"] is True
        assert result["status"] == "pending"
        assert "did not reach a terminal status" in result["msg"]
