import pytest

from plugins.modules import project as mod


def test_project_update_idempotency(monkeypatch):
    # Monkeypatch fetch_project_tag_bindings to control tag binding reads
    # First call: project has env=development
    # After update: project has env=production

    # Define initial project data as returned by the REST-style wrapper
    project_initial = {
        "data": {
            "id": "prj-test",
            "attributes": {
                "name": "proj",
                "description": "test project",
                "auto-destroy-activity-duration": "14d",
                "default-execution-mode": "remote",
            },
            "relationships": {
                "default-agent-pool": {"data": None}
            },
        }
    }

    project_updated = {
        "data": {
            "id": "prj-test",
            "attributes": {
                "name": "proj",
                "description": "test project updated",
                "auto-destroy-activity-duration": "15d",
                "default-execution-mode": "local",
            },
            "relationships": {
                "default-agent-pool": {"data": None}
            },
        }
    }

    params = {
        "project": "proj",
        "description": "test project updated",
        "auto_destroy_activity_duration": "15d",
        "execution_mode": "local",
        "tag_bindings": [{"key": "env", "value": "production"}],
    }

    # Simulate tag bindings read returning development initially
    monkeypatch.setattr(mod, "fetch_project_tag_bindings", lambda client, project_id: {"env": "development"})

    # First invocation: expect an update is required (changed True)
    res_first = mod.state_update(client=None, params=params, project=project_initial, check_mode=True)
    assert res_first.get("changed") is True, f"Expected first update to be needed, got: {res_first}"

    # Now simulate the remote state matching desired state
    monkeypatch.setattr(mod, "fetch_project_tag_bindings", lambda client, project_id: {"env": "production"})

    # Second invocation: no changes should be detected
    res_second = mod.state_update(client=None, params=params, project=project_updated, check_mode=True)
    assert res_second.get("changed") is False, f"Expected idempotent second update, got: {res_second}"
