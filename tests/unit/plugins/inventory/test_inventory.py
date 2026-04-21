# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin

from ansible_collections.hashicorp.terraform.plugins.inventory.inventory import InventoryModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
    TerraformTokenNotFoundError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs import OutputsSource, _collect_hosts_from_spec
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.search import SearchSource
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.statefile import (
    StatefileSource,
    _build_provider_configs,
    _get_tag_value,
    _parse_provider_name,
    _resolve_resource_preference,
    _should_include_resource,
    get_resource_hostname,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import (
    _resolve_single_preference,
    get_preferred_hostname,
    passes_filters,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.factory import SOURCES, get_source_backend

# ---------------------------------------------------------------------------
# Module-level patch target constants
# ---------------------------------------------------------------------------

_INV_MODULE = "ansible_collections.hashicorp.terraform.plugins.inventory.inventory"
_STATEFILE_SRC = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.statefile"
_OUTPUTS_SRC = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs"
_COMMON = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common"


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
        "search_child_modules": False,
        "provider_mapping": [],
        "hosts_from": None,
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


def _make_resource_state(resources):
    """Build a Terraform state dict with the given resources list."""
    return {"version": 4, "resources": resources, "outputs": {}}


def _aws_resource(name, instances, mode="managed", module=None):
    """Build a minimal aws_instance resource dict."""
    r = {
        "mode": mode,
        "type": "aws_instance",
        "name": name,
        "provider": 'provider["registry.terraform.io/hashicorp/aws"]',
        "instances": instances,
    }
    if module:
        r["module"] = module
    return r


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
            "web",
            "ws",
            {"env": "prod", "name": "web-1"},
            hostnames=[{"name": "name", "prefix": "env"}],
        )
        assert result == "prod_web-1"

    def test_dict_preference_with_custom_separator(self):
        result = get_preferred_hostname(
            "web",
            "ws",
            {"env": "prod", "name": "web-1"},
            hostnames=[{"name": "name", "prefix": "env", "separator": "-"}],
        )
        assert result == "prod-web-1"

    def test_dict_preference_missing_name_key_raises(self):
        with pytest.raises(TerraformError, match="'name' key must be defined"):
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
        assert (
            passes_filters(
                {"env": "prod", "region": "us-east"},
                [{"env": "prod", "region": "eu-west"}],
                [],
            )
            is False
        )

    def test_include_all_keys_matching(self):
        assert (
            passes_filters(
                {"env": "prod", "region": "us-east"},
                [{"env": "prod", "region": "us-east"}],
                [],
            )
            is True
        )

    def test_include_any_filter_matches(self):
        assert (
            passes_filters(
                {"env": "staging"},
                [{"env": "prod"}, {"env": "staging"}],
                [],
            )
            is True
        )


# ---------------------------------------------------------------------------
# _parse_provider_name (sources/statefile)
# ---------------------------------------------------------------------------


class TestParseProviderName:
    def test_root_module_provider_string(self):
        s = 'provider["registry.terraform.io/hashicorp/aws"]'
        assert _parse_provider_name(s) == "registry.terraform.io/hashicorp/aws"

    def test_child_module_provider_string(self):
        s = 'module.networking.provider["registry.terraform.io/hashicorp/azurerm"]'
        assert _parse_provider_name(s) == "registry.terraform.io/hashicorp/azurerm"

    def test_unrecognised_format_returns_none(self):
        assert _parse_provider_name("hashicorp/aws") is None

    def test_empty_string_returns_none(self):
        assert _parse_provider_name("") is None


# ---------------------------------------------------------------------------
# _build_provider_configs (sources/statefile)
# ---------------------------------------------------------------------------


class TestBuildProviderConfigs:
    def test_defaults_include_aws_azure_gcp(self):
        configs = _build_provider_configs([])
        assert "registry.terraform.io/hashicorp/aws" in configs
        assert "registry.terraform.io/hashicorp/azurerm" in configs
        assert "registry.terraform.io/hashicorp/google" in configs

    def test_custom_mapping_appended(self):
        configs = _build_provider_configs(
            [
                {"provider_name": "registry.terraform.io/digitalocean/digitalocean", "types": ["digitalocean_droplet"]},
            ]
        )
        assert "digitalocean_droplet" in configs["registry.terraform.io/digitalocean/digitalocean"]

    def test_custom_types_extend_existing_provider(self):
        configs = _build_provider_configs(
            [
                {"provider_name": "registry.terraform.io/hashicorp/aws", "types": ["aws_spot_instance_request"]},
            ]
        )
        assert "aws_instance" in configs["registry.terraform.io/hashicorp/aws"]
        assert "aws_spot_instance_request" in configs["registry.terraform.io/hashicorp/aws"]

    def test_no_duplicate_types(self):
        configs = _build_provider_configs(
            [
                {"provider_name": "registry.terraform.io/hashicorp/aws", "types": ["aws_instance"]},
            ]
        )
        assert configs["registry.terraform.io/hashicorp/aws"].count("aws_instance") == 1


# ---------------------------------------------------------------------------
# _should_include_resource (sources/statefile)
# ---------------------------------------------------------------------------


class TestShouldIncludeResource:
    _PROVIDER_CONFIGS = {
        "registry.terraform.io/hashicorp/aws": ["aws_instance"],
    }

    def _resource(self, mode="managed", rtype="aws_instance", provider="aws", module=None):
        r = {
            "mode": mode,
            "type": rtype,
            "provider": f'provider["registry.terraform.io/hashicorp/{provider}"]',
        }
        if module:
            r["module"] = module
        return r

    def test_managed_resource_in_configs_is_included(self):
        assert _should_include_resource(self._resource(), False, self._PROVIDER_CONFIGS) is True

    def test_data_source_excluded(self):
        assert _should_include_resource(self._resource(mode="data"), False, self._PROVIDER_CONFIGS) is False

    def test_child_module_excluded_by_default(self):
        r = self._resource(module="module.networking")
        assert _should_include_resource(r, False, self._PROVIDER_CONFIGS) is False

    def test_child_module_included_when_search_child_modules_true(self):
        r = self._resource(module="module.networking")
        assert _should_include_resource(r, True, self._PROVIDER_CONFIGS) is True

    def test_unknown_provider_excluded(self):
        r = self._resource(provider="unknown_vendor")
        assert _should_include_resource(r, False, self._PROVIDER_CONFIGS) is False

    def test_unknown_type_excluded(self):
        r = self._resource(rtype="aws_s3_bucket")
        assert _should_include_resource(r, False, self._PROVIDER_CONFIGS) is False


# ---------------------------------------------------------------------------
# _get_tag_value (sources/statefile)
# ---------------------------------------------------------------------------


class TestGetTagValue:
    def test_simple_tag_returns_value(self):
        attrs = {"tags": {"Name": "web-1"}}
        assert _get_tag_value(attrs, "Name") == "web-1"

    def test_missing_tag_returns_none(self):
        attrs = {"tags": {"Env": "prod"}}
        assert _get_tag_value(attrs, "Name") is None

    def test_tag_eq_spec_matching_returns_key_value(self):
        attrs = {"tags": {"Name": "web-1"}}
        assert _get_tag_value(attrs, "Name=web-1") == "Name_web-1"

    def test_tag_eq_spec_mismatch_returns_none(self):
        attrs = {"tags": {"Name": "web-2"}}
        assert _get_tag_value(attrs, "Name=web-1") is None

    def test_tags_not_dict_returns_none(self):
        attrs = {"tags": "a-string"}
        assert _get_tag_value(attrs, "Name") is None

    def test_no_tags_key_returns_none(self):
        assert _get_tag_value({}, "Name") is None


# ---------------------------------------------------------------------------
# _resolve_resource_preference (sources/statefile)
# ---------------------------------------------------------------------------


class TestResolveResourcePreference:
    def test_tag_prefix_resolves_from_tags(self):
        attrs = {"tags": {"Name": "web-1"}}
        assert _resolve_resource_preference(attrs, "tag:Name") == "web-1"

    def test_attribute_lookup_returns_value(self):
        attrs = {"public_ip": "1.2.3.4"}
        assert _resolve_resource_preference(attrs, "public_ip") == "1.2.3.4"

    def test_attribute_not_present_returns_literal(self):
        assert _resolve_resource_preference({}, "static-hostname") == "static-hostname"

    def test_blank_attribute_value_returns_none(self):
        assert _resolve_resource_preference({"public_dns": "  "}, "public_dns") is None

    def test_blank_preference_returns_none(self):
        assert _resolve_resource_preference({}, "   ") is None


# ---------------------------------------------------------------------------
# get_resource_hostname (sources/statefile)
# ---------------------------------------------------------------------------


class TestGetResourceHostname:
    def test_no_hostnames_default_fallback(self):
        assert get_resource_hostname("aws_instance", "web", {}) == "aws_instance_web"

    def test_no_hostnames_with_index_key(self):
        assert get_resource_hostname("aws_instance", "servers", {}, index_key=0) == "aws_instance_servers_0"

    def test_string_index_key(self):
        assert get_resource_hostname("aws_instance", "servers", {}, index_key="us-east") == "aws_instance_servers_us-east"

    def test_attribute_preference_resolved(self):
        attrs = {"public_dns": "ec2.example.com"}
        assert get_resource_hostname("aws_instance", "web", attrs, hostnames=["public_dns"]) == "ec2.example.com"

    def test_tag_preference_resolved(self):
        attrs = {"tags": {"Name": "web-1"}}
        assert get_resource_hostname("aws_instance", "web", attrs, hostnames=["tag:Name"]) == "web-1"

    def test_dict_preference_with_prefix(self):
        attrs = {"tags": {"Name": "web-1", "Env": "prod"}}
        result = get_resource_hostname(
            "aws_instance",
            "web",
            attrs,
            hostnames=[{"name": "tag:Name", "prefix": "tag:Env", "separator": "-"}],
        )
        assert result == "prod-web-1"

    def test_dict_preference_missing_name_raises(self):
        with pytest.raises(TerraformError, match="'name' key must be defined"):
            get_resource_hostname("aws_instance", "web", {}, hostnames=[{"prefix": "tag:Env"}])

    def test_all_preferences_empty_falls_back(self):
        # tag:Name misses, public_dns present but empty → both resolve to None → fallback
        result = get_resource_hostname("aws_instance", "web", {"public_dns": ""}, hostnames=["tag:Name", "public_dns"])
        assert result == "aws_instance_web"

    def test_first_non_empty_preference_wins(self):
        attrs = {"public_ip": "1.2.3.4", "name": "web-1"}
        result = get_resource_hostname("aws_instance", "web", attrs, hostnames=["name", "public_ip"])
        assert result == "web-1"


# ---------------------------------------------------------------------------
# StatefileSource — validate_options (sources/statefile)
# ---------------------------------------------------------------------------


class TestStatefileSourceValidateOptions:
    def test_workspace_id_alone_is_valid(self):
        StatefileSource.validate_options({"workspace_id": "ws-abc", "organization": None, "workspace": None})

    def test_org_and_workspace_is_valid(self):
        StatefileSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": "my-ws"})

    def test_missing_all_raises(self):
        with pytest.raises(TerraformError, match="workspace_id.*organization.*workspace"):
            StatefileSource.validate_options({"workspace_id": None, "organization": None, "workspace": None})

    def test_only_org_without_workspace_raises(self):
        with pytest.raises(TerraformError):
            StatefileSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": None})

    def test_only_workspace_without_org_raises(self):
        with pytest.raises(TerraformError):
            StatefileSource.validate_options({"workspace_id": None, "organization": None, "workspace": "my-ws"})


# ---------------------------------------------------------------------------
# StatefileSource — collect_hosts (sources/statefile)
# ---------------------------------------------------------------------------


class TestStatefileSourceCollectHosts:
    def _make_source(
        self,
        workspace_id=None,
        organization="my-org",
        workspace="my-ws",
        search_child_modules=False,
        provider_mapping=None,
        hostnames=None,
    ):
        options = {
            "workspace_id": workspace_id,
            "organization": organization,
            "workspace": workspace,
            "search_child_modules": search_child_modules,
            "provider_mapping": provider_mapping or [],
            "hostnames": hostnames or [],
        }
        return StatefileSource(Mock(), options)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_single_aws_instance_produces_one_record(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("web_server", [{"attributes": {"public_ip": "1.2.3.4", "env": "prod"}}]),
            ]
        )

        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0]["host_vars"] == {"public_ip": "1.2.3.4", "env": "prod"}
        assert records[0]["workspace_name"] == "my-ws"
        assert records[0]["output_name"] == "aws_instance_web_server"
        assert "resolved_hostname" in records[0]
        assert records[0]["resolved_hostname"] == "aws_instance_web_server"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_count_instances_produce_indexed_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "servers",
                    [
                        {"index_key": 0, "attributes": {"public_ip": "10.0.0.1"}},
                        {"index_key": 1, "attributes": {"public_ip": "10.0.0.2"}},
                    ],
                ),
            ]
        )

        records = self._make_source().collect_hosts()

        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["resolved_hostname"] == "aws_instance_servers_0"
        assert records[1]["index"] == 1
        assert records[1]["resolved_hostname"] == "aws_instance_servers_1"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_for_each_instances_produce_string_indexed_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "servers",
                    [
                        {"index_key": "us-east", "attributes": {"az": "us-east-1a"}},
                        {"index_key": "eu-west", "attributes": {"az": "eu-west-1a"}},
                    ],
                ),
            ]
        )

        records = self._make_source().collect_hosts()

        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"aws_instance_servers_us-east", "aws_instance_servers_eu-west"}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_data_source_resource_skipped(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("lookup", [{"attributes": {"id": "i-abc"}}], mode="data"),
            ]
        )

        records = self._make_source().collect_hosts()
        assert records == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_child_module_resource_skipped_by_default(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("child_srv", [{"attributes": {"public_ip": "10.1.0.1"}}], module="module.networking"),
            ]
        )

        records = self._make_source(search_child_modules=False).collect_hosts()
        assert records == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_child_module_resource_included_when_search_child_modules(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("child_srv", [{"attributes": {"public_ip": "10.1.0.1"}}], module="module.networking"),
            ]
        )

        records = self._make_source(search_child_modules=True).collect_hosts()
        assert len(records) == 1

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_unknown_provider_resource_skipped(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                {
                    "mode": "managed",
                    "type": "custom_vm",
                    "name": "srv",
                    "provider": 'provider["registry.terraform.io/unknown/unknown"]',
                    "instances": [{"attributes": {"ip": "1.2.3.4"}}],
                }
            ]
        )

        records = self._make_source().collect_hosts()
        assert records == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_empty_resources_returns_no_records(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state([])
        assert self._make_source().collect_hosts() == []

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_tag_based_hostname_resolution(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("web", [{"attributes": {"tags": {"Name": "web-1"}}}]),
            ]
        )

        records = self._make_source(hostnames=["tag:Name"]).collect_hosts()
        assert records[0]["resolved_hostname"] == "web-1"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_workspace_name_stored_on_record(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-xyz", "resolved-name")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("srv", [{"attributes": {"public_ip": "1.2.3.4"}}]),
            ]
        )

        records = self._make_source(workspace_id="ws-xyz").collect_hosts()
        assert records[0]["workspace_name"] == "resolved-name"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_custom_provider_mapping_includes_resource(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                {
                    "mode": "managed",
                    "type": "digitalocean_droplet",
                    "name": "web",
                    "provider": 'provider["registry.terraform.io/digitalocean/digitalocean"]',
                    "instances": [{"attributes": {"name": "droplet-1"}}],
                }
            ]
        )

        source = self._make_source(
            provider_mapping=[
                {"provider_name": "registry.terraform.io/digitalocean/digitalocean", "types": ["digitalocean_droplet"]},
            ]
        )
        records = source.collect_hosts()
        assert len(records) == 1


