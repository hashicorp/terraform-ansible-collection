# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin

from ansible_collections.hashicorp.terraform.plugins.inventory.inventory import InventoryModule
from ansible_collections.hashicorp.terraform.plugins.inventory.sources.outputs import OutputsSource
from ansible_collections.hashicorp.terraform.plugins.inventory.sources.search import SearchSource
from ansible_collections.hashicorp.terraform.plugins.inventory.sources.statefile import StatefileSource, _download_statefile
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.common import (
    _resolve_single_preference,
    get_preferred_hostname,
    passes_filters,
)
from ansible_collections.hashicorp.terraform.plugins.inventory.utils.factory import SOURCES, get_source_backend
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
    TerraformTokenNotFoundError,
)

# ---------------------------------------------------------------------------
# Module-level patch target constants
# ---------------------------------------------------------------------------

_INV_MODULE = "ansible_collections.hashicorp.terraform.plugins.inventory.inventory"
_STATEFILE_SRC = "ansible_collections.hashicorp.terraform.plugins.inventory.sources.statefile"
_OUTPUTS_SRC = "ansible_collections.hashicorp.terraform.plugins.inventory.sources.outputs"
_COMMON = "ansible_collections.hashicorp.terraform.plugins.inventory.utils.common"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(options: dict) -> InventoryModule:
    plugin = InventoryModule()
    plugin.inventory = Mock()
    loader = Mock()
    loader.get_basedir.return_value = "/"
    plugin.loader = loader
    plugin.templar = Mock()
    plugin.display = Mock()
    plugin._options = options
    return plugin


@contextmanager
def _parse_ctx(plugin):
    """Patch BaseInventoryPlugin.parse (Templar setup) and _read_config_data for tests."""
    with patch.object(plugin, "_read_config_data"):
        with patch.object(BaseInventoryPlugin, "parse", return_value=None):
            yield


def _base_options(**overrides) -> dict:
    defaults = {
        "tfe_token": "test-token",
        "tfe_address": "https://app.terraform.io",
        "organization": "my-org",
        "workspace": "my-ws",
        "workspace_id": None,
        "source": "statefile",
        "hostnames": [],
        "include_filters": [],
        "exclude_filters": [],
        "compose": {},
        "keyed_groups": [],
        "groups": {},
        "strict": False,
    }
    defaults.update(overrides)
    return defaults


def _make_state_json(outputs: dict) -> bytes:
    """Build a minimal Terraform state JSON blob with the given outputs dict."""
    return json.dumps({"version": 4, "outputs": outputs}).encode()


# ---------------------------------------------------------------------------
# verify_file
# ---------------------------------------------------------------------------


