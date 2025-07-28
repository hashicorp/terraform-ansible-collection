.. _hashicorp.terraform.configuration_version_module:


*****************************************
hashicorp.terraform.configuration_version
*****************************************

**Manage configuration versions in Terraform Enterprise/Cloud.**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Create or archive configuration-versions in Terraform Enterprise/Cloud.
- If *workspace* and *configuration_files_path* is specified and the *state* is ``present``, this module will create a configuration version in the workspace and upload the file to it.
- If a *configuration_version_id* is specified and the *state* is ``archived``, this module will discard the uploaded ``.tar.gz`` file associated with this configuration version. This can only archive the configuration versions that were created with the API or CLI, are in an uploaded state, have no runs in progress, and are not the current configuration version for any workspace.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>auto_queue_runs</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>no</li>
                                    <li><div style="color: blue"><b>yes</b>&nbsp;&larr;</div></li>
                        </ul>
                </td>
                <td>
                        <div>When true, runs are queued automatically when the configuration version is uploaded.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>configuration_files_path</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">path</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Path to the configuration file that should be uploaded for the configuration version.</div>
                        <div>This can be a directory or a tarball (`.tar.gz`) containing configuration-related files.</div>
                        <div>When a path to a directory is provided, all it&#x27;s content will be built into a tarball (&#x27;.tar.gz&#x27;) within the module.</div>
                        <div>This file will be read from the Ansible &#x27;host&#x27; context and not the &#x27;controller&#x27; context.</div>
                        <div style="font-size: small; color: darkgreen"><br/>aliases: project_path</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>configuration_version_id</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>The id of the configuration version that needs to be archived.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>organization</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Name of the organization that the workspace for the configuration-version belongs to.</div>
                        <div>This is required when <em>workspace</em> key is set.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>poll_interval</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">2</div>
                </td>
                <td>
                        <div>Configures the interval (in seconds) to wait between retries of inspecting the `configuration-version` status.</div>
                        <div>This is used with `state=present` when creating a new configuration-version and uploading a configuration file for it.</div>
                        <div>This works in conjunction with the <em>poll_timeout</em> parameter.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>poll_timeout</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">10</div>
                </td>
                <td>
                        <div>Configures the timeout (in seconds) for polling while inspecting the `configuration-version` status.</div>
                        <div>This is used with `state=present` when creating a new configuration-version and uploading a configuration file for it.</div>
                        <div>This works in conjunction with the <em>poll_interval</em> parameter.</div>
                        <div>This would factor in the time in case of errors leading to exponential backoff.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>provisional</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>no</b>&nbsp;&larr;</div></li>
                                    <li>yes</li>
                        </ul>
                </td>
                <td>
                        <div>When <code>true</code>, this configuration version does not immediately become the workspace current configuration version. If the associated run is applied, it then becomes the current configuration version unless a newer one exists.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>speculative</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>no</b>&nbsp;&larr;</div></li>
                                    <li>yes</li>
                        </ul>
                </td>
                <td>
                        <div>When true, this configuration version may only be used to create runs which are speculative which cannot be confirmed or applied.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>state</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>present</b>&nbsp;&larr;</div></li>
                                    <li>absent</li>
                                    <li>archived</li>
                        </ul>
                </td>
                <td>
                        <div>The state the configuration version should be in.</div>
                        <div>Setting `state=present` creates a new configuration-version and upload to it.</div>
                        <div>Setting `state=archived` archives an existing configuration-version, if it exists. Requires the <em>configuration_version_id</em> field to be set.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>tf_hostname</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">"https://app.terraform.io"</div>
                </td>
                <td>
                        <div>The Terraform Enterprise hostname.</div>
                        <div>If this value is not set, the environment variable <code>TF_HOSTNAME</code> environment variables will be tried.</div>
                        <div>If the environment variable is also unset, this will default to <a href='https://app.terraform.io'>https://app.terraform.io</a>.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>tf_max_retries</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">3</div>
                </td>
                <td>
                        <div>Specifies the total number of retries to allow for a request to TFE/C.</div>
                        <div>If this value is not set, the environment variable <code>TF_MAX_RETRIES</code> will be tried.</div>
                        <div>If the environment variable is also unset, by default <code>3</code> retries will be performed.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>tf_timeout</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">10</div>
                </td>
                <td>
                        <div>Specifies the timeout (in seconds) Ansible should use for requests sent to TFE/C.</div>
                        <div>If this value is not set, the environment variable <code>TF_TIMEOUT</code> will be used.</div>
                        <div>If the environment variable is also unset, this value will default to 10s.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>tf_token</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>The Terraform Enterprise/Cloud authentication token.</div>
                        <div>See the HCP documentation for more information about authentication tokens <a href='https://developer.hashicorp.com/terraform/cloud-docs/api-docs#authentication'>https://developer.hashicorp.com/terraform/cloud-docs/api-docs#authentication</a>.</div>
                        <div>If this value is not set, the environment variable <code>TF_TOKEN</code> environment variables will be tried.</div>
                        <div>If the environment variable is also unset, an exception will be raised and the task will fail.</div>
                        <div>The user should ensure that token being used has the correct permissions to perform the operations requested through the Ansible task.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>tf_validate_certs</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>no</li>
                                    <li><div style="color: blue"><b>yes</b>&nbsp;&larr;</div></li>
                        </ul>
                </td>
                <td>
                        <div>Determines whether to allow insecure connections to Terraform Enterprise/Cloud.</div>
                        <div>If <code>no</code>, SSL certificates will not be validated.</div>
                        <div>If this value is not set, the environment variable <code>TF_VALIDATE_CERTS</code> environment variables will be tried.</div>
                        <div>If the environment variable is also unset, certificates will be validated.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>workspace</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Name of the workspace for the configuration-version.</div>
                        <div>When this key is set, <em>organization</em> must be specified so that the ID of the workspace can be retrieved.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>workspace_id</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>ID of the workspace for the configuration-version.</div>
                        <div>Either <em>workspace</em> (and <em>organization</em>) or <em>workspace_id</em> must be specified when creating new a `configuration-version`.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - **Caution:** When run against a remote host, environment variables and files will be read from the Ansible 'host' context and not the 'controller' context. As such, files may need to be explicitly copied to the 'host' before the task is executed.