# ---------------------------------------------------------------------------
# OutputsSource — validate_options (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceValidateOptions:
    def test_workspace_id_alone_is_valid(self):
        OutputsSource.validate_options({"workspace_id": "ws-abc", "organization": None, "workspace": None})

    def test_org_and_workspace_is_valid(self):
        OutputsSource.validate_options({"workspace_id": None, "organization": "my-org", "workspace": "my-ws"})

    def test_missing_all_raises(self):
        with pytest.raises(TerraformError, match="workspace_id.*organization.*workspace"):
            OutputsSource.validate_options({"workspace_id": None, "organization": None, "workspace": None})

    def test_only_org_without_workspace_raises(self):
        with pytest.raises(TerraformError):
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
# _collect_hosts_from_spec — unit tests (sources/outputs)
# ---------------------------------------------------------------------------


class TestCollectHostsFromSpec:
    """Unit tests for _collect_hosts_from_spec covering all kind×element_type combos."""

    _WS = "my-ws"

    def _spec(self, **kwargs):
        return kwargs

    # ── scalar ────────────────────────────────────────────────────────────────

    def test_scalar_produces_one_record_with_value_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip", kind="scalar", element_type="string"),
            {"ip": "1.2.3.4"},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"]["value"] == "1.2.3.4"
        assert records[0]["index"] is None

    def test_scalar_with_use_as_sets_named_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip", kind="scalar", element_type="string", use_as="ansible_host"),
            {"ip": "1.2.3.4"},
            self._WS,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    # ── list × primitive ──────────────────────────────────────────────────────

    def test_list_string_produces_indexed_records(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", kind="list", element_type="string"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["host_vars"]["value"] == "1.2.3.4"
        assert records[1]["index"] == 1
        assert records[1]["host_vars"]["value"] == "5.6.7.8"

    def test_list_string_with_use_as_sets_named_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", kind="list", element_type="string", use_as="ansible_host"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"
        assert records[1]["host_vars"]["ansible_host"] == "5.6.7.8"

    def test_list_string_no_resolved_hostname_uses_index(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", kind="list", element_type="string"),
            {"ips": ["1.2.3.4"]},
            self._WS,
        )
        assert "resolved_hostname" not in records[0]

    # ── list × object ─────────────────────────────────────────────────────────

    def test_list_object_produces_indexed_records_with_dict_host_vars(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", kind="list", element_type="object"),
            {"hosts": [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["host_vars"] == {"ip": "1.2.3.4"}
        assert records[0]["index"] == 0

    def test_list_object_skips_non_dict_elements(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", kind="list", element_type="object"),
            {"hosts": [{"ip": "1.2.3.4"}, "not-a-dict"]},
            self._WS,
        )
        assert len(records) == 1

    # ── map × primitive ───────────────────────────────────────────────────────

    def test_map_string_key_becomes_resolved_hostname(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", kind="map", element_type="string"),
            {"host_map": {"web-1": "1.2.3.4", "web-2": "5.6.7.8"}},
            self._WS,
        )
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}

    def test_map_string_key_stored_as_key_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", kind="map", element_type="string"),
            {"host_map": {"web-1": "1.2.3.4"}},
            self._WS,
        )
        assert records[0]["host_vars"]["key"] == "web-1"
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_map_string_with_use_as_sets_named_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", kind="map", element_type="string", use_as="ansible_host"),
            {"host_map": {"web-1": "1.2.3.4"}},
            self._WS,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"

    # ── map × object ──────────────────────────────────────────────────────────

    def test_map_object_key_becomes_resolved_hostname(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", kind="map", element_type="object"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}, "web-2": {"ip": "5.6.7.8"}}},
            self._WS,
        )
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}

    def test_map_object_host_vars_include_key_variable(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", kind="map", element_type="object"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}}},
            self._WS,
        )
        assert records[0]["host_vars"]["key"] == "web-1"
        assert records[0]["host_vars"]["ip"] == "1.2.3.4"

    def test_map_object_skips_non_dict_values(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", kind="map", element_type="object"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}, "bad": "not-a-dict"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["resolved_hostname"] == "web-1"

    # ── object × object ───────────────────────────────────────────────────────

    def test_object_produces_single_record_with_dict_as_host_vars(self):
        records = _collect_hosts_from_spec(
            self._spec(output="single", kind="object", element_type="object"),
            {"single": {"ip": "1.2.3.4", "env": "prod"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"ip": "1.2.3.4", "env": "prod"}
        assert records[0]["index"] is None

    # ── edge cases ────────────────────────────────────────────────────────────

    def test_missing_output_name_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="nonexistent", kind="list", element_type="string"),
            {"other_output": ["1.2.3.4"]},
            self._WS,
        )
        assert records == []

    def test_list_kind_wrong_value_type_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", kind="list", element_type="string"),
            {"ips": "not-a-list"},
            self._WS,
        )
        assert records == []

    def test_map_kind_wrong_value_type_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", kind="map", element_type="object"),
            {"hosts": ["not", "a", "dict"]},
            self._WS,
        )
        assert records == []

    def test_workspace_name_set_on_all_records(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", kind="list", element_type="string"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            "custom-ws",
        )
        assert all(r["workspace_name"] == "custom-ws" for r in records)


