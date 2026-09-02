# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/module_utils/reserved_tag_keys.py."""

from unittest.mock import Mock

from ansible_collections.hashicorp.terraform.plugins.module_utils.reserved_tag_keys import (
    create_reserved_tag_key,
    delete_reserved_tag_key,
    get_reserved_tag_key,
    get_reserved_tag_key_by_key,
    try_delete_reserved_tag_key,
    update_reserved_tag_key,
)


class TestGetReservedTagKey:
    def test_get_by_id(self):
        # get_reserved_tag_key returns None since pytfe doesn't provide read()
        adapter = Mock()
        result = get_reserved_tag_key(adapter, "rtk-1")
        assert result is None

    def test_not_found_returns_none(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.reserved_tag_keys.read.side_effect = NotFound("not found")
        result = get_reserved_tag_key(adapter, "rtk-missing")
        assert result is None


class TestGetReservedTagKeyByKey:
    def test_get_by_key(self):
        from pytfe.models import ReservedTagKey

        adapter = Mock()
        adapter.client.reserved_tag_key.list.return_value = iter(
            [
                ReservedTagKey(id="rtk-1", key="environment", disable_overrides=True),
                ReservedTagKey(id="rtk-2", key="team", disable_overrides=False),
            ]
        )
        result = get_reserved_tag_key_by_key(adapter, "my-org", "environment")
        assert result is not None
        assert result["key"] == "environment"
        adapter.client.reserved_tag_key.list.assert_called_once_with("my-org")

    def test_not_found_returns_none(self):
        from pytfe.models import ReservedTagKey

        adapter = Mock()
        rtk = ReservedTagKey(id="rtk-1", key="team", disable_overrides=False)
        adapter.client.reserved_tag_key.list.return_value = [rtk]
        result = get_reserved_tag_key_by_key(adapter, "my-org", "environment")
        assert result is None

    def test_not_found_exception_returns_none(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.reserved_tag_key.list.side_effect = NotFound("not found")
        result = get_reserved_tag_key_by_key(adapter, "my-org", "environment")
        assert result is None


class TestCreateReservedTagKey:
    def test_create(self):
        from pytfe.models import ReservedTagKey, ReservedTagKeyCreateOptions

        adapter = Mock()
        adapter.client.reserved_tag_key.create.return_value = ReservedTagKey(
            id="rtk-new",
            key="environment",
            disable_overrides=True,
        )
        result = create_reserved_tag_key(adapter, "my-org", {"key": "environment", "disable_overrides": True})
        assert result["id"] == "rtk-new"
        assert result["key"] == "environment"
        assert result["disable_overrides"] is True
        adapter.client.reserved_tag_key.create.assert_called_once()
        # Verify that model_validate was called on the options
        call_args = adapter.client.reserved_tag_key.create.call_args
        assert call_args[0][0] == "my-org"
        assert isinstance(call_args[0][1], ReservedTagKeyCreateOptions)


class TestUpdateReservedTagKey:
    def test_update(self):
        from pytfe.models import ReservedTagKey, ReservedTagKeyUpdateOptions

        adapter = Mock()
        adapter.client.reserved_tag_key.update.return_value = ReservedTagKey(
            id="rtk-1",
            key="environment",
            disable_overrides=False,
        )
        result = update_reserved_tag_key(adapter, "rtk-1", {"disable_overrides": False})
        assert result["id"] == "rtk-1"
        assert result["disable_overrides"] is False
        adapter.client.reserved_tag_key.update.assert_called_once()
        # Verify that model_validate was called on the options
        call_args = adapter.client.reserved_tag_key.update.call_args
        assert call_args[0][0] == "rtk-1"
        assert isinstance(call_args[0][1], ReservedTagKeyUpdateOptions)


class TestDeleteReservedTagKey:
    def test_delete(self):
        adapter = Mock()
        delete_reserved_tag_key(adapter, "rtk-1")
        adapter.client.reserved_tag_key.delete.assert_called_once_with("rtk-1")


class TestTryDeleteReservedTagKey:
    def test_returns_true_when_deleted(self):
        adapter = Mock()
        result = try_delete_reserved_tag_key(adapter, "rtk-1")
        assert result is True
        adapter.client.reserved_tag_key.delete.assert_called_once_with("rtk-1")

    def test_returns_false_when_not_found(self):
        from pytfe.errors import NotFound

        adapter = Mock()
        adapter.client.reserved_tag_key.delete.side_effect = NotFound("not found")
        result = try_delete_reserved_tag_key(adapter, "rtk-missing")
        assert result is False
