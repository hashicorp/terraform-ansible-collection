# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pytest configuration and fixtures for Terraform collection unit tests.

This file provides common fixtures and configuration that can be used
across all unit tests in the collection.
"""

from unittest.mock import Mock, patch

import pytest


class DummyModule:
    """A basic mock Ansible module for testing."""

    def __init__(self, params=None, check_mode=False):
        self.params = params or {}
        self.failed = False
        self.exit_args = None
        self.fail_args = None
        self.check_mode = check_mode
        self.changed = False

    def fail_json(self, **kwargs):
        self.failed = True
        self.fail_args = kwargs
        msg = kwargs.get("msg", "fail_json called with no message")
        raise AssertionError(msg)

    def exit_json(self, **kwargs):
        self.exit_args = kwargs
        if "changed" in kwargs:
            self.changed = kwargs["changed"]
        raise SystemExit(kwargs)


class EnhancedDummyModule(DummyModule):
    """A mock Ansible module with enhanced tracking for better test inspection."""

    def __init__(self, params=None, check_mode=False):
        super().__init__(params, check_mode)
        self.call_history = []
        self.warnings = []
        self.deprecations = []
        self.debug_messages = []

    def warn(self, warning):
        self.warnings.append(warning)
        self.call_history.append(("warn", warning))

    def deprecate(self, msg, version=None):
        self.deprecations.append({"msg": msg, "version": version})
        self.call_history.append(("deprecate", msg, version))

    def debug(self, msg):
        self.debug_messages.append(msg)
        self.call_history.append(("debug", msg))

    def fail_json(self, **kwargs):
        self.call_history.append(("fail_json", kwargs))
        super().fail_json(**kwargs)

    def fail_from_exception(self, exception):
        self.call_history.append(("fail_from_exception", str(exception)))
        self.failed = True
        self.fail_args = {"msg": str(exception)}
        raise AssertionError(f"fail_from_exception called with: {exception}")

    def exit_json(self, **kwargs):
        self.call_history.append(("exit_json", kwargs))
        super().exit_json(**kwargs)


@pytest.fixture
def dummy_module():
    """Factory fixture to create DummyModule with custom parameters."""

    def _create_module(params=None, check_mode=False, enhanced=False):
        if enhanced:
            return EnhancedDummyModule(params, check_mode)
        return DummyModule(params, check_mode)

    return _create_module


@pytest.fixture
def enhanced_dummy_module():
    """Provide an EnhancedDummyModule instance for testing."""
    return EnhancedDummyModule()


@pytest.fixture
def mock_terraform_client():
    """
    Mock TerraformClient class fixture with pre-configured HTTP responses.

    Returns:
        Mock: A mock TerraformClient class that returns a fully configured mock instance
    """
    with patch("ansible_collections.hashicorp.terraform.plugins.module_utils.common.TerraformClient") as mock_class:
        mock_instance = Mock()
        mock_instance.hostname = "app.terraform.io"
        mock_instance.base_url = "https://app.terraform.io/api/v2"
        mock_instance.session = Mock()

        # Set up common session methods with default successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "test-id"}}
        mock_response.raise_for_status.return_value = None

        mock_instance.session.get.return_value = mock_response
        mock_instance.session.post.return_value = mock_response
        mock_instance.session.patch.return_value = mock_response
        mock_instance.session.delete.return_value = mock_response

        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_time():
    """
    Mock time.sleep and time.time for tests that involve timing.

    Returns:
        dict: Dictionary with 'sleep' and 'time' mock objects

    Usage:
        def test_timeout(mock_time):
            mock_time['time'].side_effect = [0, 30, 60]  # Simulate time progression
            mock_time['sleep'].return_value = None  # No actual sleeping
    """
    with patch("time.sleep") as mock_sleep, patch("time.time") as mock_time_func:

        mock_sleep.return_value = None  # Don't actually sleep
        mock_time_func.side_effect = range(1000)  # Incrementing time

        yield {"sleep": mock_sleep, "time": mock_time_func}
