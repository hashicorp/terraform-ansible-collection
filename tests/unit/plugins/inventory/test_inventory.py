# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import re
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin

from ansible_collections.hashicorp.terraform.plugins.inventory.tfc_inv import InventoryModule
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
    TerraformTokenNotFoundError,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs import OutputsSource, _collect_hosts_from_spec, parse_type
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.statefile import (
    StatefileSource,
    _build_provider_configs,
    _get_tag_value,
    _parse_provider_name,
    _resolve_resource_preference,
    _sanitize_sensitive_attributes,
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

_INV_MODULE = "ansible_collections.hashicorp.terraform.plugins.inventory.tfc_inv"
_STATEFILE_SRC = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.statefile"
_OUTPUTS_SRC = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs"
_COMMON = "ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(options: dict) -> InventoryModule:
    plugin = InventoryModule()
    # The plugin loader normally sets ``_load_name`` after instantiation; set it
    # here so option lookups that fall through to Ansible config raise a clear
    # config error instead of ``AttributeError`` under plain ``pytest``.
    plugin._load_name = "hashicorp.terraform.tfc_inv"
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
        "hostvars_prefix": "",
        "hostvars_suffix": "",
        # Multi-workspace + caching options. Seeded here so option lookups in
        # parse() resolve from _options directly instead of falling through to
        # Ansible config (which requires the full plugin loader).
        "workspace_filters": {},
        "enable_parallel_processing": False,
        "concurrency": 5,
        "cache": False,
        "cache_validate_current_state_version": False,
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

    def test_field_absent_returns_none(self):
        # Plain strings are NOT treated as literal hostnames — unresolved
        # preferences return None so the caller can try the next preference
        # or fall back to the default. This prevents hostname collisions
        # silently collapsing multi-host inventories into a single literal-
        # named host (the bug from the original spread-vs-nest debate).
        assert _resolve_single_preference("out", {}, "literal-hostname") is None

    def test_blank_field_value_returns_none(self):
        assert _resolve_single_preference("out", {"name": ""}, "name") is None

    def test_none_field_value_returns_none(self):
        assert _resolve_single_preference("out", {"name": None}, "name") is None

    def test_blank_preference_string_returns_none(self):
        assert _resolve_single_preference("out", {}, "   ") is None

    def test_dotted_path_walks_nested_dict(self):
        # Dotted paths read into nested user-data dicts (e.g. a Terraform
        # output object that contains a `tags` dict).
        host_vars = {"name": "web-1", "tags": {"role": "api", "env": "prod"}}
        assert _resolve_single_preference("out", host_vars, "name") == "web-1"
        assert _resolve_single_preference("out", host_vars, "tags.role") == "api"

    def test_dotted_path_missing_intermediate_key_returns_none(self):
        assert _resolve_single_preference("out", {"tags": {}}, "tags.missing") is None

    def test_dotted_path_into_non_dict_returns_none(self):
        assert _resolve_single_preference("out", {"tags": "primitive"}, "tags.role") is None


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

    def test_unresolved_preference_falls_back_to_default(self):
        # Plain strings are NOT treated as literal hostnames; an unresolved
        # preference falls through to the workspace+output[_index] default.
        # Set a static hostname via `compose: {ansible_host: "static"}` if
        # that's what you want.
        assert get_preferred_hostname("web", "ws", {}, hostnames=["static-host"]) == "ws_web"


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

    def test_dotted_filter_key_walks_nested_dict(self):
        # Filters work against the nested user payload via dotted keys.
        host_vars = {"item": {"role": "web", "tags": {"env": "prod"}}}
        assert passes_filters(host_vars, [{"item.role": "web"}], []) is True
        assert passes_filters(host_vars, [{"item.tags.env": "prod"}], []) is True
        assert passes_filters(host_vars, [{"item.role": "db"}], []) is False

    def test_dotted_filter_with_missing_path_does_not_match(self):
        host_vars = {"item": {"role": "web"}}
        assert passes_filters(host_vars, [{"item.missing": "anything"}], []) is False


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

    def test_attribute_not_present_returns_none(self):
        # Plain strings are NOT treated as literal hostnames — an unresolved
        # preference falls through (and ultimately to the resource-name
        # default) instead of silently collapsing multi-host inventories
        # into a single literal-named host.  Mirrors outputs source.
        assert _resolve_resource_preference({}, "static-hostname") is None

    def test_blank_attribute_value_returns_none(self):
        assert _resolve_resource_preference({"public_dns": "  "}, "public_dns") is None

    def test_blank_preference_returns_none(self):
        assert _resolve_resource_preference({}, "   ") is None

    def test_attribute_dropped_as_sensitive_returns_none(self):
        # When sanitization removed an attribute referenced by a hostname
        # preference, resolution must return None (so the next preference or
        # the resource-name fallback is used) — never a literal that could
        # collapse multiple hosts to the same name.
        attrs = {"public_ip": "1.2.3.4"}  # 'private_dns' was sanitized out
        assert _resolve_resource_preference(attrs, "private_dns") is None


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
# _sanitize_sensitive_attributes (sources/statefile)
# ---------------------------------------------------------------------------


class TestSanitizeSensitiveAttributes:
    def test_top_level_sensitive_attr_removed(self):
        attrs = {"public_ip": "1.2.3.4", "password": "secret"}
        paths = [[{"type": "get_attr", "value": "password"}]]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_multiple_sensitive_attrs_removed(self):
        attrs = {"public_ip": "1.2.3.4", "password": "secret", "token": "abc"}
        paths = [
            [{"type": "get_attr", "value": "password"}],
            [{"type": "get_attr", "value": "token"}],
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_nested_dict_path_removed(self):
        attrs = {"config": {"username": "admin", "password": "secret"}}
        paths = [
            [
                {"type": "get_attr", "value": "config"},
                {"type": "get_attr", "value": "password"},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"config": {"username": "admin"}}

    def test_nested_list_index_drops_top_level_list(self):
        attrs = {"items": [{"k": "keep"}, {"k": "drop"}], "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "items"},
                {"type": "index", "value": 1},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_multiple_sensitive_list_indices_in_same_list_no_leak(self):
        attrs = {"secrets": ["first", "second", "public"], "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "secrets"},
                {"type": "index", "value": 0},
            ],
            [
                {"type": "get_attr", "value": "secrets"},
                {"type": "index", "value": 1},
            ],
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_nested_map_string_index_removed(self):
        attrs = {"creds": {"prod": "secret", "dev": "ok"}}
        paths = [
            [
                {"type": "get_attr", "value": "creds"},
                {"type": "index", "value": "prod"},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"creds": {"dev": "ok"}}

    def test_unknown_traversal_falls_back_to_top_level(self):
        attrs = {"creds": {"username": "admin", "password": "secret"}, "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "creds"},
                {"type": "mystery", "value": "password"},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_missing_intermediate_key_falls_back_to_top_level(self):
        attrs = {"config": {"username": "admin"}, "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "config"},
                {"type": "get_attr", "value": "missing_branch"},
                {"type": "get_attr", "value": "password"},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_empty_sensitive_attributes_leaves_hostvars_unchanged(self):
        attrs = {"public_ip": "1.2.3.4", "env": "prod"}
        result = _sanitize_sensitive_attributes(attrs, [])
        assert result == attrs

    def test_empty_path_entry_ignored(self):
        attrs = {"public_ip": "1.2.3.4"}
        result = _sanitize_sensitive_attributes(attrs, [[]])
        assert result == attrs

    def test_malformed_first_step_with_no_attribute_reference_ignored(self):
        attrs = {"public_ip": "1.2.3.4"}
        paths = [[{"type": "index", "value": 0}]]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == attrs

    def test_does_not_mutate_input_attributes(self):
        attrs = {"password": "secret", "public_ip": "1.2.3.4"}
        paths = [[{"type": "get_attr", "value": "password"}]]
        _sanitize_sensitive_attributes(attrs, paths)
        assert attrs == {"password": "secret", "public_ip": "1.2.3.4"}

    def test_top_level_attr_already_absent_is_silent(self):
        attrs = {"public_ip": "1.2.3.4"}
        paths = [[{"type": "get_attr", "value": "password"}]]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_unhashable_get_attr_value_does_not_crash(self):
        # A malformed sensitive path with an unhashable value must not raise
        # TypeError from `value in parent` — it should fall through safely.
        attrs = {"public_ip": "1.2.3.4"}
        paths = [[{"type": "get_attr", "value": []}]]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_unhashable_index_value_does_not_crash(self):
        attrs = {"creds": {"a": 1, "b": 2}, "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "creds"},
                {"type": "index", "value": {}},
            ]
        ]
        # Falls back to deleting top-level 'creds'.
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}

    def test_unhashable_walking_step_does_not_crash(self):
        # Unhashable get_attr in an intermediate walking step also short-circuits
        # to top-level fallback rather than crashing.
        attrs = {"creds": {"nested": {"x": 1}}, "public_ip": "1.2.3.4"}
        paths = [
            [
                {"type": "get_attr", "value": "creds"},
                {"type": "get_attr", "value": []},
                {"type": "get_attr", "value": "x"},
            ]
        ]
        result = _sanitize_sensitive_attributes(attrs, paths)
        assert result == {"public_ip": "1.2.3.4"}


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

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_sensitive_attributes_dropped_from_host_vars(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "web",
                    [
                        {
                            "attributes": {
                                "public_ip": "1.2.3.4",
                                "password": "supersecret",
                                "config": {"username": "admin", "token": "tok"},
                            },
                            "sensitive_attributes": [
                                [{"type": "get_attr", "value": "password"}],
                                [
                                    {"type": "get_attr", "value": "config"},
                                    {"type": "get_attr", "value": "token"},
                                ],
                            ],
                        }
                    ],
                ),
            ]
        )

        records = self._make_source().collect_hosts()

        assert len(records) == 1
        host_vars = records[0]["host_vars"]
        assert "password" not in host_vars
        assert host_vars["config"] == {"username": "admin"}
        # Non-sensitive attributes remain available.
        assert host_vars["public_ip"] == "1.2.3.4"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_sensitive_list_indices_drop_entire_list_from_host_vars(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "web",
                    [
                        {
                            "attributes": {
                                "public_ip": "1.2.3.4",
                                "secrets": ["first-secret", "second-secret", "public-ish"],
                            },
                            "sensitive_attributes": [
                                [
                                    {"type": "get_attr", "value": "secrets"},
                                    {"type": "index", "value": 0},
                                ],
                                [
                                    {"type": "get_attr", "value": "secrets"},
                                    {"type": "index", "value": 1},
                                ],
                            ],
                        }
                    ],
                ),
            ]
        )

        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0]["host_vars"] == {"public_ip": "1.2.3.4"}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_sensitive_attribute_value_never_emitted_via_hostname(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "web",
                    [
                        {
                            "attributes": {"public_ip": "1.2.3.4", "private_dns": "internal.example"},
                            "sensitive_attributes": [
                                [{"type": "get_attr", "value": "private_dns"}],
                            ],
                        }
                    ],
                ),
            ]
        )

        records = self._make_source(hostnames=["private_dns"]).collect_hosts()
        # Sensitive value must never appear in inventory output, regardless of
        # how hostname preferences degrade when the attribute is gone.
        assert records[0]["resolved_hostname"] != "internal.example"
        assert "private_dns" not in records[0]["host_vars"]
        assert records[0]["host_vars"]["public_ip"] == "1.2.3.4"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_no_sensitive_attributes_preserves_all_host_vars(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "web",
                    [{"attributes": {"public_ip": "1.2.3.4", "env": "prod"}}],
                ),
            ]
        )

        records = self._make_source(hostnames=["public_ip"]).collect_hosts()
        assert records[0]["host_vars"] == {"public_ip": "1.2.3.4", "env": "prod"}
        assert records[0]["resolved_hostname"] == "1.2.3.4"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_sanitized_hostname_does_not_collapse_multi_host_inventory(self, mock_resolve, mock_download):
        # Two distinct instances both have private_dns marked sensitive.  Each
        # must fall back to a unique resource-name-based default rather than
        # all collapsing to the literal preference string.
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "servers",
                    [
                        {
                            "index_key": 0,
                            "attributes": {"public_ip": "10.0.0.1", "private_dns": "host-a.internal"},
                            "sensitive_attributes": [[{"type": "get_attr", "value": "private_dns"}]],
                        },
                        {
                            "index_key": 1,
                            "attributes": {"public_ip": "10.0.0.2", "private_dns": "host-b.internal"},
                            "sensitive_attributes": [[{"type": "get_attr", "value": "private_dns"}]],
                        },
                    ],
                ),
            ]
        )

        records = self._make_source(hostnames=["private_dns"]).collect_hosts()
        names = [r["resolved_hostname"] for r in records]
        assert names == ["aws_instance_servers_0", "aws_instance_servers_1"]
        for r in records:
            assert "private_dns" not in r["host_vars"]

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_child_module_sensitive_attributes_also_sanitized(self, mock_resolve, mock_download):
        # search_child_modules=True must not bypass sanitization for resources
        # discovered inside a child module.
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "child_srv",
                    [
                        {
                            "attributes": {"public_ip": "10.1.0.1", "password": "topsecret"},
                            "sensitive_attributes": [[{"type": "get_attr", "value": "password"}]],
                        }
                    ],
                    module="module.networking",
                ),
            ]
        )

        records = self._make_source(search_child_modules=True).collect_hosts()
        assert len(records) == 1
        assert "password" not in records[0]["host_vars"]
        assert records[0]["host_vars"]["public_ip"] == "10.1.0.1"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    def test_malformed_sensitive_path_drops_top_level_attr(self, mock_resolve, mock_download):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = _make_resource_state(
            [
                _aws_resource(
                    "web",
                    [
                        {
                            "attributes": {"creds": {"username": "admin", "password": "secret"}, "public_ip": "1.2.3.4"},
                            "sensitive_attributes": [
                                [
                                    {"type": "get_attr", "value": "creds"},
                                    {"type": "unknown", "value": "password"},
                                ],
                            ],
                        }
                    ],
                ),
            ]
        )

        records = self._make_source().collect_hosts()
        host_vars = records[0]["host_vars"]
        assert "creds" not in host_vars
        assert host_vars["public_ip"] == "1.2.3.4"


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

    def test_hosts_from_without_type_defaults_to_dynamic_and_is_valid(self):
        OutputsSource.validate_options({"workspace_id": "ws-abc", "hosts_from": {"output": "my_hosts"}})

    def test_hosts_from_with_explicit_dynamic_type_is_valid(self):
        OutputsSource.validate_options({"workspace_id": "ws-abc", "hosts_from": {"output": "my_hosts", "type": "dynamic"}})


