# -*- coding: utf-8 -*-

# Copyright (c) 2025 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible_collections.hashicorp.terraform.plugins.module_utils.common import TerraformClient
from ansible_collections.hashicorp.terraform.plugins.module_utils.exceptions import (
    TerraformError,
)
from ansible.module_utils.six import iteritems


def get_workspace(client: TerraformClient, organization: str, workspace_name: str):
    """
    Retrieves a specified workspace from Terraform Cloud.

    Sends a GET request to fetch details of a workspace identified by its name
    within a given organization. If the workspace is not found, returns an empty
    dictionary. If successful, returns the workspace data with an added "status" field.
    For any other error status, raises an HTTPError.

    Args:
        client (TerraformClient): An authenticated client used to interact with
            the Terraform Cloud API.
        organization (str): The name of the Terraform Cloud organization.
        workspace_name (str): The name of the workspace to retrieve.

    Returns:
        dict: A dictionary containing the workspace data (with an added "status" field)
        if found, or an empty dictionary if the workspace is not found (status 404).

    Raises:
        TerraformError: If the request fails with a non-404 status code.
    """
    response = client.get(f"/organizations/{organization}/workspaces/{workspace_name}")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response_status == 404:
        # workspace was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # workspace was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def get_workspace_by_id(client: TerraformClient, workspace_id: str):
    """
    Retrieves a specified workspace from Terraform Cloud.

    Sends a GET request to fetch details of a workspace identified by id. If the workspace is not found, returns an empty
    dictionary. If successful, returns the workspace data with an added "status" field.
    For any other error status, raises an HTTPError.

    Args:
        client (TerraformClient): An authenticated client used to interact with
            the Terraform Cloud API.
        organization (str): The name of the Terraform Cloud organization.
        workspace_name (str): The name of the workspace to retrieve.

    Returns:
        dict: A dictionary containing the workspace data (with an added "status" field)
        if found, or an empty dictionary if the workspace is not found (status 404).

    Raises:
        TerraformError: If the request fails with a non-404 status code.
    """
    response = client.get(f"/workspaces/{workspace_id}")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response_status == 404:
        # workspace was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # workspace was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def get_tag_bindings(client: TerraformClient, workspace_id: str):

    response = client.get(f"/workspaces/{workspace_id}/tag-bindings")
    response_data = response.get("data", {})
    response_status = response["status"]
    if response_status == 404:
        # workspace was not found
        # This should not raise an exception
        return {}
    elif response_status == 200:
        # workspace was fetched successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A failure status code was received when attempting to fetch the specified configuration version
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def create_workspace(client: TerraformClient, organization: str, data: dict):
    """
    Creates a new workspace for a specified Terraform Cloud workspace.

    Sends a POST request to the Terraform Cloud API to create a workspace
    associated with the given organization. If the operation is successful, returns the
    workspace data with the response status code included.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        organization (str): The name of the organization
        attributes (dict): A dictionary of attributes to include in the workspace payload.

    Returns:
        dict: The response data from Terraform Cloud, including the created
        workspace details.

    Raises:
        TerraformError: If the request fails (i.e., non-201 status code is returned).
    """
    response = client.post(f"/organizations/{organization}/workspaces", data=data)
    response_data = response.get("data", {})
    response_status = response["status"]
    if response_status == 201:
        # workspace was created successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A non-201 status code was received when attempting to create specified workspace
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def update_workspace(client: TerraformClient, workspace_id: str, data: dict):
    """
    Updates an existing workspace for a specified Terraform Cloud workspace.

    Sends a POST request to the Terraform Cloud API to update a workspace
    associated with the given organization. If the operation is successful, returns the
    workspace data with the response status code included.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        organization (str): The name of the organization
        workspace_id (Str): The ID of the workspace to update.
        attributes (dict): A dictionary of attributes to include in the workspace payload.

    Returns:
        dict: The response data from Terraform Cloud, including the created
        workspace details.

    Raises:
        TerraformError: If the request fails (i.e., non-200 status code is returned).
    """
    response = client.patch(f"/workspaces/{workspace_id}", data=data)
    response_data = response.get("data", {})
    response_status = response["status"]
    if response_status == 200:
        # workspace was created successfully
        response_data.update({"status": response_status})
        return response_data
    else:
        # A non-201 status code was received when attempting to update specified workspace
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def safe_delete_workspace(client: TerraformClient, workspace_id: str):
    """
    Safe deletes a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the safe delete action for a given workspace.
    If the workspace does not exist or the user lacks
    authorization, returns an empty dictionary. If the delete action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to safe delete.

    Returns:
        dict: Response data if the delete request is successfully initiated,
        or an empty dictionary if the workspace is not found.

    Raises:
        TerraformError: If the archive request fails with a non-404 or non-204 status code.
    """
    response = client.post(f"/workspaces/{workspace_id}/actions/safe-delete")
    response_status = response["status"]

    if response["status"] == 404:
        # Workspace was not found
        # This should not raise an exception
        return {}
    elif response["status"] == 204:
        # Delete process initiated successfully
        # returns the response payload
        return {"status": response_status}
    else:
        # Delete process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def force_delete_workspace(client: TerraformClient, workspace_id: str):
    """
    Force deletes a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the delete action for a given workspace.
    If the workspace does not exist or the user lacks
    authorization, returns an empty dictionary. If the delete action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to delete.

    Returns:
        dict: Response data if the delete request is successfully initiated,
        or an empty dictionary if the workspace is not found.

    Raises:
        TerraformError: If the archive request fails with a non-404 or non-204 status code.
    """
    response = client.delete(f"/workspaces/{workspace_id}")
    response_status = response["status"]

    if response["status"] == 404:
        # Workspace was not found
        # This should not raise an exception
        return {}
    elif response["status"] == 204:
        # Delete process initiated successfully
        # returns the response payload
        return {"status": response_status}
    else:
        # Delete process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def lock_workspace(client: TerraformClient, workspace_id: str, lock_reason: str):
    """
    Lock a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the lock action for a given workspace.
    If the workspace does not exist or the user lacks
    authorization, returns an empty dictionary. If the lock action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to safe delete.

    Returns:
        dict: Response data if the delete request is successfully initiated,
        or an empty dictionary if the workspace is not found.

    Raises:
        TerraformError: If the archive request fails with a non-404 or non-200 status code.
    """
    payload = {
        "reason": lock_reason,
    }
    response = client.post(f"/workspaces/{workspace_id}/actions/lock", data=payload)
    response_data = response.get("data", {})
    response_status = response["status"]

    if response["status"] == 404:
        # Workspace was not found
        # This should not raise an exception
        return {}

    elif response_status == 200:
        # workspace was locked successfully
        response_data.update({"status": response_status})
        return response_data

    else:
        # Lock process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def unlock_workspace(client: TerraformClient, workspace_id: str):
    """
    Unlock a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the unlock action for a given workspace.
    If the workspace does not exist or the user lacks
    authorization, returns an empty dictionary. If the unlock action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to safe delete.

    Returns:
        dict: Response data if the unlock request is successfully initiated,
        or an empty dictionary if the workspace is not found.

    Raises:
        TerraformError: If the unlock request fails with a non-404 or non-200 status code.
    """
    response = client.post(f"/workspaces/{workspace_id}/actions/unlock")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response["status"] == 404:
        # Workspace was not found
        # This should not raise an exception
        return {}

    elif response_status == 200:
        # workspace was unlocked successfully
        response_data.update({"status": response_status})
        return response_data

    else:
        # Lock process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def force_unlock_workspace(client: TerraformClient, workspace_id: str):
    """
    Force unlock a specified workspace in Terraform Cloud.

    Sends a POST request to initiate the force unlock action for a given workspace.
    If the workspace does not exist or the user lacks
    authorization, returns an empty dictionary. If the force unlock action is
    successfully initiated, returns the response data. Raises an HTTPError if the
    request fails for any reason other than a 404 Not Found.

    Args:
        client (TerraformClient): An authenticated client instance used to interact
            with the Terraform Cloud API.
        workspace_id (str): The ID of the workspace to safe delete.

    Returns:
        dict: Response data if the force unlock request is successfully initiated,
        or an empty dictionary if the workspace is not found.

    Raises:
        TerraformError: If the force unlock request fails with a non-404 or non-200 status code.
    """
    response = client.post(f"/workspaces/{workspace_id}/actions/force-unlock")
    response_data = response.get("data", {})
    response_status = response["status"]

    if response["status"] == 404:
        # Workspace was not found
        # This should not raise an exception
        return {}

    elif response_status == 200:
        # workspace was force unlocked successfully
        response_data.update({"status": response_status})
        return response_data

    else:
        # Force unlock process was not initiated successfully
        # there can be several reasons for this so we raise an exception with the response
        raise TerraformError(response)


def sort_list(val):
    if isinstance(val, list):
        if isinstance(val[0], dict):
            sorted_keys = [tuple(sorted(dict_.keys())) for dict_ in val]
            # All keys should be identical
            if len(set(sorted_keys)) != 1:
                raise ValueError("dictionaries do not match")

            return sorted(val, key=lambda d: tuple(d[k] for k in sorted_keys[0]))
        return sorted(val)
    return val


def dict_diff(base, comparable):
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
        raise AssertionError("`base` must be of type <dict>")
    if not isinstance(comparable, dict):
        if comparable is None:
            comparable = dict()
        else:
            raise AssertionError("`comparable` must be of type <dict>")

    updates = dict()

    for key, value in iteritems(base):
        if isinstance(value, dict):
            item = comparable.get(key)
            if item is not None:
                sub_diff = dict_diff(value, comparable[key])
                if sub_diff:
                    updates[key] = sub_diff
        else:
            comparable_value = comparable.get(key)
            if comparable_value is not None:
                if sort_list(base[key]) != sort_list(comparable_value):
                    updates[key] = comparable_value

    for key in set(comparable.keys()).difference(base.keys()):
        updates[key] = comparable.get(key)

    return updates
