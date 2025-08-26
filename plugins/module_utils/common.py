# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import re
import traceback

from typing import Any, Callable, Dict, List, Optional, Union

from ansible.module_utils.six import iteritems


try:
    import requests
    import requests.adapters

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from urllib3.util.retry import Retry

    HAS_URLLIB3 = True
except ImportError:
    HAS_URLLIB3 = False

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.compat.version import LooseVersion

from .exceptions import (
    TerraformError,
    TerraformHostnameNotFoundError,
    TerraformTokenNotFoundError,
)


# Constants
HTTP_URL_PATTERN = r"^https?://"


class AnsibleTerraformModule(AnsibleModule):
    """Ansible module class for hashicorp.terraform modules."""

    DEFAULT_SETTINGS = {
        "check_requests": True,
        "module_class": AnsibleModule,
    }

    AUTH_ARGSPEC = {
        "tf_token": {
            "required": False,
            "fallback": (env_fallback, ["TF_TOKEN"]),
            "no_log": True,
        },
        "tf_hostname": {
            "required": False,
            "default": "https://app.terraform.io",
            "fallback": (env_fallback, ["TF_HOSTNAME"]),
        },
        "tf_validate_certs": {
            "type": "bool",
            "fallback": (env_fallback, ["TF_VALIDATE_CERTS"]),
            "default": True,
        },
        "tf_max_retries": {
            "required": False,
            "type": "int",
            "fallback": (env_fallback, ["TF_MAX_RETRIES"]),
            "default": 3,
        },
        "tf_timeout": {
            "required": False,
            "type": "int",
            "fallback": (env_fallback, ["TF_TIMEOUT"]),
            "default": 10,
        },
    }

    def __init__(self, **kwargs) -> None:
        local_settings = {}
        for key in AnsibleTerraformModule.DEFAULT_SETTINGS:
            try:
                local_settings[key] = kwargs.pop(key)
            except KeyError:
                local_settings[key] = AnsibleTerraformModule.DEFAULT_SETTINGS[key]
        self.settings = local_settings

        kwargs["argument_spec"].update(self.AUTH_ARGSPEC)

        self._module = self.settings["module_class"](**kwargs)

        if self.settings["check_requests"]:
            self.requires("requests")

    @property
    def check_mode(self):
        return self._module.check_mode

    @property
    def _diff(self):
        return self._module._diff

    @property
    def _name(self):
        return self._module._name

    @property
    def params(self):
        return self._module.params

    def warn(self, *args, **kwargs):
        return self._module.warn(*args, **kwargs)

    def deprecate(self, *args, **kwargs):
        return self._module.deprecate(*args, **kwargs)

    def debug(self, *args, **kwargs):
        return self._module.debug(*args, **kwargs)

    def exit_json(self, *args, **kwargs):
        return self._module.exit_json(*args, **kwargs)

    def fail_json(self, *args, **kwargs):
        return self._module.fail_json(*args, **kwargs)

    def fail_from_exception(self, exception):
        msg = to_text(exception)
        tb = "".join(
            traceback.format_exception(None, exception, exception.__traceback__),
        )
        return self.fail_json(msg=msg, exception=tb)

    def requires(
        self,
        dependency: str,
        minimum: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        try:
            requires(dependency, minimum, reason=reason)
        except Exception as e:
            self.fail_json(msg=to_text(e))


def requires(
    dependency: str,
    minimum: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    """Fail if a specific dependency is not present at a minimum version.

    If a minimum version is not specified it will require only that the
    dependency is present. This function raises an exception when the
    dependency is not found at the required version.

    Args:
        dependency (str): The name of the required package/dependency to check.
        minimum (str, optional): The minimum version required for the dependency.
                                If None, only checks that the dependency is present.
                                Defaults to None.
        reason (str, optional): Additional context or reason why this dependency
                               is required. Used in error messages. Defaults to None.

    Returns:
        None: This function does not return a value.

    Raises:
        Exception: If the dependency is not found or does not meet the minimum
                  version requirement.
    """
    if not has_at_least(dependency, minimum):
        if minimum is not None:
            lib = "{0}>={1}".format(dependency, minimum)
        else:
            lib = dependency
        raise TerraformError(missing_required_lib(lib, reason=reason))


def has_at_least(dependency: str, minimum: Optional[str] = None) -> bool:
    """Check if a dependency is present and meets minimum version requirements.

    Performs a comprehensive check to determine if the specified package is
    available and optionally validates it meets or exceeds a minimum version.
    Uses semantic version comparison for accurate version checking.

    Args:
        dependency (str): The name of the package to check. Must be a valid
                         Python package name that can be imported.
        minimum (str, optional): The minimum version requirement in semantic
                                version format (e.g., "1.2.3", "2.0.0").
                                If None, only verifies package presence.
                                Defaults to None.

    Returns:
        bool: True if the dependency is present and meets version requirements,
              False otherwise. Returns False for any import or version parsing
              errors to fail safely.

    Note:
        This function is designed to fail gracefully - any errors during
        package discovery or version parsing will result in False being
        returned rather than raising exceptions.
    """
    result = False

    try:
        # Retrieve available dependency versions
        available_packages = gather_versions([dependency])
        current_version = available_packages.get(dependency)

        # Check if dependency was found and version is discoverable
        if current_version is not None:
            # If no minimum version specified, dependency presence is sufficient
            if minimum is None:
                result = True
            else:
                # Perform semantic version comparison
                result = LooseVersion(current_version) >= LooseVersion(minimum)

    except Exception:
        # If for some reason the validation fails, result remains False
        result = False

    return result


def gather_versions(packages: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Gather version information for specified packages.

    Args:
        packages (list, optional): List of package names to check.
                                   If None, uses a default set of common packages.

    Returns:
        dict: Dictionary mapping package names to their versions.
    """
    if packages is None:
        packages = ["requests"]

    versions = {}

    for package_name in packages:
        try:
            # Import the package
            package = __import__(package_name)

            # Try different common version attributes
            version = None
            for attr in ["__version__", "version", "VERSION"]:
                if hasattr(package, attr):
                    version = getattr(package, attr)
                    break

            if version:
                versions[package_name] = to_text(version)

        except ImportError:
            # Package not available, skip it
            pass
        except Exception:
            # Any other error, skip this package
            pass

    return versions


class ClientMixin:
    """
    Mixin class to provide common client functionality.
    This can be used to extend the TerraformClient class with additional methods.
    """

    def sanitize_response(self, response: Union[Dict[str, Any], List[Any]], keys_to_include: List[str]) -> Any:
        """
        Sanitize the response by retaining only specified keys, recursively.

        This method traverses through nested dictionaries and lists,
        filtering out only the keys specified in the `keys_to_include` list.

        Args:
            response (dict or list): The response data to sanitize.
            keys_to_include (list): List of keys to keep in the response.

        Returns:
            dict, list, or None: The sanitized response structure with only the allowed keys,
                                or None if no valid keys remain.
        """
        if isinstance(response, dict):
            return self._sanitize_dict(response, keys_to_include)

        if isinstance(response, list):
            return self._sanitize_list(response, keys_to_include)

        return response

    def _sanitize_dict(self, data: Dict[str, Any], keys_to_include: List[str]) -> Union[Dict[str, Any], None]:
        """
        Recursively sanitize a dictionary by retaining only specified keys.

        Args:
            data (dict): The dictionary to sanitize.
            keys_to_include (list): Keys to retain in the sanitized result.

        Returns:
            dict or None: Sanitized dictionary or None if no keys matched or nested matches found.
        """
        result = {}

        for key, value in data.items():
            if key in keys_to_include:
                result[key] = self.sanitize_response(value, keys_to_include) if isinstance(value, (dict, list)) else value
            elif isinstance(value, (dict, list)):
                nested = self.sanitize_response(value, keys_to_include)
                if nested:
                    result[key] = nested

        return result or None

    def _sanitize_list(self, data: List[Any], keys_to_include: List[str]) -> Union[List[Any], None]:
        """
        Recursively sanitize a list by applying sanitization to each element.

        Args:
            data (list): The list to sanitize.
            keys_to_include (list): Keys to retain from each dictionary/list element.

        Returns:
            list or None: A sanitized list with relevant keys retained in each element,
                        or None if all elements were filtered out.
        """
        sanitized = [self.sanitize_response(item, keys_to_include) for item in data]
        sanitized = [item for item in sanitized if item]
        return sanitized or None

    def dict_to_json(self, data: Dict) -> str:
        """
        Convert data to a JSON string.

        Args:
            data (Any): The data to convert to JSON.

        Returns:
            str: The JSON string representation of the data.
        """
        try:
            return json.dumps(data)
        except TypeError as e:
            raise ValueError(f"Failed to convert data to JSON: {e}") from e

    def json_to_dict(self, json_str: Union[bytes, str]) -> Dict[str, Any]:
        """
        Convert a JSON string to a Python object.

        Args:
            json_str (str): The JSON string to convert.

        Returns:
            Any: The Python object representation of the JSON string.
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON string: {e}") from e

    @staticmethod
    def make_request(function: Callable):
        """Decorator to handle API requests and responses with retry on connection errors."""

        def wrapper(self, path: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
            """
            Wrapper function to make API requests.

            Args:
                path (str): The API endpoint path.
                data (dict, optional): The data to send in the request body.
                **kwargs: Additional keyword arguments for the request.
            """
            method = function.__name__.upper()
            content_type = self.session.headers.get("Content-Type", "application/vnd.api+json")

            if method in ["POST", "PUT", "DELETE", "PATCH"] and data and content_type.endswith("json"):
                data = self.dict_to_json(data)

            if not re.match(HTTP_URL_PATTERN, path):
                url = f"{self.base_url}{path}"
            else:
                url = path

            # Let the session handle retries automatically
            # The retry mechanism is configured in create_session()
            response = self.session.request(
                method,
                url,
                data=data,
                timeout=self.timeout,
            )

            if response.content and content_type.endswith("json"):
                result = self.json_to_dict(response.content)
            else:
                result = response.content

            if kwargs.get("keys_to_include"):
                result = self.sanitize_response(result, kwargs["keys_to_include"])

            return {"status": response.status_code, "data": result}

        return wrapper

    def head(self, path: str) -> Any:
        """
        Send a HEAD request to the specified API endpoint.

        Args:
            path (str): The API endpoint path to send the request to.

        Returns:
            Response: The response object resulting from the HEAD request.

        Raises:
            Exception: If the request fails due to network or server error.
        """
        pass

    @make_request
    def get(self, path: str) -> Any:
        """
        Retrieve data from the specified API endpoint.

        Args:
            path (str): The API endpoint path to retrieve data from.

        Returns:
            dict: The response data from the API.

        Raises:
            Exception: If the request fails due to network or server error.
        """
        pass

    @make_request
    def post(self, path: str, data: Dict[str, Any]) -> Any:
        """
        Send a POST request to the specified API endpoint.

        Args:
            path (str): The API endpoint path to send the request to.
            data (dict): The payload to include in the POST request body. Defaults to None.

        Returns:
            Response: The response object resulting from the POST request.

        Raises:
            Exception: If the request fails due to network or server error.
        """
        pass

    @make_request
    def put(self, path: str, data: Dict[str, Any]) -> Any:
        """Send a PUT request to the specified API endpoint.

        Args:
            path (str): The API endpoint path where the data should be sent.
            data (dict, optional): The data payload to be sent in the request body. Defaults to None.

        Returns:
            Response: The response object resulting from the PUT request.

        Raises:
            Exception: If the request fails due to network or server error.
        """
        pass

    @make_request
    def patch(self, path: str, data: Dict[str, Any]) -> Any:
        """
        Send a PATCH request to the specified API endpoint.

        Args:
            path (str): The API endpoint path where the data should be sent.
            data (dict): The data payload to be sent in the request body.

        Returns:
            Response: The response object resulting from the PATCH request.

        Raises:
            Exception: If the request fails due to network or server error.
        """
        pass

    @make_request
    def delete(self, path: str) -> None:
        """
        Deletes the specified resource at the given path.

        Args:
            path (str): The file system path to the file or directory to be deleted.

        Raises:
            Exception: If the deletion fails due to network or server error.

        Returns:
            None

        """
        pass

    def pre_checks(self):
        """Perform pre-checks to ensure the client is configured correctly."""
        if not isinstance(self, ArchivistClient) and not self._token:
            raise TerraformTokenNotFoundError("Terraform token not found. Set the TF_TOKEN environment variable or pass it as the tf_token module argument.")
        elif not self.hostname:
            raise TerraformHostnameNotFoundError("Terraform hostname not found. Set the TF_HOSTNAME environment variable or pass it as an argument.")

    def create_session(self, **kwargs: Any) -> Any:
        """
        Create a requests session with the specified parameters.
        This method can be overridden to customize session creation.
        """
        if not HAS_REQUESTS:
            raise ImportError(missing_required_lib("requests"))
        if not HAS_URLLIB3:
            raise ImportError(missing_required_lib("urllib3"))

        self.session = requests.Session()
        self.url = kwargs.get("base_url")
        self.session.headers.update(kwargs.get("headers", {}))
        self.tf_max_retries = kwargs.get("tf_max_retries")
        self.timeout = kwargs.get("timeout")

        self.retry_strategy = Retry(
            total=self.tf_max_retries,
            connect=self.tf_max_retries,
            read=self.tf_max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "PUT", "DELETE"]),
            raise_on_status=False,
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=self.retry_strategy)

        self.session.verify = kwargs.get("validate_certs")

        if self.url.startswith("https://"):
            self.session.mount("https://", adapter)
        else:
            self.session.mount("http://", adapter)
        return self.session


class TerraformClient(ClientMixin):
    def __init__(self, **kwargs: Any) -> None:
        self.hostname: str = kwargs.get("tf_hostname")
        self._token: str = kwargs.get("tf_token")
        self.verify: bool = kwargs.get("tf_validate_certs")

        self.headers: Dict[str, str] = kwargs.get("headers", {})
        self.session_args: Dict[str, Any] = {
            "timeout": kwargs.get("timeout"),
            "tf_max_retries": kwargs.get("tf_max_retries"),
            "validate_certs": self.verify,
            "headers": self.headers,
            "follow_redirects": kwargs.get("follow_redirects", True),
            "base_url": self.base_url,
        }

        self.session = self.create_session(**self.session_args)

        if not self.headers:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/vnd.api+json",
                },
            )

        elif "Authorization" not in self.headers:
            self.session.headers.update(
                {"Authorization": f"Bearer {self._token}"},
            )

        self.pre_checks()

    @property
    def base_url(self):
        """Construct the base URL for the Terraform API."""
        if re.match(HTTP_URL_PATTERN, self.hostname):
            return f"{self.hostname}/api/v2"
        return f"https://{self.hostname}/api/v2"


