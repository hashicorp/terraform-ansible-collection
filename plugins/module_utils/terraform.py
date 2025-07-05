# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


import re
import json
from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible.errors import AnsibleError
from ansible.module_utils.urls import Request
from ansible.module_utils.six.moves.http_cookiejar import CookieJar
from typing import Optional, Dict, Any, Callable, List, Union
from .exceptions import (
    TerraformTokenNotFoundError,
    TerraformHostnameNotFoundError,
    TerraformSSLValidationError
)


class TerraformModule(AnsibleModule):
    AUTH_ARGSPEC = dict(
        tf_token=dict(
            required=False,
            fallback=(env_fallback, ["TF_TOKEN"]),
        ),
        tf_hostname=dict(
            required=False,
            default="app.terraform.io",
            fallback=(env_fallback, ["TF_HOSTNAME"]),
        ),
        tf_validate_certs=dict(
            required=True,
            fallback=(env_fallback, ["TF_VALIDATE_CERTS"]),
        ),
    )

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

        Args:
            response (dict or list): The response data to sanitize.
            keys_to_include (list): List of keys to keep in the response.

        Returns:
            dict or list: The sanitized response data.
        """

        if isinstance(response, dict):
            result = {}
            for k, v in response.items():
                if k in keys_to_include:
                    result[k] = self.sanitize_response(v, keys_to_include) if isinstance(v, (dict, list)) else v
                elif isinstance(v, (dict, list)):
                    nested = self.sanitize_response(v, keys_to_include)
                    if nested:
                        result[k] = nested
            return result or None

        elif isinstance(response, list):
            filtered = [self.sanitize_response(item, keys_to_include) for item in response]
            filtered = [item for item in filtered if item]
            return filtered or None

        else:
            return response

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
            raise AnsibleError(f"Failed to convert data to JSON: {e}")

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
            raise AnsibleError(f"Failed to decode JSON string: {e}")

    @staticmethod
    def make_request(function: Callable):
        """Decorator to handle API requests and responses."""
        def wrapper(self, path: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
            """
            Wrapper function to make API requests.

            Args:
                path (str): The API endpoint path.
                data (dict, optional): The data to send in the request body.
                **kwargs: Additional keyword arguments for the request.
            """
            method = function.__name__.upper()

            if not path.startswith("/"):
                path = f"/{path}"

            if method in ["POST", "PUT", "DELETE"] and data:
                data = self.dict_to_json(data)

            url = f"{self.base_url}{path}"
            response = self.session.open(
                method,
                url,
                data=data,
            )

            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                reason = getattr(response, "reason", "Unknown error")
                raise AnsibleError(
                    f"Failed to {method} {path}: {reason} ({status})"
                )

            result = self.json_to_dict(response.read())

            if kwargs.get("keys_to_include"):
                return self.sanitize_response(result, kwargs["keys_to_include"])

            return result
        return wrapper

    @make_request
    def get(self, path: str) -> Any:
        """
        Retrieve data from the specified API endpoint.

        Args:
            path (str): The API endpoint path to retrieve data from.

        Returns:
            dict: The response data from the API.

        Raises:
            AnsibleError: If the request fails due to network or server error.
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
            AnsibleError: If the request fails due to network or server error.
        """
        pass

    @make_request
    def put(self, path: str, data: Dict[str, Any]) -> Any:
        """ Send a PUT request to the specified API endpoint.

        Args:
            path (str): The API endpoint path where the data should be sent.
            data (dict, optional): The data payload to be sent in the request body. Defaults to None.

        Returns:
            Response: The response object resulting from the PUT request.

        Raises:
            AnsibleError: If the request fails due to network or server error.
        """
        pass

    @make_request
    def delete(self, path: str) -> None:
        """
        Deletes the specified resource at the given path.

        Args:
            path (str): The file system path to the file or directory to be deleted.

        Raises:
            AnsibleError: If the deletion fails due to network or server error.

        Returns:
            None

        """
        pass


class TerraformClient(ClientMixin):
    def __init__(self, **kwargs: Any) -> None:
        self.hostname: str = kwargs.get("tf_hostname", "app.terraform.io")
        self._token: str = (
            kwargs.get("tf_token") or self._get_token_from_config_file()
        )
        self.verify: bool = kwargs.get("tf_validate_certs", True)
        self.headers: Dict[str, str] = kwargs.get("headers", {})
        self.session_args: Dict[str, Any] = {
            "timeout": kwargs.get("timeout", 10),
            "validate_certs": self.verify,
            "headers": self.headers,
            "cookies": kwargs.get("cookies", CookieJar()),
            "follow_redirects": kwargs.get("follow_redirects", True),
        }
        self.session: Request = Request(**self.session_args)

        if not self.headers:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/vnd.api+json",
                },
            )

        elif "Authorization" not in self.headers:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self._token}"
                },
            )

        self.pre_checks()

    @property
    def base_url(self):
        """Construct the base URL for the Terraform API."""
        if re.match(r"^https?://", self.hostname):
            return f"{self.hostname}/api/v2"
        return f"https://{self.hostname}/api/v2"

    def _get_token_from_config_file(self):
        """
        Placeholder for reading the Terraform token from a config file.
        """
        # Implement logic to read from ~/.terraformrc or ~/.terraform.d/credentials.tfrc.json if needed
        pass

    def pre_checks(self):
        """Perform pre-checks to ensure the client is configured correctly."""
        if not self._token:
            raise TerraformTokenNotFoundError(
                "Terraform token not found. Set the TFE_TOKEN environment variable or pass it as an argument."
            )
        elif not self.hostname:
            raise TerraformHostnameNotFoundError(
                "Terraform hostname not found. Set the TF_HOSTNAME environment variable or pass it as an argument."
            )
        elif self.hostname.startswith("http://") and self.verify:
            raise TerraformSSLValidationError(
                "Invalid configuration: SSL verification is enabled (`TF_VALIDATE_CERTS=True`), "
                "but the URL starts with 'http://' (non-secure)"
            )