# ---------------------------------------------------------------------------
# OutputsSource — hosts_from mode via collect_hosts (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceHostsFromMode:
    def _make_source(self, hosts_from):
        options = {
            "workspace_id": None,
            "organization": "my-org",
            "workspace": "my-ws",
            "hosts_from": hosts_from,
        }
        return OutputsSource(Mock(), options)

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_hosts_from_dict_normalized_to_list(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "instance_ips", "value": ["1.2.3.4", "5.6.7.8"]},
        ]
        records = self._make_source(hosts_from={"output": "instance_ips", "kind": "list", "element_type": "string", "use_as": "ansible_host"}).collect_hosts()
        assert len(records) == 2
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_hosts_from_list_of_specs_combined(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "web_ips", "value": ["1.2.3.4"]},
            {"name": "db_ips", "value": ["10.0.0.1"]},
        ]
        records = self._make_source(
            hosts_from=[
                {"output": "web_ips", "kind": "list", "element_type": "string", "use_as": "ansible_host"},
                {"output": "db_ips", "kind": "list", "element_type": "string", "use_as": "ansible_host"},
            ]
        ).collect_hosts()
        assert len(records) == 2

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_hosts_from_disables_auto_detection(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "structured", "value": {"ip": "1.2.3.4"}},  # would be auto-detected
            {"name": "ips", "value": ["5.6.7.8"]},  # hosts_from target
        ]
        records = self._make_source(hosts_from={"output": "ips", "kind": "list", "element_type": "string"}).collect_hosts()
        output_names = {r["output_name"] for r in records}
        assert output_names == {"ips"}
        assert "structured" not in output_names

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_map_object_resolved_hostname_set_directly(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ec2", "value": {"web-1": {"ip": "1.2.3.4"}, "web-2": {"ip": "5.6.7.8"}}},
        ]
        records = self._make_source(hosts_from={"output": "ec2", "kind": "map", "element_type": "object"}).collect_hosts()
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}