Examples
--------

.. code-block:: yaml

    - name: Create a configuration version and queue runs
      hashicorp.terraform.configuration_version:
        workspace: <your-workspace-id>
        state: present
        configuration_files_path: <path-to-your-configuration-files>
        poll_interval: 3
        poll_timeout: 15

    # Assuming play output is registered in 'result'
    #  "result": {
    #         "attributes": {
    #             "auto-queue-runs": true,
    #             "changed-files": [],
    #             "error": null,
    #             "error-message": null,
    #             "provisional": false,
    #             "source": "tfe-api",
    #             "speculative": false,
    #             "status": "uploaded",
    #             "status-timestamps": {
    #                 "uploaded-at": "2025-07-25T05:26:26+00:00"
    #             }
    #         },
    #         "changed": true,
    #         "failed": false,
    #         "id": "cv-id",
    #         "links": {
    #             "download": "download-link",
    #             "self": "api-link"
    #         },
    #         "relationships": {
    #             "ingress-attributes": {
    #                 "data": null,
    #                 "links": {
    #                     "related": "api-link"
    #                 }
    #             }
    #         },
    #         "type": "configuration-versions"
    #     }

    - name: Create a configuration version but do not queue runs automatically when the configuration version is uploaded.
      hashicorp.terraform.configuration_version:
        workspace: <your-workspace-name>
        organization: <your-organization-name>
        state: present
        auto_queue_runs: false
        configuration_files_path: <path-to-your-configuration-file>

    # Assuming play output is registered in 'result'
    # "result": {
    #         "attributes": {
    #             "auto-queue-runs": false,
    #             "changed-files": [],
    #             "error": null,
    #             "error-message": null,
    #             "provisional": false,
    #             "source": "tfe-api",
    #             "speculative": false,
    #             "status": "uploaded",
    #             "status-timestamps": {
    #                 "uploaded-at": "2025-07-25T05:29:30+00:00"
    #             }
    #         },
    #         "changed": true,
    #         "failed": false,
    #         "id": "cv-id",
    #         "links": {
    #             "download": "download-link",
    #             "self": "api-link"
    #         },
    #         "relationships": {
    #             "ingress-attributes": {
    #                 "data": null,
    #                 "links": {
    #                     "related": "api-link"
    #                 }
    #             }
    #         },
    #         "type": "configuration-versions"
    #     }

    - name: Create a configuration for speculative runs
      hashicorp.terraform.configuration_version:
        workspace_id: <your-workspace-id>
        state: present
        speculative: true
        configuration_files_path: <path-to-your-configuration-file>

    # Assuming play output is registered in 'result'
    # "result": {
    #         "attributes": {
    #             "auto-queue-runs": true,
    #             "changed-files": [],
    #             "error": null,
    #             "error-message": null,
    #             "provisional": false,
    #             "source": "tfe-api",
    #             "speculative": true,
    #             "status": "uploaded",
    #             "status-timestamps": {
    #                 "uploaded-at": "2025-07-25T05:31:36+00:00"
    #             }
    #         },
    #         "changed": true,
    #         "failed": false,
    #         "id": "cv-id",
    #         "links": {
    #             "download": "download-link",
    #             "self": "api-link"
    #         },
    #         "relationships": {
    #             "ingress-attributes": {
    #                 "data": null,
    #                 "links": {
    #                     "related": "api-link"
    #                 }
    #             }
    #         },
    #         "type": "configuration-versions"
    #     }
    #
    # Configuration version is created but could not transition to uploaded state
    #
    # FAILED! => {"attributes": {"auto-queue-runs": true, "changed-files": [], "error": null, "error-message": null,
    # "provisional": true, "source": "tfe-api", "speculative": false, "status": "pending", "status-timestamps": {}},
    # "changed": false, "id": "cv-id", "links": {"self": "api-link"},
    # "msg": "Configuration version cv-id was created but could not transition to uploaded state.", "relationships":
    # {"ingress-attributes": {"data": null, "links": {"related": "api-link"}}},
    # "type": "configuration-versions"}

    - name: Create a configuration version that will not immediately become the workspace current configuration version
      hashicorp.terraform.configuration_version:
        workspace_id: <your-workspace-id>
        state: present
        provisional: true
        configuration_files_path: <path-to-your-configuration-file>

    # Assuming play output is registered in 'result'
    # "result": {
    #         "attributes": {
    #             "auto-queue-runs": true,
    #             "changed-files": [],
    #             "error": null,
    #             "error-message": null,
    #             "provisional": true,
    #             "source": "tfe-api",
    #             "speculative": false,
    #             "status": "uploaded",
    #             "status-timestamps": {
    #                 "uploaded-at": "2025-07-25T09:28:12+00:00"
    #             }
    #         },
    #         "changed": true,
    #         "failed": false,
    #         "id": "cv-id",
    #         "links": {
    #             "download": "download-link",
    #             "self": "api-link"
    #         },
    #         "relationships": {
    #             "ingress-attributes": {
    #                 "data": null,
    #                 "links": {
    #                     "related": "api-link"
    #                 }
    #             }
    #         },
    #         "type": "configuration-versions"
    #     }

    - name: Discard a configuration version
      hashicorp.terraform.configuration_version:
        state: archived
        configuration_version_id: <configuration-version-id>

    # Assuming play output is registered in 'archive_record'
    # "archive_record": {
    #         "changed": true,
    #         "failed": false,
    #         "msg": "Configuration version cv-mTaz7Qq44wVRGcdA archived successfully."
    #     }



Return Values
-------------
Common return values are documented `here <https://docs.ansible.com/ansible/latest/reference_appendices/common_return_values.html#common-return-values>`_, the following are the fields unique to this module:

.. raw:: html

    <table border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="2">Key</th>
            <th>Returned</th>
            <th width="100%">Description</th>
        </tr>
            <tr>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>outputs</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>on success</td>
                <td>
                            <div>A dictionary of the configuration version details.</div>
                    <br/>
                </td>
            </tr>
                                <tr>
                    <td class="elbow-placeholder">&nbsp;</td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>attributes</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>The attributes of the configuration version created.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder">&nbsp;</td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>configuration_version_id</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">string</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>ID of the configuration version created/archived.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder">&nbsp;</td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>msg</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">string</span>
                    </div>
                </td>
                <td>when state is &#x27;archived&#x27;</td>
                <td>
                            <div>The successfull completion of archive.</div>
                    <br/>
                </td>
            </tr>

    </table>
    <br/><br/>


Status
------


Authors
~~~~~~~

- Kaushiki Singh (@kausingh)
