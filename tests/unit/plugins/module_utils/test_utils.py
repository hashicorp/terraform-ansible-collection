import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import TerraformError
from ansible_collections.hashicorp.terraform.plugins.module_utils.utils import dict_diff, sort_list


class TestUtils:
    """Parameterized test cases for DataUtils utility methods."""

    @pytest.mark.parametrize(
        "input_list,expected",
        [
            ([{"key2": "value2", "key1": "value1"}, {"key1": "value1", "key2": "value2"}]),
            ([{"name": "zeta", "code": "alpha"}, {"code": "alpha", "name": "zeta"}]),
        ],
    )
    def test_sort_list_with_dicts(self, input_list, expected):
        assert sort_list(input_list) == expected

    @pytest.mark.parametrize(
        "input_list",
        [
            [{"key1": "value1", "key2": "value2"}, {"key1": "value2", "key3": "value3"}],
            [{"foo": "bar"}, {"baz": "qux"}],
        ],
    )
    def test_sort_list_with_dicts_inconsistent_keys_raises(self, input_list):
        with pytest.raises(ValueError, match="dictionaries do not match"):
            sort_list(input_list)

    @pytest.mark.parametrize("input_val", ["just a string", {"key": "value"}, None])
    def test_sort_list_with_non_list_returns_input(self, input_val):
        assert sort_list(input_val) == input_val

    @pytest.mark.parametrize(
        "base,comparable,expected",
        [
            ({"key1": "value1", "key2": "value2"}, {"key1": "value1", "key2": "different_value"}, {"key2": "different_value"}),
            ({"key1": "value1", "key2": "value2"}, {"key1": "value1"}, {}),
            ({"key1": "value1"}, {"key1": "value1", "key2": "value2"}, {"key2": "value2"}),
            (
                {"key1": {"subkey1": "subvalue1", "subkey2": "subvalue2"}, "key2": "value3"},
                {"key1": {"subkey1": "subvalue1", "subkey2": "DIFFERENT"}, "key2": "value3"},
                {"key1": {"subkey2": "DIFFERENT"}},
            ),
            ({"key1": ["value1", "value2", "value3"]}, {"key1": ["value3", "value2", "value1"]}, {}),  # lists sorted equal, no diff
            ({"key1": ["value1", "value2", "value3"]}, {"key1": ["new1", "new2", "new3"]}, {"key1": ["new1", "new2", "new3"]}),
            ({}, {"newkey": "newvalue"}, {"newkey": "newvalue"}),
        ],
    )
    def test_dict_diff_valid_cases(self, base, comparable, expected):
        assert dict_diff(base, comparable) == expected

    @pytest.mark.parametrize(
        "base",
        [
            "not a dict",
            ["list"],
            None,
        ],
    )
    def test_dict_diff_base_not_dict_raises(self, base):
        with pytest.raises(TerraformError, match="`base` must be of type <dict>"):
            dict_diff(base, {"key1": "value1"})

    @pytest.mark.parametrize("comparable", ["not a dict", ["list"], 123])
    def test_dict_diff_comparable_not_dict_raises(self, comparable):
        with pytest.raises(TerraformError, match="`comparable` must be of type <dict>"):
            dict_diff({"key1": "value1"}, comparable)

    def test_dict_diff_comparable_none(self):
        base = {"key1": "value1"}
        assert dict_diff(base, None) == {}
