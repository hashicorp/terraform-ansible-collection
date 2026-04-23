# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest
from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tfe_policy_checks import LookupModule

MOD = "ansible_collections.hashicorp.terraform.plugins.lookup.tfe_policy_checks"


@pytest.fixture
def lookup_plugin():
    return LookupModule()


@pytest.fixture
def patched_client():
    with patch(f"{MOD}.TerraformClient") as mock_class:
        mock_client = Mock()
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_client
        ctx.__exit__.return_value = False
        mock_class.from_mapping.return_value = ctx
        yield mock_client, mock_class


CHECKS = [
    {"id": "polchk-1", "status": "passed"},
    {"id": "polchk-2", "status": "soft_failed"},
    {"id": "polchk-3", "status": "hard_failed"},
]


class TestTfePolicyChecksLookup:

    @patch(f"{MOD}.list_policy_checks")
    def test_list_by_run_id(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = list(CHECKS)
        result = lookup_plugin.run([], None, run_id="run-1")
        assert len(result) == 3

    @patch(f"{MOD}.list_policy_checks")
    def test_only_failures_filter(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = list(CHECKS)
        result = lookup_plugin.run([], None, run_id="run-1", only_failures=True)
        assert {c["id"] for c in result} == {"polchk-2", "polchk-3"}

    @patch(f"{MOD}.get_policy_check")
    def test_single_by_id(self, mock_get, patched_client, lookup_plugin):
        mock_get.return_value = {"id": "polchk-9", "status": "passed"}
        result = lookup_plugin.run([], None, policy_check_id="polchk-9")
        assert result == [{"id": "polchk-9", "status": "passed"}]

    @patch(f"{MOD}.get_policy_check")
    def test_single_not_found(self, mock_get, patched_client, lookup_plugin):
        mock_get.return_value = None
        with pytest.raises(AnsibleError, match="not found"):
            lookup_plugin.run([], None, policy_check_id="polchk-missing")

    def test_mutually_exclusive(self, patched_client, lookup_plugin):
        with pytest.raises(AnsibleError, match="mutually exclusive"):
            lookup_plugin.run([], None, run_id="run-1", policy_check_id="polchk-1")

    def test_missing_required(self, patched_client, lookup_plugin):
        with pytest.raises(AnsibleError, match="is required"):
            lookup_plugin.run([], None)

    @patch(f"{MOD}.list_policy_checks")
    def test_api_error_wrapped(self, mock_list, patched_client, lookup_plugin):
        mock_list.side_effect = RuntimeError("boom")
        with pytest.raises(AnsibleError, match="tfe_policy_checks lookup failed"):
            lookup_plugin.run([], None, run_id="run-1")