class TestVerifyFile:
    def test_inventory_yaml_accepted(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "my.inventory.yaml"
        f.touch()
        assert plugin.verify_file(str(f)) is True

    def test_inventory_yml_accepted(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "my.inventory.yml"
        f.touch()
        assert plugin.verify_file(str(f)) is True

    def test_terraform_inventory_yaml_accepted(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "terraform_inventory.yaml"
        f.touch()
        assert plugin.verify_file(str(f)) is True

    def test_terraform_inventory_yml_accepted(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "terraform_inventory.yml"
        f.touch()
        assert plugin.verify_file(str(f)) is True

    def test_terraform_state_yaml_rejected(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "terraform_state.yaml"
        f.touch()
        assert plugin.verify_file(str(f)) is False

    def test_generic_yaml_rejected(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "hosts.yaml"
        f.touch()
        assert plugin.verify_file(str(f)) is False

    def test_ini_rejected(self, tmp_path):
        plugin = InventoryModule()
        f = tmp_path / "inventory.ini"
        f.touch()
        assert plugin.verify_file(str(f)) is False

    def test_nonexistent_file_rejected(self, tmp_path):
        plugin = InventoryModule()
        assert plugin.verify_file(str(tmp_path / "inventory.yaml")) is False


# ---------------------------------------------------------------------------
# _resolve_single_preference (utils/common)
# ---------------------------------------------------------------------------


class TestResolveSinglePreference:
    def test_output_name_token_no_index(self):
        assert _resolve_single_preference("my_out", {}, "output_name") == "my_out"

    def test_output_name_token_with_index(self):
        assert _resolve_single_preference("my_out", {}, "output_name", index=2) == "my_out_2"

    def test_field_present_in_host_vars(self):
        assert _resolve_single_preference("out", {"public_ip": "1.2.3.4"}, "public_ip") == "1.2.3.4"

    def test_field_absent_treated_as_literal(self):
        assert _resolve_single_preference("out", {}, "literal-hostname") == "literal-hostname"

    def test_blank_field_value_returns_none(self):
        assert _resolve_single_preference("out", {"name": ""}, "name") is None

    def test_none_field_value_returns_none(self):
        assert _resolve_single_preference("out", {"name": None}, "name") is None

    def test_blank_preference_string_returns_none(self):
        assert _resolve_single_preference("out", {}, "   ") is None


# ---------------------------------------------------------------------------
# get_preferred_hostname (utils/common)
# ---------------------------------------------------------------------------


class TestGetPreferredHostname:
    def test_no_hostnames_default_fallback(self):
        assert get_preferred_hostname("web", "ws", {}) == "ws_web"

    def test_no_hostnames_with_index(self):
        assert get_preferred_hostname("servers", "ws", {}, index=3) == "ws_servers_3"

    def test_empty_hostnames_list_uses_fallback(self):
        assert get_preferred_hostname("web", "ws", {}, hostnames=[]) == "ws_web"

    def test_field_hostname(self):
        assert get_preferred_hostname("web", "ws", {"ip": "10.0.0.1"}, hostnames=["ip"]) == "10.0.0.1"

    def test_empty_field_value_falls_through_to_next_preference(self):
        result = get_preferred_hostname("web", "ws", {"name": "", "id": "host-1"}, hostnames=["name", "id"])
        assert result == "host-1"

    def test_output_name_preference(self):
        assert get_preferred_hostname("my_output", "ws", {}, hostnames=["output_name"]) == "my_output"

    def test_output_name_with_index(self):
        assert get_preferred_hostname("servers", "ws", {}, hostnames=["output_name"], index=1) == "servers_1"

    def test_dict_preference_name_only(self):
        assert get_preferred_hostname("web", "ws", {"id": "abc"}, hostnames=[{"name": "id"}]) == "abc"

    def test_dict_preference_with_prefix_default_sep(self):
        result = get_preferred_hostname(
            "web", "ws",
            {"env": "prod", "name": "web-1"},
            hostnames=[{"name": "name", "prefix": "env"}],
        )
        assert result == "prod_web-1"

    def test_dict_preference_with_custom_separator(self):
        result = get_preferred_hostname(
            "web", "ws",
            {"env": "prod", "name": "web-1"},
            hostnames=[{"name": "name", "prefix": "env", "separator": "-"}],
        )
        assert result == "prod-web-1"

    def test_dict_preference_missing_name_key_raises(self):
        with pytest.raises(AnsibleError, match="'name' key must be defined"):
            get_preferred_hostname("web", "ws", {}, hostnames=[{"prefix": "env"}])

    def test_unresolvable_preferences_use_fallback(self):
        assert get_preferred_hostname("web", "ws", {}, hostnames=["output_name"]) == "web"

    def test_literal_string_used_as_hostname(self):
        assert get_preferred_hostname("web", "ws", {}, hostnames=["static-host"]) == "static-host"


# ---------------------------------------------------------------------------
# passes_filters (utils/common)
# ---------------------------------------------------------------------------


class TestPassesFilters:
    def test_no_filters_always_passes(self):
        assert passes_filters({"env": "prod"}, [], []) is True

    def test_none_filters_always_passes(self):
        assert passes_filters({"env": "prod"}, None, None) is True

    def test_include_filter_matching(self):
        assert passes_filters({"env": "prod"}, [{"env": "prod"}], []) is True

    def test_include_filter_not_matching(self):
        assert passes_filters({"env": "staging"}, [{"env": "prod"}], []) is False

    def test_exclude_filter_matching(self):
        assert passes_filters({"env": "staging"}, [], [{"env": "staging"}]) is False

    def test_exclude_filter_not_matching(self):
        assert passes_filters({"env": "prod"}, [], [{"env": "staging"}]) is True

    def test_exclude_takes_priority_over_include(self):
        assert passes_filters({"env": "prod"}, [{"env": "prod"}], [{"env": "prod"}]) is False

    def test_include_requires_all_keys_in_a_dict(self):
        assert passes_filters(
            {"env": "prod", "region": "us-east"},
            [{"env": "prod", "region": "eu-west"}],
            [],
        ) is False

    def test_include_all_keys_matching(self):
        assert passes_filters(
            {"env": "prod", "region": "us-east"},
            [{"env": "prod", "region": "us-east"}],
            [],
        ) is True

    def test_include_any_filter_matches(self):
        assert passes_filters(
            {"env": "staging"},
            [{"env": "prod"}, {"env": "staging"}],
            [],
        ) is True


# ---------------------------------------------------------------------------
# StatefileSource — validate_options (sources/statefile)
# ---------------------------------------------------------------------------


class TestStatefileSourceValidateOptions:
    def test_workspace_id_alone_is_valid(self):
        StatefileSource.validate_options({"workspace_id": "ws-abc", "organization": None, "workspace": None})

    def test_org_and_workspace_is_valid(self):
        StatefileSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": "my-ws"})

    def test_missing_all_raises(self):
        with pytest.raises(AnsibleParserError, match="workspace_id.*organization.*workspace"):
            StatefileSource.validate_options({"workspace_id": None, "organization": None, "workspace": None})

    def test_only_org_without_workspace_raises(self):
        with pytest.raises(AnsibleParserError):
            StatefileSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": None})

    def test_only_workspace_without_org_raises(self):
        with pytest.raises(AnsibleParserError):
            StatefileSource.validate_options({"workspace_id": None, "organization": None, "workspace": "my-ws"})


# ---------------------------------------------------------------------------
# StatefileSource — collect_hosts (sources/statefile)
# ---------------------------------------------------------------------------


class TestStatefileSourceCollectHosts:
    def _make_source(self, workspace_id=None, organization="my-org", workspace="my-ws"):
        options = {"workspace_id": workspace_id, "organization": organization, "workspace": workspace}
        return StatefileSource(Mock(), options)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_dict_output_produces_one_record(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "web_server": {"value": {"ip": "1.2.3.4", "env": "prod"}, "type": "object"},
            }
        }
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0] == {
            "output_name": "web_server",
            "workspace_name": "my-ws",
            "host_vars": {"ip": "1.2.3.4", "env": "prod"},
            "index": None,
        }

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_list_output_produces_indexed_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "servers": {"value": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]},
            }
        }
        records = self._make_source().collect_hosts()

        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["host_vars"] == {"ip": "10.0.0.1"}
        assert records[1]["index"] == 1
        assert records[1]["host_vars"] == {"ip": "10.0.0.2"}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_scalar_and_mixed_list_outputs_skipped(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "str_val": {"value": "a-string"},
                "num_val": {"value": 42},
                "mixed_list": {"value": ["a", {"k": "v"}]},
                "dict_val": {"value": {"ip": "1.2.3.4"}},
            }
        }
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0]["output_name"] == "dict_val"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_empty_outputs_section_returns_no_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {"outputs": {}}
        assert self._make_source().collect_hosts() == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_missing_outputs_key_returns_no_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {"version": 4}
        assert self._make_source().collect_hosts() == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_workspace_name_from_resolve_used_as_prefix(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-xyz", "resolved-name")
        mock_download.return_value = {
            "outputs": {"host": {"value": {"ip": "1.2.3.4"}}}
        }
        records = self._make_source(workspace_id="ws-xyz").collect_hosts()

        assert records[0]["workspace_name"] == "resolved-name"


# ---------------------------------------------------------------------------
# OutputsSource — validate_options (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceValidateOptions:
    def test_workspace_id_alone_is_valid(self):
        OutputsSource.validate_options({"workspace_id": "ws-abc", "organization": None, "workspace": None})

    def test_org_and_workspace_is_valid(self):
        OutputsSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": "my-ws"})

    def test_missing_all_raises(self):
        with pytest.raises(AnsibleParserError, match="workspace_id.*organization.*workspace"):
            OutputsSource.validate_options({"workspace_id": None, "organization": None, "workspace": None})

    def test_only_org_without_workspace_raises(self):
        with pytest.raises(AnsibleParserError):
            OutputsSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": None})


# ---------------------------------------------------------------------------
# OutputsSource — collect_hosts (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceCollectHosts:
    def _make_source(self, workspace_id=None, organization="my-org", workspace="my-ws"):
        options = {"workspace_id": workspace_id, "organization": organization, "workspace": workspace}
        return OutputsSource(Mock(), options)

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_dict_output_produces_one_record(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "web_server", "value": {"ip": "1.2.3.4", "env": "prod"}, "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0] == {
            "output_name": "web_server",
            "workspace_name": "my-ws",
            "host_vars": {"ip": "1.2.3.4", "env": "prod"},
            "index": None,
        }

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_list_output_produces_indexed_records(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "servers", "value": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}], "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[1]["index"] == 1

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_scalar_and_mixed_list_outputs_skipped(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "str_val", "value": "a-string", "sensitive": False},
            {"name": "num_val", "value": 42, "sensitive": False},
            {"name": "mixed_list", "value": ["a", {"k": "v"}], "sensitive": False},
            {"name": "dict_val", "value": {"ip": "1.2.3.4"}, "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0]["output_name"] == "dict_val"

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_empty_outputs_returns_no_records(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = []
        assert self._make_source().collect_hosts() == []


# ---------------------------------------------------------------------------
# SearchSource stub (sources/search)
# ---------------------------------------------------------------------------


class TestSearchSourceStub:
    def test_validate_options_raises_not_implemented(self):
        with pytest.raises(AnsibleParserError, match="not yet implemented"):
            SearchSource.validate_options({})

    def test_collect_hosts_raises_not_implemented(self):
        with pytest.raises(AnsibleParserError, match="not yet implemented"):
            SearchSource(Mock(), {}).collect_hosts()


# ---------------------------------------------------------------------------
# get_source_backend factory (utils/factory)
# ---------------------------------------------------------------------------


class TestGetSourceBackend:
    def test_statefile_returns_statefile_class(self):
        assert get_source_backend("statefile") is StatefileSource

    def test_outputs_returns_outputs_class(self):
        assert get_source_backend("outputs") is OutputsSource

    def test_search_returns_search_class(self):
        assert get_source_backend("search") is SearchSource

    def test_unknown_source_raises(self):
        with pytest.raises(AnsibleParserError, match="Unknown source"):
            get_source_backend("nonexistent")

    def test_sources_registry_contains_all_backends(self):
        assert set(SOURCES.keys()) == {"statefile", "outputs", "search"}


# ---------------------------------------------------------------------------
# InventoryModule.parse — integration (source: statefile)
# ---------------------------------------------------------------------------


class TestInventoryModuleParseStatefile:
    """Integration tests for parse() with source=statefile.

    Patches TerraformClient in the inventory module, resolve_workspace and
    _download_statefile in the statefile source module to avoid real I/O.
    """

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_org_and_workspace_resolves_and_downloads(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {"outputs": {}}

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_resolve.assert_called_once()
        mock_download.assert_called_once()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_dict_output_adds_one_host(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "web_server": {"value": {"public_ip": "1.2.3.4", "env": "prod"}},
            }
        }

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("my-ws_web_server")
        plugin.inventory.set_variable.assert_any_call("my-ws_web_server", "public_ip", "1.2.3.4")
        plugin.inventory.set_variable.assert_any_call("my-ws_web_server", "env", "prod")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_list_output_adds_indexed_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "servers": {"value": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]},
            }
        }

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"my-ws_servers_0", "my-ws_servers_1"}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_scalar_outputs_skipped(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "str_val": {"value": "just-a-string"},
                "num_val": {"value": 42},
                "mixed": {"value": ["a", {"k": "v"}]},
                "dict_val": {"value": {"ip": "1.2.3.4"}},
            }
        }

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 1
        plugin.inventory.add_host.assert_called_once_with("my-ws_dict_val")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostnames_field_preference(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {"web_server": {"value": {"public_ip": "1.2.3.4", "name": "web-1"}}}
        }

        plugin = _make_plugin(_base_options(hostnames=["name"]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("web-1")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_exclude_filter_removes_host(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "staging_srv": {"value": {"env": "staging", "ip": "10.0.0.1"}},
                "prod_srv": {"value": {"env": "prod", "ip": "10.0.0.2"}},
            }
        }

        plugin = _make_plugin(_base_options(exclude_filters=[{"env": "staging"}]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 1
        plugin.inventory.add_host.assert_called_once_with("my-ws_prod_srv")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_include_filter_restricts_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {
                "staging_srv": {"value": {"env": "staging"}},
                "prod_srv": {"value": {"env": "prod"}},
            }
        }

        plugin = _make_plugin(_base_options(include_filters=[{"env": "prod"}]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 1
        plugin.inventory.add_host.assert_called_once_with("my-ws_prod_srv")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_compose_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {"server": {"value": {"public_ip": "1.2.3.4"}}}
        }

        plugin = _make_plugin(_base_options(compose={"ansible_host": "public_ip"}))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_set_composite_vars") as mock_set_composite:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_set_composite.assert_called_once_with(
            {"ansible_host": "public_ip"},
            {"public_ip": "1.2.3.4"},
            "my-ws_server",
            strict=False,
        )

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_keyed_groups_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {"server": {"value": {"env": "prod"}}}
        }
        keyed_groups = [{"key": "env", "prefix": "env"}]

        plugin = _make_plugin(_base_options(keyed_groups=keyed_groups))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_add_host_to_keyed_groups") as mock_keyed:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_keyed.assert_called_once_with(keyed_groups, {"env": "prod"}, "my-ws_server", strict=False)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_composed_groups_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {
            "outputs": {"server": {"value": {"env": "prod"}}}
        }
        groups = {"production": "env == 'prod'"}

        plugin = _make_plugin(_base_options(groups=groups))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_add_host_to_composed_groups") as mock_comp_groups:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_comp_groups.assert_called_once_with(groups, {"env": "prod"}, "my-ws_server", strict=False)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_workspace_name_from_attributes_nested(self, mock_client_cls, mock_resolve, mock_download):
        """resolve_workspace returns nested attributes name → used as prefix."""
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "nested-ws")
        mock_download.return_value = {
            "outputs": {"host": {"value": {"ip": "1.2.3.4"}}}
        }

        plugin = _make_plugin(_base_options(organization=None, workspace=None, workspace_id="ws-abc"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("nested-ws_host")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_empty_state_adds_no_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = {"outputs": {}}

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_not_called()


# ---------------------------------------------------------------------------
# InventoryModule.parse — integration (source: outputs)
# ---------------------------------------------------------------------------


class TestInventoryModuleParseOutputs:
    """Integration tests for parse() with source=outputs."""

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_dict_output_adds_one_host(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "web_server", "value": {"public_ip": "1.2.3.4", "env": "prod"}, "sensitive": False},
        ]

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("my-ws_web_server")
        plugin.inventory.set_variable.assert_any_call("my-ws_web_server", "public_ip", "1.2.3.4")

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_list_output_adds_indexed_hosts(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "servers", "value": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}], "sensitive": False},
        ]

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"my-ws_servers_0", "my-ws_servers_1"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_terraform_error_from_fetch_outputs_raises_parser_error(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.side_effect = AnsibleParserError("Failed to fetch workspace outputs: API failure")

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="Failed to fetch"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_empty_outputs_adds_no_hosts(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = []

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_not_called()


# ---------------------------------------------------------------------------
# InventoryModule.parse — common error paths
# ---------------------------------------------------------------------------


class TestInventoryModuleParseErrors:
    def test_missing_workspace_raises(self):
        plugin = _make_plugin(_base_options(organization=None, workspace=None, workspace_id=None))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="workspace"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_missing_token_raises(self):
        plugin = _make_plugin(_base_options(tfe_token=""))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="token"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_token_not_found_error_wraps_as_parser_error(self, mock_client_cls):
        mock_client_cls.side_effect = TerraformTokenNotFoundError("no token")

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="Authentication"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_source_search_raises_not_implemented(self):
        plugin = _make_plugin(_base_options(source="search"))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="not yet implemented"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")
