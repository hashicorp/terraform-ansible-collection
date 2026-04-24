# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from unittest.mock import MagicMock, Mock, patch

import pytest
from ansible.errors import AnsibleError

from ansible_collections.hashicorp.terraform.plugins.lookup.tfe_run_events import LookupModule

MOD = "ansible_collections.hashicorp.terraform.plugins.lookup.tfe_run_events"


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


EVENTS = [
    {"id": "ev-1", "action": "created", "created_at": "2026-01-01T00:00:00Z"},
    {"id": "ev-2", "action": "planned", "created_at": "2026-01-02T00:00:00Z"},
    {"id": "ev-3", "action": "applied", "created_at": "2026-01-03T00:00:00Z"},
]


class TestTfeRunEventsLookup:

    @patch(f"{MOD}.list_run_events")
    def test_lookup_all_events(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = list(EVENTS)
        result = lookup_plugin.run([], None, run_id="run-1")
        assert len(result) == 3

    @patch(f"{MOD}.list_run_events")
    def test_filter_by_action(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = list(EVENTS)
        result = lookup_plugin.run([], None, run_id="run-1", action="applied")
        assert len(result) == 1
        assert result[0]["id"] == "ev-3"

    @patch(f"{MOD}.list_run_events")
    def test_filter_by_since_until(self, mock_list, patched_client, lookup_plugin):
        mock_list.return_value = list(EVENTS)
        result = lookup_plugin.run([], None, run_id="run-1", since="2026-01-02T00:00:00Z", until="2026-01-02T23:59:59Z")
        assert [e["id"] for e in result] == ["ev-2"]

    def test_missing_run_id(self, patched_client, lookup_plugin):
        with pytest.raises(AnsibleError, match="run_id is required"):
            lookup_plugin.run([], None)

    @patch(f"{MOD}.list_run_events")
    def test_api_error_wrapped(self, mock_list, patched_client, lookup_plugin):
        mock_list.side_effect = RuntimeError("boom")
        with pytest.raises(AnsibleError, match="tfe_run_events lookup failed"):
            lookup_plugin.run([], None, run_id="run-1")