class ArchivistClient(ClientMixin):
    def __init__(self, **kwargs: Any) -> None:
        self.hostname: str = "archivist.terraform.io"
        self.verify: bool = kwargs.get("tf_validate_certs")
        self.headers: Dict[str, str] = {}
        self.session_args: Dict[str, Any] = {
            "timeout": kwargs.get("timeout"),
            "tf_max_retries": kwargs.get("tf_max_retries"),
            "validate_certs": self.verify,
            "headers": self.headers,
            "follow_redirects": kwargs.get("follow_redirects", True),
            "base_url": self.base_url,
        }
        self.session: Any = self.create_session(**self.session_args)
        if not self.headers:
            self.session.headers.update(
                {
                    "Content-Type": "application/octet-stream",
                },
            )
        self.pre_checks()

    @property
    def base_url(self):
        """Construct the base URL for the Terraform Archivist API."""
        if re.match(HTTP_URL_PATTERN, self.hostname):
            return f"{self.hostname}/v1"
        return f"https://{self.hostname}/v1"


class DataUtils:
    @classmethod
    def sort_list(self, val):
        if isinstance(val, list):
            if isinstance(val[0], dict):
                sorted_keys = [tuple(sorted(dict_.keys())) for dict_ in val]
                # All keys should be identical
                if len(set(sorted_keys)) != 1:
                    raise ValueError("dictionaries do not match")

                return sorted(val, key=lambda d: tuple(d[k] for k in sorted_keys[0]))
            return sorted(val)
        return val

    @classmethod
    def dict_diff(cls, base, comparable):
        """Generate a dict object of differences

        This function will compare two dict objects and return the difference
        between them as a dict object.  For scalar values, the key will reflect
        the updated value.  If the key does not exist in `comparable`, then then no
        key will be returned.  For lists, the value in comparable will wholly replace
        the value in base for the key.  For dicts, the returned value will only
        return keys that are different.

        :param base: dict object to base the diff on
        :param comparable: dict object to compare against base

        :returns: new dict object with differences
        """
        if not isinstance(base, dict):
            raise TerraformError("`base` must be of type <dict>")
        if not isinstance(comparable, dict):
            if comparable is None:
                comparable = dict()
            else:
                raise TerraformError("`comparable` must be of type <dict>")

        updates = dict()

        for key, value in iteritems(base):
            if isinstance(value, dict):
                item = comparable.get(key)
                if item is not None:
                    sub_diff = cls.dict_diff(value, comparable[key])
                    if sub_diff:
                        updates[key] = sub_diff
            else:
                comparable_value = comparable.get(key)
                if comparable_value is not None:
                    if cls.sort_list(base[key]) != cls.sort_list(comparable_value):
                        updates[key] = comparable_value

        for key in set(comparable.keys()).difference(base.keys()):
            updates[key] = comparable.get(key)

        return updates