# ---------------------------------------------------------------------------
# OutputsSource — collect_hosts (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceCollectHosts:
    def _make_source(self, workspace_id=None, organization="my-org", workspace="my-ws"):
        options = {"workspace_id": workspace_id, "organization": organization, "workspace": workspace}
        return OutputsSource(Mock(), options)

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_unrelated_dict_output_ignored_without_hosts_from(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "web_server", "value": {"ip": "1.2.3.4", "env": "prod"}, "sensitive": False},
            {"name": "servers", "value": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}], "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert records == []

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_default_ansible_host_object_output_produces_one_record(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": {"ip": "1.2.3.4", "metadata": {"env": "prod"}}, "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0] == {
            "output_name": "ansible_host",
            "workspace_name": "my-ws",
            "host_vars": {"ip": "1.2.3.4", "metadata": {"env": "prod"}},
            "index": None,
            "workspace_id": "ws-abc",
        }

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_default_ansible_host_scalar_output_produces_one_record(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": "1.2.3.4", "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 1
        assert records[0]["output_name"] == "ansible_host"
        assert records[0]["host_vars"] == {"value": "1.2.3.4", "ansible_host": "1.2.3.4"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_default_ansible_host_list_string_output_produces_indexed_records(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": ["10.0.0.1", "10.0.0.2"], "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["host_vars"] == {"value": "10.0.0.1", "ansible_host": "10.0.0.1"}
        assert records[1]["index"] == 1
        assert records[1]["host_vars"] == {"value": "10.0.0.2", "ansible_host": "10.0.0.2"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_default_ansible_host_map_string_output_uses_map_keys_as_hostnames(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": {"web1": "10.0.0.1", "web2": "10.0.0.2"}, "sensitive": False},
        ]
        records = self._make_source().collect_hosts()

        assert len(records) == 2
        assert records[0]["resolved_hostname"] == "web1"
        assert records[0]["host_vars"] == {"value": "10.0.0.1", "ansible_host": "10.0.0.1"}
        assert records[1]["resolved_hostname"] == "web2"
        assert records[1]["host_vars"] == {"value": "10.0.0.2", "ansible_host": "10.0.0.2"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_empty_outputs_returns_no_records(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = []
        assert self._make_source().collect_hosts() == []


# ---------------------------------------------------------------------------
# parse_type — type expression parser (sources/outputs)
# ---------------------------------------------------------------------------


class TestParseType:
    """Verify each supported Terraform type expression maps to the right shape."""

    @pytest.mark.parametrize(
        "expr,shape",
        [
            # Special: dynamic (matches Terraform's plugin-framework dynamic type)
            ("dynamic", "dynamic"),
            # Primitives
            ("string", "primitive"),
            ("number", "primitive"),
            ("bool", "primitive"),
            # Structural: object (with and without schema body)
            ("object", "object"),
            ("object({})", "object"),
            ("object({name=string})", "object"),
            ("object({name=string, age=number, tags=map(string)})", "object"),
            # Structural: tuple (with and without element-types body) — routed through dynamic
            ("tuple", "dynamic"),
            ("tuple([])", "dynamic"),
            ("tuple([string])", "dynamic"),
            ("tuple([string, number, bool])", "dynamic"),
            ("tuple([string, object])", "dynamic"),
            # Collections
            ("list(string)", "seq_primitive"),
            ("list(number)", "seq_primitive"),
            ("list(bool)", "seq_primitive"),
            ("list(object)", "seq_object"),
            ("set(string)", "seq_primitive"),
            ("set(number)", "seq_primitive"),
            ("set(bool)", "seq_primitive"),
            ("set(object)", "seq_object"),
            ("map(string)", "map_primitive"),
            ("map(number)", "map_primitive"),
            ("map(bool)", "map_primitive"),
            ("map(object)", "map_object"),
        ],
    )
    def test_supported_expressions_parse(self, expr, shape):
        assert parse_type(expr) == shape

    def test_set_and_list_produce_identical_shape(self):
        assert parse_type("set(string)") == parse_type("list(string)")
        assert parse_type("set(object)") == parse_type("list(object)")

    def test_object_with_and_without_schema_produce_identical_shape(self):
        # The schema body is informational; runtime behavior is identical.
        assert parse_type("object") == parse_type("object({})") == parse_type("object({foo=string})")

    def test_tuple_with_and_without_body_routes_through_dynamic(self):
        assert parse_type("tuple") == parse_type("tuple([])") == parse_type("tuple([string,number])") == "dynamic"

    @pytest.mark.parametrize("expr", [" string ", "  list(object) ", "list( string )", "MAP(STRING)"])
    def test_whitespace_tolerated_but_case_required(self, expr):
        # whitespace is fine; an UPPERCASE form should fail since HCL uses lowercase types.
        if expr.lower() == expr:
            assert parse_type(expr)
        else:
            with pytest.raises(TerraformError):
                parse_type(expr)

    @pytest.mark.parametrize(
        "expr",
        [
            "auto",  # renamed → dynamic
            "list",  # must declare element type
            "set",
            "map",
            "list(list(string))",  # nested
            "map(list(string))",
            "list(map(string))",
            "any",  # Terraform input-var placeholder; not meaningful for outputs
            "null",  # null is a value, not a type
            "string()",
            "string(string)",
            "",
            "   ",
        ],
    )
    def test_unsupported_expressions_raise_with_helpful_message(self, expr):
        with pytest.raises(TerraformError) as exc:
            parse_type(expr)
        # Message should list valid forms or mention reshaping in Terraform.
        msg = str(exc.value).lower()
        assert "supported forms" in msg or "non-empty" in msg

    def test_unsupported_message_links_to_terraform_types_docs(self):
        with pytest.raises(TerraformError) as exc:
            parse_type("totally-bogus")
        assert "developer.hashicorp.com/terraform/language/expressions/types" in str(exc.value)

    def test_nested_collection_message_mentions_flatten(self):
        with pytest.raises(TerraformError, match=r"flatten\(\)|for expression"):
            parse_type("map(list(string))")

    @pytest.mark.parametrize("expr", [None, 123, [], {}])
    def test_non_string_input_raises(self, expr):
        with pytest.raises(TerraformError):
            parse_type(expr)


# ---------------------------------------------------------------------------
# _collect_hosts_from_spec — unit tests (sources/outputs)
# ---------------------------------------------------------------------------


class TestCollectHostsFromSpec:
    """Unit tests for ``_collect_hosts_from_spec`` covering each shape."""

    _WS = "my-ws"

    def _spec(self, **kwargs):
        return kwargs

    # ── primitive (string / number / bool) ────────────────────────────────────

    def test_string_produces_one_record_with_value_var(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip", type="string"),
            {"ip": "1.2.3.4"},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"]["value"] == "1.2.3.4"
        assert "item" not in records[0]["host_vars"]
        assert records[0]["index"] is None

    def test_string_auto_ansible_host_when_compose_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip", type="string"),
            {"ip": "1.2.3.4"},
            self._WS,
            compose_active=False,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_string_no_auto_ansible_host_when_compose_active(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip", type="string"),
            {"ip": "1.2.3.4"},
            self._WS,
            compose_active=True,
        )
        assert "ansible_host" not in records[0]["host_vars"]
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_number_primitive_records_value(self):
        records = _collect_hosts_from_spec(
            self._spec(output="count", type="number"),
            {"count": 42},
            self._WS,
        )
        assert records[0]["host_vars"]["value"] == 42

    def test_bool_primitive_records_value(self):
        records = _collect_hosts_from_spec(
            self._spec(output="enabled", type="bool"),
            {"enabled": True},
            self._WS,
        )
        assert records[0]["host_vars"]["value"] is True

    # ── list(primitive) and set(primitive) ────────────────────────────────────

    def test_list_string_produces_indexed_records(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["host_vars"]["value"] == "1.2.3.4"
        assert records[1]["index"] == 1
        assert records[1]["host_vars"]["value"] == "5.6.7.8"

    def test_list_string_auto_ansible_host_when_compose_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
            compose_active=False,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"
        assert records[1]["host_vars"]["ansible_host"] == "5.6.7.8"

    def test_list_string_no_auto_ansible_host_when_compose_active(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
            compose_active=True,
        )
        assert "ansible_host" not in records[0]["host_vars"]
        assert "ansible_host" not in records[1]["host_vars"]
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_list_string_no_resolved_hostname_uses_index(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": ["1.2.3.4"]},
            self._WS,
        )
        assert "resolved_hostname" not in records[0]

    def test_set_string_matches_list_string(self):
        value = ["1.2.3.4", "5.6.7.8"]
        list_recs = _collect_hosts_from_spec(self._spec(output="ips", type="list(string)"), {"ips": value}, self._WS)
        set_recs = _collect_hosts_from_spec(self._spec(output="ips", type="set(string)"), {"ips": value}, self._WS)
        assert list_recs == set_recs

    # ── list(object) and set(object) ──────────────────────────────────────────

    def test_list_object_produces_indexed_records_with_flat_host_vars(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="list(object)"),
            {"hosts": [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["host_vars"] == {"ip": "1.2.3.4"}
        assert records[0]["index"] == 0

    def test_list_object_skips_non_dict_elements(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="list(object)"),
            {"hosts": [{"ip": "1.2.3.4"}, "not-a-dict"]},
            self._WS,
        )
        assert len(records) == 1

    def test_set_object_matches_list_object(self):
        value = [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]
        list_recs = _collect_hosts_from_spec(self._spec(output="hosts", type="list(object)"), {"hosts": value}, self._WS)
        set_recs = _collect_hosts_from_spec(self._spec(output="hosts", type="set(object)"), {"hosts": value}, self._WS)
        assert list_recs == set_recs

    # ── map(primitive) ────────────────────────────────────────────────────────

    def test_map_string_key_becomes_resolved_hostname(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", type="map(string)"),
            {"host_map": {"web-1": "1.2.3.4", "web-2": "5.6.7.8"}},
            self._WS,
        )
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}

    def test_map_string_does_not_inject_key_var(self):
        # Map key is exposed as resolved_hostname (→ inventory_hostname) only;
        # no separate `key` host var is injected. This keeps user dict shapes
        # uncluttered and matches AWS inventory plugin conventions.
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", type="map(string)"),
            {"host_map": {"web-1": "1.2.3.4"}},
            self._WS,
        )
        assert records[0]["resolved_hostname"] == "web-1"
        assert "key" not in records[0]["host_vars"]
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_map_string_auto_ansible_host_when_compose_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", type="map(string)"),
            {"host_map": {"web-1": "1.2.3.4"}},
            self._WS,
            compose_active=False,
        )
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"

    def test_map_string_no_auto_ansible_host_when_compose_active(self):
        records = _collect_hosts_from_spec(
            self._spec(output="host_map", type="map(string)"),
            {"host_map": {"web-1": "1.2.3.4"}},
            self._WS,
            compose_active=True,
        )
        assert "ansible_host" not in records[0]["host_vars"]

    # ── map(object) ───────────────────────────────────────────────────────────

    def test_map_object_key_becomes_resolved_hostname(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="map(object)"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}, "web-2": {"ip": "5.6.7.8"}}},
            self._WS,
        )
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}

    def test_map_object_spreads_user_dict_flat(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="map(object)"),
            {"ec2": {"web-1": {"ip": "1.2.3.4", "env": "prod"}}},
            self._WS,
        )
        assert records[0]["host_vars"] == {"ip": "1.2.3.4", "env": "prod"}
        assert records[0]["resolved_hostname"] == "web-1"
        assert "key" not in records[0]["host_vars"]

    def test_map_object_skips_non_dict_values(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="map(object)"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}, "bad": "not-a-dict"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["resolved_hostname"] == "web-1"

    def test_map_object_user_field_named_key_is_preserved_no_injection(self):
        # The plugin does not inject a `key` host var, so a user dict
        # containing a field literally named "key" is preserved as-is.
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="map(object)"),
            {"ec2": {"web-1": {"key": "user-key", "ip": "1.2.3.4"}}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"key": "user-key", "ip": "1.2.3.4"}
        assert records[0]["resolved_hostname"] == "web-1"

    def test_list_object_user_dict_spread_directly(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="list(object)"),
            {"hosts": [{"name": "web-1", "ip": "1.2.3.4"}]},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"name": "web-1", "ip": "1.2.3.4"}

    def test_object_shape_no_auto_ansible_host_when_compose_empty(self):
        # Only primitive shapes auto-assign ansible_host; object shapes never do.
        records = _collect_hosts_from_spec(
            self._spec(output="single", type="object"),
            {"single": {"ip": "1.2.3.4", "env": "prod"}},
            self._WS,
            compose_active=False,
        )
        assert "ansible_host" not in records[0]["host_vars"]

    def test_list_object_no_auto_ansible_host_when_compose_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="list(object)"),
            {"hosts": [{"ip": "1.2.3.4"}]},
            self._WS,
            compose_active=False,
        )
        assert "ansible_host" not in records[0]["host_vars"]

    def test_map_object_no_auto_ansible_host_when_compose_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="map(object)"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}}},
            self._WS,
            compose_active=False,
        )
        assert "ansible_host" not in records[0]["host_vars"]

    # ── object ────────────────────────────────────────────────────────────────

    def test_object_produces_single_record_with_user_dict_spread_flat(self):
        records = _collect_hosts_from_spec(
            self._spec(output="single", type="object"),
            {"single": {"ip": "1.2.3.4", "env": "prod"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"ip": "1.2.3.4", "env": "prod"}
        assert records[0]["index"] is None

    # ── dynamic-detection ─────────────────────────────────────────────────────

    def test_dynamic_dict_of_dicts_treated_as_map_object(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ec2", type="dynamic"),
            {"ec2": {"web-1": {"ip": "1.2.3.4"}, "web-2": {"ip": "5.6.7.8"}}},
            self._WS,
        )
        assert len(records) == 2
        assert {r["resolved_hostname"] for r in records} == {"web-1", "web-2"}

    def test_dynamic_dict_of_primitives_treated_as_object(self):
        # The ambiguous case: dynamic picks `object`, not `map(string)`.
        records = _collect_hosts_from_spec(
            self._spec(output="cfg", type="dynamic"),
            {"cfg": {"region": "us-east-1", "env": "prod"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"region": "us-east-1", "env": "prod"}
        assert "resolved_hostname" not in records[0]

    def test_dynamic_list_of_dicts_treated_as_list_object(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="dynamic"),
            {"hosts": [{"ip": "1.2.3.4"}, {"ip": "5.6.7.8"}]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["index"] == 0
        assert records[0]["host_vars"] == {"ip": "1.2.3.4"}

    def test_dynamic_list_of_primitives_treated_as_seq_primitive(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="dynamic"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["host_vars"]["value"] == "1.2.3.4"
        assert records[1]["host_vars"]["value"] == "5.6.7.8"

    @pytest.mark.parametrize("value", ["a-string", 42, 3.14, True])
    def test_dynamic_primitives_treated_as_primitive(self, value):
        records = _collect_hosts_from_spec(
            self._spec(output="x", type="dynamic"),
            {"x": value},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"]["value"] == value

    def test_dynamic_omitted_type_defaults_to_dynamic(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ip"),
            {"ip": "1.2.3.4"},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    def test_dynamic_empty_list_skipped_silently(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="dynamic"),
            {"ips": []},
            self._WS,
        )
        assert records == []

    def test_dynamic_empty_dict_skipped_silently(self):
        records = _collect_hosts_from_spec(
            self._spec(output="cfg", type="dynamic"),
            {"cfg": {}},
            self._WS,
        )
        assert records == []

    def test_dynamic_none_skipped_silently(self):
        records = _collect_hosts_from_spec(
            self._spec(output="x", type="dynamic"),
            {"x": None},
            self._WS,
        )
        assert records == []

    def test_dynamic_mixed_list_emits_warning_and_skips(self):
        with patch(f"{_OUTPUTS_SRC}._warn") as mock_warn:
            records = _collect_hosts_from_spec(
                self._spec(output="mixed", type="dynamic"),
                {"mixed": ["a", {"k": "v"}]},
                self._WS,
            )
            assert records == []
            mock_warn.assert_called_once()
            assert "mixed" in mock_warn.call_args.args[0]

    # ── tuple (routes through dynamic detection) ──────────────────────────────

    def test_tuple_bare_dispatches_via_dynamic_detection(self):
        # `tuple` (no element-types body) is a wire-level synonym for `dynamic`
        # — runtime detection inspects the value.
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="tuple"),
            {"ips": ["10.0.0.1", "10.0.0.2"]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["host_vars"]["value"] == "10.0.0.1"

    def test_tuple_with_element_types_body_dispatches_via_dynamic(self):
        # `tuple([object, object])` — body is informational, runtime behavior
        # matches `tuple` / `dynamic`.
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="tuple([object, object])"),
            {"hosts": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]},
            self._WS,
        )
        assert len(records) == 2
        assert records[0]["host_vars"] == {"ip": "10.0.0.1"}

    # ── object with schema body ────────────────────────────────────────────────

    def test_object_with_schema_body_treated_as_object(self):
        # `object({attr=type,...})` — body is informational, runtime behavior
        # is identical to bare `object`.
        records = _collect_hosts_from_spec(
            self._spec(output="single", type="object({ip=string, env=string})"),
            {"single": {"ip": "1.2.3.4", "env": "prod"}},
            self._WS,
        )
        assert len(records) == 1
        assert records[0]["host_vars"] == {"ip": "1.2.3.4", "env": "prod"}

    def test_dynamic_unsupported_value_emits_warning_and_skips(self):
        with patch(f"{_OUTPUTS_SRC}._warn") as mock_warn:
            records = _collect_hosts_from_spec(
                self._spec(output="weird", type="dynamic"),
                {"weird": object()},
                self._WS,
            )
            assert records == []
            mock_warn.assert_called_once()

    # ── edge cases ────────────────────────────────────────────────────────────

    def test_missing_output_name_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="nonexistent", type="list(string)"),
            {"other_output": ["1.2.3.4"]},
            self._WS,
        )
        assert records == []

    def test_list_kind_wrong_value_type_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": "not-a-list"},
            self._WS,
        )
        assert records == []

    def test_map_kind_wrong_value_type_returns_empty(self):
        records = _collect_hosts_from_spec(
            self._spec(output="hosts", type="map(object)"),
            {"hosts": ["not", "a", "dict"]},
            self._WS,
        )
        assert records == []

    def test_workspace_name_set_on_all_records(self):
        records = _collect_hosts_from_spec(
            self._spec(output="ips", type="list(string)"),
            {"ips": ["1.2.3.4", "5.6.7.8"]},
            "custom-ws",
        )
        assert all(r["workspace_name"] == "custom-ws" for r in records)


# ---------------------------------------------------------------------------
# OutputsSource — hosts_from validation (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceHostsFromValidation:
    """validate_options should reject malformed hosts_from before any I/O."""

    _WS_OPTS = {"workspace_id": "ws-abc", "organization": None, "workspace": None}

    def _validate(self, hosts_from):
        OutputsSource.validate_options({**self._WS_OPTS, "hosts_from": hosts_from})

    def test_none_is_accepted(self):
        self._validate(None)

    def test_dict_spec_accepted(self):
        self._validate({"output": "ips", "type": "list(string)"})

    def test_list_of_specs_accepted(self):
        self._validate([{"output": "ips", "type": "list(string)"}, {"output": "ec2", "type": "map(object)"}])

    def test_top_level_wrong_type_raises(self):
        with pytest.raises(TerraformError, match="hosts_from must be"):
            self._validate("not-a-mapping-or-list")

    def test_spec_must_be_mapping(self):
        with pytest.raises(TerraformError, match=r"hosts_from\[0\] must be a mapping"):
            self._validate(["not-a-mapping"])

    def test_missing_output_raises(self):
        with pytest.raises(TerraformError, match="non-empty 'output' string"):
            self._validate({"type": "string"})

    def test_empty_output_raises(self):
        with pytest.raises(TerraformError, match="non-empty 'output' string"):
            self._validate({"output": "", "type": "string"})

    @pytest.mark.parametrize(
        "good_type",
        [
            "dynamic",
            "tuple",
            "tuple([string, number])",
            "object",
            "object({name=string, tags=map(string)})",
        ],
    )
    def test_terraform_native_type_expressions_accepted(self, good_type):
        self._validate({"output": "x", "type": good_type})

    @pytest.mark.parametrize(
        "bad_type",
        [
            "auto",  # renamed → dynamic
            "list(list(string))",
            "map(list(string))",
            "list(map(string))",
            "any",  # input-var placeholder, not meaningful for outputs
            "null",  # null is a value, not a type
            "string()",
            "",
        ],
    )
    def test_invalid_type_expression_raises(self, bad_type):
        with pytest.raises(TerraformError):
            self._validate({"output": "x", "type": bad_type})

    def test_nested_collection_error_mentions_flatten(self):
        with pytest.raises(TerraformError, match=r"flatten\(\)|for expression"):
            self._validate({"output": "x", "type": "map(list(string))"})

    def test_use_as_key_rejected_with_migration_message(self):
        with pytest.raises(TerraformError, match=r"'use_as' is no longer supported") as exc:
            self._validate({"output": "x", "type": "list(string)", "use_as": "ansible_host"})
        msg = str(exc.value)
        assert "compose" in msg
        assert "value" in msg

    def test_item_spec_key_rejected_with_migration_message(self):
        # Defensive against users who saw the (now-reverted) item-nested docs.
        with pytest.raises(TerraformError, match=r"'item' is not a recognised spec key") as exc:
            self._validate({"output": "x", "type": "string", "item": "anything"})
        assert "value" in str(exc.value)

    def test_key_spec_key_rejected_with_migration_message(self):
        # Defensive against users who saw the (now-reverted) item-nested docs.
        with pytest.raises(TerraformError, match=r"'key' is not a recognised spec key") as exc:
            self._validate({"output": "x", "type": "map(object)", "key": "anything"})
        assert "inventory_hostname" in str(exc.value)


# ---------------------------------------------------------------------------
# OutputsSource — hosts_from mode via collect_hosts (sources/outputs)
# ---------------------------------------------------------------------------


class TestOutputsSourceHostsFromMode:
    def _make_source(self, hosts_from, compose=None):
        options = {
            "workspace_id": None,
            "organization": "my-org",
            "workspace": "my-ws",
            "hosts_from": hosts_from,
            "compose": compose or {},
        }
        return OutputsSource(Mock(), options)

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_hosts_from_dict_normalized_to_list(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "instance_ips", "value": ["1.2.3.4", "5.6.7.8"]},
        ]
        records = self._make_source(hosts_from={"output": "instance_ips", "type": "list(string)"}).collect_hosts()
        assert len(records) == 2
        # No compose → ansible_host is auto-set to the primitive value.
        assert records[0]["host_vars"]["ansible_host"] == "1.2.3.4"
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

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
                {"output": "web_ips", "type": "list(string)"},
                {"output": "db_ips", "type": "list(string)"},
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
        records = self._make_source(hosts_from={"output": "ips", "type": "list(string)"}).collect_hosts()
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
        records = self._make_source(hosts_from={"output": "ec2", "type": "map(object)"}).collect_hosts()
        assert len(records) == 2
        hostnames = {r["resolved_hostname"] for r in records}
        assert hostnames == {"web-1", "web-2"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_hosts_from_dynamic_dispatches_at_runtime(self, mock_resolve, mock_fetch):
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ec2", "value": {"web-1": {"ip": "1.2.3.4"}, "web-2": {"ip": "5.6.7.8"}}},
        ]
        records = self._make_source(hosts_from={"output": "ec2", "type": "dynamic"}).collect_hosts()
        assert len(records) == 2
        assert {r["resolved_hostname"] for r in records} == {"web-1", "web-2"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_compose_active_suppresses_auto_ansible_host(self, mock_resolve, mock_fetch):
        # When compose is non-empty, the user is in control; do not auto-assign
        # ansible_host even if compose doesn't reference it.
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ips", "value": ["1.2.3.4"]},
        ]
        source = self._make_source(
            hosts_from={"output": "ips", "type": "list(string)"},
            compose={"some_other_var": "value"},
        )
        records = source.collect_hosts()
        assert len(records) == 1
        assert "ansible_host" not in records[0]["host_vars"]
        assert records[0]["host_vars"]["value"] == "1.2.3.4"

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    def test_map_object_user_dict_spread_flat_with_no_key_injection(self, mock_resolve, mock_fetch):
        # Regression: user dict fields are spread flat at the top level
        # (matching aws_ec2). The map key is exposed only as resolved_hostname
        # (→ inventory_hostname) — there is no `key` host variable injected,
        # so user fields named `item` or `key` are preserved as-is.
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ec2", "value": {"web-1": {"item": "user-data", "key": "user-key", "ip": "1.2.3.4"}}},
        ]
        source = self._make_source(hosts_from={"output": "ec2", "type": "map(object)"})
        records = source.collect_hosts()
        assert len(records) == 1
        assert records[0]["host_vars"] == {"item": "user-data", "key": "user-key", "ip": "1.2.3.4"}
        assert records[0]["resolved_hostname"] == "web-1"


