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
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.outputs import OutputsSource, _collect_hosts_from_spec, parse_type
from ansible_collections.hashicorp.terraform.plugins.module_utils.inventory.sources.search import SearchSource
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
        "hostvars_prefix": "",
        "hostvars_suffix": "",
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
        assert records[0]["host_vars"] == {"ip": "10.0.0.1"}
        assert records[1]["index"] == 1
        assert records[1]["host_vars"] == {"ip": "10.0.0.2"}

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
        plugin.inventory.set_variable.assert_any_call("my-ws_web_server", "env", "prod")

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

    def test_source_search_raises_not_implemented(self):
        plugin = _make_plugin(_base_options(source="search"))
        with _parse_ctx(plugin):
            with pytest.raises(AnsibleParserError, match="not yet implemented"):
                plugin.parse(Mock(), Mock(), "/fake/inventory.yml")
