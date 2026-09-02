# -*- coding: utf-8 -*-

# Copyright IBM Corp. 2025, 2026
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for plugins/modules/stack_info.py."""

from unittest.mock import Mock, patch

from ansible_collections.hashicorp.terraform.plugins.modules.stack_info import main

MODULE_PATH = "ansible_collections.hashicorp.terraform.plugins.modules.stack_info"


class TestStackInfoMain:
    """Tests for the stack_info module's main() dispatch logic."""

    def test_lookup_by_id_found(self):
        stack = {"id": "st-1", "name": "stack-a"}
        mod = Mock()
        mod.params = {"stack_id": "st-1"}
        mod.check_mode = False
        mod.exit_json = Mock(side_effect=SystemExit(0))
        mod.fail_json = Mock(side_effect=SystemExit(1))

        adapter = Mock()
        mock_client_ctx = Mock()
        mock_client_ctx.__enter__ = Mock(return_value=adapter)
        mock_client_ctx.__exit__ = Mock(return_value=False)
        mod.client = Mock(return_value=mock_client_ctx)

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=mod),
            patch(f"{MODULE_PATH}.get_stack", return_value=stack),
        ):
            try:
                main()
            except SystemExit:
                pass

        mod.exit_json.assert_called_once()
        assert mod.exit_json.call_args[1]["stack"] == stack

    def test_lookup_by_id_not_found(self):
        """Raises ValueError (fail_json) when stack_id is not found."""
        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule") as mock_cls,
            patch(f"{MODULE_PATH}.get_stack", return_value=None),
        ):
            mod = Mock()
            mod.params = {"stack_id": "st-missing"}
            mod.check_mode = False
            mod.fail_json = Mock(side_effect=SystemExit(1))
            mod.exit_json = Mock(side_effect=SystemExit(0))
            mock_cls.return_value = mod

            adapter = Mock()
            mock_client_ctx = Mock()
            mock_client_ctx.__enter__ = Mock(return_value=adapter)
            mock_client_ctx.__exit__ = Mock(return_value=False)
            mod.client = Mock(return_value=mock_client_ctx)

            with patch(f"{MODULE_PATH}.get_stack", return_value=None):
                try:
                    main()
                except SystemExit:
                    pass

            mod.fail_json.assert_called_once()
            assert "not found" in mod.fail_json.call_args[1]["msg"]

    def test_lookup_by_name_and_organization_found(self):
        stack = {"id": "st-1", "name": "stack-a"}
        mod = Mock()
        mod.params = {"organization": "org", "name": "stack-a"}
        mod.check_mode = False
        mod.exit_json = Mock(side_effect=SystemExit(0))
        mod.fail_json = Mock(side_effect=SystemExit(1))

        adapter = Mock()
        mock_client_ctx = Mock()
        mock_client_ctx.__enter__ = Mock(return_value=adapter)
        mock_client_ctx.__exit__ = Mock(return_value=False)
        mod.client = Mock(return_value=mock_client_ctx)

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=mod),
            patch(f"{MODULE_PATH}.get_stack_by_name", return_value=stack),
        ):
            try:
                main()
            except SystemExit:
                pass

        mod.exit_json.assert_called_once()
        assert mod.exit_json.call_args[1]["stack"] == stack

    def test_lookup_by_name_not_found(self):
        """Raises ValueError (fail_json) when name lookup yields None."""
        mod = Mock()
        mod.params = {"organization": "org", "name": "missing-stack"}
        mod.check_mode = False
        mod.exit_json = Mock(side_effect=SystemExit(0))
        mod.fail_json = Mock(side_effect=SystemExit(1))

        adapter = Mock()
        mock_client_ctx = Mock()
        mock_client_ctx.__enter__ = Mock(return_value=adapter)
        mock_client_ctx.__exit__ = Mock(return_value=False)
        mod.client = Mock(return_value=mock_client_ctx)

        with (
            patch(f"{MODULE_PATH}.AnsibleTerraformModule", return_value=mod),
            patch(f"{MODULE_PATH}.get_stack_by_name", return_value=None),
        ):
            try:
                main()
            except SystemExit:
                pass

        mod.fail_json.assert_called_once()
        assert "not found" in mod.fail_json.call_args[1]["msg"]