# ---------------------------------------------------------------------------
# get_source_backend factory (utils/factory)
# ---------------------------------------------------------------------------


class TestGetSourceBackend:
    def test_statefile_returns_statefile_class(self):
        assert get_source_backend("statefile") is StatefileSource

    def test_outputs_returns_outputs_class(self):
        assert get_source_backend("outputs") is OutputsSource

    def test_unknown_source_raises(self):
        with pytest.raises(TerraformError, match="Unknown source"):
            get_source_backend("nonexistent")

    def test_sources_registry_contains_all_backends(self):
        assert set(SOURCES.keys()) == {"statefile", "outputs"}


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
    def test_default_ansible_host_object_output_adds_one_host(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": {"public_ip": "1.2.3.4", "metadata": {"env": "prod"}}, "sensitive": False},
        ]

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        plugin.inventory.add_host.assert_called_once_with("my-ws_ansible_host")
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host", "public_ip", "1.2.3.4")
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host", "metadata", {"env": "prod"})

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_default_ansible_host_list_string_output_adds_indexed_hosts(self, mock_client_cls, mock_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ansible_host", "value": ["10.0.0.1", "10.0.0.2"], "sensitive": False},
        ]

        plugin = _make_plugin(_base_options(source="outputs"))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"my-ws_ansible_host_0", "my-ws_ansible_host_1"}
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host_0", "ansible_host", "10.0.0.1")
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host_1", "ansible_host", "10.0.0.2")

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

    # ── regression: list(object) + hostnames=[name] produces N distinct hosts ──

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_list_object_with_hostnames_name_produces_distinct_hosts_no_collapse(self, mock_client_cls, mock_resolve, mock_fetch):
        # Reproduces the production bug the user hit on Ansible Automation
        # Platform: list(object) of 3 elements with hostnames: [name].
        # Before the literal-fallback drop, all three records resolved to the
        # literal "name" → Ansible's add_host("name") collapsed them into
        # one host whose hostvars were repeatedly overwritten.
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {
                "name": "ec2_hosts",
                "value": [
                    {"name": "hcp-ec2-1", "instance_id": "i-1", "private_ip": "10.0.0.1", "public_ip": "1.1.1.1"},
                    {"name": "hcp-ec2-2", "instance_id": "i-2", "private_ip": "10.0.0.2", "public_ip": "2.2.2.2"},
                    {"name": "hcp-ec2-3", "instance_id": "i-3", "private_ip": "10.0.0.3", "public_ip": "3.3.3.3"},
                ],
                "sensitive": False,
            },
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostnames=["name"],
                hosts_from={"output": "ec2_hosts", "type": "list(object)"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # Three distinct hosts named from the per-record `name` field — no collapse.
        assert plugin.inventory.add_host.call_count == 3
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"hcp-ec2-1", "hcp-ec2-2", "hcp-ec2-3"}

    # ── hostvars_prefix / hostvars_suffix ──────────────────────────────────────

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostvars_prefix_renames_user_fields_only(self, mock_client_cls, mock_resolve, mock_fetch):
        # User-data fields get the prefix; ansible_host (Ansible-reserved) and
        # value (plugin contract) are never prefixed.
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "web", "value": {"name": "web-1", "public_ip": "1.2.3.4"}, "sensitive": False},
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostvars_prefix="tf_",
                hosts_from={"output": "web", "type": "object"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # User fields are prefixed: name → tf_name, public_ip → tf_public_ip
        plugin.inventory.set_variable.assert_any_call("my-ws_web", "tf_name", "web-1")
        plugin.inventory.set_variable.assert_any_call("my-ws_web", "tf_public_ip", "1.2.3.4")
        # Original (unprefixed) user-field names must NOT be set.
        for call in plugin.inventory.set_variable.call_args_list:
            assert call[0][1] != "name"
            assert call[0][1] != "public_ip"

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostvars_prefix_hostnames_works_with_prefixed_reference(self, mock_client_cls, mock_resolve, mock_fetch):
        # With hostvars_prefix=tf_ and hostnames=[tf_instance_id], the
        # prefixed name resolves via the resolution view (combined dict
        # holding both original and prefixed keys), matching aws_rds.
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {
                "name": "ec2",
                "value": [
                    {"name": "web-1", "instance_id": "i-aaa"},
                    {"name": "web-2", "instance_id": "i-bbb"},
                ],
                "sensitive": False,
            },
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostvars_prefix="tf_",
                hosts_from={"output": "ec2", "type": "list(object)"},
                hostnames=["tf_instance_id"],
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"i-aaa", "i-bbb"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostvars_prefix_hostnames_also_works_with_original_reference(self, mock_client_cls, mock_resolve, mock_fetch):
        # With hostvars_prefix=tf_ and hostnames=[instance_id] (UNprefixed),
        # resolution must STILL work — the resolution view contains both
        # original and prefixed names. This is what AWS plugins do.
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {
                "name": "ec2",
                "value": [
                    {"name": "web-1", "instance_id": "i-aaa"},
                    {"name": "web-2", "instance_id": "i-bbb"},
                ],
                "sensitive": False,
            },
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostvars_prefix="tf_",
                hosts_from={"output": "ec2", "type": "list(object)"},
                hostnames=["instance_id"],
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert plugin.inventory.add_host.call_count == 2
        hostnames = {c[0][0] for c in plugin.inventory.add_host.call_args_list}
        assert hostnames == {"i-aaa", "i-bbb"}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostvars_prefix_filters_resolve_against_combined_view(self, mock_client_cls, mock_resolve, mock_fetch):
        # include_filters with prefixed key should match (and an unprefixed
        # key would equally — both names live in the resolution view).
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {
                "name": "ec2",
                "value": [
                    {"name": "web-1", "role": "web"},
                    {"name": "db-1", "role": "db"},
                ],
                "sensitive": False,
            },
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostvars_prefix="tf_",
                hosts_from={"output": "ec2", "type": "list(object)"},
                include_filters=[{"tf_role": "web"}],
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # Only the web host should be registered (db filtered out).
        assert plugin.inventory.add_host.call_count == 1

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_hostvars_prefix_does_not_rename_value_for_primitives(self, mock_client_cls, mock_resolve, mock_fetch):
        # `value` is a plugin-contract var name and must never be renamed —
        # otherwise `compose: {ansible_host: value}` and `hostnames: [value]`
        # would silently break for users who later add a hostvars_prefix.
        mock_client_cls.return_value = Mock()
        mock_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [
            {"name": "ip", "value": "1.2.3.4", "sensitive": False},
        ]

        plugin = _make_plugin(
            _base_options(
                source="outputs",
                hostvars_prefix="tf_",
                hosts_from={"output": "ip", "type": "string"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # `value` and `ansible_host` (auto-set since compose is empty) are never
        # prefixed — `tf_value` / `tf_ansible_host` must NOT be set.
        plugin.inventory.set_variable.assert_any_call("my-ws_ip", "value", "1.2.3.4")
        plugin.inventory.set_variable.assert_any_call("my-ws_ip", "ansible_host", "1.2.3.4")
        for call in plugin.inventory.set_variable.call_args_list:
            assert call[0][1] != "tf_value"
            assert call[0][1] != "tf_ansible_host"


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
        mock_client_cls.from_mapping.side_effect = TerraformTokenNotFoundError("no token")

        plugin = _make_plugin(_base_options())
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="Authentication"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_source_search_raises_unknown_source(self):
        plugin = _make_plugin(_base_options(source="search"))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="Unknown source"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")


# ---------------------------------------------------------------------------
# InventoryModule cache behavior — Cacheable mixin, timeout-based caching
# ---------------------------------------------------------------------------


def _make_cache_plugin(options: dict) -> InventoryModule:
    """Build a plugin with a dict-backed _cache attr (matches CachePluginAdjudicator's
    KeyError-on-miss / __setitem__-on-write contract well enough for unit tests)."""
    plugin = _make_plugin(options)
    plugin._cache = {}
    return plugin


def _v1_blob(source: str, *, data, workspace_id="ws-abc", workspace_name="my-ws", state_version_id=None) -> dict:
    """Build the v1 cache blob shape for tests."""
    return {
        "schema": "tfc_inv_cache_v1",
        "source": source,
        "workspace_name": workspace_name,
        "workspace_id": workspace_id,
        "state_version_id": state_version_id,
        "data": data,
    }


def _cache_key_for(source: str, ws="my-ws", org="my-org") -> str:
    """Compute the inner cache key the plugin would generate for org/workspace config."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", "_".join(["hashicorp.terraform.tfc_inv", source, f"{org}/{ws}"]))


class TestInventoryCacheStatefile:
    """Caching behavior with source=statefile."""

    def _state(self, ip="10.0.0.1"):
        return _make_resource_state([_aws_resource("web", [{"attributes": {"public_ip": ip}}])])

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_disabled_skips_read_and_write(self, mock_client_cls, mock_src_resolve, mock_download):
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=False))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_download.assert_called_once()
        assert plugin._cache == {}

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_miss_writes_blob(self, mock_client_cls, mock_src_resolve, mock_download):
        """On miss, the source fetches live and the plugin stores
        ``{workspace_name, state}`` so subsequent runs can serve fully offline."""
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=True))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_download.assert_called_once()
        # Static key derived purely from inventory config (no API calls).
        # The inner regex sanitizer maps "/" -> "_" so the org/ws separator
        # ends up as "_" in the stored key.
        expected_key = _cache_key_for("statefile")
        assert expected_key in plugin._cache
        assert plugin._cache[expected_key] == _v1_blob("statefile", data=self._state())

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_hit_skips_client_construction(self, mock_client_cls, mock_src_resolve, mock_download):
        """The strongest assertion: on cache hit, no TerraformClient is built
        and no API helper is invoked. This is what makes the cache offline-capable."""
        plugin = _make_cache_plugin(_base_options(cache=True))
        # Inner key is built from raw config (workspace_id absent → org/ws form),
        # then sanitized to filesystem-safe chars.
        key = _cache_key_for("statefile")
        plugin._cache[key] = _v1_blob("statefile", data=self._state(ip="10.9.9.9"))

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        # No client built, no source-level resolve, no download. Pure offline path.
        mock_client_cls.assert_not_called()
        mock_src_resolve.assert_not_called()
        mock_download.assert_not_called()
        # And inventory was still produced from the cached blob.
        plugin.inventory.set_variable.assert_any_call("aws_instance_web", "public_ip", "10.9.9.9")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_flush_cache_runtime_skips_read_but_writes(self, mock_client_cls, mock_src_resolve, mock_download):
        """``--flush-cache`` passes ``cache=False`` to parse() while user opt-in
        remains True. Read must be skipped but a fresh write is expected."""
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=True))
        # Pre-seed a stale entry that should be overwritten.
        key = _cache_key_for("statefile")
        plugin._cache[key] = _v1_blob("statefile", data={"stale": "payload"})

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=False)

        # Read was skipped -> live download happened.
        mock_download.assert_called_once()
        # And the stale entry was overwritten with the fresh blob.
        assert plugin._cache[key] == _v1_blob("statefile", data=self._state())

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cached_blob_honors_changed_provider_mapping(self, mock_client_cls, mock_src_resolve, mock_download):
        """Cache holds raw state JSON; provider_mapping is re-applied on every
        parse, so a config change must reshape the inventory even on cache hit."""
        # Cached state contains a null_resource which is NOT in the default mapping.
        null_state = _make_resource_state(
            [
                {
                    "mode": "managed",
                    "type": "null_resource",
                    "name": "marker",
                    "provider": 'provider["registry.terraform.io/hashicorp/null"]',
                    "instances": [{"attributes": {"triggers": {"server_ip": "10.0.0.1"}}}],
                }
            ]
        )
        key = _cache_key_for("statefile")
        cached_blob = _v1_blob("statefile", data=null_state)

        # Run 1: default provider_mapping -> null_resource filtered out.
        plugin1 = _make_cache_plugin(_base_options(cache=True))
        plugin1._cache[key] = cached_blob
        with _parse_ctx(plugin1):
            plugin1.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)
        plugin1.inventory.add_host.assert_not_called()

        # Run 2: explicit provider_mapping -> null_resource picked up.
        plugin2 = _make_cache_plugin(
            _base_options(
                cache=True,
                provider_mapping=[
                    {
                        "provider_name": "registry.terraform.io/hashicorp/null",
                        "types": ["null_resource"],
                    }
                ],
            )
        )
        plugin2._cache[key] = cached_blob
        with _parse_ctx(plugin2):
            plugin2.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)
        plugin2.inventory.add_host.assert_called_once()
        # Both runs were pure cache hits.
        mock_client_cls.assert_not_called()
        mock_download.assert_not_called()


class TestInventoryCacheOutputs:
    """Caching behavior with source=outputs."""

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_disabled_skips_read_and_write(self, mock_client_cls, mock_src_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        mock_fetch.return_value = [{"name": "ansible_host", "value": "1.2.3.4", "sensitive": False}]

        plugin = _make_cache_plugin(_base_options(source="outputs", cache=False))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_fetch.assert_called_once()
        assert plugin._cache == {}

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_miss_writes_blob(self, mock_client_cls, mock_src_resolve, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        outputs = [{"name": "ansible_host", "value": "1.2.3.4", "sensitive": False}]
        mock_fetch.return_value = outputs

        plugin = _make_cache_plugin(_base_options(source="outputs", cache=True))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        mock_fetch.assert_called_once()
        expected_key = _cache_key_for("outputs")
        assert plugin._cache[expected_key] == _v1_blob("outputs", data=outputs)

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_hit_skips_client_construction(self, mock_client_cls, mock_src_resolve, mock_fetch):
        plugin = _make_cache_plugin(_base_options(source="outputs", cache=True))
        cached_outputs = [{"name": "ansible_host", "value": "9.9.9.9", "sensitive": False}]
        key = _cache_key_for("outputs")
        plugin._cache[key] = _v1_blob("outputs", data=cached_outputs)

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        mock_client_cls.assert_not_called()
        mock_src_resolve.assert_not_called()
        mock_fetch.assert_not_called()
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host", "ansible_host", "9.9.9.9")

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cached_blob_honors_changed_hosts_from(self, mock_client_cls, mock_src_resolve, mock_fetch):
        """Cache holds raw outputs list; hosts_from is re-applied per parse."""
        cached_outputs = [
            {"name": "ips", "value": ["10.0.0.1", "10.0.0.2"], "sensitive": False},
        ]
        key = _cache_key_for("outputs")
        cached_blob = _v1_blob("outputs", data=cached_outputs)

        # Run 1: no hosts_from -> default mode looks for ``ansible_host`` only -> 0 hosts.
        plugin1 = _make_cache_plugin(_base_options(source="outputs", cache=True))
        plugin1._cache[key] = cached_blob
        with _parse_ctx(plugin1):
            plugin1.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)
        plugin1.inventory.add_host.assert_not_called()

        # Run 2: explicit hosts_from points at ``ips`` -> 2 hosts.
        plugin2 = _make_cache_plugin(
            _base_options(
                source="outputs",
                cache=True,
                hosts_from={"output": "ips", "type": "list(string)"},
            )
        )
        plugin2._cache[key] = cached_blob
        with _parse_ctx(plugin2):
            plugin2.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)
        assert plugin2.inventory.add_host.call_count == 2

        # Both runs were pure cache hits.
        mock_client_cls.assert_not_called()
        mock_fetch.assert_not_called()


class TestInventoryCacheKey:
    """Cache key composition — exercising _cache_key directly.

    The key is built from STATIC config only (no API calls). The address is
    intentionally not part of the key — cross-endpoint isolation is the user's
    job via ``cache_prefix`` / ``cache_connection``. The key uses chars safe
    for filesystem-backed cache plugins (jsonfile etc.).
    """

    def _key(self, plugin, source, ws_id=None, organization=None, workspace=None):
        return plugin._cache_key(source, ws_id, organization, workspace)

    def test_source_changes_key(self):
        p = InventoryModule()
        a = self._key(p, "outputs", organization="o", workspace="w")
        b = self._key(p, "statefile", organization="o", workspace="w")
        assert a != b

    def test_workspace_changes_key(self):
        p = InventoryModule()
        a = self._key(p, "outputs", organization="o", workspace="w1")
        b = self._key(p, "outputs", organization="o", workspace="w2")
        assert a != b

    def test_organization_changes_key(self):
        """Same workspace name in different orgs must NOT collide."""
        p = InventoryModule()
        a = self._key(p, "outputs", organization="org-a", workspace="w")
        b = self._key(p, "outputs", organization="org-b", workspace="w")
        assert a != b

    def test_workspace_id_path_differs_from_org_workspace_path(self):
        """Two ways of pointing at the same workspace produce different keys
        (we don't try to canonicalize — they'd be different inventory configs)."""
        p = InventoryModule()
        a = self._key(p, "outputs", ws_id="ws-abc")
        b = self._key(p, "outputs", organization="o", workspace="w")
        assert a != b

    def test_key_is_filesystem_safe(self):
        """No characters that file-backed cache plugins (jsonfile etc.) treat
        as path separators or otherwise mangle."""
        p = InventoryModule()
        key = self._key(p, "outputs", organization="my-org", workspace="my-ws")
        assert all(c.isalnum() or c in "._-" for c in key), f"unsafe char in key: {key!r}"
        # And carries all the discriminator parts.
        assert "outputs" in key and "my-org" in key and "my-ws" in key

    def test_unsafe_chars_get_sanitized(self):
        """Defensive: even if a workspace/org name contained a special
        character, the key must remain filesystem-safe."""
        p = InventoryModule()
        key = self._key(p, "outputs", organization="org/with/slashes", workspace="ws:with:colons")
        assert "/" not in key
        assert ":" not in key


# ---------------------------------------------------------------------------
# InventoryModule cache validation mode (cache_validate_current_state_version)
# ---------------------------------------------------------------------------


class TestInventoryCacheValidationStatefile:
    """Apply-aware cache validation for source=statefile.

    Opt-in via ``cache_validate_current_state_version: true``. Each run
    resolves the workspace and the current state version ID; the cached
    blob is reused only when its recorded ``state_version_id`` matches.
    Trade-off: not offline-capable.
    """

    def _state(self, ip="10.0.0.1"):
        return _make_resource_state([_aws_resource("web", [{"attributes": {"public_ip": ip}}])])

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_hit_with_matching_sv_id_skips_download(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_download):
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-1"

        plugin = _make_cache_plugin(_base_options(cache=True, cache_validate_current_state_version=True))
        key = _cache_key_for("statefile")
        plugin._cache[key] = _v1_blob("statefile", data=self._state(ip="10.9.9.9"), state_version_id="sv-1")

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        # Validation API calls happened (this is the trade-off vs. default mode):
        mock_inv_resolve.assert_called_once()
        mock_inv_sv.assert_called_once()
        # But the heavy download was skipped — that's the freshness-validated win.
        mock_download.assert_not_called()
        # And inventory came from the cached blob.
        plugin.inventory.set_variable.assert_any_call("aws_instance_web", "public_ip", "10.9.9.9")

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_changed_sv_id_refreshes_cache(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_download):
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-NEW"
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=True, cache_validate_current_state_version=True))
        key = _cache_key_for("statefile")
        # Cached blob from a previous apply (older sv_id):
        plugin._cache[key] = _v1_blob("statefile", data={"stale": "payload"}, state_version_id="sv-OLD")

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        # Validation noticed the mismatch and pulled fresh data.
        mock_download.assert_called_once()
        # And the cache is now tagged with the new sv_id.
        assert plugin._cache[key]["state_version_id"] == "sv-NEW"
        assert plugin._cache[key]["data"] == self._state()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_missing_sv_id_in_blob_treated_as_miss(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_download):
        """A blob written by a default-mode (validation=False) run lacks an
        ``state_version_id`` value — validation mode must treat that as a
        miss rather than reuse it."""
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-1"
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=True, cache_validate_current_state_version=True))
        key = _cache_key_for("statefile")
        # Default-mode shape: state_version_id=None
        plugin._cache[key] = _v1_blob("statefile", data=self._state(), state_version_id=None)

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        mock_download.assert_called_once()
        assert plugin._cache[key]["state_version_id"] == "sv-1"

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_api_failure_raises_parser_error(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_download):
        """When validation cannot run (e.g., HCP/TFE unreachable),
        cache_validate_current_state_version=true refuses to silently serve
        cached data — it raises so the operator notices."""
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = None  # API call failed inside resolve_current_state_version_id

        plugin = _make_cache_plugin(_base_options(cache=True, cache_validate_current_state_version=True))
        # Even with fresh-looking cached data, raise rather than serve it stale.
        plugin._cache[_cache_key_for("statefile")] = _v1_blob("statefile", data=self._state(), state_version_id="sv-1")

        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="cache_validate_current_state_version"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        mock_download.assert_not_called()

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_miss_writes_blob_with_current_sv_id(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_download):
        """A first-run cache miss in validation mode writes a blob whose
        ``state_version_id`` equals the resolved current sv_id."""
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-FIRST"
        mock_download.return_value = self._state()

        plugin = _make_cache_plugin(_base_options(cache=True, cache_validate_current_state_version=True))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        key = _cache_key_for("statefile")
        assert plugin._cache[key] == _v1_blob("statefile", data=self._state(), state_version_id="sv-FIRST")


class TestInventoryCacheValidationOutputs:
    """Apply-aware cache validation for source=outputs."""

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_hit_with_matching_sv_id_skips_fetch(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-1"

        cached_outputs = [{"name": "ansible_host", "value": "9.9.9.9", "sensitive": False}]
        plugin = _make_cache_plugin(_base_options(source="outputs", cache=True, cache_validate_current_state_version=True))
        plugin._cache[_cache_key_for("outputs")] = _v1_blob("outputs", data=cached_outputs, state_version_id="sv-1")

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        mock_inv_sv.assert_called_once()
        mock_fetch.assert_not_called()
        plugin.inventory.set_variable.assert_any_call("my-ws_ansible_host", "ansible_host", "9.9.9.9")

    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_INV_MODULE}.resolve_current_state_version_id")
    @patch(f"{_INV_MODULE}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_validation_changed_sv_id_refreshes_outputs(self, mock_client_cls, mock_inv_resolve, mock_inv_sv, mock_fetch):
        mock_client_cls.return_value = Mock()
        mock_inv_resolve.return_value = ("ws-abc", "my-ws")
        mock_inv_sv.return_value = "sv-NEW"
        fresh_outputs = [{"name": "ansible_host", "value": "1.2.3.4", "sensitive": False}]
        mock_fetch.return_value = fresh_outputs

        plugin = _make_cache_plugin(_base_options(source="outputs", cache=True, cache_validate_current_state_version=True))
        key = _cache_key_for("outputs")
        plugin._cache[key] = _v1_blob("outputs", data=[{"name": "ansible_host", "value": "old"}], state_version_id="sv-OLD")

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        mock_fetch.assert_called_once()
        assert plugin._cache[key] == _v1_blob("outputs", data=fresh_outputs, state_version_id="sv-NEW")


class TestStatefileSensitiveSanitizationForCache:
    """Sanitization happens BEFORE the blob lands in cache.

    Persisted cache entries must never contain values Terraform flagged as
    sensitive — those would otherwise be written to disk under
    ~/.ansible/cache/.
    """

    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_cache_miss_writes_sanitized_state_only(self, mock_client_cls, mock_src_resolve, mock_download):
        """Live state with sensitive_attributes -> cached state has them stripped."""
        mock_client_cls.return_value = Mock()
        mock_src_resolve.return_value = ("ws-abc", "my-ws")
        # Raw state from TFC includes a sensitive password attribute.
        raw_state = _make_resource_state(
            [
                {
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "web",
                    "provider": 'provider["registry.terraform.io/hashicorp/aws"]',
                    "instances": [
                        {
                            "attributes": {
                                "public_ip": "1.2.3.4",
                                "password": "VERY-SECRET",
                            },
                            "sensitive_attributes": [[{"type": "get_attr", "value": "password"}]],
                        }
                    ],
                }
            ]
        )
        mock_download.return_value = raw_state

        plugin = _make_cache_plugin(_base_options(cache=True))
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        key = _cache_key_for("statefile")
        cached_state = plugin._cache[key]["data"]
        instance = cached_state["resources"][0]["instances"][0]
        # Sensitive value gone; non-sensitive value preserved.
        assert "password" not in instance["attributes"]
        assert instance["attributes"]["public_ip"] == "1.2.3.4"
        # And the marker was dropped — its referent is gone, so future
        # second-pass sanitization on the cached blob is a no-op.
        assert "sensitive_attributes" not in instance


# ---------------------------------------------------------------------------
# Multi-workspace mode (workspace_filters)
# ---------------------------------------------------------------------------


def _per_ws_key(source: str, ws_id: str) -> str:
    """Per-workspace cache key produced by _cache_key(source, workspace_id, None, None)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", "_".join(["hashicorp.terraform.tfc_inv", source, ws_id]))


def _selector_key(source: str, org: str, filters: dict) -> str:
    """Mirror _selector_cache_key()."""
    import json as _json

    normalized = _json.dumps(filters or {}, sort_keys=True, default=str)
    raw = "_".join(["hashicorp.terraform.tfc_inv", "selector", source, org or "", normalized])
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)


class TestMultiWorkspaceOptionValidation:
    """Mutex / required-together / range checks happen before any API call."""

    def test_workspace_filters_with_workspace_id_fails(self):
        plugin = _make_plugin(
            _base_options(
                workspace_id="ws-abc",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
            )
        )
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="mutually exclusive"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_workspace_filters_with_workspace_name_fails(self):
        plugin = _make_plugin(
            _base_options(
                workspace_filters={"project_id": "prj-x"},
            )
        )
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="mutually exclusive"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_workspace_filters_requires_organization(self):
        plugin = _make_plugin(
            _base_options(
                workspace=None,
                organization=None,
                workspace_filters={"project_id": "prj-x"},
            )
        )
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="requires 'organization'"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_concurrency_too_low_fails(self):
        plugin = _make_plugin(_base_options(concurrency=0))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="concurrency must be between"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

    def test_concurrency_above_max_fails(self):
        plugin = _make_plugin(_base_options(concurrency=11))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="concurrency must be between"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")


class TestListWorkspaces:
    """The list_workspaces() helper maps YAML keys → WorkspaceListOptions."""

    def _client_returning(self, workspaces):
        client = Mock()
        client.client.workspaces.list.return_value = iter(workspaces)
        return client

    def test_project_id_must_start_with_prj_prefix(self):
        from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import list_workspaces

        client = self._client_returning([])
        with pytest.raises(TerraformError, match="must be a project ID starting with 'prj-'"):
            list_workspaces(client, "my-org", {"project_id": "Finance_Prod"})

    def test_unsupported_filter_keys_fail(self):
        from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import list_workspaces

        client = self._client_returning([])
        with pytest.raises(TerraformError, match="unsupported keys"):
            list_workspaces(client, "my-org", {"unknown_key": "x"})

    def test_empty_filter_values_dropped(self):
        from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import list_workspaces

        client = self._client_returning([])
        list_workspaces(client, "my-org", {"name_search": "", "tags": "prod"})
        opts = client.client.workspaces.list.call_args.args[1]
        # tags forwarded, empty name_search dropped.
        assert getattr(opts, "tags", None) == "prod"
        # search field corresponds to name_search; empty value means unset/None.
        assert getattr(opts, "search", None) in (None, "")

    def test_filter_field_mapping_via_attributes(self):
        from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import list_workspaces

        client = self._client_returning([])
        list_workspaces(
            client,
            "my-org",
            {
                "project_id": "prj-abc",
                "name_search": "web",
                "tags": "prod,linux",
                "exclude_tags": "deprecated",
                "wildcard_name": "*prod*",
                "current_run_status": "applied",
                "sort": "name",
                "page_size": 50,
            },
        )
        opts = client.client.workspaces.list.call_args.args[1]
        assert opts.project_id == "prj-abc"
        assert opts.search == "web"
        assert opts.tags == "prod,linux"
        assert opts.exclude_tags == "deprecated"
        assert opts.wildcard_name == "*prod*"
        assert opts.current_run_status == "applied"
        assert opts.sort == "name"
        assert opts.page_size == 50

    def test_returns_id_name_tuples(self):
        """Matches pytfe's actual Workspace model: id / name at the top level."""
        from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.utils.common import list_workspaces

        ws_a = Mock()
        ws_a.id = "ws-a"
        ws_a.name = "alpha"
        ws_b = Mock()
        ws_b.id = "ws-b"
        ws_b.name = "beta"
        client = self._client_returning([ws_a, ws_b])

        targets = list_workspaces(client, "my-org", {})
        assert targets == [("ws-a", "alpha"), ("ws-b", "beta")]


class TestSelectorCacheKey:
    """The selector cache key must be order-independent and filesystem-safe."""

    def test_filter_order_does_not_change_key(self):
        plugin = _make_plugin(_base_options())
        k1 = plugin._selector_cache_key("outputs", "my-org", {"project_id": "prj-x", "tags": "prod"})
        k2 = plugin._selector_cache_key("outputs", "my-org", {"tags": "prod", "project_id": "prj-x"})
        assert k1 == k2

    def test_different_filters_produce_different_keys(self):
        plugin = _make_plugin(_base_options())
        k1 = plugin._selector_cache_key("outputs", "my-org", {"project_id": "prj-x"})
        k2 = plugin._selector_cache_key("outputs", "my-org", {"project_id": "prj-y"})
        assert k1 != k2

    def test_key_is_filesystem_safe(self):
        plugin = _make_plugin(_base_options())
        k = plugin._selector_cache_key("outputs", "my org/x", {"name_search": "a/b:c?d"})
        assert re.match(r"^[A-Za-z0-9._-]+$", k) is not None


class TestMultiWorkspaceFlow:
    """End-to-end multi-workspace dispatch (sequential and parallel)."""

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_outputs_two_workspaces_merge_with_workspace_vars(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        """Two workspaces matched by filters merge their outputs, and every
        host gets ``tfc_workspace_id`` / ``tfc_workspace_name`` stamped."""
        mock_client_cls.return_value = Mock()
        mock_list.return_value = [("ws-a", "alpha"), ("ws-b", "beta")]
        # Source-level resolve must not be called — the dispatcher hands the
        # workspace identity to the source via _validation_ctx.
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")

        def _fetch(client, workspace_id):
            return [{"name": "ansible_host", "value": f"{workspace_id}-host", "sensitive": False}]

        mock_fetch.side_effect = _fetch

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # Both workspaces produced one host each.
        assert mock_fetch.call_count == 2
        # Hosts were registered with the per-workspace stamp.
        calls = plugin.inventory.set_variable.call_args_list
        recorded = {(c.args[0], c.args[1]): c.args[2] for c in calls if len(c.args) >= 3}
        # Whatever the hostname, tfc_workspace_id / tfc_workspace_name keys
        # appear paired with their respective workspace ids.
        ws_ids = {v for (h, k), v in recorded.items() if k == "tfc_workspace_id"}
        ws_names = {v for (h, k), v in recorded.items() if k == "tfc_workspace_name"}
        assert ws_ids == {"ws-a", "ws-b"}
        assert ws_names == {"alpha", "beta"}

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_STATEFILE_SRC}._download_statefile")
    @patch(f"{_STATEFILE_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_statefile_two_workspaces_merge(self, mock_client_cls, mock_src_resolve, mock_download, mock_list):
        mock_client_cls.return_value = Mock()
        mock_list.return_value = [("ws-a", "alpha"), ("ws-b", "beta")]
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")
        mock_download.side_effect = lambda client, ws_id: _make_resource_state([_aws_resource("web", [{"attributes": {"public_ip": f"{ws_id}-ip"}}])])

        plugin = _make_cache_plugin(
            _base_options(
                source="statefile",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert mock_download.call_count == 2
        # Both workspaces own aws_instance.web. Without cross-workspace
        # disambiguation the two would collapse onto a single Ansible host;
        # assert two distinct hosts, each suffixed with its workspace name.
        added_hosts = {c.args[0] for c in plugin.inventory.add_host.call_args_list}
        assert added_hosts == {"aws_instance_web_alpha", "aws_instance_web_beta"}

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_parallel_mode_same_result_as_sequential(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        mock_client_cls.return_value = Mock()
        mock_list.return_value = [("ws-a", "alpha"), ("ws-b", "beta"), ("ws-c", "gamma")]
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")
        mock_fetch.side_effect = lambda c, ws: [{"name": "ansible_host", "value": f"{ws}-h", "sensitive": False}]

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
                enable_parallel_processing=True,
                concurrency=3,
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        assert mock_fetch.call_count == 3

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_zero_matched_workspaces_warns_and_returns_empty(self, mock_client_cls, mock_list):
        mock_client_cls.return_value = Mock()
        mock_list.return_value = []

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-empty"},
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # No hosts added — set_variable never called.
        plugin.inventory.set_variable.assert_not_called()


class TestMultiWorkspaceCaching:
    """Selector and per-workspace caching, default (offline-friendly) mode."""

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_selector_cache_miss_writes_selector_and_per_workspace_blobs(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        mock_client_cls.return_value = Mock()
        mock_list.return_value = [("ws-a", "alpha"), ("ws-b", "beta")]
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")
        mock_fetch.side_effect = lambda c, ws: [{"name": "ansible_host", "value": f"{ws}-h", "sensitive": False}]

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
                cache=True,
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        sel_key = _selector_key("outputs", "my-org", {"project_id": "prj-x"})
        assert sel_key in plugin._cache
        assert plugin._cache[sel_key]["schema"] == "tfc_inv_selector_v1"
        assert _per_ws_key("outputs", "ws-a") in plugin._cache
        assert _per_ws_key("outputs", "ws-b") in plugin._cache

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_selector_and_per_workspace_cache_hit_skips_all_api_calls(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        """The offline-friendly contract: with both layers warm, ZERO API
        calls happen and no TerraformClient is constructed in the workers."""
        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
                cache=True,
            )
        )
        # Pre-seed selector + per-workspace blobs.
        plugin._cache[_selector_key("outputs", "my-org", {"project_id": "prj-x"})] = {
            "schema": "tfc_inv_selector_v1",
            "targets": [["ws-a", "alpha"], ["ws-b", "beta"]],
        }
        plugin._cache[_per_ws_key("outputs", "ws-a")] = _v1_blob(
            "outputs",
            data=[{"name": "ansible_host", "value": "alpha-h", "sensitive": False}],
            workspace_id="ws-a",
            workspace_name="alpha",
        )
        plugin._cache[_per_ws_key("outputs", "ws-b")] = _v1_blob(
            "outputs",
            data=[{"name": "ansible_host", "value": "beta-h", "sensitive": False}],
            workspace_id="ws-b",
            workspace_name="beta",
        )

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=True)

        # No workspace listing, no per-workspace fetch, no client construction.
        mock_list.assert_not_called()
        mock_fetch.assert_not_called()
        mock_client_cls.assert_not_called()
        mock_src_resolve.assert_not_called()

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_flush_cache_skips_reads_writes_fresh_layers(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        """--flush-cache (cache=False at runtime) must skip both layers' reads
        but still write fresh data into both."""
        mock_client_cls.return_value = Mock()
        mock_list.return_value = [("ws-a", "alpha")]
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")
        mock_fetch.return_value = [{"name": "ansible_host", "value": "fresh", "sensitive": False}]

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
                cache=True,
            )
        )
        # Pre-seed stale entries that should be overwritten.
        plugin._cache[_selector_key("outputs", "my-org", {"project_id": "prj-x"})] = {
            "schema": "tfc_inv_selector_v1",
            "targets": [["ws-STALE", "stale"]],
        }
        plugin._cache[_per_ws_key("outputs", "ws-a")] = _v1_blob(
            "outputs",
            data=[{"name": "ansible_host", "value": "stale", "sensitive": False}],
            workspace_id="ws-a",
            workspace_name="alpha",
        )

        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml", cache=False)

        # Reads skipped → live list + live fetch.
        mock_list.assert_called_once()
        mock_fetch.assert_called_once()
        # Both layers refreshed.
        assert plugin._cache[_selector_key("outputs", "my-org", {"project_id": "prj-x"})]["targets"] == [["ws-a", "alpha"]]
        assert plugin._cache[_per_ws_key("outputs", "ws-a")]["data"] == [{"name": "ansible_host", "value": "fresh", "sensitive": False}]


class TestMultiWorkspaceValidationMode:
    """cache_validate_current_state_version with multiple workspaces."""

    @patch(f"{_INV_MODULE}.list_workspaces")
    @patch(f"{_OUTPUTS_SRC}.fetch_outputs")
    @patch(f"{_OUTPUTS_SRC}.resolve_workspace")
    @patch(f"{_INV_MODULE}.TerraformClient")
    def test_sv_id_failure_skips_one_workspace_others_continue(self, mock_client_cls, mock_src_resolve, mock_fetch, mock_list):
        """One workspace's read_current() raises → that workspace is excluded
        with a warning; the other workspace's inventory still appears."""
        mock_list.return_value = [("ws-good", "good"), ("ws-bad", "bad")]
        mock_src_resolve.side_effect = AssertionError("resolve_workspace should not run on multi-mode")
        mock_fetch.return_value = [{"name": "ansible_host", "value": "good-h", "sensitive": False}]

        # The TerraformClient context manager returns a client whose
        # state_versions.read_current succeeds for ws-good but fails for ws-bad.
        def _build_client(_options):
            cm = Mock()
            client = Mock()

            def _read_current(ws_id):
                if ws_id == "ws-good":
                    return Mock(id="sv-1")
                raise RuntimeError("network error")

            client.client.state_versions.read_current.side_effect = _read_current
            cm.__enter__ = Mock(return_value=client)
            cm.__exit__ = Mock(return_value=False)
            return cm

        mock_client_cls.from_mapping.side_effect = _build_client
        mock_client_cls.return_value = Mock()  # selector-cache miss path also constructs the client

        plugin = _make_cache_plugin(
            _base_options(
                source="outputs",
                workspace=None,
                workspace_filters={"project_id": "prj-x"},
                cache=True,
                cache_validate_current_state_version=True,
            )
        )
        with _parse_ctx(plugin):
            plugin.parse(Mock(), Mock(), "/fake/inventory.yml")

        # Only the good workspace got fetched; the bad one was skipped.
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args.args[1] == "ws-good"
