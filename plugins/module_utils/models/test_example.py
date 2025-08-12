
from .runs import RunRequest


if __name__ == "__main__":
    run_request = RunRequest.create(
            workspace_id="ws-123456789",
            message="Deploy infrastructure changes",
            auto_apply=False,
            plan_only=True,
            is_destroy=True
        )


    payload = run_request.model_dump(by_alias=True, exclude_unset=True)
    print(f"Run creation payload: {payload}")
