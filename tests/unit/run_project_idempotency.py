import importlib.util
import sys
from pathlib import Path

# Load the repo's plugins/modules/project.py directly to avoid test-suite package shadowing
repo_root = Path(__file__).resolve().parents[2]
proj_path = repo_root / "plugins" / "modules" / "project.py"
spec = importlib.util.spec_from_file_location("repo_project", str(proj_path))
mod = importlib.util.module_from_spec(spec)
sys.modules["repo_project"] = mod
spec.loader.exec_module(mod)

# initial project
project_initial = {
    "data": {
        "id": "prj-test",
        "attributes": {
            "name": "proj",
            "description": "test project",
            "auto-destroy-activity-duration": "14d",
            "default-execution-mode": "remote",
        },
        "relationships": {"default-agent-pool": {"data": None}},
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
        "relationships": {"default-agent-pool": {"data": None}},
    }
}

params = {
    "project": "proj",
    "description": "test project updated",
    "auto_destroy_activity_duration": "15d",
    "execution_mode": "local",
    "tag_bindings": [{"key": "env", "value": "production"}],
}

# patch fetch_project_tag_bindings by assigning directly on module
mod.fetch_project_tag_bindings = lambda client, project_id: {"env": "development"}
res_first = mod.state_update(client=None, params=params, project=project_initial, check_mode=True)
print("first:", res_first)

mod.fetch_project_tag_bindings = lambda client, project_id: {"env": "production"}
res_second = mod.state_update(client=None, params=params, project=project_updated, check_mode=True)
print("second:", res_second)
