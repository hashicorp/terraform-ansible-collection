# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import re

from typing import Any, Callable, Dict, List, Optional, Union


try:
    import requests
    import requests.adapters

    from urllib3.util.retry import Retry

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None
    Retry = None

from ansible.module_utils.basic import AnsibleModule, env_fallback, missing_required_lib

from .exceptions import (
    TerraformHostnameNotFoundError,
    TerraformTokenNotFoundError,
)


# Constants
HTTP_URL_PATTERN = r"^https?://"


class TerraformModule(AnsibleModule):
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

    def __init__(
        self,
        argument_spec,
        bypass_checks=False,
        no_log=False,
        mutually_exclusive=None,
        required_together=None,
        required_one_of=None,
        add_file_common_args=False,
        supports_check_mode=False,
        required_if=None,
        required_by=None,
    ):
        """Initialize the module updating argspec with auth params."""
        argument_spec.update(TerraformModule.AUTH_ARGSPEC)
        super().__init__(
            argument_spec,
            bypass_checks,
            no_log,
            mutually_exclusive,
            required_together,
            required_one_of,
            add_file_common_args,
            supports_check_mode,
            required_if,
            required_by,
        )


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
            )

            # At this point, retries have already been handled by the session
            # If we still have an error status, retries were exhausted
            status = getattr(response, "status_code", 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"Failed to {method} {path} after retries: {response.json()}")

            if response.content and content_type.endswith("json"):
                result = self.json_to_dict(response.content)
            else:
                result = response.content

            if kwargs.get("keys_to_include"):
                result = self.sanitize_response(result, kwargs["keys_to_include"])

            return {"status": status, "data": result}

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
        if not HAS_REQUESTS or not requests or not Retry:
            raise ImportError(missing_required_lib("requests"))

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
        self.headers: Dict[str, str] = kwargs.get("headers", {})
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
