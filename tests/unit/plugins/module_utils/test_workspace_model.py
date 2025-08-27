import pytest

from ansible_collections.hashicorp.terraform.plugins.module_utils.models.common import (
    Relationship,
    create_project_reference,
)
from ansible_collections.hashicorp.terraform.plugins.module_utils.models.workspace import (
    TagBindingAttributes,
    TagBindingResourceData,
    TagBindingsRelationship,
    WorkspaceAttributes,
    WorkspaceRequest,
)


@pytest.mark.parametrize(
    "input_dict, expected_output",
    [
        (
            {"environment": "uat"},
            [TagBindingResourceData(type="tag-bindings", attributes=TagBindingAttributes(key="environment", value="uat"))],
        ),
        (
            {"team": "devops", "region": "us-east"},
            [
                TagBindingResourceData(type="tag-bindings", attributes=TagBindingAttributes(key="team", value="devops")),
                TagBindingResourceData(type="tag-bindings", attributes=TagBindingAttributes(key="region", value="us-east")),
            ],
        ),
        ({}, []),
    ],
)
def test_create_tag_bindings_reference(input_dict, expected_output):
    result = WorkspaceRequest.create_tag_bindings_reference(input_dict)
    assert result == expected_output


@pytest.mark.parametrize(
    "project_id, tag_bindings, attributes",
    [
        ("proj-123", None, {"name": "dev-workspace"}),
        (None, {"env": "prod"}, {"name": "prod-workspace"}),
        ("proj-456", {"team": "infra"}, {"name": "infra-workspace"}),
        (None, None, {"name": "basic-workspace"}),
    ],
)
def test_workspace_request_create(project_id, tag_bindings, attributes):
    req = WorkspaceRequest.create(project_id=project_id, tag_bindings=tag_bindings, **attributes)

    assert req.data.type == "workspaces"

    attr_dict = req.data.attributes.__dict__
    assert attr_dict["name"] == attributes["name"]

    rel = req.data.relationships

    if project_id or tag_bindings:
        # relationships should be set
        assert rel is not None

        if project_id:
            expected_project_rel = create_project_reference(project_id)
            assert rel.project is not None
            assert isinstance(rel.project, Relationship)
            assert rel.project.data.type == "projects"
            assert expected_project_rel.id == rel.project.data.id

        else:
            assert rel.project is None

        if tag_bindings:
            assert isinstance(rel.tag_bindings, TagBindingsRelationship)
            assert rel.tag_bindings.data is not None
            for item in rel.tag_bindings.data:
                assert item.type == "tag-bindings"
                assert isinstance(item.attributes.key, str)
                assert isinstance(item.attributes.value, str)
        else:
            assert rel.tag_bindings is None
    else:
        # neither project_id nor tag_bindings passed, so relationships should be None
        assert rel is None


def test_workspace_attributes_alias_parsing():
    input_data = {
        "allow-destroy-plan": True,
        "auto-apply": False,
        "terraform-version": "1.5.0",
        "execution-mode": "remote",
        "source-name": "main",
    }

    # WorkspaceAttributes likely uses from_dict if it's a custom BaseModel
    attrs = WorkspaceAttributes.model_validate(input_data)

    assert attrs.allow_destroy_plan is True
    assert attrs.auto_apply is False
    assert attrs.terraform_version == "1.5.0"
    assert attrs.execution_mode == "remote"
    assert attrs.source_name == "main"