# ---------------------------------------------------------------------------
# SearchSource stub (sources/search)
# ---------------------------------------------------------------------------


class TestSearchSourceStub:
    def test_validate_options_raises_not_implemented(self):
        with pytest.raises(TerraformError, match="not yet implemented"):
            SearchSource.validate_options({})

    def test_collect_hosts_raises_not_implemented(self):
        with pytest.raises(TerraformError, match="not yet implemented"):
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
        with pytest.raises(TerraformError, match="Unknown source"):
            get_source_backend("nonexistent")

    def test_sources_registry_contains_all_backends(self):
        assert set(SOURCES.keys()) == {"statefile", "outputs", "search"}


# ---------------------------------------------------------------------------
# InventoryModule.parse — integration (source: statefile)
# ---------------------------------------------------------------------------


class TestInventoryModuleParseStatefile:
    """Integration tests for parse() with source=statefile (resource-based)."""

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_org_and_workspace_resolves_and_downloads(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state([])

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_resolve.assert_called_once()
        mock_download.assert_called_once()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_aws_instance_adds_one_host(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("web_server", [{"attributes": {"public_ip": "1.2.3.4", "env": "prod"}}]),
            ]
        )

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("aws_instance_web_server")
        plugin.inventory.set_variable.assert_any_call("aws_instance_web_server", "public_ip", "1.2.3.4")
        plugin.inventory.set_variable.assert_any_call("aws_instance_web_server", "env", "prod")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_count_instances_adds_indexed_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "servers",
                    [
                        {"index_key": 0, "attributes": {"public_ip": "10.0.0.1"}},
                        {"index_key": 1, "attributes": {"public_ip": "10.0.0.2"}},
                    ],
                ),
            ]
        )

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"aws_instance_servers_0", "aws_instance_servers_1"}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_data_source_skipped(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("lookup", [{"attributes": {"id": "ami-abc"}}], mode="data"),
            ]
        )

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_not_called()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_child_module_excluded_by_default(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("child_srv", [{"attributes": {"public_ip": "10.1.0.1"}}], module="module.networking"),
            ]
        )

        plugin = _make_plugin(_base_options(search_child_modules=False))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_not_called()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_child_module_included_with_search_child_modules(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("child_srv", [{"attributes": {"public_ip": "10.1.0.1"}}], module="module.networking"),
            ]
        )

        plugin = _make_plugin(_base_options(search_child_modules=True))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("aws_instance_child_srv")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_provider_mapping_enables_custom_resource(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        do_resource = {
            "mode": "managed",
            "type": "digitalocean_droplet",
            "name": "web",
            "provider": 'provider["registry.terraform.io/digitalocean/digitalocean"]',
            "instances": [{"attributes": {"name": "droplet-1"}}],
        }
        mock_download.return_value = _make_resource_state([do_resource])

        plugin = _make_plugin(
            _base_options(
                provider_mapping=[
                    {"provider_name": "registry.terraform.io/digitalocean/digitalocean", "types": ["digitalocean_droplet"]},
                ]
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("digitalocean_droplet_web")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_provider_mapping_absent_custom_resource_skipped(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        do_resource = {
            "mode": "managed",
            "type": "digitalocean_droplet",
            "name": "web",
            "provider": 'provider["registry.terraform.io/digitalocean/digitalocean"]',
            "instances": [{"attributes": {"name": "droplet-1"}}],
        }
        mock_download.return_value = _make_resource_state([do_resource])

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_not_called()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_attribute_hostname_preference(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("web_server", [{"attributes": {"public_ip": "1.2.3.4", "name": "web-1"}}]),
            ]
        )

        plugin = _make_plugin(_base_options(hostnames=["name"]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("web-1")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_tag_hostname_preference(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("web_server", [{"attributes": {"tags": {"Name": "web-1"}}}]),
            ]
        )

        plugin = _make_plugin(_base_options(hostnames=["tag:Name"]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("web-1")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_exclude_filter_removes_host(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("staging_srv", [{"attributes": {"env": "staging", "ip": "10.0.0.1"}}]),
                _aws_resource("prod_srv", [{"attributes": {"env": "prod", "ip": "10.0.0.2"}}]),
            ]
        )

        plugin = _make_plugin(_base_options(exclude_filters=[{"env": "staging"}]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 1
        plugin.inventory.add_host.assert_called_once_with("aws_instance_prod_srv")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_include_filter_restricts_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("staging_srv", [{"attributes": {"env": "staging"}}]),
                _aws_resource("prod_srv", [{"attributes": {"env": "prod"}}]),
            ]
        )

        plugin = _make_plugin(_base_options(include_filters=[{"env": "prod"}]))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 1
        plugin.inventory.add_host.assert_called_once_with("aws_instance_prod_srv")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_compose_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("server", [{"attributes": {"public_ip": "1.2.3.4"}}]),
            ]
        )

        plugin = _make_plugin(_base_options(compose={"ansible_host": "public_ip"}))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_set_composite_vars") as mock_set_composite:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_set_composite.assert_called_once_with(
            {"ansible_host": "public_ip"},
            {"public_ip": "1.2.3.4"},
            "aws_instance_server",
            strict=False,
        )

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_keyed_groups_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("server", [{"attributes": {"instance_state": "running"}}]),
            ]
        )
        keyed_groups = [{"key": "instance_state", "prefix": "state"}]

        plugin = _make_plugin(_base_options(keyed_groups=keyed_groups))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_add_host_to_keyed_groups") as mock_keyed:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_keyed.assert_called_once_with(keyed_groups, {"instance_state": "running"}, "aws_instance_server", strict=False)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_composed_groups_is_forwarded(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource("server", [{"attributes": {"env": "prod"}}]),
            ]
        )
        groups = {"production": "env == 'prod'"}

        plugin = _make_plugin(_base_options(groups=groups))
        with _parse_ctx(plugin):
            with patch.object(plugin, "_add_host_to_composed_groups") as mock_comp_groups:
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_comp_groups.assert_called_once_with(groups, {"env": "prod"}, "aws_instance_server", strict=False)

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_empty_resources_adds_no_hosts(self, mock_client_cls, mock_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state([])

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
        mock_fetch.side_effect = TerraformError("Failed to fetch workspace outputs: API failure")

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
